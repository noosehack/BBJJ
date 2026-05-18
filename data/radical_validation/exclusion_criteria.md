# Exclusion Criteria Audit

## Purpose

Determine whether categories A/B/C (used to exclude "perception failures" from validation) have rigorous operational definitions, or whether they act as a protective filter that makes the notation unfalsifiable.

## Category Definitions and Operational Criteria

### Category B — Keypoint Failure

**Current implementation:**

```
def _has_bad_keypoints(quality: dict) -> bool:
    for part_name, part_q in quality.items():
        if part_q["n_below_thresh"] > 0:
            return True
    return False
```

Threshold: `CONFIDENCE_THRESHOLD = 0.3` (from axis_reconstruction.py).

**Operational criterion:** At least one COCO keypoint involved in the failed constraint has confidence < 0.3.

**Is this objectively measurable?** YES. Keypoint confidence is a numeric output of the pose estimator. The threshold is fixed. No semantic judgment involved.

**Can it be abused?** PARTIALLY. The criterion is necessary but not sufficient for a genuine keypoint failure. A keypoint with confidence 0.29 might be perfectly localized; one with 0.31 might be badly wrong. The threshold is arbitrary. However:
- The criterion is applied uniformly across all constraints
- It does not depend on whether the constraint is met or not
- It cannot be tuned per-radical to protect specific results
- Population rate: 9.5% — plausible for COCO pose estimation on grappling images

**Ambiguity rate:** LOW. The criterion is binary (confidence above/below threshold). Edge cases exist near 0.3 but the impact is bounded.

**Assessment: LEGITIMATE but imprecise.** B classification is necessary for honest evaluation — you cannot evaluate contact detection when the body part is invisible. The threshold could be varied (0.2, 0.4) as a sensitivity analysis to test robustness of downstream results.

---

### Category C — 2D Observability Failure

**Current implementation:**

```python
CONSTRAINTS_2D_HARD = {
    "CON(Op.To->Me.To h=0)",     # torso-on-torso
    "CON(Me.Fo-->Me.Fo+ h=0)",   # ankle closure
}

CONSTRAINTS_2D_NOISY = {
    "FacingOpposed()",
    "FacingAligned()",
}
```

For required contacts not in these sets:

```python
if cs.constraint_type == "required_con":
    if "best_score=" in cs.detail:
        bs = float(cs.detail.split("best_score=")[1])
        if bs > 0.005:
            return "C"
    return "C"  # ← ALWAYS C
```

**Operational criterion:** One of:
1. Constraint is in a hardcoded list of "known 2D-unobservable" constraints, OR
2. Constraint is a required contact that failed (any required contact, regardless of context)

**Is this objectively measurable?** CRITERION 1: PARTIALLY — the list is a priori and physically motivated (torso-torso distance, ankle crossing, shoulder normal projection are geometrically understood to degrade under 2D projection). But the list is authored by the same team that authored the radicals. CRITERION 2: NO — this is the critical problem.

**THIS IS THE CIRCULAR REASONING:**

The classifier has **zero paths** from a failed required contact to category D (algebra too strict). Every required contact failure with adequate keypoints is classified as C. The decision tree:

```
required contact failed?
  → keypoints bad? → B
  → keypoints OK? → C (always)
  → NEVER D
```

This means: **the clean validation rate for required contacts is tautologically 100%.** The pipeline excludes every required-contact failure as "perception," then checks whether required contacts are met in the remaining samples. Of course they are — the failures were already removed.

**Can it be abused?** YES, AND IT IS. Not maliciously, but structurally. The classifier assumes every required contact in the notation is correct. This assumption is the conclusion it claims to reach.

**Ambiguity rate:** HIGH for required contacts. The pipeline cannot distinguish:
- "Contact exists physically but 2D projection makes it undetectable" (genuine C)
- "Contact does not exist because the position doesn't require it" (should be D)
- "Contact is present in most instances but this is a rare variation" (ambiguous)

Without ground truth for whether the contact actually exists in the image, this distinction is unknowable from keypoints alone.

**Assessment: ILLEGITIMATE for required contacts.** The C classification for required contacts contains an unfalsifiable assumption. It should be flagged as "UNKNOWN (B or C or D)" rather than assumed C.

---

### Category A — Bad Tag

**Current implementation:**

```python
if rv_true.weighted_score < 0.25:
    for rname in FUNDAMENTAL_RADICALS:
        if rv_other.all_required_met and rv_other.weighted_score >= 0.8:
            return "A"
```

**Operational criterion:** True radical weighted score < 0.25 AND some other fundamental radical has all requirements met with score >= 0.8.

**Is this objectively measurable?** YES, but the thresholds (0.25, 0.8) are arbitrary and the logic uses the very radicals being validated to judge tag correctness.

