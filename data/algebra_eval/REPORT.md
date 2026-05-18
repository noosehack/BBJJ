# Algebra Evaluation Report

**Date**: 2026-05-07
**Dataset**: ViCoS BJJ, 37,409 samples (both poses present), 6 evaluable classes
**Pipeline**: keypoints -> observed CON/FRM -> radical match -> predicted position

## Bottom Line

**Overall accuracy: 25.6% (9,581 / 37,409)**
**Macro F1: 0.343**
**Random baseline for 6 classes: 16.7%**

The algebraic matcher is barely above random. It does not reliably classify classical positions from image-derived keypoints.

---

## Per-Class Results

| Class | N     | Accuracy | Precision | Recall | F1    | Top Wrong Prediction |
|-------|-------|----------|-----------|--------|-------|---------------------|
| SCTR  | 6,596 | 32.0%    | 70.3%     | 32.0%  | 0.440 | LSSO (1,617)        |
| BCTR  | 6,500 | 29.3%    | 51.9%     | 29.3%  | 0.375 | RDLR (996)          |
| HGRD  | 4,209 | 27.3%    | 43.8%     | 27.3%  | 0.337 | LSSO (786)          |
| CGRD  | 6,682 | 25.5%    | 76.8%     | 25.5%  | 0.383 | BCTR (946)          |
| 5050  | 6,467 | 24.7%    | 34.5%     | 24.7%  | 0.288 | LSSO (1,216)        |
| MNT   | 6,955 | 15.9%    | 43.3%     | 15.9%  | 0.233 | RDLR (1,103)        |

**SCTR is best** (32%) because it requires only 1 arm-to-torso contact + frame constraints (simplest radical).
**MNT is worst** (15.9%) because it requires 2 bilateral leg-to-torso contacts + facing opposed + on-ground (all fail frequently).

---

## Root Cause Analysis

### 1. Contact Inference is the Primary Failure (PERCEPTION)

**Problem**: 2D keypoint proximity != 3D contact/entanglement.

The contact inference treats any two limbs within a pixel distance threshold as "in contact." A knee that is *near* a torso in the 2D projection is not the same as a leg *wrapping around* a torso. In grappling, limbs from both athletes overlap in 2D even when there is no actual entanglement.

