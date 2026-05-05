"""BlawkOps demo API: image upload -> BLISP algebra."""

import sys
import uuid
import time
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.infer_image import infer_image, format_output, visualize

DEMO_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = DEMO_DIR / "uploads"
RESULT_DIR = DEMO_DIR / "results"
UPLOAD_DIR.mkdir(exist_ok=True)
RESULT_DIR.mkdir(exist_ok=True)

RADICAL_EXPLANATIONS = {
    "MNT": "Mount -- top athlete sits astride the bottom athlete's torso, knees bracketing the hips.",
    "BCTR": "Back Control -- rear athlete has chest-to-back alignment with hooks or seatbelt grip.",
    "SCTR": "Side Control -- top athlete pins across the bottom athlete's torso from the side, arms controlling head and hips.",
    "CGRD": "Closed Guard -- bottom athlete wraps both legs around the top athlete's torso, ankles locked.",
    "HGRD": "Half Guard -- bottom athlete entangles one of the top athlete's legs between both of theirs.",
    "HGRD_L": "Half Guard (left) -- half guard with left leg as primary entangle.",
    "5050": "50/50 Guard -- both athletes mirror-entangle each other's legs in a symmetric cross-leg lock.",
    "DLR": "De La Riva -- bottom athlete hooks one leg behind the opponent's lead leg, foot on the outside of the hip.",
    "SLX": "Single Leg X / Ashi Garami -- bottom athlete controls opponent's leg with an outside hook, same axis as DLR but opposite helicity.",
    "RDLR": "Reverse De La Riva -- bottom athlete hooks one leg behind the opponent's far leg from inside.",
    "LSSO": "Lasso Guard -- bottom athlete wraps their leg around the opponent's arm from outside to inside.",
    "OMOP": "Omoplata setup -- bottom athlete wraps their leg around the opponent's arm with reversed axis orientation.",
}

MAX_UPLOAD_MB = 20
CLEANUP_AGE_SECONDS = 3600

app = FastAPI(title="BlawkOps Demo", docs_url="/api/docs")


def _cleanup_old_files():
    now = time.time()
    for d in (UPLOAD_DIR, RESULT_DIR):
        for f in d.iterdir():
            if f.is_file() and (now - f.stat().st_mtime) > CLEANUP_AGE_SECONDS:
                f.unlink(missing_ok=True)


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

    try:
        result = infer_image(
            image_path=str(upload_path),
            backend="yolo",
            pov_strategy="both",
        )
    except ValueError as e:
        import logging
        logging.warning(f"Detection failed for {upload_path.name}: {e}")
        raise HTTPException(
            422,
            detail={
                "error": "detection_failed",
                "message": str(e),
                "hint": "The image needs two clearly visible athletes. Try a wider shot or a different angle.",
                "upload": upload_path.name,
            },
        )

    overlay_path = visualize(result, str(upload_path), str(RESULT_DIR))
    overlay_name = Path(overlay_path).name

    summary = format_output(result, "summary")
    sexpr = format_output(result, "sexpr")
    json_fpt = format_output(result, "json")

    import json
    fpt_data = json.loads(json_fpt)

    rad = result.best_radical or "NONE"

    return {
        "radical": rad,
        "confidence": round(result.best_confidence, 4),
        "explanation": RADICAL_EXPLANATIONS.get(rad, "No known radical matched."),
        "pov": result.pov_label,
        "contacts": fpt_data.get("contacts", []),
        "frame_constraints": fpt_data.get("frame_constraints", []),
        "all_matches": fpt_data.get("all_matches", []),
        "sexpr": sexpr,
        "summary": summary,
        "overlay_url": f"/results/{overlay_name}",
    }


app.mount("/results", StaticFiles(directory=str(RESULT_DIR)), name="results")
app.mount("/", StaticFiles(directory=str(DEMO_DIR / "static"), html=True), name="static")
