"""Demo test runner: YOLO ft-v2 → geo+ordered_cr_cw → predicted position.

Runs the full pipeline on arbitrary images:
  1. YOLO fine-tuned pose detection (two athletes)
  2. geo + ordered_cr_cw feature extraction (635 features)
  3. MLP classification → position + confidence + top-3

Output per image:
  - Annotated image (skeletons, boxes, prediction, top-3, confidence)
  - JSON with full feature dump and supporting constraints

Usage:
    python3 -m tools.demo_test image.jpg
    python3 -m tools.demo_test folder/
    python3 -m tools.demo_test image.jpg --gt-label MNT
"""

import argparse
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.pose_classifier_v2 import BodyFrame, extract_all_features
from tools.cross_ratio_features import extract_geo_confidence_weighted
from tools.ordered_cross_ratio import (
    extract_ordered_cr_features, confidence_weight_ordered_cr,
    CONSTRAINTS, FEATURES_PER_CONSTRAINT,
)

import joblib

# ── Model loading ────────────────────────────────────────────────

MODEL_DIR = Path(__file__).resolve().parent.parent / "models_geometry"
YOLO_MODEL = Path(__file__).resolve().parent.parent / "models" / "best.pt"

_model = None
_scaler = None
_feature_names = None
_label_encoder = None
_yolo = None


def _load_model():
    global _model, _scaler, _feature_names, _label_encoder
    if _model is not None:
        return
    _model = joblib.load(MODEL_DIR / "model.joblib")
    _scaler = joblib.load(MODEL_DIR / "scaler.joblib")
    _feature_names = joblib.load(MODEL_DIR / "feature_names.joblib")
    _label_encoder = joblib.load(MODEL_DIR / "label_encoder.joblib")


def _load_yolo(model_path=None):
    global _yolo
    if _yolo is not None:
        return
    from ultralytics import YOLO
    path = model_path or str(YOLO_MODEL)
    _yolo = YOLO(path)


# ── YOLO detection ───────────────────────────────────────────────

def _detect_poses(image_path):
    results = _yolo(str(image_path), verbose=False)
    persons = _extract_persons(results)
    if len(persons) >= 2:
        return persons
    persons = _extract_persons(_yolo(str(image_path), verbose=False, conf=0.01))
    return persons


def _extract_persons(results):
    persons = []
    for r in results:
        if r.keypoints is None:
            continue
        boxes = r.boxes.xyxy.cpu().numpy() if r.boxes is not None else None
        for idx, kps in enumerate(r.keypoints.data):
            person_kps = []
            for kp in kps:
                person_kps.append([float(kp[0]), float(kp[1]), float(kp[2])])
            if len(person_kps) == 17:
                box = boxes[idx].tolist() if boxes is not None and idx < len(boxes) else None
                persons.append({"kps": person_kps, "box": box})
    return persons


def _kp_bbox(kps, thresh=0.2):
    vis = [(x, y) for x, y, c in kps if c > thresh]
    if len(vis) < 4:
        return None
    xs, ys = zip(*vis)
    return [min(xs), min(ys), max(xs), max(ys)]


def _iou(a, b):
    x1 = max(a[0], b[0]); y1 = max(a[1], b[1])
    x2 = min(a[2], b[2]); y2 = min(a[3], b[3])
    inter = max(0, x2 - x1) * max(0, y2 - y1)
    area_a = (a[2] - a[0]) * (a[3] - a[1])
    area_b = (b[2] - b[0]) * (b[3] - b[1])
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0


