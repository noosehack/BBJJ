"""Failure audit of radical validation pipeline.

Separates failures into:
  A. Bad tag — dataset label appears wrong or too coarse
  B. Keypoint failure — required body parts missing, swapped, occluded
  C. 2D observability failure — relation true but unobservable from monocular keypoints
  D. Algebra too strict — constraint not actually necessary for tagged position
  E. Algebra too weak — false radicals match because radical lacks distinguishing constraint
  F. OGRD family issue — open guard is not a single radical
"""

import json
import math
import random
import sys
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from data.schema import Annotation, Pose, Keypoint
from data.label_map import VICOS_TO_BLISP, normalize, blisp_label
from dic.radicals import ALL_RADICALS, Radical, OGRD_SUBTYPES
from dic.relations import CON
from dic.frames import FacingOpposed, FacingAligned, OnGround, NotOnGround, FrameConstraint
from tools.contact_inference import (
    infer_contacts, infer_frame_constraints,
    InferredCON, InferredFrame,
    _con_similarity, _find_frame, _find_contact,
    CON_MATCH_THRESHOLD, FORBIDDEN_MATCH_THRESHOLD,
    CONTACT_THRESHOLD, PROXIMITY_THRESHOLD,
)
from tools.axis_reconstruction import (
    reconstruct_axes, torso_length, torso_center, facing_direction,
    point_to_segment_distance,
    kp_to_vec, Vec2, CONFIDENCE_THRESHOLD,
    L_HIP, R_HIP, L_ANKLE, R_ANKLE, L_KNEE, R_KNEE,
    L_SHOULDER, R_SHOULDER, L_WRIST, R_WRIST, NOSE,
    L_ELBOW, R_ELBOW,
)
from tools.radical_validation import (
    validate_radical, validate_sample, SampleValidation,
    RadicalValidation, ConstraintScore, _desc_con, _desc_frame,
)
from tools.algebra_eval import load_annotations, sample_by_class, EVALUABLE_BLISP


# ── keypoint indices for each body part ──────────────────────────

PART_KEYPOINTS = {
    ("Le", "-"): [L_ANKLE, L_KNEE, L_HIP],
    ("Le", "+"):  [R_ANKLE, R_KNEE, R_HIP],
    ("Le", ""):   [L_ANKLE, L_KNEE, L_HIP, R_ANKLE, R_KNEE, R_HIP],
    ("Ar", "-"): [L_WRIST, L_ELBOW, L_SHOULDER],
    ("Ar", "+"):  [R_WRIST, R_ELBOW, R_SHOULDER],
    ("Ar", ""):   [L_WRIST, L_ELBOW, L_SHOULDER, R_WRIST, R_ELBOW, R_SHOULDER],
    ("To", ""):   [L_SHOULDER, R_SHOULDER, L_HIP, R_HIP],
    ("Fo", "-"): [L_ANKLE, L_KNEE],
    ("Fo", "+"):  [R_ANKLE, R_KNEE],
    ("Fo", ""):   [L_ANKLE, L_KNEE, R_ANKLE, R_KNEE],
    ("Hd", ""):   [NOSE],
    ("Ba", ""):   [L_HIP, R_HIP, L_SHOULDER, R_SHOULDER],
}

# Constraints where 2D projection fundamentally cannot observe the relation,
# even with perfect keypoints
CONSTRAINTS_2D_HARD = {
    "CON(Op.To->Me.To h=0)",     # torso-on-torso: midline segments overlap
    "CON(Me.Fo-->Me.Fo+ h=0)",   # ankle closure: 3D leg-loop collapses in 2D
}

# Constraints where 2D projection is unreliable (high noise) but not impossible
CONSTRAINTS_2D_NOISY = {
    "FacingOpposed()",
    "FacingAligned()",
}


@dataclass
class AuditRecord:
    sample_id: str
    image_path: str
    dataset_tag: str
    true_blisp: str
    category: str
    category_label: str
    cluster: str
    bucket: str
    true_radical_score: float
    true_radical_all_met: bool
    highest_false_radical: str
    highest_false_score: float
    highest_false_all_met: bool
    failed_constraints: list[str]
    satisfied_constraints: list[str]
    n_inferred_contacts: int
    n_inferred_frames: int
    keypoint_quality: dict
    explanation: str
    constraint_detail: list[dict] = field(default_factory=list)


CATEGORY_LABELS = {
    "A": "Bad tag",
    "B": "Keypoint failure",
    "C": "2D observability failure",
    "D": "Algebra too strict",
    "E": "Algebra too weak",
    "F": "OGRD family issue",
    "OK": "Success",
}

FUNDAMENTAL_RADICALS = {"MNT", "BCTR", "SCTR", "CGRD", "HGRD", "TRTL", "OGRD"}


def _kp_quality(pose: Pose, part: str, sign: str) -> dict:
    key = (part, sign)
    if key not in PART_KEYPOINTS:
        key = (part, "")
    indices = PART_KEYPOINTS.get(key, [])
    confs = [pose.keypoints[i].confidence for i in indices]
    if not confs:
        return {"min_conf": 0.0, "avg_conf": 0.0, "n_below_thresh": 0, "n_total": 0}
    return {
        "min_conf": min(confs),
        "avg_conf": sum(confs) / len(confs),
        "n_below_thresh": sum(1 for c in confs if c < CONFIDENCE_THRESHOLD),
        "n_total": len(confs),
    }


