"""Audit ViCoS pose annotations for fine-tuning readiness."""

import json
import os
import statistics
import sys
from pathlib import Path

DEFAULT_ANN = Path(__file__).resolve().parent.parent / "data" / "raw" / "annotations.json"
DEFAULT_IMG = Path(__file__).resolve().parent.parent / "data" / "raw" / "images"


def audit(ann_path: Path = DEFAULT_ANN, img_dir: Path = DEFAULT_IMG):
    with open(ann_path) as f:
        data = json.load(f)

    total = len(data)
    has_p1 = has_p2 = has_both = p1_only = p2_only = 0
    by_class = {}
    by_class_both = {}
    all_confs = []
    low_vis = 0

    on_disk = set(f.replace(".jpg", "") for f in os.listdir(img_dir) if f.endswith(".jpg"))

    for d in data:
        p1 = "pose1" in d and d["pose1"] and len(d["pose1"]) == 17
        p2 = "pose2" in d and d["pose2"] and len(d["pose2"]) == 17
        pos = d["position"]

        if p1: has_p1 += 1
        if p2: has_p2 += 1
        if p1 and p2: has_both += 1
        if p1 and not p2: p1_only += 1
        if p2 and not p1: p2_only += 1

        by_class[pos] = by_class.get(pos, 0) + 1
        if p1 and p2:
            by_class_both[pos] = by_class_both.get(pos, 0) + 1

        for key in ("pose1", "pose2"):
            if key in d and d[key] and len(d[key]) == 17:
                confs = [kp[2] for kp in d[key]]
                all_confs.extend(confs)
                if sum(1 for c in confs if c < 0.3) > 5:
                    low_vis += 1

    both_on_disk = sum(
        1 for d in data
        if ("pose1" in d and d["pose1"] and len(d["pose1"]) == 17
            and "pose2" in d and d["pose2"] and len(d["pose2"]) == 17
            and d["image"] in on_disk)
    )

    print(f"Total annotations:     {total}")
    print(f"Has pose1:             {has_p1}")
    print(f"Has pose2:             {has_p2}")
    print(f"Has both:              {has_both}")
    print(f"pose1 only:            {p1_only}")
    print(f"pose2 only:            {p2_only}")
    print(f"Images on disk:        {len(on_disk)}")
    print(f"Both poses + on disk:  {both_on_disk}")
    print()

    print("Class distribution (total / both poses):")
    for pos in sorted(by_class.keys()):
        t = by_class[pos]
        b = by_class_both.get(pos, 0)
        pct = b / t * 100 if t else 0
        print(f"  {pos:20s} {t:6d}  both: {b:6d} ({pct:5.1f}%)")
    print()

    print(f"Keypoint confidence:")
    print(f"  Mean:   {statistics.mean(all_confs):.3f}")
    print(f"  Median: {statistics.median(all_confs):.3f}")
    print(f"  Stdev:  {statistics.stdev(all_confs):.3f}")
    print(f"  Low-vis poses (>5 kp < 0.3): {low_vis}")
    print()

    buckets = [(0, 0.1), (0.1, 0.3), (0.3, 0.5), (0.5, 0.7), (0.7, 0.9), (0.9, 1.01)]
    for lo, hi in buckets:
        n = sum(1 for c in all_confs if lo <= c < hi)
        pct = n / len(all_confs) * 100
        print(f"  [{lo:.1f}, {hi:.1f}): {n:>10d} ({pct:5.1f}%)")


if __name__ == "__main__":
    audit()
