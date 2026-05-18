"""Similarity-invariant cross-body features + combined extraction pipeline.

Replaces dropped body-frame projections with features invariant under
2D similarity transforms (rotation + uniform scale):
  - Cross-body distance ratios (22 features)
  - Signed areas of cross-body triangles (11 features)
  - Cross-body angle features via center line (12 features)
  - Encirclement ratios (6 features)
"""

import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.pose_classifier_v2 import (
    BodyFrame, v2, vlen, vnorm, vdot, vcross,
    L_SH, R_SH, L_HP, R_HP, L_KN, R_KN, L_AN, R_AN, NOSE,
    extract_all_features,
)
from tools.cross_ratio_features import (
    extract_cross_ratio_features, extract_geo_confidence_weighted,
)
from tools.ordered_cross_ratio import (
    extract_ordered_cr_features, confidence_weight_ordered_cr,
)
from tools.feature_invariance import filter_invariant


def _signed_area(p1, p2, p3):
    return float((p2[0] - p1[0]) * (p3[1] - p1[1]) -
                 (p2[1] - p1[1]) * (p3[0] - p1[0]))


def extract_cross_body_features(kps_me, kps_op):
    """New similarity-invariant cross-body features (51 total)."""
    bf_me = BodyFrame(kps_me)
    bf_op = BodyFrame(kps_op)
    avg_tl = (bf_me.torso_len + bf_op.torso_len) / 2
    avg_tl2 = avg_tl * avg_tl

    f, n = [], []

    # ── 1. Cross-body distance ratios (22) ──
    dist_pairs = [
        (bf_me.kp_vec(L_KN), bf_op.H, "me_lkn_op_hp"),
        (bf_me.kp_vec(R_KN), bf_op.H, "me_rkn_op_hp"),
        (bf_me.kp_vec(L_AN), bf_op.C, "me_lan_op_C"),
        (bf_me.kp_vec(R_AN), bf_op.C, "me_ran_op_C"),
        (bf_me.kp_vec(L_KN), bf_op.C, "me_lkn_op_C"),
        (bf_me.kp_vec(R_KN), bf_op.C, "me_rkn_op_C"),
        (bf_me.S, bf_op.H, "me_sh_op_hp"),
        (bf_me.H, bf_op.S, "me_hp_op_sh"),
        (bf_me.H, bf_op.H, "me_hp_op_hp"),
        (bf_me.kp_vec(L_KN), bf_op.kp_vec(L_KN), "me_lkn_op_lkn"),
        (bf_me.kp_vec(L_KN), bf_op.kp_vec(R_KN), "me_lkn_op_rkn"),
        (bf_me.kp_vec(R_KN), bf_op.kp_vec(L_KN), "me_rkn_op_lkn"),
        (bf_me.kp_vec(R_KN), bf_op.kp_vec(R_KN), "me_rkn_op_rkn"),
        (bf_me.kp_vec(L_AN), bf_op.kp_vec(L_AN), "me_lan_op_lan"),
        (bf_me.kp_vec(R_AN), bf_op.kp_vec(R_AN), "me_ran_op_ran"),
        (bf_me.kp_vec(L_AN), bf_op.kp_vec(R_AN), "me_lan_op_ran"),
        (bf_me.kp_vec(R_AN), bf_op.kp_vec(L_AN), "me_ran_op_lan"),
        (bf_me.nose, bf_op.C, "me_nose_op_C"),
        (bf_me.C, bf_op.nose, "me_C_op_nose"),
        (bf_me.kp_vec(L_AN), bf_op.H, "me_lan_op_hp"),
        (bf_me.kp_vec(R_AN), bf_op.H, "me_ran_op_hp"),
        (bf_me.S, bf_op.S, "me_sh_op_sh"),
    ]
    for p1, p2, label in dist_pairs:
        f.append(float(vlen(p1 - p2) / avg_tl))
        n.append(f"xd_{label}")

    # ── 2. Signed areas — rotation-invariant bracket detection (11) ──
    triangles = [
        (bf_me.kp_vec(L_KN), bf_me.kp_vec(R_KN), bf_op.C, "me_kn_bracket_op_C"),
        (bf_me.kp_vec(L_KN), bf_me.kp_vec(R_KN), bf_op.H, "me_kn_bracket_op_H"),
        (bf_me.kp_vec(L_AN), bf_me.kp_vec(R_AN), bf_op.C, "me_an_bracket_op_C"),
        (bf_me.kp_vec(L_AN), bf_me.kp_vec(R_AN), bf_op.H, "me_an_bracket_op_H"),
        (bf_op.kp_vec(L_KN), bf_op.kp_vec(R_KN), bf_me.C, "op_kn_bracket_me_C"),
        (bf_op.kp_vec(L_KN), bf_op.kp_vec(R_KN), bf_me.H, "op_kn_bracket_me_H"),
        (bf_op.kp_vec(L_AN), bf_op.kp_vec(R_AN), bf_me.C, "op_an_bracket_me_C"),
        (bf_me.S, bf_me.H, bf_op.C, "me_torso_op_C"),
        (bf_op.S, bf_op.H, bf_me.C, "op_torso_me_C"),
        (bf_me.kp_vec(L_SH), bf_me.kp_vec(R_SH), bf_op.C, "me_sh_bracket_op_C"),
        (bf_op.kp_vec(L_SH), bf_op.kp_vec(R_SH), bf_me.C, "op_sh_bracket_me_C"),
    ]
    for p1, p2, p3, label in triangles:
        f.append(_signed_area(p1, p2, p3) / avg_tl2)
        n.append(f"sa_{label}")

    # ── 3. Cross-body angles via center line (12) ──
    cl_vec = bf_op.C - bf_me.C
    cl_dir = vnorm(cl_vec) if vlen(cl_vec) > 1e-6 else v2(1, 0)

    angle_pairs = [
        (bf_me.torso_dir, "me_torso_vs_center"),
        (bf_op.torso_dir, "op_torso_vs_center"),
        (bf_me.facing_dir, "me_facing_vs_center"),
        (bf_op.facing_dir, "op_facing_vs_center"),
        (bf_me.sh_dir, "me_sh_vs_center"),
        (bf_op.sh_dir, "op_sh_vs_center"),
    ]
    for vec, label in angle_pairs:
        f.append(float(vdot(vec, cl_dir)))
        n.append(f"xa_dot_{label}")
        f.append(float(vcross(vec, cl_dir)))
        n.append(f"xa_cross_{label}")

    # ── 4. Encirclement ratios (6) ──
    def _enc(p1, p2, target):
        d12 = vlen(p1 - p2)
        if d12 < 1e-6:
            return 0.0
        return float((vlen(p1 - target) + vlen(p2 - target)) / d12)

    enc_triples = [
        (bf_me.kp_vec(L_KN), bf_me.kp_vec(R_KN), bf_op.C, "me_kn_encircle_op_C"),
        (bf_me.kp_vec(L_KN), bf_me.kp_vec(R_KN), bf_op.H, "me_kn_encircle_op_H"),
        (bf_me.kp_vec(L_AN), bf_me.kp_vec(R_AN), bf_op.C, "me_an_encircle_op_C"),
        (bf_me.kp_vec(L_AN), bf_me.kp_vec(R_AN), bf_op.H, "me_an_encircle_op_H"),
        (bf_op.kp_vec(L_KN), bf_op.kp_vec(R_KN), bf_me.C, "op_kn_encircle_me_C"),
        (bf_op.kp_vec(L_AN), bf_op.kp_vec(R_AN), bf_me.C, "op_an_encircle_me_C"),
    ]
    for p1, p2, target, label in enc_triples:
        f.append(_enc(p1, p2, target))
        n.append(f"enc_{label}")

    return f, n


