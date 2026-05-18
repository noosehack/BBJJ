# Challenge Report: Stress-Testing the Radical Formalism

**Date:** 2026-05-14  
**Purpose:** Determine whether the current validation results genuinely support the notation, or whether the evaluation pipeline contains circular reasoning, confirmation bias, or over-filtering.

---

## Executive Summary

The notation DOES encode real positional structure, but the evaluation pipeline is structurally incapable of falsifying required contacts. The "98-100% clean validation" claim is a tautology, not an empirical finding. After honest accounting:

- **4 claims survive:** CON as primitive, MNT discrimination, stable-attractor scope, SCTR/BCTR algebra issues
- **3 claims are invalidated:** "98-100% clean validation," "7 fundamental radicals," TRTL notation correctness
- **2 claims need human verification:** required-contact necessity, TRTL torso contact existence

The formalism is worth pursuing but needs honest empirical grounding that the current pipeline cannot provide.

---

## Task 1: Exclusion Logic Audit

**Full analysis:** [exclusion_criteria.md](exclusion_criteria.md)

### The Critical Finding

The function `classify_constraint_failure()` has **no code path** from a required-contact failure to category D (algebra too strict). Every required-contact failure with adequate keypoints is classified as C (2D observability failure). This makes the "clean validation rate" for required contacts tautologically 100%.

### Operational Criteria Assessment

| Category | Objective? | Abusable? | Ambiguity |
|----------|-----------|-----------|-----------|
| A (Bad tag) | Yes (numeric thresholds) | No (nearly inert, 0.1%) | Low |
| B (Keypoint) | Yes (confidence < 0.3) | Partially (threshold is arbitrary) | Low |
| C (2D observability) | **No** for required contacts | **Yes — structurally** | **High** |
| D (Algebra too strict) | Yes for forbidden/frames | No | Moderate |

### Quantitative Impact

| Class | Excluded (A+B+C) | Raw all_met | Clean all_met | OK rate |
|-------|------------------:|------------:|--------------:|--------:|
| CGRD | 63.6% | 35.0% | 100.0% (tautology) | **0.7%** |
| TRTL | 100.0% | 0.0% | N/A (untestable) | **0.0%** |
| HGRD | 15.0% | 83.2% | 98.1% | **0.0%** |
| MNT | 43.7% | 55.2% | 98.0% | **52.7%** |
| OGRD | 0.2% | 98.6% | 98.8% | **29.9%** |
| BCTR | 24.0% | 45.5% | 62.0% | **43.5%** |
| SCTR | 12.5% | 56.3% | 66.6% | **56.1%** |

The **OK rate** (validates AND separates, no exclusion) is the only honest end-to-end metric. CGRD at 0.7% and HGRD at 0.0% mean these radicals never simultaneously validate and separate on raw data. TRTL at 0.0% means it never validates at all.

### Adversarial Examples

Three cases where notation failures could be misclassified as perception:

1. **MNT left leg (Me.Le-->Op.To):** Some mount variants (technical mount, S-mount) have only one leg on the torso. The contact may genuinely be absent, not hidden by projection. Classified C, could be D.

2. **CGRD ankle closure:** Some "closed guard" dataset samples may have uncrossed ankles (high guard with feet on hips). The contact may be absent. Classified C, could be A or D.

3. **HGRD FacingOpposed:** Deep half guard and lockdown variants genuinely lack facing-opposed. This is both C (measurement noise) and D (constraint is typical, not invariant).

---

## Task 2: Blind Audit Protocol

**Full protocol:** [blind_audit_protocol.md](blind_audit_protocol.md)

### Design

- 350 images (50 per radical × 7 radicals)
- Stratified sampling: 15 OK, 15 contested-C, 10 B, 10 D per radical
- Annotators see: image + keypoint overlay
- Annotators do NOT see: dataset label, radical name, system verdict
- Questions: binary/ternary physical contact assessments ("Is left leg wrapped around torso?")
- 2 annotators per image, Cohen's κ for agreement

### Critical Test

For required contacts where the system says "C (2D failure)": annotators determine whether the contact genuinely exists in the image. If annotators say "No" → the failure is D (notation error), not C (perception error). This breaks the circularity.

---

## Task 3: Invariant vs Contingent Constraints

**Full classification:** [invariant_vs_contingent.json](invariant_vs_contingent.json)

### Summary

| Classification | Count | Examples |
|---------------|------:|---------|
| Invariant | 17 | OnGround(Op.Ba) for MNT; ankle closure for CGRD |
| Typical | 5 | FacingOpposed for HGRD; second leg for MNT/BCTR |
| Contingent | 3 | NotOnGround(Op.Ba) for BCTR; forbidden legs for SCTR |
| **Total** | **25** | |

### Constraints That Should Change

| Constraint | Radical | Current | Recommended |
|-----------|---------|---------|-------------|
| NotOnGround(Op.Ba) | BCTR | required frame | **remove** (contingent) |
| CON(Me.Le->Op.Le± h=-) forbidden | SCTR | forbidden_con | **remove or bilateral** (contingent) |
| FacingOpposed() | HGRD | required frame | **demote to soft** (typical) |
| CON(Me.Le-->Op.To h=+) | MNT | required_con | **reconsider** (typical — technical mount exists) |
| FacingOpposed() | OGRD | required frame | **demote to soft** (typical — some open guards face away) |

---

## Task 4: Injectivity Analysis

**Full analysis:** [injectivity_analysis.md](injectivity_analysis.md)

### Summary

