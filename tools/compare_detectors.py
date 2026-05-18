"""Compare pose detection models on the fixed 90-image entangled benchmark.

Same diagnostic pipeline, same images, different YOLO model weights.
Reports: detection rate, failure types, PCK, downstream accuracy, runtime.
"""

import json
import math
import os
import random
import sys
import time
import warnings
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
warnings.filterwarnings("ignore")

from tools.infer_image import (
    YoloPoseBackend, _nms_keypoints, _mean_conf, _select_most_distinct_pair,
)
from tools.geometry_classifier import classify_both_pov

FINE_MAP = {
    "mount1": "MNT", "mount2": "MNT",
    "side_control1": "SCTR", "side_control2": "SCTR",
    "closed_guard1": "CGRD", "closed_guard2": "CGRD",
}

TARGET = {"MNT", "SCTR", "CGRD"}


def load_benchmark(n_per_class=30, seed=42):
    random.seed(seed)
    with open("data/raw/annotations.json") as f:
        anns = json.load(f)

    by_class = defaultdict(list)
    for a in anns:
        pos = a["position"]
        fine = FINE_MAP.get(pos)
        if fine not in TARGET:
            continue
        p1, p2 = a.get("pose1"), a.get("pose2")
        if not p1 or len(p1) != 17 or not p2 or len(p2) != 17:
            continue
        img_path = f"data/raw/images/{a['image']}.jpg"
        if not os.path.exists(img_path):
            continue
        by_class[fine].append({
            "image": a["image"], "position": pos, "fine": fine,
            "gt_p1": p1, "gt_p2": p2, "img_path": img_path,
        })

    sample = []
    for cls in sorted(TARGET):
        items = by_class[cls]
        random.shuffle(items)
        sample.extend(items[:n_per_class])
    return sample


def gt_center(kps):
    pts = [kps[i] for i in [5, 6, 11, 12] if kps[i][2] > 0]
    if len(pts) < 2:
        pts = [k for k in kps if k[2] > 0]
    if not pts:
        return None
    return (np.mean([p[0] for p in pts]), np.mean([p[1] for p in pts]))


def match_det_to_gt(det, gt_p1, gt_p2):
    dc = gt_center(det)
    if dc is None:
        return None, float("inf")
    g1, g2 = gt_center(gt_p1), gt_center(gt_p2)
    d1 = math.dist(dc, g1) if g1 else float("inf")
    d2 = math.dist(dc, g2) if g2 else float("inf")
    return (1, d1) if d1 <= d2 else (2, d2)


def pck(det_kps, gt_kps, thr=0.2):
    sh = ((gt_kps[5][0]+gt_kps[6][0])/2, (gt_kps[5][1]+gt_kps[6][1])/2)
    hp = ((gt_kps[11][0]+gt_kps[12][0])/2, (gt_kps[11][1]+gt_kps[12][1])/2)
    tl = max(math.dist(sh, hp), 10)
    threshold = thr * tl
    ok = total = 0
    for i in range(17):
        if gt_kps[i][2] > 0:
            total += 1
            if math.dist((det_kps[i][0], det_kps[i][1]), (gt_kps[i][0], gt_kps[i][1])) <= threshold:
                ok += 1
    return ok / total if total > 0 else 0


def classify_failure(dets_raw, dets_nms, viable, gt_p1, gt_p2, pair):
    if len(viable) < 2:
        if len(dets_raw) < 2:
            return "missed_athlete"
        elif len(dets_nms) < 2:
            return "merged_nms"
        else:
            return "low_conf"
    if pair is None:
        return "pair_fail"
    m_a, _ = match_det_to_gt(pair[0], gt_p1, gt_p2)
    m_b, _ = match_det_to_gt(pair[1], gt_p1, gt_p2)
    if m_a == m_b:
        return "dup_ghost"
    gt_a = gt_p1 if m_a == 1 else gt_p2
    gt_b = gt_p1 if m_b == 1 else gt_p2
    if pck(pair[0], gt_a) < 0.3 or pck(pair[1], gt_b) < 0.3:
        return "bad_kps"
    return "ok"


