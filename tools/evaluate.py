"""Evaluate annotation quality: compare inferred radicals against ViCoS ground truth."""

import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Optional

from tools.annotate import FPTRecord, annotate_batch, export_fpt, load_fpt


# Which BLISP labels map to which radicals (one label may map to several)
BLISP_TO_RADICALS = {
    "MNT":     {"MNT"},
    "BCTR":    {"BCTR"},
    "GRD":     {"DLR", "SLX", "RDLR", "LSSO", "OMOP", "CGRD"},
    "GRD_CLP": {"CGRD", "DLR", "SLX", "RDLR"},
    "HGRD":    {"DLR", "SLX", "RDLR"},
    "5050":    {"DLR", "SLX"},
    "SCTR":    set(),
    "TRTL":    set(),
    "STND":    set(),
    "TKDN":    set(),
}


def evaluate(records: list[FPTRecord]) -> dict:
    total = len(records)
    has_match = sum(1 for r in records if r.radical_match is not None)
    has_poses = sum(1 for r in records if r.contacts)

    by_blisp = defaultdict(list)
    for r in records:
        by_blisp[r.blisp_label].append(r)

    per_class = {}
    compatible_total = 0
    compatible_correct = 0

    for label, recs in sorted(by_blisp.items()):
        expected_radicals = BLISP_TO_RADICALS.get(label, set())
        n = len(recs)
        matched = sum(1 for r in recs if r.radical_match is not None)
        if expected_radicals:
            correct = sum(
                1 for r in recs
                if r.radical_match in expected_radicals
            )
            compatible_total += n
            compatible_correct += correct
        else:
            correct = None

        radical_dist = Counter(r.radical_match for r in recs)
        avg_conf = (
            sum(r.match_confidence for r in recs if r.radical_match) / matched
            if matched > 0 else 0.0
        )

        per_class[label] = {
            "count": n,
            "has_match": matched,
            "correct": correct,
            "accuracy": round(correct / n, 4) if correct is not None and n > 0 else None,
            "avg_confidence": round(avg_conf, 4),
            "radical_distribution": dict(radical_dist.most_common()),
        }

    compatible_acc = (
        round(compatible_correct / compatible_total, 4)
        if compatible_total > 0 else None
    )

    return {
        "total": total,
        "has_poses": has_poses,
        "has_match": has_match,
        "compatible_accuracy": compatible_acc,
        "compatible_total": compatible_total,
        "compatible_correct": compatible_correct,
        "per_class": per_class,
    }


def print_report(result: dict) -> None:
    print(f"\n{'='*60}")
    print(f"  BLISP Annotation Evaluation Report")
    print(f"{'='*60}")
    print(f"  Total records:        {result['total']:>8}")
    print(f"  With poses:           {result['has_poses']:>8}")
    print(f"  With radical match:   {result['has_match']:>8}")

    if result["compatible_accuracy"] is not None:
        pct = result["compatible_accuracy"] * 100
        print(f"  Compatible accuracy:  {pct:>7.1f}%  "
              f"({result['compatible_correct']}/{result['compatible_total']})")

    print(f"\n{'─'*60}")
    print(f"  {'Label':<10} {'Count':>7} {'Match':>7} {'Correct':>8} {'Acc':>7} {'AvgConf':>8}")
    print(f"  {'─'*10} {'─'*7} {'─'*7} {'─'*8} {'─'*7} {'─'*8}")
    for label, cls in sorted(result["per_class"].items()):
        correct_str = f"{cls['correct']:>8}" if cls["correct"] is not None else "     n/a"
        acc_str = f"{cls['accuracy']*100:>6.1f}%" if cls["accuracy"] is not None else "    n/a"
        print(f"  {label:<10} {cls['count']:>7} {cls['has_match']:>7} "
              f"{correct_str} {acc_str} {cls['avg_confidence']:>7.3f}")

    print(f"\n{'─'*60}")
    print(f"  Radical distribution per class:")
    for label, cls in sorted(result["per_class"].items()):
        dist = cls["radical_distribution"]
        top = sorted(dist.items(), key=lambda x: -x[1])[:5]
        dist_str = ", ".join(f"{k}:{v}" for k, v in top)
        print(f"    {label:<10} {dist_str}")
    print()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Evaluate BLISP annotations")
    parser.add_argument("--fpt", type=Path, help="Load existing FPT records from JSON")
    parser.add_argument("--export", type=Path, help="Export FPT records to JSON")
    parser.add_argument("--limit", type=int, help="Limit number of annotations to process")
    parser.add_argument("--smooth", type=int, default=0, metavar="K",
                        help="(experimental) Apply temporal score smoothing with ±K frame window")
    parser.add_argument("--wsmooth", type=int, default=0, metavar="K",
                        help="(experimental) Apply confidence-weighted smoothing with ±K frame window")
    parser.add_argument("--persist", type=int, default=8, metavar="N",
                        help="Require N consecutive frames before label switch (default: 8)")
    parser.add_argument("--no-persist", action="store_true",
                        help="Disable default persistence filter")
    parser.add_argument("--videos", type=str, default=None,
                        help="Comma-separated video prefixes to include (e.g. 00,14,15)")
    parser.add_argument("--flicker", action="store_true",
                        help="Report label flicker rate per video")
    args = parser.parse_args()

    if args.fpt and args.fpt.exists():
        print(f"Loading FPT records from {args.fpt}...", file=sys.stderr)
        records = load_fpt(args.fpt)
    else:
        from data.loader import load_annotations
        print("Loading annotations...", file=sys.stderr)
        annotations = load_annotations()
        if args.videos:
            prefixes = tuple(v.strip() for v in args.videos.split(","))
            annotations = [a for a in annotations if a.image[:2] in prefixes]
            print(f"Filtered to videos {prefixes}: {len(annotations)} annotations", file=sys.stderr)
        if args.limit:
            annotations = annotations[:args.limit]
        print(f"Annotating {len(annotations)} images...", file=sys.stderr)
        records = annotate_batch(annotations, progress=True)
        if args.export:
            export_fpt(records, args.export)
            print(f"Exported to {args.export}", file=sys.stderr)

    if args.smooth > 0:
        from tools.temporal import smooth_scores
        print(f"Applying temporal smoothing (k={args.smooth})...", file=sys.stderr)
        records = smooth_scores(records, k=args.smooth)

    if args.wsmooth > 0:
        from tools.temporal import weighted_smooth
        print(f"Applying weighted smoothing (k={args.wsmooth})...", file=sys.stderr)
        records = weighted_smooth(records, k=args.wsmooth)

    if not args.no_persist and args.persist > 0:
        from tools.temporal import apply_persistence
        print(f"Applying persistence filter (min_frames={args.persist})...", file=sys.stderr)
        records = apply_persistence(records, min_frames=args.persist)

    result = evaluate(records)
    print_report(result)

    if args.flicker:
        from tools.temporal import flicker_rate
        rates = flicker_rate(records)
        print(f"{'─'*60}")
        print(f"  Flicker rate (label switches / frame):")
        for vid, rate in sorted(rates.items()):
            if vid == "overall":
                continue
            print(f"    vid {vid}: {rate:.4f}")
        print(f"    overall: {rates['overall']:.4f}")
        print()
