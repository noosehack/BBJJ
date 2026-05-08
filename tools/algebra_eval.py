"""Evaluate algebraic matcher against the labelled ViCoS dataset.

Runs: keypoints → observed CON/FRM → radical match → predicted position
and compares against the known position labels.
"""

import csv
import json
import random
import sys
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field, asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from data.schema import Annotation, Pose
from data.label_map import VICOS_TO_BLISP, normalize, blisp_label
from dic.radicals import ALL_RADICALS
from tools.contact_inference import (
    infer_contacts, infer_frame_constraints, match_radical,
    InferredCON, InferredFrame,
)
from tools.annotate import _serialize_con, _serialize_frame
from tools.blisp_export import _format_con, _format_frame

# Classes that have matching radicals
EVALUABLE_BLISP = {b for b in {e["blisp"] for e in VICOS_TO_BLISP.values()} if b in ALL_RADICALS}

EQUIVALENT_RADICALS = {
    "HGRD": {"HGRD"},
}


@dataclass
class EvalRow:
    image_id: str
    image_path: str
    true_label: str
    true_blisp: str
    predicted_radical: str
    match_score: float
    pov: str
    observed_con: list[str]
    observed_frm: list[str]
    observed_axs: list[str]
    canonical_required_con: list[str]
    canonical_forbidden_con: list[str]
    canonical_required_frm: list[str]
    pass_requirements: list[str]
    miss_requirements: list[str]
    extra_contacts: list[str]
    is_correct: bool
    failure_reason: str


def _fmt_con_short(ic: InferredCON) -> str:
    c = ic.con
    att = f"{c.attacker.limb_ref.role}.{c.attacker.limb_ref.part}{c.attacker.limb_ref.sign}"
    ax = f"{c.axis.limb_ref.role}.{c.axis.limb_ref.part}{c.axis.limb_ref.sign}"
    return f"({att}->{ax} h={c.helicity} {ic.confidence:.3f})"


def _fmt_frame_short(inf: InferredFrame) -> str:
    t = type(inf.constraint).__name__
    part = ""
    if hasattr(inf.constraint, "part"):
        p = inf.constraint.part
        part = f" {p.role}.{p.part}{p.sign}"
    return f"({t}{part} {inf.confidence:.3f})"


def _fmt_axs(ic: InferredCON) -> list[str]:
    c = ic.con
    axes = []
    for ad in [c.attacker, c.axis]:
        lr = ad.limb_ref
        label = f"{lr.role}.{lr.part}{lr.sign}_{{{ad.from_pt}->{ad.to_pt}}}"
        axes.append(label)
    return axes


def _fmt_canon_con(c) -> str:
    att = f"{c.attacker.limb_ref.role}.{c.attacker.limb_ref.part}{c.attacker.limb_ref.sign}"
    ax = f"{c.axis.limb_ref.role}.{c.axis.limb_ref.part}{c.axis.limb_ref.sign}"
    return f"({att}->{ax} h={c.helicity})"


def _fmt_canon_frame(f) -> str:
    t = type(f).__name__
    if hasattr(f, "part"):
        p = f.part
        return f"({t} {p.role}.{p.part}{p.sign})"
    return f"({t})"


