from dataclasses import dataclass
from typing import Optional
from data.schema import Annotation, Pose


VICOS_TO_BLISP = {
    "standing":       {"blisp": "STND", "ambiguity": "none"},
    "takedown1":      {"blisp": "TKDN", "ambiguity": "none"},
    "takedown2":      {"blisp": "TKDN", "ambiguity": "none"},
    "open_guard1":    {"blisp": "OGRD", "ambiguity": "high"},
    "open_guard2":    {"blisp": "OGRD", "ambiguity": "high"},
    "closed_guard1":  {"blisp": "CGRD", "ambiguity": "low"},
    "closed_guard2":  {"blisp": "CGRD", "ambiguity": "low"},
    "half_guard1":    {"blisp": "HGRD", "ambiguity": "medium"},
    "half_guard2":    {"blisp": "HGRD", "ambiguity": "medium"},
    "5050_guard":     {"blisp": "5050", "ambiguity": "low"},
    "side_control1":  {"blisp": "SCTR", "ambiguity": "low"},
    "side_control2":  {"blisp": "SCTR", "ambiguity": "low"},
    "mount1":         {"blisp": "MNT",  "ambiguity": "low"},
    "mount2":         {"blisp": "MNT",  "ambiguity": "low"},
    "back1":          {"blisp": "BCTR", "ambiguity": "medium"},
    "back2":          {"blisp": "BCTR", "ambiguity": "medium"},
    "turtle1":        {"blisp": "TRTL", "ambiguity": "medium"},
    "turtle2":        {"blisp": "TRTL", "ambiguity": "medium"},
}

ALL_VICOS_CLASSES = set(VICOS_TO_BLISP.keys())


def blisp_label(vicos_position: str) -> str:
    entry = VICOS_TO_BLISP.get(vicos_position)
    if entry is None:
        raise ValueError(f"unknown ViCoS position: {vicos_position}")
    return entry["blisp"]


def ambiguity(vicos_position: str) -> str:
    entry = VICOS_TO_BLISP.get(vicos_position)
    if entry is None:
        raise ValueError(f"unknown ViCoS position: {vicos_position}")
    return entry["ambiguity"]


@dataclass
class NormalizedAnnotation:
    """Annotation with POV resolved: me_pose is the reference player."""
    vicos_position: str
    blisp_label: str
    ambiguity: str
    image: str
    frame: int
    me_pose: Optional[Pose]
    op_pose: Optional[Pose]


def _parse_suffix(position: str) -> Optional[str]:
    """Extract the numeric suffix from a ViCoS label, or None."""
    if position[-1] in ("1", "2"):
        return position[-1]
    return None


def normalize(ann: Annotation) -> NormalizedAnnotation:
    """Apply POV normalization.

    Suffix convention:
      suffix "1" -> Me = pose1, Op = pose2
      suffix "2" -> Me = pose2, Op = pose1
      no suffix  -> Me = pose1, Op = pose2 (default; e.g. "standing", "5050_guard")
    """
    suffix = _parse_suffix(ann.position)

    if suffix == "2":
        me_pose = ann.pose2
        op_pose = ann.pose1
    else:
        me_pose = ann.pose1
        op_pose = ann.pose2

    bl = blisp_label(ann.position)
    amb = ambiguity(ann.position)

    return NormalizedAnnotation(
        vicos_position=ann.position,
        blisp_label=bl,
        ambiguity=amb,
        image=ann.image,
        frame=ann.frame,
        me_pose=me_pose,
        op_pose=op_pose,
    )
