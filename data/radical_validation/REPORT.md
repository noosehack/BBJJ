# Radical Validation Report

**Date:** 2026-05-14  
**Dataset:** ViCoS, 52,419 samples (7 evaluable classes)  
**Pipeline:** `tools/radical_validation.py`  
**Question:** Given a known labeled BJJ position, do the proposed relational radicals validate against observed body geometry?

## Executive Summary

95.4% of validation failures are **perceptual** (keypoint inference insufficient), not **notational** (radical definition wrong). The constraint algebra itself is structurally sound for 5 of 7 radicals. Two radicals have critical issues: TRTL (0% on its defining contact) and OGRD (frame-only definition creates massive overlap).

## Per-Class Constraint Satisfaction

| Class | N | All Met % | Avg Weighted | Avg Contacts |
|-------|---|-----------|--------------|--------------|
| OGRD | 12,657 | 98.6% | 0.725 | 4.6 |
| HGRD | 4,209 | 83.2% | 0.815 | 8.9 |
| SCTR | 6,596 | 56.3% | 0.836 | 9.8 |
| MNT | 6,955 | 55.2% | 0.726 | 12.3 |
| BCTR | 6,500 | 45.5% | 0.814 | 13.7 |
| CGRD | 6,682 | 35.0% | 0.751 | 11.1 |
| TRTL | 8,820 | 0.0% | 0.626 | 8.7 |

## Per-Radical Constraint Analysis

### Stable constraints (>90% satisfaction)

| Radical | Constraint | Satisfaction | Type |
|---------|-----------|-------------|------|
| TRTL | CON(Op.Le+->Me.To h=-) forbidden | 100.0% | forbidden_con |
| TRTL | CON(Op.Le-->Me.To h=+) forbidden | 100.0% | forbidden_con |
| CGRD | NotOnGround(Op.Ba) | 99.9% | frame |
| OGRD | OnGround(Me.Ba) | 98.6% | frame |
| MNT | OnGround(Op.Ba) | 98.3% | frame |
| HGRD | OnGround(Me.Ba) | 98.0% | frame |
| BCTR | CON(Me.Le+->Op.To h=-) | 92.5% | required_con |
| SCTR | OnGround(Op.Ba) | 91.1% | frame |
| BCTR | CON(Me.Fo-->Me.Fo+ h=0) forbidden | 91.2% | forbidden_con |
| MNT | CON(Me.Le+->Op.To h=-) | 90.0% | required_con |

**Ground/elevation frames are highly reliable** (91-100%). The 2D hip-height proxy works.

### Fragile constraints (<70% satisfaction)

| Radical | Constraint | Satisfaction | Type |
|---------|-----------|-------------|------|
| TRTL | CON(Op.To->Me.To h=0) | 0.0% | required_con |
| CGRD | CON(Me.Fo-->Me.Fo+ h=0) | 46.0% | required_con |
| MNT | FacingOpposed() | 46.0% | frame |
| OGRD | FacingOpposed() | 46.4% | frame |
| TRTL | FacingAligned() | 50.4% | frame |
| MNT | CON(Me.Le-->Op.To h=+) | 55.9% | required_con |
| HGRD | FacingOpposed() | 61.7% | frame |
| CGRD | CON(Me.Le-->Op.To h=+) | 65.6% | required_con |
| BCTR | NotOnGround(Op.Ba) | 69.7% | frame |

**Facing direction is unreliable** (46-62% for FacingOpposed, 50-81% for FacingAligned). This is a known 2D perception limitation — shoulder-direction dot product collapses under camera angle variation.

**The "minus-sign leg" contact** (Me.Le-->Op.To h=+) is fragile across MNT (56%), CGRD (66%), BCTR (73%). The left-leg-to-torso contact is harder to infer than the right-leg-to-torso, likely due to occlusion patterns.

**Ankle closure** (Me.Fo-->Me.Fo+ h=0) at 46% for CGRD is a known hard problem — the 2D ankle proximity test is a lossy proxy for the 3D leg-loop invariant.

## Failure Taxonomy

| Category | Count | % of Failures |
|----------|-------|---------------|
| Perception (weighted >= 0.5) | 22,498 | 95.4% |
| Notation (weighted < 0.3) | 1,081 | 4.6% |
| **Total failures** | **23,579** | |

### Top failure modes by class

**TRTL** — 8,820/8,820 fail (100%). The torso-to-torso CON `CON(Op.To->Me.To h=0)` has **0% satisfaction**. The current axis reconstruction cannot detect torso-on-torso contact because the torso axis is a virtual segment (hip-to-shoulder midline) and two overlapping torso axes never produce a small point-to-segment distance. This is purely perceptual — the notation is correct but the geometry pipeline cannot observe it.

**CGRD** — 4,341/6,682 fail (65%). Primary failure: ankle closure (3,075 perception failures). Secondary: left-leg contact (1,764 perception). The closed guard radical is the most constraint-heavy (3 required contacts + 1 frame), making it fragile to any single miss.

**MNT** — 3,116/6,955 fail (45%). Left-leg contact (2,810) and facing direction (1,128) dominate. Mount is structurally sound but hard to fully observe.

**BCTR** — 3,545/6,500 fail (55%). NotOnGround frame (1,718) is the top failure — the elevation heuristic struggles when both fighters are on the mat but one is face-down.

**SCTR** — 2,879/6,596 fail (44%). Forbidden leg contacts (1,284 + 1,323) trigger false violations — the contact inference detects leg-on-leg proximity in side control that shouldn't count.

