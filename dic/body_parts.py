from dataclasses import dataclass
from enum import Enum


class BodyPart(str, Enum):
    Le = "Le"
    Ar = "Ar"
    Fo = "Fo"
    Hp = "Hp"
    Ha = "Ha"
    Sh = "Sh"
    To = "To"
    Hd = "Hd"
    Kn = "Kn"
    El = "El"
    Sn = "Sn"
    Wr = "Wr"
    Ba = "Ba"
    Ne = "Ne"
    LePair = "LePair"


VIRTUAL_PARTS = {BodyPart.Ha, BodyPart.Sn, BodyPart.Ba, BodyPart.Ne}

MIDLINE_PARTS = {BodyPart.To, BodyPart.Hd, BodyPart.Ba, BodyPart.Ne}

# COCO 17-keypoint index -> (BLISP part code, sign or None for midline)
COCO_TO_BLISP = {
    0:  ("Hd", None),
    1:  ("Hd", None),
    2:  ("Hd", None),
    3:  ("Hd", None),
    4:  ("Hd", None),
    5:  ("Sh", "-"),
    6:  ("Sh", "+"),
    7:  ("El", "-"),
    8:  ("El", "+"),
    9:  ("Wr", "-"),
    10: ("Wr", "+"),
    11: ("Hp", "-"),
    12: ("Hp", "+"),
    13: ("Kn", "-"),
    14: ("Kn", "+"),
    15: ("Fo", "-"),
    16: ("Fo", "+"),
}

# Distal -> proximal endpoints for limb axes
DEFAULT_AXIS_ENDPOINTS = {
    "Le": ("Fo", "Hp"),
    "Ar": ("Wr", "Sh"),
    "To": ("Hp", "Sh"),
}


@dataclass(frozen=True)
class LimbRef:
    role: str   # "Me" or "Op"
    part: str   # body part code
    sign: str = ""  # "+" or "-" for bilateral parts, "" for midline

    def __str__(self):
        return f"{self.role}.{self.part}{self.sign}"


@dataclass(frozen=True)
class AxisDef:
    limb_ref: LimbRef
    from_pt: str   # distal endpoint code
    to_pt: str     # proximal endpoint code

    def __str__(self):
        return f"{self.limb_ref}_{{{self.from_pt}->{self.to_pt}}}"
