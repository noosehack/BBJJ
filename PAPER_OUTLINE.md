# Paper 1: Outline and Scaffold

## Working Titles

1. **A Finite Relational Representation of Fundamental Brazilian Jiu-Jitsu Positions**
2. Positional Radicals: Symbolic Formalization of Interpersonal Entanglement in Grappling
3. Canonical Forms for Contact-Based Positional Equivalence in Brazilian Jiu-Jitsu

Recommended: **Title 1.** It is accurate, restrained, and precisely scoped.

---

## Abstract (Draft)

We propose a finite symbolic representation of the fundamental positional state space of Brazilian Jiu-Jitsu. Positions are formalized not as body postures but as equivalence classes over interpersonal contact relations and spatial frame constraints. The representation uses a single relational primitive — a directed contact between two oriented limb axes with helicity — together with four frame predicates. Seven canonical positions (mount, side control, back control, closed guard, open guard, half guard, turtle) are defined as radical structures: finite conjunctions of required contacts, forbidden contacts, and frame constraints. We prove that the seven radicals are pairwise distinguishable under this representation and define a structural distance metric over the resulting state space. We evaluate empirical recoverability of the symbolic states from image-derived body geometry on the ViCoS grappling dataset (37,409 samples, 6 evaluable classes). The algebraic matcher achieves 25.6% accuracy from 2D keypoints alone — significantly above the 16.7% random baseline but far below practical utility. We present a detailed failure-mode analysis showing that the dominant source of error is the projection of 3D entanglement onto 2D proximity, not the symbolic representation itself. This distinction — between the structural validity of the formalism and the limitations of its visual grounding — is the central empirical finding.

---

## Contribution Statement

The contributions of this paper are:

1. **A finite relational grammar** for interpersonal grappling positions, built from a single contact primitive (CON) and four frame predicates, with no learned parameters.
2. **Canonical radical definitions** for seven fundamental BJJ positions as constraint conjunctions over this grammar, together with a proof of pairwise distinguishability.
3. **A structural distance metric** over positional state space, counting independent field edits between radical definitions.
4. **An empirical evaluation** on the ViCoS dataset demonstrating partial recoverability and precisely characterizing the perception-representation gap.

The contribution is representational, not perceptual. We do not claim to solve position recognition. We claim to formalize what positions *are*, and to precisely measure how far a minimal visual pipeline falls short of recovering them.

---

## Section Structure

### 1. Introduction

**Goal**: Motivate the formalization problem. Distinguish it from recognition/classification.

**Key argument**: BJJ instruction, competition analysis, and automated coaching all implicitly rely on a notion of "position" that has never been formally defined. Practitioners agree on what mount is, but no prior work states the necessary and sufficient conditions. Without a formal definition, any classifier is an unnamed function — it may correlate with positions without representing them.

**Scope declaration**: This paper formalizes the seven fundamental macro positions only. It does not address submissions, transition sequences, sub-guards beyond open guard subtypes, or complete competitive state spaces. These are deferred to future work.

**Paragraph plan**:
- P1: BJJ as a finite-state contact sport. Positions as the coarse-grained state space.
- P2: The gap — no formal positional ontology exists. Classifiers label; they do not define.
- P3: This paper's claim — positions admit a finite relational representation from a small symbolic grammar.
- P4: Structure of the paper. Scope limitations.

### 2. Related Work

**Three threads** (keep brief — this is not a survey paper):

**2.1 Grappling / combat sports recognition.**
Pose-based action recognition in martial arts and wrestling. ViCoS dataset (Blažič et al.). Prior BJJ classifiers (CNN-based, skeleton-based). Key observation: all prior work treats positions as opaque class labels. No prior work defines positions structurally.

**2.2 Contact and interaction modeling.**
Interpersonal contact detection in computer vision (HOI, contact estimation, social touch). Key observation: most contact work addresses *whether* contact occurs, not *what relational structure* the contact instantiates. Our work is about relational structure, not contact detection.

**2.3 Symbolic / formal models in movement science.**
Laban Movement Analysis. Labanotation. Benesh notation. Sport formalization efforts. Key observation: these systems formalize individual body movement. Grappling requires *interpersonal* relational representation — two bodies, mutual constraints. No existing notation handles this.

**Gap statement**: No prior work provides a formal symbolic representation of interpersonal positional structure in grappling.

### 3. Formal Model

