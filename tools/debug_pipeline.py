"""Diagnose YOLO pose detection failures on entangled positions.

For each image: run YOLO, compare to ground-truth keypoints, classify failure type,
compute keypoint quality metrics, and report downstream classification accuracy.
"""

import json
import math
import os
import random
import sys
import warnings
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
warnings.filterwarnings("ignore")

from tools.infer_image import (
    YoloPoseBackend, _nms_keypoints, _kp_bbox, _bbox_area, _mean_conf, _iou,
    _select_most_distinct_pair,
)
from tools.geometry_classifier import classify_both_pov

FINE_MAP = {
    "mount1": "MNT", "mount2": "MNT",
    "side_control1": "SCTR", "side_control2": "SCTR",
    "back1": "BCTR", "back2": "BCTR",
    "closed_guard1": "CGRD", "closed_guard2": "CGRD",
    "open_guard1": "OGRD", "open_guard2": "OGRD",
    "half_guard1": "HGRD", "half_guard2": "HGRD",
    "turtle1": "TRTL", "turtle2": "TRTL",
    "standing": "STND",
}

TARGET_HARD = {"MNT", "SCTR", "CGRD"}


def load_anns_with_gt():
    with open("data/raw/annotations.json") as f:
        anns = json.load(f)
    valid = []
    for a in anns:
        pos = a["position"]
        fine = FINE_MAP.get(pos)
        if fine not in TARGET_HARD:
            continue
        p1 = a.get("pose1")
        p2 = a.get("pose2")
        if not p1 or len(p1) != 17 or not p2 or len(p2) != 17:
            continue
        img_path = f"data/raw/images/{a['image']}.jpg"
        if not os.path.exists(img_path):
            continue
        valid.append({
            "image": a["image"],
            "position": pos,
            "fine": fine,
            "gt_p1": p1,
            "gt_p2": p2,
            "img_path": img_path,
        })
    return valid


def gt_center(kps):
    pts = [kps[i] for i in [5, 6, 11, 12] if kps[i][2] > 0]
    if len(pts) < 2:
        pts = [k for k in kps if k[2] > 0]
    if not pts:
        return None
    return (np.mean([p[0] for p in pts]), np.mean([p[1] for p in pts]))


def match_detection_to_gt(det, gt_p1, gt_p2):
    det_c = gt_center(det)
    if det_c is None:
        return None, float("inf")
    g1 = gt_center(gt_p1)
    g2 = gt_center(gt_p2)
    d1 = math.dist(det_c, g1) if g1 else float("inf")
    d2 = math.dist(det_c, g2) if g2 else float("inf")
    return (1, d1) if d1 <= d2 else (2, d2)


def keypoint_pck(det_kps, gt_kps, threshold_frac=0.2):
    sh_mid = ((gt_kps[5][0]+gt_kps[6][0])/2, (gt_kps[5][1]+gt_kps[6][1])/2)
    hp_mid = ((gt_kps[11][0]+gt_kps[12][0])/2, (gt_kps[11][1]+gt_kps[12][1])/2)
    torso_len = max(math.dist(sh_mid, hp_mid), 10)
    threshold = threshold_frac * torso_len
    correct = total = 0
    for i in range(17):
        if gt_kps[i][2] > 0:
            total += 1
            d = math.dist((det_kps[i][0], det_kps[i][1]), (gt_kps[i][0], gt_kps[i][1]))
            if d <= threshold:
                correct += 1
    return correct / total if total > 0 else 0, total


def classify_failure(detections_raw, detections_nms, viable, gt_p1, gt_p2, pair_result):
    n_viable = len(viable)

    if n_viable < 2:
        if len(detections_raw) < 2:
            return "missed_athlete"
        elif len(detections_nms) < 2:
            return "merged_after_nms"
        else:
            return "low_conf_filtered"

    if pair_result is None:
        return "pairing_failed"

    det_a, det_b = pair_result
    match_a, _ = match_detection_to_gt(det_a, gt_p1, gt_p2)
    match_b, _ = match_detection_to_gt(det_b, gt_p1, gt_p2)

    if match_a == match_b:
        return "duplicate_ghost"

    gt_for_a = gt_p1 if match_a == 1 else gt_p2
    gt_for_b = gt_p1 if match_b == 1 else gt_p2
    pck_a, _ = keypoint_pck(det_a, gt_for_a)
    pck_b, _ = keypoint_pck(det_b, gt_for_b)

    if pck_a < 0.3 or pck_b < 0.3:
        return "bad_keypoints"

    return "correct_detection"


