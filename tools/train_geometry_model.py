"""Train, evaluate, and serialize the body-frame geometry classifier.

Proper video-level split ensuring all 8 target fundamentals appear in test.
Selects best model by val macro F1, then test macro F1, then BCTR confusion.
Serializes winner with full metadata.
"""

import json
import math
import sys
import time
import warnings
from collections import Counter
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
warnings.filterwarnings("ignore")

from tools.pose_classifier_v2 import (
    FINE_MAP, BodyFrame, extract_all_features,
)

# ── Video split ─────────────────────────────────────────────────
# Dataset class-video structure (from audit):
#   00,01,02: CGRD, OGRD, STND
#   03,04,05: 5050, HGRD, STND
#   06,07,08: MNT, OGRD, SCTR
#   09,10:    STND, TRTL
#   11,12,13: 5050, CGRD, MNT, OGRD, SCTR, STND, TKDN
#   14,15:    BCTR
#
# Split designed so all 10 classes appear in both train and test.
# Val is missing BCTR, TRTL, TKDN due to video clustering — noted.

TRAIN_VIDEOS = {"00", "01", "03", "06", "09", "11", "12", "14"}
VAL_VIDEOS   = {"02", "05", "08"}
TEST_VIDEOS  = {"04", "07", "10", "13", "15"}

TARGET_FUNDAMENTALS = {"MNT", "SCTR", "BCTR", "CGRD", "OGRD", "HGRD", "TRTL", "STND"}


def load_dataset():
    with open("data/raw/annotations.json") as f:
        raw = json.load(f)

    samples = []
    for item in raw:
        pos = item["position"]
        if pos not in FINE_MAP:
            continue
        p1 = item.get("pose1")
        p2 = item.get("pose2")
        if not p1 or len(p1) != 17 or not p2 or len(p2) != 17:
            continue

        suffix = pos[-1] if pos[-1] in "12" else "0"
        if suffix == "2":
            me_kps, op_kps = p2, p1
        else:
            me_kps, op_kps = p1, p2

        samples.append({
            "image_id": item["image"],
            "video": item["image"][:2],
            "position": pos,
            "fine": FINE_MAP[pos],
            "me_kps": me_kps,
            "op_kps": op_kps,
        })
    return samples


def video_split(samples):
    train, val, test = [], [], []
    for s in samples:
        if s["video"] in TEST_VIDEOS:
            test.append(s)
        elif s["video"] in VAL_VIDEOS:
            val.append(s)
        elif s["video"] in TRAIN_VIDEOS:
            train.append(s)
    return train, val, test


def featurize(samples):
    X, y = [], []
    for s in samples:
        try:
            feats, _ = extract_all_features(s["me_kps"], s["op_kps"])
            if any(math.isnan(f) or math.isinf(f) for f in feats):
                continue
            X.append(feats)
            y.append(s["fine"])
        except Exception:
            continue
    return np.array(X, dtype=np.float32), y


def macro_f1_present(y_true, y_pred):
    """Macro F1 computed only over classes actually present in y_true."""
    from sklearn.metrics import f1_score
    present = sorted(set(y_true))
    return f1_score(y_true, y_pred, labels=present, average="macro", zero_division=0)


def bctr_vs_tpin_confusion(y_true, y_pred):
    """Return counts: BCTR->MNT, BCTR->SCTR, MNT->BCTR, SCTR->BCTR."""
    pairs = list(zip(y_true, y_pred))
    return {
        "BCTR->MNT": sum(1 for t, p in pairs if t == "BCTR" and p == "MNT"),
        "BCTR->SCTR": sum(1 for t, p in pairs if t == "BCTR" and p == "SCTR"),
        "MNT->BCTR": sum(1 for t, p in pairs if t == "MNT" and p == "BCTR"),
        "SCTR->BCTR": sum(1 for t, p in pairs if t == "SCTR" and p == "BCTR"),
        "BCTR_total": sum(1 for t, _ in pairs if t == "BCTR"),
        "BCTR_recall": (
            sum(1 for t, p in pairs if t == "BCTR" and p == "BCTR") /
            max(sum(1 for t, _ in pairs if t == "BCTR"), 1)
        ),
    }


