"""Cross-ratio feature benchmark: compare four classifiers on GT vs YOLO.

Classifiers:
  1. geometry_only:     existing 203 body-frame features
  2. cross_ratio_only:  cross-ratio features from landmark quadruples
  3. combined:          geometry + cross-ratio concatenated
  4. conf_weighted:     confidence-weighted geometry + cross-ratio

Evaluation:
  - Train on GT keypoints (annotations.json, video split)
  - Evaluate on frozen benchmark images with both GT and YOLO keypoints
  - Report: GT accuracy, YOLO accuracy, GT→YOLO degradation, per-class confusion
  - Feature stability: how much each feature changes GT→YOLO (same images)

Usage:
  python -m tools.cross_ratio_benchmark
"""

import json
import math
import sys
import time
import warnings
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.pose_classifier_v2 import (
    BodyFrame, extract_all_features, FINE_MAP, load_dataset, video_split,
)
from tools.cross_ratio_features import (
    extract_cross_ratio_features,
    extract_confidence_weighted_features,
    extract_geo_confidence_weighted,
    N_CR_FEATURES,
)

BENCH_DIR = Path("benchmark_perception")
FROZEN_SET = BENCH_DIR / "frozen_eval.json"
RESULTS_DIR = BENCH_DIR / "results"
OUTPUT_DIR = BENCH_DIR / "cross_ratio"

TARGET_CLASSES = ["MNT", "SCTR", "BCTR", "CGRD", "OGRD", "HGRD", "TRTL", "STND"]


# ── Feature extraction helpers ────────────────────────────────────

def safe_extract_geo(kps_a, kps_b):
    try:
        feats, names = extract_all_features(kps_a, kps_b)
        if any(math.isnan(f) or math.isinf(f) for f in feats):
            return None, None
        return feats, names
    except Exception:
        return None, None


def safe_extract_cr(kps_a, kps_b):
    try:
        feats, names = extract_cross_ratio_features(kps_a, kps_b)
        if any(math.isnan(f) or math.isinf(f) for f in feats):
            return None, None
        return feats, names
    except Exception:
        return None, None


def safe_extract_cw(geo_feats, cr_feats, geo_names, cr_names, kps_a, kps_b):
    try:
        feats, names = extract_confidence_weighted_features(
            geo_feats, cr_feats, geo_names, cr_names, kps_a, kps_b)
        if any(math.isnan(f) or math.isinf(f) for f in feats):
            return None, None
        return feats, names
    except Exception:
        return None, None


# ── Training ──────────────────────────────────────────────────────

def build_training_data():
    """Extract all four feature sets from training data."""
    print("Loading dataset...")
    samples = load_dataset()
    train, val, test = video_split(samples)
    trainval = train + val
    print(f"  Train+Val: {len(trainval)}  Test: {len(test)}")

    feature_sets = {
        "geometry_only": {"X_train": [], "X_test": [], "names": None},
        "cross_ratio_only": {"X_train": [], "X_test": [], "names": None},
        "combined": {"X_train": [], "X_test": [], "names": None},
        "geo_conf_weighted": {"X_train": [], "X_test": [], "names": None},
        "conf_weighted": {"X_train": [], "X_test": [], "names": None},
    }

    y_train, y_test = [], []
    train_ok, test_ok = 0, 0
    skipped = 0

    for split_name, split_data, X_key, y_list in [
        ("trainval", trainval, "X_train", y_train),
        ("test", test, "X_test", y_test),
    ]:
        for s in split_data:
            me_kps, op_kps = s["me_kps"], s["op_kps"]
            geo, geo_n = safe_extract_geo(me_kps, op_kps)
            cr, cr_n = safe_extract_cr(me_kps, op_kps)
            if geo is None or cr is None:
                skipped += 1
                continue

            cw, cw_n = safe_extract_cw(geo, cr, geo_n, cr_n, me_kps, op_kps)
            if cw is None:
                skipped += 1
                continue

            combined = geo + cr
            combined_n = geo_n + cr_n

            geo_cw, geo_cw_n = extract_geo_confidence_weighted(
                geo, geo_n, me_kps, op_kps)

            feature_sets["geometry_only"][X_key].append(geo)
            feature_sets["cross_ratio_only"][X_key].append(cr)
            feature_sets["combined"][X_key].append(combined)
            feature_sets["geo_conf_weighted"][X_key].append(geo_cw)
            feature_sets["conf_weighted"][X_key].append(cw)

            if feature_sets["geometry_only"]["names"] is None:
                feature_sets["geometry_only"]["names"] = geo_n
                feature_sets["cross_ratio_only"]["names"] = cr_n
                feature_sets["combined"]["names"] = combined_n
                feature_sets["geo_conf_weighted"]["names"] = geo_cw_n
                feature_sets["conf_weighted"]["names"] = cw_n

            y_list.append(s["fine"])

    print(f"  Skipped: {skipped}")
    print(f"  Train samples: {len(y_train)}, Test samples: {len(y_test)}")

    for fs_name in feature_sets:
        feature_sets[fs_name]["X_train"] = np.array(
            feature_sets[fs_name]["X_train"], dtype=np.float32)
        feature_sets[fs_name]["X_test"] = np.array(
            feature_sets[fs_name]["X_test"], dtype=np.float32)
        n_feats = feature_sets[fs_name]["X_train"].shape[1]
        print(f"  {fs_name}: {n_feats} features")

    return feature_sets, y_train, y_test


