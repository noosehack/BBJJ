# Feature Engineering for YOLO-Robust Position Classification

Three trials of feature engineering for BJJ position classification,
focused on closing the accuracy gap between ground-truth keypoints and
YOLO-detected keypoints.

**Evaluation protocol**: 360 frozen images (stride-50, 8 classes, balanced).
Train on GT keypoints from ViCoS annotations (58K samples, video split).
Evaluate on frozen benchmark with both GT and YOLO keypoints.
Classifier: MLP (256-128), sklearn, early stopping.

---

## Trial 1: Perception Backend Comparison

**Question**: Which pose estimation backend best handles entangled athletes?

| Backend | Detection rate | Accuracy | PCK@0.5 |
|---------|---------------|----------|---------|
| GT (annotations) | 100% | 88.6% | 100% |
| YOLO fine-tuned v2 | 96% | 63.1% | 76.2% |
| OpenPifPaf (bottom-up) | 64% | 12.2% | 53.8% |
| MMPose RTMO (bottom-up) | 32% | 12.5% | 72.5% |

**Finding**: Bottom-up pose estimation is categorically worse for grappling.
OpenPifPaf detects more people but with poor keypoints. RTMO has decent
keypoint quality when it detects someone but misses most athletes entirely.
Top-down YOLO wins by a wide margin. The GT→YOLO degradation (88.6%→63.1%,
-25.5pp) is the gap to close with better features.

**Files**: `tools/benchmark_perception.py`, `benchmark_perception/results/`

---

## Trial 2: Naked Cross-Ratio Features

**Hypothesis**: Cross-ratios are projective invariants (scale/perspective
invariant). They should be more stable under keypoint perturbation than
body-frame-relative coordinates.

**Design**: 31 quadruples of COCO landmarks (torso, shoulder, hip, knee,
ankle, arm, head groups). Each produces 3 features: log(CR), orientation
sign, min confidence. Total: 93 cross-ratio features.

Five classifiers compared:

| Classifier | Features | GT acc | YOLO acc | Degradation |
|------------|----------|--------|----------|-------------|
| geometry_only | 203 | 81.6% | 59.2% | 22.3% |
| cross_ratio_only | 93 | 88.3% | 43.6% | 44.6% |
| combined | 296 | 85.8% | 49.1% | 36.6% |
| geo_conf_weighted | 203 | 81.8% | 67.1% | 14.8% |
| conf_weighted | 296 | 85.8% | 69.1% | 16.7% |

**Finding 1**: Naked cross-ratios achieve high GT accuracy (88.3%) but
collapse on YOLO (43.6%, worse than geometry alone). The log_cr values are
extremely sensitive to keypoint noise — mean stability ratio 4.15 for CRs
vs 1073 for raw geometry features, but the log transform amplifies small
denominator perturbations.

**Finding 2**: Confidence weighting is the dominant robustness mechanism.
Multiplying features by keypoint confidence gates unreliable features and
provides +8pp for geometry, +20pp for combined features. The geo_conf_weighted
classifier achieves the best degradation (14.8%) — simply weighting the
existing geometry features by confidence is more effective than adding
cross-ratios.

**Finding 3**: Naked cross-ratios lose topology information. CR(A,B,C,D) is
a single scalar — it doesn't tell you which side A is on relative to B, or
whether the landmarks are ordered left-to-right. Two very different body
configurations can produce the same cross-ratio.

**Files**: `tools/cross_ratio_features.py`, `tools/cross_ratio_benchmark.py`,
`benchmark_perception/cross_ratio/`

---

## Trial 3: Ordered Projective Cross-Ratio Constraints

**Hypothesis**: Ordered projective constraints preserve the topological
information that naked CRs discard (ordering, sidedness, bracket patterns)
while retaining projective invariance for the cross-ratio component.

**Design**: 27 constraints, each projecting 4 semantic landmarks onto a
body-frame axis (me_torso, op_torso, me_hip, op_hip, me_sh, center_line).
Each constraint produces 16 features:

- 6 order signs: pairwise comparison signs encoding projected ordering
- 1 log cross-ratio: projective invariant
- 2 distance ratios: relative spacing along axis
- 4 lateral displacements: perpendicular offset from axis (normalized)
- 2 bracket predicates: same-side/opposite-side patterns
- 1 min confidence: quality gate

Total: 432 ordered CR features. All confidence-weighted.

27 constraints organized by body region:
- Torso stacking (4): torso-on-torso via me/op axes
- Knee straddle (5): knee pairs projected onto opponent torso/hip
- Ankle-torso (4): ankle wrap patterns around torso axes
- Knee entanglement (3): knee-knee interactions
- Ankle-ankle (2): ankle alignment
- Shoulder alignment (2): shoulder pairs across athletes
- Arm engagement (2): wrist-to-torso reach
- Head-body (2): head position relative to hips
- Mixed cross-body (3): asymmetric cross-athlete patterns

