"""Pose-to-radical family classifier using annotated keypoints.

NO contact/proximity heuristics. Direct pose geometry -> position family.
Split by video to prevent frame leakage.
"""

import json
import math
import sys
import time
import warnings
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

warnings.filterwarnings("ignore")

# ── Dataset labels → fundamental radical families ────────────────

FAMILY_MAP = {
    "mount1":         "TOP_PIN",
    "mount2":         "TOP_PIN",
    "side_control1":  "TOP_PIN",
    "side_control2":  "TOP_PIN",
    "back1":          "BACK_CTRL",
    "back2":          "BACK_CTRL",
    "closed_guard1":  "GUARD",
    "closed_guard2":  "GUARD",
    "open_guard1":    "GUARD",
    "open_guard2":    "GUARD",
    "half_guard1":    "GUARD",
    "half_guard2":    "GUARD",
    "5050_guard":     "GUARD",
    "turtle1":        "TURTLE",
    "turtle2":        "TURTLE",
    "standing":       "STANDING",
    "takedown1":      "STANDING",
    "takedown2":      "STANDING",
}

# Also keep fine labels for top-3 reporting
FINE_MAP = {
    "mount1":         "MNT",
    "mount2":         "MNT",
    "side_control1":  "SCTR",
    "side_control2":  "SCTR",
    "back1":          "BCTR",
    "back2":          "BCTR",
    "closed_guard1":  "CGRD",
    "closed_guard2":  "CGRD",
    "open_guard1":    "OGRD",
    "open_guard2":    "OGRD",
    "half_guard1":    "HGRD",
    "half_guard2":    "HGRD",
    "5050_guard":     "5050",
    "turtle1":        "TRTL",
    "turtle2":        "TRTL",
    "standing":       "STND",
    "takedown1":      "TKDN",
    "takedown2":      "TKDN",
}


# ── Feature extraction ───────────────────────────────────────────

COCO_NAMES = [
    "nose", "left_eye", "right_eye", "left_ear", "right_ear",
    "left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
    "left_wrist", "right_wrist", "left_hip", "right_hip",
    "left_knee", "right_knee", "left_ankle", "right_ankle",
]

L_SH, R_SH = 5, 6
L_HP, R_HP = 11, 12
L_KN, R_KN = 13, 14
L_AN, R_AN = 15, 16
NOSE = 0


def _midpoint(kps, i, j):
    x = (kps[i][0] + kps[j][0]) / 2
    y = (kps[i][1] + kps[j][1]) / 2
    c = min(kps[i][2], kps[j][2])
    return x, y, c


def _dist(a, b):
    return math.sqrt((a[0] - b[0])**2 + (a[1] - b[1])**2)


def _angle(dx, dy):
    return math.degrees(math.atan2(dx, dy))


def _torso_length(kps):
    sh_mid = _midpoint(kps, L_SH, R_SH)
    hp_mid = _midpoint(kps, L_HP, R_HP)
    return max(_dist(sh_mid, hp_mid), 1.0)


