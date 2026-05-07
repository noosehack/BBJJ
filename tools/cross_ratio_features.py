"""Cross-ratio feature layer for BJJ position classification.

Cross-ratios of landmark quadruples are projective invariants — they depend
only on relative distances between landmarks, making them more stable under
keypoint perturbation than body-frame-relative coordinates.

Given four 2D points P1..P4, the distance-based cross-ratio is:
    CR(P1,P2,P3,P4) = (d(P1,P3) * d(P2,P4)) / (d(P2,P3) * d(P1,P4))

Each quadruple produces 3 features:
  - log_cr: log(CR), centered at 0 (CR=1 → 0)
  - orientation_sign: sign of the oriented area of the first triangle
  - min_conf: minimum keypoint confidence (quality gate for downstream)
"""

import math
import numpy as np

# ── COCO-17 keypoint indices ─────────────────────────────────────

NOSE = 0
L_SH, R_SH = 5, 6
L_EL, R_EL = 7, 8
L_WR, R_WR = 9, 10
L_HP, R_HP = 11, 12
L_KN, R_KN = 13, 14
L_AN, R_AN = 15, 16


def _pt(kps, idx):
    return np.array([kps[idx][0], kps[idx][1]], dtype=np.float64)


def _conf(kps, idx):
    return float(kps[idx][2])


def _mid(kps, i, j):
    return (_pt(kps, i) + _pt(kps, j)) * 0.5


def _mid_conf(kps, i, j):
    return min(_conf(kps, i), _conf(kps, j))


def _dist(a, b):
    return float(np.linalg.norm(a - b))


def _signed_area(p1, p2, p3):
    return float((p2[0] - p1[0]) * (p3[1] - p1[1]) -
                 (p2[1] - p1[1]) * (p3[0] - p1[0]))


def _cross_ratio(p1, p2, p3, p4):
    d13 = _dist(p1, p3)
    d24 = _dist(p2, p4)
    d23 = _dist(p2, p3)
    d14 = _dist(p1, p4)
    denom = d23 * d14
    if denom < 1e-6:
        return 1.0
    return (d13 * d24) / denom


def _log_cr(cr):
    if cr <= 0:
        return 0.0
    return math.log(cr)


# ── Quadruple definitions ────────────────────────────────────────
#
# Each entry: (name, (kps_src_1, idx_1), (kps_src_2, idx_2), ...)
# kps_src is "a" or "b" (athlete A or B)
# idx can be an int (COCO index) or a tuple (i, j) meaning midpoint

QUADRUPLES = []


def _q(name, a1, a2, a3, a4):
    QUADRUPLES.append((name, a1, a2, a3, a4))


# ── 1. Torso relations ──────────────────────────────────────────
# These capture relative torso position and orientation

# All four torso anchors
_q("torso_shsh_hphp",
   ("a", (L_SH, R_SH)), ("a", (L_HP, R_HP)),
   ("b", (L_SH, R_SH)), ("b", (L_HP, R_HP)))

# Interleaved: A.sh — B.sh — A.hp — B.hp
_q("torso_interleaved",
   ("a", (L_SH, R_SH)), ("b", (L_SH, R_SH)),
   ("a", (L_HP, R_HP)), ("b", (L_HP, R_HP)))

# Crossed: A.sh — B.hp — B.sh — A.hp
_q("torso_crossed",
   ("a", (L_SH, R_SH)), ("b", (L_HP, R_HP)),
   ("b", (L_SH, R_SH)), ("a", (L_HP, R_HP)))

# ── 2. Shoulder alignment ───────────────────────────────────────

_q("shoulders_all",
   ("a", L_SH), ("a", R_SH), ("b", L_SH), ("b", R_SH))

_q("shoulders_cross",
   ("a", L_SH), ("b", R_SH), ("a", R_SH), ("b", L_SH))

# ── 3. Hip alignment ────────────────────────────────────────────

_q("hips_all",
   ("a", L_HP), ("a", R_HP), ("b", L_HP), ("b", R_HP))

