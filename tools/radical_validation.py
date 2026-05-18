"""Radical validation pipeline: given known labels + geometry, validate constraints.

This is NOT classification. For each sample with known label L:
  1. Infer contacts/frames from geometry
  2. Score every constraint in the TRUE radical R(L) individually
  3. Score every constraint in all FALSE radicals R(L') for separation analysis
  4. Aggregate into per-radical constraint statistics, overlap matrices, failure taxonomy
"""

import json
import sys
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from data.schema import Annotation, Pose
from data.label_map import VICOS_TO_BLISP, normalize, blisp_label
from dic.radicals import ALL_RADICALS, Radical
from dic.relations import CON
from dic.frames import FacingOpposed, FacingAligned, OnGround, NotOnGround, FrameConstraint
from tools.contact_inference import (
    infer_contacts, infer_frame_constraints,
    InferredCON, InferredFrame,
    _con_similarity, _find_frame, _find_contact,
    CON_MATCH_THRESHOLD, FORBIDDEN_MATCH_THRESHOLD,
)
from tools.algebra_eval import load_annotations, sample_by_class, EVALUABLE_BLISP


# ── per-constraint scoring ───────────────────────────────────────

@dataclass
class ConstraintScore:
    constraint_type: str   # "required_con", "frame", "forbidden_con", "forbidden_bilateral"
    constraint_desc: str
    satisfied: bool
    score: float           # 0..1 weighted score
    detail: str = ""


@dataclass
class RadicalValidation:
    radical_name: str
    is_true_radical: bool
    constraint_scores: list[ConstraintScore] = field(default_factory=list)
    n_satisfied: int = 0
    n_total: int = 0
    weighted_score: float = 0.0
    all_required_met: bool = False
    any_forbidden_violated: bool = False


@dataclass
class SampleValidation:
    image_id: str
    true_label: str
    true_blisp: str
    pov: str
    n_inferred_contacts: int
    n_inferred_frames: int
    radical_scores: dict[str, RadicalValidation] = field(default_factory=dict)


def _desc_con(c: CON) -> str:
    att = f"{c.attacker.limb_ref.role}.{c.attacker.limb_ref.part}{c.attacker.limb_ref.sign}"
    ax = f"{c.axis.limb_ref.role}.{c.axis.limb_ref.part}{c.axis.limb_ref.sign}"
    return f"CON({att}->{ax} h={c.helicity})"


def _desc_frame(f: FrameConstraint) -> str:
    t = type(f).__name__
    if hasattr(f, "part"):
        p = f.part
        return f"{t}({p.role}.{p.part}{p.sign})"
    return f"{t}()"


def validate_radical(
    rad: Radical,
    contacts: list[InferredCON],
    frames: list[InferredFrame],
) -> RadicalValidation:
    scores = []
    n_satisfied = 0
    n_total = 0
    all_req_met = True
    any_forbidden = False

    # 1. Required contacts
    used_indices: set[int] = set()
    for req_con in rad.contacts:
        n_total += 1
        best_score = 0.0
        best_idx = None
        best_cand = None
        for i, cand in enumerate(contacts):
            if i in used_indices:
                continue
            s = _con_similarity(req_con, cand.con)
            w = s * cand.confidence
            if w > best_score:
                best_score = w
                best_idx = i
                best_cand = cand
        satisfied = best_score > CON_MATCH_THRESHOLD
        if satisfied and best_idx is not None:
            used_indices.add(best_idx)
            n_satisfied += 1
            detail = f"matched conf={best_cand.confidence:.3f} dist={best_cand.distance:.3f}"
        else:
            all_req_met = False
            detail = f"best_score={best_score:.4f}" if best_score > 0 else "no_candidate"
        scores.append(ConstraintScore(
            "required_con", _desc_con(req_con), satisfied, best_score, detail))

    # 2. Frame constraints
    for fc in rad.frame_constraints:
        n_total += 1
        match = _find_frame(fc, frames)
        if match is not None:
            n_satisfied += 1
            scores.append(ConstraintScore(
                "frame", _desc_frame(fc), True, match.confidence,
                f"conf={match.confidence:.3f}"))
        else:
            is_hard = isinstance(fc, (OnGround, NotOnGround))
            if is_hard:
                all_req_met = False
            scores.append(ConstraintScore(
                "frame", _desc_frame(fc), False, 0.0, "not_found"))

    # 3. Forbidden contacts (should NOT be present)
    for forb_con in rad.forbidden_contacts:
        n_total += 1
        found = _find_contact(forb_con, contacts, FORBIDDEN_MATCH_THRESHOLD)
        if found is None:
            n_satisfied += 1
            scores.append(ConstraintScore(
                "forbidden_con", _desc_con(forb_con), True, 1.0, "correctly_absent"))
        else:
            any_forbidden = True
            all_req_met = False
            scores.append(ConstraintScore(
                "forbidden_con", _desc_con(forb_con), False, 0.0,
                f"violated conf={found.confidence:.3f}"))

    # 4. Forbidden bilateral (ALL must be present for violation)
    if rad.forbidden_bilateral:
        n_total += 1
        all_bilateral_found = True
        bilateral_used: set[int] = set()
        for req in rad.forbidden_bilateral:
            best_w = 0.0
            best_i = None
            for i, cand in enumerate(contacts):
                if i in bilateral_used:
                    continue
                s = _con_similarity(req, cand.con)
                w = s * cand.confidence
                if w > best_w:
                    best_w = w
                    best_i = i
            if best_i is not None and best_w > CON_MATCH_THRESHOLD:
                bilateral_used.add(best_i)
            else:
                all_bilateral_found = False
                break
        if not all_bilateral_found:
            n_satisfied += 1
            scores.append(ConstraintScore(
                "forbidden_bilateral", "bilateral_set", True, 1.0, "correctly_absent"))
        else:
            any_forbidden = True
            all_req_met = False
            scores.append(ConstraintScore(
                "forbidden_bilateral", "bilateral_set", False, 0.0, "all_bilateral_present"))

    weighted = n_satisfied / n_total if n_total > 0 else 1.0

    return RadicalValidation(
        radical_name=rad.name,
        is_true_radical=False,
        constraint_scores=scores,
        n_satisfied=n_satisfied,
        n_total=n_total,
        weighted_score=weighted,
        all_required_met=all_req_met,
        any_forbidden_violated=any_forbidden,
    )