def evaluate_one(ann: Annotation) -> EvalRow:
    true_blisp = blisp_label(ann.position)
    norm = normalize(ann)

    if norm.me_pose is None or norm.op_pose is None:
        return EvalRow(
            image_id=ann.image, image_path=f"data/raw/images/{ann.image}.jpg",
            true_label=ann.position, true_blisp=true_blisp,
            predicted_radical="NONE", match_score=0.0, pov="none",
            observed_con=[], observed_frm=[], observed_axs=[],
            canonical_required_con=[], canonical_forbidden_con=[],
            canonical_required_frm=[],
            pass_requirements=[], miss_requirements=[], extra_contacts=[],
            is_correct=False, failure_reason="missing_pose",
        )

    # Run with known POV (from suffix convention)
    contacts_known = infer_contacts(norm.me_pose, norm.op_pose)
    frames_known = infer_frame_constraints(norm.me_pose, norm.op_pose)
    matches_known = match_radical(contacts_known, frames_known)

    # Also try reversed POV
    contacts_rev = infer_contacts(norm.op_pose, norm.me_pose)
    frames_rev = infer_frame_constraints(norm.op_pose, norm.me_pose)
    matches_rev = match_radical(contacts_rev, frames_rev)

    # Pick the POV that gives the best match
    best_known = matches_known[0] if matches_known else None
    best_rev = matches_rev[0] if matches_rev else None

    if best_known and best_rev:
        if best_known.confidence >= best_rev.confidence:
            contacts, frames, matches, pov = contacts_known, frames_known, matches_known, "known"
        else:
            contacts, frames, matches, pov = contacts_rev, frames_rev, matches_rev, "reversed"
    elif best_known:
        contacts, frames, matches, pov = contacts_known, frames_known, matches_known, "known"
    elif best_rev:
        contacts, frames, matches, pov = contacts_rev, frames_rev, matches_rev, "reversed"
    else:
        contacts, frames, matches, pov = contacts_known, frames_known, matches_known, "none"

    predicted = matches[0].radical_name if matches else "NONE"
    score = matches[0].confidence if matches else 0.0

    # Observed
    obs_con = [_fmt_con_short(c) for c in contacts[:10]]
    obs_frm = [_fmt_frame_short(f) for f in frames]
    obs_axs = list(set(a for c in contacts[:10] for a in _fmt_axs(c)))

    # Canonical for the TRUE radical
    canon = ALL_RADICALS.get(true_blisp)
    canon_req_con = [_fmt_canon_con(c) for c in canon.contacts] if canon else []
    canon_forb_con = [_fmt_canon_con(c) for c in canon.forbidden_contacts] if canon else []
    canon_req_frm = [_fmt_canon_frame(f) for f in canon.frame_constraints] if canon else []

    # Check which requirements of the TRUE radical pass/miss
    pass_reqs = []
    miss_reqs = []
    if canon:
        # Check contacts
        true_matches = match_radical(contacts, frames, {true_blisp: canon})
        if true_matches:
            for mc in true_matches[0].matched_contacts:
                pass_reqs.append(f"CON:{_fmt_con_short(mc)}")
            for mf in true_matches[0].matched_frames:
                pass_reqs.append(f"FRM:{_fmt_frame_short(mf)}")
            # Find which required contacts were NOT matched
            matched_count = len(true_matches[0].matched_contacts)
            for i, req_con in enumerate(canon.contacts):
                if i >= matched_count:
                    miss_reqs.append(f"CON:{_fmt_canon_con(req_con)}")
        else:
            for req_con in canon.contacts:
                miss_reqs.append(f"CON:{_fmt_canon_con(req_con)}")
            for req_frm in canon.frame_constraints:
                miss_reqs.append(f"FRM:{_fmt_canon_frame(req_frm)}")

    # Extra contacts not required by the true radical
    extra = []
    if contacts:
        for c in contacts[:5]:
            extra.append(_fmt_con_short(c))

    # Correctness
    equiv = EQUIVALENT_RADICALS.get(true_blisp, {true_blisp})
    is_correct = predicted in equiv

    # Failure reason
    failure_reason = ""
    if not is_correct:
        if predicted == "NONE":
            if not contacts:
                failure_reason = "no_contacts_inferred"
            elif miss_reqs:
                failure_reason = f"true_radical_missed:{';'.join(miss_reqs[:3])}"
            else:
                failure_reason = "no_radical_matched"
        elif predicted in ALL_RADICALS:
            failure_reason = f"wrong_radical:{predicted}"
        else:
            failure_reason = f"unknown_prediction:{predicted}"

    return EvalRow(
        image_id=ann.image,
        image_path=f"data/raw/images/{ann.image}.jpg",
        true_label=ann.position,
        true_blisp=true_blisp,
        predicted_radical=predicted,
        match_score=round(score, 4),
        pov=pov,
        observed_con=obs_con,
        observed_frm=obs_frm,
        observed_axs=obs_axs,
        canonical_required_con=canon_req_con,
        canonical_forbidden_con=canon_forb_con,
        canonical_required_frm=canon_req_frm,
        pass_requirements=pass_reqs,
        miss_requirements=miss_reqs,
        extra_contacts=extra,
        is_correct=is_correct,
        failure_reason=failure_reason,
    )


def load_annotations() -> list[Annotation]:
    with open("data/raw/annotations.json") as f:
        raw = json.load(f)
    anns = []
    for item in raw:
        pose1 = Pose.from_raw(item["pose1"]) if item.get("pose1") else None
        pose2 = Pose.from_raw(item["pose2"]) if item.get("pose2") else None
        anns.append(Annotation(
            position=item["position"],
            image=item["image"],
            frame=item.get("frame", 0),
            pose1=pose1,
            pose2=pose2,
        ))
    return anns


