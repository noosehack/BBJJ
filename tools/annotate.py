"""Batch annotation pipeline: run contact inference on the ViCoS dataset."""

from dataclasses import dataclass, field, asdict
from typing import Optional
import json
import sys
from pathlib import Path

from data.schema import Annotation, Pose
from data.label_map import normalize, NormalizedAnnotation
from tools.contact_inference import (
    infer_contacts, infer_frame_constraints, match_radical,
    InferredCON, InferredFrame, PositionMatch,
)


@dataclass
class FPTRecord:
    image: str
    frame: int
    vicos_label: str
    blisp_label: str
    ambiguity: str
    radical_match: Optional[str]
    match_confidence: float
    contacts: list[dict] = field(default_factory=list)
    frame_constraints: list[dict] = field(default_factory=list)
    all_matches: list[dict] = field(default_factory=list)


def _serialize_con(ic: InferredCON) -> dict:
    c = ic.con
    return {
        "attacker": f"{c.attacker.limb_ref.role}.{c.attacker.limb_ref.part}{c.attacker.limb_ref.sign}",
        "attacker_axis": f"{c.attacker.from_pt}->{c.attacker.to_pt}",
        "axis": f"{c.axis.limb_ref.role}.{c.axis.limb_ref.part}{c.axis.limb_ref.sign}",
        "axis_orient": f"{c.axis.from_pt}->{c.axis.to_pt}",
        "depth": c.depth,
        "helicity": c.helicity,
        "confidence": round(ic.confidence, 4),
        "distance": round(ic.distance, 4),
    }


def _serialize_frame(inf: InferredFrame) -> dict:
    fc = inf.constraint
    name = type(fc).__name__
    d = {"type": name, "confidence": round(inf.confidence, 4)}
    if hasattr(fc, "part"):
        d["part"] = f"{fc.part.role}.{fc.part.part}{fc.part.sign}"
    return d


def annotate_one(norm: NormalizedAnnotation) -> FPTRecord:
    if norm.me_pose is None or norm.op_pose is None:
        return FPTRecord(
            image=norm.image,
            frame=norm.frame,
            vicos_label=norm.vicos_position,
            blisp_label=norm.blisp_label,
            ambiguity=norm.ambiguity,
            radical_match=None,
            match_confidence=0.0,
        )

    contacts = infer_contacts(norm.me_pose, norm.op_pose)
    frames = infer_frame_constraints(norm.me_pose, norm.op_pose)
    matches = match_radical(contacts, frames)

    best_name = matches[0].radical_name if matches else None
    best_conf = matches[0].confidence if matches else 0.0

    top_contacts = contacts[:8]

    return FPTRecord(
        image=norm.image,
        frame=norm.frame,
        vicos_label=norm.vicos_position,
        blisp_label=norm.blisp_label,
        ambiguity=norm.ambiguity,
        radical_match=best_name,
        match_confidence=round(best_conf, 4),
        contacts=[_serialize_con(c) for c in top_contacts],
        frame_constraints=[_serialize_frame(f) for f in frames],
        all_matches=[
            {"radical": m.radical_name, "confidence": round(m.confidence, 4)}
            for m in matches[:5]
        ],
    )


def annotate_batch(
    annotations: list[Annotation],
    progress: bool = False,
) -> list[FPTRecord]:
    records = []
    total = len(annotations)
    for i, ann in enumerate(annotations):
        norm = normalize(ann)
        records.append(annotate_one(norm))
        if progress and (i + 1) % 5000 == 0:
            print(f"  {i+1}/{total} annotated...", file=sys.stderr)
    return records


def export_fpt(records: list[FPTRecord], path: Path) -> None:
    data = [asdict(r) for r in records]
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def load_fpt(path: Path) -> list[FPTRecord]:
    with open(path) as f:
        data = json.load(f)
    return [FPTRecord(**d) for d in data]


if __name__ == "__main__":
    from data.loader import load_annotations

    print("Loading annotations...", file=sys.stderr)
    annotations = load_annotations()

    print(f"Annotating {len(annotations)} images...", file=sys.stderr)
    records = annotate_batch(annotations, progress=True)

    out_path = Path("blisp/export/fpt_records.json")
    export_fpt(records, out_path)
    print(f"Exported {len(records)} FPT records to {out_path}", file=sys.stderr)