**HGRD** — 708/4,209 fail (17%). Best-performing contact radical. FacingOpposed is the weak link (38% miss rate), but OnGround is reliable.

**OGRD** — 178/12,657 fail (1.4%). Nearly perfect — but it has only frame constraints and no required contacts, so this is expected.

## Confusion-Overlap Analysis

### Critical overlaps (rate where false radical has all_required_met)

| True Class | False Radical | Overlap Rate |
|------------|--------------|-------------|
| BCTR | DLR | 86.7% |
| BCTR | SLX | 86.7% |
| BCTR | RDLR | 86.2% |
| MNT | DLR | 85.6% |
| MNT | SLX | 85.7% |
| MNT | RDLR | 85.4% |
| CGRD | OGRD | 97.8% |
| HGRD | OGRD | 98.0% |
| OGRD | HGRD | 66.9% |

**OGRD subtypes (DLR, SLX, RDLR)** satisfy their constraints on 28-87% of non-OGRD samples. These radicals have only 1 required contact each (a specific leg-on-leg) with no frame constraints, making them extremely permissive. They fire as false positives on nearly any sample with detected leg proximity.

**OGRD as superclass** has 98.6% satisfaction on its own class, but HGRD also satisfies on 98% of OGRD samples (since HGRD's OnGround + leg contact are common in OGRD data). The OGRD definition (frame-only, no contacts) is too weak to discriminate.

## Positive vs Negative Scoring

The diagonal should be highest in each row. Violations indicate radicals that don't separate well:

| True | BCTR | CGRD | HGRD | MNT | OGRD | SCTR | TRTL |
|------|------|------|------|-----|------|------|------|
| BCTR | **0.814** | 0.618 | 0.377 | 0.529 | 0.106 | 0.427 | 0.702 |
| CGRD | 0.684 | **0.751** | 0.812 | 0.542 | 0.801 | 0.372 | 0.572 |
| HGRD | 0.468 | 0.353 | **0.815** | 0.216 | 0.799 | 0.389 | 0.557 |
| MNT | 0.555 | 0.401 | 0.460 | **0.726** | 0.230 | 0.573 | 0.601 |
| OGRD | 0.491 | 0.310 | 0.710 | 0.147 | **0.725** | 0.340 | 0.610 |
| SCTR | 0.385 | 0.200 | 0.301 | 0.521 | 0.274 | **0.836** | 0.568 |
| TRTL | 0.466 | 0.260 | 0.301 | 0.374 | 0.232 | 0.729 | **0.626** |

**SCTR is the strongest separator** — highest on-diagonal (0.836) with good margins. **TRTL is the weakest** — its true score (0.626) is beaten by SCTR (0.729) on TRTL samples. **CGRD vs HGRD** — HGRD scores higher (0.812) than CGRD (0.751) on CGRD's own data, because the ankle closure constraint drags CGRD down.

## OGRD Superclass Status

OGRD has no required contacts — only FacingOpposed + OnGround(Me.Ba). This makes it a frame envelope rather than a position radical. Evidence:

- 98.6% self-satisfaction, but HGRD satisfies on 66.9% of OGRD samples
- DLR/SLX each satisfy on 53% of OGRD samples
- OGRD satisfies on 97.8% of CGRD and 98.0% of HGRD samples (because those are both ground-player positions)

**Recommendation:** OGRD should remain a **superclass** (frame envelope) with subtypes (DLR, SLX, RDLR, LSSO, OMOP) providing discrimination. The notation is correct — OGRD *is* a family, not a specific position. But the subtypes need frame constraints added (at minimum FacingOpposed + OnGround(Me.Ba)) to reduce false positive rates.

## Recommendations

### Notation fixes (structural)

1. **TRTL torso-to-torso contact**: The notation is correct in 3D but unobservable in 2D. Either (a) add an alternative 2D-observable proxy constraint (e.g., hip-to-hip distance), or (b) mark TRTL as requiring 3D keypoints and exclude from 2D evaluation.

2. **OGRD subtype frame constraints**: Add `FacingOpposed() + OnGround(Me.Ba)` to DLR, SLX, RDLR, LSSO, OMOP. Currently these have no frame constraints, causing massive false positive rates.

3. **SCTR forbidden contacts**: The two forbidden leg-on-leg contacts (Me.Le->Op.Le+/- h=-) are violated ~22% of the time on true SCTR data. These may be too strict — consider raising the forbidden match threshold or switching to a bilateral forbidden (both legs must be present, not either).

### Perception fixes (inference pipeline)

1. **Facing direction**: The shoulder-dot-product heuristic fails ~50% of the time. Consider using hip-shoulder cross product, or torso orientation relative to camera, or make facing a soft constraint everywhere.

2. **Ankle closure**: 46% satisfaction for CGRD. The 2D ankle proximity test (CLOSURE_THRESHOLD=0.20) is too strict or the wrong proxy. Consider: hip angle difference, leg-crossing detection via keypoint ordering, or accept that closed guard requires 3D for reliable detection.

3. **Left-leg (minus-sign) contact**: Consistently lower satisfaction than right-leg. Investigate whether this is a labeling convention issue (ViCoS suffix→POV mapping) or genuine asymmetric occlusion.

### Depth in CON

Depth fields (d1, d2, d3) are symbolic labels in the notation but not validated against geometry. The contact inference assigns depth based on distance thresholds (deep <0.15, mid <0.3, shallow). The validation pipeline currently ignores depth in similarity scoring (handled by _con_similarity which gives 0.6 base for part match). Future work: validate whether inferred depth correlates with radical-specified depth levels.
