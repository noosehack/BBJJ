# Matboard V1 P1 — Semantic Playtest Report

**Date**: 2026-05-19
**Engine**: Matboard V1 kernel + P1 tuning (sub_threat decay, CGRD offensive submissions)
**Games**: 20 scripted, 7 scenario families
**Runtime**: BLISP hybrid mode, deterministic
**Tests**: 12 suites, 164 assertions, 0 failures

---

## Summary

| Metric | Value |
|--------|-------|
| Games played | 20 |
| Submissions | 9 (G05, G06, G08, G09, G13, G15, G16, G17, G19) |
| Points wins | 10 (G01, G02, G03, G07, G10, G11, G12, G14, G18, G20) |
| Draws | 1 (G04) |
| Semantic failures | 0 (F1-F3 fixed in V1) |
| Semantic issues | 1 (I3: momentum decay — still open) |
| BJJ-plausible outcomes | 20 of 20 |

### P1 Changes

Sub_threat tuning in resolve.blisp:
- **Decay**: sub_threat decrements by 1 each turn when A does NOT play a submission MOR. Floor at 0. Position change still resets to 0.
- **CGRD offensive**: CGRD added to `pos-is-off` for sub_threat. Submission-tagged MORs from closed guard (triangle, future armbar/choke) now accumulate sub_threat.

Code: `(clamp (+ (GET gmem :sub_threat) -1) 0 3)` replaces `(GET gmem :sub_threat)` in the else branch.

---

## Comparison vs Pre-P1

| Game | Pre-P1 | Post-P1 | Change |
|------|--------|---------|--------|
| G06 | A pts (12t), sub=0 | A **sub** (4t), sub=0→1→2→3 | **I1 FIXED** — triangle from CGRD now accumulates |
| G10 | A pts, sub=2×9 frozen | A pts, sub=2→1→0 decay | **I2 FIXED** — sub_threat decays on PASS |
| G12 | sub=1×9 after escape | sub=1→0 after escape | Decay removes stale threat |
| G18 | sub=1×10 after escape | sub=1→0 after escape | Decay cleans up post-escape |
| All others | — | — | Unchanged |

---

## Changed Game Results

### G06: CGRD triangle-from-defense (CHANGED)

| Field | Pre-P1 | Post-P1 |
|-------|--------|---------|
| RAD path | STDN → CGRD×12 | STDN → CGRD×4 → (sub t4) |
| Sub_threat | 0 (constant) | 0 → 1 → 2 → 3 |
| Winner | A by points (2 / -2) | A by **submission** (turn 4) |
| BJJ-plausible | NO (I1) | **YES** |
| Semantic issue | I1: CGRD not in offensive set | **I1 FIXED** |

Triangle from closed guard now accumulates sub_threat and finishes in 4 turns. This is BJJ-correct — triangle choke from closed guard is one of the most common submissions in competition.

### G10: SCTR sub-threat-non-decay (CHANGED)

| Field | Pre-P1 | Post-P1 |
|-------|--------|---------|
| Sub_threat | 0 → 1 → 2 → 2×9 (frozen) | 0 → 1 → 2 → 1 → 0×8 |
| BJJ-plausible | PARTIAL (I2) | **YES** |
| Semantic issue | I2: sub_threat frozen at 2 | **I2 FIXED** |

Sub_threat correctly decays when A stops applying submission MORs. After 2 consecutive americanas, A passes — sub_threat drops 2→1→0 over 2 turns. This models the reality that submission pressure dissipates when the attacker disengages.

### G12: MNT B-escapes-vs-A-control (CHANGED)

| Field | Pre-P1 | Post-P1 |
|-------|--------|---------|
| Sub_threat progression | 0→0→1→1×9 | 0→0→1→0×9 |
| Winner | A by points (2 / -2) | A by points (2 / -2) |