def _parse_con_parts(desc: str) -> tuple[str, str, str, str]:
    """Parse CON(X.PartSign->Y.PartSign h=...) → (att_role, att_ps, ax_role, ax_ps)"""
    inner = desc[4:-1]
    arrow_idx = inner.index("->")
    att_str = inner[:arrow_idx].strip()
    rest = inner[arrow_idx+2:].strip()
    ax_str = rest.split(" ")[0]

    def _split(s):
        dot = s.index(".")
        role = s[:dot]
        ps = s[dot+1:]
        if ps and ps[-1] in ("+", "-"):
            return role, ps[:-1], ps[-1]
        return role, ps, ""

    att_role, att_part, att_sign = _split(att_str)
    ax_role, ax_part, ax_sign = _split(ax_str)
    return att_role, att_part + att_sign, ax_role, ax_part + ax_sign


def _keypoint_quality_for_con(
    desc: str, me_pose: Pose, op_pose: Pose,
) -> dict:
    att_role, att_ps, ax_role, ax_ps = _parse_con_parts(desc)

    att_part = att_ps.rstrip("+-")
    att_sign = att_ps[len(att_part):]
    ax_part = ax_ps.rstrip("+-")
    ax_sign = ax_ps[len(ax_part):]

    att_pose = me_pose if att_role == "Me" else op_pose
    ax_pose = me_pose if ax_role == "Me" else op_pose

    return {
        "attacker": _kp_quality(att_pose, att_part, att_sign),
        "axis": _kp_quality(ax_pose, ax_part, ax_sign),
    }


def _keypoint_quality_for_frame(
    desc: str, me_pose: Pose, op_pose: Pose,
) -> dict:
    quality = {}
    if "Facing" in desc:
        quality["me_shoulders"] = _kp_quality(me_pose, "To", "")
        quality["me_nose"] = _kp_quality(me_pose, "Hd", "")
        quality["op_shoulders"] = _kp_quality(op_pose, "To", "")
        quality["op_nose"] = _kp_quality(op_pose, "Hd", "")
    elif "Ground" in desc:
        if "Me." in desc:
            quality["me_hips"] = _kp_quality(me_pose, "Ba", "")
        if "Op." in desc:
            quality["op_hips"] = _kp_quality(op_pose, "Ba", "")
            quality["me_hips"] = _kp_quality(me_pose, "Ba", "")
    return quality


def _has_bad_keypoints(quality: dict) -> bool:
    for part_name, part_q in quality.items():
        if isinstance(part_q, dict) and "min_conf" in part_q:
            if part_q["n_below_thresh"] > 0:
                return True
    return False


def _nearest_candidate_score(
    con_desc: str, contacts: list[InferredCON],
) -> tuple[float, float]:
    """Find the best matching inferred contact for a required CON.
    Returns (best_similarity, best_distance)."""
    att_role, att_ps, ax_role, ax_ps = _parse_con_parts(con_desc)
    best_sim = 0.0
    best_dist = float("inf")
    for cand in contacts:
        cr = cand.con
        c_att = f"{cr.attacker.limb_ref.role}.{cr.attacker.limb_ref.part}{cr.attacker.limb_ref.sign}"
        c_ax = f"{cr.axis.limb_ref.role}.{cr.axis.limb_ref.part}{cr.axis.limb_ref.sign}"
        att_match = (att_role + "." + att_ps) == c_att
        ax_match = (ax_role + "." + ax_ps) == c_ax
        if att_match or ax_match:
            s = _con_similarity(
                CON(cr.attacker, cr.axis, cr.depth, cr.helicity),
                cr,
            )
            if cand.confidence > best_sim:
                best_sim = cand.confidence
                best_dist = cand.distance
    return best_sim, best_dist


def classify_constraint_failure(
    cs: ConstraintScore,
    kp_quality: dict,
    contacts: list[InferredCON],
    true_blisp: str,
) -> str:
    desc = cs.constraint_desc

    # Step 1: check keypoints
    if _has_bad_keypoints(kp_quality):
        return "B"

    # Step 2: known 2D-unobservable
    if desc in CONSTRAINTS_2D_HARD:
        return "C"

    # Step 3: known 2D-noisy (facing direction)
    if desc in CONSTRAINTS_2D_NOISY:
        return "C"

    # Step 4: type-specific logic
    if cs.constraint_type == "forbidden_con":
        # Forbidden contact violated = contact detected that shouldn't be there
        # With good keypoints and 2D-observable, this means the algebra is too strict
        return "D"

    if cs.constraint_type == "forbidden_bilateral":
        return "D"

    if cs.constraint_type == "required_con":
        # Required contact not found. Keypoints are fine, constraint is 2D-observable.
        # Check the detail for nearest candidate score.
        # If best_score is > 0 but below threshold → the contact is marginal → C (2D noise)
        # If best_score is 0 → no candidate at all → could be D (not necessary) or C (projection)
        if "best_score=" in cs.detail:
            try:
                bs = float(cs.detail.split("best_score=")[1])
            except (ValueError, IndexError):
                bs = 0.0
            if bs > 0.005:
                return "C"

        # No candidate at all — the body parts exist but no contact was found.
        # This is a 2D projection issue: the contact exists physically but the
        # 2D point-to-segment distance is too large.
        return "C"

    if cs.constraint_type == "frame":
        # Ground frame with good keypoints: possible bad tag or algebra issue
        if "OnGround" in desc or "NotOnGround" in desc:
            return "D"

    return "D"


