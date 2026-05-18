# Adversarial Review: A Finite Relational Representation of Fundamental BJJ Positions

## Role

This document presents a hostile reviewer critique of the radical formalism, followed by author responses. The purpose is to determine which claims survive scrutiny and which must be weakened or abandoned.

---

## CRITICISM 1: Circular Validation

**Reviewer:**

The central empirical claim — "4 of 7 radicals validate at 98–100% on clean data" — is circular. The pipeline classifies every required-contact failure as a "perception failure" (category B or C), then excludes these from the "clean" validation set, then checks whether required contacts are met. Of course they are: the failures were already removed.

Specifically, in `classify_constraint_failure()`, the code path for `required_con` always returns B (keypoint below threshold) or C (everything else). There is no code path from a required-contact failure to D (algebra too strict). This makes the "clean validation rate" for required contacts tautologically 100%.

The authors cannot claim the notation is empirically validated when the evaluation is structurally incapable of falsifying it.

**Author Response:**

This criticism is correct. The required-contact validation is circular as implemented. The classifier assumes every required contact in the notation is correct, making the result unfalsifiable.

We acknowledge:
1. The "98-100% clean validation" figure for CGRD, HGRD, MNT, and OGRD is a consequence of classifier design, not an empirical finding about notation correctness.
2. No required contact has been empirically tested for necessity — only for detectability.
3. A blind audit (where annotators confirm contact existence without knowing the expected radical) is required before any validation claim can be made.

The defensible claims are:
- The raw (unexcluded) satisfaction rates per constraint ARE empirical measurements (e.g., "right-leg-on-torso contact is detectable in 90% of MNT samples")
- The forbidden-contact and ground-frame validations are NOT circular (they have code paths to D)
- The SCTR (29.2% D) and BCTR (28.9% D) findings are genuine because they come from forbidden contacts and frames that CAN be falsified

We weaken the claim to: "The notation's frame constraints and forbidden contacts are empirically testable and partially validated. Required contacts have not been independently validated."

---

## CRITICISM 2: Exclusion Bias

**Reviewer:**

The paper excludes 37.1% of samples as "perception failures" before computing validation rates. For CGRD, the exclusion rate is 63.6%. For TRTL, it is 100%. This is not methodological rigor — it is survivorship bias.

The exclusion categories are not independently validated:
- Category B (keypoint failure) has an arbitrary threshold (confidence < 0.3)
- Category C (2D observability) is applied to ALL required-contact failures with adequate keypoints — effectively reclassifying every notation failure as a sensor failure

The post-exclusion "clean" rates are meaningless if the exclusion criteria are biased toward protecting the notation.

**Author Response:**

We accept the force of this criticism for category C as applied to required contacts. The C-vs-D distinction for required contacts is currently an assumption, not a measurement.

Category B, however, is defensible. Keypoint confidence is a numeric output of the pose estimator, not a semantic judgment. The threshold (0.3) is the same one used by the axis reconstruction pipeline, applied uniformly. A sensitivity analysis varying the threshold (0.2, 0.3, 0.4) would quantify the impact. We have not done this analysis.

Category C for facing direction and ankle closure is partially defensible on geometric grounds: the shoulder-normal dot product IS a noisy estimator of facing direction under projection, and ankle proximity IS a lossy proxy for 3D leg closure. But we cannot distinguish "2D projection made the contact undetectable" from "the contact does not exist" without independent verification.

The honest framing: "Raw validation rates range from 0% (TRTL) to 98.6% (OGRD). The gap between raw and clean rates reflects either perception limitations or notation errors; we cannot determine the proportion without human annotation."

---

## CRITICISM 3: Semantic Leakage in Category Assignment

**Reviewer:**

The failure categories use domain knowledge to protect the notation. The TRTL torso-to-torso contact is classified as "2D unobservable" — but how do the authors know it is unobservable? Because the constraint was designed to represent torso contact, and the inference pipeline cannot detect it. The category assignment ASSUMES the contact is present and blames the sensor.

But what if TRTL-tagged samples don't actually have torso-on-torso contact? What if the dataset includes images where the top player is next to, not on, the turtled player? The 0% detection rate is equally consistent with "the contact doesn't exist in these images" and "the contact exists but is undetectable."

The authors' domain knowledge about what TRTL "should" look like is leaking into what is supposed to be an empirical evaluation.

**Author Response:**

This is correct. The TRTL assessment is based on the assumption that turtle = torso-on-torso contact. We have not verified this from the images.

The defensible claim: "The torso-to-torso CON is undetectable by the current inference pipeline (0% detection rate). Whether this reflects a detection failure or a notation error cannot be determined without visual inspection of the images."

The weaker but honest claim: "The point_to_segment_distance function between two torso axes of similar length geometrically cannot produce small values when the segments are parallel — this is a known limitation of the geometry, not an empirical finding about the images."