def train_classifiers(feature_sets, y_train, y_test):
    """Train MLP classifier for each feature set, report test accuracy."""
    from sklearn.neural_network import MLPClassifier
    from sklearn.preprocessing import StandardScaler, LabelEncoder
    from sklearn.metrics import accuracy_score, classification_report

    le = LabelEncoder()
    le.fit(sorted(set(y_train) | set(y_test)))
    y_tr_enc = le.transform(y_train)
    y_te_enc = le.transform(y_test)

    models = {}
    scalers = {}

    print(f"\n{'='*70}")
    print("  TRAINING (MLP, same hyperparams as deployed model)")
    print(f"{'='*70}")

    for fs_name, fs in feature_sets.items():
        print(f"\n  [{fs_name}] {fs['X_train'].shape[1]} features...")
        scaler = StandardScaler()
        X_tr = np.nan_to_num(scaler.fit_transform(fs["X_train"]), 0)
        X_te = np.nan_to_num(scaler.transform(fs["X_test"]), 0)

        model = MLPClassifier(
            hidden_layer_sizes=(256, 128),
            max_iter=500,
            early_stopping=True,
            validation_fraction=0.15,
            random_state=42,
        )
        t0 = time.time()
        model.fit(X_tr, y_tr_enc)
        elapsed = time.time() - t0

        y_pred = le.inverse_transform(model.predict(X_te))
        acc = accuracy_score(y_test, y_pred)
        print(f"  Test accuracy: {acc:.1%} ({elapsed:.1f}s)")

        models[fs_name] = model
        scalers[fs_name] = scaler

    return models, scalers, le


# ── Frozen benchmark evaluation ───────────────────────────────────

def load_frozen_eval():
    """Load frozen eval set with GT keypoints."""
    with open(FROZEN_SET) as f:
        data = json.load(f)
    return data["samples"]


def load_yolo_results():
    """Load YOLO predictions with saved keypoints."""
    results = {}
    yolo_path = RESULTS_DIR / "yolo_ft_v2.jsonl"
    if not yolo_path.exists():
        print(f"  WARNING: {yolo_path} not found")
        return results
    for line in open(yolo_path):
        r = json.loads(line)
        if r.get("kps_a") and r.get("kps_b"):
            results[r["image_id"]] = r
    return results


def classify_both_pov(kps_a, kps_b, model, scaler, le, extract_fn):
    """Try both POV orderings, return (pred_label, confidence, features)."""
    feats_ab = extract_fn(kps_a, kps_b)
    feats_ba = extract_fn(kps_b, kps_a)

    if feats_ab is None and feats_ba is None:
        return None, 0.0, None

    results = []
    for feats in [feats_ab, feats_ba]:
        if feats is None:
            results.append((None, 0.0, None))
            continue
        X = np.nan_to_num(scaler.transform([feats]), 0)
        proba = model.predict_proba(X)[0]
        pred_idx = int(np.argmax(proba))
        conf = float(proba[pred_idx])
        label = le.inverse_transform([pred_idx])[0]
        results.append((label, conf, feats))

    if results[0][1] >= results[1][1]:
        return results[0]
    return results[1]


