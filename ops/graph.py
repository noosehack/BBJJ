"""Positional hierarchy, transitions, and structural distance between radicals."""

from dic.radicals import ALL_RADICALS, OGRD_SUBTYPES, Radical
from dic.relations import CON
from dic.frames import (
    FacingOpposed, FacingAligned, OnGround, NotOnGround,
    KneeBracket, NotKneeBracket,
)


# ── Defense levels (barriers remaining: feet, knees, hips) ────────
#
#   3 = all barriers intact (feet engaged)
#   2 = feet cleared, knees engaged
#   1 = knees cleared, hips engaged
#   0 = guard passed / dominant

DEFENSE_LEVEL = {
    "OGRD": 3, "DLR": 3, "SLX": 3, "RDLR": 3, "LSSO": 3, "OMOP": 3,
    "HGRD": 2,
    "CGRD": 1,
    "SCTR": 0, "MNT": 0, "BCTR": 0, "TRTL": 0,
}

DEFENSE_LABELS = {3: "feet", 2: "knees", 1: "hips", 0: "passed"}


# ── Positional transitions ────────────────────────────────────────
#
# Directed edges: (from, to, transition_type)
# "pass" = top advances, "recover" = bottom escapes, "lateral" = same level

TRANSITIONS = [
    # Guard passing (top advances through defense lines)
    ("OGRD", "HGRD",  "pass"),
    ("OGRD", "SCTR",  "pass"),
    ("HGRD", "SCTR",  "pass"),
    ("CGRD", "SCTR",  "pass"),
    ("CGRD", "MNT",   "pass"),

    # Guard retention / closing
    ("OGRD", "CGRD",  "close"),
    ("HGRD", "CGRD",  "close"),

    # Dominant advancement
    ("SCTR", "MNT",   "advance"),
    ("SCTR", "BCTR",  "advance"),
    ("TRTL", "BCTR",  "advance"),

    # Escapes / recovery (bottom regains guard)
    ("SCTR", "HGRD",  "recover"),
    ("SCTR", "OGRD",  "recover"),
    ("SCTR", "TRTL",  "recover"),
    ("MNT",  "OGRD",  "recover"),
    ("MNT",  "HGRD",  "recover"),
    ("BCTR", "TRTL",  "recover"),
    ("BCTR", "OGRD",  "recover"),
    ("TRTL", "OGRD",  "recover"),

    # OGRD subtype transitions (lateral, each = 1 CON field change)
    ("DLR",  "SLX",   "lateral"),    # helicity flip
    ("SLX",  "DLR",   "lateral"),    # helicity flip
    ("DLR",  "RDLR",  "lateral"),    # target sign flip (Op.Le+ → Op.Le-)
    ("RDLR", "DLR",   "lateral"),    # target sign flip
    ("SLX",  "LSSO",  "lateral"),    # axis part (Op.Le → Op.Ar)
    ("LSSO", "SLX",   "lateral"),    # axis part
    ("LSSO", "OMOP",  "lateral"),    # axis direction flip (Wr→Sh to Sh→Wr)
    ("OMOP", "LSSO",  "lateral"),    # axis direction flip
]


# ── Feature extraction ────────────────────────────────────────────

def _frame_vec(rad):
    v = {
        "facing_opposed": 0, "facing_aligned": 0,
        "ground_me": 0, "ground_op": 0,
        "elevated_me": 0, "elevated_op": 0,
        "kbr": 0, "no_kbr": 0,
    }
    for fc in rad.frame_constraints:
        if isinstance(fc, FacingOpposed):   v["facing_opposed"] = 1
        elif isinstance(fc, FacingAligned): v["facing_aligned"] = 1
        elif isinstance(fc, OnGround):
            v["ground_me" if fc.part.role == "Me" else "ground_op"] = 1
        elif isinstance(fc, NotOnGround):
            v["elevated_me" if fc.part.role == "Me" else "elevated_op"] = 1
        elif isinstance(fc, KneeBracket):    v["kbr"] = 1
        elif isinstance(fc, NotKneeBracket): v["no_kbr"] = 1
    return v


