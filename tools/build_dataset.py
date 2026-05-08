"""Build supervised dataset: COCO keypoints → RAD label.

Pipeline: load annotations → infer contacts → match radicals → persist
→ normalize keypoints + extract symbolic features → split by video → save .npz

Usage:
    python -m tools.build_dataset [--persist N] [--no-pov-aug] [--out DIR]
"""

import argparse
import json
import math
import sys
from collections import Counter
from pathlib import Path

import numpy as np

from data.loader import load_annotations
from data.schema import Annotation, Pose
from data.label_map import normalize, NormalizedAnnotation
from tools.annotate import annotate_one, FPTRecord
from tools.temporal import apply_persistence
from tools.axis_reconstruction import (
    torso_center, torso_length, Vec2,
    L_SHOULDER, R_SHOULDER, L_HIP, R_HIP,
)


DEFAULT_SPLITS = {
    "train": ["00", "01", "03", "04", "06", "07", "09", "11", "12", "14"],
    "val":   ["02", "05", "10"],
    "test":  ["08", "13", "15"],
}


# ── keypoint normalization ──────────────────────────────────────

def normalize_keypoints(me_pose: Pose, op_pose: Pose) -> np.ndarray:
    """Normalize 34 keypoints into Me's body frame.

    Returns (34, 3) float32 array [x, y, confidence].
    Steps: translate by Me torso center, scale by torso length,
    rotate so Me's torso axis points up (0, -1 in image coords).
    """
    center = torso_center(me_pose)
    tl = max(torso_length(me_pose), 1.0)

    kps = me_pose.keypoints
    hip_mid = Vec2(
        (kps[L_HIP].x + kps[R_HIP].x) / 2,
        (kps[L_HIP].y + kps[R_HIP].y) / 2,
    )
    sh_mid = Vec2(
        (kps[L_SHOULDER].x + kps[R_SHOULDER].x) / 2,
        (kps[L_SHOULDER].y + kps[R_SHOULDER].y) / 2,
    )
    dx = sh_mid.x - hip_mid.x
    dy = sh_mid.y - hip_mid.y
    vlen = math.sqrt(dx * dx + dy * dy)

    if vlen < 1e-10:
        cos_a, sin_a = 1.0, 0.0
    else:
        cos_a = -dy / vlen
        sin_a = -dx / vlen

    result = np.zeros((34, 3), dtype=np.float32)
    for i, pose in enumerate([me_pose, op_pose]):
        for j, kp in enumerate(pose.keypoints):
            x = (kp.x - center.x) / tl
            y = (kp.y - center.y) / tl
            result[i * 17 + j] = [
                cos_a * x - sin_a * y,
                sin_a * x + cos_a * y,
                kp.confidence,
            ]

    return result


# ── symbolic feature extraction ─────────────────────────────────

N_SYM_FEATURES = 30

_FRAME_SLOTS = [
    ("FacingOpposed", ""),
    ("FacingAligned", ""),
    ("OnGround", "Op.Ba"),
    ("OnGround", "Me.Ba"),
    ("NotOnGround", "Op.Ba"),
    ("NotOnGround", "Me.Ba"),
]

RADICAL_SCORE_SCALE = 30.0


def extract_symbolic_features(r: FPTRecord, class_names: list[str]) -> np.ndarray:
    """Extract 30-dim symbolic feature vector from an FPTRecord.

    Layout:
      [0:9]   per-radical match scores (normalized by /30)
      [9:17]  frame constraint confidences (8 slots)
      [17:22] contact summary (n/8, max_conf, mean_conf, closure_flag, closure_conf)
      [22:30] top-4 contact (confidence, distance) pairs
    """
    feat = np.zeros(N_SYM_FEATURES, dtype=np.float32)

    match_scores = {m["radical"]: m["confidence"] for m in r.all_matches}
    for i, name in enumerate(class_names):
        feat[i] = match_scores.get(name, 0.0) / RADICAL_SCORE_SCALE

    frame_map: dict[tuple[str, str], float] = {}
    for fc in r.frame_constraints:
        frame_map[(fc["type"], fc.get("part", ""))] = fc["confidence"]
    for i, (ftype, fpart) in enumerate(_FRAME_SLOTS):
        feat[9 + i] = frame_map.get((ftype, fpart), 0.0)

    contacts = r.contacts
    n = len(contacts)
    feat[17] = n / 8.0
    if n > 0:
        confs = [c["confidence"] for c in contacts]
        feat[18] = max(confs)
        feat[19] = sum(confs) / n
    for c in contacts:
        if c["attacker"].startswith("Me.Fo") and c["axis"].startswith("Me.Fo"):
            feat[20] = 1.0
            feat[21] = c["confidence"]
            break

    for i, c in enumerate(contacts[:4]):
        feat[22 + i * 2] = c["confidence"]
        feat[23 + i * 2] = c["distance"]

    return feat


