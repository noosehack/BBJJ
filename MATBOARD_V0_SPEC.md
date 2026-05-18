# MATBOARD V0 — Frozen Specification

**Status**: FROZEN. Do not expand ontology unless something fundamentally breaks.

**What this is**: Deterministic symbolic BJJ game engine for teaching.
**What this is NOT**: CV, ML, physics sim, biomechanics, commercial game, NLP.

---

## 1. State

```
Σ := (ORI, GND, Set(CON))
```

### CON — Contact (the ONLY primitive)

```
CON := (actor: PartRef, target: PartRef, hel: Helicity)
```

- `PartRef := (role: Me|Op, part: Part, side: +|-|∅)`
- `Part ∈ {Le, Ar, To, Hd, Ne, Hp}`
- `Helicity ∈ {+, -, ∅}` — wrapping direction or barrier (∅)
- **Identity**: two CONs are equal iff `(actor, target, hel)` match. No depth field.

### ORI — Orientation

```
ORI := (facing: Facing, level: Level, alignment: Alignment)
```

- `Facing ∈ {OPPOSED, ALIGNED, PERP}`
- `Level ∈ {ME_OVER, OP_OVER, LEVEL}`
- `Alignment ∈ {NORMAL, INVERTED}`

### GND — Ground State

```
GND := (me: Ground, op: Ground)
```

- `Ground ∈ {SUPINE, PRONE, SEATED, KNEELING, STANDING, TURTLE}`

---

## 2. Radicals (Position Definitions)

8 matboard positions. Each is a constraint bundle:

```
Radical := (
    name: str,
    required_cons: Set(CON),      # all must be present
    forbidden_cons: Set(CON),     # none may be present (OR-semantics)
    ori_pred: Predicate(ORI),     # must hold
    gnd_pred: Predicate(GND),     # must hold
)
```

Classification: most specific matching radical wins. STDN is the fallback (matches any state not claimed by a more specific radical).

### Position List

| ID   | Name          | Tier    | Key Constraints |
|------|---------------|---------|-----------------|
| STDN | Standing      | neutral | no CONs / fallback |
| OGRD | Open Guard    | defense | Me.Le→Op (not closed) |
| CGRD | Closed Guard  | defense | Me.Le+→Op.To + Me.Le-→Op.To (legs enclose) |
| HGRD | Half Guard    | defense | one Me.Le→Op.Le |
| TRTL | Turtle        | defense | GND.me=TURTLE |
| SCTR | Side Control  | offense | Me.Ar→Op.To, ORI.level=ME_OVER |
| MNT  | Mount         | offense | Me.Le+→Op.To + Me.Le-→Op.To, ORI.level=ME_OVER |
| BCTR | Back Control  | offense | Me.Le+→Op.To + Me.Le-→Op.To, ORI.facing=ALIGNED |

Priority order (most specific first): BCTR > MNT > CGRD > SCTR > HGRD > OGRD > TRTL > STDN

---

## 3. MOR — Morphism (Formal Move)

```
MOR := (
    id: str,
    name: str,
    fiber: str,             # position this MOR is played FROM
    pre: List[Predicate],   # all must hold (conjunction)
    ops: List[Op],          # state mutations
    post: List[Predicate],  # expected result (assertion, not enforcement)
    fail: FailMode,         # what happens on contested denial
    cost: int,              # structural complexity (1-3)
    burst: int,             # execution speed (1-3)
    rev: bool,              # true = MOR also reverses (swap roles)
    tags: List[str],        # pedagogical tags
)
```

### Op Vocabulary (state mutations only)

```
ADD(con)           — add a CON to state
DEL(con)           — remove a CON (contestable by opponent MAINTAIN)
MAINTAIN(con)      — declare CON held (blocks opponent DEL)
SET_ORI(field, val) — set one ORI field
SET_GND(role, val)  — set one GND field
```

**NOT ops** (these are game memory, not state):
- sub_threat updates
- momentum updates

These are computed by engine rules after RESOLVE, based on what happened.

### Precondition Predicates

```
HAS_CON(con)           — state contains this CON
IN_RADICAL(radical_id)  — state classifies as this position
ORI_EQ(field, value)    — ORI field matches
GND_EQ(role, value)     — GND field matches
```

### Fail Modes

```
SAFE   — partial success; whatever ops aren't denied still apply
RSK    — transactional; if ANY critical op is denied, entire MOR fails
```

---

## 4. RESOLVE — Simultaneous Resolution

```
Σ_{t+1} = RESOLVE(Σ_t, MOR_a, MOR_b)
```

### Algorithm

1. **Legality check**: verify each MOR's `pre` against current state. Illegal MOR → PASS.
2. **Expand ops**: collect all ops from both MORs.
3. **Identify contests**: a DEL by player A on CON X is contested if player B has MAINTAIN(X).
4. **Resolve contests**: compare PRIORITY of the DEL vs the MAINTAIN. Higher priority wins.
5. **Apply non-contested ops**: all ADDs, SET_ORI, SET_GND, and uncontested DELs apply.
6. **Apply MAINTAIN mechanic**: for each of player A's CONs — if player B's MOR has a DEL on that CON, and player A's MOR does NOT have MAINTAIN on that CON, the DEL succeeds uncontested.
7. **Classify**: determine new position from resulting state.
8. **Update game memory**: momentum, sub_threat (engine rules, not MOR ops).