def _select_athletes(persons):
    if len(persons) < 2:
        return None, None, f"only {len(persons)} athlete(s) detected"

    # NMS by keypoint bbox
    scored = []
    for p in persons:
        bbox = p.get("box") or _kp_bbox(p["kps"])
        if bbox is None:
            continue
        mc = sum(c for _, _, c in p["kps"]) / 17
        scored.append((mc, bbox, p))
    scored.sort(key=lambda t: -t[0])

    keep = []
    for mc, bbox, p in scored:
        if not any(_iou(bbox, kb) > 0.85 for _, kb, _ in keep):
            keep.append((mc, bbox, p))

    if len(keep) < 2:
        return None, None, f"only {len(keep)} distinct athlete(s) after NMS"

    # Pick most distinct pair
    import itertools
    best_pair, best_score = None, -1
    for (_, ba, pa), (_, bb, pb) in itertools.combinations(keep, 2):
        overlap = _iou(ba, bb)
        area_min = min(
            (ba[2] - ba[0]) * (ba[3] - ba[1]),
            (bb[2] - bb[0]) * (bb[3] - bb[1]),
        )
        score = area_min * (1 - overlap)
        if score > best_score:
            best_score = score
            best_pair = (pa, pb)

    return best_pair[0], best_pair[1], None


# ── Feature extraction + classification ──────────────────────────

def _extract_features(kps_a, kps_b):
    geo, geo_n = extract_all_features(kps_a, kps_b)
    ocr, ocr_n = extract_ordered_cr_features(kps_a, kps_b)
    gcw, gcw_n = extract_geo_confidence_weighted(geo, geo_n, kps_a, kps_b)
    ocrw, ocrw_n = confidence_weight_ordered_cr(ocr, ocr_n)
    return gcw + ocrw, gcw_n + ocrw_n, ocr, ocr_n


def _classify(features):
    arr = np.array([features], dtype=np.float32)
    scaled = np.nan_to_num(_scaler.transform(arr), 0)
    proba = _model.predict_proba(scaled)[0]
    classes = list(_label_encoder.classes_)
    ranked = sorted(zip(classes, proba), key=lambda x: -x[1])
    return ranked


def _top_constraints(ocr_features, ocr_names, predicted_class, n=5):
    """Find the ordered constraints most informative for the predicted class.

    Heuristic: constraints with highest absolute feature magnitude
    (confidence-weighted order signs and bracket predicates),
    filtered to those with decent confidence.
    """
    block = FEATURES_PER_CONSTRAINT + 1  # 16 per constraint
    results = []

    for ci, (c_name, axis, *_) in enumerate(CONSTRAINTS):
        base = ci * block
        if base + block > len(ocr_features):
            break

        chunk = ocr_features[base:base + block]
        minconf = chunk[-1]
        if minconf < 0.2:
            continue

        order_signs = chunk[0:6]
        logcr = chunk[6]
        drat = chunk[7:9]
        laterals = chunk[9:13]
        brackets = chunk[13:15]

        order_strength = sum(abs(s) for s in order_signs)
        bracket_strength = sum(abs(b) for b in brackets)
        signal = (order_strength + bracket_strength) * minconf

        results.append({
            "constraint": c_name,
            "axis": axis,
            "confidence": round(minconf, 3),
            "order_signs": [int(s) for s in order_signs],
            "log_cr": round(logcr, 3),
            "brackets": [round(b, 2) for b in brackets],
            "signal_strength": round(signal, 3),
        })

    results.sort(key=lambda r: -r["signal_strength"])
    return results[:n]


# ── Run on single image ─────────────────────────────────────────

@dataclass
class DemoResult:
    image_path: str
    success: bool
    error: str
    predicted_class: str
    confidence: float
    top3: list
    pov_label: str
    athlete_a: dict
    athlete_b: dict
    top_constraints: list
    all_probabilities: dict
    gt_label: str
    correct: bool


