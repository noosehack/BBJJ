"""Image-to-algebra inference: detect poses, extract connections, match radicals."""

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Protocol

from data.schema import Pose, Keypoint
from tools.contact_inference import (
    infer_contacts, infer_frame_constraints, match_radical,
    InferredCON, InferredFrame, PositionMatch,
)
from tools.annotate import FPTRecord, _serialize_con, _serialize_frame
from tools.blisp_export import fpt_to_sexpr
from tools.axis_reconstruction import torso_center, torso_length


# ── result type ──────────────────────────────────────────────────

@dataclass
class InferenceResult:
    image_path: str
    me_pose: Pose
    op_pose: Pose
    pov_label: str
    contacts: list[InferredCON]
    frame_constraints: list[InferredFrame]
    matches: list[PositionMatch]
    best_radical: Optional[str]
    best_confidence: float
    fpt_record: FPTRecord


# ── pose detection backends ──────────────────────────────────────

class PoseBackend(Protocol):
    def detect(self, image_path: str) -> list[list[list[float]]]:
        """Return list of detected persons, each 17 x [x, y, confidence]."""
        ...


class PrecomputedBackend:
    """Load keypoints from a JSON file (ViCoS-compatible format)."""

    def __init__(self, json_path: str):
        self._path = json_path

    def detect(self, image_path: str) -> list[list[list[float]]]:
        with open(self._path) as f:
            data = json.load(f)
        persons = []
        if isinstance(data, dict):
            for key in ("pose1", "pose2"):
                if key in data and data[key]:
                    persons.append(data[key])
        elif isinstance(data, list):
            if data and isinstance(data[0], list) and isinstance(data[0][0], (int, float)):
                persons.append(data)
            elif data and isinstance(data[0], list) and isinstance(data[0][0], list):
                persons = data
            else:
                for item in data:
                    if isinstance(item, dict):
                        for key in ("pose1", "pose2"):
                            if key in item and item[key]:
                                persons.append(item[key])
                        break
        return persons


class YoloPoseBackend:
    """YOLOv8/11 pose detection via ultralytics."""

    def __init__(self, model_name: str = "yolo11m-pose.pt"):
        try:
            from ultralytics import YOLO
        except ImportError:
            raise RuntimeError(
                "YOLO pose detection requires 'ultralytics'. "
                "Install: pip install ultralytics"
            )
        self._model = YOLO(model_name)

    def detect(self, image_path: str) -> list[list[list[float]]]:
        results = self._model(image_path, verbose=False)
        persons = []
        for r in results:
            if r.keypoints is None:
                continue
            for kps in r.keypoints.data:
                person = []
                for kp in kps:
                    x, y, c = float(kp[0]), float(kp[1]), float(kp[2])
                    person.append([x, y, c])
                if len(person) == 17:
                    persons.append(person)
        return persons


def _get_backend(
    name: str,
    keypoints_json: Optional[str] = None,
    model_name: Optional[str] = None,
) -> PoseBackend:
    if name == "precomputed" or (name == "auto" and keypoints_json):
        if not keypoints_json:
            raise ValueError("--keypoints required for precomputed backend")
        return PrecomputedBackend(keypoints_json)
    if name in ("yolo", "auto"):
        if model_name:
            return YoloPoseBackend(model_name)
        return YoloPoseBackend()
    raise ValueError(f"Unknown backend: {name}")


# ── athlete selection ────────────────────────────────────────────

def _bbox_area(kps: list[list[float]], conf_thresh: float = 0.2) -> float:
    visible = [(x, y) for x, y, c in kps if c > conf_thresh]
    if len(visible) < 4:
        return 0.0
    xs = [p[0] for p in visible]
    ys = [p[1] for p in visible]
    return (max(xs) - min(xs)) * (max(ys) - min(ys))


def _mean_conf(kps: list[list[float]]) -> float:
    return sum(c for _, _, c in kps) / len(kps) if kps else 0.0


def select_athletes(
    detections: list[list[list[float]]],
    strategy: str = "largest_pair",
) -> tuple[list[list[float]], list[list[float]]]:
    viable = [(i, d) for i, d in enumerate(detections) if _mean_conf(d) > 0.15]

    if len(viable) < 2:
        n = len(viable)
        raise ValueError(f"Need two athletes detected; found {n}.")

    if strategy == "largest_pair":
        viable.sort(key=lambda t: -_bbox_area(t[1]))
    elif strategy == "closest_pair":
        import itertools
        best_pair = None
        best_dist = float("inf")
        for (i, a), (j, b) in itertools.combinations(viable, 2):
            pa = Pose.from_raw(a)
            pb = Pose.from_raw(b)
            d = (torso_center(pa) - torso_center(pb)).length()
            if d < best_dist:
                best_dist = d
                best_pair = (a, b)
        return best_pair

    if len(viable) > 2:
        print(
            f"Warning: {len(viable)} people detected, selecting two largest.",
            file=sys.stderr,
        )

    return viable[0][1], viable[1][1]