Turn 3: A's mnt_sub from MNT increments sub_threat to 1. Bridge succeeds (MNT→CGRD). Turn 4: Both players' MNT MORs fail preconditions in CGRD, effectively PASS. Sub_threat decays 1→0. Previously sub_threat=1 persisted through 9 CGRD turns.

### G18: SCTR shrimp-escape (CHANGED)

| Field | Pre-P1 | Post-P1 |
|-------|--------|---------|
| Sub_threat progression | 0→1→1×10 | 0→1→0×10 |
| Winner | A by points (0.5 / -0.5) | A by points (0.5 / -0.5) |

After shrimp escape (SCTR→HGRD), sub_threat decays from 1→0 on the first PASS. Previously persisted at 1 for 10 turns.

---

## Semantic Issues

### I1: Triangle from CGRD — FIXED

CGRD now in offensive set for sub_threat. Triangle accumulates: 0→1→2→3→submission.

### I2: Sub_threat Does Not Decay — FIXED

Sub_threat decays by 1 each turn without a submission MOR. Floor at 0. Position change resets to 0.

### I3: Momentum Does Not Decay (G01, G02, G07, G10, G11, G20) — OPEN

**Severity**: LOW — momentum freezes on mutual PASS. Still present. Deferred to P2.

---

## Unchanged Games

All other games (G01-G05, G07-G09, G11, G13-G16, G19-G20) produce identical results. Consecutive submission MORs still increment sub_threat as before — decay only applies when a non-submission turn occurs.

Key verification:
- G05 (sweep→mount→sub): mnt_sub×3 = 0→1→2→3, submission turn 5. Unchanged.
- G08 (americana sub): americana×3 = 0→1→2→3, submission turn 4. Unchanged.
- G09 (sub-reset-on-advance): americana×2→mount→mnt_sub×3, sub resets on advance. Unchanged.
- G17 (bridge-escape-cycle): sub resets on position change (MNT→CGRD→MNT). Unchanged.
- G20 (failed-escape-chain): mnt_pressure×10, sub=0 constant. Unchanged.

---

## Test Changes

| Suite | Assertions | Change |
|-------|-----------|--------|
| test_sub_decay.blisp (NEW) | 18 | Decay, CGRD subs, interleave patterns |
| test_submission_threat.blisp | 8 | "triangle from CGRD" now expects sub=1 |
| test_illegality.blisp | 8 | "illegal sub" now expects decay (1→0) |
| All other suites | 130 | Unchanged, 0 regressions |
| **Total** | **164** | **0 failures** |

---

## Conclusions

1. **I1 and I2 are fixed.** Sub_threat decay and CGRD offensive submissions resolve both open semantic issues. All 20 games are BJJ-plausible.

2. **Decay creates temporal pressure.** Attackers must commit to consecutive submissions — pausing to reposition or control causes sub_threat to decay. This matches real grappling: a stalled submission attempt loses effectiveness.

3. **CGRD submissions are balanced.** Triangle from guard finishes in 4 turns (same speed as americana from side control). CGRD's lower VAL (2 vs SCTR 2.5, MNT 4) compensates for the submission access — guard is a legitimate but not dominant attacking platform.

4. **Escape + decay interaction is natural.** After a successful escape (G12, G18), the stale sub_threat decays away. The escapee isn't penalized by a threat that no longer applies.

5. **One issue remains: I3 (momentum decay).** Momentum freezes on mutual PASS. Deferred to P2 — lower priority than sub_threat since momentum doesn't affect win conditions.

---

## Next Priority

| Priority | Item | Status |
|----------|------|--------|
| ~~P0~~ | ~~Escape MORs~~ | **DONE** |
| ~~P0~~ | ~~Conflict resolution~~ | **DONE** |
| ~~P1~~ | ~~Sub_threat decay~~ | **DONE** |
| ~~P1~~ | ~~CGRD offensive submissions~~ | **DONE** |
| P2 | Momentum decay on mutual PASS | Open |
| P2 | Back-take transition (→BCTR) | Open |
| P2 | Turtle transition (failed takedown→TRTL) | Open |
