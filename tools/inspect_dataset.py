#!/usr/bin/env python3
"""Inspect the ViCoS BJJ dataset: class histogram, pose coverage, image verification."""

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from data.loader import load_annotations, verify_images
from data.label_map import VICOS_TO_BLISP, normalize


def main():
    print("Loading annotations...")
    annotations = load_annotations()
    print(f"Total annotations: {len(annotations)}")
    print(f"Unique images: {len(set(a.image for a in annotations))}")

    # ── ViCoS class histogram ─────────────────────────────────────
    print("\n── ViCoS class histogram ──")
    vicos_counts = Counter(a.position for a in annotations)
    for pos in sorted(vicos_counts):
        print(f"  {pos:20s}  {vicos_counts[pos]:6d}")
    print(f"  {'TOTAL':20s}  {sum(vicos_counts.values()):6d}")
    print(f"  Classes: {len(vicos_counts)}")

    # ── BLISP label histogram ─────────────────────────────────────
    print("\n── BLISP label histogram ──")
    blisp_counts = Counter()
    for a in annotations:
        na = normalize(a)
        blisp_counts[na.blisp_label] += 1
    for label in sorted(blisp_counts):
        print(f"  {label:10s}  {blisp_counts[label]:6d}")

    # ── Pose coverage ─────────────────────────────────────────────
    print("\n── Pose coverage ──")
    has_both = sum(1 for a in annotations if a.pose1 and a.pose2)
    has_pose1 = sum(1 for a in annotations if a.pose1)
    has_pose2 = sum(1 for a in annotations if a.pose2)
    neither = sum(1 for a in annotations if not a.pose1 and not a.pose2)
    print(f"  Both poses:  {has_both:6d}  ({100*has_both/len(annotations):.1f}%)")
    print(f"  Pose1 only:  {has_pose1 - has_both:6d}")
    print(f"  Pose2 only:  {has_pose2 - has_both:6d}")
    print(f"  Neither:     {neither:6d}")

    # ── POV normalization check ───────────────────────────────────
    print("\n── POV normalization ──")
    me_present = sum(1 for a in annotations if normalize(a).me_pose is not None)
    op_present = sum(1 for a in annotations if normalize(a).op_pose is not None)
    both_norm = sum(1 for a in annotations
                    if normalize(a).me_pose is not None and normalize(a).op_pose is not None)
    print(f"  Me pose present: {me_present:6d}  ({100*me_present/len(annotations):.1f}%)")
    print(f"  Op pose present: {op_present:6d}  ({100*op_present/len(annotations):.1f}%)")
    print(f"  Both after norm: {both_norm:6d}  ({100*both_norm/len(annotations):.1f}%)")

    # ── Image file verification ───────────────────────────────────
    print("\n── Image file verification ──")
    found, missing_count, missing_sample = verify_images(annotations)
    print(f"  Found:   {found:6d}")
    print(f"  Missing: {missing_count:6d}")
    if missing_sample:
        print(f"  Sample missing: {missing_sample[:5]}")


if __name__ == "__main__":
    main()
