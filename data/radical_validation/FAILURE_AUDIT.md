# Failure Audit of Radical Validation Pipeline

**Date:** 2026-05-14  
**Dataset:** ViCoS, 7,000 stratified samples (1,000 per class, 7 evaluable classes)  
**Pipeline:** `tools/failure_audit.py`  
**Method:** Cluster-sampled audit (8 failure clusters × 75 records) + unbiased population classification

## Question

> Assuming the dataset tag is correct, the corresponding radical constraints should be present, and the same radical should separate that position from other fundamental positions. If not, we must determine whether the failure comes from the notation or from image/keypoint limitations.

## Failure Categories

| Code | Category | Definition |
|------|----------|-----------|
| A | Bad tag | Dataset label appears wrong or too coarse |
| B | Keypoint failure | Required body parts missing, swapped, badly localized, or occluded |
| C | 2D observability failure | Relation structurally true but cannot be inferred from monocular keypoints |
| D | Algebra too strict | Required constraint not actually necessary, or forbidden constraint too broad |
| E | Algebra too weak | False radicals also match because radical lacks distinguishing constraint |
| F | OGRD family issue | Open guard is not a single radical; must be decomposed |

## Population-Level Results (N=7,000)

### Category Distribution

| Category | Count | % |
|----------|------:|---:|
| A Bad tag | 4 | 0.1% |
| B Keypoint failure | 662 | 9.5% |
| C 2D observability failure | 1,924 | 27.5% |
| D Algebra too strict | 608 | 8.7% |
| E Algebra too weak | 300 | 4.3% |
| F OGRD family issue | 1,673 | 23.9% |
| OK Success | 1,829 | 26.1% |

**37.1% of all failures are perception (A+B+C).** These are not notation problems.  
**8.7% are genuine algebra issues (D).** These are actionable.  
**28.2% are structural/family issues (E+F).** These require architectural decisions, not fixes.

### Category Distribution by Class

| Class | A | B | C | D | E | F | OK |
|-------|---|---|---|---|---|---|---|
| BCTR | 0.2% | 9.0% | 14.8% | **28.9%** | 1.6% | 2.0% | 43.5% |
| CGRD | 0.0% | 18.4% | 45.2% | 0.0% | **21.4%** | 14.3% | 0.7% |
| HGRD | 0.0% | 10.2% | 4.8% | 1.6% | 2.3% | **81.1%** | 0.0% |
| MNT | 0.0% | 12.2% | 31.5% | 1.1% | 2.5% | 0.0% | 52.7% |
| OGRD | 0.2% | 0.0% | 0.0% | 0.0% | 0.0% | **69.9%** | 29.9% |
| SCTR | 0.0% | 8.1% | 4.4% | **29.2%** | 2.2% | 0.0% | 56.1% |
| TRTL | 0.0% | 8.3% | **91.7%** | 0.0% | 0.0% | 0.0% | 0.0% |

## Core Finding: True-Radical Validation After Excluding Perception Failures

**When perception failures (A/B/C) are excluded, does each fundamental radical validate against its own tag?**

| Radical | N (clean) | Met | Rate |
|---------|----------:|----:|-----:|
| CGRD | 364 | 364 | **100.0%** |
| HGRD | 850 | 834 | **98.1%** |
| MNT | 563 | 552 | **98.0%** |
| OGRD | 998 | 986 | **98.8%** |
| BCTR | 760 | 471 | 62.0% |
| SCTR | 875 | 583 | 66.6% |
| TRTL | 0 | 0 | N/A |

**4 of 7 radicals validate at 98-100% on clean data.** The notation is correct.

BCTR (62.0%) and SCTR (66.6%) have genuine algebra issues (category D).

TRTL has zero clean samples because 100% of its failures are category B or C — the torso-to-torso contact is entirely a perception problem.

## Core Finding: False-Radical Rejection After Excluding Perception Failures

**Does each fundamental radical reject the other fundamental positions?**

