"""Infer candidate CON tuples and frame constraints from two COCO poses."""

from dataclasses import dataclass, field
from typing import Optional
from data.schema import Pose
from dic.body_parts import LimbRef, AxisDef
from dic.relations import CON
from dic.frames import (
    FacingOpposed, FacingAligned, OnGround, NotOnGround,
    KneeBracket, NotKneeBracket, FrameConstraint,
)
from dic.radicals import ALL_RADICALS, Radical
from tools.axis_reconstruction import (
    ReconstructedAxis, Vec2, kp_to_vec,
    reconstruct_axes, torso_length, torso_center, facing_direction,
    point_to_segment_distance,
    L_HIP, R_HIP, L_ANKLE, R_ANKLE, L_KNEE, R_KNEE,
    NOSE, L_SHOULDER, R_SHOULDER,
    CONFIDENCE_THRESHOLD,
)

CONTACT_THRESHOLD = 0.3
PROXIMITY_THRESHOLD = 0.6
CLOSURE_THRESHOLD = 0.20
KBR_THRESHOLD = 0.6
MISSING_FACING_PENALTY = 0.7


@dataclass
class InferredCON:
    con: CON
    confidence: float
    distance: float     # normalized by avg torso length


@dataclass
class InferredFrame:
    constraint: FrameConstraint
    confidence: float


@dataclass
class PositionMatch:
    radical_name: str
    confidence: float
    matched_contacts: list[InferredCON] = field(default_factory=list)
    matched_frames: list[InferredFrame] = field(default_factory=list)


# ── contact inference ─────────────────────────────────────────────

def infer_contacts(me_pose: Pose, op_pose: Pose) -> list[InferredCON]:
    me_axes = reconstruct_axes(me_pose, "Me")
    op_axes = reconstruct_axes(op_pose, "Op")

    me_tl = torso_length(me_pose)
    op_tl = torso_length(op_pose)
    norm_len = max((me_tl + op_tl) / 2, 1.0)

    contacts = []
    for me_ax in me_axes:
        for op_ax in op_axes:
            me_mid = Vec2(
                (me_ax.origin.x + me_ax.endpoint.x) * 0.5,
                (me_ax.origin.y + me_ax.endpoint.y) * 0.5,
            )
            d_origin = point_to_segment_distance(me_ax.origin, op_ax.origin, op_ax.endpoint)
            d_mid = point_to_segment_distance(me_mid, op_ax.origin, op_ax.endpoint)
            dist = min(d_origin, d_mid)
            contact_pt = me_ax.origin if d_origin <= d_mid else me_mid
            norm_dist = dist / norm_len
            if norm_dist > PROXIMITY_THRESHOLD:
                continue

            cross = op_ax.direction.cross(contact_pt - op_ax.origin)
            helicity = "+" if cross >= 0 else "-"

            if norm_dist < CONTACT_THRESHOLD:
                dist_conf = 1.0 - norm_dist / CONTACT_THRESHOLD
            else:
                dist_conf = 0.5 * (1.0 - (norm_dist - CONTACT_THRESHOLD)
                                   / (PROXIMITY_THRESHOLD - CONTACT_THRESHOLD))
            confidence = dist_conf * min(me_ax.confidence, op_ax.confidence)

            if norm_dist < 0.15:
                depth = "deep"
            elif norm_dist < 0.3:
                depth = "mid"
            else:
                depth = "shallow"

            con = CON(me_ax.axis_def, op_ax.axis_def, depth, helicity)
            contacts.append(InferredCON(con, confidence, norm_dist))

    # Self-contact: foot closure (ankles crossing behind opponent)
    _detect_closure(me_pose, norm_len, contacts)

    contacts.sort(key=lambda c: -c.confidence)
    return contacts