_q("hips_cross",
   ("a", L_HP), ("b", R_HP), ("a", R_HP), ("b", L_HP))

# ── 4. Frame shape (per athlete) ────────────────────────────────

_q("frame_a", ("a", L_SH), ("a", R_SH), ("a", L_HP), ("a", R_HP))
_q("frame_b", ("b", L_SH), ("b", R_SH), ("b", L_HP), ("b", R_HP))

# ── 5. Knee geometry (mount / guard / half-guard) ───────────────

# All four knees
_q("knees_all",
   ("a", L_KN), ("a", R_KN), ("b", L_KN), ("b", R_KN))

# A knees vs B hips (mount straddle)
_q("a_knees_b_hips",
   ("a", L_KN), ("a", R_KN), ("b", L_HP), ("b", R_HP))

# B knees vs A hips (reverse straddle)
_q("b_knees_a_hips",
   ("b", L_KN), ("b", R_KN), ("a", L_HP), ("a", R_HP))

# A knees bracket around B torso center
_q("a_straddle_b",
   ("a", L_KN), ("a", R_KN), ("a", (L_HP, R_HP)), ("b", (L_HP, R_HP)))

# B knees bracket around A torso center
_q("b_straddle_a",
   ("b", L_KN), ("b", R_KN), ("b", (L_HP, R_HP)), ("a", (L_HP, R_HP)))

# A knees vs B torso (mount bracket)
_q("a_kn_b_torso",
   ("a", L_KN), ("b", (L_HP, R_HP)), ("a", R_KN), ("b", (L_SH, R_SH)))

# B knees vs A torso
_q("b_kn_a_torso",
   ("b", L_KN), ("a", (L_HP, R_HP)), ("b", R_KN), ("a", (L_SH, R_SH)))

# ── 6. Ankle geometry (guard closure) ───────────────────────────

_q("ankles_all",
   ("a", L_AN), ("a", R_AN), ("b", L_AN), ("b", R_AN))

# A ankles around B torso (guard wrap)
_q("a_ankles_b_torso",
   ("a", L_AN), ("b", (L_HP, R_HP)), ("a", R_AN), ("b", (L_SH, R_SH)))

# B ankles around A torso
_q("b_ankles_a_torso",
   ("b", L_AN), ("a", (L_HP, R_HP)), ("b", R_AN), ("a", (L_SH, R_SH)))

# A ankle closure (guard closure ratio)
_q("a_ankle_closure",
   ("a", L_AN), ("a", R_AN), ("a", (L_HP, R_HP)), ("b", (L_HP, R_HP)))

# B ankle closure
_q("b_ankle_closure",
   ("b", L_AN), ("b", R_AN), ("b", (L_HP, R_HP)), ("a", (L_HP, R_HP)))

# ── 7. Arm engagement ───────────────────────────────────────────

_q("elbows_all",
   ("a", L_EL), ("a", R_EL), ("b", L_EL), ("b", R_EL))

_q("wrists_all",
   ("a", L_WR), ("a", R_WR), ("b", L_WR), ("b", R_WR))

# Arm reach: wrists relative to opponent torso
_q("a_wr_b_torso",
   ("a", L_WR), ("a", R_WR), ("b", (L_SH, R_SH)), ("b", (L_HP, R_HP)))

_q("b_wr_a_torso",
   ("b", L_WR), ("b", R_WR), ("a", (L_SH, R_SH)), ("a", (L_HP, R_HP)))

# ── 8. Head-body ────────────────────────────────────────────────

_q("heads_hips",
   ("a", NOSE), ("a", (L_HP, R_HP)), ("b", NOSE), ("b", (L_HP, R_HP)))

_q("heads_shoulders",
   ("a", NOSE), ("a", (L_SH, R_SH)), ("b", NOSE), ("b", (L_SH, R_SH)))

# ── 9. Mixed cross-body (discriminative for specific positions) ──

# A shoulder-hip line vs B shoulder-hip line (T-shape for SCTR)
_q("a_sh_b_hp_cross",
   ("a", (L_SH, R_SH)), ("b", (L_HP, R_HP)), ("a", (L_HP, R_HP)), ("b", (L_SH, R_SH)))

