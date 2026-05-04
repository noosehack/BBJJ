from dic.body_parts import LimbRef, AxisDef
from dic.relations import CON, neg_helicity
from dic.frames import (
    FrameConstraint, FacingOpposed, FacingAligned, OnGround, NotOnGround,
)
from dic.radicals import Radical


# ── operations on CON ─────────────────────────────────────────────

def hel_flip(con: CON) -> CON:
    """Flip helicity, preserve everything else."""
    return CON(con.attacker, con.axis, con.depth, neg_helicity(con.helicity))


def ax_sub(con: CON, new_axis: AxisDef) -> CON:
    """Substitute the target axis."""
    return CON(con.attacker, new_axis, con.depth, con.helicity)


def ax_rev(con: CON) -> CON:
    """Reverse axis orientation (swap from/to endpoints)."""
    rev_axis = AxisDef(con.axis.limb_ref, con.axis.to_pt, con.axis.from_pt)
    return CON(con.attacker, rev_axis, con.depth, con.helicity)


def pov_swap_con(con: CON) -> CON:
    """Swap attacker/axis and flip helicity, then rename Me<->Op."""
    new_att = _swap_role_axis(con.axis)
    new_axis = _swap_role_axis(con.attacker)
    return CON(new_att, new_axis, con.depth, neg_helicity(con.helicity))


# ── operations on frame constraints ──────────────────────────────

def pov_swap_frame(fc: FrameConstraint) -> FrameConstraint:
    """Transform a frame constraint under POV-SWAP."""
    if isinstance(fc, FacingOpposed):
        return FacingOpposed()
    if isinstance(fc, FacingAligned):
        return FacingAligned()
    if isinstance(fc, OnGround):
        return OnGround(_swap_role_limb(fc.part))
    if isinstance(fc, NotOnGround):
        return NotOnGround(_swap_role_limb(fc.part))
    raise TypeError(f"unknown frame constraint: {fc}")


# ── operations on radicals ────────────────────────────────────────

def hel_flip_radical(rad: Radical) -> Radical:
    """HEL-FLIP every CON in the radical."""
    return Radical(
        rad.name,
        rad.frame_constraints,
        tuple(hel_flip(c) for c in rad.contacts),
    )


def pov_swap_radical(rad: Radical) -> Radical:
    """POV-SWAP the entire radical: every CON + frame constraints."""
    return Radical(
        rad.name,
        tuple(pov_swap_frame(fc) for fc in rad.frame_constraints),
        tuple(pov_swap_con(c) for c in rad.contacts),
    )


# ── helpers ───────────────────────────────────────────────────────

def _swap_role(role: str) -> str:
    return "Op" if role == "Me" else "Me"


def _swap_role_limb(ref: LimbRef) -> LimbRef:
    return LimbRef(_swap_role(ref.role), ref.part, ref.sign)


def _swap_role_axis(ax: AxisDef) -> AxisDef:
    return AxisDef(_swap_role_limb(ax.limb_ref), ax.from_pt, ax.to_pt)
