"""Ordered projective radical constraints.

Each constraint projects four semantic landmarks onto a body-frame axis,
then extracts:

  1. ORDER SIGNATURE: 6 pairwise signs encoding the projected ordering
     of A,B,C,D along the axis.  Encodes topology — which landmarks
     come before/after which — robust to small perturbations because
     a sign only flips when two landmarks actually swap positions.

  2. LOG CROSS-RATIO: log((t_C-t_A)(t_D-t_B) / ((t_C-t_B)(t_D-t_A)))
     Projective invariant of the four collinear projected positions.
     Captures relative spacing independent of scale/translation.

  3. PROJECTED DISTANCE RATIOS: d(A,B)/span and d(C,D)/span
     How the four points divide the projection interval.

  4. SIDE PREDICATES: 4 signed lateral displacements from the axis,
     plus 2 bracket predicates (same-side / opposite-side).
     Encodes left/right, inside/outside, anterior/posterior.

  5. CONFIDENCE: min keypoint confidence of the four landmarks.

All features come in raw and confidence-weighted versions.
"""

import math
import numpy as np

from tools.pose_classifier_v2 import (
    BodyFrame, v2, vmid, vlen, vnorm, vdot,
    NOSE, L_SH, R_SH, L_EL, R_EL, L_WR, R_WR,
    L_HP, R_HP, L_KN, R_KN, L_AN, R_AN,
)


# ── Projection infrastructure ────────────────────────────────────

def _project(points, origin, direction):
    """Project 2D points onto a line defined by origin + direction.

    Returns (t_values, s_values) where:
      t = signed distance along direction (longitudinal)
      s = signed distance perpendicular (lateral; positive = left of direction)
    """
    perp = v2(-direction[1], direction[0])
    t_vals, s_vals = [], []
    for p in points:
        off = p - origin
        t_vals.append(float(vdot(off, direction)))
        s_vals.append(float(vdot(off, perp)))
    return t_vals, s_vals


def _log_cross_ratio_1d(t_a, t_b, t_c, t_d):
    """Cross-ratio of four scalar positions on a line.
    CR = (t_C - t_A)(t_D - t_B) / ((t_C - t_B)(t_D - t_A))
    Returns log(|CR|) with sign.
    """
    num = (t_c - t_a) * (t_d - t_b)
    den = (t_c - t_b) * (t_d - t_a)
    if abs(den) < 1e-8:
        return 0.0
    cr = num / den
    if cr <= 0:
        return -math.log(max(abs(cr), 1e-8))
    return math.log(cr)


def _pairwise_order_signs(t_a, t_b, t_c, t_d):
    """Six pairwise comparison signs encoding the ordering of 4 projected points.
    Returns list of 6 values in {-1, 0, +1}.
    """
    def sgn(x):
        if x > 1e-6:
            return 1.0
        elif x < -1e-6:
            return -1.0
        return 0.0

    return [
        sgn(t_a - t_b),  # A vs B
        sgn(t_a - t_c),  # A vs C
        sgn(t_a - t_d),  # A vs D
        sgn(t_b - t_c),  # B vs C
        sgn(t_b - t_d),  # B vs D
        sgn(t_c - t_d),  # C vs D
    ]


def _distance_ratios(t_a, t_b, t_c, t_d):
    """Projected distance ratios normalized by span."""
    span = max(t_a, t_b, t_c, t_d) - min(t_a, t_b, t_c, t_d)
    if span < 1e-6:
        return [0.0, 0.0]
    return [
        abs(t_a - t_b) / span,
        abs(t_c - t_d) / span,
    ]


def _side_predicates(s_a, s_b, s_c, s_d, ref_len):
    """Lateral predicates: signed positions + bracket patterns.

    Returns:
      4 normalized lateral positions (divided by ref_len)
      2 bracket predicates: same_side(A,C) and same_side(B,D)
    """
    rl = max(ref_len, 1.0)
    lat = [s_a / rl, s_b / rl, s_c / rl, s_d / rl]
    # Bracket: positive = same side, negative = opposite sides (one brackets)
    bracket_ac = 1.0 if s_a * s_c > 0 else (-1.0 if s_a * s_c < 0 else 0.0)
    bracket_bd = 1.0 if s_b * s_d > 0 else (-1.0 if s_b * s_d < 0 else 0.0)
    return lat + [bracket_ac, bracket_bd]


