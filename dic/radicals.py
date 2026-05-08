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
    forbidden_contacts: tuple[CON, ...] = ()
    forbidden_bilateral: tuple[CON, ...] = ()

    def __str__(self):
        parts = [self.name, "{"]
        for fc in self.frame_constraints:
            parts.append(f"  {fc}")
        for c in self.contacts:
            parts.append(f"  {c}")
        for c in self.forbidden_contacts:
            parts.append(f"  NOT {c}")
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
    forbidden_contacts=(
        CON(_me_ax("Fo", "-", "Fo", "Kn"), _me_ax("Fo", "+", "Fo", "Kn"), "d", "0"),
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

SCTR = Radical("SCTR",
    frame_constraints=(
        OnGround(_ref("Op", "Ba")),
    ),
    contacts=(
        CON(_me_ax("Ar", "+", "Wr", "Sh"), _op_ax("To", "", "Hp", "Sh"), "d1", "-"),
    ),
    forbidden_contacts=(
        CON(_me_ax("Le", "", "Fo", "Hp"), _op_ax("Le", "+", "Fo", "Hp"), "d", "-"),
        CON(_me_ax("Le", "", "Fo", "Hp"), _op_ax("Le", "-", "Fo", "Hp"), "d", "-"),
    ),
)

HGRD = Radical("HGRD",
    frame_constraints=(
        FacingOpposed(),
        OnGround(_ref("Me", "Ba")),
    ),
    contacts=(
        CON(_me_ax("Le", "", "Fo", "Hp"), _op_ax("Le", "", "Fo", "Hp"), "d1", "-"),
    ),
)

FIFTY_FIFTY = Radical("5050",
    contacts=(
        CON(_me_ax("Le", "-", "Fo", "Hp"), _op_ax("Le", "+", "Fo", "Hp"), "d1", "-"),
        CON(_me_ax("Le", "+", "Fo", "Hp"), _op_ax("Le", "-", "Fo", "Hp"), "d2", "-"),
    ),
    forbidden_bilateral=(
        CON(_me_ax("Le", "+", "Fo", "Hp"), _op_ax("To", "", "Hp", "Sh"), "d", "-"),
        CON(_me_ax("Le", "-", "Fo", "Hp"), _op_ax("To", "", "Hp", "Sh"), "d", "+"),
    ),
)

CGRD = Radical("CGRD",
    frame_constraints=(
        NotOnGround(_ref("Op", "Ba")),
    ),
    contacts=(
        CON(_me_ax("Le", "+", "Fo", "Hp"), _op_ax("To", "", "Hp", "Sh"), "d1", "-"),
        CON(_me_ax("Le", "-", "Fo", "Hp"), _op_ax("To", "", "Hp", "Sh"), "d2", "+"),
        CON(_me_ax("Fo", "-", "Fo", "Kn"), _me_ax("Fo", "+", "Fo", "Kn"), "d3", "0"),
    ),
)

TRTL = Radical("TRTL",
    frame_constraints=(
        FacingAligned(),
    ),
    contacts=(
        CON(_op_ax("To", "", "Hp", "Sh"), _me_ax("To", "", "Hp", "Sh"), "d1", "0"),
    ),
    forbidden_contacts=(
        CON(_op_ax("Le", "+", "Fo", "Hp"), _me_ax("To", "", "Hp", "Sh"), "d", "-"),
        CON(_op_ax("Le", "-", "Fo", "Hp"), _me_ax("To", "", "Hp", "Sh"), "d", "+"),
    ),
)

OGRD = Radical("OGRD",
    frame_constraints=(
        FacingOpposed(),
        OnGround(_ref("Me", "Ba")),
    ),
)

OGRD_SUBTYPES = ("DLR", "SLX", "RDLR", "LSSO", "OMOP")


ALL_RADICALS = {
    "MNT": MNT,
    "BCTR": BCTR,
    "SCTR": SCTR,
    "CGRD": CGRD,
    "OGRD": OGRD,
    "HGRD": HGRD,
    "TRTL": TRTL,
    "DLR": DLR,
    "SLX": SLX,
    "RDLR": RDLR,
    "LSSO": LSSO,
    "OMOP": OMOP,
}