Four classifiers compared:

| Classifier | Features | GT acc | YOLO acc | Degradation |
|------------|----------|--------|----------|-------------|
| A: geo_cw | 203 | 81.8% | 67.1% | 14.8% |
| B: naked_cr_cw | 93 | 88.5% | 56.1% | 32.5% |
| C: ordered_cr_cw | 432 | 90.8% | 74.0% | 16.8% |
| D: geo + ordered_cr_cw | 635 | 89.1% | 75.7% | 13.4% |

**Per-class YOLO accuracy (D: geo + ordered_cr_cw)**:

| Class | GT acc | YOLO acc | Degradation |
|-------|--------|----------|-------------|
| BCTR | 78% | 61% | +17% |
| CGRD | 82% | 70% | +11% |
| HGRD | 92% | 74% | +18% |
| MNT | 92% | 60% | +32% |
| OGRD | 96% | 98% | -2% |
| SCTR | 88% | 65% | +22% |
| STND | 100% | 96% | +4% |
| TRTL | 78% | 75% | +3% |

**Feature stability by type** (mean |delta_f|/|f| GT→YOLO):

| Feature type | Mean stability | Median stability |
|-------------|---------------|-----------------|
| minconf | 1.08 | 1.06 |
| bracket | 1.22 | 1.35 |
| order signs | 1.38 | 1.40 |
| dist_ratios | 4.88 | 3.56 |
| lateral | 4.41 | 3.31 |
| log_cr | 20.41 | 15.57 |

**Finding 1**: Ordered CR features dramatically outperform naked CRs.
YOLO accuracy jumps from 56.1% (naked) to 74.0% (ordered), an +18pp gain.
The order signatures and bracket predicates carry most of the discriminative
power while being the most YOLO-stable features.

**Finding 2**: The combined model (D) achieves the best YOLO accuracy
(75.7%) and lowest degradation (13.4%). Adding geometry features to ordered
CRs helps by +1.7pp YOLO — a modest but consistent improvement. The
geometry features contribute complementary information (body-frame angles,
normalized distances) that ordered CRs don't capture.

**Finding 3**: log_cr remains the least stable feature type (mean 20.4) but
the order signatures compensate — they encode the same topological information
as a discrete signal that only flips when landmarks actually swap position.

**Finding 4**: OGRD (open guard) benefits most from ordered CRs, jumping
from 68% (naked) to 98% YOLO accuracy. TRTL (turtle) also improves
dramatically (12%→75%). MNT (mount) remains the hardest class at 60% YOLO
due to heavy occlusion.

**Finding 5**: The dominant confusion pattern across all classifiers is
misclassification as TKDN (takedown) under YOLO — this is a detection
artifact where poor keypoint quality makes dynamic positions look like
transitions.

**Files**: `tools/ordered_cross_ratio.py`, `tools/ordered_cr_benchmark.py`,
`benchmark_perception/ordered_cr/`

---

## Progression Summary

```
Trial 1 (baseline):     GT 81.6% → YOLO 59.2%   degrad 22.3%   (geometry only)
Trial 2 (conf weight):  GT 85.8% → YOLO 69.1%   degrad 16.7%   (geo+CR conf-weighted)
Trial 3 (ordered CR):   GT 89.1% → YOLO 75.7%   degrad 13.4%   (geo+ordered CR conf-weighted)
```

Net improvement: +16.5pp YOLO accuracy, -8.9pp degradation gap.

Key insights:
1. **Confidence weighting** is the single most impactful technique (+8pp alone)
2. **Order signatures** are more valuable than cross-ratio values themselves
3. **Body-frame projection** provides the semantic grounding that naked CRs lack
4. **Bracket predicates** (same-side/opposite-side) are near-binary and almost perfectly stable
5. **Top-down detection** (YOLO) is essential — bottom-up methods fail on entangled bodies

---

## Remaining Weaknesses

- **MNT** (mount): 60% YOLO, 32% degradation. Heavy torso-on-torso occlusion
  makes lower-body keypoints unreliable. Needs upper-body-only features.
- **SCTR** (side control): 65% YOLO, 22% degradation. Often confused with
  HGRD when the classifier can't resolve the relative torso orientation.
- **BCTR** (back control): 61% YOLO, 17% degradation. Aligned-facing
  constraint is hard to verify from noisy keypoints.
- **TKDN confusion**: the dominant misclassification target across all
  classifiers. Consider a TKDN-vs-position meta-classifier or temporal
  smoothing.

## Deployment

The `geo_ordered_cr_cw` feature set (635 features, MLP 256-128) is the
recommended production configuration. Feature extraction runs in <1ms per
frame. Train with `tools/ordered_cr_benchmark.py`, deploy via
`tools/geometry_classifier.py` with the updated feature pipeline.
