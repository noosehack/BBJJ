"""Train MLP baseline: keypoints → RAD.

Usage:
    python -m tools.train [--epochs N] [--lr LR] [--batch BATCH] [--data DIR] [--out DIR]
    python -m tools.train --symbolic [--out models_sym]
"""

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from tools.dataset import BJJDataset
from tools.model import RadicalMLP


def confusion_matrix(y_true: np.ndarray, y_pred: np.ndarray, n_classes: int) -> np.ndarray:
    cm = np.zeros((n_classes, n_classes), dtype=np.int64)
    for t, p in zip(y_true, y_pred):
        cm[t, p] += 1
    return cm


def print_confusion_matrix(cm: np.ndarray, class_names: list[str], file=sys.stderr):
    n = len(class_names)
    header = "          " + " ".join(f"{name:>6}" for name in class_names)
    print(header, file=file)
    for i in range(n):
        row = f"  {class_names[i]:<6}  " + " ".join(f"{cm[i, j]:>6}" for j in range(n))
        total = cm[i].sum()
        acc = cm[i, i] / total * 100 if total > 0 else 0
        row += f"  | {acc:5.1f}%"
        print(row, file=file)


def train_epoch(model, loader, criterion, optimizer, device):
    model.train()
    total_loss = 0.0
    correct = 0
    total = 0
    for X, y in loader:
        X, y = X.to(device), y.to(device)
        optimizer.zero_grad()
        logits = model(X)
        loss = criterion(logits, y)
        loss.backward()
        optimizer.step()
        total_loss += loss.item() * X.size(0)
        correct += (logits.argmax(1) == y).sum().item()
        total += X.size(0)
    return total_loss / total, correct / total


@torch.no_grad()
def eval_epoch(model, loader, criterion, device):
    model.eval()
    total_loss = 0.0
    correct = 0
    total = 0
    all_preds = []
    all_labels = []
    for X, y in loader:
        X, y = X.to(device), y.to(device)
        logits = model(X)
        loss = criterion(logits, y)
        total_loss += loss.item() * X.size(0)
        preds = logits.argmax(1)
        correct += (preds == y).sum().item()
        total += X.size(0)
        all_preds.append(preds.cpu().numpy())
        all_labels.append(y.cpu().numpy())
    return (
        total_loss / total,
        correct / total,
        np.concatenate(all_preds),
        np.concatenate(all_labels),
    )


def main():
    parser = argparse.ArgumentParser(description="Train MLP baseline")
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--batch", type=int, default=256)
    parser.add_argument("--data", type=str, default="data/dataset")
    parser.add_argument("--symbolic", action="store_true", help="Include symbolic features (102+30=132 input)")
    parser.add_argument("--out", type=str, default=None)
    args = parser.parse_args()

    if args.out is None:
        args.out = "models_sym" if args.symbolic else "models"

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Device: {device}", file=sys.stderr)

    train_ds = BJJDataset(args.data, "train", symbolic=args.symbolic)
    val_ds = BJJDataset(args.data, "val", symbolic=args.symbolic)

    train_loader = DataLoader(train_ds, batch_size=args.batch, shuffle=True, num_workers=2)
    val_loader = DataLoader(val_ds, batch_size=args.batch, shuffle=False, num_workers=2)

    n_feat = train_ds.n_features
    mode = "keypoints + symbolic" if args.symbolic else "keypoints only"
    print(f"Train: {len(train_ds)}, Val: {len(val_ds)}, Classes: {train_ds.n_classes}", file=sys.stderr)
    print(f"Features: {n_feat} ({mode})", file=sys.stderr)

    model = RadicalMLP(n_classes=train_ds.n_classes, n_features=n_feat).to(device)
    weights = train_ds.class_weights().to(device)
    criterion = nn.CrossEntropyLoss(weight=weights)
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode="max", factor=0.5, patience=5,
    )

    best_val_acc = 0.0
    best_epoch = 0
    patience_counter = 0
    patience_limit = 15

    print(f"\n{'Epoch':>5} {'TrLoss':>8} {'TrAcc':>7} {'VlLoss':>8} {'VlAcc':>7} {'LR':>9}", file=sys.stderr)
    print("─" * 52, file=sys.stderr)

    t0 = time.time()
    for epoch in range(1, args.epochs + 1):
        train_loss, train_acc = train_epoch(model, train_loader, criterion, optimizer, device)
        val_loss, val_acc, val_preds, val_labels = eval_epoch(model, val_loader, criterion, device)
        lr = optimizer.param_groups[0]["lr"]
        scheduler.step(val_acc)

        improved = ""
        if val_acc > best_val_acc:
            best_val_acc = val_acc
            best_epoch = epoch
            patience_counter = 0
            torch.save({
                "epoch": epoch,
                "model_state_dict": model.state_dict(),
                "val_acc": val_acc,
                "class_names": train_ds.class_names,
                "n_classes": train_ds.n_classes,
                "n_features": n_feat,
                "symbolic": args.symbolic,
            }, out_dir / "best_model.pt")
            improved = " *"
        else:
            patience_counter += 1

        print(
            f"{epoch:>5} {train_loss:>8.4f} {train_acc:>6.1%} {val_loss:>8.4f} {val_acc:>6.1%} {lr:>9.1e}{improved}",
            file=sys.stderr,
        )

        if patience_counter >= patience_limit:
            print(f"\nEarly stopping at epoch {epoch}", file=sys.stderr)
            break

    elapsed = time.time() - t0
    print(f"\nTraining complete in {elapsed:.0f}s", file=sys.stderr)
    print(f"Best val accuracy: {best_val_acc:.1%} (epoch {best_epoch})", file=sys.stderr)

    # Final confusion matrix on val set with best model
    checkpoint = torch.load(out_dir / "best_model.pt", weights_only=True)
    model.load_state_dict(checkpoint["model_state_dict"])
    _, _, val_preds, val_labels = eval_epoch(model, val_loader, criterion, device)

    cm = confusion_matrix(val_labels, val_preds, train_ds.n_classes)
    print(f"\nVal confusion matrix (rows=true, cols=pred):", file=sys.stderr)
    print_confusion_matrix(cm, train_ds.class_names)

    # Save training summary
    summary = {
        "best_epoch": best_epoch,
        "best_val_acc": round(best_val_acc, 4),
        "epochs_trained": epoch,
        "elapsed_seconds": round(elapsed, 1),
        "lr": args.lr,
        "batch_size": args.batch,
        "device": str(device),
        "n_features": n_feat,
        "symbolic": args.symbolic,
        "confusion_matrix": cm.tolist(),
    }
    with open(out_dir / "train_summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\nSaved to {out_dir}/", file=sys.stderr)


if __name__ == "__main__":
    main()
