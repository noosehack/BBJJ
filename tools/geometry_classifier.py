"""Geometry-based radical classifier for the live demo.

Loads the serialized body-frame model and provides:
  1. Classification from learned geometry features
  2. Structured geometry explanation (body frames, orientation, dominance)
  3. Debug geometry for visualization (torso axes, centerlines, etc.)
"""

import json
import math
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import joblib

from tools.pose_classifier_v2 import (
    BodyFrame, extract_all_features, extract_relative_frame_features,
    vdot, vcross, vlen, vnorm, vangle, angle_diff, v2,
)

MODEL_DIR = Path(__file__).resolve().parent.parent / "models_geometry"

_model = None
_scaler = None
_feature_names = None
_label_encoder = None
_model_type = None


def _load():
    global _model, _scaler, _feature_names, _label_encoder, _model_type
    if _model is not None:
        return
    _model = joblib.load(MODEL_DIR / "model.joblib")
    _scaler = joblib.load(MODEL_DIR / "scaler.joblib")
    _feature_names = joblib.load(MODEL_DIR / "feature_names.joblib")
    _label_encoder = joblib.load(MODEL_DIR / "label_encoder.joblib")
    config_path = MODEL_DIR / "config.json"
    if config_path.exists():
        with open(config_path) as f:
            cfg = json.load(f)
        _model_type = cfg.get("classifier_source", "learned_geometry")
    else:
        _model_type = "learned_geometry"


def _extract_combined_features(kps_a, kps_b):
    """Extract geo + ordered_cr confidence-weighted features (635 total)."""
    from tools.cross_ratio_features import extract_geo_confidence_weighted
    from tools.ordered_cross_ratio import (
        extract_ordered_cr_features, confidence_weight_ordered_cr,
    )
    geo, geo_n = extract_all_features(kps_a, kps_b)
    ocr, ocr_n = extract_ordered_cr_features(kps_a, kps_b)
    gcw, gcw_n = extract_geo_confidence_weighted(geo, geo_n, kps_a, kps_b)
    ocrw, ocrw_n = confidence_weight_ordered_cr(ocr, ocr_n)
    return gcw + ocrw, gcw_n + ocrw_n


RADICAL_EXPLANATIONS = {
    "MNT": "Mount -- top athlete astride bottom torso, vertical dominance, hips centered over opponent.",
    "BCTR": "Back Control -- chest-to-back alignment, same-direction torso axes, posterior control.",
    "SCTR": "Side Control -- perpendicular torso geometry, lateral chest across bottom torso.",
    "CGRD": "Closed Guard -- bottom athlete wraps legs around top athlete, frontal enclosure.",
    "OGRD": "Open Guard -- bottom athlete faces top with open leg frame, no closed enclosure.",
    "HGRD": "Half Guard -- asymmetric leg entanglement, one leg trapped between opponent's.",
    "TRTL": "Turtle -- compact curled defender, attacker on top/behind with posterior geometry.",
    "STND": "Standing -- upright athletes, no ground dominance.",
    "5050": "50/50 Guard -- symmetric leg entanglement, mirrored positions.",
    "TKDN": "Takedown -- transition from standing, one athlete driving the other down.",
}


@dataclass
class BodyFrameDebug:
    """Geometry data for one athlete, serializable for the UI."""
    shoulder_mid: tuple[float, float]
    hip_mid: tuple[float, float]
    center: tuple[float, float]
    torso_vec: tuple[float, float]
    torso_angle_deg: float
    sh_axis: tuple[float, float]
    hp_axis: tuple[float, float]
    facing_dir: tuple[float, float]
    facing_conf: float
    torso_len: float
    sh_width: float
    hp_width: float


@dataclass
class OrientationDebug:
    """Pairwise orientation geometry."""
    torso_axis_dot: float
    torso_axis_cross: float
    facing_dot: float
    sh_axis_dot: float
    hp_axis_dot: float
    orientation_label: str
    vert_dominance: float
    top_label: str
    center_dist: float
    hip_dist: float


@dataclass
class RadicalCondition:
    """One interpretable condition checked for a radical."""
    name: str
    value: float
    threshold: str
    met: bool
    description: str


@dataclass
class GeometryResult:
    """Full geometry classification result."""
    radical: str
    confidence: float
    explanation: str
    classifier_source: str  # "learned_geometry" or "deterministic_rules"
    probabilities: dict[str, float]
    body_frame_a: BodyFrameDebug
    body_frame_b: BodyFrameDebug
    orientation: OrientationDebug
    conditions: list[RadicalCondition]
    pov_label: str


def _bf_debug(bf: BodyFrame) -> BodyFrameDebug:
    return BodyFrameDebug(
        shoulder_mid=(float(bf.S[0]), float(bf.S[1])),
        hip_mid=(float(bf.H[0]), float(bf.H[1])),
        center=(float(bf.C[0]), float(bf.C[1])),
        torso_vec=(float(bf.torso_vec[0]), float(bf.torso_vec[1])),
        torso_angle_deg=float(math.degrees(bf.torso_angle)),
        sh_axis=(float(bf.sh_axis[0]), float(bf.sh_axis[1])),
        hp_axis=(float(bf.hp_axis[0]), float(bf.hp_axis[1])),
        facing_dir=(float(bf.facing_dir[0]), float(bf.facing_dir[1])),
        facing_conf=float(bf.facing_conf),
        torso_len=float(bf.torso_len),
        sh_width=float(bf.sh_width),
        hp_width=float(bf.hp_width),
    )