def _detect_closure(pose: Pose, norm_len: float, contacts: list[InferredCON]) -> None:
    """Detect foot closure (ankles locked) — the cycle in the contact graph.
    In 2D, approximated by ankle proximity normalized by torso length.
    LEG_LOOP_CONTAINS(Op.To) is the correct 3D invariant but collapses
    under 2D projection (tested: convex hull, hip angle, leg-axis projection,
    convergence ratio — all show heavy overlap between guard and hooks)."""
    l_ankle = pose.keypoints[L_ANKLE]
    r_ankle = pose.keypoints[R_ANKLE]
    if l_ankle.confidence < CONFIDENCE_THRESHOLD or r_ankle.confidence < CONFIDENCE_THRESHOLD:
        return
    a = Vec2(l_ankle.x, l_ankle.y)
    b = Vec2(r_ankle.x, r_ankle.y)
    ankle_dist = (a - b).length()
    norm_dist = ankle_dist / norm_len
    if norm_dist > CLOSURE_THRESHOLD:
        return

    dist_conf = 1.0 - norm_dist / CLOSURE_THRESHOLD
    confidence = dist_conf * min(l_ankle.confidence, r_ankle.confidence)
    depth = "deep" if norm_dist < 0.10 else "mid"

    fo_l = AxisDef(LimbRef("Me", "Fo", "-"), "Fo", "Kn")
    fo_r = AxisDef(LimbRef("Me", "Fo", "+"), "Fo", "Kn")
    contacts.append(InferredCON(CON(fo_l, fo_r, depth, "0"), confidence, norm_dist))


# ── frame constraint inference ────────────────────────────────────

def infer_frame_constraints(me_pose: Pose, op_pose: Pose) -> list[InferredFrame]:
    constraints: list[InferredFrame] = []

    # facing direction
    me_face = facing_direction(me_pose)
    op_face = facing_direction(op_pose)
    dot = me_face.dot(op_face)
    if dot < -0.3:
        constraints.append(InferredFrame(FacingOpposed(), min(1.0, abs(dot))))
    elif dot > 0.3:
        constraints.append(InferredFrame(FacingAligned(), min(1.0, abs(dot))))

    # ground contact: higher image-y = lower in scene
    me_hip_y = max(me_pose.keypoints[L_HIP].y, me_pose.keypoints[R_HIP].y)
    op_hip_y = max(op_pose.keypoints[L_HIP].y, op_pose.keypoints[R_HIP].y)
    avg_tl = max((torso_length(me_pose) + torso_length(op_pose)) / 2, 1.0)
    y_diff = abs(me_hip_y - op_hip_y)

    if y_diff > 0.2 * avg_tl:
        conf = min(1.0, y_diff / avg_tl)
        if op_hip_y > me_hip_y:
            constraints.append(InferredFrame(OnGround(LimbRef("Op", "Ba")), conf))
            constraints.append(InferredFrame(NotOnGround(LimbRef("Me", "Ba")), conf))
        else:
            constraints.append(InferredFrame(OnGround(LimbRef("Me", "Ba")), conf))
            constraints.append(InferredFrame(NotOnGround(LimbRef("Op", "Ba")), conf))
    else:
        constraints.append(InferredFrame(NotOnGround(LimbRef("Me", "Ba")), 0.5))
        constraints.append(InferredFrame(NotOnGround(LimbRef("Op", "Ba")), 0.5))

    # knee bracket: do Me's knees bracket Op's torso?
    kbr = _infer_knee_bracket(me_pose, op_pose)
    if kbr is not None:
        constraints.append(kbr)

    return constraints