# Knee-ankle interactions (half guard asymmetry)
_q("kn_an_left",
   ("a", L_KN), ("a", L_AN), ("b", L_KN), ("b", L_AN))

_q("kn_an_right",
   ("a", R_KN), ("a", R_AN), ("b", R_KN), ("b", R_AN))

# Knee-ankle cross-body (leg entanglement)
_q("kn_an_cross",
   ("a", L_KN), ("b", R_AN), ("a", R_KN), ("b", L_AN))


# ── Feature extraction ───────────────────────────────────────────

def _resolve_point(kps, spec):
    """Resolve a landmark spec to (point, confidence).

    spec is either:
      - int: COCO index
      - (int, int): midpoint of two COCO indices
    """
    if isinstance(spec, int):
        return _pt(kps, spec), _conf(kps, spec)
    else:
        i, j = spec
        return _mid(kps, i, j), _mid_conf(kps, i, j)


def extract_cross_ratio_features(kps_a, kps_b):
    """Extract cross-ratio features from two athletes' COCO-17 keypoints.

    Returns:
        features: list of float values
        names: list of feature name strings
    """
    kps_map = {"a": kps_a, "b": kps_b}

    features = []
    names = []

    for q_name, spec1, spec2, spec3, spec4 in QUADRUPLES:
        # Resolve four points
        p1, c1 = _resolve_point(kps_map[spec1[0]], spec1[1])
        p2, c2 = _resolve_point(kps_map[spec2[0]], spec2[1])
        p3, c3 = _resolve_point(kps_map[spec3[0]], spec3[1])
        p4, c4 = _resolve_point(kps_map[spec4[0]], spec4[1])

        # Cross-ratio
        cr = _cross_ratio(p1, p2, p3, p4)
        log_cr = _log_cr(cr)

        # Orientation sign from signed area of triangle (p1, p2, p3)
        area = _signed_area(p1, p2, p3)
        orient = 1.0 if area > 0 else (-1.0 if area < 0 else 0.0)

        # Minimum confidence
        min_c = min(c1, c2, c3, c4)

        features.extend([log_cr, orient, min_c])
        names.extend([
            f"cr_{q_name}_logcr",
            f"cr_{q_name}_orient",
            f"cr_{q_name}_minconf",
        ])

    return features, names


def extract_geo_confidence_weighted(geo_features, geo_names, kps_a, kps_b):
    """Weight geometry features by average keypoint confidence."""
    avg_conf_a = sum(_conf(kps_a, i) for i in range(17)) / 17.0
    avg_conf_b = sum(_conf(kps_b, i) for i in range(17)) / 17.0
    avg_conf = (avg_conf_a + avg_conf_b) / 2.0

    weighted = [f * avg_conf for f in geo_features]
    w_names = [f"cw_{n}" for n in geo_names]
    return weighted, w_names


def extract_confidence_weighted_features(geo_features, cr_features,
                                         geo_names, cr_names,
                                         kps_a, kps_b):
    """Weight features by the confidence of their constituent keypoints.

    Geometry features: weighted by average confidence of both athletes.
    Cross-ratio features: the min_conf is already present; multiply
    log_cr and orient by it so the model can learn to discount.
    """
    weighted, w_names = extract_geo_confidence_weighted(
        geo_features, geo_names, kps_a, kps_b)

    # For cross-ratio features, use per-quadruple min_conf
    i = 0
    while i < len(cr_features):
        log_cr = cr_features[i]
        orient = cr_features[i + 1]
        min_c = cr_features[i + 2]

        base_name = cr_names[i].replace("_logcr", "")
        weighted.extend([log_cr * min_c, orient * min_c, min_c])
        w_names.extend([
            f"cw_{base_name}_logcr",
            f"cw_{base_name}_orient",
            f"cw_{base_name}_minconf",
        ])
        i += 3

    return weighted, w_names


N_QUADRUPLES = len(QUADRUPLES)
N_CR_FEATURES = N_QUADRUPLES * 3