def validate_sample(ann: Annotation) -> Optional[SampleValidation]:
    true_blisp = blisp_label(ann.position)
    if true_blisp not in EVALUABLE_BLISP:
        return None

    norm = normalize(ann)
    if norm.me_pose is None or norm.op_pose is None:
        return None

    contacts = infer_contacts(norm.me_pose, norm.op_pose)
    frames = infer_frame_constraints(norm.me_pose, norm.op_pose)

    sv = SampleValidation(
        image_id=ann.image,
        true_label=ann.position,
        true_blisp=true_blisp,
        pov="known",
        n_inferred_contacts=len(contacts),
        n_inferred_frames=len(frames),
    )

    for rname, rad in ALL_RADICALS.items():
        rv = validate_radical(rad, contacts, frames)
        rv.is_true_radical = (rname == true_blisp)
        sv.radical_scores[rname] = rv

    return sv


# ── aggregation ──────────────────────────────────────────────────

@dataclass
class ConstraintStat:
    constraint_type: str
    constraint_desc: str
    n_samples: int = 0
    n_satisfied: int = 0
    total_score: float = 0.0
    scores: list[float] = field(default_factory=list)

    @property
    def satisfaction_rate(self) -> float:
        return self.n_satisfied / self.n_samples if self.n_samples > 0 else 0.0

    @property
    def avg_score(self) -> float:
        return self.total_score / self.n_samples if self.n_samples > 0 else 0.0

    @property
    def variance(self) -> float:
        if self.n_samples < 2:
            return 0.0
        mean = self.avg_score
        return sum((s - mean) ** 2 for s in self.scores) / (self.n_samples - 1)