def run_model(model_path, benchmark, label, nms_iou=0.5, conf_min=0.15):
    print(f"\n{'='*60}")
    print(f"  MODEL: {label}")
    print(f"  Path:  {model_path}")
    print(f"  NMS IoU: {nms_iou}  Conf min: {conf_min}")
    print(f"{'='*60}")

    yolo = YoloPoseBackend(model_path)
    results = []
    t0 = time.time()

    for ann in benchmark:
        img = ann["img_path"]
        gt1, gt2 = ann["gt_p1"], ann["gt_p2"]

        dets_raw = yolo._extract(yolo._model(img, verbose=False))
        if len(dets_raw) < 2:
            dets_raw = yolo._extract(yolo._model(img, verbose=False, conf=0.01))

        dets_nms = _nms_keypoints(dets_raw, iou_thresh=nms_iou)
        viable = [(i, d) for i, d in enumerate(dets_nms) if _mean_conf(d) > conf_min]

        pair = None
        if len(viable) >= 2:
            if len(viable) == 2:
                pair = (viable[0][1], viable[1][1])
            else:
                pair = _select_most_distinct_pair(viable)

        ftype = classify_failure(dets_raw, dets_nms, viable, gt1, gt2, pair)

        pck_vals = []
        if pair and ftype in ("ok", "bad_kps"):
            ma, _ = match_det_to_gt(pair[0], gt1, gt2)
            mb, _ = match_det_to_gt(pair[1], gt1, gt2)
            ga = gt1 if ma == 1 else gt2
            gb = gt1 if mb == 1 else gt2
            pck_vals = [pck(pair[0], ga), pck(pair[1], gb)]

        pred = None
        if pair:
            try:
                r = classify_both_pov(pair[0], pair[1])
                pred = r.radical
            except Exception:
                pred = "ERROR"

        results.append({
            "image": ann["image"], "fine": ann["fine"],
            "n_raw": len(dets_raw), "n_viable": len(viable),
            "ftype": ftype, "pck": pck_vals,
            "pred": pred, "correct": pred == ann["fine"] if pred else False,
        })

    elapsed = time.time() - t0
    n = len(results)

    # ── Report ──
    print(f"\n  Runtime: {elapsed:.1f}s ({elapsed/n:.2f}s/image)")

    # Failure types
    ftypes = Counter(r["ftype"] for r in results)
    print(f"\n  Failure types:")
    for ft, cnt in ftypes.most_common():
        print(f"    {ft:20s}: {cnt:3d} ({cnt/n:.0%})")

    # Per-class metrics
    print(f"\n  Per-class:")
    print(f"  {'':>5s} {'det2':>5s} {'pair':>5s} {'okKP':>5s} {'PCK':>6s} {'rad':>5s}")
    totals = {"det2": 0, "pair": 0, "ok": 0, "rad_ok": 0, "pck_sum": 0, "pck_n": 0}
    for cls in sorted(TARGET):
        cr = [r for r in results if r["fine"] == cls]
        nc = len(cr)
        det2 = sum(1 for r in cr if r["n_viable"] >= 2)
        pair_ok = sum(1 for r in cr if r["ftype"] in ("ok", "bad_kps"))
        kp_ok = sum(1 for r in cr if r["ftype"] == "ok")
        pcks = [p for r in cr for p in r["pck"]]
        mean_pck = np.mean(pcks) if pcks else 0
        rad_ok = sum(1 for r in cr if r["correct"])
        print(f"  {cls:>5s} {det2:>3d}/{nc:<2d} {pair_ok:>3d}/{nc:<2d} {kp_ok:>3d}/{nc:<2d} {mean_pck:>5.1%} {rad_ok:>3d}/{nc:<2d}")
        totals["det2"] += det2
        totals["pair"] += pair_ok
        totals["ok"] += kp_ok
        totals["rad_ok"] += rad_ok
        totals["pck_sum"] += sum(pcks)
        totals["pck_n"] += len(pcks)

    all_pck = totals["pck_sum"] / totals["pck_n"] if totals["pck_n"] else 0
    print(f"  {'ALL':>5s} {totals['det2']:>3d}/{n:<2d} {totals['pair']:>3d}/{n:<2d} {totals['ok']:>3d}/{n:<2d} {all_pck:>5.1%} {totals['rad_ok']:>3d}/{n:<2d}")

    # Downstream confusion
    detected = [r for r in results if r["pred"] is not None]
    print(f"\n  Downstream radical accuracy: {totals['rad_ok']}/{n} = {totals['rad_ok']/n:.0%} overall, "
          f"{totals['rad_ok']}/{len(detected)} = {totals['rad_ok']/max(len(detected),1):.0%} when detected")

    for cls in sorted(TARGET):
        cr = [r for r in results if r["fine"] == cls and r["pred"] is not None and not r["correct"]]
        if cr:
            confused = Counter(r["pred"] for r in cr)
            print(f"    {cls} confused: {dict(confused.most_common(4))}")

    return {
        "label": label,
        "runtime": elapsed,
        "n": n,
        "ftypes": dict(ftypes),
        "det2_rate": totals["det2"] / n,
        "pair_rate": totals["pair"] / n,
        "ok_kp_rate": totals["ok"] / n,
        "mean_pck": all_pck,
        "radical_acc": totals["rad_ok"] / n,
        "radical_acc_detected": totals["rad_ok"] / max(len(detected), 1),
    }


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    benchmark = load_benchmark(n)
    print(f"Benchmark: {len(benchmark)} images ({n}/class)")
    for cls in sorted(TARGET):
        print(f"  {cls}: {sum(1 for b in benchmark if b['fine'] == cls)}")

    configs = [
        ("yolo11m-pose.pt", "stock-11m", 0.5, 0.15),
        ("models_pose/bjj_v2_posehead/weights/best.pt", "ft-v2 nms=0.5", 0.5, 0.15),
        ("models_pose/bjj_v2_posehead/weights/best.pt", "ft-v2 nms=0.7", 0.7, 0.15),
        ("models_pose/bjj_v2_posehead/weights/best.pt", "ft-v2 nms=0.8", 0.8, 0.15),
        ("models_pose/bjj_v2_posehead/weights/best.pt", "ft-v2 nms=0.9", 0.9, 0.15),
    ]

    configs = [(p, l, n, c) for p, l, n, c in configs if os.path.exists(p)]
    print(f"\nConfigs to compare: {[l for _, l, _, _ in configs]}")

    all_results = {}
    for path, label, nms_iou, conf_min in configs:
        all_results[label] = run_model(path, benchmark, label, nms_iou=nms_iou, conf_min=conf_min)

    # ── Decision table ──
    print(f"\n\n{'='*70}")
    print(f"  DECISION TABLE")
    print(f"{'='*70}")
    print(f"  {'Model':<22s} {'Det2':>6s} {'Pair':>6s} {'GoodKP':>7s} {'PCK':>6s} {'RadAcc':>7s} {'DetAcc':>7s} {'Time':>6s}")
    print(f"  {'-'*22} {'-'*6} {'-'*6} {'-'*7} {'-'*6} {'-'*7} {'-'*7} {'-'*6}")
    for label in [l for _, l, _, _ in configs]:
        r = all_results[label]
        print(f"  {label:<22s} {r['det2_rate']:>5.0%} {r['pair_rate']:>5.0%} {r['ok_kp_rate']:>6.0%} "
              f"{r['mean_pck']:>5.1%} {r['radical_acc']:>6.0%} {r['radical_acc_detected']:>6.0%} {r['runtime']:>5.0f}s")

    print(f"\n  Oracle (GT keypoints): 94.1% radical accuracy")
    print(f"  Target: >=70% radical accuracy on this benchmark")

    out = Path("demo_benchmark")
    out.mkdir(exist_ok=True)
    with open(out / "model_comparison.json", "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\n  Saved: demo_benchmark/model_comparison.json")


if __name__ == "__main__":
    main()