def extract_single_pose_features(kps):
    """Extract geometric features from one 17x3 pose."""
    features = []
    feature_names = []

    sh_mid = _midpoint(kps, L_SH, R_SH)
    hp_mid = _midpoint(kps, L_HP, R_HP)
    tl = _torso_length(kps)

    # Normalized keypoints (relative to hip midpoint, scaled by torso length)
    for i, name in enumerate(COCO_NAMES):
        x, y, c = kps[i]
        nx = (x - hp_mid[0]) / tl
        ny = (y - hp_mid[1]) / tl
        features.extend([nx, ny, c])
        feature_names.extend([f"{name}_nx", f"{name}_ny", f"{name}_conf"])

    # Torso vector and angle
    torso_dx = hp_mid[0] - sh_mid[0]
    torso_dy = hp_mid[1] - sh_mid[1]
    torso_angle = _angle(torso_dx, torso_dy)
    features.append(torso_angle)
    feature_names.append("torso_angle")

    # Shoulder midpoint
    features.extend([sh_mid[0], sh_mid[1]])
    feature_names.extend(["sh_mid_x", "sh_mid_y"])

    # Hip midpoint
    features.extend([hp_mid[0], hp_mid[1]])
    feature_names.extend(["hp_mid_x", "hp_mid_y"])

    # Body center (avg of sh_mid and hp_mid)
    cx = (sh_mid[0] + hp_mid[0]) / 2
    cy = (sh_mid[1] + hp_mid[1]) / 2
    features.extend([cx, cy])
    feature_names.extend(["body_center_x", "body_center_y"])

    # Torso length
    features.append(tl)
    feature_names.append("torso_length")

    # Shoulder width
    sw = _dist(kps[L_SH], kps[R_SH])
    features.append(sw / tl)
    feature_names.append("shoulder_width_norm")

    # Hip width
    hw = _dist(kps[L_HP], kps[R_HP])
    features.append(hw / tl)
    feature_names.append("hip_width_norm")

    # Limb lengths (normalized)
    limb_pairs = [
        (L_SH, L_HP, "left_torso"), (R_SH, R_HP, "right_torso"),
        (L_SH, L_KN, "left_upper_arm_to_knee"),  # skip, not standard
        (L_HP, L_KN, "left_thigh"), (R_HP, R_KN, "right_thigh"),
        (L_KN, L_AN, "left_shin"), (R_KN, R_AN, "right_shin"),
    ]
    for a, b, name in limb_pairs:
        d = _dist(kps[a], kps[b]) / tl
        features.append(d)
        feature_names.append(f"{name}_norm")

    # Knee-to-hip distances (compactness measure)
    for ki, hi, name in [(L_KN, L_HP, "l_knee_to_hip"), (R_KN, R_HP, "r_knee_to_hip")]:
        d = _dist(kps[ki], kps[hi]) / tl
        features.append(d)
        feature_names.append(f"{name}_norm")

    # Ankle-to-ankle distance
    ankle_dist = _dist(kps[L_AN], kps[R_AN]) / tl
    features.append(ankle_dist)
    feature_names.append("ankle_ankle_norm")

    # Visibility counts
    vis_upper = sum(1 for i in range(0, 11) if kps[i][2] > 0.3)
    vis_lower = sum(1 for i in range(11, 17) if kps[i][2] > 0.3)
    features.extend([vis_upper, vis_lower])
    feature_names.extend(["vis_upper", "vis_lower"])

    return features, feature_names