def _orientation_debug(bf_a: BodyFrame, bf_b: BodyFrame) -> OrientationDebug:
    avg_tl = (bf_a.torso_len + bf_b.torso_len) / 2

    torso_dot = float(vdot(bf_a.torso_dir, bf_b.torso_dir))
    torso_cross = float(vcross(bf_a.torso_dir, bf_b.torso_dir))
    facing_dot = float(vdot(bf_a.facing_dir, bf_b.facing_dir))
    sh_dot = float(vdot(bf_a.sh_dir, bf_b.sh_dir))
    hp_dot = float(vdot(bf_a.hp_dir, bf_b.hp_dir))

    if torso_dot > 0.5:
        orient = "same_direction"
    elif torso_dot < -0.5:
        orient = "opposed"
    elif abs(torso_cross) > 0.7:
        orient = "perpendicular"
    else:
        orient = "oblique"

    vert_dom = float((bf_b.C[1] - bf_a.C[1]) / avg_tl)
    if vert_dom > 0.3:
        top_label = "A_on_top"
    elif vert_dom < -0.3:
        top_label = "B_on_top"
    else:
        top_label = "level"

    return OrientationDebug(
        torso_axis_dot=round(torso_dot, 3),
        torso_axis_cross=round(torso_cross, 3),
        facing_dot=round(facing_dot, 3),
        sh_axis_dot=round(sh_dot, 3),
        hp_axis_dot=round(hp_dot, 3),
        orientation_label=orient,
        vert_dominance=round(vert_dom, 3),
        top_label=top_label,
        center_dist=round(float(vlen(bf_a.C - bf_b.C) / avg_tl), 3),
        hip_dist=round(float(vlen(bf_a.H - bf_b.H) / avg_tl), 3),
    )


def _check_radical_conditions(radical: str, bf_a: BodyFrame, bf_b: BodyFrame, orient: OrientationDebug) -> list[RadicalCondition]:
    """Check interpretable geometry conditions for the predicted radical."""
    conditions = []
    avg_tl = (bf_a.torso_len + bf_b.torso_len) / 2

    if radical == "MNT":
        conditions.append(RadicalCondition(
            "top_dominance", orient.vert_dominance, "> 0.2",
            orient.vert_dominance > 0.2,
            "Top athlete above bottom athlete",
        ))
        conditions.append(RadicalCondition(
            "torso_over_torso", orient.center_dist, "< 2.0",
            orient.center_dist < 2.0,
            "Bodies stacked vertically",
        ))
        a_hp_in_b = bf_b.to_local(bf_a.H)
        conditions.append(RadicalCondition(
            "hips_centered", abs(a_hp_in_b[1]), "< 0.8",
            abs(a_hp_in_b[1]) < 0.8,
            "Top hips centered over bottom torso",
        ))
        conditions.append(RadicalCondition(
            "facing_opposed", orient.facing_dot, "< 0.0",
            orient.facing_dot < 0.0,
            "Athletes facing each other (opposed)",
        ))

    elif radical == "BCTR":
        conditions.append(RadicalCondition(
            "same_direction", orient.torso_axis_dot, "> 0.3",
            orient.torso_axis_dot > 0.3,
            "Torso axes aligned (same direction)",
        ))
        conditions.append(RadicalCondition(
            "sh_aligned", orient.sh_axis_dot, "> 0.3",
            orient.sh_axis_dot > 0.3,
            "Shoulder axes aligned",
        ))
        conditions.append(RadicalCondition(
            "hp_aligned", orient.hp_axis_dot, "> 0.3",
            orient.hp_axis_dot > 0.3,
            "Hip axes aligned",
        ))
        ab_dir = vnorm(bf_b.C - bf_a.C) if vlen(bf_b.C - bf_a.C) > 1e-6 else v2(0, 0)
        facing_toward = float(vdot(bf_a.facing_dir, ab_dir))
        conditions.append(RadicalCondition(
            "chest_to_back", facing_toward, "> 0.0",
            facing_toward > 0.0,
            "Attacker chest faces defender back",
        ))

    elif radical == "SCTR":
        conditions.append(RadicalCondition(
            "perpendicular", abs(orient.torso_axis_cross), "> 0.4",
            abs(orient.torso_axis_cross) > 0.4,
            "Torso axes perpendicular",
        ))
        conditions.append(RadicalCondition(
            "top_dominance", orient.vert_dominance, "> 0.1",
            orient.vert_dominance > 0.1,
            "Top athlete dominant",
        ))
        a_sh_in_b_lat = bf_b.to_local(bf_a.S)[1]
        conditions.append(RadicalCondition(
            "lateral_chest", abs(a_sh_in_b_lat), "> 0.3",
            abs(a_sh_in_b_lat) > 0.3,
            "Top chest crosses bottom torso laterally",
        ))

    elif radical == "CGRD":
        conditions.append(RadicalCondition(
            "frontal", orient.facing_dot, "< -0.2",
            orient.facing_dot < -0.2,
            "Athletes facing each other",
        ))
        b_between = _b_between_a_knees(bf_a, bf_b)
        conditions.append(RadicalCondition(
            "between_legs", b_between, "= 1.0",
            b_between > 0.5,
            "Top athlete between bottom legs",
        ))
        a_ankle_dist = float(vlen(bf_a.kp_vec(15) - bf_a.kp_vec(16)) / avg_tl)
        conditions.append(RadicalCondition(
            "ankles_close", a_ankle_dist, "< 1.0",
            a_ankle_dist < 1.0,
            "Guard player ankles close (enclosure)",
        ))

    elif radical == "OGRD":
        conditions.append(RadicalCondition(
            "frontal", orient.facing_dot, "< 0.0",
            orient.facing_dot < 0.0,
            "Athletes facing each other",
        ))
        b_between = _b_between_a_knees(bf_a, bf_b)
        conditions.append(RadicalCondition(
            "between_legs", b_between, "= 1.0",
            b_between > 0.5,
            "Top athlete in guard player's leg frame",
        ))

    elif radical == "HGRD":
        conditions.append(RadicalCondition(
            "frontal_or_oblique", orient.facing_dot, "< 0.3",
            orient.facing_dot < 0.3,
            "Athletes roughly facing",
        ))

    elif radical == "TRTL":
        conditions.append(RadicalCondition(
            "compact_defender", orient.center_dist, "< 2.5",
            orient.center_dist < 2.5,
            "Athletes close together",
        ))
        conditions.append(RadicalCondition(
            "posterior_control", orient.torso_axis_dot, "> 0.0",
            orient.torso_axis_dot > 0.0,
            "Attacker behind/above defender",
        ))

    elif radical == "STND":
        both_upright = (
            abs(math.degrees(bf_a.torso_angle) - 90) < 45 and
            abs(math.degrees(bf_b.torso_angle) - 90) < 45
        )
        conditions.append(RadicalCondition(
            "upright", 1.0 if both_upright else 0.0, "= 1.0",
            both_upright,
            "Both athletes roughly upright",
        ))
        conditions.append(RadicalCondition(
            "no_ground_dom", abs(orient.vert_dominance), "< 0.5",
            abs(orient.vert_dominance) < 0.5,
            "No clear top/bottom dominance",
        ))

    return conditions


