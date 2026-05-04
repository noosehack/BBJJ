"""BLISP s-expression serialization for FPT records."""

from tools.annotate import FPTRecord


def _format_nam(r: FPTRecord) -> str:
    vid = r.image[:2]
    return f"video{vid}_frame{r.frame:06d}"


def _format_con(c: dict) -> str:
    att = c["attacker"]
    ax = c["axis"]
    conf = c["confidence"]
    hel = c["helicity"]
    return f"(CON {att} {ax} {conf} {hel})"


def _format_frame(f: dict) -> str:
    t = f["type"]
    if t == "FacingOpposed":
        return "(EQ y (NEG y'))"
    if t == "FacingAligned":
        return "(EQ y y')"
    part = f.get("part", "?")
    if t == "OnGround":
        return f"(Z0 {part})"
    if t == "NotOnGround":
        return f"(NOT (Z0 {part}))"
    if t == "KneeBracket":
        return f"(KBR {part})"
    if t == "NotKneeBracket":
        return f"(NOT (KBR {part}))"
    return f"({t})"


def _format_axes(contacts: list[dict]) -> list[str]:
    seen = set()
    axes = []
    for c in contacts:
        for key, orient_key in [("attacker", "attacker_axis"), ("axis", "axis_orient")]:
            name = c[key]
            orient = c.get(orient_key, "")
            label = f"{name}_{{{orient}}}" if orient else name
            if label not in seen:
                seen.add(label)
                axes.append(f"(AXS {label})")
    return axes


def fpt_to_sexpr(r: FPTRecord) -> str:
    nam = _format_nam(r)
    lines = [
        "(FPT",
        "  :KND POS",
        f'  :NAM "{nam}"',
        "  :CMPN {",
    ]

    if r.contacts:
        ax_strs = _format_axes(r.contacts)
        lines.append("    AXS (")
        for a in ax_strs:
            lines.append(f"      {a}")
        lines.append("    )")

    if r.contacts:
        lines.append("    CON (")
        for c in r.contacts:
            lines.append(f"      {_format_con(c)}")
        lines.append("    )")

    if r.frame_constraints:
        lines.append("    FRM (")
        for f in r.frame_constraints:
            lines.append(f"      {_format_frame(f)}")
        lines.append("    )")

    if r.radical_match:
        lines.append(f"    RAD {r.radical_match}")
    else:
        lines.append("    RAD NONE")

    if r.all_matches:
        lines.append("    CONF (")
        for m in r.all_matches:
            lines.append(f"      ({m['radical']} {m['confidence']})")
        lines.append("    )")

    lines.append("  }")
    lines.append(")")
    return "\n".join(lines)


def export_sexpr(records: list[FPTRecord], path) -> None:
    from pathlib import Path
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w") as f:
        for r in records:
            f.write(fpt_to_sexpr(r))
            f.write("\n\n")