| Radical | Injective? | Distinct configs collapsed | Severity |
|---------|-----------|---------------------------|----------|
| CGRD | Approximately | 2-3 variants | Low |
| MNT | No | 3-4 variants | Low |
| TRTL | No | 2-3 variants | Moderate |
| BCTR | No | 3-4 variants | Moderate |
| HGRD | No | 5+ systems | **High** |
| SCTR | No | 5+ systems | **High** |
| OGRD | No | 20+ types | **Critical** |

No radical is perfectly injective, but CGRD and MNT are at appropriate granularity. HGRD and SCTR collapse structurally distinct positions (Z-guard vs deep half; kesa vs north-south). OGRD collapses all open guard types.

### Transition States

The notation describes stable attractor states only. Transitional states (knee-cut pass, partial mount, partial back take) fall between radicals and are not representable. This is an acknowledged limitation, consistent with how all BJJ taxonomies work.

---

## Task 5: OGRD Ontology

**Full analysis:** [ogrd_ontology_analysis.md](ogrd_ontology_analysis.md)

### Verdict: OGRD is Not a Radical

OGRD has:
- No required contacts
- Only frame constraints (FacingOpposed + OnGround)
- 98% overlap with HGRD and CGRD
- No discriminative power

OGRD is the residual: "bottom player on the ground, facing opponent, with no specific entanglement." It defines what the position IS NOT (not closed guard, not half guard) rather than what it IS.

### Recommendation: Option C — Superclass Only

Reclassify OGRD as a frame superclass. The vocabulary becomes "6 fundamental radicals + 1 superclass with N subtypes." Subtypes (DLR, SLX, etc.) inherit the OGRD frame constraints to become discriminative.

---

## Task 6: Temporal / Transitional States

### Current State: Stable Attractors Only

The notation describes positions where a practitioner could rest — mount, side control, guard. It does NOT describe:
- Guard passing trajectories
- Scrambles
- Partial positions (one hook in, between mount and half guard)
- Positional transitions in progress

### Can the Algebra Represent Transitional States?

**At the constraint level:** Yes. A partial mount has some MNT constraints satisfied and some not. The constraint vector is meaningful even when no radical fully matches.

**At the radical level:** No. A partial mount is neither MNT nor HGRD. The radical function returns "no match" or returns the closest match, which may be misleading.

**At the graph level:** Transitions are modeled as edges between radicals (ops/graph.py: TRANSITIONS). The graph structure captures THAT transitions happen, but not the geometry of the transition itself.

### Verdict

The notation currently describes (A) stable attractor states only. This is appropriate for a positional taxonomy. Extending to (B) the full state space would require a continuous representation (e.g., constraint satisfaction vectors) rather than discrete radicals. This is a possible future extension, not a current flaw.

---

## Task 7: Adversarial Review

**Full review:** [adversarial_review.md](adversarial_review.md)

### Claims That Survive

1. **CON as the single relational primitive** — not challenged by any validation data
2. **MNT separates from other positions** — 94.5% false-radical rejection, honest measurement
3. **The notation describes stable attractors** — explicitly limited, not a weakness
4. **SCTR and BCTR have genuine algebra issues** — falsifiable, measured, actionable
5. **The structural distance metric** — not tested in this evaluation, remains theoretical

### Claims That Are Invalidated

1. **"98-100% clean validation"** — circular for required contacts; tautological
2. **"7 fundamental radicals"** — OGRD is not a radical; SCTR/HGRD are too coarse
3. **"TRTL notation is correct"** — untestable from current data; an assumption
4. **"Failures are mostly perception"** — C classification for required contacts is unfalsifiable

### Claims That Need Human Verification

1. **Required contacts are necessary for each position** — needs blind audit
2. **TRTL torso contact exists in images** — needs visual inspection
3. **CGRD ankle closure exists in "closed_guard" images** — needs visual inspection
4. **FacingOpposed is present in half guard images** — needs visual inspection

---

## Honest Summary

### What the formalism gets right

1. **The CON primitive is sound.** A single relational tuple for body contacts is a clean design. Nothing in the validation data contradicts this choice.

2. **MNT and SCTR discriminate well** (on raw data, with no exclusion). MNT has 52.7% OK rate — not perfect, but meaningful. SCTR has 56.1%. These positions have enough constraints to separate from others.

3. **Frame constraints work when they're testable.** OnGround / NotOnGround satisfy at 91-100% on raw data. These are reliable, testable, and discriminative.

4. **The forbidden-contact mechanism works.** Forbidden contacts for SCTR are genuinely too strict (29.2% D), and this was correctly identified. The mechanism allows testing and falsification.

### What the formalism gets wrong

1. **Required contacts are untested.** The evaluation pipeline cannot distinguish "contact not detectable" from "contact not present." All required-contact claims are assumptions.

2. **OGRD is not a position.** Including it as a fundamental radical inflates the system and creates misleading overlap statistics.

3. **Several constraints are contingent, not invariant.** BCTR elevation, SCTR forbidden legs, and HGRD facing-opposed are not structurally necessary for their positions.

4. **The notation is too coarse for SCTR and HGRD.** These radicals collapse structurally distinct positions.

### What must happen next

1. **Blind audit** — the single most important next step. Without it, no claim about required contacts is defensible.

2. **Revise SCTR and BCTR** — remove contingent constraints. These are the only proven algebra errors.

3. **Reclassify OGRD** — superclass, not radical.

4. **Present raw rates** — stop using "clean" rates. Report raw satisfaction rates per constraint as measurements of the pipeline, not validation of the notation.

5. **Separate theoretical from empirical claims** — the CON primitive, structural distance, and radical decomposition are theoretical contributions. The ViCoS evaluation is a feasibility study with known limitations, not proof of correctness.
