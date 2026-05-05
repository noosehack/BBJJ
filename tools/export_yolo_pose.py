"""Export ViCoS annotations to YOLO pose training format.

YOLO pose label format (one line per person, all values normalized to [0,1]):
  class cx cy w h kp0_x kp0_y kp0_v kp1_x kp1_y kp1_v ... kp16_x kp16_y kp16_v

Visibility: 0=not labeled, 1=labeled but occluded, 2=labeled and visible
We map: conf < 0.1 -> 0, conf < 0.5 -> 1, conf >= 0.5 -> 2
"""

import json
import os
import shutil
import sys
from pathlib import Path
from PIL import Image

DEFAULT_ANN = Path(__file__).resolve().parent.parent / "data" / "raw" / "annotations.json"
DEFAULT_IMG = Path(__file__).resolve().parent.parent / "data" / "raw" / "images"
DEFAULT_OUT = Path(__file__).resolve().parent.parent / "data" / "yolo_pose"

SPLITS = {
    "train": ["00", "01", "03", "04", "06", "09", "11", "14"],
    "val":   ["02", "05", "07", "10", "12"],
}

DEFAULT_STRIDE = 5


def _conf_to_vis(conf: float) -> int:
    if conf < 0.1:
        return 0
    if conf < 0.5:
        return 1
    return 2


def _bbox_from_keypoints(kps, img_w, img_h):
    """Compute normalized bounding box from visible keypoints."""
    visible = [(x, y) for x, y, c in kps if c > 0.1]
    if len(visible) < 3:
        return None
    xs = [p[0] for p in visible]
    ys = [p[1] for p in visible]
    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)

    pad_x = (x_max - x_min) * 0.05
    pad_y = (y_max - y_min) * 0.05
    x_min = max(0, x_min - pad_x)
    y_min = max(0, y_min - pad_y)
    x_max = min(img_w, x_max + pad_x)
    y_max = min(img_h, y_max + pad_y)

    cx = (x_min + x_max) / 2 / img_w
    cy = (y_min + y_max) / 2 / img_h
    w = (x_max - x_min) / img_w
    h = (y_max - y_min) / img_h
    return cx, cy, w, h


def _format_person(kps, img_w, img_h):
    bbox = _bbox_from_keypoints(kps, img_w, img_h)
    if bbox is None:
        return None
    cx, cy, w, h = bbox

    parts = [f"0 {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}"]
    for x, y, c in kps:
        nx = max(0.0, min(1.0, x / img_w))
        ny = max(0.0, min(1.0, y / img_h))
        vis = _conf_to_vis(c)
        parts.append(f"{nx:.6f} {ny:.6f} {vis}")
    return " ".join(parts)


def export(
    ann_path: Path = DEFAULT_ANN,
    img_dir: Path = DEFAULT_IMG,
    out_dir: Path = DEFAULT_OUT,
    require_both: bool = True,
    stride: int = DEFAULT_STRIDE,
    progress: bool = True,
):
    with open(ann_path) as f:
        data = json.load(f)

    out_dir = Path(out_dir)
    for split in SPLITS:
        (out_dir / split / "images").mkdir(parents=True, exist_ok=True)
        (out_dir / split / "labels").mkdir(parents=True, exist_ok=True)

    vid_to_split = {}
    for split, vids in SPLITS.items():
        for v in vids:
            vid_to_split[v] = split

    stats = {"train": 0, "val": 0, "skipped_no_both": 0, "skipped_no_image": 0,
             "skipped_bad_kp": 0, "skipped_stride": 0}
    total = len(data)
    vid_frame_count = {}

    for i, d in enumerate(data):
        img_id = d["image"]
        vid_id = img_id[:2]
        split = vid_to_split.get(vid_id)
        if split is None:
            continue

        seq = vid_frame_count.get(vid_id, 0)
        vid_frame_count[vid_id] = seq + 1
        if stride > 1 and seq % stride != 0:
            stats["skipped_stride"] += 1
            continue

        p1 = d.get("pose1")
        p2 = d.get("pose2")
        p1_ok = p1 and len(p1) == 17
        p2_ok = p2 and len(p2) == 17

        if require_both and not (p1_ok and p2_ok):
            stats["skipped_no_both"] += 1
            continue

        src_img = img_dir / f"{img_id}.jpg"
        if not src_img.exists():
            stats["skipped_no_image"] += 1
            continue

        img = Image.open(src_img)
        img_w, img_h = img.size

        lines = []
        for kps in (p1, p2):
            if kps and len(kps) == 17:
                line = _format_person(kps, img_w, img_h)
                if line:
                    lines.append(line)

        if len(lines) < 2 and require_both:
            stats["skipped_bad_kp"] += 1
            continue

        if not lines:
            stats["skipped_bad_kp"] += 1
            continue

        dst_img = out_dir / split / "images" / f"{img_id}.jpg"
        dst_lbl = out_dir / split / "labels" / f"{img_id}.txt"

        if not dst_img.exists():
            os.symlink(src_img.resolve(), dst_img)

        with open(dst_lbl, "w") as f:
            f.write("\n".join(lines) + "\n")

        stats[split] += 1

        if progress and (i + 1) % 10000 == 0:
            print(f"  {i+1}/{total}...", file=sys.stderr)

    yaml_path = out_dir / "dataset.yaml"
    yaml_content = f"""path: {out_dir.resolve()}
train: train/images
val: val/images

kpt_shape: [17, 3]
flip_idx: [0, 2, 1, 4, 3, 6, 5, 8, 7, 10, 9, 12, 11, 14, 13, 16, 15]

names:
  0: person
"""
    with open(yaml_path, "w") as f:
        f.write(yaml_content)

    print(f"Export complete:", file=sys.stderr)
    print(f"  Train: {stats['train']}", file=sys.stderr)
    print(f"  Val:   {stats['val']}", file=sys.stderr)
    print(f"  Skipped (stride {stride}):    {stats['skipped_stride']}", file=sys.stderr)
    print(f"  Skipped (no both poses): {stats['skipped_no_both']}", file=sys.stderr)
    print(f"  Skipped (no image):      {stats['skipped_no_image']}", file=sys.stderr)
    print(f"  Skipped (bad keypoints): {stats['skipped_bad_kp']}", file=sys.stderr)
    print(f"  Dataset YAML: {yaml_path}", file=sys.stderr)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Export ViCoS to YOLO pose format")
    parser.add_argument("--out", type=str, default=str(DEFAULT_OUT))
    parser.add_argument("--single-pose", action="store_true",
                        help="Include images with only one pose annotation")
    parser.add_argument("--stride", type=int, default=DEFAULT_STRIDE,
                        help=f"Take every Nth frame per video (default {DEFAULT_STRIDE}, 1=all)")
    args = parser.parse_args()
    export(out_dir=Path(args.out), require_both=not args.single_pose, stride=args.stride)