### PRIORITY

```
PRIORITY(mor, game_mem) = mor.burst + INITIATIVE + DEFENSE_BONUS - DIFFICULTY
```

- `INITIATIVE`: +1 if this player won the previous contest (tracked in game memory). Turn 1: player A gets initiative.
- `DEFENSE_BONUS`: +1 if this player is in a worse position (lower V_pos).
- `DIFFICULTY`: `mor.cost - 1` (cost 1 = no penalty, cost 3 = -2 penalty).

### Tie-Breaking

**Ties preserve current state.** Contested op fails; the CON remains as-is. This creates structural inertia.

### Invalid Prompt

Invalid prompt → PASS. No ops. All of that player's CONs are undefended (no MAINTAIN), so opponent DELs succeed freely.

---

## 5. VAL — Position Valuation

```
VAL(state) = V_pos(position) + V_control(cons)
```

### V_pos (lookup)

| Position | V_pos |
|----------|-------|
| BCTR     | +4    |
| MNT      | +3    |
| SCTR     | +2    |
| TRTL     | -1    |
| HGRD     | 0     |
| CGRD     | +1    |
| OGRD     | 0     |
| STDN     | 0     |

Values are from Me's perspective. Op's V_pos is negated.

### V_control

+0.5 per CON owned by Me, -0.5 per CON owned by Op. Capped at ±2.

---

## 6. Game Memory

```
GameMem := (
    momentum: int,      # [-3, +3], who has tempo
    sub_threat: int,     # [0, 3], submission progress
    initiative: Role,    # who won last contest
    turn: int,           # current turn number
)
```

### Update Rules (after RESOLVE, not inside MOR ops)

- **momentum**: +1 if your MOR succeeded (at least one op applied), -1 if opponent's did. Clamped [-3, +3].
- **sub_threat**: +1 if a MOR with tag "submission" succeeded from an offensive position (SCTR/MNT/BCTR). Reset to 0 on position change away from offense.
- **initiative**: goes to the player who won the most contests this turn. Tie = no change.

### Win Conditions

- **Submission**: sub_threat reaches 3. Submitting player wins.
- **Points**: after 12 turns, highest cumulative VAL wins.
- **Draw**: equal VAL after 12 turns.

---

## 7. Canonicalization

Z₂ × Z₂ symmetry group:

- **σ (side swap)**: swap + and - sides on all PartRefs. Le+ ↔ Le-. Hel flips.
- **π (POV swap)**: swap Me ↔ Op on all PartRefs. Hel flips. ORI transforms (level inverts, facing preserved).

Canonical form: apply σ and π to minimize a lexicographic ordering on CON set.

---

## 8. Footprints

### TURN_FPT

```
TURN_FPT := (
    turn: int,
    state_before: Σ,
    mor_a: MOR_id,
    mor_b: MOR_id,
    contests: List[(Op, Op, winner)],
    state_after: Σ,
    position_before: str,
    position_after: str,
    val_before: (float, float),
    val_after: (float, float),
    game_mem_after: GameMem,
)
```

### GAME_FPT

```
GAME_FPT := (
    turns: List[TURN_FPT],
    winner: Role | None,
    win_condition: "submission" | "points" | "draw",
    final_val: (float, float),
)
```

---

## 9. Escape MOR Design Principle

Escape MORs MUST ADD guard-appropriate CONs, not just DEL offensive CONs. Recovery requires rebuilding structure.

Example: elbow-knee escape from mount → DEL(opponent mount CONs) + ADD(Me.Le→Op.Le half guard CON) + SET_GND appropriate.

---

## 10. Implementation Plan

### File Structure

```
BBJJ/engine/
    types.py       — PartRef, CON, ORI, GND, State, MOR, Op, Predicate, GameMem, FPT
    radicals.py    — 8 radical definitions
    classify.py    — state → position
    resolve.py     — RESOLVE algorithm
    val.py         — VAL computation
    game.py        — game loop, memory updates, win conditions
    cli.py         — REPL interface

BBJJ/data/
    mor_library.json — 16-20 MORs for v0
```

### Minimum Playable MOR Set (16)

2 per position:
- STDN: takedown, pull_guard
- OGRD: sweep, submit_attempt
- CGRD: sweep, submit_attempt
- HGRD: sweep, pass
- TRTL: stand_up, sit_to_guard
- SCTR: advance_mount, submit_attempt
- MNT: submit_attempt, maintain_pressure
- BCTR: submit_attempt, maintain_control

### Critical Test

Play S1 road: pull guard (STDN→CGRD) → sweep (CGRD→MNT) → submit×3 (MNT, sub_threat 0→1→2→3). Verify state transitions, classification, and footprint correctness.

---

## Deferred (NOT v0)

- Subtopology classification (DLR, SLX, etc.)
- Submission identity (which sub specifically)
- MOR branching / decision trees
- Gi vs no-gi variants
- Guard retention system
- Style modifiers
- Resource allocation / fatigue
- AI agents / NLP
- CV / graphics / physics
