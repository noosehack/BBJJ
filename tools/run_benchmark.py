"""Run the geometry classifier on benchmark images and generate a report.

Two modes:
  1. Full pipeline: YOLO detection -> geometry classifier (real-world demo path)
  2. Ground-truth: ViCoS keypoints -> geometry classifier (isolated classification quality)
"""

import json
import os
import random
import sys
import time
from collections import defaultdict, Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

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

TARGET = {"MNT", "SCTR", "BCTR", "CGRD", "OGRD", "HGRD", "TRTL", "STND"}


def load_annotations():
    with open("data/raw/annotations.json") as f:
        return json.load(f)


def select_benchmark(anns, n_per_class=10, seed=42):
    random.seed(seed)
    by_class = defaultdict(list)
    for a in anns:
        pos = a["position"]
        fine = FINE_MAP.get(pos)
        if fine and fine in TARGET:
            by_class[fine].append(a)

    selected = []
    for cls in sorted(by_class.keys()):
        items = by_class[cls]
        random.shuffle(items)
        seen_vids = set()
        picked = []
        for a in items:
            vid = a["image"][:2]
            if len(picked) < n_per_class:
                if vid not in seen_vids or len(picked) < n_per_class:
                    seen_vids.add(vid)
                    picked.append(a)
        selected.extend(picked)
    return selected


def run_ground_truth(benchmark):
    """Classify using ViCoS ground-truth keypoints."""
    print(f"\n{'='*60}")
    print(f"  MODE: Ground-truth keypoints (bypass YOLO)")
    print(f"{'='*60}")

    results = []
    correct = 0

    for a in benchmark:
        pos = a["position"]
        true_label = FINE_MAP[pos]
        img_id = a["image"]

        p1 = a.get("pose1")
        p2 = a.get("pose2")
        if not p1 or len(p1) != 17 or not p2 or len(p2) != 17:
            print(f"  SKIP  {true_label:5s}  {img_id} (missing keypoints)")
            continue

        suffix = pos[-1] if pos[-1] in "12" else "0"
        if suffix == "2":
            me_kps, op_kps = p2, p1
        else:
            me_kps, op_kps = p1, p2

        try:
            result = classify_both_pov(me_kps, op_kps)
            pred = result.radical
            conf = result.confidence
            match = pred == true_label
            if match:
                correct += 1
        except Exception as e:
            pred = "ERROR"
            conf = 0.0
            match = False

        status = "PASS" if match else "FAIL"
        print(f"  {status}  {true_label:5s} -> {pred:5s}  {conf:.1%}  {img_id}")

        results.append({
            "image_id": img_id,
            "true_label": true_label,
            "predicted": pred,
            "confidence": round(conf, 4),
            "correct": match,
            "mode": "ground_truth",
        })

    return results


def run_yolo_pipeline(benchmark):
    """Classify using YOLO-detected keypoints (real demo path)."""
    from tools.infer_image import YoloPoseBackend, select_athletes

    print(f"\n{'='*60}")
    print(f"  MODE: Full pipeline (YOLO -> geometry classifier)")
    print(f"{'='*60}")

    yolo = YoloPoseBackend("models_pose/bjj_v2_posehead/weights/best.pt")
    NMS_IOU = 0.8
    results = []
    correct = 0

    for a in benchmark:
        pos = a["position"]
        true_label = FINE_MAP[pos]
        img_id = a["image"]
        img_path = f"data/raw/images/{img_id}.jpg"

        if not os.path.exists(img_path):
            continue

        try:
            detections = yolo.detect(img_path)
            raw_a, raw_b = select_athletes(detections, nms_iou=NMS_IOU)
            result = classify_both_pov(raw_a, raw_b)
            pred = result.radical
            conf = result.confidence
            match = pred == true_label
            if match:
                correct += 1
        except Exception as e:
            pred = "DETECT_FAIL"
            conf = 0.0
            match = False

        status = "PASS" if match else "FAIL"
        print(f"  {status}  {true_label:5s} -> {pred:5s}  {conf:.1%}  {img_id}")

        results.append({
            "image_id": img_id,
            "true_label": true_label,
            "predicted": pred,
            "confidence": round(conf, 4),
            "correct": match,
            "mode": "yolo_pipeline",
        })

    return results