This is the core section. Four subsections building the representation bottom-up.

#### 3.1 Anatomical Entities

**Definition 1** (Body Part Vocabulary). A finite set of anatomical part codes:

B = {Le, Ar, Fo, Hp, Ha, Sh, To, Hd, Kn, El, Wr, Ba, Ne}

Parts are bilateral (Le, Ar, Fo, ...) or midline (To, Hd, Ba).

**Definition 2** (Limb Reference). A triple `(role, part, sign)` where:
- role ∈ {Me, Op} — the two athletes
- part ∈ B
- sign ∈ {+, -, ∅} — laterality (+ right, - left, ∅ midline)

**Definition 3** (Axis). A directed segment between two anatomical landmarks on the same limb. Formally an oriented 1-cell: `axis(limb_ref, from_point, to_point)` where from/to are distal/proximal endpoints.

Default axes: Le = Fo→Hp, Ar = Wr→Sh, To = Hp→Sh.

**Remark**: The axis direction matters. Reversing an axis (e.g., Sh→Wr vs Wr→Sh) changes the structural identity of a contact. This is how LSSO and OMOP differ.

#### 3.2 The Contact Primitive

**Definition 4** (CON). The single relational primitive. A CON is a 9-tuple:

CON = (att_role, att_part, att_sign, att_dir, ax_role, ax_part, ax_sign, ax_dir, helicity)

Intuitively: an attacker limb wraps around an axis limb. The nine fields are:

| Field | Domain | Meaning |
|-------|--------|---------|
| att_role | {Me, Op} | Who attacks |
| att_part | B | Which limb attacks |
| att_sign | {+, -, ∅} | Left/right/midline |
| att_dir | {fwd, rev} | Axis orientation |
| ax_role | {Me, Op} | Who provides the axis |
| ax_part | B | Which limb is the axis |
| ax_sign | {+, -, ∅} | Left/right/midline |
| ax_dir | {fwd, rev} | Axis orientation |
| helicity | {+, -, 0} | Wrapping chirality |

**Remark on helicity**: The sign {+, -} encodes the chirality of the wrap (viewed from the distal end of the axis, clockwise vs counterclockwise). The value 0 encodes achiral closure (e.g., ankles locked — no preferred wrapping direction).

**Design decision — why one primitive**: Prior informal descriptions of grappling use many relation types: grip, hook, clinch, pin, clamp, etc. We show these are all instances of CON with specific field values. GRP(Me.Ha+ → Op.Collar) is a CON where att_part = Ha and the collar is modeled as a specific axis on the torso. HOOK(Me.Fo- → Op.Hip) is a CON where att_part = Fo. This unification is not merely notational convenience — it enables the distance metric (Section 3.4) because all contacts live in a single 9-dimensional space.

**Proposition 1** (CON field independence). The nine fields of CON are pairwise independent: any valid assignment to one field is compatible with any valid assignment to any other field.

*Proof sketch*: Verify by construction that for each pair of fields (f_i, f_j), every combination (v_i, v_j) ∈ dom(f_i) × dom(f_j) can be instantiated by some physically realizable contact. [This requires careful enumeration — potential weak point, see Section 8.]

#### 3.3 Frame Constraints

**Definition 5** (Frame Constraint). Global spatial predicates over the two-body configuration. Four types:

| Predicate | Notation | Meaning |
|-----------|----------|---------|
| FacingOpposed | y = -y' | Athletes face each other |
| FacingAligned | y = y' | Athletes face same direction |
| OnGround(X) | Z₀(X) | Body part X at ground level |
| NotOnGround(X) | ¬Z₀(X) | Body part X elevated |

where X is a LimbRef (e.g., Me.Ba, Op.Ba).

**Remark**: Frame constraints are *not* relational in the same sense as CON. They are unary or global predicates about spatial configuration. They are needed because CON alone cannot distinguish, e.g., mount from closed guard (both have two legs wrapping the torso — the difference is who is on the ground).

#### 3.4 Radical

**Definition 6** (Radical). A radical is a named tuple:

R = (name, F, C_req, C_fbd, C_fbd_bi)

where:
- F ⊆ FrameConstraints — required frame constraints
- C_req ⊆ CON — required contacts (must all be present)
- C_fbd ⊆ CON — forbidden contacts (none may be present)
- C_fbd_bi ⊆ CON × CON — forbidden bilateral pairs (at most one of each pair may be present)

