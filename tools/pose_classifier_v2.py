"""Pose-to-radical classifier v2: body-frame algebraic features.

Explicit body-frame geometry for each athlete, relative frame coordinates,
orientation/facing features, and position-specific discriminators.
No contact/proximity heuristics. Strict video-level split.
"""

import json
import math
import sys
import time
import warnings
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

warnings.filterwarnings("ignore")

# ── Label maps ───────────────────────────────────────────────────

FAMILY_MAP = {
    "mount1": "TOP_PIN", "mount2": "TOP_PIN",
    "side_control1": "TOP_PIN", "side_control2": "TOP_PIN",
    "back1": "BACK_CTRL", "back2": "BACK_CTRL",
    "closed_guard1": "GUARD", "closed_guard2": "GUARD",
    "open_guard1": "GUARD", "open_guard2": "GUARD",
    "half_guard1": "GUARD", "half_guard2": "GUARD",
    "5050_guard": "GUARD",
    "turtle1": "TURTLE", "turtle2": "TURTLE",
    "standing": "STANDING",
    "takedown1": "STANDING", "takedown2": "STANDING",
}

FINE_MAP = {
    "mount1": "MNT", "mount2": "MNT",
    "side_control1": "SCTR", "side_control2": "SCTR",
    "back1": "BCTR", "back2": "BCTR",
    "closed_guard1": "CGRD", "closed_guard2": "CGRD",
    "open_guard1": "OGRD", "open_guard2": "OGRD",
    "half_guard1": "HGRD", "half_guard2": "HGRD",
    "5050_guard": "5050",
    "turtle1": "TRTL", "turtle2": "TRTL",
    "standing": "STND",
    "takedown1": "TKDN", "takedown2": "TKDN",
}


# ── Vec2 math ────────────────────────────────────────────────────

def v2(x, y):
    return np.array([x, y], dtype=np.float64)


def vmid(a, b):
    return (a + b) * 0.5


def vlen(a):
    return np.linalg.norm(a)


def vnorm(a):
    n = vlen(a)
    return a / n if n > 1e-8 else v2(0, 0)


def vcross(a, b):
    return float(a[0] * b[1] - a[1] * b[0])


def vdot(a, b):
    return float(np.dot(a, b))


def vangle(a):
    return math.atan2(a[1], a[0])


def angle_diff(a, b):
    d = a - b
    while d > math.pi: d -= 2 * math.pi
    while d < -math.pi: d += 2 * math.pi
    return d


# ── COCO indices ─────────────────────────────────────────────────

NOSE = 0
L_EYE, R_EYE = 1, 2
L_EAR, R_EAR = 3, 4
L_SH, R_SH = 5, 6
L_EL, R_EL = 7, 8
L_WR, R_WR = 9, 10
L_HP, R_HP = 11, 12
L_KN, R_KN = 13, 14
L_AN, R_AN = 15, 16


# ── Body frame ───────────────────────────────────────────────────

