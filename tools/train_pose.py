"""Fine-tune YOLO11-pose on ViCoS BJJ dataset."""

import argparse
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Fine-tune YOLO11 pose on BJJ data")
    parser.add_argument("--data", type=str, default="data/yolo_pose/dataset.yaml",
                        help="Path to dataset.yaml")
    parser.add_argument("--model", type=str, default="yolo11m-pose.pt",
                        help="Base model to fine-tune")
    parser.add_argument("--epochs", type=int, default=10,
                        help="Training epochs")
    parser.add_argument("--imgsz", type=int, default=640,
                        help="Image size")
    parser.add_argument("--batch", type=int, default=16,
                        help="Batch size")
    parser.add_argument("--project", type=str, default="models_pose",
                        help="Output directory for runs")
    parser.add_argument("--name", type=str, default="bjj_finetune",
                        help="Run name")
    parser.add_argument("--lr0", type=float, default=0.001,
                        help="Initial learning rate")
    parser.add_argument("--freeze", type=int, default=0,
                        help="Number of backbone layers to freeze (0=none)")
    args = parser.parse_args()

    data_path = Path(args.data)
    if not data_path.exists():
        print(f"Dataset YAML not found: {data_path}", file=sys.stderr)
        print("Run first: python -m tools.export_yolo_pose", file=sys.stderr)
        sys.exit(1)

    try:
        from ultralytics import YOLO
    except ImportError:
        print("ultralytics required: pip install ultralytics", file=sys.stderr)
        sys.exit(1)

    model = YOLO(args.model)

    print(f"Fine-tuning {args.model} on {args.data}", file=sys.stderr)
    print(f"  epochs={args.epochs} imgsz={args.imgsz} batch={args.batch}", file=sys.stderr)
    print(f"  lr0={args.lr0} freeze={args.freeze}", file=sys.stderr)
    print(f"  output: {args.project}/{args.name}", file=sys.stderr)

    train_args = dict(
        data=str(data_path.resolve()),
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        project=args.project,
        name=args.name,
        lr0=args.lr0,
        pose=12.0,
        exist_ok=True,
        verbose=True,
    )

    if args.freeze > 0:
        train_args["freeze"] = args.freeze

    results = model.train(**train_args)

    best_path = Path(args.project) / args.name / "weights" / "best.pt"
    if best_path.exists():
        print(f"\nBest model: {best_path}", file=sys.stderr)
        print(f"\nTo use in inference:", file=sys.stderr)
        print(f"  python -m tools.infer_image image.jpg --model {best_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