def _con_sig(con):
    """Compact signature for a CON: (att_role, att_part, ax_role, ax_part, helicity)."""
    a = con.attacker.limb_ref
    x = con.axis.limb_ref
    return (a.role, a.part, a.sign, x.role, x.part, x.sign, con.helicity)


def _contact_type(con):
    """Coarse contact type: role.part→role.part."""
    a = con.attacker.limb_ref
    x = con.axis.limb_ref
    return f"{a.role}.{a.part}->{x.role}.{x.part}"


def feature_vector(rad):
    """Full feature dict for a radical."""
    fv = _frame_vec(rad)
    fv["n_contacts"] = len(rad.contacts)
    fv["n_forbidden"] = len(rad.forbidden_contacts)
    fv["n_forbidden_bilateral"] = len(rad.forbidden_bilateral)
    fv["has_closure"] = int(any(
        c.attacker.limb_ref.role == c.axis.limb_ref.role
        for c in rad.contacts
    ))

    con_types = set()
    for c in rad.contacts:
        con_types.add(_contact_type(c))
    fbd_types = set()
    for c in rad.forbidden_contacts:
        fbd_types.add(_contact_type(c))

    all_types = set()
    for r in ALL_RADICALS.values():
        for c in r.contacts:
            all_types.add(_contact_type(c))

    for t in sorted(all_types):
        fv[f"con:{t}"] = int(t in con_types)
    for t in sorted(all_types):
        fv[f"fbd:{t}"] = int(t in fbd_types)

    return fv


# ── Structural distance ──────────────────────────────────────────
#
# Distance = frame_dist + contact_dist + forbidden_dist
#
# Contact distance aligns CONs by minimum edit cost.
# Independent CON fields (endpoints are entailed by part):
#   att_role, att_part, att_sign, att_dir, ax_role, ax_part, ax_sign, ax_dir, helicity
#
# Unmatched penalty = N_CON_FIELDS (9): adding/removing a contact means
# specifying all 9 fields from nothing, same as max possible edit distance.

from dic.body_parts import DEFAULT_AXIS_ENDPOINTS


def _axis_dir(axis_def):
    """'fwd' if from→to matches default endpoints, 'rev' if flipped."""
    default = DEFAULT_AXIS_ENDPOINTS.get(axis_def.limb_ref.part)
    if default is None:
        return "fwd"
    if (axis_def.from_pt, axis_def.to_pt) == default:
        return "fwd"
    return "rev"


def _con_to_tuple(con):
    """Independent fields only — endpoints entailed by part, direction captured separately."""
    a = con.attacker.limb_ref
    x = con.axis.limb_ref
    return (a.role, a.part, a.sign, _axis_dir(con.attacker),
            x.role, x.part, x.sign, _axis_dir(con.axis),
            con.helicity)


def _con_field_dist(c1, c2):
    """Count differing independent fields between two CONs."""
    return sum(a != b for a, b in zip(_con_to_tuple(c1), _con_to_tuple(c2)))


def _frame_dist(r1, r2):
    f1 = _frame_vec(r1)
    f2 = _frame_vec(r2)
    return sum(abs(f1[k] - f2[k]) for k in f1)


N_CON_FIELDS = 9


def _align_contacts(list1, list2):
    """Min-cost alignment of two contact lists. Unmatched = N_CON_FIELDS."""
    UNMATCHED = N_CON_FIELDS
    if not list1 and not list2:
        return 0
    if not list1:
        return len(list2) * UNMATCHED
    if not list2:
        return len(list1) * UNMATCHED

    # Greedy: match each c1 to the closest unused c2
    used = set()
    total = 0
    for c1 in list1:
        best_j, best_d = -1, UNMATCHED + 1
        for j, c2 in enumerate(list2):
            if j in used:
                continue
            d = _con_field_dist(c1, c2)
            if d < best_d:
                best_d = d
                best_j = j
        if best_j >= 0 and best_d <= UNMATCHED:
            used.add(best_j)
            total += best_d
        else:
            total += UNMATCHED
    total += (len(list2) - len(used)) * UNMATCHED
    return total