# ── POV assignment ───────────────────────────────────────────────

def _run_inference(me_pose: Pose, op_pose: Pose, label: str) -> InferenceResult:
    contacts = infer_contacts(me_pose, op_pose)
    frames = infer_frame_constraints(me_pose, op_pose)
    matches = match_radical(contacts, frames)

    best_name = matches[0].radical_name if matches else None
    best_conf = matches[0].confidence if matches else 0.0

    fpt = FPTRecord(
        image=label,
        frame=0,
        vicos_label="",
        blisp_label="",
        ambiguity="inferred",
        radical_match=best_name,
        match_confidence=round(best_conf, 4),
        contacts=[_serialize_con(c) for c in contacts[:8]],
        frame_constraints=[_serialize_frame(f) for f in frames],
        all_matches=[
            {"radical": m.radical_name, "confidence": round(m.confidence, 4)}
            for m in matches[:5]
        ],
    )

    return InferenceResult(
        image_path=label,
        me_pose=me_pose,
        op_pose=op_pose,
        pov_label="",
        contacts=contacts,
        frame_constraints=frames,
        matches=matches,
        best_radical=best_name,
        best_confidence=best_conf,
        fpt_record=fpt,
    )


def assign_pov(
    raw_a: list[list[float]],
    raw_b: list[list[float]],
    strategy: str,
    label: str,
) -> InferenceResult:
    pose_a = Pose.from_raw(raw_a)
    pose_b = Pose.from_raw(raw_b)

    if strategy == "both":
        r_ab = _run_inference(pose_a, pose_b, label)
        r_ab.pov_label = "A=Me"
        r_ba = _run_inference(pose_b, pose_a, label)
        r_ba.pov_label = "B=Me"
        return r_ab if r_ab.best_confidence >= r_ba.best_confidence else r_ba

    if strategy == "top_is_me":
        ca = torso_center(pose_a)
        cb = torso_center(pose_b)
        if ca.y <= cb.y:
            r = _run_inference(pose_a, pose_b, label)
            r.pov_label = "A=Me (top)"
        else:
            r = _run_inference(pose_b, pose_a, label)
            r.pov_label = "B=Me (top)"
        return r

    if strategy == "left_is_me":
        ca = torso_center(pose_a)
        cb = torso_center(pose_b)
        if ca.x <= cb.x:
            r = _run_inference(pose_a, pose_b, label)
            r.pov_label = "A=Me (left)"
        else:
            r = _run_inference(pose_b, pose_a, label)
            r.pov_label = "B=Me (left)"
        return r

    raise ValueError(f"Unknown POV strategy: {strategy}")


# ── top-level orchestrator ───────────────────────────────────────

def infer_image(
    image_path: str,
    backend: str = "auto",
    keypoints_json: Optional[str] = None,
    model_name: Optional[str] = None,
    athlete_strategy: str = "largest_pair",
    pov_strategy: str = "both",
) -> InferenceResult:
    detector = _get_backend(backend, keypoints_json, model_name)
    detections = detector.detect(image_path)
    raw_a, raw_b = select_athletes(detections, athlete_strategy)
    label = Path(image_path).stem
    return assign_pov(raw_a, raw_b, pov_strategy, label)


# ── output formatting ────────────────────────────────────────────

def format_summary(result: InferenceResult) -> str:
    lines = []
    lines.append(f"RAD  {result.best_radical or 'NONE'}")
    lines.append(f"CONF {result.best_confidence:.4f}")
    lines.append(f"POV  {result.pov_label}")
    lines.append("")

    lines.append("FRM:")
    for f in result.fpt_record.frame_constraints:
        t = f["type"]
        c = f["confidence"]
        part = f.get("part", "")
        lines.append(f"  ({t} {part} {c})".rstrip())
    lines.append("")

    lines.append("CON:")
    for c in result.fpt_record.contacts:
        att = c["attacker"]
        ax = c["axis"]
        hel = c["helicity"]
        conf = c["confidence"]
        lines.append(f"  (CON {att} {ax} {conf} {hel})")
    lines.append("")

    if result.fpt_record.all_matches:
        lines.append("ALL:")
        for m in result.fpt_record.all_matches:
            lines.append(f"  {m['radical']:6s} {m['confidence']:.4f}")

    return "\n".join(lines)