# ── annotation + persistence pipeline ───────────────────────────

def _annotate_and_persist(
    annotations: list[Annotation],
    swap_pov: bool = False,
    persist_n: int = 8,
) -> tuple[list[FPTRecord], dict[str, NormalizedAnnotation]]:
    norms: dict[str, NormalizedAnnotation] = {}
    records: list[FPTRecord] = []
    total = len(annotations)

    tag = "swapped" if swap_pov else "original"
    for i, ann in enumerate(annotations):
        norm = normalize(ann)
        if swap_pov:
            norm = NormalizedAnnotation(
                vicos_position=norm.vicos_position,
                blisp_label=norm.blisp_label,
                ambiguity=norm.ambiguity,
                image=norm.image,
                frame=norm.frame,
                me_pose=norm.op_pose,
                op_pose=norm.me_pose,
            )
        norms[norm.image] = norm
        records.append(annotate_one(norm))
        if (i + 1) % 10000 == 0:
            print(f"  [{tag}] {i+1}/{total} annotated...", file=sys.stderr)

    print(f"  [{tag}] applying persistence (N={persist_n})...", file=sys.stderr)
    records = apply_persistence(records, min_frames=persist_n)
    return records, norms


# ── sample construction ─────────────────────────────────────────

def build_samples(
    records: list[FPTRecord],
    norms: dict[str, NormalizedAnnotation],
    class_to_idx: dict[str, int],
    class_names: list[str],
    is_augmented: bool = False,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[dict]]:
    features = []
    sym_features = []
    labels = []
    meta = []

    for r in records:
        if r.radical_match is None or r.radical_match not in class_to_idx:
            continue

        norm = norms.get(r.image)
        if norm is None or norm.me_pose is None or norm.op_pose is None:
            continue

        kps = normalize_keypoints(norm.me_pose, norm.op_pose)
        features.append(kps.flatten())
        sym_features.append(extract_symbolic_features(r, class_names))
        labels.append(class_to_idx[r.radical_match])
        meta.append({
            "video_id": r.image[:2],
            "frame_id": r.frame,
            "image": r.image,
            "radical": r.radical_match,
            "confidence": r.match_confidence,
            "augmented": is_augmented,
        })

    if not features:
        empty_sym = np.zeros((0, N_SYM_FEATURES), dtype=np.float32)
        return np.zeros((0, 102), dtype=np.float32), np.zeros(0, dtype=np.int64), empty_sym, []

    return (
        np.array(features, dtype=np.float32),
        np.array(labels, dtype=np.int64),
        np.array(sym_features, dtype=np.float32),
        meta,
    )


