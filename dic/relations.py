from dataclasses import dataclass
from dic.body_parts import LimbRef, AxisDef


@dataclass(frozen=True)
class CON:
    """The only primitive relation.

    CON(attacker_{from->to}, axis_{from->to}, depth, helicity)

    Both attacker and axis are oriented limbs (AxisDef).
    Everything else (GRP, HOOK, CLP) is a derived macro over CON.
    """
    attacker: AxisDef
    axis: AxisDef
    depth: str      # symbolic depth label: "d", "d1", "d2", etc.
    helicity: str   # "+" or "-"

    def __str__(self):
        return f"CON({self.attacker}, {self.axis}, {self.depth}, {self.helicity})"


def neg_helicity(h: str) -> str:
    if h == "+":
        return "-"
    if h == "-":
        return "+"
    raise ValueError(f"invalid helicity: {h}")