def evaluate_on_frozen(models, scalers, le, feature_sets):
    """Evaluate all classifiers on frozen benchmark with GT and YOLO keypoints."""
    samples = load_frozen_eval()
    yolo_results = load_yolo_results()

    print(f"\n{'='*70}")
    print(f"  FROZEN BENCHMARK EVALUATION ({len(samples)} images)")
    print(f"  YOLO results available: {len(yolo_results)}")
    print(f"{'='*70}")

    # Build extraction functions for each feature set
    def make_extract_fn(fs_name):
        def extract(kps_a, kps_b):
            geo, geo_n = safe_extract_geo(kps_a, kps_b)
            if geo is None:
                return None
            if fs_name == "geometry_only":
                return geo
            if fs_name == "geo_conf_weighted":
                gcw, _ = extract_geo_confidence_weighted(
                    geo, geo_n, kps_a, kps_b)
                return gcw
            cr, cr_n = safe_extract_cr(kps_a, kps_b)
            if cr is None:
                return None
            if fs_name == "cross_ratio_only":
                return cr
            if fs_name == "combined":
                return geo + cr
            if fs_name == "conf_weighted":
                cw, _ = safe_extract_cw(geo, cr, geo_n, cr_n, kps_a, kps_b)
                return cw
            return None
        return extract

    # Results per classifier
    all_results = {}

    for fs_name in feature_sets:
        model = models[fs_name]
        scaler = scalers[fs_name]
        extract_fn = make_extract_fn(fs_name)

        gt_correct = 0
        gt_total = 0
        yolo_correct = 0
        yolo_total = 0
        gt_per_class = defaultdict(lambda: {"n": 0, "correct": 0})
        yolo_per_class = defaultdict(lambda: {"n": 0, "correct": 0})
        gt_confusion = defaultdict(Counter)
        yolo_confusion = defaultdict(Counter)

        # Feature stability tracking
        stability_diffs = []  # (feature_idx, abs_diff) per image
        stability_feature_names = feature_sets[fs_name].get("names", [])

        for s in samples:
            true_label = s["fine_label"]
            if true_label not in TARGET_CLASSES:
                continue

            img_id = s["image_id"]

            # GT evaluation
            gt1 = s.get("gt_pose1")
            gt2 = s.get("gt_pose2")
            if gt1 and gt2 and len(gt1) == 17 and len(gt2) == 17:
                # POV: suffix-based like the GT benchmark
                suffix = s["position"][-1] if s["position"][-1] in "12" else "0"
                if suffix == "2":
                    kps_a, kps_b = gt2, gt1
                else:
                    kps_a, kps_b = gt1, gt2

                pred, conf, gt_feats = classify_both_pov(
                    kps_a, kps_b, model, scaler, le, extract_fn)
                if pred is not None:
                    gt_total += 1
                    gt_per_class[true_label]["n"] += 1
                    if pred == true_label:
                        gt_correct += 1
                        gt_per_class[true_label]["correct"] += 1
                    else:
                        gt_confusion[true_label][pred] += 1
            else:
                gt_feats = None

            # YOLO evaluation
            yolo_r = yolo_results.get(img_id)
            if yolo_r and yolo_r.get("kps_a") and yolo_r.get("kps_b"):
                y_kps_a = yolo_r["kps_a"]
                y_kps_b = yolo_r["kps_b"]

                pred, conf, yolo_feats = classify_both_pov(
                    y_kps_a, y_kps_b, model, scaler, le, extract_fn)
                if pred is not None:
                    yolo_total += 1
                    yolo_per_class[true_label]["n"] += 1
                    if pred == true_label:
                        yolo_correct += 1
                        yolo_per_class[true_label]["correct"] += 1
                    else:
                        yolo_confusion[true_label][pred] += 1

                # Feature stability: compare GT and YOLO features
                if gt_feats is not None and yolo_feats is not None:
                    diffs = []
                    for fi in range(len(gt_feats)):
                        d = abs(gt_feats[fi] - yolo_feats[fi])
                        denom = abs(gt_feats[fi]) + 1e-6
                        diffs.append(d / denom)
                    stability_diffs.append(diffs)

        gt_acc = gt_correct / gt_total if gt_total else 0
        yolo_acc = yolo_correct / yolo_total if yolo_total else 0
        degrad = gt_acc - yolo_acc

        all_results[fs_name] = {
            "gt_acc": gt_acc, "gt_total": gt_total, "gt_correct": gt_correct,
            "yolo_acc": yolo_acc, "yolo_total": yolo_total, "yolo_correct": yolo_correct,
            "degradation": degrad,
            "gt_per_class": dict(gt_per_class),
            "yolo_per_class": dict(yolo_per_class),
            "gt_confusion": {k: dict(v) for k, v in gt_confusion.items()},
            "yolo_confusion": {k: dict(v) for k, v in yolo_confusion.items()},
            "stability_diffs": stability_diffs,
            "feature_names": stability_feature_names,
        }

    return all_results