def extract_pair_features(kps_a, kps_b):
    """Extract pairwise features between two poses."""
    features = []
    feature_names = []

    sh_mid_a = _midpoint(kps_a, L_SH, R_SH)
    hp_mid_a = _midpoint(kps_a, L_HP, R_HP)
    sh_mid_b = _midpoint(kps_b, L_SH, R_SH)
    hp_mid_b = _midpoint(kps_b, L_HP, R_HP)

    tl_a = _torso_length(kps_a)
    tl_b = _torso_length(kps_b)
    avg_tl = (tl_a + tl_b) / 2

    # Center distance
    cx_a = (sh_mid_a[0] + hp_mid_a[0]) / 2
    cy_a = (sh_mid_a[1] + hp_mid_a[1]) / 2
    cx_b = (sh_mid_b[0] + hp_mid_b[0]) / 2
    cy_b = (sh_mid_b[1] + hp_mid_b[1]) / 2
    center_dist = math.sqrt((cx_a - cx_b)**2 + (cy_a - cy_b)**2) / avg_tl
    features.append(center_dist)
    feature_names.append("center_dist_norm")

    # Hip-to-hip distance
    hip_dist = _dist(hp_mid_a, hp_mid_b) / avg_tl
    features.append(hip_dist)
    feature_names.append("hip_hip_dist_norm")

    # Shoulder-to-shoulder distance
    sh_dist = _dist(sh_mid_a, sh_mid_b) / avg_tl
    features.append(sh_dist)
    feature_names.append("sh_sh_dist_norm")

    # Relative vertical displacement (positive = A is above B)
    vert_disp = (cy_b - cy_a) / avg_tl
    features.append(vert_disp)
    feature_names.append("vert_displacement_norm")

    # Relative horizontal displacement
    horiz_disp = (cx_b - cx_a) / avg_tl
    features.append(horiz_disp)
    feature_names.append("horiz_displacement_norm")

    # Torso angle difference
    torso_dx_a = hp_mid_a[0] - sh_mid_a[0]
    torso_dy_a = hp_mid_a[1] - sh_mid_a[1]
    torso_dx_b = hp_mid_b[0] - sh_mid_b[0]
    torso_dy_b = hp_mid_b[1] - sh_mid_b[1]
    angle_a = _angle(torso_dx_a, torso_dy_a)
    angle_b = _angle(torso_dx_b, torso_dy_b)
    angle_diff = angle_a - angle_b
    # Normalize to [-180, 180]
    if angle_diff > 180: angle_diff -= 360
    if angle_diff < -180: angle_diff += 360
    features.append(angle_diff)
    feature_names.append("torso_angle_diff")

    # Torso length ratio
    features.append(tl_a / tl_b if tl_b > 0 else 1.0)
    feature_names.append("torso_length_ratio")

    # Bbox overlap proxy: min/max of all visible keypoints
    def _bbox(kps):
        vis = [(x, y) for x, y, c in kps if c > 0.1]
        if len(vis) < 4:
            return None
        xs = [p[0] for p in vis]
        ys = [p[1] for p in vis]
        return min(xs), min(ys), max(xs), max(ys)

    bbox_a = _bbox(kps_a)
    bbox_b = _bbox(kps_b)
    if bbox_a and bbox_b:
        # Aspect ratios
        w_a = bbox_a[2] - bbox_a[0]
        h_a = bbox_a[3] - bbox_a[1]
        w_b = bbox_b[2] - bbox_b[0]
        h_b = bbox_b[3] - bbox_b[1]
        features.append(w_a / max(h_a, 1))
        features.append(w_b / max(h_b, 1))
        feature_names.extend(["bbox_aspect_a", "bbox_aspect_b"])

        # Scale ratio
        area_a = w_a * h_a
        area_b = w_b * h_b
        features.append(area_a / max(area_b, 1))
        feature_names.append("bbox_scale_ratio")

        # IoU
        x1 = max(bbox_a[0], bbox_b[0])
        y1 = max(bbox_a[1], bbox_b[1])
        x2 = min(bbox_a[2], bbox_b[2])
        y2 = min(bbox_a[3], bbox_b[3])
        inter = max(0, x2 - x1) * max(0, y2 - y1)
        union = area_a + area_b - inter
        features.append(inter / max(union, 1))
        feature_names.append("bbox_iou")
    else:
        features.extend([0, 0, 1, 0])
        feature_names.extend(["bbox_aspect_a", "bbox_aspect_b", "bbox_scale_ratio", "bbox_iou"])

    # Top/bottom proxy: which athlete has higher y (lower in image = on ground)
    # Positive = A is on bottom (higher y)
    top_bottom = (hp_mid_a[1] - hp_mid_b[1]) / avg_tl
    features.append(top_bottom)
    feature_names.append("top_bottom_proxy")

    # Cross-body distances (A's limbs to B's body and vice versa)
    # A's hands to B's hip midpoint
    for wi, name in [(9, "a_l_wrist_to_b_hip"), (10, "a_r_wrist_to_b_hip")]:
        d = _dist(kps_a[wi], hp_mid_b) / avg_tl
        features.append(d)
        feature_names.append(name)
    # B's hands to A's hip midpoint
    for wi, name in [(9, "b_l_wrist_to_a_hip"), (10, "b_r_wrist_to_a_hip")]:
        d = _dist(kps_b[wi], hp_mid_a) / avg_tl
        features.append(d)
        feature_names.append(name)
    # A's ankles to B's hip midpoint
    for ai, name in [(15, "a_l_ankle_to_b_hip"), (16, "a_r_ankle_to_b_hip")]:
        d = _dist(kps_a[ai], hp_mid_b) / avg_tl
        features.append(d)
        feature_names.append(name)
    # B's ankles to A's hip midpoint
    for ai, name in [(15, "b_l_ankle_to_a_hip"), (16, "b_r_ankle_to_a_hip")]:
        d = _dist(kps_b[ai], hp_mid_a) / avg_tl
        features.append(d)
        feature_names.append(name)

    return features, feature_names


def extract_features(kps_a, kps_b):
    """Full feature vector for a pair of poses."""
    feats_a, names_a = extract_single_pose_features(kps_a)
    feats_b, names_b = extract_single_pose_features(kps_b)
    feats_pair, names_pair = extract_pair_features(kps_a, kps_b)

    all_feats = feats_a + feats_b + feats_pair
    all_names = [f"A_{n}" for n in names_a] + [f"B_{n}" for n in names_b] + names_pair
    return all_feats, all_names