# ── main ────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Build supervised keypoint → RAD dataset")
    parser.add_argument("--persist", type=int, default=8, help="Persistence filter N (default: 8)")
    parser.add_argument("--no-pov-aug", action="store_true", help="Disable POV-SWAP augmentation")
    parser.add_argument("--out", type=str, default="data/dataset", help="Output directory")
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    from dic.radicals import ALL_RADICALS
    class_names = sorted(ALL_RADICALS.keys())
    class_to_idx = {name: i for i, name in enumerate(class_names)}

    print("Loading annotations...", file=sys.stderr)
    annotations = load_annotations()
    print(f"  {len(annotations)} annotations", file=sys.stderr)

    # Original POV
    print("\nOriginal POV:", file=sys.stderr)
    records, norms = _annotate_and_persist(annotations, swap_pov=False, persist_n=args.persist)
    X_orig, y_orig, S_orig, meta_orig = build_samples(
        records, norms, class_to_idx, class_names, is_augmented=False,
    )
    print(f"  → {len(y_orig)} samples", file=sys.stderr)

    # POV-SWAP augmentation
    if not args.no_pov_aug:
        print("\nSwapped POV:", file=sys.stderr)
        swap_records, swap_norms = _annotate_and_persist(
            annotations, swap_pov=True, persist_n=args.persist,
        )
        X_swap, y_swap, S_swap, meta_swap = build_samples(
            swap_records, swap_norms, class_to_idx, class_names, is_augmented=True,
        )
        print(f"  → {len(y_swap)} samples", file=sys.stderr)

        X_all = np.concatenate([X_orig, X_swap]) if len(X_swap) > 0 else X_orig
        y_all = np.concatenate([y_orig, y_swap]) if len(y_swap) > 0 else y_orig
        S_all = np.concatenate([S_orig, S_swap]) if len(S_swap) > 0 else S_orig
        meta_all = meta_orig + meta_swap
    else:
        X_all, y_all, S_all, meta_all = X_orig, y_orig, S_orig, meta_orig

    # Split by video
    print("\nSplitting by video...", file=sys.stderr)
    splits: dict[str, dict] = {}
    for split_name, vid_ids in DEFAULT_SPLITS.items():
        vid_set = set(vid_ids)
        mask = np.array([m["video_id"] in vid_set for m in meta_all])
        splits[split_name] = {
            "X": X_all[mask],
            "X_sym": S_all[mask],
            "y": y_all[mask],
            "meta": [m for m, keep in zip(meta_all, mask) if keep],
        }

    # Save arrays + metadata
    for split_name, data in splits.items():
        np.savez_compressed(
            out_dir / f"{split_name}.npz",
            X=data["X"], X_sym=data["X_sym"], y=data["y"],
        )
        with open(out_dir / f"{split_name}_meta.json", "w") as f:
            json.dump(data["meta"], f)

    info = {
        "class_names": class_names,
        "class_to_idx": class_to_idx,
        "n_classes": len(class_names),
        "n_features": 102,
        "n_sym_features": N_SYM_FEATURES,
        "feature_layout": "34 keypoints x [x, y, conf]; first 17 = Me, last 17 = Op",
        "sym_feature_layout": (
            "[0:9] per-radical scores/30, "
            "[9:17] frame confs (FacOpp,FacAln,OG_OpBa,OG_MeBa,NOG_OpBa,NOG_MeBa,KBR,NKBR), "
            "[17:22] contact summary (n/8,max_conf,mean_conf,closure_flag,closure_conf), "
            "[22:30] top-4 contact (conf,dist) pairs"
        ),
        "normalization": "translate by Me torso center, scale by torso length, rotate torso vertical",
        "persist_n": args.persist,
        "pov_augmented": not args.no_pov_aug,
        "splits": {},
    }

    # Report
    print("\n" + "=" * 60, file=sys.stderr)
    print("  Dataset Construction Report", file=sys.stderr)
    print("=" * 60, file=sys.stderr)

    for split_name in DEFAULT_SPLITS:
        data = splits[split_name]
        n = len(data["y"])
        aug_count = sum(1 for m in data["meta"] if m.get("augmented"))
        orig_count = n - aug_count
        dist = Counter(data["y"].tolist())

        info["splits"][split_name] = {
            "videos": DEFAULT_SPLITS[split_name],
            "n_samples": n,
            "n_original": orig_count,
            "n_augmented": aug_count,
            "class_counts": {class_names[idx]: int(cnt) for idx, cnt in sorted(dist.items())},
        }

        print(f"\n  {split_name}: {n} samples ({orig_count} orig + {aug_count} aug)", file=sys.stderr)
        print(f"    videos: {DEFAULT_SPLITS[split_name]}", file=sys.stderr)
        print(f"    {'Class':<10} {'Count':>7} {'%':>6}", file=sys.stderr)
        print(f"    {'─' * 10} {'─' * 7} {'─' * 6}", file=sys.stderr)
        for idx in sorted(dist.keys()):
            cnt = dist[idx]
            pct = 100.0 * cnt / n if n > 0 else 0
            print(f"    {class_names[idx]:<10} {cnt:>7} {pct:>5.1f}%", file=sys.stderr)

    total = sum(len(splits[s]["y"]) for s in splits)
    print(f"\n  Total: {total} samples", file=sys.stderr)

    with open(out_dir / "info.json", "w") as f:
        json.dump(info, f, indent=2)

    print(f"\n  Saved to {out_dir}/", file=sys.stderr)


if __name__ == "__main__":
    main()
