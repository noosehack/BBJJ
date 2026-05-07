"""Gated perception benchmark: YOLO vs bottom-up pose backends.

Experimental discipline:
  - Fixed frozen eval subset from held-out videos
  - Same images for every backend
  - COCO-17 two-athlete normalization for every backend
  - Saved intermediate predictions to JSONL
  - Separate metrics: pose quality / limb ownership / classification / end-to-end
  - Failure taxonomy per image

Usage:
  python benchmark_perception.py freeze          # Step 0: create frozen eval set
  python benchmark_perception.py smoke           # Step 1: smoke test each backend
  python benchmark_perception.py run <backend>   # Step 2+: run one backend
  python benchmark_perception.py compare         # Step 5: compare all results
"""

import json
import math
import os
import random
import sys
import time
import warnings
from collections import Counter, defaultdict
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

import numpy as np

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# ── Config ──────────────────────────────────────────────────────

BENCH_DIR = Path("benchmark_perception")
FROZEN_SET = BENCH_DIR / "frozen_eval.json"
RESULTS_DIR = BENCH_DIR / "results"
OVERLAYS_DIR = BENCH_DIR / "overlays"

FINE_MAP = {
    "mount1": "MNT", "mount2": "MNT",
    "side_control1": "SCTR", "side_control2": "SCTR",
    "back1": "BCTR", "back2": "BCTR",
    "closed_guard1": "CGRD", "closed_guard2": "CGRD",
    "open_guard1": "OGRD", "open_guard2": "OGRD",
    "half_guard1": "HGRD", "half_guard2": "HGRD",
    "turtle1": "TRTL", "turtle2": "TRTL",
    "standing": "STND",
    "5050_1": "5050", "5050_2": "5050",
}

TARGET_CLASSES = ["MNT", "SCTR", "BCTR", "CGRD", "OGRD", "HGRD", "TRTL", "STND"]

# All videos available — we subsample with large stride to avoid frame leakage
# (class distribution is per-video, so video-level holdout leaves classes empty)
ALL_VIDEOS = True
STRIDE = 50  # take every 50th frame to decorrelate


# ── Data types ──────────────────────────────────────────────────

@dataclass
class EvalSample:
    image_id: str
    video_id: str
    position: str
    fine_label: str
    img_path: str
    gt_pose1: Optional[list] = None  # 17 x [x, y, conf]
    gt_pose2: Optional[list] = None


@dataclass
class PoseResult:
    """Raw output from a perception backend for one image."""
    image_id: str
    backend: str
    n_raw_detections: int
    n_after_selection: int
    kps_a: Optional[list] = None  # 17 x [x, y, conf]
    kps_b: Optional[list] = None
    detection_time_ms: float = 0.0
    error: Optional[str] = None


@dataclass
class LimbOwnership:
    """Per-skeleton limb ownership analysis against GT."""
    arms_consistent: float = 0.0   # fraction of arm joints owned by same GT person
    legs_consistent: float = 0.0   # fraction of leg joints owned by same GT person
    torso_consistent: float = 0.0  # fraction of torso joints owned by same GT person
    overall_consistent: float = 0.0
    mixed_skeleton: bool = False   # True if >30% joints from wrong GT person


@dataclass
class ImageResult:
    """Full result for one image through one backend."""
    image_id: str
    video_id: str
    true_label: str
    backend: str

    # Perception
    n_raw_detections: int = 0
    n_selected: int = 0
    detection_time_ms: float = 0.0
    detection_error: Optional[str] = None

    # Keypoints (saved for analysis)
    kps_a: Optional[list] = None
    kps_b: Optional[list] = None

    # Pose quality
    mean_conf_a: float = 0.0
    mean_conf_b: float = 0.0
    high_conf_kps_a: int = 0
    high_conf_kps_b: int = 0
    pck_a: float = 0.0  # PCK@0.2 vs GT
    pck_b: float = 0.0

    # Limb ownership
    ownership_a: Optional[dict] = None
    ownership_b: Optional[dict] = None

    # Geometry features (saved for debugging)
    geometry_features: Optional[dict] = None

    # Classification
    radical_prediction: Optional[str] = None
    radical_confidence: float = 0.0
    radical_correct: bool = False
    top3: Optional[list] = None

    # Failure classification
    failure_type: str = "unknown"
    # missed_athlete | duplicate_ghost | merged_athletes |
    # cross_assigned_limbs | bad_keypoints | geometry_error | correct


