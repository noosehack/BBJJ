# OGRD Ontology Analysis

## Question

Is OGRD actually a radical? Or is it a superclass, a residual category, or merely "the absence of closure"?

## Current Definition

```
OGRD = Radical("OGRD",
    frame_constraints=(
        FacingOpposed(),
        OnGround(Me.Ba),
    ),
)
```

No required contacts. No forbidden contacts. Only two frame constraints.

## Test 1: Is OGRD Closed Under the Algebra?

**Closure property:** If a state S satisfies OGRD, and a small perturbation S' is applied (an athlete moves slightly), does S' still satisfy OGRD?

**Analysis:** OGRD requires FacingOpposed + OnGround(Me.Ba). Small perturbations:
- Bottom player turns slightly → may lose FacingOpposed → exits OGRD
- Bottom player sits up → still OnGround → stays OGRD
- Top player steps around → may lose FacingOpposed → exits OGRD
- Any leg contact established → still satisfies OGRD (no contacts to violate)

OGRD is NOT closed under perturbation. The FacingOpposed constraint is fragile — any rotation of either fighter can break it. However, this is true of all radicals that include facing constraints.

OGRD is closed under contact perturbation: because it has no contact constraints, adding or removing any contact does not affect OGRD satisfaction. This is the problem — OGRD is insensitive to the primary relational structure of the notation.

**Verdict:** OGRD is topologically open — it defines a region of frame space but not contact space. It is closed under contact perturbation but not under frame perturbation.

## Test 2: Can OGRD Be Uniquely Defined Without Subtypes?

**What would uniqueness mean?** OGRD should specify a configuration that no other radical specifies.

**Overlap analysis (from validation data):**

| True class | OGRD satisfies? |
|-----------|----------------|
| OGRD | 98.6% |
| HGRD | 98.0% |
| CGRD | 97.8% |
| MNT | ~0% (FacingOpposed fails because OnGround(Me.Ba) fails — MNT has OnGround(Op.Ba)) |
| SCTR | ~0.5% |

OGRD satisfies on 98% of HGRD and CGRD samples because those are both ground-bottom-player positions. OGRD does NOT uniquely identify open guard — it identifies "any bottom player on the ground facing the opponent."

The subtypes (DLR, SLX, RDLR, LSSO, OMOP) provide actual positional discrimination through their contact constraints. Without them, OGRD is indistinguishable from the union of HGRD and CGRD (minus the specific constraints that differentiate those).

**Verdict:** OGRD cannot be uniquely defined without subtypes. It is a frame envelope that contains HGRD, CGRD, and the subtypes. It is not a position — it is a region.

## Test 3: Does OGRD Admit a Finite Invariant Structure?

**Question:** Can OGRD be decomposed into a finite set of invariant sub-positions?

**The problem:** Open guard in BJJ is an open-ended creative space. New guard types are invented regularly (worm guard, K-guard, matrix guard, etc.). Each is defined by a specific leg/grip configuration. The number of distinct guard types is not finite in practice.

However, the BLISP notation proposes that each guard type is distinguished by a specific CON pattern on the OGRD frame. If the set of possible CON patterns on the OGRD frame is finite (bounded by the finite set of body parts and contact geometries), then the decomposition is finite in principle.

**Body part combinatorics:** With 4 limb types (Le, Ar, Fo, To), 2 roles (Me, Op), 3 signs (+, -, midline), 3 depths, and 2 helicities, the theoretical CON space is finite but large (~4 × 3 × 4 × 3 × 3 × 2 = 864 distinct CONs per role pair). Practical guard types use ~1-3 primary CONs each.

**Verdict:** OGRD admits a finite decomposition in principle (bounded by CON combinatorics), but the decomposition is not compact — the number of meaningful subtypes (guard systems) is large (20+) and grows as practitioners invent new configurations.

## Test 4: Is OGRD "Absence of Closure"?

**Hypothesis:** OGRD = {states with OnGround(Me.Ba) ∧ FacingOpposed} \ {CGRD ∪ HGRD}.