def _b_between_a_knees(bf_a, bf_b):
    b_lat = bf_a.to_local(bf_b.C)[1]
    l_kn_lat = bf_a.to_local(bf_a.kp_vec(13))[1]
    r_kn_lat = bf_a.to_local(bf_a.kp_vec(14))[1]
    mn, mx = min(l_kn_lat, r_kn_lat), max(l_kn_lat, r_kn_lat)
    return 1.0 if mn < b_lat < mx else 0.0


def classify(kps_a: list, kps_b: list, pov_label: str = "") -> GeometryResult:
    """Run geometry classification on two athletes' keypoints.

    kps_a, kps_b: 17 x [x, y, confidence]
    Returns GeometryResult with classification + explanation.
    """
    _load()

    bf_a = BodyFrame(kps_a)
    bf_b = BodyFrame(kps_b)

    if _model_type == "geo_ordered_cr_cw":
        feats, _ = _extract_combined_features(kps_a, kps_b)
    else:
        feats, _ = extract_all_features(kps_a, kps_b)
    feats_arr = np.array([feats], dtype=np.float32)
    feats_scaled = np.nan_to_num(_scaler.transform(feats_arr), 0)

    proba_raw = _model.predict_proba(feats_scaled)[0]
    classes = list(_label_encoder.classes_)
    proba = {c: round(float(p), 4) for c, p in zip(classes, proba_raw)}

    pred_idx = int(np.argmax(proba_raw))
    radical = classes[pred_idx]
    confidence = float(proba_raw[pred_idx])

    orient = _orientation_debug(bf_a, bf_b)
    conditions = _check_radical_conditions(radical, bf_a, bf_b, orient)
    for c in conditions:
        c.met = bool(c.met)
        c.value = float(c.value)

    return GeometryResult(
        radical=radical,
        confidence=round(confidence, 4),
        explanation=RADICAL_EXPLANATIONS.get(radical, "Unknown position."),
        classifier_source=_model_type or "learned_geometry",
        probabilities=proba,
        body_frame_a=_bf_debug(bf_a),
        body_frame_b=_bf_debug(bf_b),
        orientation=orient,
        conditions=conditions,
        pov_label=pov_label,
    )


def classify_both_pov(kps_a: list, kps_b: list) -> GeometryResult:
    """Try both POV assignments, return the one with higher confidence."""
    r_ab = classify(kps_a, kps_b, pov_label="A=Me")
    r_ba = classify(kps_b, kps_a, pov_label="B=Me")
    return r_ab if r_ab.confidence >= r_ba.confidence else r_ba