def classify_sample(
    sv: SampleValidation,
    ann: Annotation,
    me_pose: Pose,
    op_pose: Pose,
    contacts: list[InferredCON],
) -> str:
    rv_true = sv.radical_scores.get(sv.true_blisp)
    if rv_true is None:
        return "A"

    # Success path: true radical validates
    if rv_true.all_required_met:
        # Check E: false fundamental radicals also match
        for rname in FUNDAMENTAL_RADICALS:
            if rname == sv.true_blisp:
                continue
            rv = sv.radical_scores.get(rname)
            if rv and rv.all_required_met:
                if rname == "OGRD" or sv.true_blisp == "OGRD":
                    return "F"
                if rv.weighted_score >= rv_true.weighted_score:
                    return "E"
        return "OK"

    # Failure path: true radical does not fully validate
    failed = [cs for cs in rv_true.constraint_scores if not cs.satisfied]
    if not failed:
        return "OK"

    # Check for bad tag first: if true radical is very low and another is very high
    if rv_true.weighted_score < 0.25:
        for rname in FUNDAMENTAL_RADICALS:
            if rname == sv.true_blisp or rname == "OGRD":
                continue
            rv_other = sv.radical_scores.get(rname)
            if rv_other and rv_other.all_required_met and rv_other.weighted_score >= 0.8:
                return "A"

    # OGRD family: true class is OGRD and fails (only has frame constraints)
    if sv.true_blisp == "OGRD":
        return "F"

    # Classify each failed constraint
    categories = []
    for cs in failed:
        if cs.constraint_type in ("required_con", "forbidden_con", "forbidden_bilateral"):
            kp_q = _keypoint_quality_for_con(cs.constraint_desc, me_pose, op_pose)
        else:
            kp_q = _keypoint_quality_for_frame(cs.constraint_desc, me_pose, op_pose)
        cat = classify_constraint_failure(cs, kp_q, contacts, sv.true_blisp)
        categories.append(cat)

    # Aggregate: pick the dominant category
    cat_counts = Counter(categories)

    # If any constraint failure is B (keypoint), and it's the majority or the only
    # non-C category, the sample is B
    if cat_counts.get("B", 0) > 0:
        non_bc = sum(v for k, v in cat_counts.items() if k not in ("B", "C"))
        if non_bc == 0:
            return "B"

    # If all failures are C (2D observability)
    if all(c == "C" for c in categories):
        return "C"

    # Mix of B and C
    if all(c in ("B", "C") for c in categories):
        return "C" if cat_counts.get("C", 0) >= cat_counts.get("B", 0) else "B"

    # If forbidden contacts dominate → D
    n_forbidden_d = sum(1 for cs, cat in zip(failed, categories)
                        if cs.constraint_type == "forbidden_con" and cat == "D")
    if n_forbidden_d > 0 and n_forbidden_d >= len(failed) // 2:
        return "D"

    # If D is present at all (ground frame issues, etc.)
    if "D" in cat_counts:
        return "D"

    # Fallback
    return max(cat_counts, key=cat_counts.get)