class BodyFrame:
    """Algebraic body frame from COCO keypoints."""

    def __init__(self, kps):
        self.kps = kps  # 17 x [x, y, conf]

        # Key points as vectors
        self.l_sh = v2(kps[L_SH][0], kps[L_SH][1])
        self.r_sh = v2(kps[R_SH][0], kps[R_SH][1])
        self.l_hp = v2(kps[L_HP][0], kps[L_HP][1])
        self.r_hp = v2(kps[R_HP][0], kps[R_HP][1])
        self.nose = v2(kps[NOSE][0], kps[NOSE][1])

        # Midpoints
        self.S = vmid(self.l_sh, self.r_sh)  # shoulder midpoint
        self.H = vmid(self.l_hp, self.r_hp)  # hip midpoint
        self.C = vmid(self.S, self.H)         # body center

        # Torso axis: H -> S (proximal to distal, hip to shoulder)
        self.torso_vec = self.S - self.H
        self.torso_len = max(vlen(self.torso_vec), 1.0)
        self.torso_dir = vnorm(self.torso_vec)

        # Torso angle (from positive x-axis)
        self.torso_angle = vangle(self.torso_vec)

        # Lateral shoulder axis: left_shoulder -> right_shoulder
        self.sh_axis = self.r_sh - self.l_sh
        self.sh_dir = vnorm(self.sh_axis)
        self.sh_width = vlen(self.sh_axis)

        # Hip axis: left_hip -> right_hip
        self.hp_axis = self.r_hp - self.l_hp
        self.hp_dir = vnorm(self.hp_axis)
        self.hp_width = vlen(self.hp_axis)

        # Cross-product signs (handedness)
        # torso x shoulder_axis: positive = normal 2D frame
        self.torso_sh_cross = vcross(self.torso_dir, self.sh_dir)
        self.torso_hp_cross = vcross(self.torso_dir, self.hp_dir)

        # Facing direction proxy: perpendicular to torso in the direction of the "front"
        # Front = direction from torso midline toward nose (if visible)
        if kps[NOSE][2] > 0.2:
            nose_off = self.nose - self.C
            # Project nose offset onto the plane perpendicular to torso
            perp = nose_off - self.torso_dir * vdot(nose_off, self.torso_dir)
            self.facing_dir = vnorm(perp)
            self.facing_conf = min(vlen(perp) / self.torso_len, 1.0)
        else:
            # Fallback: use cross product of torso with vertical to guess front
            self.facing_dir = v2(-self.torso_dir[1], self.torso_dir[0])
            self.facing_conf = 0.3

        # Body-frame coordinate system: torso_dir = "up", lateral = perpendicular
        self.frame_up = self.torso_dir
        self.frame_lateral = v2(-self.torso_dir[1], self.torso_dir[0])

    def to_local(self, world_pt):
        """Transform a world point into this body's local frame.
        Returns (longitudinal, lateral) coordinates normalized by torso length."""
        offset = world_pt - self.C
        longi = vdot(offset, self.frame_up) / self.torso_len
        lat = vdot(offset, self.frame_lateral) / self.torso_len
        return longi, lat

    def kp_vec(self, idx):
        return v2(self.kps[idx][0], self.kps[idx][1])

    def kp_conf(self, idx):
        return self.kps[idx][2]


# ── Feature extraction ───────────────────────────────────────────

def extract_body_frame_features(bf, prefix):
    """Features from a single athlete's body frame."""
    f = []
    n = []

    # Torso angle
    f.append(bf.torso_angle)
    n.append(f"{prefix}_torso_angle")

    # Torso length (raw, for scale)
    f.append(bf.torso_len)
    n.append(f"{prefix}_torso_len")

    # Shoulder and hip widths normalized
    f.append(bf.sh_width / bf.torso_len)
    n.append(f"{prefix}_sh_width_norm")
    f.append(bf.hp_width / bf.torso_len)
    n.append(f"{prefix}_hp_width_norm")

    # Cross-product signs (frame handedness)
    f.append(bf.torso_sh_cross)
    n.append(f"{prefix}_torso_sh_cross")
    f.append(bf.torso_hp_cross)
    n.append(f"{prefix}_torso_hp_cross")

    # Facing direction angle
    f.append(vangle(bf.facing_dir))
    n.append(f"{prefix}_facing_angle")
    f.append(bf.facing_conf)
    n.append(f"{prefix}_facing_conf")

    # All 17 keypoints in local frame
    for i in range(17):
        longi, lat = bf.to_local(bf.kp_vec(i))
        conf = bf.kp_conf(i)
        f.extend([longi, lat, conf])
        n.extend([f"{prefix}_kp{i}_longi", f"{prefix}_kp{i}_lat", f"{prefix}_kp{i}_conf"])

    # Knee positions relative to hip line (for mount/guard detection)
    l_kn_local = bf.to_local(bf.kp_vec(L_KN))
    r_kn_local = bf.to_local(bf.kp_vec(R_KN))
    f.extend([l_kn_local[0], l_kn_local[1], r_kn_local[0], r_kn_local[1]])
    n.extend([f"{prefix}_l_knee_longi", f"{prefix}_l_knee_lat",
              f"{prefix}_r_knee_longi", f"{prefix}_r_knee_lat"])

    # Ankle positions relative to hip line
    l_an_local = bf.to_local(bf.kp_vec(L_AN))
    r_an_local = bf.to_local(bf.kp_vec(R_AN))
    f.extend([l_an_local[0], l_an_local[1], r_an_local[0], r_an_local[1]])
    n.extend([f"{prefix}_l_ankle_longi", f"{prefix}_l_ankle_lat",
              f"{prefix}_r_ankle_longi", f"{prefix}_r_ankle_lat"])

    # Leg compactness
    l_leg_len = (vlen(bf.kp_vec(L_HP) - bf.kp_vec(L_KN)) +
                 vlen(bf.kp_vec(L_KN) - bf.kp_vec(L_AN))) / bf.torso_len
    r_leg_len = (vlen(bf.kp_vec(R_HP) - bf.kp_vec(R_KN)) +
                 vlen(bf.kp_vec(R_KN) - bf.kp_vec(R_AN))) / bf.torso_len
    f.extend([l_leg_len, r_leg_len])
    n.extend([f"{prefix}_l_leg_len_norm", f"{prefix}_r_leg_len_norm"])

    # Visibility counts
    vis_upper = sum(1 for i in range(0, 11) if bf.kp_conf(i) > 0.3)
    vis_lower = sum(1 for i in range(11, 17) if bf.kp_conf(i) > 0.3)
    f.extend([vis_upper, vis_lower])
    n.extend([f"{prefix}_vis_upper", f"{prefix}_vis_lower"])

    return f, n