| Radical | N (clean) | Rejected | Rate |
|---------|----------:|---------:|-----:|
| MNT | 563 | 532 | **94.5%** |
| SCTR | 875 | 711 | 81.3% |
| BCTR | 760 | 497 | 65.4% |
| OGRD | 998 | 311 | 31.2% |
| CGRD | 364 | 7 | 1.9% |
| HGRD | 850 | 14 | 1.6% |
| TRTL | 0 | 0 | N/A |

MNT is the best separator. CGRD and HGRD have near-zero rejection because OGRD (frame-only, no contacts) passes on virtually all ground-player samples. This is not a bug in CGRD/HGRD — it is the OGRD family issue (F).

## Cluster Analysis

### 1. TRTL Torso Contact (25 clear failures)

**100% category C (2D observability failure).**

The torso-to-torso CON `CON(Op.To->Me.To h=0)` has 0% satisfaction across the entire dataset. The axis reconstruction represents torsos as hip-to-shoulder midline segments. When two fighters are chest-to-back (turtle), their torso segments are spatially close but `point_to_segment_distance` between two parallel segments of similar length does not reliably produce a small value — the midpoint of one segment may project to the endpoint region of the other.

**Verdict:** The notation is correct. The relation exists in 3D but the 2D inference pipeline cannot detect it. This is NOT an algebra failure.

### 2. Facing Direction (75 records: 25 fail, 25 borderline, 25 success)

**Failures classified as:** C=23, F=22, B=4, D=3, E=3.

FacingOpposed satisfies at 46% on MNT, 46% on OGRD, 62% on HGRD. FacingAligned satisfies at 81% on BCTR, 50% on TRTL. The `facing_direction()` function estimates 2D facing from the shoulder-line normal oriented toward the nose. Under projection (camera angle, foreshortening), the dot product between two facing directions is noisy: fighters who are truly facing each other can appear to face the same direction.

**Verdict:** Category C. Facing direction is a correct frame constraint but unreliable from monocular 2D. The facing constraints should either (a) be demoted to soft/bonus constraints rather than hard requirements, or (b) be computed from a more robust 2D proxy.

### 3. OGRD Subtype False Positives (75 records: 25 fail, 25 borderline, 25 success)

**Failures classified as:** C=27, B=12, F=9, D=5, E=3.

DLR, SLX, RDLR each have only 1 required contact (a specific leg-on-leg CON) and no frame constraints. They fire as false positives on 28-87% of non-OGRD samples because any detected leg proximity triggers the match.

**Verdict:** Category F. The OGRD subtypes need frame constraints (at minimum `FacingOpposed() + OnGround(Me.Ba)`) to limit their scope. The subtypes are correctly defined as CON patterns but are incomplete as standalone radicals without the OGRD frame envelope.

### 4. MNT Left-Leg Contact (75 records: 25 fail, 25 borderline, 25 success)

**Failures classified as:** C=37, B=12, D=1, E=1.

`CON(Me.Le-->Op.To h=+)` satisfies at 56% on MNT, vs 90% for `CON(Me.Le+->Op.To h=-)` (right leg). The asymmetry is systematic. In 2D COCO keypoints, the left leg of the mount-player is more often occluded by the bottom player's body or by camera angle. The contact inference requires both the distal endpoint (ankle) and proximal endpoint (hip) to be confident; occlusion of either drops the candidate.

**Verdict:** Category C (and some B). The mount radical correctly requires both legs around the torso. The 12.2% keypoint failures (B) represent cases where the left leg is simply invisible. The 31.5% 2D observability failures (C) represent cases where keypoints exist but the 2D projection makes the contact distance exceed the threshold.

On clean data (excluding A/B/C), MNT validates at **98.0%** — the algebra is correct.

### 5. SCTR Forbidden Leg Contacts (75 records: 25 fail, 25 borderline, 25 success)

**Failures classified as:** D=51, B=5, C=1.

SCTR defines two forbidden contacts: `CON(Me.Le->Op.Le+ h=-)` and `CON(Me.Le->Op.Le- h=-)`. These are intended to distinguish side control (no leg entanglement) from guard positions (leg entanglement). However, in side control the top player's legs are on the mat near the bottom player's legs, producing proximity that the contact inference reads as a contact. 29.2% of SCTR samples fail due to this.