def build_audit_record(
    sv: SampleValidation,
    ann: Annotation,
    me_pose: Pose,
    op_pose: Pose,
    contacts: list[InferredCON],
    cluster: str,
    bucket: str,
) -> AuditRecord:
    rv_true = sv.radical_scores.get(sv.true_blisp)
    true_score = rv_true.weighted_score if rv_true else 0.0
    true_all_met = rv_true.all_required_met if rv_true else False

    best_false_name = "NONE"
    best_false_score = 0.0
    best_false_all_met = False
    for rname, rv in sv.radical_scores.items():
        if rname == sv.true_blisp or rname not in FUNDAMENTAL_RADICALS:
            continue
        if rv.weighted_score > best_false_score:
            best_false_name = rname
            best_false_score = rv.weighted_score
            best_false_all_met = rv.all_required_met

    failed_constraints = []
    satisfied_constraints = []
    constraint_detail = []
    if rv_true:
        for cs in rv_true.constraint_scores:
            if cs.constraint_type in ("required_con", "forbidden_con", "forbidden_bilateral"):
                kp_q = _keypoint_quality_for_con(cs.constraint_desc, me_pose, op_pose)
            else:
                kp_q = _keypoint_quality_for_frame(cs.constraint_desc, me_pose, op_pose)

            entry = {
                "type": cs.constraint_type,
                "desc": cs.constraint_desc,
                "satisfied": cs.satisfied,
                "score": round(cs.score, 4),
                "detail": cs.detail,
                "keypoint_quality": {
                    k: {kk: round(vv, 3) if isinstance(vv, float) else vv
                        for kk, vv in v.items()} if isinstance(v, dict) else v
                    for k, v in kp_q.items()
                },
            }
            if not cs.satisfied:
                cat = classify_constraint_failure(cs, kp_q, contacts, sv.true_blisp)
                entry["failure_category"] = cat
                entry["failure_label"] = CATEGORY_LABELS[cat]
                failed_constraints.append(f"{cs.constraint_type}:{cs.constraint_desc}")
            else:
                satisfied_constraints.append(f"{cs.constraint_type}:{cs.constraint_desc}")
            constraint_detail.append(entry)

    all_me_confs = [kp.confidence for kp in me_pose.keypoints]
    all_op_confs = [kp.confidence for kp in op_pose.keypoints]
    kp_quality_summary = {
        "me_min": round(min(all_me_confs), 3),
        "me_avg": round(sum(all_me_confs) / len(all_me_confs), 3),
        "me_n_low": sum(1 for c in all_me_confs if c < CONFIDENCE_THRESHOLD),
        "op_min": round(min(all_op_confs), 3),
        "op_avg": round(sum(all_op_confs) / len(all_op_confs), 3),
        "op_n_low": sum(1 for c in all_op_confs if c < CONFIDENCE_THRESHOLD),
    }

    category = classify_sample(sv, ann, me_pose, op_pose, contacts)
    explanation = _build_explanation(sv, rv_true, category, me_pose, op_pose, contacts)

    return AuditRecord(
        sample_id=sv.image_id,
        image_path=f"data/raw/images/{sv.image_id}.jpg",
        dataset_tag=sv.true_label,
        true_blisp=sv.true_blisp,
        category=category,
        category_label=CATEGORY_LABELS.get(category, "OK"),
        cluster=cluster,
        bucket=bucket,
        true_radical_score=round(true_score, 4),
        true_radical_all_met=true_all_met,
        highest_false_radical=best_false_name,
        highest_false_score=round(best_false_score, 4),
        highest_false_all_met=best_false_all_met,
        failed_constraints=failed_constraints,
        satisfied_constraints=satisfied_constraints,
        n_inferred_contacts=sv.n_inferred_contacts,
        n_inferred_frames=sv.n_inferred_frames,
        keypoint_quality=kp_quality_summary,
        explanation=explanation,
        constraint_detail=constraint_detail,
    )


def _build_explanation(
    sv: SampleValidation,
    rv_true: Optional[RadicalValidation],
    category: str,
    me_pose: Pose,
    op_pose: Pose,
    contacts: list[InferredCON],
) -> str:
    if category == "OK":
        n_false_met = sum(
            1 for rn, rv in sv.radical_scores.items()
            if rn != sv.true_blisp and rn in FUNDAMENTAL_RADICALS and rv.all_required_met
        )
        if n_false_met > 0:
            return f"True radical validates. {n_false_met} false fundamental radical(s) also pass (minor separation issue)."
        return "True radical validates and separates correctly."

    if rv_true is None:
        return "No true radical found in ALL_RADICALS."

    failed = [cs for cs in rv_true.constraint_scores if not cs.satisfied]
    failed_descs = [cs.constraint_desc for cs in failed]

    if category == "A":
        others = []
        for rn in FUNDAMENTAL_RADICALS:
            if rn == sv.true_blisp:
                continue
            rv = sv.radical_scores.get(rn)
            if rv and rv.all_required_met:
                others.append(f"{rn}({rv.weighted_score:.2f})")
        return (f"Tag '{sv.true_label}' suspect. True radical {sv.true_blisp} scores "
                f"{rv_true.weighted_score:.3f}. Better matches: {', '.join(others[:3])}. "
                f"Failed: {', '.join(failed_descs)}.")

    if category == "B":
        low_parts = []
        for cs in failed:
            if cs.constraint_type in ("required_con", "forbidden_con"):
                kp_q = _keypoint_quality_for_con(cs.constraint_desc, me_pose, op_pose)
            else:
                kp_q = _keypoint_quality_for_frame(cs.constraint_desc, me_pose, op_pose)
            for part_name, part_q in kp_q.items():
                if isinstance(part_q, dict) and part_q.get("n_below_thresh", 0) > 0:
                    low_parts.append(f"{part_name}(min={part_q['min_conf']:.2f})")
        return (f"Keypoint quality insufficient. Low-confidence: {', '.join(low_parts[:5])}. "
                f"Failed: {', '.join(failed_descs)}.")

    if category == "C":
        hard = [d for d in failed_descs if d in CONSTRAINTS_2D_HARD]
        noisy = [d for d in failed_descs if d in CONSTRAINTS_2D_NOISY]
        marginal = [d for d in failed_descs if d not in CONSTRAINTS_2D_HARD
                    and d not in CONSTRAINTS_2D_NOISY]
        parts = []
        if hard:
            parts.append(f"structurally unobservable: {', '.join(hard)}")
        if noisy:
            parts.append(f"2D-noisy: {', '.join(noisy)}")
        if marginal:
            parts.append(f"contact near threshold: {', '.join(marginal)}")
        return f"2D observability failure. {'; '.join(parts)}."

    if category == "D":
        forb = [cs for cs in failed if cs.constraint_type == "forbidden_con"]
        req = [cs for cs in failed if cs.constraint_type == "required_con"]
        frame = [cs for cs in failed if cs.constraint_type == "frame"]
        parts = []
        if forb:
            parts.append(f"forbidden contacts violated (too strict): "
                        f"{', '.join(cs.constraint_desc for cs in forb)}")
        if req:
            parts.append(f"required contacts not met despite good keypoints: "
                        f"{', '.join(cs.constraint_desc for cs in req)}")
        if frame:
            parts.append(f"frame constraints failed: "
                        f"{', '.join(cs.constraint_desc for cs in frame)}")
        return f"Algebra issue. {'; '.join(parts)}."

    if category == "E":
        false_matches = [
            (rn, rv.weighted_score) for rn, rv in sv.radical_scores.items()
            if rn != sv.true_blisp and rn in FUNDAMENTAL_RADICALS and rv.all_required_met
        ]
        false_matches.sort(key=lambda x: -x[1])
        fm_str = ", ".join(f"{n}({s:.3f})" for n, s in false_matches[:3])
        return f"True radical validates but false radicals also pass: {fm_str}."

    if category == "F":
        subs_met = [sub for sub in OGRD_SUBTYPES
                    if sub in sv.radical_scores and sv.radical_scores[sub].all_required_met]
        if sv.true_blisp == "OGRD":
            return (f"OGRD (frame-only) fails on {', '.join(failed_descs)}. "
                    f"Subtypes that pass: {', '.join(subs_met) if subs_met else 'none'}.")
        return (f"OGRD family overlap: true class {sv.true_blisp}, "
                f"OGRD subtypes also pass: {', '.join(subs_met) if subs_met else 'none'}.")

    return f"Unclassified. Failed: {', '.join(failed_descs)}."


