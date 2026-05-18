"""Train classifier without body-frame projection features.

Drops invalid_bodyframe_2d features (cross-body-frame projections).
Keeps: similarity_2d + camera_conditioned_2d + projective_2d features,
plus naked cross-ratios and new cross-body features.

Camera-conditioned features (vert_dominance, absolute angles) are kept
because they work for virtually all real-world photos. The body-frame
projections are the features that truly break under viewpoint change.

Usage:
    python -m tools.train_invariant_model
    python -m tools.train_invariant_model --strict   # drop camera too
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
from tools.feature_invariance import filter_invariant, audit
from tools.invariant_features import extract_invariant_feature_set

MODEL_DIR = Path("models_geometry")

TRAIN_VIDEOS = {"00", "01", "03", "06", "09", "11", "12", "14"}
VAL_VIDEOS   = {"02", "05", "08"}
TEST_VIDEOS  = {"04", "07", "10", "13", "15"}

TARGET_CLASSES = {"MNT", "SCTR", "BCTR", "CGRD", "OGRD", "HGRD", "TRTL"}


def _bad(feats):
    return any(math.isnan(f) or math.isinf(f) for f in feats)


def print_audit(keep_camera: bool):
    """Print invariance audit of the old 635-feature pipeline."""
    with open("data/raw/annotations.json") as f:
        raw = json.load(f)
    sample = next(
        item for item in raw
        if item["position"] in FINE_MAP
        and item.get("pose1") and len(item.get("pose1", [])) == 17
        and item.get("pose2") and len(item.get("pose2", [])) == 17
    )
    geo, geo_n = extract_all_features(sample["pose1"], sample["pose2"])
    ocr, ocr_n = extract_ordered_cr_features(sample["pose1"], sample["pose2"])
    gcw, gcw_n = extract_geo_confidence_weighted(geo, geo_n,
                                                  sample["pose1"], sample["pose2"])
    ocrw, ocrw_n = confidence_weight_ordered_cr(ocr, ocr_n)
    old_names = gcw_n + ocrw_n

    from tools.feature_invariance import KEEP_WITH_CAMERA, KEEP_STRICT
    keep = KEEP_WITH_CAMERA if keep_camera else KEEP_STRICT

    groups = audit(old_names)
    print(f"Old pipeline: {len(old_names)} features")
    for level in sorted(groups):
        ct = len(groups[level])
        action = "KEEP" if level in keep else "DROP"
        print(f"  {level:30s}: {ct:4d}  [{action}]")
        if action == "DROP":
            examples = groups[level][:3]
            print(f"    e.g. {', '.join(examples)}")


def load_and_featurize(keep_camera: bool):
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

        if label not in TARGET_CLASSES:
            continue

        if video in TEST_VIDEOS:
            X_list, y_list = X_test, y_test
        elif video in TRAIN_VIDEOS or video in VAL_VIDEOS:
            X_list, y_list = X_train, y_train
        else:
            continue

        try:
            feats, names = extract_invariant_feature_set(
                me_kps, op_kps, keep_camera=keep_camera)
            if feats is None or _bad(feats):
                skipped += 1
                continue
            X_list.append(feats)
            y_list.append(label)
            if feature_names is None:
                feature_names = names
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

    print("═══ Feature Invariance Audit ═══\n")
    print_audit()

    print("\n═══ Invariant Feature Extraction ═══\n")
    t0 = time.time()
    X_train, y_train, X_test, y_test, feature_names = load_and_featurize()
    print(f"  Extraction: {time.time() - t0:.0f}s")

    inv_groups = audit(feature_names)
    print(f"\nNew pipeline: {len(feature_names)} features")
    for level in sorted(inv_groups):
        print(f"  {level:30s}: {len(inv_groups[level]):4d}")

    le = LabelEncoder()
    le.fit(sorted(set(y_train) | set(y_test)))

    scaler = StandardScaler()
    X_tr = np.nan_to_num(scaler.fit_transform(X_train), 0)
    X_te = np.nan_to_num(scaler.transform(X_test), 0)

    print(f"\n═══ Training MLP(256, 128) ═══\n")
    t0 = time.time()
    model = MLPClassifier(
        hidden_layer_sizes=(256, 128),
        max_iter=500,
        early_stopping=True,
        validation_fraction=0.15,
        random_state=42,
    )
    model.fit(X_tr, le.transform(y_train))
    print(f"  Training: {time.time() - t0:.0f}s")

    y_pred = le.inverse_transform(model.predict(X_te))
    acc = accuracy_score(y_test, y_pred)
    print(f"\nTest accuracy: {acc:.1%}")
    print(classification_report(y_test, y_pred, zero_division=0))

    # Count feature categories
    n_inv_geo = sum(1 for nm in feature_names
                    if not nm.startswith(("cw_cr_", "cr_",
                                         "cw_xd_", "cw_sa_", "cw_xa_", "cw_enc_",
                                         "xd_", "sa_", "xa_", "enc_")))
    n_naked_cr = sum(1 for nm in feature_names
                     if nm.startswith(("cw_cr_", "cr_")))
    n_cross_body = sum(1 for nm in feature_names
                       if nm.startswith(("cw_xd_", "cw_sa_", "cw_xa_", "cw_enc_")))

    MODEL_DIR.mkdir(exist_ok=True)
    joblib.dump(model, MODEL_DIR / "model.joblib")
    joblib.dump(scaler, MODEL_DIR / "scaler.joblib")
    joblib.dump(feature_names, MODEL_DIR / "feature_names.joblib")
    joblib.dump(le, MODEL_DIR / "label_encoder.joblib")

    config = {
        "model_type": "MLP_invariant_geo_cr",
        "features": len(feature_names),
        "feature_set": (f"invariant_geo_ocr({n_inv_geo}) + "
                        f"naked_cr({n_naked_cr}) + "
                        f"cross_body({n_cross_body})"),
        "invariance_policy": ("only projective_2d + similarity_2d; "
                              "no body-frame projections or absolute angles"),
        "classes": list(le.classes_),
        "excluded_classes": ["5050", "TKDN", "STND"],
        "excluded_reason": (
            "5050: overrepresented in ViCoS but rare in real BJJ; "
            "TKDN: transitional, not stable; "
            "STND: not useful, becomes default bucket for bad predictions"
        ),
        "train_samples": len(y_train),
        "test_samples": len(y_test),
        "test_accuracy": round(acc, 4),
        "classifier_source": "invariant_geo_cr",
    }
    with open(MODEL_DIR / "config.json", "w") as f:
        json.dump(config, f, indent=2)

    print(f"\nSaved to {MODEL_DIR}/")
    print(f"  {n_inv_geo} invariant geo/OCR + {n_naked_cr} naked CR + "
          f"{n_cross_body} cross-body = {len(feature_names)} total")


if __name__ == "__main__":
    main()