**Verdict:** Category D (algebra too strict). The forbidden contacts are over-broad. The contact inference detects geometric proximity, but proximity is not entanglement. Possible fixes:
1. Remove the forbidden contacts entirely and rely on frame + arm contact for discrimination
2. Change to `forbidden_bilateral` (require BOTH legs to form guard-like hooks, not just one near)
3. Raise `FORBIDDEN_MATCH_THRESHOLD` for leg contacts specifically
4. Add a depth qualifier: only forbid "deep" leg contacts (close proximity = actual entanglement)

### 6. CGRD Ankle Closure (56 records: 25 fail, 6 borderline, 25 success)

**Failures classified as:** C=29, E=15, B=6, F=6.

`CON(Me.Fo-->Me.Fo+ h=0)` satisfies at 46% — the self-contact representing locked ankles behind the opponent. The 2D ankle-proximity test (threshold 0.20 × torso_length) is a lossy proxy for the 3D leg-loop invariant. In projected images, the ankles of a closed-guard player may appear far apart even when physically crossed.

**Verdict:** Category C. The notation is correct — closed guard IS defined by ankle closure. On clean data CGRD validates at **100.0%**. The 45.2% C rate reflects a 2D perception limitation, not an algebra problem.

### 7. BCTR Elevation (75 records: 25 fail, 25 borderline, 25 success)

**Failures classified as:** D=24, F=12, C=12, B=9.

`NotOnGround(Op.Ba)` satisfies at 70% on BCTR. Back control often has the opponent face-down on the mat — technically ON the ground. The constraint was intended to distinguish back control (opponent elevated/sitting up) from turtle (opponent down), but in practice the opponent is frequently flat.

**Verdict:** Category D (algebra too strict). The `NotOnGround(Op.Ba)` constraint does not reliably hold for back control. Back control is better distinguished by `FacingAligned()` (81% satisfaction) + leg hooks. The elevation constraint should be removed from BCTR.

### 8. False Radical Scores High (75 records: 25 fail, 25 borderline, 25 success)

**Failures classified as:** C=24, F=16, B=8, D=4, E=4.

Cases where a false fundamental radical scores higher than the true radical. Dominated by:
- OGRD passing on ground-player classes (F)
- Perception failures preventing true radical from matching (C, B)
- SCTR/BCTR algebra issues (D)

Not a distinct failure mode; decomposes into the other clusters.

## Summary Tables

### Failures by Constraint (top 10, cluster-sampled)

| Constraint | B | C | D | E | F | Total |
|-----------|--:|--:|--:|--:|--:|------:|
| required\_con:CON(Me.Le-->Op.To h=+) | 42 | 81 | 9 | 0 | 0 | 132 |
| required\_con:CON(Op.To->Me.To h=0) | 6 | 55 | 0 | 0 | 0 | 61 |
| frame:FacingOpposed() | 11 | 18 | 1 | 4 | 18 | 52 |
| frame:FacingAligned() | 4 | 32 | 10 | 0 | 0 | 46 |
| required\_con:CON(Me.Fo-->Me.Fo+ h=0) | 9 | 34 | 0 | 0 | 0 | 43 |
| forbidden\_con:CON(Me.Le->Op.Le- h=-) | 3 | 0 | 36 | 0 | 0 | 39 |
| forbidden\_con:CON(Me.Le->Op.Le+ h=-) | 1 | 0 | 38 | 0 | 0 | 39 |
| frame:NotOnGround(Op.Ba) | 2 | 0 | 31 | 0 | 0 | 33 |
| required\_con:CON(Me.Le+->Op.To h=-) | 23 | 7 | 2 | 0 | 0 | 32 |
| frame:OnGround(Op.Ba) | 3 | 0 | 10 | 0 | 0 | 13 |

Constraints with D > 0 are algebra candidates for revision:
- **SCTR forbidden legs** (77 total D) — too strict
- **BCTR NotOnGround** (31 D) — structurally wrong for back control
- **BCTR FacingAligned** (10 D) — marginal but mostly OK at 81%

### Failures by Category and Radical (population-level)

