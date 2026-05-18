# Injectivity Analysis

## Question

Can two structurally distinct positional states satisfy the same radical?

Formally: does there exist X ≠ Y such that Rad(X) = Rad(Y)?

If so, the radical function is not injective, and structurally different positions collapse to the same representation. This would mean the notation is too coarse to distinguish positions that fighters, coaches, and competitors treat as distinct.

## Method

For each radical R, identify the minimal constraint set and search for distinct configurations that satisfy all constraints. A "distinct configuration" means a different positional state with different tactical properties, entries, exits, and control dynamics — not just a different camera angle of the same position.

## Analysis

### MNT — Mount

**Constraints:** FacingOpposed, OnGround(Op.Ba), Me.Le+ on Op.To, Me.Le- on Op.To

**Distinct configurations satisfying MNT:**

1. **Low mount** — rider sits on opponent's hips, both legs wrapped at waist level
2. **High mount** — rider sits on opponent's chest, legs wrapped at shoulder level
3. **S-mount** — rider has one leg posted behind opponent's head, one wrapping torso
4. **Mounted crucifix** — rider has opponent's arm trapped between legs

All of these have both legs on torso and facing opposed. They are tactically distinct positions (different submission threats, different escape routes, different control dynamics).

**Is this a problem?** PARTIALLY. Low and high mount are variations of the same fundamental position — collapsing them is reasonable. S-mount and mounted crucifix are more structurally distinct but still share the core mount geometry. A practitioner would say these are all "mount" despite tactical differences.

**Verdict:** MNT is not injective, but the non-injectivity is at a natural granularity level. Mount variants share a structural core (bilateral leg-on-torso contact). The radical captures the shared structure correctly. Finer distinctions would require additional constraints (arm position, leg height) that would make the radical more brittle.

---

### BCTR — Back Control

**Constraints:** FacingAligned, NotOnGround(Op.Ba)*, Me.Le+ on Op.To, Me.Le- on Op.To, NOT(ankle closure)

(*NotOnGround is contingent and likely to be removed.)

**Distinct configurations satisfying BCTR:**

1. **Seatbelt back control** — hooks in, underhook + overhook (seatbelt grip)
2. **Body triangle back control** — one leg threads, ankle locks with other leg (note: this MAY trigger the forbidden ankle closure, making it excluded)
3. **Rear mount** — hooks in, opponent flat on stomach, controller on top
4. **Back crucifix** — one arm trapped between controller's legs from the back

These are tactically distinct. Body triangle is a different control system from hooks. Rear mount is different from seated back control.

**Is this a problem?** YES, to a degree. Body triangle back control is structurally different from hook-based back control (different leg contact graph), but both collapse to BCTR if the forbidden ankle closure is not triggered. The radical cannot distinguish them.

**Verdict:** BCTR is not injective. The hook-based vs body-triangle distinction is structurally real but not captured.

---

### SCTR — Side Control

**Constraints:** OnGround(Op.Ba), Me.Ar+ on Op.To, NOT(Me.Le on Op.Le+ or Op.Le-)

**Distinct configurations satisfying SCTR:**

1. **Standard side control** — crossface + underhook, chest-to-chest, hips heavy
2. **Kesa gatame (scarf hold)** — head control, hip-to-hip, perpendicular body angle
3. **Reverse kesa gatame** — facing opponent's legs, back-to-back pressure
4. **North-south** — chest on chest but head-to-toe alignment
5. **Twister side control** — body angle rotated, near-leg trapped

These are VERY different positions. Kesa gatame has a fundamentally different control logic from standard side control. North-south has a completely different body alignment. Reverse kesa is a different facing direction entirely.

**Is this a problem?** YES. SCTR collapses at least 4-5 structurally distinct positions. The constraint set (arm on torso + opponent on ground + no leg entanglement) is too permissive. Any top-position control with an arm across the torso and no guard satisfies SCTR.

**Verdict:** SCTR is the least injective fundamental radical. It represents a broad category ("top control without guard") rather than a specific position. North-south and kesa are structurally and tactically distinct from standard side control.

---

### CGRD — Closed Guard

**Constraints:** NotOnGround(Op.Ba), Me.Le+ on Op.To, Me.Le- on Op.To, Me.Fo- on Me.Fo+ (ankle closure)

**Distinct configurations satisfying CGRD:**

1. **Standard closed guard** — guard player supine, legs wrapped, ankles crossed at opponent's lower back
2. **High guard** — ankles crossed high on opponent's back, near shoulders
3. **Rubber guard** — one leg over-hooked behind opponent's head, ankles still crossed

High guard and rubber guard are variations. The constraint set is specific enough (requires ankle closure) that the space of satisfying configurations is narrow.

**Is this a problem?** NOT REALLY. Closed guard variants share the essential structure (bilateral leg wrap + closure). The tactical differences (grip, leg height) are beyond what a positional radical should capture.

**Verdict:** CGRD is approximately injective. The ankle closure constraint is discriminative enough to exclude most non-closed-guard positions.

---

### HGRD — Half Guard

**Constraints:** FacingOpposed, OnGround(Me.Ba), Me.Le on Op.Le