# ── Landmark resolution ──────────────────────────────────────────

def _resolve(kps, spec):
    """Resolve a landmark spec to (2D point, confidence).

    spec is:
      int          → single COCO keypoint
      (int, int)   → midpoint of two keypoints (conf = min)
    """
    if isinstance(spec, int):
        return v2(kps[spec][0], kps[spec][1]), float(kps[spec][2])
    i, j = spec
    pt = vmid(v2(kps[i][0], kps[i][1]), v2(kps[j][0], kps[j][1]))
    c = min(float(kps[i][2]), float(kps[j][2]))
    return pt, c


# ── Axis resolution ──────────────────────────────────────────────

def _get_axes(bf_me, bf_op):
    """Build named projection axes from two body frames."""
    # Center line: Me.center → Op.center
    cl_dir = bf_op.C - bf_me.C
    cl_len = vlen(cl_dir)
    cl_dir = vnorm(cl_dir) if cl_len > 1e-6 else bf_me.torso_dir

    return {
        "me_torso": (bf_me.H, bf_me.torso_dir),
        "op_torso": (bf_op.H, bf_op.torso_dir),
        "me_hip":   (bf_me.H, bf_me.hp_dir),
        "op_hip":   (bf_op.H, bf_op.hp_dir),
        "me_sh":    (bf_me.S, bf_me.sh_dir),
        "center":   (bf_me.C, cl_dir),
    }


# ── Constraint definitions ───────────────────────────────────────
#
# Each constraint: (name, axis_name,
#                   (role_A, spec_A), (role_B, spec_B),
#                   (role_C, spec_C), (role_D, spec_D))
# role is "me" or "op"
# spec is int or (int,int) for midpoint

CONSTRAINTS = []


def _c(name, axis, a, b, c, d):
    CONSTRAINTS.append((name, axis, a, b, c, d))


# ── 1. Torso stacking ───────────────────────────────────────────
# Captures vertical dominance, parallel vs perpendicular torsos.
# Quadruple: (Me.sh_ctr, Me.hp_ctr, Op.sh_ctr, Op.hp_ctr)

_c("torso_on_me_torso", "me_torso",
   ("me", (L_SH, R_SH)), ("me", (L_HP, R_HP)),
   ("op", (L_SH, R_SH)), ("op", (L_HP, R_HP)))

_c("torso_on_op_torso", "op_torso",
   ("me", (L_SH, R_SH)), ("me", (L_HP, R_HP)),
   ("op", (L_SH, R_SH)), ("op", (L_HP, R_HP)))

_c("torso_on_center", "center",
   ("me", (L_SH, R_SH)), ("me", (L_HP, R_HP)),
   ("op", (L_SH, R_SH)), ("op", (L_HP, R_HP)))

# Interleaved torso anchors for T-shape detection
_c("torso_cross_on_center", "center",
   ("me", (L_SH, R_SH)), ("op", (L_HP, R_HP)),
   ("op", (L_SH, R_SH)), ("me", (L_HP, R_HP)))


# ── 2. Knee straddle (mount/guard) ──────────────────────────────
# My knees relative to opponent's hip frame.

# Longitudinal: where are my knees along op's torso?
_c("me_kn_ophp_on_op_torso", "op_torso",
   ("me", L_KN), ("me", R_KN),
   ("op", L_HP), ("op", R_HP))

# Lateral: do my knees bracket op's hips?
_c("me_kn_ophp_on_op_hip", "op_hip",
   ("me", L_KN), ("me", R_KN),
   ("op", L_HP), ("op", R_HP))

# Same, projecting onto center line
_c("me_kn_ophp_on_center", "center",
   ("me", L_KN), ("me", R_KN),
   ("op", L_HP), ("op", R_HP))