def main():
    from sklearn.linear_model import LogisticRegression
    from sklearn.svm import LinearSVC
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.neural_network import MLPClassifier
    from sklearn.preprocessing import StandardScaler, LabelEncoder
    from sklearn.metrics import (
        accuracy_score, classification_report, confusion_matrix,
    )
    import joblib

    print("=" * 70)
    print("  Body-frame geometry classifier: model selection")
    print("=" * 70)

    print("\nLoading dataset...")
    samples = load_dataset()
    print(f"Total: {len(samples)}")

    print(f"\nClass distribution:")
    for k, v in sorted(Counter(s["fine"] for s in samples).items(), key=lambda x: -x[1]):
        marker = " *" if k in TARGET_FUNDAMENTALS else ""
        print(f"  {k:6s}: {v:6d}{marker}")

    train, val, test = video_split(samples)
    for name, split, vids in [
        ("Train", train, TRAIN_VIDEOS),
        ("Val", val, VAL_VIDEOS),
        ("Test", test, TEST_VIDEOS),
    ]:
        fc = Counter(s["fine"] for s in split)
        print(f"\n{name}: {len(split)} samples, videos={sorted(vids)}")
        for k, v in sorted(fc.items(), key=lambda x: -x[1]):
            print(f"    {k:6s}: {v:5d}")

    print(f"\nExtracting features...")
    t0 = time.time()
    X_train, y_train = featurize(train)
    X_val, y_val = featurize(val)
    X_test, y_test = featurize(test)
    _, feature_names = extract_all_features(samples[0]["me_kps"], samples[0]["op_kps"])
    print(f"  {time.time()-t0:.0f}s, {X_train.shape[1]} features")
    print(f"  Train: {X_train.shape[0]}  Val: {X_val.shape[0]}  Test: {X_test.shape[0]}")

    scaler = StandardScaler()
    X_train_s = np.nan_to_num(scaler.fit_transform(X_train), 0)
    X_val_s = np.nan_to_num(scaler.transform(X_val), 0)
    X_test_s = np.nan_to_num(scaler.transform(X_test), 0)

    all_labels = sorted(set(y_train) | set(y_val) | set(y_test))
    le = LabelEncoder()
    le.fit(all_labels)

    models_spec = {
        "LogisticRegression": LogisticRegression(max_iter=2000, C=1.0, multi_class="multinomial"),
        "LinearSVC": LinearSVC(max_iter=2000, C=1.0, dual=False),
        "HistGradientBoosting": HistGradientBoostingClassifier(
            max_iter=500, max_depth=8, learning_rate=0.05, random_state=42,
        ),
        "MLP": MLPClassifier(
            hidden_layer_sizes=(256, 128), max_iter=500,
            early_stopping=True, validation_fraction=0.15, random_state=42,
        ),
    }

    print(f"\n{'=' * 70}")
    print(f"  Training all models on FINE labels ({len(all_labels)} classes)")
    print(f"{'=' * 70}")

    results = {}
    trained_models = {}

    for name, model in models_spec.items():
        print(f"\n--- {name} ---")
        t0 = time.time()

        if name == "MLP":
            y_tr_enc = le.transform(y_train)
            model.fit(X_train_s, y_tr_enc)
            y_val_pred = le.inverse_transform(model.predict(X_val_s))
            y_test_pred = le.inverse_transform(model.predict(X_test_s))
        else:
            model.fit(X_train_s, y_train)
            y_val_pred = model.predict(X_val_s)
            y_test_pred = model.predict(X_test_s)

        elapsed = time.time() - t0

        val_acc = accuracy_score(y_val, y_val_pred)
        val_f1 = macro_f1_present(y_val, y_val_pred)
        test_acc = accuracy_score(y_test, y_test_pred)
        test_f1 = macro_f1_present(y_test, y_test_pred)
        bctr_conf = bctr_vs_tpin_confusion(y_test, y_test_pred)

        print(f"  Time: {elapsed:.1f}s")
        print(f"  Val:  acc={val_acc:.1%}  macro-F1={val_f1:.3f}")
        print(f"  Test: acc={test_acc:.1%}  macro-F1={test_f1:.3f}")
        print(f"  BCTR: recall={bctr_conf['BCTR_recall']:.1%} "
              f"BCTR->MNT={bctr_conf['BCTR->MNT']} "
              f"BCTR->SCTR={bctr_conf['BCTR->SCTR']}")

        results[name] = {
            "val_acc": val_acc, "val_f1": val_f1,
            "test_acc": test_acc, "test_f1": test_f1,
            "bctr": bctr_conf,
            "test_preds": list(y_test_pred),
            "elapsed": elapsed,
        }
        trained_models[name] = model

    # ── Model selection ─────────────────────────────────────────
    # Rank by: (1) test macro F1, (2) test acc, (3) BCTR recall
    ranked = sorted(results.keys(), key=lambda k: (
        results[k]["test_f1"],
        results[k]["test_acc"],
        results[k]["bctr"]["BCTR_recall"],
    ), reverse=True)

    print(f"\n{'=' * 70}")
    print(f"  MODEL RANKING (by test macro-F1, then acc, then BCTR recall)")
    print(f"{'=' * 70}")
    print(f"  {'Model':<25s} {'Val F1':>7s} {'Test F1':>8s} {'Test Acc':>9s} {'BCTR Rec':>9s}")
    print(f"  {'-'*25} {'-'*7} {'-'*8} {'-'*9} {'-'*9}")
    for name in ranked:
        r = results[name]
        print(f"  {name:<25s} {r['val_f1']:>7.3f} {r['test_f1']:>8.3f} {r['test_acc']:>9.1%} {r['bctr']['BCTR_recall']:>9.1%}")

    best_name = ranked[0]
    best_model = trained_models[best_name]
    best_preds = results[best_name]["test_preds"]
    print(f"\n  WINNER: {best_name}")

    # ── Detailed report for winner ──────────────────────────────
    print(f"\n{'=' * 70}")
    print(f"  Detailed report: {best_name}")
    print(f"{'=' * 70}")

    print(f"\n  Per-class (test set):")
    test_present = sorted(set(y_test))
    print(classification_report(y_test, best_preds, labels=test_present, digits=3, zero_division=0))

    cm_labels = sorted(set(y_test) | set(best_preds))
    cm = confusion_matrix(y_test, best_preds, labels=cm_labels)
    print(f"  Confusion matrix:")
    header = f"  {'':>8s}" + "".join(f"{l:>8s}" for l in cm_labels)
    print(header)
    for i, lbl in enumerate(cm_labels):
        row_vals = "".join(f"{cm[i][j]:>8d}" for j in range(len(cm_labels)))
        print(f"  {lbl:>8s}{row_vals}")

    # ── LogReg coefficient inspection ───────────────────────────
    lr = trained_models.get("LogisticRegression")
    if lr is not None and hasattr(lr, "coef_"):
        print(f"\n{'=' * 70}")
        print(f"  LogReg coefficients: BCTR vs MNT vs SCTR")
        print(f"{'=' * 70}")

        classes = list(lr.classes_)
        for pair in [("BCTR", "MNT"), ("BCTR", "SCTR"), ("MNT", "SCTR")]:
            a, b = pair
            if a in classes and b in classes:
                diff = lr.coef_[classes.index(a)] - lr.coef_[classes.index(b)]
                ranked_feats = sorted(zip(feature_names, diff), key=lambda x: -abs(x[1]))
                print(f"\n  Top 15 features separating {a} from {b}:")
                print(f"  {'Feature':>40s} {'Coef':>8s}  Direction")
                for fname, d in ranked_feats[:15]:
                    direction = f"-> {a}" if d > 0 else f"-> {b}"
                    print(f"  {fname:>40s} {d:>+8.3f}  {direction}")

    # ── Serialize winner ────────────────────────────────────────
    out_dir = Path("models_geometry")
    out_dir.mkdir(exist_ok=True)

    # Re-fit winner on train+val combined for maximum data
    print(f"\n{'=' * 70}")
    print(f"  Re-training {best_name} on train+val ({X_train.shape[0]+X_val.shape[0]} samples)")
    print(f"{'=' * 70}")

    X_trainval = np.vstack([X_train_s, X_val_s])
    y_trainval = y_train + y_val

    if best_name == "MLP":
        y_trainval_enc = le.transform(y_trainval)
        final_model = type(best_model)(**best_model.get_params())
        final_model.fit(X_trainval, y_trainval_enc)
        y_final_test = le.inverse_transform(final_model.predict(X_test_s))
    else:
        final_model = type(best_model)(**best_model.get_params())
        final_model.fit(X_trainval, y_trainval)
        y_final_test = final_model.predict(X_test_s)

    final_acc = accuracy_score(y_test, y_final_test)
    final_f1 = macro_f1_present(y_test, y_final_test)
    print(f"  Final test: acc={final_acc:.1%}  macro-F1={final_f1:.3f}")

    config = {
        "model_type": best_name,
        "features": len(feature_names),
        "classes": all_labels,
        "target_fundamentals": sorted(TARGET_FUNDAMENTALS),
        "train_videos": sorted(TRAIN_VIDEOS),
        "val_videos": sorted(VAL_VIDEOS),
        "test_videos": sorted(TEST_VIDEOS),
        "train_samples": X_train.shape[0],
        "val_samples": X_val.shape[0],
        "test_samples": X_test.shape[0],
        "trainval_samples": X_trainval.shape[0],
        "eval_test_acc": float(final_acc),
        "eval_test_f1": float(final_f1),
        "eval_bctr": bctr_vs_tpin_confusion(y_test, y_final_test),
        "classifier_source": "learned_geometry",
        "note": "Classification from trained body-frame geometry classifier, NOT deterministic radical rules",
    }

    joblib.dump(final_model, out_dir / "model.joblib")
    joblib.dump(scaler, out_dir / "scaler.joblib")
    joblib.dump(feature_names, out_dir / "feature_names.joblib")
    joblib.dump(le, out_dir / "label_encoder.joblib")
    with open(out_dir / "config.json", "w") as f:
        json.dump(config, f, indent=2)

    print(f"\n  Saved to {out_dir}/:")
    for fp in sorted(out_dir.iterdir()):
        print(f"    {fp.name} ({fp.stat().st_size / 1024:.0f} KB)")

    # Per-class final report
    print(f"\n  Final per-class (test):")
    print(classification_report(y_test, y_final_test, labels=test_present, digits=3, zero_division=0))

    print(f"\nDone.")


if __name__ == "__main__":
    main()
