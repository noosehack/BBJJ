"""Diagnostic: dump raw keypoint tensors from YOLO before any filtering."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

COCO_NAMES = [
    "nose", "left_eye", "right_eye", "left_ear", "right_ear",
    "left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
    "left_wrist", "right_wrist", "left_hip", "right_hip",
    "left_knee", "right_knee", "left_ankle", "right_ankle",
]

LOWER_BODY = {"left_hip", "right_hip", "left_knee", "right_knee", "left_ankle", "right_ankle"}


def dump_raw(image_path: str, model_path: str, conf_thresholds=(0.25, 0.10, 0.01, 0.001)):
    from ultralytics import YOLO
    model = YOLO(model_path)

    print(f"=== RAW KEYPOINT DIAGNOSTIC: {image_path} ===\n")

    for conf_thresh in conf_thresholds:
        print(f"\n{'='*60}")
        print(f"  DETECTION CONF THRESHOLD: {conf_thresh}")
        print(f"{'='*60}")

        results = model(image_path, verbose=False, conf=conf_thresh)

        person_idx = 0
        for r in results:
            if r.keypoints is None:
                print("  No keypoints in result")
                continue

            if r.boxes is not None:
                for bi, box in enumerate(r.boxes):
                    bc = float(box.conf[0]) if box.conf is not None else 0.0
                    coords = box.xyxy[0].tolist() if box.xyxy is not None else []
                    print(f"\n  Box {bi}: conf={bc:.4f} coords={[round(c,1) for c in coords]}")

            for ki, kps in enumerate(r.keypoints.data):
                person_idx += 1
                box_conf = float(r.boxes.conf[ki]) if r.boxes is not None and ki < len(r.boxes.conf) else 0.0
                print(f"\n  Person {person_idx} (box_conf={box_conf:.4f}):")
                print(f"  {'Joint':<18} {'X':>8} {'Y':>8} {'Conf':>8}  {'Status'}")
                print(f"  {'-'*18} {'-'*8} {'-'*8} {'-'*8}  {'-'*12}")

                lower_body_stats = []
                for ji, kp in enumerate(kps):
                    x, y, c = float(kp[0]), float(kp[1]), float(kp[2])
                    name = COCO_NAMES[ji] if ji < len(COCO_NAMES) else f"kp_{ji}"

                    if c > 0.5:
                        status = "GOOD"
                    elif c > 0.3:
                        status = "weak"
                    elif c > 0.1:
                        status = "very_weak"
                    elif c > 0.01:
                        status = "NEAR_ZERO"
                    else:
                        status = "DEAD"

                    marker = " <<<" if name in LOWER_BODY else ""
                    print(f"  {name:<18} {x:>8.1f} {y:>8.1f} {c:>8.4f}  {status}{marker}")

                    if name in LOWER_BODY:
                        lower_body_stats.append((name, x, y, c))

                print(f"\n  Lower-body summary for person {person_idx}:")
                for name, x, y, c in lower_body_stats:
                    print(f"    {name}: conf={c:.4f} at ({x:.0f}, {y:.0f})")

        if person_idx == 0:
            print("  NO PERSONS DETECTED at this threshold")


def dump_resolution_comparison(image_path: str, model_path: str, sizes=(640, 960, 1280)):
    from ultralytics import YOLO
    model = YOLO(model_path)

    print(f"\n\n{'='*60}")
    print(f"  RESOLUTION COMPARISON")
    print(f"{'='*60}")

    for sz in sizes:
        print(f"\n--- imgsz={sz} ---")
        results = model(image_path, verbose=False, conf=0.01, imgsz=sz)

        for r in results:
            if r.keypoints is None:
                print(f"  No keypoints at {sz}")
                continue
            for ki, kps in enumerate(r.keypoints.data):
                box_conf = float(r.boxes.conf[ki]) if r.boxes is not None and ki < len(r.boxes.conf) else 0.0
                lower = []
                for ji, kp in enumerate(kps):
                    name = COCO_NAMES[ji]
                    x, y, c = float(kp[0]), float(kp[1]), float(kp[2])
                    if name in LOWER_BODY:
                        lower.append((name, c))
                print(f"  Person {ki+1} (box={box_conf:.3f}): " +
                      " | ".join(f"{n}={c:.3f}" for n, c in lower))


def save_debug_json(image_path: str, model_path: str, output_path: str):
    from ultralytics import YOLO
    model = YOLO(model_path)
    results = model(image_path, verbose=False, conf=0.01)

    debug_data = {"image": image_path, "persons": []}
    for r in results:
        if r.keypoints is None:
            continue
        for ki, kps in enumerate(r.keypoints.data):
            box_conf = float(r.boxes.conf[ki]) if r.boxes is not None and ki < len(r.boxes.conf) else 0.0
            person = {"box_conf": round(box_conf, 4), "keypoints": {}}
            for ji, kp in enumerate(kps):
                name = COCO_NAMES[ji]
                x, y, c = float(kp[0]), float(kp[1]), float(kp[2])
                person["keypoints"][name] = {"x": round(x, 1), "y": round(y, 1), "conf": round(c, 4)}
            debug_data["persons"].append(person)

    with open(output_path, "w") as f:
        json.dump(debug_data, f, indent=2)
    print(f"\nDebug JSON saved to {output_path}")


def render_debug_overlay(image_path: str, model_path: str, output_path: str):
    """Render ALL joints including low-confidence ones with visual distinction."""
    from ultralytics import YOLO
    from PIL import Image, ImageDraw, ImageFont

    model = YOLO(model_path)
    results = model(image_path, verbose=False, conf=0.01)

    COCO_SKELETON = [
        (0, 1), (0, 2), (1, 3), (2, 4),
        (5, 6), (5, 7), (7, 9), (6, 8), (8, 10),
        (5, 11), (6, 12), (11, 12),
        (11, 13), (13, 15), (12, 14), (14, 16),
    ]
    COLORS = [
        (124, 110, 240),  # purple - person 1
        (248, 113, 113),  # red - person 2
        (52, 211, 153),   # green - person 3
        (251, 191, 36),   # yellow - person 4
    ]

    img = Image.open(image_path).convert("RGB")
    draw = ImageDraw.Draw(img)

    for r in results:
        if r.keypoints is None:
            continue
        for ki, kps in enumerate(r.keypoints.data):
            color = COLORS[ki % len(COLORS)]
            box_conf = float(r.boxes.conf[ki]) if r.boxes is not None and ki < len(r.boxes.conf) else 0.0

            points = []
            for ji, kp in enumerate(kps):
                x, y, c = float(kp[0]), float(kp[1]), float(kp[2])
                points.append((x, y, c))

            # Draw skeleton lines
            for i, j in COCO_SKELETON:
                xi, yi, ci = points[i]
                xj, yj, cj = points[j]
                min_c = min(ci, cj)
                if min_c > 0.3:
                    draw.line([(xi, yi), (xj, yj)], fill=color, width=3)
                elif min_c > 0.1:
                    # dashed effect: draw shorter segments
                    faint = tuple(c // 2 for c in color)
                    draw.line([(xi, yi), (xj, yj)], fill=faint, width=2)
                elif min_c > 0.01:
                    faint = tuple(c // 3 for c in color)
                    draw.line([(xi, yi), (xj, yj)], fill=faint, width=1)

            # Draw joints
            for ji, (x, y, c) in enumerate(points):
                name = COCO_NAMES[ji]
                is_lower = name in LOWER_BODY

                if c > 0.5:
                    r_size = 6
                    fill = color
                elif c > 0.3:
                    r_size = 5
                    fill = color
                elif c > 0.1:
                    r_size = 5
                    fill = tuple(c // 2 for c in color)
                elif c > 0.01:
                    r_size = 4
                    fill = (255, 255, 0) if is_lower else tuple(c // 3 for c in color)
                else:
                    continue

                draw.ellipse([x - r_size, y - r_size, x + r_size, y + r_size], fill=fill)

                # Label low-conf lower-body joints
                if is_lower and c < 0.3:
                    label = f"{name.split('_')[1][:2]} {c:.2f}"
                    draw.text((x + r_size + 2, y - 6), label, fill=(255, 255, 0))

            # Label person
            if points:
                nose_x, nose_y, _ = points[0]
                draw.text((nose_x - 20, nose_y - 20),
                          f"P{ki+1} box={box_conf:.2f}", fill=color)

    img.save(output_path, quality=95)
    print(f"Debug overlay saved to {output_path}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("image")
    parser.add_argument("--model", default=None)
    parser.add_argument("--save-json", default=None)
    parser.add_argument("--save-overlay", default=None)
    parser.add_argument("--resolution-test", action="store_true")
    args = parser.parse_args()

    model = args.model or str(
        Path(__file__).resolve().parent.parent / "models_pose" / "bjj_v2_posehead" / "weights" / "best.pt"
    )

    dump_raw(args.image, model)

    if args.resolution_test:
        dump_resolution_comparison(args.image, model)

    if args.save_json:
        save_debug_json(args.image, model, args.save_json)

    if args.save_overlay:
        render_debug_overlay(args.image, model, args.save_overlay)