def _infer_knee_bracket(me_pose: Pose, op_pose: Pose) -> InferredFrame | None:
    me_kps = me_pose.keypoints
    op_kps = op_pose.keypoints

    if me_kps[L_KNEE].confidence < 0.3 or me_kps[R_KNEE].confidence < 0.3:
        return None
    if op_kps[L_SHOULDER].confidence < 0.3 or op_kps[R_SHOULDER].confidence < 0.3:
        return None
    if op_kps[L_HIP].confidence < 0.3 or op_kps[R_HIP].confidence < 0.3:
        return None

    op_tl = max(torso_length(op_pose), 1.0)

    op_nose = kp_to_vec(op_kps[NOSE])
    op_sh_l = kp_to_vec(op_kps[L_SHOULDER])
    op_sh_r = kp_to_vec(op_kps[R_SHOULDER])
    op_sh_mid = (op_sh_l + op_sh_r) * 0.5
    op_neck = (op_nose + op_sh_mid) * 0.5
    op_hp_l = kp_to_vec(op_kps[L_HIP])
    op_hp_r = kp_to_vec(op_kps[R_HIP])
    op_hp_mid = (op_hp_l + op_hp_r) * 0.5

    head_targets = [op_nose, op_sh_l, op_sh_r, op_sh_mid, op_neck]
    hip_targets = [op_hp_l, op_hp_r, op_hp_mid]

    me_kn_l = kp_to_vec(me_kps[L_KNEE])
    me_kn_r = kp_to_vec(me_kps[R_KNEE])

    def min_dist(pt, targets):
        return min((pt - t).length() for t in targets)

    kn_l_head = min_dist(me_kn_l, head_targets) / op_tl
    kn_l_hip = min_dist(me_kn_l, hip_targets) / op_tl
    kn_r_head = min_dist(me_kn_r, head_targets) / op_tl
    kn_r_hip = min_dist(me_kn_r, hip_targets) / op_tl

    cost_a = max(kn_l_head, kn_r_hip)
    cost_b = max(kn_r_head, kn_l_hip)
    best_cost = min(cost_a, cost_b)

    ref = LimbRef("Op", "To", "")
    if best_cost < KBR_THRESHOLD:
        conf = min(1.0, 1.0 - best_cost / KBR_THRESHOLD)
        return InferredFrame(KneeBracket(ref), conf)
    else:
        conf = min(1.0, (best_cost - KBR_THRESHOLD) / KBR_THRESHOLD)
        return InferredFrame(NotKneeBracket(ref), conf)


# ── radical matching ──────────────────────────────────────────────

def match_radical(
    contacts: list[InferredCON],
    frames: list[InferredFrame],
    radicals: dict[str, Radical] | None = None,
) -> list[PositionMatch]:
    if radicals is None:
        radicals = ALL_RADICALS

    candidates = []
    for name, rad in radicals.items():
        contact_hits = _match_all_contacts(rad.contacts, contacts)
        if contact_hits is None:
            continue

        if _has_forbidden_contact(rad.forbidden_contacts, contacts):
            continue

        if _has_bilateral_forbidden(rad.forbidden_bilateral, contacts):
            continue

        hard_reqs = tuple(
            r for r in rad.frame_constraints
            if isinstance(r, (OnGround, NotOnGround, KneeBracket, NotKneeBracket))
        )
        hard_hits = _match_all_grounds(hard_reqs, frames)
        if hard_hits is None:
            continue

        facing_reqs = tuple(
            r for r in rad.frame_constraints if isinstance(r, (FacingOpposed, FacingAligned))
        )
        facing_hits = _match_found_frames(facing_reqs, frames)

        frame_hits = hard_hits + facing_hits
        n_con = len(contact_hits)
        n_frame = len(frame_hits)
        n_facing_missing = len(facing_reqs) - len(facing_hits)
        avg_conf = (
            sum(c.confidence for c in contact_hits) / n_con if n_con > 0 else 0.0
        )
        specificity = n_con + n_frame
        score = 10 * n_con + 5 * n_frame + avg_conf + specificity

        if frame_hits:
            score *= min(f.confidence for f in frame_hits)
        if n_facing_missing > 0:
            score *= MISSING_FACING_PENALTY ** n_facing_missing

        candidates.append(PositionMatch(name, score, contact_hits, frame_hits))

    candidates.sort(key=lambda m: -m.confidence)
    return candidates