def print_summary(results, mode_label):
    total = len(results)
    correct = sum(1 for r in results if r["correct"])
    detect_fail = sum(1 for r in results if r["predicted"] == "DETECT_FAIL")

    print(f"\n  {mode_label}: {correct}/{total} = {correct/total:.1%}")
    if detect_fail:
        valid = total - detect_fail
        valid_correct = sum(1 for r in results if r["correct"])
        print(f"  Detection failures: {detect_fail}/{total}")
        print(f"  Accuracy excluding detect failures: {valid_correct}/{valid} = {valid_correct/valid:.1%}" if valid > 0 else "")

    class_correct = Counter()
    class_total = Counter()
    class_confused = defaultdict(lambda: Counter())

    for r in results:
        tl = r["true_label"]
        class_total[tl] += 1
        if r["correct"]:
            class_correct[tl] += 1
        elif r["predicted"] != "DETECT_FAIL":
            class_confused[tl][r["predicted"]] += 1

    print(f"\n  {'Class':>6s} {'N':>4s} {'OK':>4s} {'Acc':>6s} {'DetF':>5s}  Confused with")
    print(f"  {'-'*6} {'-'*4} {'-'*4} {'-'*6} {'-'*5}  {'-'*25}")
    for cls in sorted(TARGET):
        n = class_total[cls]
        c = class_correct[cls]
        df = sum(1 for r in results if r["true_label"] == cls and r["predicted"] == "DETECT_FAIL")
        acc = c / n if n > 0 else 0
        confused = ", ".join(f"{p}({cnt})" for p, cnt in class_confused[cls].most_common(3))
        print(f"  {cls:>6s} {n:>4d} {c:>4d} {acc:>6.0%} {df:>5d}  {confused}")


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    anns = load_annotations()
    benchmark = select_benchmark(anns, n_per_class=n)
    print(f"Benchmark: {len(benchmark)} images, {n}/class, {len(TARGET)} classes")

    gt_results = run_ground_truth(benchmark)
    yolo_results = run_yolo_pipeline(benchmark)

    print(f"\n{'='*60}")
    print(f"  COMPARISON")
    print(f"{'='*60}")
    print_summary(gt_results, "Ground-truth keypoints")
    print_summary(yolo_results, "YOLO pipeline")

    out_dir = Path("demo_benchmark")
    out_dir.mkdir(exist_ok=True)

    all_results = gt_results + yolo_results
    with open(out_dir / "results.json", "w") as f:
        json.dump(all_results, f, indent=2)

    gt_acc = sum(1 for r in gt_results if r["correct"]) / len(gt_results)
    yolo_acc = sum(1 for r in yolo_results if r["correct"]) / len(yolo_results)

    with open(out_dir / "REPORT.md", "w") as f:
        f.write(f"# Benchmark Report\n\n")
        f.write(f"**Date**: {time.strftime('%Y-%m-%d')}\n")
        f.write(f"**Images**: {len(benchmark)} ({n}/class, {len(TARGET)} classes)\n")
        f.write(f"**Classifier**: MLP on body-frame features (learned_geometry)\n\n")
        f.write(f"## Accuracy\n\n")
        f.write(f"| Mode | Accuracy |\n")
        f.write(f"|------|----------|\n")
        f.write(f"| Ground-truth keypoints | **{gt_acc:.1%}** |\n")
        f.write(f"| YOLO pipeline | **{yolo_acc:.1%}** |\n\n")
        f.write(f"Ground-truth mode isolates classifier quality from detection.\n")
        f.write(f"YOLO mode is the actual demo experience.\n")

    print(f"\n  Saved: demo_benchmark/REPORT.md, demo_benchmark/results.json")


if __name__ == "__main__":
    main()