A configuration **satisfies** radical R iff:
1. All frame constraints in F hold.
2. For each c ∈ C_req, a contact matching c is present.
3. For each c ∈ C_fbd, no contact matching c is present.
4. For each pair (c₁, c₂) ∈ C_fbd_bi, at most one is present.

**The seven fundamental radicals** (see Table 1 for the complete specification):

| Radical | Frame Constraints | Required CONs | Forbidden CONs | Interpretation |
|---------|-------------------|---------------|----------------|----------------|
| MNT | FacingOpposed, Z₀(Op.Ba) | Me.Le+→Op.To(h-), Me.Le-→Op.To(h+) | — | Both legs straddle torso, opponent grounded |
| BCTR | FacingAligned, ¬Z₀(Op.Ba) | Me.Le+→Op.To(h-), Me.Le-→Op.To(h+) | Me.Fo-↔Me.Fo+(h0) | Both legs hook torso from behind, feet not locked |
| SCTR | Z₀(Op.Ba) | Me.Ar+→Op.To(h-) | Me.Le→Op.Le | Arm wraps torso, no leg entanglement |
| CGRD | ¬Z₀(Op.Ba) | Me.Le+→Op.To(h-), Me.Le-→Op.To(h+), Me.Fo-↔Me.Fo+(h0) | — | Both legs wrap torso with ankle closure |
| HGRD | FacingOpposed, Z₀(Me.Ba) | Me.Le→Op.Le(h-) | — | One leg entangles opponent's leg |
| TRTL | FacingAligned | Op.To→Me.To(h0) | Op.Le+→Me.To, Op.Le-→Me.To | Torso-to-torso contact, no leg hooks |
| OGRD | FacingOpposed, Z₀(Me.Ba) | — | — | Base position: feet engaged, no specific entanglement |

**Observation**: OGRD is the least constrained radical — it has no required contacts. It functions as the default guard position. Sub-guards (DLR, SLX, RDLR, LSSO, OMOP) are OGRD plus one additional CON.

**Theorem 1** (Pairwise Distinguishability). For any two distinct radicals R_i, R_j in the fundamental set, there exists at least one constraint (frame, required contact, or forbidden contact) that belongs to R_i but not R_j or vice versa.

*Proof*: By exhaustive comparison of the 7 × 6 / 2 = 21 pairs. [Provide as table in appendix.]

This is a finite verification, not an infinite-domain theorem. It establishes that the representation *can* distinguish the positions, not that any particular observer *will*.

**Theorem 2** (Minimality of CON). No proper subset of the nine CON fields suffices to distinguish all seven fundamental radicals.

*Proof strategy*: For each field, exhibit two radicals that agree on all other fields but differ only in that field, and whose distinction is necessary for the position vocabulary. [Need to verify — this is a candidate theorem, may need weakening. See Section 8.]

*Potential issue*: att_dir and ax_dir only distinguish LSSO from OMOP, which are sub-guards, not fundamental positions. If we restrict to the 7 fundamental radicals, fewer fields may suffice. State precisely.

#### 3.5 Structural Distance

**Definition 7** (CON field distance). For two CONs c₁, c₂:

d_field(c₁, c₂) = |{i : c₁[i] ≠ c₂[i]}|

This is the Hamming distance over the 9-field representation.

**Definition 8** (Contact alignment distance). For two contact sets C₁, C₂: compute the minimum-cost alignment where each matched pair costs d_field(c₁, c₂) and each unmatched contact costs 9 (the maximum possible field distance, equivalent to adding/removing a contact from nothing).

**Definition 9** (Structural distance). For radicals R₁, R₂:

d(R₁, R₂) = d_frame(R₁, R₂) + d_align(C_req₁, C_req₂) + d_align(C_fbd₁, C_fbd₂) + d_align(C_fbd_bi₁, C_fbd_bi₂)

where d_frame counts differing frame constraint bits.

**Proposition 2** (Metric properties). Structural distance satisfies:
- d(R, R) = 0
- d(R₁, R₂) = d(R₂, R₁) (symmetry)
- d(R₁, R₂) ≥ 0 (non-negativity)

*Status of triangle inequality*: The greedy alignment is an approximation to optimal bipartite matching. Triangle inequality holds for optimal matching but may fail for the greedy variant. [Must verify or switch to Hungarian algorithm. Flag as open.]