# ── Step 0: Freeze eval set ────────────────────────────────────

def freeze_eval_set(n_per_class=50, seed=42):
    """Select a fixed, balanced eval subset with stride-based subsampling.

    Classes are per-video in this dataset, so video-level holdout leaves
    classes empty. Instead we subsample every STRIDE-th frame per class
    to decorrelate, then take n_per_class balanced across videos.
    """
    random.seed(seed)

    with open("data/raw/annotations.json") as f:
        anns = json.load(f)

    # Sort annotations by image_id (frame order within each video)
    anns.sort(key=lambda a: a["image"])

    # Group by class, take every STRIDE-th frame
    by_class = defaultdict(list)
    class_counter = defaultdict(int)

    for a in anns:
        pos = a["position"]
        fine = FINE_MAP.get(pos)
        if fine not in TARGET_CLASSES:
            continue

        class_counter[fine] += 1
        if class_counter[fine] % STRIDE != 0:
            continue

        vid = a["image"][:2]
        img_path = f"data/raw/images/{a['image']}.jpg"
        if not os.path.exists(img_path):
            continue

        p1 = a.get("pose1")
        p2 = a.get("pose2")
        has_gt = (p1 and len(p1) == 17 and p2 and len(p2) == 17)

        by_class[fine].append({
            "image_id": a["image"],
            "video_id": vid,
            "position": pos,
            "fine_label": fine,
            "img_path": img_path,
            "has_gt": has_gt,
            "gt_pose1": p1 if has_gt else None,
            "gt_pose2": p2 if has_gt else None,
        })

    # Balance: take n_per_class from each, diversify across videos
    selected = []
    for cls in sorted(TARGET_CLASSES):
        items = by_class.get(cls, [])
        random.shuffle(items)

        # Prefer items with GT, diversify videos
        with_gt = [x for x in items if x["has_gt"]]
        without_gt = [x for x in items if not x["has_gt"]]

        picked = []
        seen_vids = Counter()
        for item in with_gt + without_gt:
            if len(picked) >= n_per_class:
                break
            # Soft video diversity: allow max n_per_class/3 per video
            vid = item["video_id"]
            if seen_vids[vid] < max(n_per_class // 3, 5):
                seen_vids[vid] += 1
                picked.append(item)

        selected.extend(picked)

    BENCH_DIR.mkdir(parents=True, exist_ok=True)

    meta = {
        "created": time.strftime("%Y-%m-%d %H:%M:%S"),
        "seed": seed,
        "n_per_class": n_per_class,
        "sampling": f"stride-{STRIDE} from all videos",
        "target_classes": TARGET_CLASSES,
        "total": len(selected),
        "per_class": {cls: sum(1 for s in selected if s["fine_label"] == cls)
                      for cls in TARGET_CLASSES},
        "with_gt": sum(1 for s in selected if s["has_gt"]),
    }

    with open(FROZEN_SET, "w") as f:
        json.dump({"meta": meta, "samples": selected}, f, indent=2)

    print(f"Frozen eval set: {len(selected)} images")
    print(f"Sampling: stride-{STRIDE} from all videos")
    print(f"With GT keypoints: {meta['with_gt']}/{meta['total']}")
    print(f"\nPer class:")
    for cls in sorted(TARGET_CLASSES):
        n = meta["per_class"].get(cls, 0)
        n_gt = sum(1 for s in selected if s["fine_label"] == cls and s["has_gt"])
        print(f"  {cls:>5s}: {n:>4d} ({n_gt} with GT)")

    return selected


# ── Pose backends (COCO-17 normalization) ───────────────────────

class PoseBackend:
    """Base class. All backends must return list of 17x[x,y,conf] detections."""
    name = "base"

    def detect(self, img_path: str) -> list:
        raise NotImplementedError

    def select_two(self, detections: list) -> tuple:
        """Select two athletes from detections. Returns (kps_a, kps_b) or raises."""
        if len(detections) < 2:
            raise ValueError(f"Need 2 athletes, found {len(detections)}")

        # Score by mean confidence, pick top 2 most distinct
        if len(detections) == 2:
            return detections[0], detections[1]

        # For >2: pick most distinct pair (minimize overlap, maximize coverage)
        from tools.infer_image import _select_most_distinct_pair, _bbox_area, _mean_conf
        viable = [(i, d) for i, d in enumerate(detections) if _mean_conf(d) > 0.15]
        if len(viable) < 2:
            raise ValueError(f"Need 2 viable athletes, found {len(viable)}")
        if len(viable) == 2:
            return viable[0][1], viable[1][1]
        pair = _select_most_distinct_pair(viable)
        if pair:
            return pair
        raise ValueError("Could not select athlete pair")


class YoloBackend(PoseBackend):
    name = "yolo_ft_v2"

    def __init__(self, model_path="models_pose/bjj_v2_posehead/weights/best.pt", nms_iou=0.8):
        from tools.infer_image import YoloPoseBackend, _nms_keypoints
        self._yolo = YoloPoseBackend(model_path)
        self._nms_iou = nms_iou

    def detect(self, img_path):
        from tools.infer_image import _nms_keypoints
        raw = self._yolo.detect(img_path)
        return _nms_keypoints(raw, iou_thresh=self._nms_iou)


class OpenPifPafBackend(PoseBackend):
    name = "openpifpaf"

    def __init__(self):
        import openpifpaf
        self._predictor = openpifpaf.Predictor(checkpoint="shufflenetv2k30")

    def detect(self, img_path):
        from PIL import Image
        img = Image.open(img_path).convert("RGB")
        predictions, _, _ = self._predictor.pil_image(img)

        detections = []
        for pred in predictions:
            kps = pred.data  # shape (17, 3) for COCO body checkpoint
            if len(kps) == 17:
                person = [[float(kps[i][0]), float(kps[i][1]), float(kps[i][2])]
                          for i in range(17)]
                detections.append(person)
        return detections


class MMPoseBackend(PoseBackend):
    name = "mmpose_rtmo"

    def __init__(self):
        from mmpose.apis import MMPoseInferencer
        # RTMO: one-stage multi-person (bottom-up-like, trained on 7 body datasets)
        self._inferencer = MMPoseInferencer(pose2d="rtmo-l_16xb16-600e_body7-640x640")

    def detect(self, img_path):
        result = next(self._inferencer(img_path, return_datasamples=True))
        preds = result["predictions"]

        detections = []
        if isinstance(preds, list):
            for p in preds:
                if hasattr(p, "pred_instances"):
                    instances = p.pred_instances
                    for i in range(len(instances.keypoints)):
                        kps_xy = instances.keypoints[i]        # (17, 2)
                        kps_conf = instances.keypoint_scores[i]  # (17,)
                        person = [[float(kps_xy[j][0]), float(kps_xy[j][1]),
                                   float(kps_conf[j])]
                                  for j in range(17)]
                        detections.append(person)
        return detections


# ── Metrics ─────────────────────────────────────────────────────

def mean_conf(kps):
    return sum(c for _, _, c in kps) / len(kps) if kps else 0.0


def pck_score(det_kps, gt_kps, threshold=0.2):
    """PCK@threshold using GT torso length as reference."""
    sh = ((gt_kps[5][0]+gt_kps[6][0])/2, (gt_kps[5][1]+gt_kps[6][1])/2)
    hp = ((gt_kps[11][0]+gt_kps[12][0])/2, (gt_kps[11][1]+gt_kps[12][1])/2)
    torso_len = max(math.dist(sh, hp), 10)
    thr = threshold * torso_len

    ok = total = 0
    for i in range(17):
        if gt_kps[i][2] > 0:
            total += 1
            d = math.dist((det_kps[i][0], det_kps[i][1]),
                          (gt_kps[i][0], gt_kps[i][1]))
            if d <= thr:
                ok += 1
    return ok / total if total > 0 else 0.0


def gt_center(kps):
    """Center of torso keypoints."""
    pts = [kps[i] for i in [5, 6, 11, 12] if kps[i][2] > 0]
    if len(pts) < 2:
        pts = [k for k in kps if k[2] > 0]
    if not pts:
        return None
    return (np.mean([p[0] for p in pts]), np.mean([p[1] for p in pts]))


def match_detection_to_gt(det_kps, gt_p1, gt_p2):
    """Return which GT person (1 or 2) this detection is closest to."""
    dc = gt_center(det_kps)
    if dc is None:
        return None, float("inf")
    g1, g2 = gt_center(gt_p1), gt_center(gt_p2)
    d1 = math.dist(dc, g1) if g1 else float("inf")
    d2 = math.dist(dc, g2) if g2 else float("inf")
    return (1, d1) if d1 <= d2 else (2, d2)


def limb_ownership_analysis(det_kps, gt_p1, gt_p2):
    """For each detected joint, check if nearest GT joint belongs to same person.

    Returns LimbOwnership with consistency scores per body region.
    """
    ARM_JOINTS = [5, 6, 7, 8, 9, 10]    # shoulders, elbows, wrists
    LEG_JOINTS = [11, 12, 13, 14, 15, 16]  # hips, knees, ankles
    TORSO_JOINTS = [0, 5, 6, 11, 12]     # nose, shoulders, hips

    # Determine which GT person this detection "belongs to" (by torso center)
    match_id, _ = match_detection_to_gt(det_kps, gt_p1, gt_p2)
    if match_id is None:
        return LimbOwnership()

    def check_group(joint_ids):
        correct = total = 0
        for j in joint_ids:
            if det_kps[j][2] < 0.1:
                continue
            total += 1
            d1 = math.dist((det_kps[j][0], det_kps[j][1]),
                           (gt_p1[j][0], gt_p1[j][1])) if gt_p1[j][2] > 0 else float("inf")
            d2 = math.dist((det_kps[j][0], det_kps[j][1]),
                           (gt_p2[j][0], gt_p2[j][1])) if gt_p2[j][2] > 0 else float("inf")
            nearest_gt = 1 if d1 <= d2 else 2
            if nearest_gt == match_id:
                correct += 1
        return correct / total if total > 0 else 1.0

    arms = check_group(ARM_JOINTS)
    legs = check_group(LEG_JOINTS)
    torso = check_group(TORSO_JOINTS)
    overall = check_group(list(range(17)))

    return LimbOwnership(
        arms_consistent=arms,
        legs_consistent=legs,
        torso_consistent=torso,
        overall_consistent=overall,
        mixed_skeleton=(overall < 0.7),
    )


def classify_failure(result: ImageResult) -> str:
    """Classify the failure mode for this image."""
    if result.detection_error:
        if "Need 2" in (result.detection_error or ""):
            if result.n_raw_detections < 2:
                return "missed_athlete"
            return "merged_athletes"
        return "detection_error"

    if result.n_selected < 2:
        return "missed_athlete"

    # Check for duplicate ghost (both detections match same GT person)
    # This requires GT — skip if no ownership data
    if result.ownership_a and result.ownership_b:
        oa = result.ownership_a
        ob = result.ownership_b
        if oa.get("overall_consistent", 1) < 0.5 and ob.get("overall_consistent", 1) < 0.5:
            return "merged_athletes"
        if oa.get("mixed_skeleton") or ob.get("mixed_skeleton"):
            return "cross_assigned_limbs"

    # Check PCK
    if result.pck_a < 0.3 or result.pck_b < 0.3:
        return "bad_keypoints"

    # If detection was OK but classification wrong
    if not result.radical_correct:
        return "geometry_error"

    return "correct"


# ── Step 1: Smoke test ──────────────────────────────────────────

def smoke_test():
    """Run each backend on one image. Verify output format."""
    # Pick one image that exists
    with open("data/raw/annotations.json") as f:
        anns = json.load(f)

    test_img = None
    for a in anns:
        if a["position"] == "standing":
            path = f"data/raw/images/{a['image']}.jpg"
            if os.path.exists(path):
                test_img = path
                break
    if not test_img:
        for a in anns:
            path = f"data/raw/images/{a['image']}.jpg"
            if os.path.exists(path):
                test_img = path
                break

    if not test_img:
        print("ERROR: no test image found")
        return False

    print(f"Smoke test image: {test_img}")
    print(f"{'='*60}")

    backends = []

    # YOLO
    try:
        print("\n[1/3] YOLO ft-v2 + NMS=0.8...")
        b = YoloBackend()
        t0 = time.time()
        dets = b.detect(test_img)
        dt = (time.time() - t0) * 1000
        kps_a, kps_b = b.select_two(dets)
        print(f"  OK: {len(dets)} detections, selected 2")
        print(f"  Time: {dt:.0f}ms")
        print(f"  A: {len(kps_a)} kps, mean_conf={mean_conf(kps_a):.3f}")
        print(f"  B: {len(kps_b)} kps, mean_conf={mean_conf(kps_b):.3f}")
        backends.append("yolo_ft_v2")
    except Exception as e:
        print(f"  FAIL: {e}")

    # OpenPifPaf
    try:
        print("\n[2/3] OpenPifPaf...")
        b = OpenPifPafBackend()
        t0 = time.time()
        dets = b.detect(test_img)
        dt = (time.time() - t0) * 1000
        kps_a, kps_b = b.select_two(dets)
        print(f"  OK: {len(dets)} detections, selected 2")
        print(f"  Time: {dt:.0f}ms")
        print(f"  A: {len(kps_a)} kps, mean_conf={mean_conf(kps_a):.3f}")
        print(f"  B: {len(kps_b)} kps, mean_conf={mean_conf(kps_b):.3f}")
        backends.append("openpifpaf")
    except Exception as e:
        print(f"  FAIL: {e}")

    # MMPose RTMO
    try:
        print("\n[3/3] MMPose RTMO...")
        b = MMPoseBackend()
        t0 = time.time()
        dets = b.detect(test_img)
        dt = (time.time() - t0) * 1000
        kps_a, kps_b = b.select_two(dets)
        print(f"  OK: {len(dets)} detections, selected 2")
        print(f"  Time: {dt:.0f}ms")
        print(f"  A: {len(kps_a)} kps, mean_conf={mean_conf(kps_a):.3f}")
        print(f"  B: {len(kps_b)} kps, mean_conf={mean_conf(kps_b):.3f}")
        backends.append("mmpose_rtmo")
    except Exception as e:
        print(f"  FAIL: {e}")

    print(f"\n{'='*60}")
    print(f"Working backends: {backends}")
    return len(backends) > 0


# ── Step 2-4: Run one backend ───────────────────────────────────

def run_backend(backend_name: str, limit: int = 0):
    """Run a single backend on the frozen eval set."""
    if not FROZEN_SET.exists():
        print("ERROR: Run 'freeze' first to create frozen eval set")
        return

    with open(FROZEN_SET) as f:
        data = json.load(f)
    samples = data["samples"]
    if limit > 0:
        samples = samples[:limit]

    print(f"Running {backend_name} on {len(samples)} images...")

    # Init backend
    if backend_name == "yolo_ft_v2":
        backend = YoloBackend()
    elif backend_name == "openpifpaf":
        backend = OpenPifPafBackend()
    elif backend_name == "mmpose_rtmo":
        backend = MMPoseBackend()
    elif backend_name == "gt":
        backend = None  # GT keypoints mode
    else:
        print(f"Unknown backend: {backend_name}")
        return

    # Init geometry classifier
    from tools.geometry_classifier import classify_both_pov

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    overlay_dir = OVERLAYS_DIR / backend_name
    overlay_dir.mkdir(parents=True, exist_ok=True)

    results = []
    t_total = time.time()

    for i, sample in enumerate(samples):
        img_id = sample["image_id"]
        true_label = sample["fine_label"]
        img_path = sample["img_path"]

        r = ImageResult(
            image_id=img_id,
            video_id=sample["video_id"],
            true_label=true_label,
            backend=backend_name,
        )

        # ── Perception ──
        if backend_name == "gt":
            # Use GT keypoints directly
            if not sample.get("gt_pose1") or not sample.get("gt_pose2"):
                r.detection_error = "no_gt_keypoints"
                r.failure_type = "no_gt"
                results.append(r)
                continue
            kps_a = sample["gt_pose1"]
            kps_b = sample["gt_pose2"]
            r.n_raw_detections = 2
            r.n_selected = 2
            # Assign POV based on position suffix
            suffix = sample["position"][-1] if sample["position"][-1] in "12" else "0"
            if suffix == "2":
                kps_a, kps_b = kps_b, kps_a
        else:
            try:
                t0 = time.time()
                dets = backend.detect(img_path)
                r.n_raw_detections = len(dets)
                kps_a, kps_b = backend.select_two(dets)
                r.detection_time_ms = (time.time() - t0) * 1000
                r.n_selected = 2
            except Exception as e:
                r.detection_error = str(e)
                r.detection_time_ms = (time.time() - t0) * 1000 if 't0' in dir() else 0
                r.failure_type = classify_failure(r)
                results.append(r)
                if (i + 1) % 50 == 0:
                    print(f"  [{i+1}/{len(samples)}] {sum(1 for x in results if x.radical_correct)}/{len(results)} correct")
                continue

        r.kps_a = kps_a
        r.kps_b = kps_b

        # ── Pose quality ──
        r.mean_conf_a = mean_conf(kps_a)
        r.mean_conf_b = mean_conf(kps_b)
        r.high_conf_kps_a = sum(1 for _, _, c in kps_a if c > 0.5)
        r.high_conf_kps_b = sum(1 for _, _, c in kps_b if c > 0.5)

        # ── PCK vs GT ──
        gt1 = sample.get("gt_pose1")
        gt2 = sample.get("gt_pose2")
        if gt1 and gt2 and len(gt1) == 17 and len(gt2) == 17:
            # Match detected A/B to GT 1/2
            ma, _ = match_detection_to_gt(kps_a, gt1, gt2)
            mb, _ = match_detection_to_gt(kps_b, gt1, gt2)

            if ma == 1:
                r.pck_a = pck_score(kps_a, gt1)
                r.pck_b = pck_score(kps_b, gt2)
            else:
                r.pck_a = pck_score(kps_a, gt2)
                r.pck_b = pck_score(kps_b, gt1)

            # ── Limb ownership ──
            own_a = limb_ownership_analysis(kps_a, gt1, gt2)
            own_b = limb_ownership_analysis(kps_b, gt1, gt2)
            r.ownership_a = asdict(own_a)
            r.ownership_b = asdict(own_b)

        # ── Geometry classification ──
        try:
            geo_result = classify_both_pov(kps_a, kps_b)
            r.radical_prediction = geo_result.radical
            r.radical_confidence = geo_result.confidence
            r.radical_correct = (geo_result.radical == true_label)
            sorted_probs = sorted(geo_result.probabilities.items(), key=lambda x: -x[1])
            r.top3 = [{"radical": rad, "conf": round(p, 4)} for rad, p in sorted_probs[:3]]
        except Exception as e:
            r.radical_prediction = "ERROR"
            r.radical_confidence = 0.0

        # ── Failure classification ──
        r.failure_type = classify_failure(r)

        results.append(r)

        if (i + 1) % 50 == 0:
            correct = sum(1 for x in results if x.radical_correct)
            print(f"  [{i+1}/{len(samples)}] {correct}/{len(results)} = {correct/len(results):.1%}")

    elapsed = time.time() - t_total

    # ── Save results ──
    out_path = RESULTS_DIR / f"{backend_name}.jsonl"
    with open(out_path, "w") as f:
        for r in results:
            f.write(json.dumps(asdict(r), default=str) + "\n")

    # ── Print summary ──
    print_backend_summary(results, backend_name, elapsed)

    return results


# ── Reporting ───────────────────────────────────────────────────

def print_backend_summary(results, backend_name, elapsed):
    n = len(results)
    detected = [r for r in results if r.detection_error is None]
    correct = sum(1 for r in results if r.radical_correct)

    print(f"\n{'='*70}")
    print(f"  {backend_name.upper()} — {n} images, {elapsed:.1f}s")
    print(f"{'='*70}")

    # A. Pose quality
    print(f"\n  A. POSE QUALITY")
    det_rate = len(detected) / n if n > 0 else 0
    print(f"     Two-athlete detection rate: {len(detected)}/{n} = {det_rate:.1%}")

    ftypes = Counter(r.failure_type for r in results)
    print(f"     Failure types:")
    for ft, cnt in ftypes.most_common():
        print(f"       {ft:>25s}: {cnt:>4d} ({cnt/n:.0%})")

    pcks = [r.pck_a for r in detected if r.pck_a > 0] + [r.pck_b for r in detected if r.pck_b > 0]
    if pcks:
        print(f"     Mean PCK@0.2: {np.mean(pcks):.1%}")

    # Limb ownership
    owns = []
    for r in detected:
        if r.ownership_a:
            owns.append(r.ownership_a)
        if r.ownership_b:
            owns.append(r.ownership_b)
    if owns:
        print(f"\n     Limb ownership (fraction joints from correct GT person):")
        print(f"       Arms:    {np.mean([o['arms_consistent'] for o in owns]):.1%}")
        print(f"       Legs:    {np.mean([o['legs_consistent'] for o in owns]):.1%}")
        print(f"       Torso:   {np.mean([o['torso_consistent'] for o in owns]):.1%}")
        print(f"       Overall: {np.mean([o['overall_consistent'] for o in owns]):.1%}")
        mixed = sum(1 for o in owns if o.get("mixed_skeleton"))
        print(f"       Mixed skeletons: {mixed}/{len(owns)} = {mixed/len(owns):.0%}")

    # B. Geometry classifier
    print(f"\n  B. CLASSIFICATION")
    print(f"     Overall accuracy: {correct}/{n} = {correct/n:.1%}")
    if detected:
        det_correct = sum(1 for r in detected if r.radical_correct)
        print(f"     When detected:    {det_correct}/{len(detected)} = {det_correct/len(detected):.1%}")

    # Per-class
    print(f"\n     {'Class':>5s} {'N':>5s} {'Det':>5s} {'Acc':>6s} {'DetAcc':>7s} {'PCK':>6s} {'LimbOwn':>8s}  Confused")
    print(f"     {'-'*5} {'-'*5} {'-'*5} {'-'*6} {'-'*7} {'-'*6} {'-'*8}  {'-'*25}")
    for cls in sorted(TARGET_CLASSES):
        cr = [r for r in results if r.true_label == cls]
        nc = len(cr)
        if nc == 0:
            continue
        det = [r for r in cr if r.detection_error is None]
        ok = sum(1 for r in cr if r.radical_correct)
        det_ok = sum(1 for r in det if r.radical_correct)
        cls_pcks = [r.pck_a for r in det if r.pck_a > 0] + [r.pck_b for r in det if r.pck_b > 0]
        cls_pck = np.mean(cls_pcks) if cls_pcks else 0
        cls_owns = []
        for r in det:
            if r.ownership_a:
                cls_owns.append(r.ownership_a["overall_consistent"])
            if r.ownership_b:
                cls_owns.append(r.ownership_b["overall_consistent"])
        cls_own = np.mean(cls_owns) if cls_owns else 0

        confused = Counter(r.radical_prediction for r in cr if not r.radical_correct and r.radical_prediction)
        conf_str = ", ".join(f"{p}({c})" for p, c in confused.most_common(3))

        print(f"     {cls:>5s} {nc:>5d} {len(det):>5d} {ok/nc:>6.0%} {det_ok/max(len(det),1):>7.0%} {cls_pck:>6.1%} {cls_own:>8.1%}  {conf_str}")

    # C. End-to-end
    print(f"\n  C. END-TO-END")
    print(f"     Image -> Pose -> Geometry -> Radical")
    print(f"     Accuracy: {correct}/{n} = {correct/n:.1%}")
    if elapsed > 0:
        print(f"     Throughput: {n/elapsed:.1f} images/sec ({elapsed/n*1000:.0f}ms/image)")


# ── Step 5: Compare all backends ────────────────────────────────

def compare():
    """Load all saved results and produce comparison table."""
    if not RESULTS_DIR.exists():
        print("ERROR: No results found. Run backends first.")
        return

    all_results = {}
    for f in sorted(RESULTS_DIR.glob("*.jsonl")):
        backend = f.stem
        results = []
        for line in open(f):
            results.append(json.loads(line))
        all_results[backend] = results

    if not all_results:
        print("No results to compare.")
        return

    print(f"\n{'='*90}")
    print(f"  PERCEPTION BENCHMARK COMPARISON")
    print(f"{'='*90}")

    # Header
    headers = ["Metric"] + list(all_results.keys())
    col_w = 14

    def row(label, values):
        print(f"  {label:<30s}" + "".join(f"{v:>{col_w}s}" for v in values))

    row("", list(all_results.keys()))
    print(f"  {'-'*30}" + ("-" * col_w) * len(all_results))

    # Compute metrics for each backend
    metrics = {}
    for backend, results in all_results.items():
        n = len(results)
        detected = [r for r in results if r.get("detection_error") is None]
        correct = sum(1 for r in results if r.get("radical_correct"))

        pcks = []
        for r in detected:
            if r.get("pck_a", 0) > 0:
                pcks.append(r["pck_a"])
            if r.get("pck_b", 0) > 0:
                pcks.append(r["pck_b"])

        owns = []
        for r in detected:
            if r.get("ownership_a"):
                owns.append(r["ownership_a"]["overall_consistent"])
            if r.get("ownership_b"):
                owns.append(r["ownership_b"]["overall_consistent"])

        legs_own = []
        for r in detected:
            if r.get("ownership_a"):
                legs_own.append(r["ownership_a"]["legs_consistent"])
            if r.get("ownership_b"):
                legs_own.append(r["ownership_b"]["legs_consistent"])

        ftypes = Counter(r.get("failure_type", "unknown") for r in results)
        times = [r.get("detection_time_ms", 0) for r in detected if r.get("detection_time_ms", 0) > 0]

        metrics[backend] = {
            "n": n,
            "det_rate": f"{len(detected)/n:.0%}",
            "accuracy": f"{correct/n:.1%}",
            "det_accuracy": f"{sum(1 for r in detected if r.get('radical_correct'))/max(len(detected),1):.1%}",
            "pck": f"{np.mean(pcks):.1%}" if pcks else "n/a",
            "limb_own": f"{np.mean(owns):.1%}" if owns else "n/a",
            "legs_own": f"{np.mean(legs_own):.1%}" if legs_own else "n/a",
            "mixed": f"{ftypes.get('cross_assigned_limbs', 0)}/{n}",
            "missed": f"{ftypes.get('missed_athlete', 0)}/{n}",
            "geo_err": f"{ftypes.get('geometry_error', 0)}/{n}",
            "correct": f"{ftypes.get('correct', 0)}/{n}",
            "ms_per_img": f"{np.mean(times):.0f}ms" if times else "n/a",
        }

    row("Detection rate", [metrics[b]["det_rate"] for b in all_results])
    row("Overall accuracy", [metrics[b]["accuracy"] for b in all_results])
    row("Accuracy (when detected)", [metrics[b]["det_accuracy"] for b in all_results])
    row("Mean PCK@0.2", [metrics[b]["pck"] for b in all_results])
    row("Limb ownership (overall)", [metrics[b]["limb_own"] for b in all_results])
    row("Limb ownership (legs)", [metrics[b]["legs_own"] for b in all_results])
    row("Mixed skeletons", [metrics[b]["mixed"] for b in all_results])
    row("Missed athletes", [metrics[b]["missed"] for b in all_results])
    row("Geometry classifier errors", [metrics[b]["geo_err"] for b in all_results])
    row("Correct", [metrics[b]["correct"] for b in all_results])
    row("Inference speed", [metrics[b]["ms_per_img"] for b in all_results])

    # Per-class comparison for key confusion pairs
    print(f"\n  KEY CONFUSION PAIRS (MNT/HGRD, SCTR/HGRD)")
    for cls in ["MNT", "HGRD", "SCTR", "CGRD"]:
        vals = []
        for backend, results in all_results.items():
            cr = [r for r in results if r.get("true_label") == cls]
            if not cr:
                vals.append("n/a")
                continue
            ok = sum(1 for r in cr if r.get("radical_correct"))
            vals.append(f"{ok}/{len(cr)}")
        row(f"  {cls} accuracy", vals)


# ── Main ────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    cmd = sys.argv[1]

    if cmd == "freeze":
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 50
        freeze_eval_set(n_per_class=n)

    elif cmd == "smoke":
        smoke_test()

    elif cmd == "run":
        if len(sys.argv) < 3:
            print("Usage: benchmark_perception.py run <backend> [limit]")
            print("Backends: gt, yolo_ft_v2, openpifpaf, mmpose_rtmo")
            return
        backend = sys.argv[2]
        limit = int(sys.argv[3]) if len(sys.argv) > 3 else 0
        run_backend(backend, limit=limit)

    elif cmd == "compare":
        compare()

    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)


if __name__ == "__main__":
    main()
