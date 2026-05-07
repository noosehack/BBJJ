"""BlawkOps demo API: image upload -> geometry-based radical classification."""

import json
import sys
import uuid
import time
from dataclasses import asdict
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.infer_image import (
    YoloPoseBackend, select_athletes, _nms_keypoints, _mean_conf,
)
from tools.geometry_classifier import classify_both_pov, GeometryResult

DEMO_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = DEMO_DIR / "uploads"
RESULT_DIR = DEMO_DIR / "results"
UPLOAD_DIR.mkdir(exist_ok=True)
RESULT_DIR.mkdir(exist_ok=True)

MAX_UPLOAD_MB = 20
CLEANUP_AGE_SECONDS = 3600

app = FastAPI(title="BlawkOps Demo", docs_url="/api/docs")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

_yolo_ft = None
_yolo_stock = None

_POSE_MODEL_FT = str(DEMO_DIR.parent / "models_pose" / "bjj_v2_posehead" / "weights" / "best.pt")
_POSE_MODEL_STOCK = "yolo11m-pose.pt"
_NMS_IOU = 0.85


def _get_yolo_ft():
    global _yolo_ft
    if _yolo_ft is None:
        _yolo_ft = YoloPoseBackend(_POSE_MODEL_FT)
    return _yolo_ft


def _get_yolo_stock():
    global _yolo_stock
    if _yolo_stock is None:
        _yolo_stock = YoloPoseBackend(_POSE_MODEL_STOCK)
    return _yolo_stock


def _detect_with_fallback(image_path: str):
    """Try fine-tuned model first; fall back to stock YOLO if it fails."""
    yolo_ft = _get_yolo_ft()
    detections = yolo_ft.detect(image_path)
    try:
        raw_a, raw_b = select_athletes(detections, nms_iou=_NMS_IOU)
        return raw_a, raw_b, "fine_tuned"
    except ValueError:
        pass

    yolo_stock = _get_yolo_stock()
    detections = yolo_stock.detect(image_path)
    raw_a, raw_b = select_athletes(detections, nms_iou=_NMS_IOU)
    return raw_a, raw_b, "stock_fallback"


def _cleanup_old_files():
    now = time.time()
    for d in (UPLOAD_DIR, RESULT_DIR):
        for f in d.iterdir():
            if f.is_file() and (now - f.stat().st_mtime) > CLEANUP_AGE_SECONDS:
                f.unlink(missing_ok=True)


