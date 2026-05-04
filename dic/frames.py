from dataclasses import dataclass
from dic.body_parts import LimbRef


@dataclass(frozen=True)
class FacingOpposed:
    """y = -y' : Me faces Op, Op faces Me."""
    pass


@dataclass(frozen=True)
class FacingAligned:
    """y = y' : same facing direction (e.g. back control)."""
    pass


@dataclass(frozen=True)
class OnGround:
    """Z0(X) : body part X is on the ground."""
    part: LimbRef


@dataclass(frozen=True)
class NotOnGround:
    """¬Z0(X) : body part X is elevated."""
    part: LimbRef


@dataclass(frozen=True)
class KneeBracket:
    """KBR(X) : Me's knees bracket X (one near head-end, one near hip-end)."""
    part: LimbRef


@dataclass(frozen=True)
class NotKneeBracket:
    """¬KBR(X) : Me's knees do NOT bracket X."""
    part: LimbRef


FrameConstraint = FacingOpposed | FacingAligned | OnGround | NotOnGround | KneeBracket | NotKneeBracket