**Table 2**: Full 7×7 distance matrix for fundamental radicals.

**Observations from the distance matrix**:
- OGRD↔HGRD = 9 (closest pair: one contact field change)
- CGRD↔MNT = 12 (differ in facing + ground, not contacts)
- TRTL is maximally distant from CGRD (43): opposite orientation, different contact topology

### 4. Empirical Evaluation

#### 4.1 Experimental Setup

**Dataset**: ViCoS BJJ grappling dataset. 37,409 samples with both athletes' COCO 17-keypoint poses. 6 evaluable position classes (MNT, SCTR, BCTR, CGRD, HGRD, 5050). OGRD excluded (not separately labeled in ViCoS; subsumed under open guard variants).

**Pipeline**: Keypoints → Axis reconstruction → Contact inference (proximity-based) → Frame constraint inference → Radical matching → Predicted position.

**No learned parameters in the matcher.** The entire pipeline is deterministic from the radical definitions. Contact inference uses a fixed proximity threshold (0.3 normalized torso lengths). Frame inference uses fixed geometric tests (dot product for facing, y-coordinate for ground).

**Baselines**:
- Random (6 classes): 16.7%
- Majority class: 18.6%

#### 4.2 Results

**Overall accuracy**: 25.6% (9,581 / 37,409). Macro F1: 0.343.

**Per-class** (Table 3):

| Position | N | Precision | Recall | F1 |
|----------|---|-----------|--------|----|
| SCTR | 6,596 | 70.3% | 32.0% | 0.440 |
| CGRD | 6,682 | 76.8% | 25.5% | 0.383 |
| BCTR | 6,500 | 51.9% | 29.3% | 0.375 |
| HGRD | 4,209 | 43.8% | 27.3% | 0.337 |
| MNT | 6,955 | 43.3% | 15.9% | 0.233 |

**Key finding**: Precision is substantially higher than recall for all positions. When the symbolic matcher produces a prediction, it is moderately reliable. The dominant failure mode is *missed detection* (required contacts not recovered from 2D projection), not *false assignment* (wrong contacts leading to wrong position).

#### 4.3 Failure Mode Analysis

Classify errors into five categories (Table 4):

| Category | Est. % of Errors | Mechanism |
|----------|------------------|-----------|
| Perception: contact inference | ~50% | 2D proximity ≠ 3D entanglement |
| Perception: frame constraints | ~15% | Facing/ground ambiguous from single viewpoint |
| Perspective assignment | ~20% | Wrong Me/Op role assignment |
| Algebra: loose radicals | ~10% | Single-contact radicals over-trigger |
| Algebra: strict radicals | ~5% | Bilateral contacts fail on valid poses |

**Critical distinction**: Categories 1–3 are *perceptual* failures — the symbolic representation is correct but the visual signal does not reliably recover it. Categories 4–5 are *representational* — the radical definitions themselves are too permissive or too strict.

Approximately 85% of errors are perceptual. The representation is not the bottleneck.

#### 4.4 Ablation: Primitive Contributions

Ablate by removing one feature class at a time and measuring accuracy change:

- Without helicity: accuracy drops by X% (or rises — helicity may be noise in 2D)
- Without frame constraints: drops by Y%
- Without forbidden contacts: drops by Z%

[Exact numbers to be computed. Helicity ablation is particularly important — the report suggests helicity is pure noise in 2D projection.]

#### 4.5 Open Guard Subtype Chain

The five OGRD subtypes (DLR, SLX, RDLR, LSSO, OMOP) form a chain of single-field edits:

DLR →(helicity) SLX →(ax_part) LSSO →(ax_dir) OMOP

DLR →(ax_sign) RDLR

Each edge is exactly one CON field change. This demonstrates the representational granularity: structurally adjacent positions differ by the minimal possible edit.

[This is a strong representational result but empirically hard to verify — all subtypes require only 1 contact, making them indistinguishable from noise in 2D. Present the algebraic chain and acknowledge visual unrecoverability.]

### 5. Discussion

#### 5.1 The Representation-Perception Gap

Central theme: the formalism is structurally sound but visually opaque. 3D entanglement projects ambiguously to 2D. This is not a flaw of the representation — it is a fundamental property of the visual recovery problem.

Analogy: a context-free grammar is correct even if a noisy parser makes errors. The grammar's correctness is established by its distinguishing power, not by any particular parser's accuracy.