# Reverse: op's knees relative to my hip frame
_c("op_kn_mehp_on_me_torso", "me_torso",
   ("op", L_KN), ("op", R_KN),
   ("me", L_HP), ("me", R_HP))

_c("op_kn_mehp_on_me_hip", "me_hip",
   ("op", L_KN), ("op", R_KN),
   ("me", L_HP), ("me", R_HP))


# ── 3. Ankle-torso (guard closure) ──────────────────────────────
# My ankles relative to opponent's torso axis — guard wrap.

_c("me_an_optorso_on_op_torso", "op_torso",
   ("me", L_AN), ("me", R_AN),
   ("op", (L_HP, R_HP)), ("op", (L_SH, R_SH)))

_c("me_an_optorso_on_op_hip", "op_hip",
   ("me", L_AN), ("me", R_AN),
   ("op", (L_HP, R_HP)), ("op", (L_SH, R_SH)))

# Reverse
_c("op_an_metorso_on_me_torso", "me_torso",
   ("op", L_AN), ("op", R_AN),
   ("me", (L_HP, R_HP)), ("me", (L_SH, R_SH)))

_c("op_an_metorso_on_me_hip", "me_hip",
   ("op", L_AN), ("op", R_AN),
   ("me", (L_HP, R_HP)), ("me", (L_SH, R_SH)))


# ── 4. Knee-knee entanglement (half guard, 50/50) ───────────────

_c("knees_on_center", "center",
   ("me", L_KN), ("me", R_KN),
   ("op", L_KN), ("op", R_KN))

_c("knees_on_me_hip", "me_hip",
   ("me", L_KN), ("me", R_KN),
   ("op", L_KN), ("op", R_KN))

_c("knees_on_me_torso", "me_torso",
   ("me", L_KN), ("me", R_KN),
   ("op", L_KN), ("op", R_KN))


# ── 5. Ankle-ankle ──────────────────────────────────────────────

_c("ankles_on_center", "center",
   ("me", L_AN), ("me", R_AN),
   ("op", L_AN), ("op", R_AN))

_c("ankles_on_me_hip", "me_hip",
   ("me", L_AN), ("me", R_AN),
   ("op", L_AN), ("op", R_AN))


# ── 6. Shoulder alignment ───────────────────────────────────────

_c("shoulders_on_center", "center",
   ("me", L_SH), ("me", R_SH),
   ("op", L_SH), ("op", R_SH))

_c("shoulders_on_me_torso", "me_torso",
   ("me", L_SH), ("me", R_SH),
   ("op", L_SH), ("op", R_SH))


# ── 7. Arm engagement ───────────────────────────────────────────

_c("me_el_optorso_on_op_torso", "op_torso",
   ("me", L_EL), ("me", R_EL),
   ("op", (L_SH, R_SH)), ("op", (L_HP, R_HP)))

_c("op_el_metorso_on_me_torso", "me_torso",
   ("op", L_EL), ("op", R_EL),
   ("me", (L_SH, R_SH)), ("me", (L_HP, R_HP)))


# ── 8. Head-body ────────────────────────────────────────────────

_c("heads_hips_on_center", "center",
   ("me", NOSE), ("op", NOSE),
   ("me", (L_HP, R_HP)), ("op", (L_HP, R_HP)))

_c("heads_hips_on_me_torso", "me_torso",
   ("me", NOSE), ("op", NOSE),
   ("me", (L_HP, R_HP)), ("op", (L_HP, R_HP)))


# ── 9. Mixed cross-body (position-specific) ─────────────────────

# Mount bracket: my knees around op's shoulder-hip line
_c("me_kn_optorso_on_op_torso", "op_torso",
   ("me", L_KN), ("op", (L_HP, R_HP)),
   ("me", R_KN), ("op", (L_SH, R_SH)))

# Guard wrap: my ankles around op's shoulder-hip line
_c("me_an_optorso_wrap_on_op_torso", "op_torso",
   ("me", L_AN), ("op", (L_HP, R_HP)),
   ("me", R_AN), ("op", (L_SH, R_SH)))