def _visualize(kps_a, kps_b, result: GeometryResult, image_path: str, output_dir: str) -> str:
    """Draw skeleton + geometry debug overlay."""
    from PIL import Image, ImageDraw

    COCO_SKELETON = [
        (0, 1), (0, 2), (1, 3), (2, 4),
        (5, 6), (5, 7), (7, 9), (6, 8), (8, 10),
        (5, 11), (6, 12), (11, 12),
        (11, 13), (13, 15), (12, 14), (14, 16),
    ]
    A_COLOR = (124, 110, 240)
    B_COLOR = (248, 113, 113)

    img = Image.open(image_path)
    if img.mode != "RGB":
        img = img.convert("RGB")
    draw = ImageDraw.Draw(img)

    def draw_skeleton(kps, color):
        for i, j in COCO_SKELETON:
            ci, cj = kps[i][2], kps[j][2]
            if ci > 0.3 and cj > 0.3:
                draw.line([(kps[i][0], kps[i][1]), (kps[j][0], kps[j][1])], fill=color, width=3)
            elif ci > 0.15 and cj > 0.15:
                faint = tuple(c // 2 for c in color)
                draw.line([(kps[i][0], kps[i][1]), (kps[j][0], kps[j][1])], fill=faint, width=2)
        for kp in kps:
            if kp[2] > 0.3:
                draw.ellipse([kp[0]-5, kp[1]-5, kp[0]+5, kp[1]+5], fill=color)

    draw_skeleton(kps_a, A_COLOR)
    draw_skeleton(kps_b, B_COLOR)

    def draw_frame(bf, color, label):
        sx, sy = bf.shoulder_mid
        hx, hy = bf.hip_mid
        cx, cy = bf.center
        # Torso axis (thick)
        draw.line([(hx, hy), (sx, sy)], fill=color, width=4)
        # Shoulder axis
        svx, svy = bf.sh_axis
        draw.line([(sx - svx*0.5, sy - svy*0.5), (sx + svx*0.5, sy + svy*0.5)],
                  fill=color, width=2)
        # Hip axis
        hvx, hvy = bf.hp_axis
        draw.line([(hx - hvx*0.5, hy - hvy*0.5), (hx + hvx*0.5, hy + hvy*0.5)],
                  fill=color, width=2)
        # Center
        draw.ellipse([cx-7, cy-7, cx+7, cy+7], fill=color, outline=(255, 255, 255))
        # Facing arrow (yellow)
        fx, fy = bf.facing_dir
        scale = bf.torso_len * 0.4
        arrow_end = (cx + fx*scale, cy + fy*scale)
        draw.line([(cx, cy), arrow_end], fill=(255, 255, 0), width=3)
        # Label
        draw.text((cx + 10, cy - 16), label, fill=(255, 255, 255))

    draw_frame(result.body_frame_a, A_COLOR, "A")
    draw_frame(result.body_frame_b, B_COLOR, "B")

    # Centerline connection
    ca = result.body_frame_a.center
    cb = result.body_frame_b.center
    draw.line([ca, cb], fill=(255, 255, 255, 128), width=1)

    # Orientation label
    orient = result.orientation
    mid = ((ca[0]+cb[0])/2, (ca[1]+cb[1])/2)
    draw.text((mid[0]-30, mid[1]-20), orient.orientation_label, fill=(255, 255, 0))
    if orient.top_label != "level":
        top_txt = "A=top" if orient.top_label == "A_on_top" else "B=top"
        draw.text((mid[0]-20, mid[1]-8), top_txt, fill=(200, 200, 200))

    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    stem = Path(image_path).stem
    save_path = out_path / f"{stem}_{result.radical}.jpg"
    img.save(str(save_path), quality=90)
    return str(save_path)


@app.post("/api/infer")
async def infer_endpoint(image: UploadFile = File(...)):
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(400, "File must be an image (JPEG, PNG, etc.)")

    data = await image.read()
    if len(data) > MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(400, f"Image exceeds {MAX_UPLOAD_MB}MB limit")

    _cleanup_old_files()

    ext = Path(image.filename or "upload.jpg").suffix or ".jpg"
    uid = uuid.uuid4().hex[:12]
    upload_path = UPLOAD_DIR / f"{uid}{ext}"
    upload_path.write_bytes(data)

    # Detect poses (fine-tuned first, stock fallback)
    try:
        raw_a, raw_b, detection_backend = _detect_with_fallback(str(upload_path))
    except ValueError as e:
        raise HTTPException(422, detail={
            "error": "detection_failed",
            "message": str(e),
            "hint": "The image needs two clearly visible athletes.",
        })

    # Pose quality assessment
    conf_a = _mean_conf(raw_a)
    conf_b = _mean_conf(raw_b)
    high_a = sum(1 for x, y, c in raw_a if c > 0.5)
    high_b = sum(1 for x, y, c in raw_b if c > 0.5)
    min_conf = min(conf_a, conf_b)
    min_high = min(high_a, high_b)

    if min_conf >= 0.5 and min_high >= 10:
        pose_quality = "good"
    elif min_conf >= 0.25 and min_high >= 5:
        pose_quality = "uncertain"
    else:
        pose_quality = "poor"

    # Classify with geometry
    result = classify_both_pov(raw_a, raw_b)

    # Determine which kps are me/op based on POV
    if result.pov_label == "B=Me":
        kps_me, kps_op = raw_b, raw_a
    else:
        kps_me, kps_op = raw_a, raw_b

    # Visualize
    overlay_path = _visualize(kps_me, kps_op, result, str(upload_path), str(RESULT_DIR))
    overlay_name = Path(overlay_path).name

    # Top-5 predictions
    sorted_probs = sorted(result.probabilities.items(), key=lambda x: -x[1])
    top5 = [{"radical": r, "confidence": round(p, 4)} for r, p in sorted_probs[:5]]

    return {
        "radical": result.radical,
        "confidence": result.confidence,
        "explanation": result.explanation,
        "classifier_source": result.classifier_source,
        "detection_backend": detection_backend,
        "pov": result.pov_label,
        "pose_quality": pose_quality,
        "pose_detail": {
            "conf_a": round(conf_a, 3),
            "conf_b": round(conf_b, 3),
            "high_conf_kps_a": high_a,
            "high_conf_kps_b": high_b,
        },
        "top_predictions": top5,
        "body_frame_a": asdict(result.body_frame_a),
        "body_frame_b": asdict(result.body_frame_b),
        "orientation": asdict(result.orientation),
        "conditions": [asdict(c) for c in result.conditions],
        "overlay_url": f"/results/{overlay_name}",
    }


app.mount("/results", StaticFiles(directory=str(RESULT_DIR)), name="results")
app.mount("/", StaticFiles(directory=str(DEMO_DIR / "static"), html=True), name="static")