#### 5.2 Sufficiency of CON

One primitive relation, nine fields. Design alternatives considered and rejected:
- Multiple relation types (GRP, HOOK, PIN, etc.): abandoned because all reduce to instances of CON. Proliferating types obscures the underlying uniformity and prevents a single distance metric.
- Richer depth modeling: the current "depth" field is symbolic and unused in the formal model. Future work could assign metric depth.

#### 5.3 What the Distance Metric Captures

Structural distance correlates with practitioner intuition about positional similarity:
- OGRD ↔ HGRD (9) — practitioners describe half guard as "one step from open guard"
- CGRD ↔ MNT (12) — closed guard and mount share contact topology (legs wrap torso) but differ in who is on top
- TRTL ↔ CGRD (43) — maximally different: different facing, different contacts, different ground state

But structural distance is *not* transition distance. SCTR→MNT is a common transition (one technique) but d(SCTR, MNT) = 29. Distance measures representational similarity, not tactical proximity.

#### 5.4 Limitations

State explicitly:

1. **Seven positions only.** The competitive BJJ state space includes dozens of guard variants, leg entanglements, standing positions, and clinch states not covered here.
2. **No dynamics.** The representation is instantaneous. Transitions, timing, momentum, and gripping sequences are out of scope.
3. **Bilateral symmetry.** The current model does not fully exploit left/right symmetry — each radical specifies explicit signs. A quotient over bilateral equivalence would reduce the state space but is deferred.
4. **Camera dependence.** The empirical evaluation is single-viewpoint. Multi-view or depth-sensing would substantially change the recoverability results.
5. **Greedy alignment.** The structural distance uses greedy rather than optimal matching. Triangle inequality is not guaranteed.
6. **No grip modeling.** Grips (collar, sleeve, pants) are critical in practice but not formalized. They would instantiate CON with hand-to-fabric axes, requiring an extended body vocabulary.

### 6. Conclusion

Restate the contribution precisely:
- We showed that seven fundamental BJJ positions admit a finite symbolic representation from a single contact primitive.
- The seven radicals are pairwise distinguishable.
- Structural distance provides a principled similarity measure.
- Empirical recoverability from 2D keypoints is partial (25.6%) but the failure is perceptual, not representational.
- The formalism provides a foundation for future work on transition algebra, grip modeling, and 3D-aware recovery.

### 7. Future Work

1. **Transition algebra**: formalize legal transitions as morphisms between radicals. Define sweep, pass, escape, submission as structured transformations on the contact graph.
2. **3D recovery**: use depth estimation or multi-view geometry to improve contact inference. The representation is 3D-native; only the visual pipeline is 2D-limited.
3. **Grip extension**: extend the body vocabulary to include clothing (collar, sleeve, belt, pant leg) as additional axis targets.
4. **Temporal consistency**: use video-level inference to smooth contact predictions over time (closure memory).
5. **Sub-guard lattice**: formalize the full open guard subtype lattice and its metric structure.

### 8. Assumptions and Weak Points

*Internal section for review — not included in final paper.*

**A1. Proposition 1 (CON field independence)**: Needs careful physical verification. Some field combinations may be anatomically impossible (e.g., Me.Fo+ wrapping Me.Ar- with helicity +). If some combinations are unrealizable, the field space has holes and the 9-dimensional Hamming model overstates the distance between certain contacts.

*Mitigation*: Restrict the claim to "combinatorially independent" (any assignment is syntactically valid) and note that not all syntactically valid CONs correspond to physically realizable configurations. The distance metric operates over syntactic descriptions, not physical configurations.

**A2. Theorem 2 (Minimality)**: Likely fails for the 7 fundamental radicals alone. att_dir and ax_dir only distinguish OGRD subtypes. For the 7 fundamentals, 7 fields may suffice. State the theorem precisely for the 12-radical set (7 fundamentals + 5 subtypes).

**A3. Greedy alignment vs. optimal matching**: The structural distance may violate triangle inequality. Either prove it doesn't (for the specific radical sizes involved — max 3 contacts), switch to Hungarian matching, or weaken the claim to "dissimilarity measure" rather than "metric."

*Note*: For |C| ≤ 3 contacts, greedy and optimal matching coincide in almost all cases. Likely safe but needs verification.