# ── Reporting ─────────────────────────────────────────────────────

def print_results(all_results):
    classifiers = list(all_results.keys())

    # ── Summary table ──
    print(f"\n{'='*90}")
    print("  CROSS-RATIO BENCHMARK — SUMMARY")
    print(f"{'='*90}")

    col_w = 16
    headers = ["Metric"] + classifiers

    def row(label, values):
        print(f"  {label:<28s}" + "".join(f"{v:>{col_w}s}" for v in values))

    row("", classifiers)
    print(f"  {'-'*28}" + ("-" * col_w) * len(classifiers))
    row("GT accuracy",
        [f"{r['gt_correct']}/{r['gt_total']} = {r['gt_acc']:.1%}"
         for r in [all_results[c] for c in classifiers]])
    row("YOLO accuracy",
        [f"{r['yolo_correct']}/{r['yolo_total']} = {r['yolo_acc']:.1%}"
         for r in [all_results[c] for c in classifiers]])
    row("GT→YOLO degradation",
        [f"{r['degradation']:+.1%}"
         for r in [all_results[c] for c in classifiers]])

    # ── Per-class GT accuracy ──
    print(f"\n  PER-CLASS GT ACCURACY")
    row("", classifiers)
    print(f"  {'-'*28}" + ("-" * col_w) * len(classifiers))
    for cls in sorted(TARGET_CLASSES):
        vals = []
        for c in classifiers:
            pc = all_results[c]["gt_per_class"].get(cls, {"n": 0, "correct": 0})
            if pc["n"] > 0:
                vals.append(f"{pc['correct']}/{pc['n']}={pc['correct']/pc['n']:.0%}")
            else:
                vals.append("n/a")
        row(f"  {cls}", vals)

    # ── Per-class YOLO accuracy ──
    print(f"\n  PER-CLASS YOLO ACCURACY")
    row("", classifiers)
    print(f"  {'-'*28}" + ("-" * col_w) * len(classifiers))
    for cls in sorted(TARGET_CLASSES):
        vals = []
        for c in classifiers:
            pc = all_results[c]["yolo_per_class"].get(cls, {"n": 0, "correct": 0})
            if pc["n"] > 0:
                vals.append(f"{pc['correct']}/{pc['n']}={pc['correct']/pc['n']:.0%}")
            else:
                vals.append("n/a")
        row(f"  {cls}", vals)

    # ── Per-class degradation ──
    print(f"\n  PER-CLASS GT→YOLO DEGRADATION")
    row("", classifiers)
    print(f"  {'-'*28}" + ("-" * col_w) * len(classifiers))
    for cls in sorted(TARGET_CLASSES):
        vals = []
        for c in classifiers:
            gt_pc = all_results[c]["gt_per_class"].get(cls, {"n": 0, "correct": 0})
            yolo_pc = all_results[c]["yolo_per_class"].get(cls, {"n": 0, "correct": 0})
            if gt_pc["n"] > 0 and yolo_pc["n"] > 0:
                gt_a = gt_pc["correct"] / gt_pc["n"]
                yolo_a = yolo_pc["correct"] / yolo_pc["n"]
                vals.append(f"{gt_a - yolo_a:+.0%}")
            else:
                vals.append("n/a")
        row(f"  {cls}", vals)

    # ── YOLO confusion for each classifier ──
    for c in classifiers:
        print(f"\n  YOLO CONFUSION — {c}")
        conf = all_results[c]["yolo_confusion"]
        for cls in sorted(TARGET_CLASSES):
            if cls in conf and conf[cls]:
                pairs = sorted(conf[cls].items(), key=lambda x: -x[1])[:3]
                pair_str = ", ".join(f"{p}({n})" for p, n in pairs)
                print(f"    {cls:>5s} → {pair_str}")

    # ── Feature stability ──
    print(f"\n{'='*90}")
    print("  FEATURE STABILITY (mean relative change GT→YOLO)")
    print(f"{'='*90}")

    for c in classifiers:
        diffs = all_results[c]["stability_diffs"]
        names = all_results[c]["feature_names"]
        if not diffs or not names:
            print(f"\n  [{c}] no stability data")
            continue

        diffs_arr = np.array(diffs, dtype=np.float64)
        mean_diff = np.nanmean(diffs_arr, axis=0)

        # Overall stability
        overall = float(np.nanmean(mean_diff))
        print(f"\n  [{c}] overall mean relative change: {overall:.3f}")

        # Stability by feature group
        if c in ("combined", "conf_weighted"):
            n_geo = 203
            geo_stability = float(np.nanmean(mean_diff[:n_geo]))
            cr_stability = float(np.nanmean(mean_diff[n_geo:]))
            print(f"    geometry features:    {geo_stability:.3f}")
            print(f"    cross-ratio features: {cr_stability:.3f}")
        elif c in ("geometry_only", "geo_conf_weighted"):
            print(f"    (all geometry, {len(names)} features)")
        elif c == "cross_ratio_only":
            # Breakdown by feature type
            logcr_idxs = [i for i, n in enumerate(names) if n.endswith("_logcr")]
            orient_idxs = [i for i, n in enumerate(names) if n.endswith("_orient")]
            conf_idxs = [i for i, n in enumerate(names) if n.endswith("_minconf")]
            if logcr_idxs:
                print(f"    log_cr features:  {np.nanmean(mean_diff[logcr_idxs]):.3f}")
            if orient_idxs:
                print(f"    orient features:  {np.nanmean(mean_diff[orient_idxs]):.3f}")
            if conf_idxs:
                print(f"    minconf features: {np.nanmean(mean_diff[conf_idxs]):.3f}")

        # Most and least stable features
        ranked = sorted(zip(names, mean_diff), key=lambda x: x[1])
        print(f"    10 most stable:")
        for name, d in ranked[:10]:
            print(f"      {name:<50s} {d:.4f}")
        print(f"    10 least stable:")
        for name, d in ranked[-10:]:
            print(f"      {name:<50s} {d:.4f}")