def _cw_naked_cr(features, names):
    """Confidence-weight naked CR: multiply log_cr and orient by min_conf."""
    w, wn = [], []
    for i in range(0, len(features), 3):
        lc, o, mc = features[i], features[i + 1], features[i + 2]
        w.extend([lc * mc, o * mc, mc])
        wn.extend([f"cw_{names[i]}", f"cw_{names[i+1]}", names[i + 2]])
    return w, wn


def _cw_cross_body(features, names, kps_me, kps_op):
    """Confidence-weight cross-body features by avg keypoint confidence."""
    avg_c = sum(kps_me[i][2] for i in range(17))
    avg_c += sum(kps_op[i][2] for i in range(17))
    avg_c /= 34.0
    w = [f * avg_c for f in features]
    wn = [f"cw_{n}" for n in names]
    return w, wn


def extract_invariant_feature_set(kps_me, kps_op, keep_camera=False):
    """Complete invariant feature extraction pipeline.

    1. Existing geo + ordered CR (confidence-weighted), filtered to invariant only
    2. Naked cross-ratio features (confidence-weighted)
    3. New cross-body features (confidence-weighted)

    keep_camera: if True, also keep camera_conditioned_2d features
                 (vert_dominance, absolute angles). These work for most
                 real-world photos but break under camera rotation.

    Returns (features, names) or (None, None) on extraction failure.
    """
    geo, geo_n = extract_all_features(kps_me, kps_op)
    ocr, ocr_n = extract_ordered_cr_features(kps_me, kps_op)

    if any(math.isnan(v) or math.isinf(v) for v in geo):
        return None, None
    if any(math.isnan(v) or math.isinf(v) for v in ocr):
        return None, None

    gcw, gcw_n = extract_geo_confidence_weighted(geo, geo_n, kps_me, kps_op)
    ocrw, ocrw_n = confidence_weight_ordered_cr(ocr, ocr_n)
    inv_f, inv_n = filter_invariant(gcw + ocrw, gcw_n + ocrw_n,
                                    keep_camera=keep_camera)

    ncr, ncr_n = extract_cross_ratio_features(kps_me, kps_op)
    ncr_cw, ncr_cw_n = _cw_naked_cr(ncr, ncr_n)

    xb, xb_n = extract_cross_body_features(kps_me, kps_op)
    xb_cw, xb_cw_n = _cw_cross_body(xb, xb_n, kps_me, kps_op)

    all_f = inv_f + ncr_cw + xb_cw
    all_n = inv_n + ncr_cw_n + xb_cw_n
    return all_f, all_n
