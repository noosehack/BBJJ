"""Train and serialize the geo + ordered_cr_cw classifier (635 features).

Replaces the 203-feature geometry-only model in models_geometry/.
Uses the same MLP(256,128) architecture, video-level split, and
confidence weighting as the ordered_cr_benchmark.

Usage:
    python -m tools.train_combined_model
"""

import json
import math
import sys
import time
import warnings
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
warnings.filterwarnings("ignore")

from tools.pose_classifier_v2 import extract_all_features, FINE_MAP
from tools.cross_ratio_features import extract_geo_confidence_weighted
from tools.ordered_cross_ratio import (
    extract_ordered_cr_features, confidence_weight_ordered_cr,
)

MODEL_DIR = Path("models_geometry")

TRAIN_VIDEOS = {"00", "01", "03", "06", "09", "11", "12", "14"}
VAL_VIDEOS   = {"02", "05", "08"}
TEST_VIDEOS  = {"04", "07", "10", "13", "15"}


def _bad(feats):
    return any(math.isnan(f) or math.isinf(f) for f in feats)


def load_and_featurize():
    with open("data/raw/annotations.json") as f:
        raw = json.load(f)

    X_train, y_train = [], []
    X_test, y_test = [], []
    feature_names = None
    skipped = 0

    for item in raw:
        pos = item["position"]
        if pos not in FINE_MAP:
            continue
        p1, p2 = item.get("pose1"), item.get("pose2")
        if not p1 or len(p1) != 17 or not p2 or len(p2) != 17:
            continue

        suffix = pos[-1] if pos[-1] in "12" else "0"
        me_kps, op_kps = (p2, p1) if suffix == "2" else (p1, p2)
        video = item["image"][:2]
        label = FINE_MAP[pos]

        if video in TEST_VIDEOS:
            X_list, y_list = X_test, y_test
        elif video in TRAIN_VIDEOS or video in VAL_VIDEOS:
            X_list, y_list = X_train, y_train
        else:
            continue

        try:
            geo, geo_n = extract_all_features(me_kps, op_kps)
            ocr, ocr_n = extract_ordered_cr_features(me_kps, op_kps)
            if _bad(geo) or _bad(ocr):
                skipped += 1
                continue

            gcw, gcw_n = extract_geo_confidence_weighted(geo, geo_n, me_kps, op_kps)
            ocrw, ocrw_n = confidence_weight_ordered_cr(ocr, ocr_n)

            combo = gcw + ocrw
            combo_n = gcw_n + ocrw_n

            X_list.append(combo)
            y_list.append(label)
            if feature_names is None:
                feature_names = combo_n
        except Exception:
            skipped += 1
            continue

    X_train = np.array(X_train, dtype=np.float32)
    X_test = np.array(X_test, dtype=np.float32)
    print(f"Train: {X_train.shape[0]}, Test: {X_test.shape[0]}, "
          f"Features: {X_train.shape[1]}, Skipped: {skipped}")
    return X_train, y_train, X_test, y_test, feature_names


def main():
    from sklearn.neural_network import MLPClassifier
    from sklearn.preprocessing import StandardScaler, LabelEncoder
    from sklearn.metrics import accuracy_score, classification_report
    import joblib

    print("Loading and featurizing...")
    t0 = time.time()
    X_train, y_train, X_test, y_test, feature_names = load_and_featurize()
    print(f"  {time.time() - t0:.0f}s")

    le = LabelEncoder()
    le.fit(sorted(set(y_train) | set(y_test)))

    scaler = StandardScaler()
    X_tr = np.nan_to_num(scaler.fit_transform(X_train), 0)
    X_te = np.nan_to_num(scaler.transform(X_test), 0)

    print(f"\nTraining MLP(256, 128)...")
    t0 = time.time()
    model = MLPClassifier(
        hidden_layer_sizes=(256, 128),
        max_iter=500,
        early_stopping=True,
        validation_fraction=0.15,
        random_state=42,
    )
    model.fit(X_tr, le.transform(y_train))
    print(f"  {time.time() - t0:.0f}s")

    y_pred = le.inverse_transform(model.predict(X_te))
    acc = accuracy_score(y_test, y_pred)
    print(f"\nTest accuracy: {acc:.1%}")
    print(classification_report(y_test, y_pred, zero_division=0))

    MODEL_DIR.mkdir(exist_ok=True)
    joblib.dump(model, MODEL_DIR / "model.joblib")
    joblib.dump(scaler, MODEL_DIR / "scaler.joblib")
    joblib.dump(feature_names, MODEL_DIR / "feature_names.joblib")
    joblib.dump(le, MODEL_DIR / "label_encoder.joblib")

    config = {
        "model_type": "MLP_geo_ordered_cr_cw",
        "features": len(feature_names),
        "feature_set": "geo_cw(203) + ordered_cr_cw(432) = 635",
        "classes": list(le.classes_),
        "train_samples": len(y_train),
        "test_samples": len(y_test),
        "test_accuracy": round(acc, 4),
        "classifier_source": "geo_ordered_cr_cw",
    }
    with open(MODEL_DIR / "config.json", "w") as f:
        json.dump(config, f, indent=2)

    print(f"\nSaved to {MODEL_DIR}/")


if __name__ == "__main__":
    main()