def save_results(all_results):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Save summary (without bulky stability arrays)
    summary = {}
    for c, r in all_results.items():
        summary[c] = {
            k: v for k, v in r.items()
            if k not in ("stability_diffs", "feature_names")
        }
    with open(OUTPUT_DIR / "summary.json", "w") as f:
        json.dump(summary, f, indent=2, default=str)

    # Save stability data separately
    for c, r in all_results.items():
        if r["stability_diffs"]:
            with open(OUTPUT_DIR / f"stability_{c}.json", "w") as f:
                json.dump({
                    "feature_names": r["feature_names"],
                    "mean_relative_change": np.nanmean(
                        np.array(r["stability_diffs"]), axis=0).tolist(),
                }, f, indent=2)

    print(f"\n  Results saved to {OUTPUT_DIR}/")


# ── Main ──────────────────────────────────────────────────────────

def main():
    if not FROZEN_SET.exists():
        print("ERROR: frozen eval set not found. Run benchmark_perception.py freeze first.")
        return

    # 1. Build training data with all feature sets
    feature_sets, y_train, y_test = build_training_data()

    # 2. Train classifiers
    models, scalers, le = train_classifiers(feature_sets, y_train, y_test)

    # 3. Evaluate on frozen benchmark
    all_results = evaluate_on_frozen(models, scalers, le, feature_sets)

    # 4. Report
    print_results(all_results)
    save_results(all_results)


if __name__ == "__main__":
    main()