def _match_all_contacts(
    required: tuple[CON, ...],
    inferred: list[InferredCON],
) -> Optional[list[InferredCON]]:
    """Each required contact must match a distinct inferred contact."""
    hits = []
    used: set[int] = set()
    for req in required:
        best = None
        best_score = 0.0
        best_idx = None
        for i, cand in enumerate(inferred):
            if i in used:
                continue
            s = _con_similarity(req, cand.con)
            w = s * cand.confidence
            if w > best_score:
                best_score = w
                best = cand
                best_idx = i
        if best is None or best_score <= CON_MATCH_THRESHOLD:
            return None
        used.add(best_idx)
        hits.append(InferredCON(best.con, best_score, best.distance))
    return hits


def _match_all_grounds(
    required: tuple[FrameConstraint, ...],
    inferred: list[InferredFrame],
) -> Optional[list[InferredFrame]]:
    hits = []
    for req in required:
        best = _find_frame(req, inferred)
        if best is None:
            return None
        hits.append(best)
    return hits


def _match_found_frames(
    required: tuple[FrameConstraint, ...],
    inferred: list[InferredFrame],
) -> list[InferredFrame]:
    hits = []
    for req in required:
        best = _find_frame(req, inferred)
        if best is not None:
            hits.append(best)
    return hits


def _has_forbidden_contact(
    forbidden: tuple[CON, ...],
    inferred: list[InferredCON],
) -> bool:
    for req in forbidden:
        if _find_contact(req, inferred) is not None:
            return True
    return False


def _has_bilateral_forbidden(
    bilateral: tuple[CON, ...],
    inferred: list[InferredCON],
) -> bool:
    if not bilateral:
        return False
    used: set[int] = set()
    for req in bilateral:
        found = False
        best_idx = None
        best_score = 0.0
        for i, cand in enumerate(inferred):
            if i in used:
                continue
            s = _con_similarity(req, cand.con)
            w = s * cand.confidence
            if w > best_score:
                best_score = w
                best_idx = i
        if best_idx is not None and best_score > CON_MATCH_THRESHOLD:
            used.add(best_idx)
            found = True
        if not found:
            return False
    return True


CON_MATCH_THRESHOLD = 0.02


def _find_frame(req: FrameConstraint, inferred: list[InferredFrame]) -> Optional[InferredFrame]:
    for inf in inferred:
        if type(inf.constraint) != type(req):
            continue
        if isinstance(req, (FacingOpposed, FacingAligned)):
            return inf
        if isinstance(req, (OnGround, NotOnGround)):
            if (inf.constraint.part.part == req.part.part
                    and inf.constraint.part.role == req.part.role):
                return inf
        if isinstance(req, (KneeBracket, NotKneeBracket)):
            if (inf.constraint.part.part == req.part.part
                    and inf.constraint.part.role == req.part.role):
                return inf
    return None


def _find_contact(req: CON, candidates: list[InferredCON]) -> Optional[InferredCON]:
    best = None
    best_score = 0.0
    for cand in candidates:
        s = _con_similarity(req, cand.con)
        w = s * cand.confidence
        if w > best_score:
            best_score = w
            best = cand
    if best and best_score > CON_MATCH_THRESHOLD:
        return InferredCON(best.con, best_score, best.distance)
    return None


def _con_similarity(required: CON, candidate: CON) -> float:
    if candidate.attacker.limb_ref.role != required.attacker.limb_ref.role:
        return 0.0
    if candidate.axis.limb_ref.role != required.axis.limb_ref.role:
        return 0.0

    att_part = required.attacker.limb_ref.part
    ax_part = required.axis.limb_ref.part
    if candidate.attacker.limb_ref.part != att_part:
        return 0.0
    if candidate.axis.limb_ref.part != ax_part:
        return 0.0

    score = 0.6
    if required.attacker.limb_ref.sign == candidate.attacker.limb_ref.sign:
        score += 0.1
    if required.axis.limb_ref.sign == candidate.axis.limb_ref.sign:
        score += 0.1
    if required.helicity == candidate.helicity:
        score += 0.2
    return score
