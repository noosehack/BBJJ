# Matboard V0 — Semantic Invariants

**Status**: FROZEN with kernel. Any change to engine BLISP must preserve these invariants.

---

## 1. MOR Legality

MOR preconditions are checked before resolution. A MOR whose preconditions fail is silently converted to PASS (nil). No ops from an illegal MOR are applied. No game memory effects from an illegal MOR occur.

**Tested**: `test_illegality.blisp` — 7 out-of-position MORs rejected, sub_threat unchanged on illegal submission.

## 2. MAINTAIN Persistence

MAINTAIN ops declare a CON as defended. A defended CON survives opponent DEL unless the DEL has strictly higher PRIORITY. On tied priority, the DEL fails and the CON persists (structural inertia).

**Tested**: `test_contests.blisp` — retain beats sweep when priority is higher; tie preserves CON.

## 3. Sweep Contact Preservation

Sweeps reverse orientation (SET_ORI) without deleting the contacts that define the new position. The hip bump sweep from CGRD to MNT uses MAINTAIN on both leg CONs, not DEL+ADD. After the sweep, both CONs remain and the position classifies correctly.

**Tested**: `test_sweep_contacts.blisp` — both leg CONs present before and after sweep; position transitions CGRD→MNT.

## 4. Submission Threat from MAINTAIN-only MORs

Submission MORs (triangle, americana, mnt_sub, bctr_rnc) contain only MAINTAIN ops. They do not change state. Sub_threat increments when a legal submission MOR is played from an offensive position (SCTR/MNT/BCTR), regardless of whether state mutates. The criterion is MOR legality (non-nil after precondition check), not state change.

**Tested**: `test_submission_threat.blisp` — MAINTAIN-only mnt_sub increments sub_threat; state confirmed unchanged; submission at sub_threat=3.

## 5. Momentum Tracks Consecutive States

Momentum uses two separate state comparisons:
- A succeeded: `st ≠ st1` (state changed by A's ops)
- B succeeded: `st1 ≠ st2` (state changed by B's ops after A's)

MAINTAIN-only MORs do not change state, so they do not affect momentum. Momentum is clamped to [-3, +3].

**Tested**: `test_momentum.blisp` — double PASS (0), A acts (+1), MAINTAIN-only (unchanged), clamp bounds.

## 6. TURN_FPT Emission

Every turn produces a TURN_FPT containing: turn number, state before/after, MOR IDs, position before/after, VAL before/after (both players), game memory after, contest wins. All fields are non-nil for played turns. VAL satisfies `val_a + val_b = 0` (zero-sum).

**Tested**: `test_turn_fpt.blisp` — all fields present, symmetry holds, PASS/PASS emits correctly.

## 7. GAME_FPT Reconstruction

GAME_FPT contains 12 fixed turn slots, winner, win condition, and final VAL. Turn slots chain: `t[n].state_after == t[n+1].state_before`. Turn numbers are sequential. Game memory chains through turns. Sub_threat progression is recoverable from the gmem_after field of each turn.

**Tested**: `test_game_fpt.blisp` — state chain verified, turn sequence verified, sub_threat progression reconstructed.

## 8. GAME_FPT Sufficiency

GAME_FPT alone is sufficient to reconstruct:
- Full game trajectory (state at every turn boundary)
- Threat progression (sub_threat from gmem_after)
- Momentum history (momentum from gmem_after)
- MOR legality (MOR IDs + position_before)
- Winning condition (winner + win_condition fields)

No information outside GAME_FPT is needed to replay a completed game.

## 9. Determinism

Resolution is a pure function of (state, MOR proposals, game memory). Identical inputs produce identical outputs. No hidden mutable state exists. No evaluation-order dependence. The engine uses no randomness, no timestamps, no external IO.

**Tested**: `test_determinism.blisp` — resolve, play-turn, and make-turn-fpt all produce identical results on repeated calls; init-state immutability confirmed.

## 10. No Hidden Runtime State

All game state is contained in three structures:
- **STATE**: CON slots, ORI, GND
- **GAME-MEM**: momentum, sub_threat, initiative, turn
- **FPT**: turn and game footprints

There is no global mutable accumulator, no side-channel state, no environment variable dependence. BLISP's `define` inside lambda/progn creates lexical bindings that do not persist across calls.

---

## Known Limitations

### count-contest-wins checks only op0/op1

`count-contest-wins` only inspects op0 and op1 for DEL contests. A DEL on op2 or op3 is correctly resolved by `resolve-op` (the CON is preserved or removed), but the contest is not counted toward initiative tracking. This means initiative may not update when contests occur on higher op slots.

### val returns float, not integer

`val` uses `(* 0.5 ...)` which produces float results. `(same 0 0.0)` is false in BLISP. Tests must use float-aware comparisons (assert-zero) when checking VAL values against zero.

### >= returns truthy integer, not boolean

BLISP's `>=` returns `1`/`0`, not `true`/`false`. `(same (>= 3 3) true)` is false. Code that needs boolean results must wrap: `(if (>= x y) true false)`.

### TUP key typo risk

BLISP keywords use `:snake_case` but variable names use `kebab-case`. A typo like `:wins-b` (hyphen) instead of `:wins_b` (underscore) creates a silently wrong key. The `:wins-b` bug was found and fixed during stabilization (resolve.blisp line 144).

### Sub_threat only tracks player A

The current implementation only checks player A's submission MOR for sub_threat accumulation. Player B's submissions are not tracked. This is a V0 simplification.