def structural_distance(r1, r2):
    """Distance between two radicals: frame + contact field differences."""
    d_frame = _frame_dist(r1, r2)
    d_con = _align_contacts(list(r1.contacts), list(r2.contacts))
    d_fbd = _align_contacts(list(r1.forbidden_contacts), list(r2.forbidden_contacts))
    d_fbd_bi = _align_contacts(list(r1.forbidden_bilateral), list(r2.forbidden_bilateral))
    return d_frame + d_con + d_fbd + d_fbd_bi


def distance_matrix(names=None):
    """Pairwise structural distance matrix."""
    if names is None:
        names = list(ALL_RADICALS.keys())
    rads = {n: ALL_RADICALS[n] for n in names}
    mat = {}
    for a in names:
        for b in names:
            mat[(a, b)] = structural_distance(rads[a], rads[b])
    return names, mat


# ── Display ───────────────────────────────────────────────────────

def print_hierarchy():
    """Print the defense-level hierarchy."""
    by_level = {}
    for name, level in DEFENSE_LEVEL.items():
        by_level.setdefault(level, []).append(name)

    print("╔══════════════════════════════════════════════════════════╗")
    print("║           POSITIONAL HIERARCHY (defense lines)          ║")
    print("╠══════════════════════════════════════════════════════════╣")
    for level in sorted(by_level.keys(), reverse=True):
        label = DEFENSE_LABELS[level]
        positions = by_level[level]
        fundamentals = [p for p in positions if p in
                        {"MNT", "SCTR", "BCTR", "CGRD", "OGRD", "HGRD", "TRTL"}]
        subtypes = [p for p in positions if p not in fundamentals]
        line = ", ".join(fundamentals)
        if subtypes:
            line += f"  [{', '.join(subtypes)}]"
        print(f"║  Level {level} ({label:6s}): {line:<40s} ║")
    print("╚══════════════════════════════════════════════════════════╝")


def print_transitions():
    """Print transition graph."""
    print("\n╔══════════════════════════════════════════════════════════╗")
    print("║              TRANSITION GRAPH                           ║")
    print("╠══════════════════════════════════════════════════════════╣")
    for kind in ("pass", "close", "advance", "recover", "lateral"):
        edges = [(a, b) for a, b, t in TRANSITIONS if t == kind]
        if edges:
            arrows = ", ".join(f"{a}→{b}" for a, b in edges)
            print(f"║  {kind:8s}: {arrows:<46s} ║")
    print("╚══════════════════════════════════════════════════════════╝")


def print_distance_matrix(names=None):
    """Print pairwise structural distance matrix."""
    names, mat = distance_matrix(names)
    w = 5

    print(f"\n{'':8s}", end="")
    for n in names:
        print(f"{n:>{w}s}", end="")
    print()
    print("  " + "─" * (6 + w * len(names)))

    for a in names:
        print(f"  {a:5s} │", end="")
        for b in names:
            d = mat[(a, b)]
            if a == b:
                print(f"{'·':>{w}s}", end="")
            else:
                print(f"{d:>{w}d}", end="")
        print()


def print_feature_comparison(names=None):
    """Print feature vectors side by side."""
    if names is None:
        names = ["MNT", "SCTR", "BCTR", "CGRD", "OGRD", "HGRD", "TRTL"]
    vecs = {n: feature_vector(ALL_RADICALS[n]) for n in names}
    all_keys = []
    for v in vecs.values():
        for k in v:
            if k not in all_keys:
                all_keys.append(k)

    w = 6
    print(f"\n  {'feature':<28s}", end="")
    for n in names:
        print(f"{n:>{w}s}", end="")
    print()
    print("  " + "─" * (28 + w * len(names)))

    for k in all_keys:
        vals = [vecs[n].get(k, 0) for n in names]
        if all(v == 0 for v in vals):
            continue
        print(f"  {k:<28s}", end="")
        for v in vals:
            print(f"{v:>{w}d}", end="")
        print()