def format_output(result: InferenceResult, fmt: str) -> str:
    if fmt == "summary":
        return format_summary(result)
    if fmt == "sexpr":
        return fpt_to_sexpr(result.fpt_record)
    if fmt == "json":
        from dataclasses import asdict
        return json.dumps(asdict(result.fpt_record), indent=2)
    raise ValueError(f"Unknown format: {fmt}")


# ── visualization ────────────────────────────────────────────────

def visualize(result: InferenceResult, image_path: str, output_dir: str) -> str:
    from PIL import Image, ImageDraw

    COCO_SKELETON = [
        (0, 1), (0, 2), (1, 3), (2, 4),
        (5, 6), (5, 7), (7, 9), (6, 8), (8, 10),
        (5, 11), (6, 12), (11, 12),
        (11, 13), (13, 15), (12, 14), (14, 16),
    ]
    ME_COLOR = (124, 110, 240)
    OP_COLOR = (248, 113, 113)

    def draw_pose(draw, pose, color, joint_r=5):
        kps = pose.keypoints
        for i, j in COCO_SKELETON:
            if kps[i].confidence > 0.3 and kps[j].confidence > 0.3:
                draw.line(
                    [(kps[i].x, kps[i].y), (kps[j].x, kps[j].y)],
                    fill=color, width=3,
                )
        for kp in kps:
            if kp.confidence > 0.3:
                draw.ellipse(
                    [kp.x - joint_r, kp.y - joint_r, kp.x + joint_r, kp.y + joint_r],
                    fill=color,
                )

    img = Image.open(image_path)
    draw = ImageDraw.Draw(img)
    draw_pose(draw, result.me_pose, ME_COLOR)
    draw_pose(draw, result.op_pose, OP_COLOR)

    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    stem = Path(image_path).stem
    rad = result.best_radical or "NONE"
    save_path = out_path / f"{stem}_{rad}.jpg"
    img.save(str(save_path), quality=90)
    return str(save_path)


# ── CLI ──────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Infer BLISP position from a BJJ image",
    )
    parser.add_argument("image", help="Path to input image")
    parser.add_argument(
        "--keypoints", type=str, default=None,
        help="JSON file with pre-extracted keypoints (enables precomputed backend)",
    )
    parser.add_argument(
        "--backend", choices=["yolo", "precomputed", "auto"], default="auto",
        help="Pose detection backend (default: auto)",
    )
    parser.add_argument(
        "--model", type=str, default=None,
        help="YOLO model file (default: yolo11m-pose.pt). Options: yolo11n-pose.pt, yolo11s-pose.pt, yolo11m-pose.pt, yolo11l-pose.pt",
    )
    parser.add_argument(
        "--athlete-strategy", choices=["largest_pair", "closest_pair"],
        default="largest_pair",
        help="How to select two athletes from detections (default: largest_pair)",
    )
    parser.add_argument(
        "--pov", choices=["both", "top_is_me", "left_is_me"], default="both",
        help="POV assignment strategy (default: both, picks higher confidence)",
    )
    parser.add_argument(
        "--format", choices=["summary", "sexpr", "json"], default="summary",
        dest="output_format",
        help="Output format (default: summary)",
    )
    parser.add_argument(
        "--visualize", action="store_true",
        help="Save visualization with keypoints and detected radical",
    )
    parser.add_argument(
        "--save-fpt", type=str, default=None,
        help="Save FPT record as JSON to this path",
    )
    parser.add_argument(
        "-o", "--output", type=str, default=None,
        help="Output file (default: stdout)",
    )

    args = parser.parse_args()

    result = infer_image(
        image_path=args.image,
        backend=args.backend,
        keypoints_json=args.keypoints,
        model_name=args.model,
        athlete_strategy=args.athlete_strategy,
        pov_strategy=args.pov,
    )

    text = format_output(result, args.output_format)

    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, "w") as f:
            f.write(text)
    else:
        print(text)

    if args.save_fpt:
        from tools.annotate import export_fpt
        export_fpt([result.fpt_record], Path(args.save_fpt))
        print(f"FPT saved to {args.save_fpt}", file=sys.stderr)

    if args.visualize:
        viz_path = visualize(result, args.image, "outputs/visualizations")
        print(f"Visualization saved to {viz_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