We acknowledge that the geometry argument explains why the pipeline WOULD fail even if the contact existed, but does not prove the contact exists.

---

## CRITICISM 4: Lack of Injectivity

**Reviewer:**

The radicals are not injective. SCTR collapses standard side control, kesa gatame, reverse kesa, and north-south into a single radical. HGRD collapses standard half guard, deep half, lockdown, Z-guard, and half butterfly. OGRD collapses all open guard types.

These are not minor variations — they are structurally distinct positions with different mechanics, entries, exits, and submission threats. A notation that cannot distinguish kesa gatame from north-south has limited practical value.

The authors claim 7 "fundamental" radicals, but 3 of them (SCTR, HGRD, OGRD) are so coarse that they collapse multiple fundamentally different positions.

**Author Response:**

The injectivity criticism is valid for SCTR, HGRD, and OGRD. We concede:

1. **SCTR** collapses positions that practitioners consider structurally distinct. Kesa gatame, north-south, and standard side control have different contact graphs, different facing directions, and different control dynamics. A single radical is insufficient.

2. **HGRD** collapses half guard variants that differ in contact topology. Z-guard (knee shield frame) is structurally different from deep half (underhook, head near hip).

3. **OGRD** is not a position but a category. This is addressed in the OGRD ontology analysis.

For **MNT**, **CGRD**, **BCTR**, and **TRTL**, the non-injectivity is at a natural granularity. Mount variants (low, high, S-mount) share a structural core that practitioners recognize as "mount." The radical captures the shared invariant structure, not the tactical variation.

The honest claim: "The notation identifies 4 fundamental positions at appropriate granularity (MNT, CGRD, BCTR, TRTL) and 3 broad categories that require further decomposition (SCTR, HGRD, OGRD)." Whether this is "7 fundamental radicals" or "4 radicals + 3 superclasses" is a framing choice.

---

## CRITICISM 5: Perception/Algebra Separation is Not Clean

**Reviewer:**

The paper claims to separate "perception failures" from "algebra failures." But the separation is not clean:

1. Some constraints are simultaneously notation-contingent AND 2D-noisy. FacingOpposed for HGRD fails 38% of the time. Is this because the 2D facing estimate is noisy (C), or because some half guard variants don't have facing-opposed (D)? Both are true. The categories are not mutually exclusive.

2. The forbidden-contact violations in SCTR could be either D (algebra too strict) or B (keypoint swap causing false contact detection). The pipeline defaults to D, but a keypoint swap where the left-right legs are flipped would produce the same signal.

3. The NotOnGround frame for BCTR is classified as D, but it could equally be C (the hip-height heuristic is noisy when both fighters are on the mat).

The six categories (A–F) are presented as a clean taxonomy, but many failures sit at the intersection of multiple categories. The single-label assignment hides this ambiguity.

**Author Response:**

This criticism is valid. We designed single-label categories for clarity, but real failures are often multi-causal. Our response:

1. **FacingOpposed for HGRD** is both contingent (some half guard variants) and noisy (2D projection). The honest assessment from invariant_vs_contingent.json classifies it as "typical" — usually present but not invariant. This means the constraint carries information but is not definitional. It should be demoted from a hard requirement to a soft signal.

2. **SCTR forbidden contacts** could involve keypoint artifacts. However, the pipeline classifies them as D only when keypoints are above threshold. We can add a sensitivity analysis: vary the confidence threshold and observe whether the D rate changes. If it is stable, the D classification is robust; if it drops, keypoint quality was contributing.

3. **BCTR NotOnGround** is genuinely ambiguous between D (opponent IS on the ground in back control) and C (hip-height comparison is noisy). The invariant_vs_contingent analysis classifies this as contingent (D), not noisy (C), based on BJJ positional mechanics: back control DOES occur with the opponent prone.

We acknowledge the taxonomy is cleaner in presentation than in reality. A multi-label assignment with confidence scores would be more honest.

---

## CRITICISM 6: OGRD Ambiguity Undermines the System

**Reviewer:**

OGRD is supposed to be a "fundamental radical" but has no contacts, no required limb relations, and overlaps with 98% of two other radicals. Including OGRD in the set of 7 fundamentals inflates the validation statistics and creates misleading confusion metrics.

Moreover, the OGRD subtypes (DLR, SLX, etc.) have only 1 contact each and no frame constraints, making them fire as false positives on 50-87% of non-OGRD samples. The notation around open guard is simultaneously too coarse (OGRD superclass) and too leaky (subtypes without frame constraints).

**Author Response:**

We concede that OGRD is not a radical in the same sense as MNT or SCTR. The recommendation from the ontology analysis is to reclassify OGRD as a frame superclass rather than a fundamental radical.

This changes the claim from "7 fundamental radicals" to "6 fundamental radicals + 1 frame superclass." The subtypes must inherit OGRD's frame constraints to become discriminative.