def extract_relative_frame_features(bf_a, bf_b):
    """Pairwise body-frame features between athlete A (me) and B (op)."""
    f = []
    n = []

    avg_tl = (bf_a.torso_len + bf_b.torso_len) / 2

    # ── 2. Facing/orientation ──

    # Torso angle difference
    torso_angle_diff = angle_diff(bf_a.torso_angle, bf_b.torso_angle)
    f.append(torso_angle_diff)
    n.append("torso_angle_diff")

    # Facing direction dot product: +1 = same direction, -1 = opposed
    facing_dot = vdot(bf_a.facing_dir, bf_b.facing_dir)
    f.append(facing_dot)
    n.append("facing_dot")

    # Facing direction cross product sign
    facing_cross = vcross(bf_a.facing_dir, bf_b.facing_dir)
    f.append(facing_cross)
    n.append("facing_cross")

    # Shoulder axis alignment
    sh_dot = vdot(bf_a.sh_dir, bf_b.sh_dir)
    f.append(sh_dot)
    n.append("sh_axis_dot")

    # Hip axis alignment
    hp_dot = vdot(bf_a.hp_dir, bf_b.hp_dir)
    f.append(hp_dot)
    n.append("hp_axis_dot")

    # Torso axis alignment
    torso_dot = vdot(bf_a.torso_dir, bf_b.torso_dir)
    f.append(torso_dot)
    n.append("torso_axis_dot")

    # Torso axis cross product (perpendicularity)
    torso_cross = vcross(bf_a.torso_dir, bf_b.torso_dir)
    f.append(torso_cross)
    n.append("torso_axis_cross")

    # Relative handedness: do both frames have same chirality?
    handedness_a = 1.0 if bf_a.torso_sh_cross > 0 else -1.0
    handedness_b = 1.0 if bf_b.torso_sh_cross > 0 else -1.0
    f.append(handedness_a * handedness_b)
    n.append("relative_handedness")

    # ── 3. Relative frame coordinates ──

    # B's key points in A's frame
    b_center_in_a = bf_a.to_local(bf_b.C)
    b_sh_in_a = bf_a.to_local(bf_b.S)
    b_hp_in_a = bf_a.to_local(bf_b.H)
    f.extend([b_center_in_a[0], b_center_in_a[1]])
    n.extend(["b_center_in_a_longi", "b_center_in_a_lat"])
    f.extend([b_sh_in_a[0], b_sh_in_a[1]])
    n.extend(["b_sh_in_a_longi", "b_sh_in_a_lat"])
    f.extend([b_hp_in_a[0], b_hp_in_a[1]])
    n.extend(["b_hp_in_a_longi", "b_hp_in_a_lat"])

    # B's knees and ankles in A's frame
    for idx, label in [(L_KN, "b_l_kn"), (R_KN, "b_r_kn"), (L_AN, "b_l_an"), (R_AN, "b_r_an")]:
        pt = bf_a.to_local(bf_b.kp_vec(idx))
        f.extend([pt[0], pt[1]])
        n.extend([f"{label}_in_a_longi", f"{label}_in_a_lat"])

    # A's key points in B's frame
    a_center_in_b = bf_b.to_local(bf_a.C)
    a_sh_in_b = bf_b.to_local(bf_a.S)
    a_hp_in_b = bf_b.to_local(bf_a.H)
    f.extend([a_center_in_b[0], a_center_in_b[1]])
    n.extend(["a_center_in_b_longi", "a_center_in_b_lat"])
    f.extend([a_sh_in_b[0], a_sh_in_b[1]])
    n.extend(["a_sh_in_b_longi", "a_sh_in_b_lat"])
    f.extend([a_hp_in_b[0], a_hp_in_b[1]])
    n.extend(["a_hp_in_b_longi", "a_hp_in_b_lat"])

    # A's knees and ankles in B's frame
    for idx, label in [(L_KN, "a_l_kn"), (R_KN, "a_r_kn"), (L_AN, "a_l_an"), (R_AN, "a_r_an")]:
        pt = bf_b.to_local(bf_a.kp_vec(idx))
        f.extend([pt[0], pt[1]])
        n.extend([f"{label}_in_b_longi", f"{label}_in_b_lat"])

    # ── 4. Dominance/frame relations ──

    # Vertical dominance: A over B? (image y: higher = lower in scene)
    # Positive = A is above B in image (A is on top)
    vert_dom = (bf_b.C[1] - bf_a.C[1]) / avg_tl
    f.append(vert_dom)
    n.append("vert_dominance")

    # Center distance
    center_dist = vlen(bf_a.C - bf_b.C) / avg_tl
    f.append(center_dist)
    n.append("center_dist_norm")

    # Hip-to-hip distance
    hip_dist = vlen(bf_a.H - bf_b.H) / avg_tl
    f.append(hip_dist)
    n.append("hip_dist_norm")

    # Shoulder-to-shoulder distance
    sh_dist = vlen(bf_a.S - bf_b.S) / avg_tl
    f.append(sh_dist)
    n.append("sh_dist_norm")

    # Centerline overlap: how much do torso axes overlap laterally?
    # Project B's center onto A's lateral axis
    b_off = bf_b.C - bf_a.C
    lat_offset_a = vdot(b_off, bf_a.frame_lateral) / avg_tl
    longi_offset_a = vdot(b_off, bf_a.frame_up) / avg_tl
    f.extend([lat_offset_a, longi_offset_a])
    n.extend(["b_lat_offset_in_a", "b_longi_offset_in_a"])

    a_off = bf_a.C - bf_b.C
    lat_offset_b = vdot(a_off, bf_b.frame_lateral) / avg_tl
    longi_offset_b = vdot(a_off, bf_b.frame_up) / avg_tl
    f.extend([lat_offset_b, longi_offset_b])
    n.extend(["a_lat_offset_in_b", "a_longi_offset_in_b"])

    # Hip-over-torso: is A's hip above B's shoulder midpoint?
    a_hp_over_b_sh = (bf_b.S[1] - bf_a.H[1]) / avg_tl
    f.append(a_hp_over_b_sh)
    n.append("a_hp_over_b_sh")

    # Shoulder-over-torso: is A's shoulder above B's hip?
    a_sh_over_b_hp = (bf_b.H[1] - bf_a.S[1]) / avg_tl
    f.append(a_sh_over_b_hp)
    n.append("a_sh_over_b_hp")

    # Torso length ratio
    f.append(bf_a.torso_len / bf_b.torso_len)
    n.append("torso_len_ratio")

    # ── 5. BCTR-specific features ──

    # Same-direction torso frames (BCTR: attacker behind defender, same direction)
    # torso_dot > 0 means same direction
    # Already have torso_axis_dot above

    # Attacker chest aligned to defender back: A's facing dir dot with A-to-B direction
    ab_dir = vnorm(bf_b.C - bf_a.C) if vlen(bf_b.C - bf_a.C) > 1e-6 else v2(0, 0)
    a_facing_toward_b = vdot(bf_a.facing_dir, ab_dir)
    f.append(a_facing_toward_b)
    n.append("a_facing_toward_b")

    b_facing_toward_a = vdot(bf_b.facing_dir, -ab_dir)
    f.append(b_facing_toward_a)
    n.append("b_facing_toward_a")

    # A behind B in B's frame: a_center_in_b longitudinal < 0 means behind
    # (already computed above as a_center_in_b)

    # A's chest near B's back line: A's shoulder midpoint in B's frame, negative longitudinal
    # (already computed as a_sh_in_b)

    # Are they NOT face-to-face? facing_dot > 0 means same direction (not face-to-face)
    # Already have facing_dot

    # ── 6. MNT-specific features ──

    # Top hips centered over bottom torso
    # Use A as top: project A's hip midpoint into B's lateral frame
    a_hp_in_b_frame = bf_b.to_local(bf_a.H)
    f.extend([a_hp_in_b_frame[0], a_hp_in_b_frame[1]])
    n.extend(["a_hp_in_b_longi", "a_hp_in_b_lat"])

    # Top knees outside bottom torso line (bracket)
    a_l_kn_in_b = bf_b.to_local(bf_a.kp_vec(L_KN))
    a_r_kn_in_b = bf_b.to_local(bf_a.kp_vec(R_KN))
    # Knee lateral spread in B's frame
    knee_lat_spread = abs(a_l_kn_in_b[1] - a_r_kn_in_b[1])
    f.append(knee_lat_spread)
    n.append("a_knee_lat_spread_in_b")

    # Are knees on opposite sides of B's centerline?
    knee_bracket = a_l_kn_in_b[1] * a_r_kn_in_b[1]  # negative = opposite sides
    f.append(knee_bracket)
    n.append("a_knee_bracket_sign_in_b")

    # Bottom supine proxy: B's torso near horizontal, B below A
    # torso angle near ±90° from vertical
    b_torso_from_vert = abs(angle_diff(bf_b.torso_angle, math.pi / 2))
    f.append(b_torso_from_vert)
    n.append("b_torso_from_vertical")

    # ── 7. SCTR-specific features ──

    # Torso axes perpendicular: abs(torso_cross) near 1
    # Already have torso_axis_cross

    # Top body lateral in bottom frame: a_center_in_b lateral magnitude
    # Already computed

    # Top chest crosses bottom torso: A's shoulder line intersects B's torso axis
    # Approximate: A's shoulder midpoint lateral offset in B's frame
    a_sh_lat_in_b = bf_b.to_local(bf_a.S)[1]
    f.append(abs(a_sh_lat_in_b))
    n.append("a_sh_lat_magnitude_in_b")

    # ── 8. GUARD-specific features ──

    # One athlete between opponent legs
    # B's center between A's knees (A = guard player, B = passer)
    b_center_between_a_knees_lat = bf_a.to_local(bf_b.C)[1]
    a_l_kn_lat = bf_a.to_local(bf_a.kp_vec(L_KN))[1]
    a_r_kn_lat = bf_a.to_local(bf_a.kp_vec(R_KN))[1]
    knee_min_lat = min(a_l_kn_lat, a_r_kn_lat)
    knee_max_lat = max(a_l_kn_lat, a_r_kn_lat)
    b_between_a_knees = 1.0 if knee_min_lat < b_center_between_a_knees_lat < knee_max_lat else 0.0
    f.append(b_between_a_knees)
    n.append("b_between_a_knees")

    # Similarly: A's center between B's knees
    a_center_between_b_knees_lat = bf_b.to_local(bf_a.C)[1]
    b_l_kn_lat = bf_b.to_local(bf_b.kp_vec(L_KN))[1]
    b_r_kn_lat = bf_b.to_local(bf_b.kp_vec(R_KN))[1]
    bkn_min = min(b_l_kn_lat, b_r_kn_lat)
    bkn_max = max(b_l_kn_lat, b_r_kn_lat)
    a_between_b_knees = 1.0 if bkn_min < a_center_between_b_knees_lat < bkn_max else 0.0
    f.append(a_between_b_knees)
    n.append("a_between_b_knees")

    # Leg enclosure: are A's ankles near B's torso from both sides?
    a_l_an_in_b = bf_b.to_local(bf_a.kp_vec(L_AN))
    a_r_an_in_b = bf_b.to_local(bf_a.kp_vec(R_AN))
    ankle_bracket_b = a_l_an_in_b[1] * a_r_an_in_b[1]
    f.append(ankle_bracket_b)
    n.append("a_ankle_bracket_sign_in_b")

    b_l_an_in_a = bf_a.to_local(bf_b.kp_vec(L_AN))
    b_r_an_in_a = bf_a.to_local(bf_b.kp_vec(R_AN))
    ankle_bracket_a = b_l_an_in_a[1] * b_r_an_in_a[1]
    f.append(ankle_bracket_a)
    n.append("b_ankle_bracket_sign_in_a")

    # Ankle-to-ankle distance for each athlete (closure)
    a_ankle_dist = vlen(bf_a.kp_vec(L_AN) - bf_a.kp_vec(R_AN)) / avg_tl
    b_ankle_dist = vlen(bf_b.kp_vec(L_AN) - bf_b.kp_vec(R_AN)) / avg_tl
    f.extend([a_ankle_dist, b_ankle_dist])
    n.extend(["a_ankle_dist_norm", "b_ankle_dist_norm"])

    return f, n