def run_image(image_path, gt_label=None):
    path = Path(image_path)
    persons = _detect_poses(path)
    pa, pb, err = _select_athletes(persons)

    if err:
        return DemoResult(
            image_path=str(path), success=False, error=err,
            predicted_class="", confidence=0, top3=[], pov_label="",
            athlete_a={}, athlete_b={}, top_constraints=[],
            all_probabilities={}, gt_label=gt_label or "", correct=False,
        )

    kps_a, kps_b = pa["kps"], pb["kps"]

    # Try both POV assignments
    feats_ab, names_ab, ocr_ab, ocr_n_ab = _extract_features(kps_a, kps_b)
    feats_ba, names_ba, ocr_ba, ocr_n_ba = _extract_features(kps_b, kps_a)

    ranked_ab = _classify(feats_ab)
    ranked_ba = _classify(feats_ba)

    if ranked_ab[0][1] >= ranked_ba[0][1]:
        ranked, ocr, ocr_n = ranked_ab, ocr_ab, ocr_n_ab
        pov = "A=Me"
        me_kps, op_kps = kps_a, kps_b
        me_box, op_box = pa.get("box"), pb.get("box")
    else:
        ranked, ocr, ocr_n = ranked_ba, ocr_ba, ocr_n_ba
        pov = "B=Me"
        me_kps, op_kps = kps_b, kps_a
        me_box, op_box = pb.get("box"), pa.get("box")

    pred = ranked[0][0]
    conf = ranked[0][1]
    top3 = [(c, round(p, 4)) for c, p in ranked[:3]]
    all_proba = {c: round(p, 4) for c, p in ranked}
    top_c = _top_constraints(ocr, ocr_n, pred)

    me_conf = sum(c for _, _, c in me_kps) / 17
    op_conf = sum(c for _, _, c in op_kps) / 17

    is_correct = (pred == gt_label) if gt_label else None

    return DemoResult(
        image_path=str(path),
        success=True,
        error="",
        predicted_class=pred,
        confidence=round(conf, 4),
        top3=top3,
        pov_label=pov,
        athlete_a={
            "role": "Me" if pov == "A=Me" else "Op",
            "keypoints": me_kps if pov == "A=Me" else op_kps,
            "mean_conf": round(me_conf if pov == "A=Me" else op_conf, 3),
            "box": me_box if pov == "A=Me" else op_box,
        },
        athlete_b={
            "role": "Op" if pov == "A=Me" else "Me",
            "keypoints": op_kps if pov == "A=Me" else me_kps,
            "mean_conf": round(op_conf if pov == "A=Me" else me_conf, 3),
            "box": op_box if pov == "A=Me" else me_box,
        },
        top_constraints=top_c,
        all_probabilities=all_proba,
        gt_label=gt_label or "",
        correct=is_correct if is_correct is not None else False,
    )


# ── Visualization ────────────────────────────────────────────────

COCO_SKELETON = [
    (0, 1), (0, 2), (1, 3), (2, 4),
    (5, 6), (5, 7), (7, 9), (6, 8), (8, 10),
    (5, 11), (6, 12), (11, 12),
    (11, 13), (13, 15), (12, 14), (14, 16),
]

ME_COLOR = (100, 180, 255)
OP_COLOR = (255, 100, 100)
BG_COLOR = (30, 30, 30, 200)

POSITION_DESCRIPTIONS = {
    "MNT": "Mount",
    "BCTR": "Back Control",
    "SCTR": "Side Control",
    "CGRD": "Closed Guard",
    "OGRD": "Open Guard",
    "HGRD": "Half Guard",
    "TRTL": "Turtle",
    "STND": "Standing",
    "5050": "50/50 Guard",
    "TKDN": "Takedown",
}


def _load_font(size):
    try:
        return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size)
    except Exception:
        return ImageFont.load_default()