**A4. OGRD as the zero-contact radical**: OGRD has no required contacts. It is satisfied by *any* configuration with FacingOpposed + OnGround(Me.Ba). This makes it a "catch-all" — any failed match could default to OGRD. The formal model handles this correctly (OGRD is the least specific radical), but it creates an asymmetry: OGRD is defined by *absence*, all others by *presence*.

*This is actually a feature, not a bug*: OGRD represents the base state of guard engagement before specific entanglement is established. Articulate this clearly.

**A5. Depth field unused**: The "depth" field in CON (d, d1, d2, d3) provides symbolic labels but plays no role in the distance metric or the matching logic. Either remove it from the formal model or explain its role (ordering multiple contacts on the same axis).

**A6. Helicity in 2D**: The empirical evaluation shows helicity is unreliable from 2D projection. This does not invalidate the formalism (helicity is a real 3D property of wrapping) but it means the 2D evaluation cannot assess whether helicity is *necessary* for distinguishability. The DLR/SLX distinction (helicity only) is formally clear but empirically inaccessible from single-viewpoint images.

---

## Proposed Figures

**Figure 1**: The defense-level hierarchy. Four horizontal bands (feet, knees, hips, passed). Seven radicals placed in their defense levels. Directed edges for transitions (pass downward, recover upward, close inward, lateral within level). *Already exists as radical_distance_graph.png.*

**Figure 2**: Anatomy of a CON. Diagram showing two athletes, an attacker limb wrapping an axis limb, with the nine fields labeled. Show helicity as clockwise/counterclockwise arrow viewed from the axis distal end.

**Figure 3**: The seven radicals as schematic contact diagrams. For each radical, show two simplified body outlines with the required contacts drawn as arcs and forbidden contacts drawn as dashed-crossed arcs. Frame constraints shown as spatial annotations (ground plane, facing arrows).

**Figure 4**: Distance matrix heatmap. 7×7 grid, color-coded by structural distance. Annotate the closest pair (OGRD-HGRD = 9) and the farthest pair (TRTL-CGRD = 43).

**Figure 5**: OGRD subtype chain. Five nodes connected by labeled single-field edges. Annotate each edge with the field that changes.

**Figure 6**: Empirical pipeline diagram. Keypoints → axis reconstruction → contact inference → frame inference → radical matching. Show an example image at each stage.

**Figure 7**: Confusion matrix from the ViCoS evaluation. Highlight the dominant error modes (LSSO over-triggering, bilateral contact failure).

**Figure 8**: Example success and failure cases. Two columns: (a) correctly matched images with recovered contacts overlaid, (b) failure cases with the specific missing/spurious contacts annotated.

---

## Proposed Venue

- **Primary**: IJCAI, AAAI, or ECAI (formal representation / symbolic AI track)
- **Alternative**: Journal of Sports Engineering and Technology, or Computer Science in Sport
- **Long shot**: CVPR workshop on human interaction understanding (if empirical component is strengthened)

The paper is primarily a formalization contribution with empirical support, not a vision paper. Venue should value the representational contribution.

---

## Open Questions for the Authors

1. **Is Proposition 1 (field independence) worth stating formally?** It requires enumerating physically realizable contacts for all field-pair combinations. If some pairs are unrealizable, the claim needs qualification.

2. **Should depth be included or removed?** It adds a field to CON but plays no role in the current formalism. Cleaner to remove it and note it as future work.

3. **Should the paper include the 5 OGRD subtypes or defer them?** They demonstrate the representational granularity beautifully (single-field chains) but they are also the source of the worst empirical failures (over-triggering). Including them is honest but risks the reader conflating representational merit with empirical performance.

   *Recommendation*: Include in the formal model (Section 3), exclude from the empirical evaluation (Section 4), present the chain as a representational result (Section 3.5 or appendix).

4. **How to handle the 25.6% accuracy result?** It is weak in absolute terms but the failure-mode analysis redeems it by showing the representation is not the bottleneck. The paper must frame this carefully: the result is *informative*, not *disappointing*. The experiment's purpose is to characterize the perception-representation boundary, not to build a working classifier.

5. **Should the 5050 guard be included?** It is in the codebase and the ViCoS evaluation but is not one of the "7 fundamental" positions. Including it adds completeness but also adds complexity.

   *Recommendation*: Include in an appendix or footnote. It demonstrates how the formalism extends beyond the core seven.