That is: OGRD is the residual of the ground-bottom-facing-opponent state space after removing closed guard and half guard.

**Evidence for:**
- OGRD has no contacts → it specifies no positive structure
- OGRD is defined by the same frames as HGRD and CGRD (FacingOpposed, OnGround(Me.Ba)) minus their contact constraints
- Every OGRD sample that also satisfies HGRD or CGRD contacts is "really" HGRD or CGRD; OGRD picks up the rest

**Evidence against:**
- The OGRD subtypes (DLR, SLX, etc.) DO have positive contact structure
- Practitioners treat "open guard" as a positive category with specific techniques, not just "not closed guard"
- The frame constraints (FacingOpposed, OnGround) are positive assertions, not negations

**Verdict:** OGRD is structurally the absence of specific entanglement patterns (closed guard closure, half guard leg trap). It defines what the bottom player is NOT doing rather than what they ARE doing. The subtypes add positive structure, but the OGRD radical itself is residual.

## Recommendation

### Option A: Keep OGRD as a Radical

**Pros:** Simple hierarchy. OGRD is the generic ground-bottom position. Subtypes refine it.
**Cons:** OGRD is not a position — it is the complement of CGRD, HGRD, and standing. It overlaps with 98% of HGRD and CGRD samples. It has no discriminative power.
**Assessment:** Intellectually dishonest. OGRD-as-radical claims to be a positional primitive on the same level as MNT or SCTR, but it lacks the structural specificity of those radicals.

### Option B: Redefine OGRD

Add a contact constraint that distinguishes open guard from other ground-bottom positions.

**Candidate constraint:** Require at least one leg-to-opponent contact (any leg on any part of opponent). This distinguishes active open guard (engaging with legs) from passively being on the bottom.

**Problem:** This would exclude seated guard, sit-up guard, and other positions where the guard player has no leg contact. These are still "open guard" in the BJJ sense.

**Assessment:** Any contact constraint would exclude legitimate open guard variants. The category is too diverse for a single contact specification.

### Option C: Treat OGRD as Superclass Only

OGRD is not a radical but a frame envelope. It is the PARENT of the subtypes (DLR, SLX, RDLR, LSSO, OMOP) and of any future subtype.

In the algebra:
- OGRD defines the frame context: FacingOpposed ∧ OnGround(Me.Ba)
- Subtypes inherit this frame and add contact constraints
- OGRD is not used as a discriminative radical in evaluation
- When no subtype matches, the state is "unspecified open guard" — acknowledged as outside the current vocabulary

**Pros:** Honest about what OGRD is. Does not pretend it is a specific position. Allows subtypes to discriminate. Allows the vocabulary to grow.
**Cons:** The evaluation can no longer claim 7 "fundamental radicals." OGRD drops out of the discriminative set. The algebra has 6 fundamental radicals + 1 superclass.

**Assessment:** This is the correct ontological treatment. OGRD is a genus, not a species.

---

## Formal Recommendation

**Option C: Treat OGRD as superclass only.**

Specific changes:

1. Remove OGRD from `EVALUABLE_BLISP` and from the discriminative radical set
2. Add OGRD's frame constraints to each subtype (DLR, SLX, RDLR, LSSO, OMOP)
3. When evaluating OGRD-tagged samples, test against subtypes only
4. Unmatched OGRD samples are "unspecified open guard" — not a validation failure

This changes the claim from "7 fundamental radicals" to "6 fundamental radicals + 1 frame superclass with 5 specified subtypes."

## Impact on Validation Results

If OGRD is reclassified as a superclass:
- OGRD's 98.8% clean validation rate is removed (not applicable to a superclass)
- HGRD's 81.1% F rate drops substantially (OGRD overlap is no longer counted as a failure)
- CGRD's 14.3% F rate drops
- The false-rejection rates for CGRD (1.9%) and HGRD (1.6%) improve dramatically because OGRD passing is no longer a "false radical matching"
- The narrative changes from "7 radicals, 4 validate at 98%+" to "6 radicals, with HGRD and MNT validating well and SCTR/BCTR needing work"
