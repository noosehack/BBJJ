from dataclasses import dataclass
from dic.body_parts import LimbRef, AxisDef
from dic.relations import CON
from dic.frames import (
    FrameConstraint, FacingOpposed, FacingAligned, OnGround, NotOnGround,
)


@dataclass(frozen=True)
class Radical:
    name: str
    frame_constraints: tuple[FrameConstraint, ...] = ()
    contacts: tuple[CON, ...] = ()

    def __str__(self):
        parts = [self.name, "{"]
        for fc in self.frame_constraints:
            parts.append(f"  {fc}")
        for c in self.contacts:
            parts.append(f"  {c}")
        parts.append("}")
        return "\n".join(parts)


# ── helper constructors ──────────────────────────────────────────

def _ref(role, part, sign=""):
    return LimbRef(role, part, sign)

def _ax(role, part, sign, from_pt, to_pt):
    return AxisDef(LimbRef(role, part, sign), from_pt, to_pt)

def _me_ax(part, sign, from_pt, to_pt):
    return _ax("Me", part, sign, from_pt, to_pt)

def _op_ax(part, sign, from_pt, to_pt):
    return _ax("Op", part, sign, from_pt, to_pt)


# ── canonical radicals (explicit literals) ────────────────────────

MNT = Radical("MNT",
    frame_constraints=(
        FacingOpposed(),
        OnGround(_ref("Op", "Ba")),
    ),
    contacts=(
        CON(_me_ax("Le", "+", "Fo", "Hp"), _op_ax("To", "", "Hp", "Sh"), "d1", "-"),
        CON(_me_ax("Le", "-", "Fo", "Hp"), _op_ax("To", "", "Hp", "Sh"), "d2", "+"),
    ),
)

BCTR = Radical("BCTR",
    frame_constraints=(
        FacingAligned(),
        NotOnGround(_ref("Op", "Ba")),
    ),
    contacts=(
        CON(_me_ax("Le", "+", "Fo", "Hp"), _op_ax("To", "", "Hp", "Sh"), "d1", "-"),
        CON(_me_ax("Le", "-", "Fo", "Hp"), _op_ax("To", "", "Hp", "Sh"), "d2", "+"),
    ),
)

DLR = Radical("DLR",
    contacts=(
        CON(_me_ax("Le", "-", "Fo", "Hp"), _op_ax("Le", "+", "Fo", "Hp"), "d", "-"),
    ),
)

SLX = Radical("SLX",
    contacts=(
        CON(_me_ax("Le", "-", "Fo", "Hp"), _op_ax("Le", "+", "Fo", "Hp"), "d", "+"),
    ),
)

RDLR = Radical("RDLR",
    contacts=(
        CON(_me_ax("Le", "-", "Fo", "Hp"), _op_ax("Le", "-", "Fo", "Hp"), "d", "-"),
    ),
)

LSSO = Radical("LSSO",
    contacts=(
        CON(_me_ax("Le", "-", "Fo", "Hp"), _op_ax("Ar", "+", "Wr", "Sh"), "d", "+"),
    ),
)

OMOP = Radical("OMOP",
    contacts=(
        CON(_me_ax("Le", "-", "Fo", "Hp"), _op_ax("Ar", "+", "Sh", "Wr"), "d", "+"),
    ),
)


ALL_RADICALS = {
    "MNT": MNT,
    "BCTR": BCTR,
    "DLR": DLR,
    "SLX": SLX,
    "RDLR": RDLR,
    "LSSO": LSSO,
    "OMOP": OMOP,
}