def extract_all_features(kps_me, kps_op):
    """Full feature vector for a pair of poses."""
    bf_me = BodyFrame(kps_me)
    bf_op = BodyFrame(kps_op)

    f_me, n_me = extract_body_frame_features(bf_me, "me")
    f_op, n_op = extract_body_frame_features(bf_op, "op")
    f_rel, n_rel = extract_relative_frame_features(bf_me, bf_op)

    all_f = f_me + f_op + f_rel
    all_n = n_me + n_op + n_rel
    return all_f, all_n


# ── Data loading ─────────────────────────────────────────────────

def load_dataset():
    with open("data/raw/annotations.json") as f:
        raw = json.load(f)

    samples = []
    for item in raw:
        pos = item["position"]
        if pos not in FAMILY_MAP:
            continue
        p1 = item.get("pose1")
        p2 = item.get("pose2")
        if not p1 or len(p1) != 17 or not p2 or len(p2) != 17:
            continue

        suffix = pos[-1] if pos[-1] in "12" else "0"
        if suffix == "2":
            me_kps, op_kps = p2, p1
        else:
            me_kps, op_kps = p1, p2

        samples.append({
            "image_id": item["image"],
            "video": item["image"][:2],
            "frame": item.get("frame", 0),
            "position": pos,
            "family": FAMILY_MAP[pos],
            "fine": FINE_MAP[pos],
            "me_kps": me_kps,
            "op_kps": op_kps,
        })
    return samples