def aggregate_results(samples: list[SampleValidation]) -> dict:
    by_class = defaultdict(list)
    for sv in samples:
        by_class[sv.true_blisp].append(sv)

    # 1. Per-radical constraint stats (true radical only)
    constraint_stats: dict[str, list[ConstraintStat]] = {}
    for rname, rad in ALL_RADICALS.items():
        if rname not in EVALUABLE_BLISP:
            continue
        class_samples = by_class.get(rname, [])
        if not class_samples:
            continue

        stats_list = []
        # build constraint descriptors from radical definition
        constraint_keys = []
        for c in rad.contacts:
            constraint_keys.append(("required_con", _desc_con(c)))
        for f in rad.frame_constraints:
            constraint_keys.append(("frame", _desc_frame(f)))
        for c in rad.forbidden_contacts:
            constraint_keys.append(("forbidden_con", _desc_con(c)))
        if rad.forbidden_bilateral:
            constraint_keys.append(("forbidden_bilateral", "bilateral_set"))

        for ctype, cdesc in constraint_keys:
            stat = ConstraintStat(ctype, cdesc)
            for sv in class_samples:
                rv = sv.radical_scores.get(rname)
                if rv is None:
                    continue
                for cs in rv.constraint_scores:
                    if cs.constraint_type == ctype and cs.constraint_desc == cdesc:
                        stat.n_samples += 1
                        if cs.satisfied:
                            stat.n_satisfied += 1
                        stat.total_score += cs.score
                        stat.scores.append(cs.score)
                        break
            stats_list.append(stat)
        constraint_stats[rname] = stats_list

    # 2. Positive vs negative scoring matrix
    # For each true class, average weighted_score of true radical vs each false radical
    pos_neg_matrix: dict[str, dict[str, float]] = {}
    for true_cls in sorted(EVALUABLE_BLISP):
        class_samples = by_class.get(true_cls, [])
        if not class_samples:
            continue
        row = {}
        for rname in ALL_RADICALS:
            scores = [sv.radical_scores[rname].weighted_score for sv in class_samples
                      if rname in sv.radical_scores]
            row[rname] = sum(scores) / len(scores) if scores else 0.0
        pos_neg_matrix[true_cls] = row

    # 3. Confusion-overlap: for each radical pair, how often does radical B
    # have all_required_met when true class is A
    overlap_matrix: dict[str, dict[str, float]] = {}
    for true_cls in sorted(EVALUABLE_BLISP):
        class_samples = by_class.get(true_cls, [])
        if not class_samples:
            continue
        row = {}
        for rname in ALL_RADICALS:
            n_met = sum(1 for sv in class_samples
                        if rname in sv.radical_scores and sv.radical_scores[rname].all_required_met)
            row[rname] = n_met / len(class_samples) if class_samples else 0.0
        overlap_matrix[true_cls] = row

    # 4. Failure taxonomy
    notation_failures = 0   # true radical has low constraint satisfaction
    perception_failures = 0  # true radical constraints partially met but geometry noisy
    total_failures = 0
    taxonomy_details: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for sv in samples:
        rv_true = sv.radical_scores.get(sv.true_blisp)
        if rv_true is None:
            continue
        if rv_true.all_required_met:
            continue  # not a failure
        total_failures += 1

        # Categorize: if weighted_score > 0.5, perception issue (close but not quite)
        # if weighted_score < 0.3, notation issue (radical doesn't match at all)
        # otherwise ambiguous
        if rv_true.weighted_score >= 0.5:
            perception_failures += 1
            category = "perception"
        elif rv_true.weighted_score < 0.3:
            notation_failures += 1
            category = "notation"
        else:
            category = "ambiguous"
            perception_failures += 1  # lean toward perception

        # Which constraints failed?
        for cs in rv_true.constraint_scores:
            if not cs.satisfied:
                taxonomy_details[sv.true_blisp][f"{category}:{cs.constraint_type}:{cs.constraint_desc}"] += 1

    # 5. Per-class summary
    class_summaries = {}
    for true_cls in sorted(EVALUABLE_BLISP):
        class_samples = by_class.get(true_cls, [])
        if not class_samples:
            continue
        n = len(class_samples)
        n_all_met = sum(1 for sv in class_samples
                        if sv.radical_scores.get(true_cls) and
                        sv.radical_scores[true_cls].all_required_met)
        avg_weighted = sum(sv.radical_scores[true_cls].weighted_score
                          for sv in class_samples
                          if true_cls in sv.radical_scores) / n
        avg_contacts = sum(sv.n_inferred_contacts for sv in class_samples) / n
        class_summaries[true_cls] = {
            "n_samples": n,
            "all_constraints_met_rate": n_all_met / n,
            "avg_weighted_score": avg_weighted,
            "avg_inferred_contacts": avg_contacts,
        }

    return {
        "constraint_stats": constraint_stats,
        "pos_neg_matrix": pos_neg_matrix,
        "overlap_matrix": overlap_matrix,
        "failure_taxonomy": {
            "total_failures": total_failures,
            "notation_failures": notation_failures,
            "perception_failures": perception_failures,
            "taxonomy_details": dict(taxonomy_details),
        },
        "class_summaries": class_summaries,
        "n_samples": len(samples),
    }


# ── reporting ────────────────────────────────────────────────────