**Distinct configurations satisfying HGRD:**

1. **Standard half guard** — bottom player controls one leg between both legs
2. **Deep half guard** — bottom player is underneath the top player, head near hip
3. **Lockdown half guard** — bottom player's legs triangle around opponent's leg
4. **Z-guard (knee shield)** — knee blocking opponent's torso while controlling leg
5. **Half butterfly** — one butterfly hook + one leg entanglement

These are structurally and tactically very different. Z-guard has a knee frame that creates completely different dynamics from deep half. Lockdown has a specific leg configuration. Deep half involves being underneath the opponent.

**Is this a problem?** YES. HGRD has only one required contact (any leg on any leg) and FacingOpposed (which is typical, not invariant). The constraint set is too permissive — any position with leg entanglement and facing-opposed qualifies.

**Additionally:** FacingOpposed is typical, not invariant. Deep half and lockdown do not always have facing-opposed. If FacingOpposed is demoted, HGRD reduces to OnGround(Me.Ba) + Me.Le on Op.Le, which is even less discriminative.

**Verdict:** HGRD is not injective and structurally underdetermined. It collapses multiple distinct half-guard systems.

---

### TRTL — Turtle

**Constraints:** FacingAligned, Op.To on Me.To, NOT(Op.Le on Me.To)

**Distinct configurations satisfying TRTL:**

1. **Standard turtle with front headlock** — top player sprawls on turtled opponent
2. **Turtle with crossface** — top player perpendicular, crossface control
3. **Floating turtle** — top player behind but not in full contact

These are distinct but share the core structure (top player on turtled opponent's back, no hooks).

**Is this a problem?** MODERATE. Turtle variations are less distinct than SCTR variations. The primary issue is that "turtle" is really the bottom player's posture (curled on all fours) and the top player's position varies. The radical describes the top-to-bottom relation, not the bottom posture.

**Verdict:** TRTL is moderately non-injective. Front headlock vs back sprawl are different positions but both satisfy the constraints.

---

### OGRD — Open Guard

**Constraints:** FacingOpposed, OnGround(Me.Ba)

**Distinct configurations satisfying OGRD:**

1. De La Riva guard
2. Single-leg X guard
3. Reverse De La Riva
4. Lasso guard
5. Spider guard
6. Collar-sleeve guard
7. Butterfly guard
8. Sit-up guard
9. K-guard
10. Worm guard
11. Lapel guard variants
12. X-guard
13. ... (dozens more)

**Is this a problem?** YES, THIS IS THE WORST CASE. OGRD satisfies with FacingOpposed + OnGround alone. ANY bottom-player position with legs free and facing the opponent qualifies. This is not a radical — it is the complement of "all other ground positions."

**Verdict:** OGRD is maximally non-injective. It collapses dozens of structurally distinct guard systems. See ogrd_ontology_analysis.md.

---

## Formal Summary

| Radical | Injective? | Distinct configs collapsing | Severity |
|---------|-----------|----------------------------|----------|
| CGRD | Approximately | 2-3 (minor variants) | Low |
| MNT | No | 3-4 (mount variants) | Low |
| TRTL | No | 2-3 (turtle top variants) | Moderate |
| BCTR | No | 3-4 (back control variants) | Moderate |
| HGRD | No | 5+ (half guard systems) | High |
| SCTR | No | 5+ (top control variants) | High |
| OGRD | No | 20+ (all open guard types) | Critical |

## Implications

1. **No radical is perfectly injective.** This is expected — radicals represent equivalence classes, not individual states. The question is whether the equivalence classes are at the right granularity.

2. **CGRD and MNT are at good granularity.** The positions they collapse are genuinely variations of the same fundamental position. A practitioner would agree these are "all mount" or "all closed guard."

3. **HGRD and SCTR need refinement.** They collapse positions that practitioners treat as fundamentally different (Z-guard vs deep half; kesa vs north-south). The constraint sets are too permissive.

4. **OGRD is not a radical in the injective sense.** It is a residual category.

## Transition State Analysis

**Passing sequences:** A guard pass moves from CGRD/HGRD/OGRD → SCTR/MNT. During the pass, the geometry transitions through states that may not satisfy any radical:
- Knee-cut pass: one leg past guard, one leg still engaged → neither HGRD nor SCTR
- Toreando pass: legs thrown to one side → briefly satisfies nothing
- Over-under pass: head on one side, one arm under leg → partial SCTR

These transitional states are NOT captured by any radical. The notation describes stable attractors only.

**Partial mount:** Mounting from side control, the top player has one leg over but the other still blocked. This partially satisfies MNT (one leg on torso) but also partially satisfies HGRD (leg entanglement). Neither radical fully applies.

**Partial back take:** From turtle, the top player gets one hook in. This is between TRTL (no hooks) and BCTR (both hooks). With one hook, neither radical fully applies if BCTR requires bilateral hooks.

**Verdict:** The current notation describes stable attractor states. Transitional states fall between radicals and are not representable. This is not necessarily a flaw — a finite set of radicals cannot represent a continuous state space — but it should be explicitly acknowledged.