We do not defend OGRD-as-radical. The inclusion was a mistake in the ontological design, not an empirical finding.

---

## CRITICISM 7: Static-State Assumption

**Reviewer:**

The notation claims to represent BJJ positions, but positions are continuous, not discrete. A guard pass is a continuous trajectory from guard to side control. A mount escape passes through half guard. The notation cannot represent these transitions — it only describes the endpoints.

If the notation can only describe stable attractor states, it is not a general-purpose representation of BJJ. It is a label system for the endpoints of transitions. The paper should be clear about this limitation rather than implying general applicability.

**Author Response:**

This is correct and we should be explicit about it. The notation describes stable attractor states — positions where a practitioner could rest without immediately losing or gaining position. Transitions between radicals are morphisms in the graph structure (defined in ops/graph.py), not states representable by radicals.

However, we note:
1. This is not a weakness unique to our system. The IBJJF scoring system, every BJJ curriculum, and every instructional system use discrete positional categories. The continuous state space is real, but discretization is universal in the domain.
2. The notation CAN represent the boundary between positions by observing which constraints are and are not satisfied. A partial mount (one leg over) satisfies some MNT constraints and some HGRD constraints. The constraint-level representation is richer than the radical-level label.
3. The transition graph (DEFENSE_LEVEL, TRANSITIONS in ops/graph.py) explicitly models the morphisms between stable states. The notation does not claim to represent the trajectory, but it does represent the graph structure.

The honest claim: "The notation represents a finite set of stable positional attractors and the transitions between them. Intermediate states are represented by partial constraint satisfaction, not by radical labels."

---

## CRITICISM 8: Confirmation Bias in Constraint Design

**Reviewer:**

The constraints were designed by practitioners who know what each position looks like. They selected constraints that match their mental model of each position. Then they tested whether those constraints are present in images of those positions. Of course they are — the constraints were designed to be present.

The real test is whether the constraints are SUFFICIENT to distinguish positions, not whether they are PRESENT. The paper conflates presence (validation) with sufficiency (discrimination).

**Author Response:**

The distinction between presence and sufficiency is important. Our validation rates measure presence. Our rejection rates measure sufficiency. The results are mixed:

**Presence (raw, no exclusion):**
- MNT right leg: 90% present (good)
- MNT left leg: 56% present (weak — but are we measuring the contact or the detector?)
- CGRD ankle closure: 46% present (weak — same question)

**Sufficiency (false-radical rejection, clean):**
- MNT: 94.5% rejection (excellent — MNT's constraints distinguish it from other positions)
- SCTR: 81.3% (good)
- CGRD: 1.9% (terrible — OGRD passes on almost all CGRD samples)
- HGRD: 1.6% (terrible — same issue)

The notation has good presence for some constraints and good sufficiency for some radicals, but NOT uniformly. The claim should be decomposed: "MNT and SCTR have sufficient constraint sets for discrimination. CGRD and HGRD do not, primarily because OGRD (frame-only) passes trivially."

---

## SUMMARY: What Survives

| Claim | Status |
|-------|--------|
| "7 fundamental radicals" | **WEAKENED** to 4–6 radicals + superclasses |
| "98-100% clean validation" | **INVALIDATED** — circular for required contacts |
| "Failures are mostly perception" | **PARTIALLY VALID** — B is defensible, C is not for required contacts |
| "The notation is correct" | **UNTESTED** for required contacts; **CORRECT** that SCTR/BCTR have D issues |
| "OGRD is a fundamental radical" | **REJECTED** — OGRD is a superclass |
| "CON is the single primitive" | **SURVIVES** — not challenged by the validation data |
| "Structural distance metric works" | **NOT TESTED** in this evaluation |
| "MNT separates from other positions" | **SURVIVES** — 94.5% rejection, honest measurement |
| "The notation describes stable attractors" | **SURVIVES** — explicitly limited, not a weakness |

## What the Authors Should Do

1. **Drop the "98-100% clean validation" claim entirely.** Replace with raw rates and acknowledge the C-vs-D ambiguity.
2. **Conduct the blind audit** described in blind_audit_protocol.md to resolve the C-vs-D question for required contacts.
3. **Reclassify OGRD** as a superclass.
4. **Fix SCTR** (remove or weaken forbidden contacts) and **BCTR** (remove NotOnGround).
5. **Present raw rates honestly:** "Right-leg-on-torso is detectable in 90% of mount images. Facing-opposed is detectable in 46%. These are measurements of the pipeline, not validation of the notation."
6. **Acknowledge the injectivity limitations:** SCTR and HGRD need refinement.
7. **Acknowledge the static-state limitation** explicitly.
8. **Separate empirical from theoretical claims:** "The CON primitive and structural distance metric are theoretical contributions. The validation against ViCoS data is a feasibility study with known methodological limitations, not a proof of correctness."
