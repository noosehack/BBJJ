"""Evaluate a pose model on downstream algebra accuracy.

Compares general YOLO vs fine-tuned YOLO by running both through
the full inference pipeline and measuring RAD match rate against
ViCoS ground-truth labels.

Usage:
  python -m tools.eval_pose_model --model models_pose/bjj_v1/weights/best.pt
  python -m tools.eval_pose_model --model yolo11m-pose.pt --baseline
  python -m tools.eval_pose_model --compare yolo11m-pose.pt models_pose/bjj_v1/weights/best.pt
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

from data.schema import Pose
from data.label_map import VICOS_TO_BLISP
from tools.infer_image import (
    YoloPoseBackend, select_athletes, assign_pov,
)

DEFAULT_ANN = Path(__file__).resolve().parent.parent / "data" / "raw" / "annotations.json"
DEFAULT_IMG = Path(__file__).resolve().parent.parent / "data" / "raw" / "images"

HARD_CLASSES = {"mount1", "mount2", "side_control1", "side_control2",
                "back1", "back2", "closed_guard1", "closed_guard2"}

TEST_VIDEOS = ["08", "13", "15"]

BLISP_TO_RADICALS = {
    "MNT":     ["MNT"],
    "BCTR":    ["BCTR"],
    "SCTR":    ["SCTR"],
    "GRD_CLP": ["CGRD"],
    "HGRD":    ["HGRD"],
    "OGRD":    ["DLR", "SLX", "RDLR", "LSSO", "OMOP", "CGRD", "HGRD"],
    "5050":    ["5050"],
    "TRTL":    [],
    "TKDN":    [],
    "STND":    [],
}


def _acceptable_radicals(vicos_position: str) -> set[str]:
    entry = VICOS_TO_BLISP.get(vicos_position)
    if not entry:
        return set()
    blisp = entry["blisp"]
    return set(BLISP_TO_RADICALS.get(blisp, []))


def evaluate_model(
    model_path: str,
    ann_path: Path = DEFAULT_ANN,
    img_dir: Path = DEFAULT_IMG,
    max_per_class: int = 50,
    progress: bool = True,
) -> dict:
    with open(ann_path) as f:
        data = json.load(f)

    test_entries = [d for d in data if d["image"][:2] in TEST_VIDEOS]

    by_class = defaultdict(list)
    for d in test_entries:
        by_class[d["position"]].append(d)

    backend = YoloPoseBackend(model_path)

    results = {
        "model": model_path,
        "total": 0,
        "detected_two": 0,
        "correct_rad": 0,
        "top3_rad": 0,
        "per_class": {},
    }

    for position in sorted(by_class.keys()):
        entries = by_class[position][:max_per_class]
        acceptable = _acceptable_radicals(position)

        cls_stats = {
            "total": len(entries),
            "detected": 0,
            "correct": 0,
            "top3": 0,
            "is_hard": position in HARD_CLASSES,
            "predicted": defaultdict(int),
        }

        for d in entries:
            img_path = img_dir / f"{d['image']}.jpg"
            if not img_path.exists():
                cls_stats["total"] -= 1
                continue

            results["total"] += 1

            try:
                detections = backend.detect(str(img_path))
                raw_a, raw_b = select_athletes(detections)
            except (ValueError, Exception):
                continue

            cls_stats["detected"] += 1
            results["detected_two"] += 1

            try:
                result = assign_pov(raw_a, raw_b, "both", d["image"])
            except Exception:
                continue

            rad = result.best_radical
            cls_stats["predicted"][rad or "NONE"] += 1

            if rad and rad in acceptable:
                cls_stats["correct"] += 1
                results["correct_rad"] += 1

            if result.matches:
                top3 = {m.radical_name for m in result.matches[:3]}
                if top3 & acceptable:
                    cls_stats["top3"] += 1
                    results["top3_rad"] += 1

        results["per_class"][position] = cls_stats

        if progress:
            det_rate = cls_stats["detected"] / cls_stats["total"] * 100 if cls_stats["total"] else 0
            acc = cls_stats["correct"] / cls_stats["detected"] * 100 if cls_stats["detected"] else 0
            hard = " [HARD]" if cls_stats["is_hard"] else ""
            print(
                f"  {position:20s}  det={det_rate:5.1f}%  acc={acc:5.1f}%  "
                f"({cls_stats['correct']}/{cls_stats['detected']}/{cls_stats['total']}){hard}",
                file=sys.stderr,
            )

    return results


def print_summary(results: dict):
    total = results["total"]
    det = results["detected_two"]
    cor = results["correct_rad"]
    t3 = results["top3_rad"]

    print(f"\nModel: {results['model']}")
    print(f"  Total images:      {total}")
    print(f"  Two-person detect: {det} ({det/total*100:.1f}%)" if total else "  No images")
    print(f"  RAD correct:       {cor} ({cor/det*100:.1f}%)" if det else "  No detections")
    print(f"  RAD in top-3:      {t3} ({t3/det*100:.1f}%)" if det else "")

    hard_det = hard_cor = hard_total = 0
    easy_det = easy_cor = easy_total = 0
    for pos, s in results["per_class"].items():
        if s["is_hard"]:
            hard_total += s["total"]
            hard_det += s["detected"]
            hard_cor += s["correct"]
        else:
            easy_total += s["total"]
            easy_det += s["detected"]
            easy_cor += s["correct"]

    print(f"\n  Hard classes (mount/side/back/closed guard):")
    print(f"    Detect: {hard_det}/{hard_total} ({hard_det/hard_total*100:.1f}%)" if hard_total else "")
    print(f"    RAD:    {hard_cor}/{hard_det} ({hard_cor/hard_det*100:.1f}%)" if hard_det else "    RAD:    0/0")
    print(f"  Easy classes (open guard/standing/turtle/etc):")
    print(f"    Detect: {easy_det}/{easy_total} ({easy_det/easy_total*100:.1f}%)" if easy_total else "")
    print(f"    RAD:    {easy_cor}/{easy_det} ({easy_cor/easy_det*100:.1f}%)" if easy_det else "    RAD:    0/0")


def main():
    parser = argparse.ArgumentParser(description="Evaluate pose model on downstream algebra accuracy")
    parser.add_argument("--model", type=str, default="yolo11m-pose.pt",
                        help="Pose model to evaluate")
    parser.add_argument("--compare", nargs=2, metavar=("BASELINE", "FINETUNED"),
                        help="Compare two models side by side")
    parser.add_argument("--max-per-class", type=int, default=50,
                        help="Max images per class to evaluate")
    args = parser.parse_args()

    if args.compare:
        print("=" * 60, file=sys.stderr)
        print(f"Baseline: {args.compare[0]}", file=sys.stderr)
        print("=" * 60, file=sys.stderr)
        r1 = evaluate_model(args.compare[0], max_per_class=args.max_per_class)
        print_summary(r1)

        print("\n" + "=" * 60, file=sys.stderr)
        print(f"Fine-tuned: {args.compare[1]}", file=sys.stderr)
        print("=" * 60, file=sys.stderr)
        r2 = evaluate_model(args.compare[1], max_per_class=args.max_per_class)
        print_summary(r2)

        print("\n" + "=" * 60)
        print("COMPARISON")
        print("=" * 60)
        for pos in sorted(set(r1["per_class"]) | set(r2["per_class"])):
            s1 = r1["per_class"].get(pos, {"detected": 0, "correct": 0, "total": 0, "is_hard": False})
            s2 = r2["per_class"].get(pos, {"detected": 0, "correct": 0, "total": 0, "is_hard": False})
            d1 = s1["detected"] / s1["total"] * 100 if s1["total"] else 0
            d2 = s2["detected"] / s2["total"] * 100 if s2["total"] else 0
            a1 = s1["correct"] / s1["detected"] * 100 if s1["detected"] else 0
            a2 = s2["correct"] / s2["detected"] * 100 if s2["detected"] else 0
            delta_d = d2 - d1
            delta_a = a2 - a1
            hard = " *" if s1.get("is_hard") or s2.get("is_hard") else ""
            print(f"  {pos:20s}  det: {d1:5.1f}→{d2:5.1f} ({delta_d:+.1f})  "
                  f"acc: {a1:5.1f}→{a2:5.1f} ({delta_a:+.1f}){hard}")
    else:
        print(f"Evaluating: {args.model}", file=sys.stderr)
        r = evaluate_model(args.model, max_per_class=args.max_per_class)
        print_summary(r)


if __name__ == "__main__":
    main()
