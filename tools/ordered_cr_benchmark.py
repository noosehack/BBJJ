"""Ordered cross-ratio benchmark: geometry vs naked CR vs ordered CR.

Classifiers (all confidence-weighted):
  A. geo_cw:                    203 geometry features × avg_conf
  B. naked_cr_cw:               93 naked cross-ratio features × min_conf
  C. ordered_cr_cw:            432 ordered projective constraint features × min_conf
  D. geo_plus_ordered_cr_cw:   203 geo + 432 ordered CR = 635 combined

Evaluation:
  Train on GT keypoints (annotations.json, video split).
  Evaluate on frozen benchmark with GT and YOLO keypoints.
  Report: GT accuracy, YOLO accuracy, GT→YOLO degradation, per-class, stability.

Usage:
  python -m tools.ordered_cr_benchmark
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
    extract_all_features, FINE_MAP, load_dataset, video_split,
)
from tools.cross_ratio_features import (
    extract_cross_ratio_features,
    extract_geo_confidence_weighted,
)
from tools.ordered_cross_ratio import (
    extract_ordered_cr_features,
    confidence_weight_ordered_cr,
    N_FEATURES_RAW as N_OCR_RAW,
)

BENCH_DIR = Path("benchmark_perception")
FROZEN_SET = BENCH_DIR / "frozen_eval.json"
RESULTS_DIR = BENCH_DIR / "results"
OUTPUT_DIR = BENCH_DIR / "ordered_cr"

TARGET_CLASSES = ["MNT", "SCTR", "BCTR", "CGRD", "OGRD", "HGRD", "TRTL", "STND"]


# ── Safe extractors ───────────────────────────────────────────────

def _bad(feats):
    return any(math.isnan(f) or math.isinf(f) for f in feats)


def _safe_geo(kps_a, kps_b):
    try:
        f, n = extract_all_features(kps_a, kps_b)
        return (None, None) if _bad(f) else (f, n)
    except Exception:
        return None, None


def _safe_naked_cr(kps_a, kps_b):
    try:
        f, n = extract_cross_ratio_features(kps_a, kps_b)
        return (None, None) if _bad(f) else (f, n)
    except Exception:
        return None, None


def _safe_ordered_cr(kps_a, kps_b):
    try:
        f, n = extract_ordered_cr_features(kps_a, kps_b)
        return (None, None) if _bad(f) else (f, n)
    except Exception:
        return None, None


def _avg_conf(kps):
    return sum(float(kps[i][2]) for i in range(17)) / 17.0


def _apply_geo_cw(geo, geo_n, kps_a, kps_b):
    return extract_geo_confidence_weighted(geo, geo_n, kps_a, kps_b)


def _apply_naked_cr_cw(cr, cr_n):
    """Weight naked CR features by per-quadruple min_conf (every 3rd feature)."""
    weighted, w_names = [], []
    i = 0
    while i < len(cr):
        log_cr, orient, min_c = cr[i], cr[i + 1], cr[i + 2]
        base = cr_n[i].replace("_logcr", "")
        weighted.extend([log_cr * min_c, orient * min_c, min_c])
        w_names.extend([f"cw_{base}_logcr", f"cw_{base}_orient", f"cw_{base}_minconf"])
        i += 3
    return weighted, w_names


# ── Build training data ───────────────────────────────────────────

def build_training_data():
    print("Loading dataset...")
    samples = load_dataset()
    train, val, test = video_split(samples)
    trainval = train + val

    classifiers = {
        "geo_cw": {"X_train": [], "X_test": [], "names": None},
        "naked_cr_cw": {"X_train": [], "X_test": [], "names": None},
        "ordered_cr_cw": {"X_train": [], "X_test": [], "names": None},
        "geo_ordered_cr_cw": {"X_train": [], "X_test": [], "names": None},
    }

    y_train, y_test = [], []
    skipped = 0

    for split_name, split_data, X_key, y_list in [
        ("trainval", trainval, "X_train", y_train),
        ("test", test, "X_test", y_test),
    ]:
        t0 = time.time()
        for s in split_data:
            me_kps, op_kps = s["me_kps"], s["op_kps"]

            geo, geo_n = _safe_geo(me_kps, op_kps)
            ncr, ncr_n = _safe_naked_cr(me_kps, op_kps)
            ocr, ocr_n = _safe_ordered_cr(me_kps, op_kps)
            if geo is None or ncr is None or ocr is None:
                skipped += 1
                continue

            # A: geometry confidence-weighted
            gcw, gcw_n = _apply_geo_cw(geo, geo_n, me_kps, op_kps)

            # B: naked CR confidence-weighted
            ncrw, ncrw_n = _apply_naked_cr_cw(ncr, ncr_n)

            # C: ordered CR confidence-weighted
            ocrw, ocrw_n = confidence_weight_ordered_cr(ocr, ocr_n)

            # D: geo + ordered CR confidence-weighted
            combo = gcw + ocrw
            combo_n = gcw_n + ocrw_n

            classifiers["geo_cw"][X_key].append(gcw)
            classifiers["naked_cr_cw"][X_key].append(ncrw)
            classifiers["ordered_cr_cw"][X_key].append(ocrw)
            classifiers["geo_ordered_cr_cw"][X_key].append(combo)

            if classifiers["geo_cw"]["names"] is None:
                classifiers["geo_cw"]["names"] = gcw_n
                classifiers["naked_cr_cw"]["names"] = ncrw_n
                classifiers["ordered_cr_cw"]["names"] = ocrw_n
                classifiers["geo_ordered_cr_cw"]["names"] = combo_n

            y_list.append(s["fine"])

        elapsed = time.time() - t0
        print(f"  {split_name}: {len(y_list)} samples ({elapsed:.1f}s)")

    print(f"  Skipped: {skipped}")

    for name, clf in classifiers.items():
        clf["X_train"] = np.array(clf["X_train"], dtype=np.float32)
        clf["X_test"] = np.array(clf["X_test"], dtype=np.float32)
        print(f"  {name}: {clf['X_train'].shape[1]} features")

    return classifiers, y_train, y_test


# ── Training ──────────────────────────────────────────────────────

def train_models(classifiers, y_train, y_test):
    from sklearn.neural_network import MLPClassifier
    from sklearn.preprocessing import StandardScaler, LabelEncoder
    from sklearn.metrics import accuracy_score

    le = LabelEncoder()
    le.fit(sorted(set(y_train) | set(y_test)))
    y_tr_enc = le.transform(y_train)

    models, scalers = {}, {}

    print(f"\n{'='*70}")
    print("  TRAINING (MLP 256-128, same architecture as deployed)")
    print(f"{'='*70}")

    for name, clf in classifiers.items():
        print(f"\n  [{name}] {clf['X_train'].shape[1]} features...")
        scaler = StandardScaler()
        X_tr = np.nan_to_num(scaler.fit_transform(clf["X_train"]), 0)
        X_te = np.nan_to_num(scaler.transform(clf["X_test"]), 0)

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

        models[name] = model
        scalers[name] = scaler

    return models, scalers, le


# ── Evaluation ────────────────────────────────────────────────────

def _make_extract_fn(clf_name):
    """Build the feature extraction function for a classifier."""
    def extract(kps_a, kps_b):
        if clf_name == "geo_cw":
            geo, geo_n = _safe_geo(kps_a, kps_b)
            if geo is None:
                return None
            f, _ = _apply_geo_cw(geo, geo_n, kps_a, kps_b)
            return f

        if clf_name == "naked_cr_cw":
            ncr, ncr_n = _safe_naked_cr(kps_a, kps_b)
            if ncr is None:
                return None
            f, _ = _apply_naked_cr_cw(ncr, ncr_n)
            return f

        if clf_name == "ordered_cr_cw":
            ocr, ocr_n = _safe_ordered_cr(kps_a, kps_b)
            if ocr is None:
                return None
            f, _ = confidence_weight_ordered_cr(ocr, ocr_n)
            return f

        if clf_name == "geo_ordered_cr_cw":
            geo, geo_n = _safe_geo(kps_a, kps_b)
            ocr, ocr_n = _safe_ordered_cr(kps_a, kps_b)
            if geo is None or ocr is None:
                return None
            gcw, _ = _apply_geo_cw(geo, geo_n, kps_a, kps_b)
            ocrw, _ = confidence_weight_ordered_cr(ocr, ocr_n)
            return gcw + ocrw

        return None
    return extract


def _classify_both_pov(kps_a, kps_b, model, scaler, le, extract_fn):
    """Try both POV orderings, pick higher confidence."""
    best = (None, 0.0, None)
    for ka, kb in [(kps_a, kps_b), (kps_b, kps_a)]:
        feats = extract_fn(ka, kb)
        if feats is None:
            continue
        X = np.nan_to_num(scaler.transform([feats]), 0)
        proba = model.predict_proba(X)[0]
        idx = int(np.argmax(proba))
        conf = float(proba[idx])
        if conf > best[1]:
            best = (le.inverse_transform([idx])[0], conf, feats)
    return best


def evaluate(models, scalers, le, classifiers):
    """Evaluate on frozen benchmark: GT and YOLO keypoints."""
    with open(FROZEN_SET) as f:
        data = json.load(f)
    samples = data["samples"]

    yolo_results = {}
    yolo_path = RESULTS_DIR / "yolo_ft_v2.jsonl"
    if yolo_path.exists():
        for line in open(yolo_path):
            r = json.loads(line)
            if r.get("kps_a") and r.get("kps_b"):
                yolo_results[r["image_id"]] = r

    print(f"\n{'='*70}")
    print(f"  FROZEN BENCHMARK ({len(samples)} images, YOLO: {len(yolo_results)})")
    print(f"{'='*70}")

    all_results = {}

    for clf_name in classifiers:
        model = models[clf_name]
        scaler = scalers[clf_name]
        extract_fn = _make_extract_fn(clf_name)
        feat_names = classifiers[clf_name].get("names", [])

        gt_correct, gt_total = 0, 0
        yolo_correct, yolo_total = 0, 0
        gt_cls = defaultdict(lambda: {"n": 0, "ok": 0})
        yolo_cls = defaultdict(lambda: {"n": 0, "ok": 0})
        gt_conf = defaultdict(Counter)
        yolo_conf = defaultdict(Counter)
        stability = []

        for s in samples:
            true = s["fine_label"]
            if true not in TARGET_CLASSES:
                continue
            img_id = s["image_id"]

            # GT pass
            gt1, gt2 = s.get("gt_pose1"), s.get("gt_pose2")
            gt_feats = None
            if gt1 and gt2 and len(gt1) == 17 and len(gt2) == 17:
                suffix = s["position"][-1] if s["position"][-1] in "12" else "0"
                ka, kb = (gt2, gt1) if suffix == "2" else (gt1, gt2)
                pred, conf, gt_feats = _classify_both_pov(
                    ka, kb, model, scaler, le, extract_fn)
                if pred is not None:
                    gt_total += 1
                    gt_cls[true]["n"] += 1
                    if pred == true:
                        gt_correct += 1
                        gt_cls[true]["ok"] += 1
                    else:
                        gt_conf[true][pred] += 1

            # YOLO pass
            yr = yolo_results.get(img_id)
            yolo_feats = None
            if yr:
                pred, conf, yolo_feats = _classify_both_pov(
                    yr["kps_a"], yr["kps_b"], model, scaler, le, extract_fn)
                if pred is not None:
                    yolo_total += 1
                    yolo_cls[true]["n"] += 1
                    if pred == true:
                        yolo_correct += 1
                        yolo_cls[true]["ok"] += 1
                    else:
                        yolo_conf[true][pred] += 1

            # Feature stability
            if gt_feats is not None and yolo_feats is not None:
                diffs = []
                for fi in range(len(gt_feats)):
                    d = abs(gt_feats[fi] - yolo_feats[fi])
                    denom = abs(gt_feats[fi]) + 1e-6
                    diffs.append(d / denom)
                stability.append(diffs)

        gt_acc = gt_correct / gt_total if gt_total else 0
        yolo_acc = yolo_correct / yolo_total if yolo_total else 0

        all_results[clf_name] = {
            "gt_acc": gt_acc, "gt_n": gt_total, "gt_ok": gt_correct,
            "yolo_acc": yolo_acc, "yolo_n": yolo_total, "yolo_ok": yolo_correct,
            "degrad": gt_acc - yolo_acc,
            "gt_cls": dict(gt_cls), "yolo_cls": dict(yolo_cls),
            "gt_conf": {k: dict(v) for k, v in gt_conf.items()},
            "yolo_conf": {k: dict(v) for k, v in yolo_conf.items()},
            "stability": stability,
            "feat_names": feat_names,
        }

    return all_results


# ── Reporting ─────────────────────────────────────────────────────

def report(all_results):
    clfs = list(all_results.keys())
    W = 20

    def row(label, vals):
        print(f"  {label:<28s}" + "".join(f"{v:>{W}s}" for v in vals))

    print(f"\n{'='*110}")
    print("  ORDERED CROSS-RATIO BENCHMARK")
    print(f"{'='*110}")

    row("", clfs)
    print(f"  {'-'*28}" + ("-" * W) * len(clfs))
    row("GT accuracy",
        [f"{r['gt_ok']}/{r['gt_n']}={r['gt_acc']:.1%}" for r in [all_results[c] for c in clfs]])
    row("YOLO accuracy",
        [f"{r['yolo_ok']}/{r['yolo_n']}={r['yolo_acc']:.1%}" for r in [all_results[c] for c in clfs]])
    row("GT→YOLO degradation",
        [f"{r['degrad']:+.1%}" for r in [all_results[c] for c in clfs]])

    # Per-class
    for mode, key, label in [("GT", "gt_cls", "GT"), ("YOLO", "yolo_cls", "YOLO")]:
        print(f"\n  PER-CLASS {label} ACCURACY")
        row("", clfs)
        print(f"  {'-'*28}" + ("-" * W) * len(clfs))
        for cls in sorted(TARGET_CLASSES):
            vals = []
            for c in clfs:
                pc = all_results[c][key].get(cls, {"n": 0, "ok": 0})
                if pc["n"] > 0:
                    vals.append(f"{pc['ok']}/{pc['n']}={pc['ok']/pc['n']:.0%}")
                else:
                    vals.append("n/a")
            row(f"  {cls}", vals)

    # Per-class degradation
    print(f"\n  PER-CLASS DEGRADATION (GT acc - YOLO acc)")
    row("", clfs)
    print(f"  {'-'*28}" + ("-" * W) * len(clfs))
    for cls in sorted(TARGET_CLASSES):
        vals = []
        for c in clfs:
            g = all_results[c]["gt_cls"].get(cls, {"n": 0, "ok": 0})
            y = all_results[c]["yolo_cls"].get(cls, {"n": 0, "ok": 0})
            if g["n"] > 0 and y["n"] > 0:
                vals.append(f"{g['ok']/g['n'] - y['ok']/y['n']:+.0%}")
            else:
                vals.append("n/a")
        row(f"  {cls}", vals)

    # YOLO confusion
    for c in clfs:
        print(f"\n  YOLO CONFUSION — {c}")
        conf = all_results[c]["yolo_conf"]
        for cls in sorted(TARGET_CLASSES):
            if cls in conf and conf[cls]:
                pairs = sorted(conf[cls].items(), key=lambda x: -x[1])[:3]
                print(f"    {cls:>5s} → {', '.join(f'{p}({n})' for p,n in pairs)}")

    # Feature stability
    print(f"\n{'='*110}")
    print("  FEATURE STABILITY (mean |Δf|/|f| across GT→YOLO matched images)")
    print(f"{'='*110}")

    for c in clfs:
        diffs = all_results[c]["stability"]
        names = all_results[c]["feat_names"]
        if not diffs or not names:
            print(f"\n  [{c}] no stability data")
            continue

        arr = np.array(diffs, dtype=np.float64)
        mean_d = np.nanmean(arr, axis=0)

        # Median is more robust to outliers from binary features
        med_d = np.nanmedian(arr, axis=0)

        overall_mean = float(np.nanmean(mean_d))
        overall_med = float(np.nanmedian(mean_d))
        print(f"\n  [{c}] mean: {overall_mean:.3f}, median: {overall_med:.3f}")

        # Breakdown for combined
        if c == "geo_ordered_cr_cw":
            n_geo = 203
            print(f"    geo block ({n_geo}):    mean={np.nanmean(mean_d[:n_geo]):.3f}  median={np.nanmedian(mean_d[:n_geo]):.3f}")
            print(f"    ocr block ({len(mean_d)-n_geo}):    mean={np.nanmean(mean_d[n_geo:]):.3f}  median={np.nanmedian(mean_d[n_geo:]):.3f}")
        elif c == "ordered_cr_cw":
            # Breakdown by feature type within constraints
            ord_idxs = [i for i, n in enumerate(names) if "_ord_" in n]
            lcr_idxs = [i for i, n in enumerate(names) if "_logcr" in n]
            drat_idxs = [i for i, n in enumerate(names) if "_drat_" in n]
            lat_idxs = [i for i, n in enumerate(names) if "_lat_" in n]
            brk_idxs = [i for i, n in enumerate(names) if "_bracket_" in n]
            conf_idxs = [i for i, n in enumerate(names) if "_minconf" in n]
            for label, idxs in [("order signs", ord_idxs), ("log_cr", lcr_idxs),
                                ("dist_ratios", drat_idxs), ("lateral", lat_idxs),
                                ("bracket", brk_idxs), ("minconf", conf_idxs)]:
                if idxs:
                    print(f"    {label:15s}: mean={np.nanmean(mean_d[idxs]):.3f}  median={np.nanmedian(mean_d[idxs]):.3f}")

        # Top-5 most/least stable
        ranked = sorted(zip(names, mean_d), key=lambda x: x[1])
        print(f"    5 most stable:")
        for nm, d in ranked[:5]:
            print(f"      {nm:<55s} {d:.4f}")
        print(f"    5 least stable:")
        for nm, d in ranked[-5:]:
            print(f"      {nm:<55s} {d:.4f}")


def save(all_results):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    summary = {}
    for c, r in all_results.items():
        summary[c] = {k: v for k, v in r.items() if k not in ("stability", "feat_names")}
    with open(OUTPUT_DIR / "summary.json", "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(f"\n  Saved to {OUTPUT_DIR}/summary.json")


# ── Main ──────────────────────────────────────────────────────────

def main():
    if not FROZEN_SET.exists():
        print("ERROR: frozen eval set not found")
        return

    classifiers, y_train, y_test = build_training_data()
    models, scalers, le = train_models(classifiers, y_train, y_test)
    all_results = evaluate(models, scalers, le, classifiers)
    report(all_results)
    save(all_results)


if __name__ == "__main__":
    main()