def print_report(results: dict):
    print(f"\n{'='*80}")
    print(f"  RADICAL VALIDATION REPORT")
    print(f"  {results['n_samples']} samples")
    print(f"{'='*80}")

    # Class summaries
    print(f"\n  ── Per-Class Summary ──")
    print(f"  {'Class':8s} {'N':>6s} {'AllMet%':>8s} {'AvgWt':>7s} {'AvgCon':>7s}")
    print(f"  {'-'*8} {'-'*6} {'-'*8} {'-'*7} {'-'*7}")
    for cls, info in sorted(results["class_summaries"].items()):
        print(f"  {cls:8s} {info['n_samples']:6d} {info['all_constraints_met_rate']:7.1%}"
              f" {info['avg_weighted_score']:7.3f} {info['avg_inferred_contacts']:7.1f}")

    # Per-radical constraint stats
    print(f"\n  ── Per-Radical Constraint Satisfaction (true radical on own class) ──")
    for rname, stats in sorted(results["constraint_stats"].items()):
        print(f"\n  {rname}:")
        print(f"    {'Type':22s} {'Constraint':45s} {'Sat%':>6s} {'AvgScr':>7s} {'Var':>7s} {'N':>5s}")
        print(f"    {'-'*22} {'-'*45} {'-'*6} {'-'*7} {'-'*7} {'-'*5}")
        for st in stats:
            print(f"    {st.constraint_type:22s} {st.constraint_desc:45s}"
                  f" {st.satisfaction_rate:5.1%} {st.avg_score:7.4f}"
                  f" {st.variance:7.4f} {st.n_samples:5d}")

    # Positive vs negative scoring matrix
    print(f"\n  ── Positive vs Negative Scoring (avg weighted score) ──")
    radicals_shown = sorted(r for r in ALL_RADICALS if r in EVALUABLE_BLISP)
    header = f"  {'True↓/Rad→':10s}" + "".join(f"{r:>8s}" for r in radicals_shown)
    print(header)
    print(f"  {'-'*10}" + "-"*8*len(radicals_shown))
    for true_cls in radicals_shown:
        row = results["pos_neg_matrix"].get(true_cls, {})
        vals = ""
        for r in radicals_shown:
            v = row.get(r, 0.0)
            marker = " *" if r == true_cls else "  "
            vals += f"{v:6.3f}{marker}"
        print(f"  {true_cls:10s}{vals}")
    print(f"  (* = true radical)")

    # Overlap matrix
    print(f"\n  ── Confusion-Overlap (rate all_required_met for radical R given true class C) ──")
    all_rads = sorted(ALL_RADICALS.keys())
    header = f"  {'True↓/Rad→':10s}" + "".join(f"{r:>7s}" for r in all_rads)
    print(header)
    for true_cls in radicals_shown:
        row = results["overlap_matrix"].get(true_cls, {})
        vals = ""
        for r in all_rads:
            v = row.get(r, 0.0)
            if v > 0.3:
                vals += f" {v:5.1%}"
            elif v > 0:
                vals += f" {v:5.1%}"
            else:
                vals += f"     ."
        print(f"  {true_cls:10s}{vals}")

    # Failure taxonomy
    ft = results["failure_taxonomy"]
    print(f"\n  ── Failure Taxonomy ──")
    print(f"  Total failures (true radical not fully met): {ft['total_failures']}")
    if ft['total_failures'] > 0:
        print(f"  Notation failures (weighted < 0.3):  {ft['notation_failures']}"
              f" ({ft['notation_failures']/ft['total_failures']:.1%})")
        print(f"  Perception failures (weighted >= 0.5): {ft['perception_failures']}"
              f" ({ft['perception_failures']/ft['total_failures']:.1%})")

    print(f"\n  Top constraint failures by class:")
    for cls in radicals_shown:
        details = ft["taxonomy_details"].get(cls, {})
        if not details:
            continue
        print(f"\n    {cls}:")
        sorted_details = sorted(details.items(), key=lambda x: -x[1])
        for desc, cnt in sorted_details[:8]:
            print(f"      {cnt:5d}  {desc}")

    # OGRD superclass analysis
    print(f"\n  ── OGRD Superclass Analysis ──")
    ogrd_row = results["pos_neg_matrix"].get("OGRD", {})
    if ogrd_row:
        print(f"  When true class is OGRD, avg weighted scores:")
        for r in sorted(ogrd_row.keys(), key=lambda k: -ogrd_row[k]):
            v = ogrd_row[r]
            if v > 0.01:
                print(f"    {r:8s}: {v:.3f}")
    ogrd_overlap = results["overlap_matrix"].get("OGRD", {})
    if ogrd_overlap:
        print(f"  OGRD samples where other radicals also have all_required_met:")
        for r in sorted(ogrd_overlap.keys(), key=lambda k: -ogrd_overlap[k]):
            v = ogrd_overlap[r]
            if v > 0.01 and r != "OGRD":
                print(f"    {r:8s}: {v:.1%}")

    # Stable vs fragile constraints
    print(f"\n  ── Stable vs Fragile Constraints ──")
    all_stats = []
    for rname, stats in results["constraint_stats"].items():
        for st in stats:
            if st.n_samples >= 10:
                all_stats.append((rname, st))

    if all_stats:
        all_stats_sorted = sorted(all_stats, key=lambda x: x[1].satisfaction_rate)
        print(f"\n  Most fragile (lowest satisfaction rate):")
        for rname, st in all_stats_sorted[:10]:
            print(f"    {rname:6s} {st.constraint_type:18s} {st.constraint_desc:40s}"
                  f" sat={st.satisfaction_rate:.1%} avg={st.avg_score:.4f}")

        print(f"\n  Most stable (highest satisfaction rate):")
        for rname, st in all_stats_sorted[-10:]:
            print(f"    {rname:6s} {st.constraint_type:18s} {st.constraint_desc:40s}"
                  f" sat={st.satisfaction_rate:.1%} avg={st.avg_score:.4f}")