# Knee-ankle interaction (half guard asymmetry)
_c("kn_an_on_center", "center",
   ("me", L_KN), ("me", L_AN),
   ("op", L_KN), ("op", L_AN))


N_CONSTRAINTS = len(CONSTRAINTS)
FEATURES_PER_CONSTRAINT = 15  # 6 order + 1 log_cr + 2 dist_ratio + 4 lat + 2 bracket


# ── Feature extraction ───────────────────────────────────────────

def extract_ordered_cr_features(kps_me, kps_op):
    """Extract ordered projective constraint features.

    Returns (features, names) where features is a flat list of floats.
    Each constraint produces FEATURES_PER_CONSTRAINT raw features
    plus 1 confidence value = 16 features total.
    """
    bf_me = BodyFrame(kps_me)
    bf_op = BodyFrame(kps_op)
    axes = _get_axes(bf_me, bf_op)
    ref_len = (bf_me.torso_len + bf_op.torso_len) / 2.0

    kps_map = {"me": kps_me, "op": kps_op}

    features = []
    names = []

    for c_name, axis_name, spec_a, spec_b, spec_c, spec_d in CONSTRAINTS:
        # Resolve landmarks
        p_a, c_a = _resolve(kps_map[spec_a[0]], spec_a[1])
        p_b, c_b = _resolve(kps_map[spec_b[0]], spec_b[1])
        p_c, c_c = _resolve(kps_map[spec_c[0]], spec_c[1])
        p_d, c_d = _resolve(kps_map[spec_d[0]], spec_d[1])
        min_conf = min(c_a, c_b, c_c, c_d)

        # Resolve axis
        origin, direction = axes[axis_name]

        # Project
        t_vals, s_vals = _project([p_a, p_b, p_c, p_d], origin, direction)
        t_a, t_b, t_c, t_d = t_vals
        s_a, s_b, s_c, s_d = s_vals

        # 1. Order signature (6 pairwise signs)
        order = _pairwise_order_signs(t_a, t_b, t_c, t_d)

        # 2. Log cross-ratio
        lcr = _log_cross_ratio_1d(t_a, t_b, t_c, t_d)

        # 3. Distance ratios
        drat = _distance_ratios(t_a, t_b, t_c, t_d)

        # 4. Side predicates (4 lateral + 2 bracket)
        sides = _side_predicates(s_a, s_b, s_c, s_d, ref_len)

        # Assemble
        prefix = f"oc_{c_name}"
        constraint_feats = order + [lcr] + drat + sides + [min_conf]
        constraint_names = (
            [f"{prefix}_ord_{i}" for i in range(6)] +
            [f"{prefix}_logcr"] +
            [f"{prefix}_drat_ab", f"{prefix}_drat_cd"] +
            [f"{prefix}_lat_a", f"{prefix}_lat_b",
             f"{prefix}_lat_c", f"{prefix}_lat_d",
             f"{prefix}_bracket_ac", f"{prefix}_bracket_bd"] +
            [f"{prefix}_minconf"]
        )

        features.extend(constraint_feats)
        names.extend(constraint_names)

    return features, names


def confidence_weight_ordered_cr(features, names):
    """Apply per-constraint confidence weighting.

    For each constraint block, multiply all features (except minconf itself)
    by the constraint's minconf value.
    """
    weighted = []
    w_names = []
    block = FEATURES_PER_CONSTRAINT + 1  # 15 feature + 1 minconf

    for i in range(0, len(features), block):
        chunk = features[i:i + block]
        chunk_names = names[i:i + block]
        min_c = chunk[-1]  # last element is minconf

        for j in range(len(chunk) - 1):
            weighted.append(chunk[j] * min_c)
            w_names.append(f"cw_{chunk_names[j]}")
        weighted.append(min_c)
        w_names.append(chunk_names[-1])

    return weighted, w_names


N_FEATURES_RAW = N_CONSTRAINTS * (FEATURES_PER_CONSTRAINT + 1)
