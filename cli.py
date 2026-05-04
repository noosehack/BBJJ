#!/usr/bin/env python3
"""BJJ-BLISP CLI.

Usage:
    python cli.py --dic                  List all radicals
    python cli.py --rad MNT             Show a specific radical
    python cli.py --match 1400294       Match a single image
    python cli.py --eval                Run evaluation (persist N=8 default)
    python cli.py --export-fpt 14       Export BLISP FPT for video prefix 14
"""

import argparse
import sys
from pathlib import Path


def cmd_dic():
    from dic.radicals import ALL_RADICALS
    for name, rad in sorted(ALL_RADICALS.items()):
        n_con = len(rad.contacts)
        n_forb = len(rad.forbidden_contacts)
        n_frame = len(rad.frame_constraints)
        forb_str = f"  forbidden:{n_forb}" if n_forb else ""
        print(f"  {name:<8} {n_con} CON  {n_frame} FRM{forb_str}")


def cmd_rad(code: str):
    from dic.radicals import ALL_RADICALS
    code = code.upper()
    if code not in ALL_RADICALS:
        print(f"Unknown radical: {code}", file=sys.stderr)
        print(f"Available: {', '.join(sorted(ALL_RADICALS))}", file=sys.stderr)
        sys.exit(1)
    print(ALL_RADICALS[code])


def cmd_match(image_id: str):
    from data.loader import load_annotations
    from data.label_map import normalize
    from tools.contact_inference import infer_contacts, infer_frame_constraints, match_radical
    from tools.annotate import annotate_one
    from tools.blisp_export import fpt_to_sexpr

    annotations = load_annotations()
    matches = [a for a in annotations if a.image == image_id]
    if not matches:
        print(f"Image {image_id} not found in dataset", file=sys.stderr)
        sys.exit(1)

    for ann in matches:
        norm = normalize(ann)
        rec = annotate_one(norm)
        print(fpt_to_sexpr(rec))
        print()


def cmd_eval(args):
    from tools.annotate import annotate_batch, load_fpt, export_fpt
    from tools.evaluate import evaluate, print_report

    if args.fpt and Path(args.fpt).exists():
        print(f"Loading FPT records from {args.fpt}...", file=sys.stderr)
        records = load_fpt(Path(args.fpt))
    else:
        from data.loader import load_annotations
        print("Loading annotations...", file=sys.stderr)
        annotations = load_annotations()
        if args.videos:
            prefixes = tuple(v.strip() for v in args.videos.split(","))
            annotations = [a for a in annotations if a.image[:2] in prefixes]
            print(f"Filtered to videos {prefixes}: {len(annotations)}", file=sys.stderr)
        if args.limit:
            annotations = annotations[:args.limit]
        print(f"Annotating {len(annotations)} images...", file=sys.stderr)
        records = annotate_batch(annotations, progress=True)

    if not args.no_persist and args.persist > 0:
        from tools.temporal import apply_persistence
        print(f"Applying persistence (N={args.persist})...", file=sys.stderr)
        records = apply_persistence(records, min_frames=args.persist)

    result = evaluate(records)
    print_report(result)

    if args.flicker:
        from tools.temporal import flicker_rate
        rates = flicker_rate(records)
        print(f"  Flicker: {rates['overall']:.4f}")


def cmd_export_fpt(args):
    from tools.annotate import annotate_batch, load_fpt, export_fpt
    from tools.blisp_export import export_sexpr

    if args.fpt and Path(args.fpt).exists():
        print(f"Loading FPT records from {args.fpt}...", file=sys.stderr)
        records = load_fpt(Path(args.fpt))
    else:
        from data.loader import load_annotations
        print("Loading annotations...", file=sys.stderr)
        annotations = load_annotations()
        prefix = args.export_fpt
        if prefix and prefix != "all":
            prefixes = tuple(v.strip() for v in prefix.split(","))
            annotations = [a for a in annotations if a.image[:2] in prefixes]
            print(f"Filtered to videos {prefixes}: {len(annotations)}", file=sys.stderr)
        if args.limit:
            annotations = annotations[:args.limit]
        print(f"Annotating {len(annotations)} images...", file=sys.stderr)
        records = annotate_batch(annotations, progress=True)

    if not args.no_persist and args.persist > 0:
        from tools.temporal import apply_persistence
        print(f"Applying persistence (N={args.persist})...", file=sys.stderr)
        records = apply_persistence(records, min_frames=args.persist)

    fmt = args.format
    out = args.output or f"blisp/export/fpt_export.{fmt}"

    if fmt == "json":
        export_fpt(records, Path(out))
    else:
        export_sexpr(records, Path(out))

    print(f"Exported {len(records)} records to {out}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(
        prog="bjj",
        description="BJJ-BLISP: image-to-notation position recognition",
    )
    parser.add_argument("--dic", action="store_true",
                        help="List all radicals")
    parser.add_argument("--rad", type=str, metavar="CODE",
                        help="Show a specific radical by code")
    parser.add_argument("--match", type=str, metavar="IMAGE_ID",
                        help="Run matching on a single image and print BLISP FPT")
    parser.add_argument("--eval", action="store_true",
                        help="Run evaluation pipeline")
    parser.add_argument("--export-fpt", type=str, metavar="VIDEO",
                        help="Export BLISP FPT records (video prefix, comma-list, or 'all')")

    parser.add_argument("--persist", type=int, default=8,
                        help="Persistence filter N (default: 8)")
    parser.add_argument("--no-persist", action="store_true",
                        help="Disable persistence filter")
    parser.add_argument("--fpt", type=str,
                        help="Load cached FPT records from JSON")
    parser.add_argument("--videos", type=str,
                        help="Comma-separated video prefixes for --eval")
    parser.add_argument("--limit", type=int,
                        help="Limit number of annotations")
    parser.add_argument("--format", choices=["sexpr", "json"], default="sexpr",
                        help="Export format (default: sexpr)")
    parser.add_argument("--output", "-o", type=str,
                        help="Output file path")
    parser.add_argument("--flicker", action="store_true",
                        help="Report flicker rate with --eval")

    args = parser.parse_args()

    if args.dic:
        cmd_dic()
    elif args.rad:
        cmd_rad(args.rad)
    elif args.match:
        cmd_match(args.match)
    elif args.eval:
        cmd_eval(args)
    elif args.export_fpt:
        cmd_export_fpt(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