def analyze_sample(yolo, ann):
    img_path = ann["img_path"]
    gt_p1 = ann["gt_p1"]
    gt_p2 = ann["gt_p2"]

    detections_raw = yolo._extract(yolo._model(img_path, verbose=False))
    if len(detections_raw) < 2:
        detections_raw = yolo._extract(yolo._model(img_path, verbose=False, conf=0.01))

    detections_nms = _nms_keypoints(detections_raw)
    viable = [(i, d) for i, d in enumerate(detections_nms) if _mean_conf(d) > 0.15]

    pair_result = None
    if len(viable) >= 2:
        if len(viable) == 2:
            pair_result = (viable[0][1], viable[1][1])
        else:
            pair_result = _select_most_distinct_pair(viable)

    failure_type = classify_failure(detections_raw, detections_nms, viable, gt_p1, gt_p2, pair_result)

    pck_scores = []
    matched_gt = None
    if pair_result is not None:
        det_a, det_b = pair_result
        match_a, _ = match_detection_to_gt(det_a, gt_p1, gt_p2)
        match_b, _ = match_detection_to_gt(det_b, gt_p1, gt_p2)

        if match_a != match_b and match_a is not None and match_b is not None:
            gt_for_a = gt_p1 if match_a == 1 else gt_p2
            gt_for_b = gt_p1 if match_b == 1 else gt_p2
            pck_a, _ = keypoint_pck(det_a, gt_for_a)
            pck_b, _ = keypoint_pck(det_b, gt_for_b)
            pck_scores = [pck_a, pck_b]
            matched_gt = (match_a, match_b)

    classify_result = None
    if pair_result is not None:
        try:
            result = classify_both_pov(pair_result[0], pair_result[1])
            classify_result = result.radical
        except Exception:
            classify_result = "ERROR"

    return {
        "image": ann["image"],
        "fine": ann["fine"],
        "n_raw": len(detections_raw),
        "n_nms": len(detections_nms),
        "n_viable": len(viable),
        "failure_type": failure_type,
        "pck_scores": pck_scores,
        "matched_gt": matched_gt,
        "predicted": classify_result,
        "correct": classify_result == ann["fine"] if classify_result else False,
    }


