"""Feature invariance audit and filtering.

Classifies every feature in the combined 635-feature pipeline:
  projective_2d        — confidence values, visibility counts
  similarity_2d        — dot products, distance ratios, self-frame coords,
                         signed areas, angle differences, center-line projections
  camera_conditioned_2d — absolute angles, image-Y vertical proxy
  invalid_bodyframe_2d  — projects one athlete into the other's 2D body frame

Only projective_2d and similarity_2d features survive filtering.
"""

KEEP_STRICT = {"projective_2d", "similarity_2d"}
KEEP_WITH_CAMERA = {"projective_2d", "similarity_2d", "camera_conditioned_2d"}


def classify_feature(name: str) -> str:
    """Return the invariance level for a named feature."""
    base = name[3:] if name.startswith("cw_") else name

    # Ordered CR: center-line axis is similarity-invariant, body-frame axes are not
    if base.startswith("oc_"):
        return "similarity_2d" if "_on_center" in base else "invalid_bodyframe_2d"

    # Naked CR features (distance-based cross-ratios)
    if base.startswith("cr_"):
        return "similarity_2d"

    # New invariant cross-body features
    if base.startswith(("xd_", "sa_", "xa_", "enc_")):
        return "similarity_2d"

    # Per-athlete self-frame features (me_/op_ prefix)
    for prefix in ("me_", "op_"):
        if not base.startswith(prefix):
            continue
        suffix = base[len(prefix):]
        if suffix in ("torso_angle", "torso_len", "facing_angle"):
            return "camera_conditioned_2d"
        if "_conf" in suffix or suffix in ("vis_upper", "vis_lower"):
            return "projective_2d"
        return "similarity_2d"

    # Cross-body frame projections
    if "_in_a_" in base or base.endswith("_in_a"):
        return "invalid_bodyframe_2d"
    if "_in_b_" in base or base.endswith("_in_b"):
        return "invalid_bodyframe_2d"

    # Body-frame bracket/between predicates
    if base in ("b_between_a_knees", "a_between_b_knees"):
        return "invalid_bodyframe_2d"

    # Camera-conditioned (image-Y as vertical proxy)
    if base in ("vert_dominance", "a_hp_over_b_sh", "a_sh_over_b_hp",
                "b_torso_from_vertical"):
        return "camera_conditioned_2d"

    # Remaining pairwise features: dots, crosses, distance ratios
    return "similarity_2d"


def filter_invariant(features: list, names: list,
                     keep_camera: bool = False) -> tuple:
    """Keep only invariant features.

    keep_camera=False: strict — projective_2d + similarity_2d only
    keep_camera=True:  also keep camera_conditioned_2d (vert_dominance etc.)
    """
    levels = KEEP_WITH_CAMERA if keep_camera else KEEP_STRICT
    f_out, n_out = [], []
    for f, n in zip(features, names):
        if classify_feature(n) in levels:
            f_out.append(f)
            n_out.append(n)
    return f_out, n_out


def audit(names: list) -> dict:
    """Group feature names by invariance level."""
    groups: dict[str, list[str]] = {}
    for n in names:
        level = classify_feature(n)
        groups.setdefault(level, []).append(n)
    return groups