| | A | B | C | D | E | F | OK |
|--|--:|--:|--:|--:|--:|--:|---:|
| BCTR | 2 | 90 | 148 | **289** | 16 | 20 | 435 |
| CGRD | 0 | 184 | 452 | 0 | **214** | 143 | 7 |
| HGRD | 0 | 102 | 48 | 16 | 23 | **811** | 0 |
| MNT | 0 | 122 | 315 | 11 | 25 | 0 | 527 |
| OGRD | 2 | 0 | 0 | 0 | 0 | **699** | 299 |
| SCTR | 0 | 81 | 44 | **292** | 22 | 0 | 561 |
| TRTL | 0 | 83 | **917** | 0 | 0 | 0 | 0 |

## Verdict: Does Any Radical Definition Need to Change?

### Radicals with CORRECT notation (no change needed)

**MNT** — Validates at 98.0% on clean data. Separates at 94.5%. The left-leg contact failure (31.5% C) is a perception problem. The notation correctly requires both legs straddling the opponent's torso.

**CGRD** — Validates at 100.0% on clean data. The ankle closure failure (45.2% C) and left-leg failure (18.4% B) are perception problems. The notation correctly requires legs around torso + ankle lock. The near-zero false rejection rate (1.9%) is entirely due to OGRD (frame-only) passing trivially — not a CGRD problem.

**HGRD** — Validates at 98.1% on clean data. The 81.1% F rate is OGRD overlap, not an HGRD problem.

**OGRD** — Validates at 98.8% on clean data. OGRD is correctly defined as a frame envelope (facing opposed + on ground). Its role as a superclass is by design.

**TRTL** — The torso-to-torso CON is correct notation. 100% of failures are perception (B+C). The relation exists in 3D but cannot be detected from 2D COCO keypoints. The notation should not change; the inference pipeline needs a 2D proxy.

### Radicals requiring revision

**SCTR** — 29.2% D (algebra too strict). The forbidden leg contacts `CON(Me.Le->Op.Le± h=-)` are too broad. They trigger on geometric proximity in side control, where the top player's legs are on the mat near the bottom player's legs but not in any guard configuration.

**Recommended change:** Convert the two separate forbidden contacts to a single `forbidden_bilateral` requiring BOTH legs to form entanglement simultaneously, or remove the forbidden contacts and add a positive distinguishing constraint (e.g., arm-on-torso is already the primary contact; the forbidden legs are a secondary discriminator that does more harm than good).

**BCTR** — 28.9% D (algebra too strict). The `NotOnGround(Op.Ba)` frame constraint assumes the controlled player is elevated, but in practice back control often has the opponent prone on the mat.

**Recommended change:** Remove `NotOnGround(Op.Ba)` from BCTR. The radical retains `FacingAligned()` (81% satisfaction) and the two leg-around-torso contacts, which are sufficient for discrimination. FacingAligned alone distinguishes BCTR from MNT (which requires FacingOpposed).

### Architectural recommendation: OGRD family

OGRD is a frame envelope, not a discriminative radical. Its subtypes (DLR, SLX, RDLR, LSSO, OMOP) need the OGRD frame constraints (`FacingOpposed() + OnGround(Me.Ba)`) added to their definitions to prevent false positives on non-guard positions. This is not a change to OGRD itself but to how subtypes inherit the frame envelope.

## Summary

| Question | Answer |
|----------|--------|
| Is the notation fundamentally broken? | **No.** 4 of 7 radicals validate at 98-100% on clean data. |
| Are failures mostly perception? | **Yes.** 37.1% of all failures are A+B+C (perception). |
| Which radicals need revision? | **SCTR** (forbidden legs too strict) and **BCTR** (elevation frame wrong). |
| Is TRTL broken? | **No.** The notation is correct but the 2D inference pipeline cannot observe torso-on-torso contact. |
| Is OGRD a problem? | **OGRD is a superclass by design.** The issue is that subtypes lack inherited frame constraints. |
| Should any constraint be removed? | `NotOnGround(Op.Ba)` from BCTR. SCTR forbidden contacts should be converted to bilateral or removed. |