# ── Data loading ─────────────────────────────────────────────────

def load_dataset():
    with open("data/raw/annotations.json") as f:
        raw = json.load(f)

    samples = []
    for item in raw:
        pos = item["position"]
        if pos not in FAMILY_MAP:
            continue
        p1 = item.get("pose1")
        p2 = item.get("pose2")
        if not p1 or len(p1) != 17 or not p2 or len(p2) != 17:
            continue

        family = FAMILY_MAP[pos]
        fine = FINE_MAP[pos]
        video = item["image"][:2]
        frame = item.get("frame", 0)
        suffix = pos[-1] if pos[-1] in "12" else "0"

        # POV normalization: suffix 1 = pose1 is "me" (reference), suffix 2 = pose2 is "me"
        if suffix == "2":
            me_kps = p2
            op_kps = p1
        else:
            me_kps = p1
            op_kps = p2

        samples.append({
            "image_id": item["image"],
            "video": video,
            "frame": frame,
            "position": pos,
            "family": family,
            "fine": fine,
            "me_kps": me_kps,
            "op_kps": op_kps,
        })

    return samples


def video_split(samples, test_videos=None, val_videos=None):
    """Split by video ID to prevent frame leakage.

    16 videos total. Use 2 for test, 2 for val, 12 for train.
    Choose videos that cover all families.
    """
    video_families = defaultdict(set)
    video_counts = Counter()
    for s in samples:
        video_families[s["video"]].add(s["family"])
        video_counts[s["video"]] += 1

    if test_videos is None:
        # Video family coverage:
        #   00-02: GUARD, STANDING
        #   03-05: GUARD, STANDING
        #   06,08: GUARD, TOP_PIN
        #   07: TOP_PIN
        #   09-10: STANDING, TURTLE (only 2 videos!)
        #   11-13: GUARD, STANDING, TOP_PIN
        #   14-15: BACK_CTRL (only 2 videos!)
        #
        # Must ensure all 5 families in train AND test.
        # Test: 01(GUARD,STANDING) + 07(TOP_PIN) + 10(TURTLE) + 15(BACK_CTRL)
        # Val:  02(GUARD,STANDING) + 06(GUARD,TOP_PIN)
        # Train: 00,03,04,05,08,09,11,12,13,14 -> all 5 families
        test_videos = {"01", "07", "10", "15"}
        val_videos = {"02", "06"}

    train, val, test = [], [], []
    for s in samples:
        if s["video"] in test_videos:
            test.append(s)
        elif s["video"] in val_videos:
            val.append(s)
        else:
            train.append(s)

    return train, val, test


def featurize(samples):
    X = []
    y_family = []
    y_fine = []
    valid_indices = []

    for i, s in enumerate(samples):
        try:
            feats, _ = extract_features(s["me_kps"], s["op_kps"])
            if any(math.isnan(f) or math.isinf(f) for f in feats):
                continue
            X.append(feats)
            y_family.append(s["family"])
            y_fine.append(s["fine"])
            valid_indices.append(i)
        except Exception:
            continue

    return np.array(X, dtype=np.float32), y_family, y_fine, valid_indices


# ── Training & evaluation ────────────────────────────────────────