**Can it be abused?** SOMEWHAT. The threshold is very conservative (only 0.1% of samples flagged), so it excludes almost nothing. If the notation were systematically wrong, this would not catch it.

**Ambiguity rate:** LOW (because the threshold is so high that almost nothing qualifies).

**Assessment: LEGITIMATE but nearly inert.** 4 samples out of 7,000 is negligible. This category has no material effect on results.

---

## Quantitative Impact of Exclusions

### How many failures become "notation-valid" only because of exclusion?

| Class | Total | Excluded (A+B+C) | Exclusion Rate | Clean N | Clean Met | "Clean Rate" |
|-------|------:|------------------:|---------------:|--------:|----------:|----------:|
| CGRD | 1,000 | 636 | 63.6% | 364 | 364 | 100.0% |
| HGRD | 1,000 | 150 | 15.0% | 850 | 834 | 98.1% |
| MNT | 1,000 | 437 | 43.7% | 563 | 552 | 98.0% |
| OGRD | 1,000 | 2 | 0.2% | 998 | 986 | 98.8% |
| BCTR | 1,000 | 240 | 24.0% | 760 | 471 | 62.0% |
| SCTR | 1,000 | 125 | 12.5% | 875 | 583 | 66.6% |
| TRTL | 1,000 | 1,000 | 100.0% | 0 | 0 | N/A |

**CGRD** excludes 63.6% of samples to achieve 100% clean validation. Of the 364 "clean" samples, only 7 (0.7% of total) are truly OK (validate AND separate). The 100% clean rate is real but misleading — it says "when the notation can be tested, it passes" while hiding that it can be tested on only 36.4% of samples.

**TRTL** excludes 100% of samples. The notation is literally untestable from this data. Claiming it is "correct" is an assumption, not a finding.

**HGRD** has 0% OK rate despite 98.1% clean validation. Every clean HGRD sample also has at least one false fundamental radical passing (mostly OGRD). The notation validates but does not discriminate.

### What the raw (unexcluded) rates actually show

| Class | Raw all_met rate (no exclusion) |
|-------|---:|
| OGRD | 98.6% |
| HGRD | 83.2% |
| MNT | 55.2% |
| SCTR | 56.3% |
| BCTR | 45.5% |
| CGRD | 35.0% |
| TRTL | 0.0% |

These are the honest numbers. No exclusion, no reinterpretation. On raw data, the notation validates at 98.6% for OGRD (which has only frame constraints and no contacts), 83.2% for HGRD, and 35-56% for the rest. TRTL is at 0%.

---

## Adversarial Examples

Cases where a notation failure could be incorrectly classified as a perception failure:

### Example 1: MNT left-leg contact (Me.Le-->Op.To)

The classifier says: "left leg keypoints are present (confidence > 0.3), contact not detected, therefore C (2D projection failure)."

Alternative explanation: some mount positions do not actually have the left leg tightly against the torso. The rider's left leg may be posted wide, hook under the arm, or be transitioning. The CONTACT may not exist — it's not that 2D projection hides it, it's that the leg is not on the torso. This would be D (notation requires a contact that isn't always present), classified as C.

The pipeline cannot distinguish these because it never examines the image.

### Example 2: CGRD ankle closure (Me.Fo-->Me.Fo+)

The classifier says: "ankle keypoints present, closure not detected, therefore C."

Alternative explanation: some closed guard positions have the ankles uncrossed — the guard player may have feet on hips, butterflied legs, or be in a transitional state where ankles aren't locked. The dataset tags these as "closed_guard" but the ankles may genuinely be apart. This is either A (bad tag — should be open guard) or D (ankle closure isn't invariant to closed guard), classified as C.

### Example 3: HGRD FacingOpposed

The classifier says: "facing direction is 2D-noisy, therefore C."

Alternative explanation: some half guard positions genuinely do NOT have fighters facing each other — the top player may be perpendicular (knee-cut position) or at an angle (quarter-guard). The constraint may be contingent rather than invariant. This would be D, classified as C.

---

## Conclusion

The current exclusion logic contains a structural circularity for required contacts. The C classification for required contacts is unfalsifiable: there is no code path that can assign D to a required contact failure, regardless of evidence. This makes the "98-100% clean validation rate" for CGRD, HGRD, MNT, and OGRD a consequence of the classifier design, not an empirical finding.

**What IS defensible:**
- B classification (keypoint confidence below threshold) is legitimate
- The raw unexcluded rates (35-98.6%) are empirically honest
- D classification for forbidden contacts and ground frames is legitimate
- The SCTR (29.2% D) and BCTR (28.9% D) findings are real

**What is NOT defensible:**
- "100% clean validation" for CGRD
- "TRTL notation is correct" (untestable)
- Any claim about required contacts being "correct" based on this pipeline
- The distinction between C and D for required contacts
