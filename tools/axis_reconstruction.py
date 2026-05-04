"""Reconstruct BLISP limb axes from COCO 17-keypoint poses."""

import math
from dataclasses import dataclass
from data.schema import Pose, Keypoint
from dic.body_parts import LimbRef, AxisDef

# COCO keypoint indices
NOSE = 0
L_SHOULDER, R_SHOULDER = 5, 6
L_ELBOW, R_ELBOW = 7, 8
L_WRIST, R_WRIST = 9, 10
L_HIP, R_HIP = 11, 12
L_KNEE, R_KNEE = 13, 14
L_ANKLE, R_ANKLE = 15, 16

CONFIDENCE_THRESHOLD = 0.3


@dataclass
class Vec2:
    x: float
    y: float

    def __add__(self, other):
        return Vec2(self.x + other.x, self.y + other.y)

    def __sub__(self, other):
        return Vec2(self.x - other.x, self.y - other.y)

    def __mul__(self, s):
        return Vec2(self.x * s, self.y * s)

    def length(self):
        return math.sqrt(self.x ** 2 + self.y ** 2)

    def normalized(self):
        l = self.length()
        return Vec2(self.x / l, self.y / l) if l > 1e-10 else Vec2(0.0, 0.0)

    def dot(self, other):
        return self.x * other.x + self.y * other.y

    def cross(self, other):
        return self.x * other.y - self.y * other.x


@dataclass
class ReconstructedAxis:
    limb_ref: LimbRef
    axis_def: AxisDef
    origin: Vec2        # distal endpoint position
    endpoint: Vec2      # proximal endpoint position
    direction: Vec2     # unit vector distal -> proximal
    length: float
    confidence: float


def kp_to_vec(kp: Keypoint) -> Vec2:
    return Vec2(kp.x, kp.y)


# (part, sign, blisp_from, blisp_to, coco_distal, coco_proximal, coco_mid)
_LIMB_DEFS = [
    ("Le", "-", "Fo", "Hp", L_ANKLE,  L_HIP,      L_KNEE),
    ("Le", "+", "Fo", "Hp", R_ANKLE,  R_HIP,      R_KNEE),
    ("Ar", "-", "Wr", "Sh", L_WRIST,  L_SHOULDER, L_ELBOW),
    ("Ar", "+", "Wr", "Sh", R_WRIST,  R_SHOULDER, R_ELBOW),
]


def reconstruct_axes(pose: Pose, role: str) -> list[ReconstructedAxis]:
    kps = pose.keypoints
    axes = []

    for part, sign, from_pt, to_pt, d_idx, p_idx, m_idx in _LIMB_DEFS:
        conf = min(kps[d_idx].confidence, kps[p_idx].confidence, kps[m_idx].confidence)
        if conf < CONFIDENCE_THRESHOLD:
            continue
        origin = kp_to_vec(kps[d_idx])
        endpoint = kp_to_vec(kps[p_idx])
        diff = endpoint - origin
        length = diff.length()
        if length < 1e-10:
            continue
        ref = LimbRef(role, part, sign)
        axes.append(ReconstructedAxis(
            ref, AxisDef(ref, from_pt, to_pt),
            origin, endpoint, diff.normalized(), length, conf,
        ))

    # Torso axis
    conf = min(kps[i].confidence for i in (L_SHOULDER, R_SHOULDER, L_HIP, R_HIP))
    if conf >= CONFIDENCE_THRESHOLD:
        hip_mid = (kp_to_vec(kps[L_HIP]) + kp_to_vec(kps[R_HIP])) * 0.5
        sh_mid = (kp_to_vec(kps[L_SHOULDER]) + kp_to_vec(kps[R_SHOULDER])) * 0.5
        diff = sh_mid - hip_mid
        length = diff.length()
        if length > 1e-10:
            ref = LimbRef(role, "To")
            axes.append(ReconstructedAxis(
                ref, AxisDef(ref, "Hp", "Sh"),
                hip_mid, sh_mid, diff.normalized(), length, conf,
            ))

    return axes


def torso_length(pose: Pose) -> float:
    kps = pose.keypoints
    hip_mid = (kp_to_vec(kps[L_HIP]) + kp_to_vec(kps[R_HIP])) * 0.5
    sh_mid = (kp_to_vec(kps[L_SHOULDER]) + kp_to_vec(kps[R_SHOULDER])) * 0.5
    return (sh_mid - hip_mid).length()


def torso_center(pose: Pose) -> Vec2:
    kps = pose.keypoints
    pts = [kps[i] for i in (L_SHOULDER, R_SHOULDER, L_HIP, R_HIP)]
    return Vec2(sum(p.x for p in pts) / 4, sum(p.y for p in pts) / 4)


def facing_direction(pose: Pose) -> Vec2:
    """Estimate 2D facing direction from the shoulder-line normal oriented toward the nose."""
    kps = pose.keypoints
    sh_l = kp_to_vec(kps[L_SHOULDER])
    sh_r = kp_to_vec(kps[R_SHOULDER])
    nose = kp_to_vec(kps[NOSE])

    sh_line = sh_r - sh_l
    n1 = Vec2(-sh_line.y, sh_line.x)
    n2 = Vec2(sh_line.y, -sh_line.x)

    sh_mid = (sh_l + sh_r) * 0.5
    to_nose = nose - sh_mid

    if n1.dot(to_nose) >= n2.dot(to_nose):
        return n1.normalized()
    return n2.normalized()


def point_to_segment_distance(point: Vec2, seg_a: Vec2, seg_b: Vec2) -> float:
    ab = seg_b - seg_a
    ap = point - seg_a
    ab_len_sq = ab.x ** 2 + ab.y ** 2
    if ab_len_sq < 1e-10:
        return ap.length()
    t = max(0.0, min(1.0, ap.dot(ab) / ab_len_sq))
    closest = Vec2(seg_a.x + t * ab.x, seg_a.y + t * ab.y)
    return (point - closest).length()