def draw_skeleton(draw, kps, color, joint_r=4):
    for i, j in COCO_SKELETON:
        ci, cj = kps[i][2], kps[j][2]
        if ci > 0.3 and cj > 0.3:
            draw.line(
                [(kps[i][0], kps[i][1]), (kps[j][0], kps[j][1])],
                fill=color, width=3,
            )
        elif ci > 0.15 and cj > 0.15:
            faint = tuple(c // 2 for c in color)
            draw.line(
                [(kps[i][0], kps[i][1]), (kps[j][0], kps[j][1])],
                fill=faint, width=2,
            )
    for x, y, c in kps:
        if c > 0.3:
            draw.ellipse([x - joint_r, y - joint_r, x + joint_r, y + joint_r], fill=color)
        elif c > 0.15:
            draw.ellipse([x - joint_r, y - joint_r, x + joint_r, y + joint_r],
                         fill=tuple(c // 2 for c in color))


def draw_box(draw, box, color, label=None, font=None):
    if box is None:
        return
    draw.rectangle(box, outline=color, width=2)
    if label and font:
        draw.text((box[0] + 4, box[1] + 2), label, fill=color, font=font)


def annotate_image(result, output_path):
    img = Image.open(result.image_path)
    if img.mode != "RGB":
        img = img.convert("RGB")
    W, H = img.size

    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw_overlay = ImageDraw.Draw(overlay)
    draw = ImageDraw.Draw(img)

    font_lg = _load_font(max(20, H // 25))
    font_md = _load_font(max(14, H // 35))
    font_sm = _load_font(max(11, H // 45))

    if not result.success:
        draw.text((10, 10), f"ERROR: {result.error}", fill=(255, 50, 50), font=font_lg)
        img.save(str(output_path), quality=95)
        return

    # Skeletons
    me_kps = result.athlete_a["keypoints"] if result.athlete_a["role"] == "Me" else result.athlete_b["keypoints"]
    op_kps = result.athlete_b["keypoints"] if result.athlete_b["role"] == "Op" else result.athlete_a["keypoints"]
    draw_skeleton(draw, me_kps, ME_COLOR)
    draw_skeleton(draw, op_kps, OP_COLOR)

    # Boxes
    me_box = result.athlete_a.get("box") if result.athlete_a["role"] == "Me" else result.athlete_b.get("box")
    op_box = result.athlete_b.get("box") if result.athlete_b["role"] == "Op" else result.athlete_a.get("box")
    draw_box(draw, me_box, ME_COLOR, "Me", font_sm)
    draw_box(draw, op_box, OP_COLOR, "Op", font_sm)

    # Info panel (top-left)
    panel_lines = []
    desc = POSITION_DESCRIPTIONS.get(result.predicted_class, result.predicted_class)
    panel_lines.append(f"{result.predicted_class} — {desc}")
    panel_lines.append(f"Confidence: {result.confidence:.1%}")
    panel_lines.append("")
    panel_lines.append("Top 3:")
    for cls, prob in result.top3:
        bar = "█" * int(prob * 20)
        panel_lines.append(f"  {cls:5s} {prob:5.1%} {bar}")

    if result.gt_label:
        panel_lines.append("")
        if result.correct:
            panel_lines.append(f"GT: {result.gt_label} ✓")
        else:
            panel_lines.append(f"GT: {result.gt_label} ✗ WRONG")

    # Panel background
    line_h = max(16, H // 35)
    panel_h = len(panel_lines) * line_h + 20
    panel_w = max(280, W // 3)
    draw_overlay.rectangle([0, 0, panel_w, panel_h], fill=BG_COLOR)

    # Panel text
    img_rgba = img.convert("RGBA")
    img_rgba = Image.alpha_composite(img_rgba, overlay)
    draw_final = ImageDraw.Draw(img_rgba)

    y = 10
    for i, line in enumerate(panel_lines):
        f = font_lg if i == 0 else font_md
        color = (255, 255, 255)
        if result.gt_label and i == len(panel_lines) - 1:
            color = (100, 255, 100) if result.correct else (255, 80, 80)
        draw_final.text((10, y), line, fill=color, font=f)
        y += line_h

    # Constraint panel (bottom-left)
    if result.top_constraints:
        c_lines = ["Supporting constraints:"]
        for tc in result.top_constraints[:4]:
            signs = "".join("+" if s > 0 else ("-" if s < 0 else "0") for s in tc["order_signs"])
            c_lines.append(f"  {tc['constraint'][:30]:30s} [{signs}] c={tc['confidence']:.2f}")

        c_panel_h = len(c_lines) * line_h + 16
        c_y_start = H - c_panel_h - 5
        draw_overlay2 = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(draw_overlay2).rectangle(
            [0, c_y_start, panel_w + 60, H], fill=BG_COLOR)
        img_rgba = Image.alpha_composite(img_rgba, draw_overlay2)
        draw_final = ImageDraw.Draw(img_rgba)

        y = c_y_start + 8
        for line in c_lines:
            draw_final.text((10, y), line, fill=(200, 200, 200), font=font_sm)
            y += line_h

    img_final = img_rgba.convert("RGB")
    img_final.save(str(output_path), quality=95)


# ── JSON output ──────────────────────────────────────────────────

def _jsonable(obj):
    if isinstance(obj, (np.floating, np.float32, np.float64)):
        return float(obj)
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    raise TypeError(f"Not JSON serializable: {type(obj)}")


def save_json(result, output_path):
    if result.success and result.athlete_a:
        me = result.athlete_a if result.athlete_a.get("role") == "Me" else result.athlete_b
        op = result.athlete_b if result.athlete_b.get("role") == "Op" else result.athlete_a
        athletes = {
            "me": {"mean_keypoint_conf": me["mean_conf"], "box": me.get("box")},
            "op": {"mean_keypoint_conf": op["mean_conf"], "box": op.get("box")},
        }
    else:
        athletes = {}

    data = {
        "image": result.image_path,
        "success": result.success,
        "error": result.error,
        "predicted_class": result.predicted_class,
        "confidence": result.confidence,
        "top3": [{"class": c, "probability": p} for c, p in result.top3],
        "pov": result.pov_label,
        "gt_label": result.gt_label,
        "correct": result.correct if result.gt_label else None,
        "athletes": athletes,
        "all_probabilities": result.all_probabilities,
        "top_constraints": result.top_constraints,
    }
    with open(str(output_path), "w") as f:
        json.dump(data, f, indent=2, default=_jsonable)


# ── Batch summary ────────────────────────────────────────────────

def print_summary(results):
    total = len(results)
    ok = sum(1 for r in results if r.success)
    failed = total - ok

    print(f"\n{'='*60}")
    print(f"  DEMO TEST SUMMARY: {ok}/{total} images processed")
    print(f"{'='*60}")

    if failed:
        print(f"\n  Failed ({failed}):")
        for r in results:
            if not r.success:
                print(f"    {Path(r.image_path).name}: {r.error}")

    print(f"\n  Predictions:")
    for r in results:
        if not r.success:
            continue
        gt_mark = ""
        if r.gt_label:
            gt_mark = " ✓" if r.correct else f" ✗ (GT={r.gt_label})"
        print(f"    {Path(r.image_path).name:40s} → {r.predicted_class:5s} {r.confidence:5.1%}{gt_mark}")

    gt_results = [r for r in results if r.success and r.gt_label]
    if gt_results:
        correct = sum(1 for r in gt_results if r.correct)
        print(f"\n  Accuracy (GT-labeled): {correct}/{len(gt_results)} = {correct/len(gt_results):.1%}")


# ── CLI ──────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Demo test: YOLO ft-v2 → geo+ordered_cr_cw → position",
    )
    parser.add_argument("input", help="Image path or folder")
    parser.add_argument("--gt-label", type=str, default=None,
                        help="Ground truth label (for single image)")
    parser.add_argument("--gt-map", type=str, default=None,
                        help="JSON file mapping image filename → GT label")
    parser.add_argument("--yolo-model", type=str, default=None,
                        help="Override YOLO model path")
    parser.add_argument("-o", "--output-dir", type=str, default="demo_output",
                        help="Output directory (default: demo_output)")
    parser.add_argument("--no-annotate", action="store_true",
                        help="Skip annotated image generation")
    args = parser.parse_args()

    _load_model()
    _load_yolo(args.yolo_model)

    gt_map = {}
    if args.gt_map:
        with open(args.gt_map) as f:
            gt_map = json.load(f)

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    input_path = Path(args.input)
    if input_path.is_dir():
        images = sorted(
            p for p in input_path.iterdir()
            if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
        )
    else:
        images = [input_path]

    results = []
    for img_path in images:
        gt = args.gt_label or gt_map.get(img_path.name)
        print(f"  {img_path.name}...", end=" ", flush=True)
        result = run_image(str(img_path), gt_label=gt)
        results.append(result)

        if result.success:
            print(f"→ {result.predicted_class} ({result.confidence:.1%})")
        else:
            print(f"→ FAIL: {result.error}")

        stem = img_path.stem
        if not args.no_annotate:
            annotate_image(result, out_dir / f"{stem}_annotated.jpg")
        save_json(result, out_dir / f"{stem}.json")

    print_summary(results)


if __name__ == "__main__":
    main()