**Evidence**: LSSO (leg wraps opponent's arm) is the #1 wrong prediction (5,009 false positives). It requires one Me.Le->Op.Ar contact. In every grappling position, some leg is spatially near some arm in the 2D projection. The proximity-based inference cannot distinguish "near" from "wrapped."

**Impact**: Affects all positions. Single-contact radicals (DLR, SLX, RDLR, LSSO, OMOP) trigger on any random proximity.

### 2. Bilateral Leg Contacts Fail Systematically (PERCEPTION + ALGEBRA)

**Problem**: MNT, BCTR, and CGRD all require two leg-to-torso contacts (Me.Le+ and Me.Le- both wrapping Op.To). These are missed 12,279 times each.

**Why**: The torso axis (Op.To) is reconstructed as a single line from hip midpoint to shoulder midpoint. For a leg to "contact" this axis, the leg's keypoints must be close to this line in 2D. In mount/back control/closed guard, the legs wrap *around* the torso in 3D, but in the 2D projection they often appear at the sides of the torso, far from the torso axis midline.

### 3. POV Assignment is Broken (ALGEBRA)

**POV distribution**:
- Known POV (suffix convention): 24,717 samples, 35.3% accuracy
- Reversed POV: 11,212 samples, 7.7% accuracy
- No match either way: 1,480 samples, 0% accuracy

The "both" strategy tries both POV assignments and picks the one with higher match score. It picks the WRONG POV for 30% of samples (11,212 reversed). When it reverses POV, accuracy drops to 7.7% -- meaning the score function does not reliably prefer the correct assignment.

**Why**: The score function multiplies contact quality by frame bonus. Spurious contacts in the reversed orientation can score higher than correct contacts in the known orientation if the frame constraints happen to match (e.g., one athlete is lower in the image in both orientations).

### 4. Single-Contact Radicals Over-trigger (ALGEBRA)

DLR, SLX, RDLR, LSSO, OMOP each require only 1 contact and 0 frame constraints. With proximity-based inference producing ~10 candidate contacts per image, at least one will match any single-contact radical. These radicals act as "catch-all" bins.

**Evidence**: The confusion matrix shows massive false positives for LSSO (5,009), RDLR (3,856), SLX (3,384), DLR (3,080).

### 5. Frame Constraints are Weak Discriminators (PERCEPTION)

- **FacingOpposed**: computed from nose-to-shoulder direction. In grappling, athletes face many directions. Missed 6,472 times.
- **OnGround**: computed from hip-y position (higher y = lower in image). In side-lying positions, both athletes have similar hip heights. Missed 8,372 times.
- **KneeBracket**: checks if Me's knees bracket Op's torso. Fails when knees are folded or obscured.

### 6. Helicity is Noise (PERCEPTION)

Helicity (clockwise/counter-clockwise wrapping) is determined by a cross-product of 2D vectors. In 2D projections of 3D entanglement, the sign of this cross-product depends on camera angle, not actual wrapping direction. DLR vs SLX differ only in helicity -- the matcher cannot distinguish them.

---

## Classification of Failures

| Category | % of errors | Description |
|----------|------------|-------------|
| Perception: contact inference | ~50% | False contacts from 2D proximity |
| Perception: frame constraints | ~15% | Wrong facing/ground from 2D ambiguity |
| Algebra: POV assignment | ~20% | Wrong Me/Op assignment |
| Algebra: radical definitions too loose | ~10% | Single-contact radicals over-trigger |
| Algebra: radical definitions too strict | ~5% | Bilateral leg contacts fail on valid positions |

---

## What Works

- **SCTR has 70.3% precision**: when the matcher says SCTR, it's right 70% of the time. SCTR's unique combination of arm-to-torso + OnGround + NotKneeBracket is relatively discriminative.
- **CGRD has 76.8% precision**: when it matches, it's reliable (requires bilateral legs + closure + NotOnGround).
- **Known-POV accuracy (35.3%)** is 4.5x reversed-POV (7.7%), confirming POV matters enormously.

---

## Answers to the Five Questions

### 1. Does image-derived algebra classify classical positions?
**No.** 25.6% accuracy on 6 classes (random = 16.7%). The algebraic matcher adds only ~9 percentage points over random.

### 2. Which positions work?
**SCTR** (32% recall, 70% precision) is the only position with usable precision. CGRD has good precision (77%) but poor recall (25.5%).

### 3. Which positions fail?
**All of them fail at recall.** MNT (16%), 5050 (25%), HGRD (27%) are near random. The bilateral-contact positions (MNT, BCTR, CGRD) suffer most because both required contacts must independently match.

### 4. Are failures due to perception or algebra?
**Both, but perception dominates (~65%).** The 2D proximity-based contact inference cannot distinguish actual wrapping/entanglement from spatial coincidence. Even perfect algebra cannot recover from false contact signals. The algebra compounds the problem by allowing single-contact radicals to over-trigger.

### 5. What changes are required before training any pose->radical model?

**The current pipeline cannot be improved to usable accuracy by tuning thresholds or radical definitions.** The fundamental limitation is that 2D keypoint proximity is not a reliable signal for 3D contact/entanglement.

Required changes (in priority order):

1. **Train a direct position classifier on the 120K labeled dataset.** Use the 2x17x3 keypoints as features and the position label as the target. An MLP or random forest on normalized keypoints will massively outperform the algebraic matcher. This classifier handles the "what position is this" question.

2. **Relegate the algebraic layer to explainability.** After the classifier predicts a position, use the algebraic definitions as an explanatory overlay: "the classifier says MNT; here's what MNT means algebraically." This preserves the BLISP formalism without depending on it for accuracy.

3. **If algebraic matching must be primary**, the contact inference needs 3D reasoning (depth estimation, limb occlusion tracking, or temporal consistency from video). 2D proximity alone is fundamentally insufficient for grappling.

---

## Files

- `data/algebra_eval/algebra_eval_samples.csv` -- Stage 1 (600 samples)
- `data/algebra_eval/algebra_eval_samples.jsonl` -- Stage 1 JSONL
- `data/algebra_eval/algebra_eval_full.csv` -- Stage 2 (37,409 samples)
- `data/algebra_eval/algebra_eval_full.jsonl` -- Stage 2 JSONL