def train_and_evaluate():
    from sklearn.linear_model import LogisticRegression
    from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier
    from sklearn.neural_network import MLPClassifier
    from sklearn.preprocessing import StandardScaler, LabelEncoder
    from sklearn.metrics import (
        accuracy_score, f1_score, precision_recall_fscore_support,
        confusion_matrix, classification_report, top_k_accuracy_score,
    )

    print("Loading dataset...")
    samples = load_dataset()
    print(f"Total samples with both poses: {len(samples)}")

    # Class distribution
    family_counts = Counter(s["family"] for s in samples)
    fine_counts = Counter(s["fine"] for s in samples)
    print(f"\nFamily distribution:")
    for f, c in sorted(family_counts.items(), key=lambda x: -x[1]):
        print(f"  {f:12s}: {c:6d}")
    print(f"\nFine label distribution:")
    for f, c in sorted(fine_counts.items(), key=lambda x: -x[1]):
        print(f"  {f:6s}: {c:6d}")

    # Video distribution
    video_counts = Counter(s["video"] for s in samples)
    print(f"\nVideo distribution:")
    for v in sorted(video_counts.keys()):
        families = set(s["family"] for s in samples if s["video"] == v)
        print(f"  video {v}: {video_counts[v]:5d} samples, families: {sorted(families)}")

    # Split
    print(f"\nSplitting by video (test=04,07 val=05,14)...")
    train, val, test = video_split(samples)

    print(f"  Train: {len(train)} ({len(set(s['video'] for s in train))} videos)")
    print(f"  Val:   {len(val)} ({len(set(s['video'] for s in val))} videos)")
    print(f"  Test:  {len(test)} ({len(set(s['video'] for s in test))} videos)")

    for split_name, split_data in [("Train", train), ("Val", val), ("Test", test)]:
        fc = Counter(s["family"] for s in split_data)
        print(f"  {split_name} families: {dict(sorted(fc.items()))}")

    # Featurize
    print(f"\nExtracting features...")
    X_train, y_train, yf_train, _ = featurize(train)
    X_val, y_val, yf_val, _ = featurize(val)
    X_test, y_test, yf_test, _ = featurize(test)
    print(f"  Train: {X_train.shape}")
    print(f"  Val:   {X_val.shape}")
    print(f"  Test:  {X_test.shape}")

    # Get feature names for later
    _, feature_names = extract_features(samples[0]["me_kps"], samples[0]["op_kps"])

    # Scale
    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_val_s = scaler.transform(X_val)
    X_test_s = scaler.transform(X_test)

    # Replace any NaN from scaling
    X_train_s = np.nan_to_num(X_train_s, 0)
    X_val_s = np.nan_to_num(X_val_s, 0)
    X_test_s = np.nan_to_num(X_test_s, 0)

    # Label encoding
    le_family = LabelEncoder()
    le_family.fit(sorted(set(y_train) | set(y_val) | set(y_test)))
    y_train_enc = le_family.transform(y_train)
    y_val_enc = le_family.transform(y_val)
    y_test_enc = le_family.transform(y_test)
    family_classes = le_family.classes_

    # Models
    models = {
        "LogisticRegression": LogisticRegression(max_iter=1000, multi_class="multinomial", C=1.0),
        "RandomForest": RandomForestClassifier(n_estimators=200, max_depth=20, n_jobs=-1, random_state=42),
        "HistGradientBoosting": HistGradientBoostingClassifier(max_iter=300, max_depth=8, learning_rate=0.1, random_state=42),
        "MLP": MLPClassifier(hidden_layer_sizes=(128, 64), max_iter=500, early_stopping=True, validation_fraction=0.15, random_state=42),
    }

    results = {}
    best_model = None
    best_acc = 0

    for name, model in models.items():
        print(f"\n{'='*60}")
        print(f"  Training {name}...")
        t0 = time.time()

        # MLP needs encoded labels for early_stopping
        if name == "MLP":
            model.fit(X_train_s, y_train_enc)
            y_val_pred_raw = model.predict(X_val_s)
            y_val_pred = le_family.inverse_transform(y_val_pred_raw)
            y_test_pred_raw = model.predict(X_test_s)
            y_test_pred = le_family.inverse_transform(y_test_pred_raw)
        else:
            model.fit(X_train_s, y_train)
            y_val_pred = model.predict(X_val_s)
            y_test_pred = model.predict(X_test_s)

        train_time = time.time() - t0
        print(f"  Trained in {train_time:.1f}s")

        val_acc = accuracy_score(y_val, y_val_pred)
        val_f1 = f1_score(y_val, y_val_pred, average="macro")
        test_acc = accuracy_score(y_test, y_test_pred)
        test_f1 = f1_score(y_test, y_test_pred, average="macro")

        print(f"  Val  accuracy: {val_acc:.1%}  macro F1: {val_f1:.3f}")
        print(f"  Test accuracy: {test_acc:.1%}  macro F1: {test_f1:.3f}")

        # Top-3 accuracy if model supports predict_proba
        top3_acc = None
        if hasattr(model, "predict_proba"):
            try:
                proba_test = model.predict_proba(X_test_s)
                y_test_for_topk = le_family.transform(y_test)
                n_classes = proba_test.shape[1]
                k = min(3, n_classes)
                top3_acc = top_k_accuracy_score(
                    y_test_for_topk, proba_test, k=k,
                    labels=list(range(n_classes)),
                )
                print(f"  Test top-3 accuracy: {top3_acc:.1%}")
            except Exception as e:
                print(f"  Top-3 failed: {e}")

        results[name] = {
            "val_acc": val_acc, "val_f1": val_f1,
            "test_acc": test_acc, "test_f1": test_f1,
            "top3_acc": top3_acc,
            "predictions": y_test_pred,
        }

        if test_acc > best_acc:
            best_acc = test_acc
            best_model = name

    # Detailed report for best model
    print(f"\n{'='*60}")
    print(f"  BEST MODEL: {best_model} (test acc={best_acc:.1%})")
    print(f"{'='*60}")

    y_test_pred = results[best_model]["predictions"]

    print(f"\n  Per-class metrics:")
    print(classification_report(y_test, y_test_pred, digits=3))

    print(f"\n  Confusion matrix:")
    labels = sorted(set(y_test) | set(y_test_pred))
    cm = confusion_matrix(y_test, y_test_pred, labels=labels)
    header = f"  {'':>12s}" + "".join(f"{l:>12s}" for l in labels)
    print(header)
    for i, true_label in enumerate(labels):
        row = f"  {true_label:>12s}" + "".join(f"{cm[i][j]:>12d}" for j in range(len(labels)))
        print(row)

    # Feature importance (if available)
    model_obj = models[best_model]
    if hasattr(model_obj, "feature_importances_"):
        importances = model_obj.feature_importances_
        top_feats = sorted(zip(feature_names, importances), key=lambda x: -x[1])[:20]
        print(f"\n  Top 20 features:")
        for fname, imp in top_feats:
            print(f"    {imp:.4f}  {fname}")

    # Failure examples
    test_samples_valid = []
    for s in test:
        try:
            feats, _ = extract_features(s["me_kps"], s["op_kps"])
            if not any(math.isnan(f) or math.isinf(f) for f in feats):
                test_samples_valid.append(s)
        except Exception:
            continue

    failures = []
    for i, (true, pred) in enumerate(zip(y_test, y_test_pred)):
        if true != pred and i < len(test_samples_valid):
            s = test_samples_valid[i]
            failures.append({
                "image_id": s["image_id"],
                "video": s["video"],
                "position": s["position"],
                "true": true,
                "predicted": pred,
            })

    print(f"\n  Failure examples (first 20):")
    print(f"  {'Image':>10s} {'Video':>6s} {'Position':>18s} {'True':>12s} {'Pred':>12s}")
    for f in failures[:20]:
        print(f"  {f['image_id']:>10s} {f['video']:>6s} {f['position']:>18s} {f['true']:>12s} {f['predicted']:>12s}")

    # Summary table
    print(f"\n\n{'='*70}")
    print(f"  SUMMARY: Fundamental Radical Family Classification")
    print(f"  Split: by video (no frame leakage)")
    print(f"  Train: {len(train)}  Val: {len(val)}  Test: {len(test)}")
    print(f"{'='*70}")
    print(f"\n  {'Model':<25s} {'Val Acc':>8s} {'Test Acc':>9s} {'Test F1':>8s} {'Top-3':>7s}")
    print(f"  {'-'*25} {'-'*8} {'-'*9} {'-'*8} {'-'*7}")
    for name in models:
        r = results[name]
        t3 = f"{r['top3_acc']:.1%}" if r['top3_acc'] is not None else "n/a"
        print(f"  {name:<25s} {r['val_acc']:>8.1%} {r['test_acc']:>9.1%} {r['test_f1']:>8.3f} {t3:>7s}")

    # Save results
    output = {
        "n_train": len(train),
        "n_val": len(val),
        "n_test": len(test),
        "family_counts": dict(family_counts),
        "split": {
            "test_videos": ["04", "07"],
            "val_videos": ["05", "14"],
        },
        "results": {
            name: {
                "val_acc": r["val_acc"],
                "val_f1": r["val_f1"],
                "test_acc": r["test_acc"],
                "test_f1": r["test_f1"],
                "top3_acc": r["top3_acc"],
            }
            for name, r in results.items()
        },
        "best_model": best_model,
    }
    with open("data/algebra_eval/pose_classifier_results.json", "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nResults saved to data/algebra_eval/pose_classifier_results.json")


if __name__ == "__main__":
    train_and_evaluate()