def save_results(results: dict, out_dir: str):
    Path(out_dir).mkdir(parents=True, exist_ok=True)

    # Save constraint stats as JSON
    cs_data = {}
    for rname, stats in results["constraint_stats"].items():
        cs_data[rname] = [{
            "type": st.constraint_type,
            "desc": st.constraint_desc,
            "n": st.n_samples,
            "sat_rate": round(st.satisfaction_rate, 4),
            "avg_score": round(st.avg_score, 4),
            "variance": round(st.variance, 4),
        } for st in stats]

    with open(f"{out_dir}/constraint_stats.json", "w") as f:
        json.dump(cs_data, f, indent=2)

    # Save matrices
    with open(f"{out_dir}/pos_neg_matrix.json", "w") as f:
        json.dump({k: {k2: round(v2, 4) for k2, v2 in v.items()}
                   for k, v in results["pos_neg_matrix"].items()}, f, indent=2)

    with open(f"{out_dir}/overlap_matrix.json", "w") as f:
        json.dump({k: {k2: round(v2, 4) for k2, v2 in v.items()}
                   for k, v in results["overlap_matrix"].items()}, f, indent=2)

    # Save failure taxonomy
    with open(f"{out_dir}/failure_taxonomy.json", "w") as f:
        ft = results["failure_taxonomy"]
        json.dump({
            "total_failures": ft["total_failures"],
            "notation_failures": ft["notation_failures"],
            "perception_failures": ft["perception_failures"],
            "details": {k: dict(v) for k, v in ft["taxonomy_details"].items()},
        }, f, indent=2)

    # Save class summaries
    with open(f"{out_dir}/class_summaries.json", "w") as f:
        json.dump(results["class_summaries"], f, indent=2)

    print(f"  Results saved to {out_dir}/")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Radical constraint validation pipeline")
    parser.add_argument("--n-per-class", type=int, default=0,
                        help="Samples per class (0 = all)")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out-dir", type=str, default="data/radical_validation")
    args = parser.parse_args()

    print("Loading annotations...")
    anns = load_annotations()
    print(f"Loaded {len(anns)} annotations")

    evaluable = [a for a in anns if blisp_label(a.position) in EVALUABLE_BLISP
                 and a.pose1 is not None and a.pose2 is not None]
    print(f"Evaluable with poses: {len(evaluable)}")

    if args.n_per_class > 0:
        samples_ann = sample_by_class(evaluable, args.n_per_class, args.seed)
    else:
        samples_ann = evaluable

    print(f"\nValidating {len(samples_ann)} samples...")
    samples = []
    t0 = time.time()
    for i, ann in enumerate(samples_ann):
        sv = validate_sample(ann)
        if sv is not None:
            samples.append(sv)
        if (i + 1) % 500 == 0:
            elapsed = time.time() - t0
            rate = (i + 1) / elapsed
            eta = (len(samples_ann) - i - 1) / rate
            print(f"  [{i+1}/{len(samples_ann)}] {rate:.0f}/s, ETA {eta:.0f}s")

    elapsed = time.time() - t0
    print(f"Done in {elapsed:.1f}s ({len(samples)}/{len(samples_ann)} valid)")

    results = aggregate_results(samples)
    print_report(results)
    save_results(results, args.out_dir)


if __name__ == "__main__":
    main()