def main():
    n_per_class = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    random.seed(42)

    print("Loading annotations...")
    all_anns = load_anns_with_gt()
    print(f"Total with GT keypoints: {len(all_anns)}")

    by_class = defaultdict(list)
    for a in all_anns:
        by_class[a["fine"]].append(a)

    sample = []
    for cls in sorted(TARGET_HARD):
        items = by_class[cls]
        random.shuffle(items)
        sample.extend(items[:n_per_class])

    print(f"Sample: {len(sample)} images ({n_per_class}/class)")
    for cls in sorted(TARGET_HARD):
        print(f"  {cls}: {sum(1 for s in sample if s['fine'] == cls)}")

    print(f"\nLoading YOLO...")
    yolo = YoloPoseBackend("yolo11m-pose.pt")

    print(f"\nAnalyzing...")
    results = []
    for i, ann in enumerate(sample):
        r = analyze_sample(yolo, ann)
        results.append(r)
        if (i + 1) % 10 == 0:
            print(f"  {i+1}/{len(sample)}")

    # ── Failure type breakdown ──
    print(f"\n{'='*60}")
    print(f"  FAILURE TYPE BREAKDOWN")
    print(f"{'='*60}")

    for cls in sorted(TARGET_HARD):
        cls_r = [r for r in results if r["fine"] == cls]
        types = Counter(r["failure_type"] for r in cls_r)
        n = len(cls_r)
        print(f"\n  {cls} ({n} images):")
        for ft, cnt in types.most_common():
            print(f"    {ft:25s}: {cnt:3d} ({cnt/n:.0%})")

    overall_types = Counter(r["failure_type"] for r in results)
    n_all = len(results)
    print(f"\n  ALL ({n_all} images):")
    for ft, cnt in overall_types.most_common():
        print(f"    {ft:25s}: {cnt:3d} ({cnt/n_all:.0%})")

    # ── Detection metrics ──
    print(f"\n{'='*60}")
    print(f"  DETECTION METRICS")
    print(f"{'='*60}")

    for cls in sorted(TARGET_HARD):
        cls_r = [r for r in results if r["fine"] == cls]
        n = len(cls_r)
        two_det = sum(1 for r in cls_r if r["n_viable"] >= 2)
        correct_pair = sum(1 for r in cls_r if r["failure_type"] in ("correct_detection", "bad_keypoints"))
        good_kps = sum(1 for r in cls_r if r["failure_type"] == "correct_detection")
        print(f"\n  {cls}:")
        print(f"    2-athlete detection:  {two_det}/{n} = {two_det/n:.0%}")
        print(f"    Correct pairing:      {correct_pair}/{n} = {correct_pair/n:.0%}")
        print(f"    Good keypoints:       {good_kps}/{n} = {good_kps/n:.0%}")

    # ── Keypoint quality ──
    print(f"\n{'='*60}")
    print(f"  KEYPOINT QUALITY (PCK@0.2)")
    print(f"{'='*60}")

    for cls in sorted(TARGET_HARD):
        cls_r = [r for r in results if r["fine"] == cls and r["pck_scores"]]
        if not cls_r:
            print(f"\n  {cls}: no correctly paired samples")
            continue
        all_pcks = []
        for r in cls_r:
            all_pcks.extend(r["pck_scores"])
        print(f"\n  {cls}: {len(cls_r)} paired samples, {len(all_pcks)} person-level PCK scores")
        print(f"    Mean PCK@0.2: {np.mean(all_pcks):.1%}")
        print(f"    Median:       {np.median(all_pcks):.1%}")
        print(f"    Min:          {np.min(all_pcks):.1%}")
        print(f"    >50%:         {sum(1 for p in all_pcks if p > 0.5)}/{len(all_pcks)}")

    # ── Downstream classification ──
    print(f"\n{'='*60}")
    print(f"  DOWNSTREAM CLASSIFICATION")
    print(f"{'='*60}")

    for cls in sorted(TARGET_HARD):
        cls_r = [r for r in results if r["fine"] == cls]
        n = len(cls_r)
        detected = [r for r in cls_r if r["predicted"] is not None]
        correct = sum(1 for r in detected if r["correct"])
        print(f"\n  {cls}: {correct}/{n} overall ({correct}/{len(detected)} when detected)")
        wrong = Counter(r["predicted"] for r in detected if not r["correct"])
        if wrong:
            print(f"    Confused: {dict(wrong.most_common(5))}")

    # ── Raw counts ──
    print(f"\n{'='*60}")
    print(f"  RAW DETECTION COUNTS")
    print(f"{'='*60}")

    for cls in sorted(TARGET_HARD):
        cls_r = [r for r in results if r["fine"] == cls]
        n_raw_d = Counter(r["n_raw"] for r in cls_r)
        n_nms_d = Counter(r["n_nms"] for r in cls_r)
        n_via_d = Counter(r["n_viable"] for r in cls_r)
        print(f"\n  {cls}:")
        print(f"    Raw:     {dict(sorted(n_raw_d.items()))}")
        print(f"    NMS:     {dict(sorted(n_nms_d.items()))}")
        print(f"    Viable:  {dict(sorted(n_via_d.items()))}")

    out_dir = Path("demo_benchmark")
    out_dir.mkdir(exist_ok=True)
    with open(out_dir / "detection_diagnosis.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved: demo_benchmark/detection_diagnosis.json")


if __name__ == "__main__":
    main()