# ── cluster extraction ───────────────────────────────────────────

CLUSTERS = {
    "TRTL_torso_contact": {
        "desc": "TRTL torso-to-torso contact 0% satisfaction",
    },
    "facing_direction": {
        "desc": "FacingOpposed/FacingAligned failures across MNT, OGRD, HGRD, BCTR, TRTL",
    },
    "OGRD_subtype_fp": {
        "desc": "OGRD subtype radicals match on non-OGRD classes",
    },
    "MNT_left_leg": {
        "desc": "MNT left-leg-to-torso contact failure",
    },
    "SCTR_forbidden_legs": {
        "desc": "SCTR forbidden leg contacts incorrectly detected",
    },
    "CGRD_ankle_closure": {
        "desc": "CGRD ankle closure detection failure",
    },
    "BCTR_elevation": {
        "desc": "BCTR NotOnGround(Op.Ba) frame failure",
    },
    "false_radical_high": {
        "desc": "False fundamental radical scores higher than true radical",
    },
}


def _is_cluster_member(sv: SampleValidation, cluster_name: str) -> Optional[str]:
    rv_true = sv.radical_scores.get(sv.true_blisp)
    if rv_true is None:
        return None

    if cluster_name == "TRTL_torso_contact":
        if sv.true_blisp != "TRTL":
            return None
        for cs in rv_true.constraint_scores:
            if "Op.To->Me.To" in cs.constraint_desc:
                if not cs.satisfied and cs.score < 0.01:
                    return "clear_failure"
                if not cs.satisfied:
                    return "borderline"
                return "success"
        return None

    elif cluster_name == "facing_direction":
        if sv.true_blisp not in ("MNT", "OGRD", "HGRD", "BCTR", "TRTL"):
            return None
        for cs in rv_true.constraint_scores:
            if "Facing" in cs.constraint_desc:
                if not cs.satisfied:
                    return "clear_failure"
                if cs.satisfied and cs.score < 0.5:
                    return "borderline"
                return "success"
        return None

    elif cluster_name == "OGRD_subtype_fp":
        if sv.true_blisp == "OGRD":
            return None
        n_sub_met = sum(
            1 for sub in OGRD_SUBTYPES
            if sub in sv.radical_scores and sv.radical_scores[sub].all_required_met
        )
        if n_sub_met >= 3:
            return "clear_failure"
        if n_sub_met >= 1:
            return "borderline"
        return "success"

    elif cluster_name == "MNT_left_leg":
        if sv.true_blisp != "MNT":
            return None
        for cs in rv_true.constraint_scores:
            if "Me.Le-->" in cs.constraint_desc and cs.constraint_type == "required_con":
                if not cs.satisfied and cs.score < 0.01:
                    return "clear_failure"
                if not cs.satisfied:
                    return "borderline"
                return "success"
        return None

    elif cluster_name == "SCTR_forbidden_legs":
        if sv.true_blisp != "SCTR":
            return None
        forb_violated = sum(
            1 for cs in rv_true.constraint_scores
            if cs.constraint_type == "forbidden_con" and not cs.satisfied
        )
        if forb_violated >= 2:
            return "clear_failure"
        if forb_violated == 1:
            return "borderline"
        return "success"

    elif cluster_name == "CGRD_ankle_closure":
        if sv.true_blisp != "CGRD":
            return None
        for cs in rv_true.constraint_scores:
            if "Me.Fo-->" in cs.constraint_desc and cs.constraint_type == "required_con":
                if not cs.satisfied and cs.score < 0.01:
                    return "clear_failure"
                if not cs.satisfied:
                    return "borderline"
                return "success"
        return None

    elif cluster_name == "BCTR_elevation":
        if sv.true_blisp != "BCTR":
            return None
        for cs in rv_true.constraint_scores:
            if "NotOnGround" in cs.constraint_desc:
                if not cs.satisfied:
                    return "clear_failure"
                if cs.satisfied and cs.score < 0.5:
                    return "borderline"
                return "success"
        return None

    elif cluster_name == "false_radical_high":
        best_false_score = 0.0
        for rname, rv in sv.radical_scores.items():
            if rname == sv.true_blisp or rname not in FUNDAMENTAL_RADICALS:
                continue
            if rv.weighted_score > best_false_score:
                best_false_score = rv.weighted_score
        if best_false_score > rv_true.weighted_score and not rv_true.all_required_met:
            return "clear_failure"
        if best_false_score > rv_true.weighted_score * 0.9:
            return "borderline"
        return "success"

    return None