def sample_by_class(anns: list[Annotation], n_per_class: int, seed: int = 42) -> list[Annotation]:
    by_class = defaultdict(list)
    for a in anns:
        bl = blisp_label(a.position)
        if bl in EVALUABLE_BLISP:
            by_class[bl].append(a)
    rng = random.Random(seed)
    sampled = []
    for bl, items in sorted(by_class.items()):
        if len(items) > n_per_class:
            sampled.extend(rng.sample(items, n_per_class))
        else:
            sampled.extend(items)
    return sampled


def write_results(rows: list[EvalRow], csv_path: str, jsonl_path: str):
    Path(csv_path).parent.mkdir(parents=True, exist_ok=True)

    # CSV
    fieldnames = [
        "image_id", "true_label", "true_blisp", "predicted_radical",
        "match_score", "pov", "is_correct", "failure_reason",
        "observed_con", "observed_frm", "canonical_required_con",
        "canonical_forbidden_con", "pass_requirements", "miss_requirements",
    ]
    with open(csv_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({
                "image_id": r.image_id,
                "true_label": r.true_label,
                "true_blisp": r.true_blisp,
                "predicted_radical": r.predicted_radical,
                "match_score": r.match_score,
                "pov": r.pov,
                "is_correct": r.is_correct,
                "failure_reason": r.failure_reason,
                "observed_con": "|".join(r.observed_con),
                "observed_frm": "|".join(r.observed_frm),
                "canonical_required_con": "|".join(r.canonical_required_con),
                "canonical_forbidden_con": "|".join(r.canonical_forbidden_con),
                "pass_requirements": "|".join(r.pass_requirements),
                "miss_requirements": "|".join(r.miss_requirements),
            })

    # JSONL
    with open(jsonl_path, "w") as f:
        for r in rows:
            f.write(json.dumps(asdict(r)) + "\n")


def print_report(rows: list[EvalRow]):
    n = len(rows)
    correct = sum(1 for r in rows if r.is_correct)
    print(f"\n{'='*70}")
    print(f"  ALGEBRA EVALUATION REPORT")
    print(f"  {n} samples, {len(EVALUABLE_BLISP)} evaluable classes")
    print(f"{'='*70}")
    print(f"\n  Overall accuracy: {correct}/{n} = {correct/n:.1%}")

    # Per-class metrics
    classes = sorted(EVALUABLE_BLISP)
    print(f"\n  {'Class':8s} {'N':>6s} {'Correct':>8s} {'Acc':>7s} {'AvgScore':>9s} {'TopWrong':>12s}")
    print(f"  {'-'*8} {'-'*6} {'-'*8} {'-'*7} {'-'*9} {'-'*12}")

    tp = defaultdict(int)
    fp = defaultdict(int)
    fn = defaultdict(int)

    for r in rows:
        if r.is_correct:
            tp[r.true_blisp] += 1
        else:
            fn[r.true_blisp] += 1
            if r.predicted_radical != "NONE":
                fp[r.predicted_radical] += 1

    for cls in classes:
        cls_rows = [r for r in rows if r.true_blisp == cls]
        if not cls_rows:
            continue
        n_cls = len(cls_rows)
        n_correct = sum(1 for r in cls_rows if r.is_correct)
        avg_score = sum(r.match_score for r in cls_rows) / n_cls
        wrong = Counter(r.predicted_radical for r in cls_rows if not r.is_correct)
        top_wrong = wrong.most_common(1)[0][0] if wrong else "-"
        print(f"  {cls:8s} {n_cls:6d} {n_correct:8d} {n_correct/n_cls:7.1%} {avg_score:9.3f} {top_wrong:>12s}")

    # Precision / Recall / F1
    print(f"\n  {'Class':8s} {'Prec':>7s} {'Recall':>7s} {'F1':>7s}")
    print(f"  {'-'*8} {'-'*7} {'-'*7} {'-'*7}")
    f1_scores = []
    for cls in classes:
        p = tp[cls] / (tp[cls] + fp[cls]) if (tp[cls] + fp[cls]) > 0 else 0
        r = tp[cls] / (tp[cls] + fn[cls]) if (tp[cls] + fn[cls]) > 0 else 0
        f1 = 2*p*r / (p+r) if (p+r) > 0 else 0
        f1_scores.append(f1)
        print(f"  {cls:8s} {p:7.1%} {r:7.1%} {f1:7.3f}")
    macro_f1 = sum(f1_scores) / len(f1_scores) if f1_scores else 0
    print(f"\n  Macro F1: {macro_f1:.3f}")

    # Confusion matrix
    all_labels = sorted(set(classes) | {"NONE"} | {r.predicted_radical for r in rows})
    pred_labels = sorted(set(r.predicted_radical for r in rows))

    print(f"\n  Confusion matrix (rows=true, cols=predicted):")
    header = f"  {'':8s}" + "".join(f"{l:>8s}" for l in pred_labels)
    print(header)
    for true_cls in classes:
        cls_rows = [r for r in rows if r.true_blisp == true_cls]
        counts = Counter(r.predicted_radical for r in cls_rows)
        row_str = f"  {true_cls:8s}" + "".join(f"{counts.get(p, 0):>8d}" for p in pred_labels)
        print(row_str)

    # Most common missed requirements
    all_misses = []
    for r in rows:
        if not r.is_correct:
            all_misses.extend(r.miss_requirements)
    miss_counts = Counter(all_misses)
    print(f"\n  Top 15 missed requirements:")
    for req, cnt in miss_counts.most_common(15):
        print(f"    {cnt:5d}  {req}")

    # Most common failure reasons
    reason_counts = Counter(r.failure_reason for r in rows if not r.is_correct)
    print(f"\n  Top 15 failure reasons:")
    for reason, cnt in reason_counts.most_common(15):
        print(f"    {cnt:5d}  {reason}")

    # POV stats
    pov_counts = Counter(r.pov for r in rows)
    pov_correct = Counter(r.pov for r in rows if r.is_correct)
    print(f"\n  POV distribution:")
    for pov in sorted(pov_counts.keys()):
        total = pov_counts[pov]
        corr = pov_correct.get(pov, 0)
        print(f"    {pov:10s}: {total:5d} total, {corr:5d} correct ({corr/total:.1%})")

    # Top 20 failure examples
    failures = [r for r in rows if not r.is_correct]
    failures.sort(key=lambda r: -r.match_score)
    print(f"\n  Top 20 highest-confidence failures:")
    print(f"  {'Image':>10s} {'True':>6s} {'Pred':>8s} {'Score':>7s} {'POV':>8s} {'Reason'}")
    for r in failures[:20]:
        reason_short = r.failure_reason[:40]
        print(f"  {r.image_id:>10s} {r.true_blisp:>6s} {r.predicted_radical:>8s} {r.match_score:>7.3f} {r.pov:>8s} {reason_short}")


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=["1", "2"], default="1")
    parser.add_argument("--n-per-class", type=int, default=100)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    print("Loading annotations...")
    anns = load_annotations()
    print(f"Loaded {len(anns)} annotations")

    # Filter to evaluable classes
    evaluable = [a for a in anns if blisp_label(a.position) in EVALUABLE_BLISP]
    print(f"Evaluable (have radicals): {len(evaluable)}")

    # Filter to annotations with both poses
    evaluable = [a for a in evaluable if a.pose1 is not None and a.pose2 is not None]
    print(f"With both poses: {len(evaluable)}")

    if args.stage == "1":
        samples = sample_by_class(evaluable, args.n_per_class, args.seed)
        suffix = "samples"
    else:
        samples = evaluable
        suffix = "full"

    print(f"\nEvaluating {len(samples)} samples...")
    rows = []
    t0 = time.time()
    for i, ann in enumerate(samples):
        row = evaluate_one(ann)
        rows.append(row)
        if (i + 1) % 200 == 0:
            elapsed = time.time() - t0
            rate = (i + 1) / elapsed
            eta = (len(samples) - i - 1) / rate
            acc = sum(1 for r in rows if r.is_correct) / len(rows)
            print(f"  [{i+1}/{len(samples)}] {rate:.0f}/s, ETA {eta:.0f}s, running acc={acc:.1%}")

    elapsed = time.time() - t0
    print(f"\nDone in {elapsed:.1f}s ({len(rows)/elapsed:.0f} samples/s)")

    csv_path = f"data/algebra_eval/algebra_eval_{suffix}.csv"
    jsonl_path = f"data/algebra_eval/algebra_eval_{suffix}.jsonl"
    write_results(rows, csv_path, jsonl_path)
    print(f"Saved: {csv_path}")
    print(f"Saved: {jsonl_path}")

    print_report(rows)


if __name__ == "__main__":
    main()