def video_split(samples):
    test_videos = {"01", "07", "10", "15"}
    val_videos = {"02", "06"}
    train, val, test = [], [], []
    for s in samples:
        if s["video"] in test_videos:
            test.append(s)
        elif s["video"] in val_videos:
            val.append(s)
        else:
            train.append(s)
    return train, val, test


def featurize(samples):
    X, y_family, y_fine = [], [], []
    valid = []
    for i, s in enumerate(samples):
        try:
            feats, _ = extract_all_features(s["me_kps"], s["op_kps"])
            if any(math.isnan(f) or math.isinf(f) for f in feats):
                continue
            X.append(feats)
            y_family.append(s["family"])
            y_fine.append(s["fine"])
            valid.append(s)
        except Exception:
            continue
    return np.array(X, dtype=np.float32), y_family, y_fine, valid


# ── Main ─────────────────────────────────────────────────────────

def main():
    from sklearn.linear_model import LogisticRegression
    from sklearn.svm import LinearSVC
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.neural_network import MLPClassifier
    from sklearn.preprocessing import StandardScaler, LabelEncoder
    from sklearn.metrics import (
        accuracy_score, f1_score, classification_report,
        confusion_matrix, top_k_accuracy_score,
    )

    print("Loading dataset...")
    samples = load_dataset()
    print(f"Total samples: {len(samples)}")

    family_counts = Counter(s["family"] for s in samples)
    fine_counts = Counter(s["fine"] for s in samples)
    print(f"\nCoarse families:")
    for k, v in sorted(family_counts.items(), key=lambda x: -x[1]):
        print(f"  {k:12s}: {v:6d}")
    print(f"\nFine labels:")
    for k, v in sorted(fine_counts.items(), key=lambda x: -x[1]):
        print(f"  {k:6s}: {v:6d}")

    # Split
    print(f"\nSplitting by video...")
    train, val, test = video_split(samples)
    for name, split in [("Train", train), ("Val", val), ("Test", test)]:
        videos = sorted(set(s["video"] for s in split))
        fc = Counter(s["family"] for s in split)
        finec = Counter(s["fine"] for s in split)
        print(f"  {name}: {len(split)} samples, videos={videos}")
        print(f"    Coarse: {dict(sorted(fc.items()))}")
        print(f"    Fine:   {dict(sorted(finec.items()))}")

    # Featurize
    print(f"\nExtracting body-frame features...")
    X_train, y_train_fam, y_train_fine, train_valid = featurize(train)
    X_val, y_val_fam, y_val_fine, val_valid = featurize(val)
    X_test, y_test_fam, y_test_fine, test_valid = featurize(test)

    _, feature_names = extract_all_features(samples[0]["me_kps"], samples[0]["op_kps"])
    print(f"  Features: {X_train.shape[1]}")
    print(f"  Train: {X_train.shape[0]}  Val: {X_val.shape[0]}  Test: {X_test.shape[0]}")

    # Scale
    scaler = StandardScaler()
    X_train_s = np.nan_to_num(scaler.fit_transform(X_train), 0)
    X_val_s = np.nan_to_num(scaler.transform(X_val), 0)
    X_test_s = np.nan_to_num(scaler.transform(X_test), 0)

    # Encode labels
    all_fam_labels = sorted(set(y_train_fam) | set(y_val_fam) | set(y_test_fam))
    all_fine_labels = sorted(set(y_train_fine) | set(y_val_fine) | set(y_test_fine))
    le_fam = LabelEncoder()
    le_fam.fit(all_fam_labels)
    le_fine = LabelEncoder()
    le_fine.fit(all_fine_labels)

    y_train_fam_enc = le_fam.transform(y_train_fam)
    y_test_fam_enc = le_fam.transform(y_test_fam)
    y_train_fine_enc = le_fine.transform(y_train_fine)
    y_test_fine_enc = le_fine.transform(y_test_fine)

    models = {
        "LogisticRegression": LogisticRegression(max_iter=2000, C=1.0, multi_class="multinomial"),
        "LinearSVC": LinearSVC(max_iter=2000, C=1.0, dual=False),
        "HistGradientBoosting": HistGradientBoostingClassifier(max_iter=500, max_depth=8, learning_rate=0.05, random_state=42),
        "MLP": MLPClassifier(hidden_layer_sizes=(256, 128), max_iter=500, early_stopping=True, validation_fraction=0.15, random_state=42),
    }

    # ── Run on BOTH coarse and fine labels ──

    for label_type, y_tr, y_te, y_va, le, label_list in [
        ("COARSE (5 families)", y_train_fam, y_test_fam, y_val_fam, le_fam, all_fam_labels),
        ("FINE (8+ radicals)", y_train_fine, y_test_fine, y_val_fine, le_fine, all_fine_labels),
    ]:
        print(f"\n\n{'#'*70}")
        print(f"  {label_type}")
        print(f"{'#'*70}")

        y_tr_enc = le.transform(y_tr)

        results = {}
        for name, model in models.items():
            print(f"\n  Training {name}...")
            t0 = time.time()

            if name == "MLP":
                model.fit(X_train_s, y_tr_enc)
                y_va_pred = le.inverse_transform(model.predict(X_val_s))
                y_te_pred = le.inverse_transform(model.predict(X_test_s))
            else:
                model.fit(X_train_s, y_tr)
                y_va_pred = model.predict(X_val_s)
                y_te_pred = model.predict(X_test_s)

            elapsed = time.time() - t0

            va_acc = accuracy_score(y_va, y_va_pred)
            va_f1 = f1_score(y_va, y_va_pred, average="macro")
            te_acc = accuracy_score(y_te, y_te_pred)
            te_f1 = f1_score(y_te, y_te_pred, average="macro")

            print(f"  {elapsed:.1f}s  Val: {va_acc:.1%} / {va_f1:.3f}  Test: {te_acc:.1%} / {te_f1:.3f}")

            results[name] = {
                "va_acc": va_acc, "va_f1": va_f1,
                "te_acc": te_acc, "te_f1": te_f1,
                "preds": y_te_pred,
            }

        # Best model detail
        best_name = max(results, key=lambda k: results[k]["te_acc"])
        best = results[best_name]
        print(f"\n  BEST: {best_name} ({best['te_acc']:.1%})")
        print(f"\n  Per-class (test):")
        print(classification_report(y_te, best["preds"], digits=3, zero_division=0))

        cm_labels = sorted(set(y_te) | set(best["preds"]))
        cm = confusion_matrix(y_te, best["preds"], labels=cm_labels)
        print(f"  Confusion matrix:")
        header = f"  {'':>12s}" + "".join(f"{l:>10s}" for l in cm_labels)
        print(header)
        for i, lbl in enumerate(cm_labels):
            print(f"  {lbl:>12s}" + "".join(f"{cm[i][j]:>10d}" for j in range(len(cm_labels))))

        # ── Feature importance for LogReg (coarse only) ──
        if label_type.startswith("COARSE"):
            lr = models["LogisticRegression"]
            if hasattr(lr, "coef_"):
                print(f"\n  LogReg coefficient inspection: BACK_CTRL vs TOP_PIN")
                bctr_idx = list(lr.classes_).index("BACK_CTRL") if "BACK_CTRL" in lr.classes_ else None
                tpin_idx = list(lr.classes_).index("TOP_PIN") if "TOP_PIN" in lr.classes_ else None
                if bctr_idx is not None and tpin_idx is not None:
                    diff = lr.coef_[bctr_idx] - lr.coef_[tpin_idx]
                    ranked = sorted(zip(feature_names, diff), key=lambda x: -abs(x[1]))
                    print(f"\n  Top 30 features separating BACK_CTRL from TOP_PIN:")
                    print(f"  {'Feature':>40s} {'Coef diff':>10s}  {'Direction'}")
                    for fname, d in ranked[:30]:
                        direction = "-> BCTR" if d > 0 else "-> TPIN"
                        print(f"  {fname:>40s} {d:>+10.4f}  {direction}")

        # Summary table
        print(f"\n  {'Model':<25s} {'Val Acc':>8s} {'Test Acc':>9s} {'Test F1':>8s}")
        print(f"  {'-'*25} {'-'*8} {'-'*9} {'-'*8}")
        for nm in models:
            r = results[nm]
            print(f"  {nm:<25s} {r['va_acc']:>8.1%} {r['te_acc']:>9.1%} {r['te_f1']:>8.3f}")

    # Save
    output_path = "data/algebra_eval/pose_classifier_v2_results.json"
    print(f"\nResults saved to {output_path}")
    with open(output_path, "w") as f:
        json.dump({"note": "see stdout for full results"}, f)


if __name__ == "__main__":
    main()