def extract_cluster_samples(
    all_samples: list[tuple[SampleValidation, Annotation, Pose, Pose, list[InferredCON]]],
    cluster_name: str,
    n_per_bucket: int = 25,
    seed: int = 42,
) -> list[AuditRecord]:
    rng = random.Random(seed)
    buckets = defaultdict(list)

    for sv, ann, me_pose, op_pose, contacts in all_samples:
        bucket = _is_cluster_member(sv, cluster_name)
        if bucket is not None:
            buckets[bucket].append((sv, ann, me_pose, op_pose, contacts))

    records = []
    for bucket_name in ("clear_failure", "borderline", "success"):
        items = buckets.get(bucket_name, [])
        if len(items) > n_per_bucket:
            items = rng.sample(items, n_per_bucket)
        for sv, ann, me_pose, op_pose, contacts in items:
            rec = build_audit_record(sv, ann, me_pose, op_pose, contacts, cluster_name, bucket_name)
            records.append(rec)

    return records


# ── summary tables ───────────────────────────────────────────────

def compute_summaries(all_records: list[AuditRecord]) -> dict:
    by_radical = defaultdict(lambda: defaultdict(int))
    by_constraint = defaultdict(lambda: defaultdict(int))
    by_category = defaultdict(int)

    failures_only = [r for r in all_records if r.category != "OK"]

    for r in failures_only:
        by_radical[r.true_blisp][r.category] += 1
        by_category[r.category] += 1
        for fc in r.failed_constraints:
            by_constraint[fc][r.category] += 1

    # Validation rates excluding A/B/C
    abc_ids = {r.sample_id for r in all_records if r.category in ("A", "B", "C")}
    clean_records = [r for r in all_records if r.sample_id not in abc_ids]

    clean_true_validation = defaultdict(lambda: {"n": 0, "met": 0})
    clean_false_rejection = defaultdict(lambda: {"n": 0, "rejected": 0})

    for r in clean_records:
        clean_true_validation[r.true_blisp]["n"] += 1
        if r.true_radical_all_met:
            clean_true_validation[r.true_blisp]["met"] += 1
        if not r.highest_false_all_met:
            clean_false_rejection[r.true_blisp]["rejected"] += 1
        clean_false_rejection[r.true_blisp]["n"] += 1

    return {
        "by_radical": {k: dict(v) for k, v in by_radical.items()},
        "by_constraint": {k: dict(v) for k, v in by_constraint.items()},
        "by_category": dict(by_category),
        "clean_true_validation": {k: dict(v) for k, v in clean_true_validation.items()},
        "clean_false_rejection": {k: dict(v) for k, v in clean_false_rejection.items()},
        "total_audited": len(all_records),
        "total_failures": len(failures_only),
        "total_successes": len(all_records) - len(failures_only),
    }


