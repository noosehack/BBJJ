"""Evaluate trained model on test set.

Usage:
    python -m tools.evaluate_model [--data DIR] [--model PATH] [--split test]
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader

from tools.dataset import BJJDataset
from tools.model import RadicalMLP
from tools.train import confusion_matrix, print_confusion_matrix, eval_epoch


def main():
    parser = argparse.ArgumentParser(description="Evaluate trained model")
    parser.add_argument("--data", type=str, default="data/dataset")
    parser.add_argument("--model", type=str, default="models/best_model.pt")
    parser.add_argument("--split", type=str, default="test")
    parser.add_argument("--symbolic", action="store_true", help="Use symbolic features")
    parser.add_argument("--batch", type=int, default=256)
    args = parser.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    checkpoint = torch.load(args.model, map_location=device, weights_only=True)
    use_sym = args.symbolic or checkpoint.get("symbolic", False)
    n_feat = checkpoint.get("n_features", 102)

    ds = BJJDataset(args.data, args.split, symbolic=use_sym)
    loader = DataLoader(ds, batch_size=args.batch, shuffle=False, num_workers=2)

    model = RadicalMLP(n_classes=ds.n_classes, n_features=n_feat).to(device)
    model.load_state_dict(checkpoint["model_state_dict"])

    criterion = torch.nn.CrossEntropyLoss()
    loss, acc, preds, labels = eval_epoch(model, loader, criterion, device)

    cm = confusion_matrix(labels, preds, ds.n_classes)

    print("=" * 60, file=sys.stderr)
    print(f"  Model Evaluation — {args.split} set", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    print(f"  Samples: {len(ds)}", file=sys.stderr)
    print(f"  Loss: {loss:.4f}", file=sys.stderr)
    print(f"  Accuracy: {acc:.1%}", file=sys.stderr)

    print(f"\n  Per-class accuracy:", file=sys.stderr)
    print(f"    {'Class':<10} {'Count':>7} {'Correct':>8} {'Acc':>7}", file=sys.stderr)
    print(f"    {'─' * 10} {'─' * 7} {'─' * 8} {'─' * 7}", file=sys.stderr)
    for i, name in enumerate(ds.class_names):
        total = cm[i].sum()
        correct = cm[i, i]
        class_acc = correct / total * 100 if total > 0 else 0
        print(f"    {name:<10} {total:>7} {correct:>8} {class_acc:>6.1f}%", file=sys.stderr)

    print(f"\n  Confusion matrix (rows=true, cols=pred):", file=sys.stderr)
    print_confusion_matrix(cm, ds.class_names)

    # Compare with symbolic labels from metadata
    if ds.meta:
        symbolic = [m["radical"] for m in ds.meta]
        pred_names = [ds.class_names[p] for p in preds]

        agree = sum(1 for s, p in zip(symbolic, pred_names) if s == p)
        print(f"\n  Model vs symbolic agreement: {agree}/{len(preds)} ({agree/len(preds):.1%})", file=sys.stderr)

        disagree_pairs = Counter(
            (s, p) for s, p in zip(symbolic, pred_names) if s != p
        )
        if disagree_pairs:
            print(f"\n  Top disagreements (symbolic → model):", file=sys.stderr)
            for (s, p), count in disagree_pairs.most_common(10):
                print(f"    {s:>8} → {p:<8}  {count:>5}", file=sys.stderr)

    results = {
        "split": args.split,
        "n_samples": len(ds),
        "loss": round(loss, 4),
        "accuracy": round(acc, 4),
        "per_class": {
            name: {
                "count": int(cm[i].sum()),
                "correct": int(cm[i, i]),
                "accuracy": round(cm[i, i] / cm[i].sum(), 4) if cm[i].sum() > 0 else 0,
            }
            for i, name in enumerate(ds.class_names)
        },
        "confusion_matrix": cm.tolist(),
    }
    out_path = Path(args.model).parent / f"eval_{args.split}.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n  Saved to {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
