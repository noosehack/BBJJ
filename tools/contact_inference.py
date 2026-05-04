"""Infer candidate CON tuples and frame constraints from two COCO poses."""

from dataclasses import dataclass, field
from typing import Optional
from data.schema import Pose
from dic.body_parts import LimbRef, AxisDef
from dic.relations import CON
from dic.frames import FacingOpposed, FacingAligned, OnGround, NotOnGround, FrameConstraint
from dic.radicals import ALL_RADICALS, Radical
from tools.axis_reconstruction import (
    ReconstructedAxis, Vec2,
    reconstruct_axes, torso_length, torso_center, facing_direction,
    point_to_segment_distance,
    L_HIP, R_HIP,
)

CONTACT_THRESHOLD = 0.3
PROXIMITY_THRESHOLD = 0.6


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
            dist = point_to_segment_distance(me_ax.origin, op_ax.origin, op_ax.endpoint)
            norm_dist = dist / norm_len
            if norm_dist > PROXIMITY_THRESHOLD:
                continue

            cross = op_ax.direction.cross(me_ax.origin - op_ax.origin)
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

    contacts.sort(key=lambda c: -c.confidence)
    return contacts


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
        else:
            constraints.append(InferredFrame(OnGround(LimbRef("Me", "Ba")), conf))

    return constraints


# ── radical matching ──────────────────────────────────────────────

def match_radical(
    contacts: list[InferredCON],
    frames: list[InferredFrame],
    radicals: dict[str, Radical] | None = None,
) -> list[PositionMatch]:
    if radicals is None:
        radicals = ALL_RADICALS

    matches = []
    for name, rad in radicals.items():
        frame_hits, frame_score = _score_frames(rad.frame_constraints, frames)
        contact_hits, contact_score = _score_contacts(rad.contacts, contacts)

        overall = contact_score * frame_score
        if overall > 0.001:
            matches.append(PositionMatch(name, overall, contact_hits, frame_hits))

    matches.sort(key=lambda m: -m.confidence)
    return matches


def _score_frames(
    required: tuple[FrameConstraint, ...],
    inferred: list[InferredFrame],
) -> tuple[list[InferredFrame], float]:
    hits = []
    score = 1.0
    for req in required:
        best = _find_frame(req, inferred)
        if best:
            hits.append(best)
            score *= best.confidence
        else:
            score *= 0.1
    return hits, score


def _find_frame(req: FrameConstraint, inferred: list[InferredFrame]) -> Optional[InferredFrame]:
    for inf in inferred:
        if type(inf.constraint) != type(req):
            continue
        if isinstance(req, (FacingOpposed, FacingAligned)):
            return inf
        if isinstance(req, (OnGround, NotOnGround)):
            if inf.constraint.part.part == req.part.part:
                return inf
    return None


def _score_contacts(
    required: tuple[CON, ...],
    inferred: list[InferredCON],
) -> tuple[list[InferredCON], float]:
    hits = []
    score = 1.0
    for req in required:
        best = _find_contact(req, inferred)
        if best:
            hits.append(best)
            score *= best.confidence
        else:
            score *= 0.05
    if len(required) > 0:
        score = score ** (1.0 / len(required))
    return hits, score


def _find_contact(req: CON, candidates: list[InferredCON]) -> Optional[InferredCON]:
    best = None
    best_score = 0.0
    for cand in candidates:
        s = _con_similarity(req, cand.con)
        w = s * cand.confidence
        if w > best_score:
            best_score = w
            best = cand
    if best and best_score > 0.05:
        return InferredCON(best.con, best_score, best.distance)
    return None


def _con_similarity(required: CON, candidate: CON) -> float:
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