def print_audit_report(all_records: list[AuditRecord], summaries: dict):
    print(f"\n{'='*80}")
    print(f"  FAILURE AUDIT REPORT")
    print(f"  {summaries['total_audited']} audited records, "
          f"{summaries['total_failures']} failures, "
          f"{summaries['total_successes']} successes")
    print(f"{'='*80}")

    print(f"\n  ── Failures by Category ──")
    print(f"  {'Cat':4s} {'Label':30s} {'Count':>6s} {'%':>7s}")
    print(f"  {'-'*4} {'-'*30} {'-'*6} {'-'*7}")
    total_f = max(summaries["total_failures"], 1)
    for cat in "ABCDEF":
        cnt = summaries["by_category"].get(cat, 0)
        label = CATEGORY_LABELS.get(cat, "?")
        print(f"  {cat:4s} {label:30s} {cnt:6d} {cnt/total_f:6.1%}")

    print(f"\n  ── Failures by Radical ──")
    radicals = sorted(FUNDAMENTAL_RADICALS)
    header = f"  {'Radical':8s}" + "".join(f"{'  '+c:>6s}" for c in "ABCDEF") + f"{'Total':>7s}"
    print(header)
    print(f"  {'-'*8}" + "-"*6*6 + f"{'-'*7}")
    for rad in radicals:
        cats = summaries["by_radical"].get(rad, {})
        total = sum(cats.values())
        vals = "".join(f"{cats.get(c, 0):6d}" for c in "ABCDEF")
        print(f"  {rad:8s}{vals}{total:7d}")

    print(f"\n  ── Failures by Constraint (top 15) ──")
    all_cons = [(con, sum(cats.values()), cats) for con, cats in summaries["by_constraint"].items()]
    all_cons.sort(key=lambda x: -x[1])
    print(f"  {'Constraint':55s}" + "".join(f"{'  '+c:>5s}" for c in "ABCDEF") + f"{'Tot':>6s}")
    for con, total, cats in all_cons[:15]:
        vals = "".join(f"{cats.get(c, 0):5d}" for c in "ABCDEF")
        print(f"  {con:55s}{vals}{total:6d}")

    print(f"\n  ── True-Radical Validation (excluding A/B/C failures) ──")
    print(f"  {'Radical':8s} {'N':>6s} {'Met':>6s} {'Rate':>7s}")
    print(f"  {'-'*8} {'-'*6} {'-'*6} {'-'*7}")
    for rad in radicals:
        info = summaries["clean_true_validation"].get(rad, {"n": 0, "met": 0})
        n, met = info["n"], info["met"]
        rate = met / n if n > 0 else 0
        print(f"  {rad:8s} {n:6d} {met:6d} {rate:6.1%}")

    print(f"\n  ── False-Radical Rejection (excluding A/B/C failures) ──")
    print(f"  {'Radical':8s} {'N':>6s} {'Rej':>6s} {'Rate':>7s}")
    print(f"  {'-'*8} {'-'*6} {'-'*6} {'-'*7}")
    for rad in radicals:
        info = summaries["clean_false_rejection"].get(rad, {"n": 0, "rejected": 0})
        n, rej = info["n"], info["rejected"]
        rate = rej / n if n > 0 else 0
        print(f"  {rad:8s} {n:6d} {rej:6d} {rate:6.1%}")

    # Per-cluster
    by_cluster = defaultdict(list)
    for r in all_records:
        by_cluster[r.cluster].append(r)

    print(f"\n  ── Per-Cluster Summary ──")
    for cluster_name in sorted(by_cluster.keys()):
        recs = by_cluster[cluster_name]
        cats = Counter(r.category for r in recs)
        buckets = Counter(r.bucket for r in recs)
        print(f"\n  {cluster_name} ({len(recs)} records):")
        print(f"    Buckets: " + ", ".join(f"{b}={c}" for b, c in sorted(buckets.items())))
        print(f"    Categories: " + ", ".join(f"{c}={n}" for c, n in sorted(cats.items())))


def print_population_report(pop: dict):
    print(f"\n{'='*80}")
    print(f"  POPULATION-LEVEL CATEGORY BREAKDOWN (unbiased)")
    print(f"{'='*80}")

    radicals = sorted(FUNDAMENTAL_RADICALS)
    all_cats = list("ABCDEF") + ["OK"]

    print(f"\n  ── Category Distribution by Class ──")
    header = f"  {'Class':8s}" + "".join(f"{c:>7s}" for c in all_cats) + f"{'Total':>7s}"
    print(header)
    print(f"  {'-'*8}" + "-"*7*len(all_cats) + f"{'-'*7}")
    pop_cat_totals = defaultdict(int)
    for rad in radicals:
        cats = pop["by_class"].get(rad, {})
        total = pop["totals"].get(rad, 0)
        vals = ""
        for c in all_cats:
            cnt = cats.get(c, 0)
            pop_cat_totals[c] += cnt
            if total > 0:
                vals += f" {cnt/total:5.1%}"
            else:
                vals += f"     ."
        print(f"  {rad:8s}{vals}{total:7d}")

    grand_total = sum(pop["totals"].values())
    print(f"\n  Grand totals (N={grand_total}):")
    for c in all_cats:
        cnt = pop_cat_totals[c]
        print(f"    {c} {CATEGORY_LABELS.get(c, 'OK'):30s}: {cnt:6d} ({cnt/grand_total:.1%})")

    print(f"\n  ── True-Radical Validation (excluding A/B/C, population-level) ──")
    print(f"  {'Radical':8s} {'N':>6s} {'Met':>6s} {'Rate':>7s}")
    print(f"  {'-'*8} {'-'*6} {'-'*6} {'-'*7}")
    for rad in radicals:
        info = pop["clean_true_validation"].get(rad, {"n": 0, "met": 0})
        n, met = info["n"], info["met"]
        rate = met / n if n > 0 else 0
        print(f"  {rad:8s} {n:6d} {met:6d} {rate:6.1%}")

    print(f"\n  ── False-Radical Rejection (excluding A/B/C, population-level) ──")
    print(f"  {'Radical':8s} {'N':>6s} {'Rej':>6s} {'Rate':>7s}")
    print(f"  {'-'*8} {'-'*6} {'-'*6} {'-'*7}")
    for rad in radicals:
        info = pop["clean_false_rejection"].get(rad, {"n": 0, "rejected": 0})
        n, rej = info["n"], info["rejected"]
        rate = rej / n if n > 0 else 0
        print(f"  {rad:8s} {n:6d} {rej:6d} {rate:6.1%}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Failure audit of radical validation")
    parser.add_argument("--n-per-class", type=int, default=500,
                        help="Samples per class to audit")
    parser.add_argument("--n-per-bucket", type=int, default=25)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out-dir", type=str, default="data/radical_validation")
    args = parser.parse_args()

    print("Loading annotations...")
    anns = load_annotations()
    evaluable = [a for a in anns if blisp_label(a.position) in EVALUABLE_BLISP
                 and a.pose1 is not None and a.pose2 is not None]
    print(f"Evaluable: {len(evaluable)}")

    samples_ann = sample_by_class(evaluable, args.n_per_class, args.seed)
    print(f"Sampled: {len(samples_ann)}")

    print("Running validation...")
    all_validated: list[tuple[SampleValidation, Annotation, Pose, Pose, list[InferredCON]]] = []
    t0 = time.time()
    for i, ann in enumerate(samples_ann):
        norm = normalize(ann)
        if norm.me_pose is None or norm.op_pose is None:
            continue
        sv = validate_sample(ann)
        if sv is None:
            continue
        contacts = infer_contacts(norm.me_pose, norm.op_pose)
        all_validated.append((sv, ann, norm.me_pose, norm.op_pose, contacts))
        if (i + 1) % 500 == 0:
            print(f"  [{i+1}/{len(samples_ann)}]")

    elapsed = time.time() - t0
    print(f"Validated {len(all_validated)} samples in {elapsed:.1f}s")

    print("\nExtracting cluster samples...")
    all_records: list[AuditRecord] = []
    for cluster_name in CLUSTERS:
        recs = extract_cluster_samples(all_validated, cluster_name, args.n_per_bucket, args.seed)
        all_records.extend(recs)
        n_by_bucket = Counter(r.bucket for r in recs)
        print(f"  {cluster_name}: {len(recs)} records "
              f"({n_by_bucket.get('clear_failure',0)} fail, "
              f"{n_by_bucket.get('borderline',0)} border, "
              f"{n_by_bucket.get('success',0)} success)")

    summaries = compute_summaries(all_records)

    # Population-level classification: classify ALL validated samples (unbiased)
    print("\nClassifying full population...")
    pop_by_class = defaultdict(lambda: defaultdict(int))
    pop_total = defaultdict(int)
    pop_clean_met = defaultdict(lambda: {"n": 0, "met": 0})
    pop_clean_rej = defaultdict(lambda: {"n": 0, "rejected": 0})

    for sv, ann, me_pose, op_pose, contacts in all_validated:
        cat = classify_sample(sv, ann, me_pose, op_pose, contacts)
        pop_by_class[sv.true_blisp][cat] += 1
        pop_total[sv.true_blisp] += 1

        if cat not in ("A", "B", "C"):
            rv_true = sv.radical_scores.get(sv.true_blisp)
            pop_clean_met[sv.true_blisp]["n"] += 1
            if rv_true and rv_true.all_required_met:
                pop_clean_met[sv.true_blisp]["met"] += 1

            best_false_all_met = False
            for rn in FUNDAMENTAL_RADICALS:
                if rn == sv.true_blisp:
                    continue
                rv = sv.radical_scores.get(rn)
                if rv and rv.all_required_met:
                    best_false_all_met = True
                    break
            pop_clean_rej[sv.true_blisp]["n"] += 1
            if not best_false_all_met:
                pop_clean_rej[sv.true_blisp]["rejected"] += 1

    population_stats = {
        "by_class": {k: dict(v) for k, v in pop_by_class.items()},
        "totals": dict(pop_total),
        "clean_true_validation": {k: dict(v) for k, v in pop_clean_met.items()},
        "clean_false_rejection": {k: dict(v) for k, v in pop_clean_rej.items()},
    }
    summaries["population"] = population_stats

    print_audit_report(all_records, summaries)
    print_population_report(population_stats)

    # Save
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    json_records = [asdict(r) for r in all_records]
    with open(out_dir / "failure_audit.json", "w") as f:
        json.dump({
            "meta": {
                "n_per_class": args.n_per_class,
                "n_per_bucket": args.n_per_bucket,
                "seed": args.seed,
                "total_records": len(all_records),
                "total_population": len(all_validated),
                "clusters": list(CLUSTERS.keys()),
            },
            "summaries": summaries,
            "records": json_records,
        }, f, indent=2)
    print(f"\nSaved {out_dir / 'failure_audit.json'}")


if __name__ == "__main__":
    main()
