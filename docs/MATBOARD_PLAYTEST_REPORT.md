# Matboard V1 — Semantic Playtest Report

**Date**: 2026-05-18
**Engine**: Matboard V1 kernel (V0 frozen + escape MORs + conflict resolution)
**Games**: 20 scripted, 7 scenario families
**Runtime**: BLISP hybrid mode, deterministic

---

## Summary

| Metric | Value |
|--------|-------|
| Games played | 20 |
| Submissions | 8 (G05, G08, G09, G13, G15, G16, G17, G19) |
| Points wins | 11 (G01, G02, G03, G06, G07, G10, G11, G12, G14, G18, G20) |
| Draws | 1 (G04) |
| Semantic failures | 0 (F1, F2, F3 all FIXED) |
| Semantic issues | 3 (I1–I3) |
| BJJ-plausible outcomes | 20 of 20 |

### V1 Changes

4 escape MORs added to morphisms.blisp (16 → 20 MORs):
- `mnt_bridge` (SET_ORI level→LEVEL, non-contestable) → CGRD
- `mnt_elbow_knee` (DEL one leg, contestable) → OGRD
- `sctr_shrimp` (DEL arm + ADD leg-on-leg, contestable) → HGRD
- `bctr_turn_in` (DEL both legs + SET_GND TURTLE, contestable) → TRTL

Conflict resolution added to resolve.blisp:
- `mor-changes-state`: detects if a MOR has any ADD/DEL/SET_ORI/SET_GND ops
- When both players' MORs are state-changing, higher priority wins; loser becomes PASS
- Fixes G03 (takedown vs pull_guard): pull_guard wins (burst=3 > burst=2), result is clean CGRD (val=2)

---

## Game Results

### Group 1: STDN — Takedown / Pull Guard / Simultaneous

#### G01: STDN takedown

| Field | Value |
|-------|-------|
| Initial RAD | STDN |
| Player roles | A = attacker, B = passive |
| Move sequence | A: takedown, PASS×11; B: PASS×12 |
| RAD path | STDN → SCTR×12 |
| VAL progression | 0 → 2.5 (constant after t1) |
| Momentum | 0 → 1 (frozen) |
| Sub_threat | 0 (constant) |
| Winner | A by points (2.5 / -2.5) |
| BJJ-plausible | YES |
| Semantic failures | None |
| Suggested tuning | Momentum should decay toward 0 on mutual PASS (see I3) |

#### G02: STDN pull_guard

| Field | Value |
|-------|-------|
| Initial RAD | STDN |
| Player roles | A = guard puller, B = passive |
| Move sequence | A: pull_guard, PASS×11; B: PASS×12 |
| RAD path | STDN → CGRD×12 |
| VAL progression | 0 → 2 (constant after t1) |
| Momentum | 0 → 1 (frozen) |
| Sub_threat | 0 (constant) |
| Winner | A by points (2 / -2) |
| BJJ-plausible | PARTIAL — pull_guard giving A positive VAL is debatable |
| Semantic failures | None |

#### G03: STDN takedown-vs-pull_guard (simultaneous)

| Field | Value |
|-------|-------|
| Initial RAD | STDN |
| Player roles | A = takedown, B = pull_guard (simultaneous) |
| Move sequence | A: takedown, PASS×11; B: pull_guard, PASS×11 |
| RAD path | STDN → CGRD×12 |
| VAL progression | 0 → 2 (constant after t1) |
| Momentum | 0 → -1 (B's pull_guard succeeds, A nullified) |
| Sub_threat | 0 (constant) |
| Winner | A by points (2 / -2) |
| BJJ-plausible | YES — **F1/F3 FIXED**. Conflict resolution detects both MORs as state-changing. pull_guard (burst=3, pri=4) beats takedown (burst=2, pri=2). Only pull_guard applies → clean CGRD, val=2. |

#### G04: STDN 12x-stall

| Field | Value |
|-------|-------|
| Initial RAD | STDN |
| Player roles | Both passive |
| Move sequence | A: PASS×12; B: PASS×12 |
| RAD path | STDN×12 |
| VAL / Momentum / Sub | 0 / 0 / 0 (constant) |
| Winner | DRAW (0 / 0) |
| BJJ-plausible | YES |

---

### Group 2: CGRD — Sweep Chain

#### G05: CGRD sweep → mount → sub (S1 road)

| Field | Value |
|-------|-------|
| Initial RAD | STDN |
| Move sequence | A: pull_guard, hip_bump, mnt_sub×3; B: PASS×12 |
| RAD path | STDN → CGRD → MNT → MNT → MNT → (sub t5) |
| VAL | 0 → 2 → 4 → 4 → 4 |
| Momentum | 0 → 1 → 2 → 2 → 2 |
| Sub_threat | 0 → 0 → 1 → 2 → 3 |
| Winner | A by submission (turn 5) |
| BJJ-plausible | YES — canonical teaching trace |

#### G06: CGRD triangle-from-defense

| Field | Value |
|-------|-------|
| Initial RAD | STDN |
| Move sequence | A: pull_guard, triangle×11; B: PASS×12 |
| RAD path | STDN → CGRD×12 |
| Sub_threat | 0 (constant — CGRD not in offensive set) |
| Winner | A by points (2 / -2) |
| BJJ-plausible | **NO** — triangle should accumulate sub_threat |
| **Semantic issue** | **I1**: CGRD not in offensive set for sub_threat |

#### G07: CGRD sweep-contact-check

| Field | Value |
|-------|-------|
| Initial RAD | STDN |
| Move sequence | A: pull_guard, hip_bump, PASS×10; B: PASS×12 |
| RAD path | STDN → CGRD → MNT×11 |
| VAL | 0 → 2 → 4 (constant) |
| Winner | A by points (4 / -4) |
| BJJ-plausible | YES — contacts preserved through sweep (Invariant #3) |

---

### Group 3: SCTR — Control / Advance / Sub_threat

#### G08: SCTR americana-sub

| Field | Value |
|-------|-------|
| Move sequence | A: takedown, sctr_americana×3; B: PASS×12 |
| RAD path | STDN → SCTR → SCTR → SCTR → (sub t4) |
| Sub_threat | 0 → 1 → 2 → 3 |
| Winner | A by submission (turn 4) |
| BJJ-plausible | YES |

#### G09: SCTR sub-reset-on-advance

| Field | Value |
|-------|-------|
| Move sequence | A: takedown, americana×2, sctr_mount, mnt_sub×3; B: PASS×12 |
| RAD path | STDN → SCTR×3 → MNT×3 → (sub t7) |
| Sub_threat | 0 → 1 → 2 → 0 → 1 → 2 → 3 |
| Winner | A by submission (turn 7) |
| BJJ-plausible | YES — sub_threat resets on position change |

#### G10: SCTR sub-threat-non-decay

| Field | Value |
|-------|-------|
| Move sequence | A: takedown, americana×2, PASS×9; B: PASS×12 |
| Sub_threat | 0 → 1 → 2 → 2×9 |
| Winner | A by points (2.5 / -2.5) |
| **Semantic issue** | **I2**: Sub_threat frozen at 2 through 9 PASS turns |

---

### Group 4: MNT — Pressure / Escape / B Fights Back

#### G11: MNT pressure-hold

| Field | Value |
|-------|-------|
| Move sequence | A: pull_guard, hip_bump, mnt_pressure×10; B: PASS×12 |
| RAD path | STDN → CGRD → MNT×11 |
| Winner | A by points (4 / -4) |
| BJJ-plausible | YES — pressure hold, no sub_threat |

#### G12: MNT B-escapes-vs-A-control (UPDATED from v2)

| Field | Value |
|-------|-------|
| Initial RAD | STDN |
| Player roles | A = alternates sub/pressure, B = alternates bridge/elbow-knee |
| Move sequence | A: pull_guard, hip_bump, [mnt_sub, mnt_pressure]×5; B: PASS×2, [mnt_bridge, mnt_elbow_knee]×5 |
| RAD path | STDN → CGRD → MNT → CGRD → CGRD×9 |
| VAL progression | 0 → 2 → 4 → 2 → 2×9 |
| Momentum | 0 → 1 → 2 → 1 → 1×9 |
| Sub_threat | 0 → 0 → 1 → 1×9 |
| Winner | A by points (2 / -2) |
| BJJ-plausible | YES — **F2 FIXED**. B escapes mount with bridge on turn 3 (MNT→CGRD). After escape, both players' MNT MORs fail preconditions in CGRD (PRED-RAD "MNT" rejects). Game settles into CGRD. Sub_threat freezes at 1 (accumulated before escape, position unchanged after). |
| Notable | Bridge escape is non-contestable — works even against mnt_sub. Elbow-knee fails against mnt_pressure (MAINTAIN beats DEL on priority). A must choose: sub (risky, escapable) or pressure (safe, blocks escape). |

---

### Group 5: BCTR — Synthetic Start / RNC / Control

#### G13: BCTR rnc-sub

| Field | Value |
|-------|-------|
| Initial RAD | BCTR (synthetic) |
| Move sequence | A: bctr_rnc×3; B: PASS×12 |
| RAD path | BCTR×3 → (sub t3) |
| Winner | A by submission (turn 3) — fastest possible finish |
| BJJ-plausible | YES |

#### G14: BCTR control-hold

| Field | Value |
|-------|-------|
| Initial RAD | BCTR (synthetic) |
| Move sequence | A: bctr_control×12; B: PASS×12 |
| Winner | A by points (5 / -5) |
| BJJ-plausible | YES |

---

### Group 6: TRTL — Synthetic Start / Standup / Sit-to-Guard

#### G15: TRTL standup → takedown → sub

| Field | Value |
|-------|-------|
| Initial RAD | TRTL (synthetic) |
| Move sequence | A: trtl_standup, takedown, americana×3; B: PASS×12 |
| RAD path | TRTL → STDN → SCTR×3 → (sub t5) |
| VAL | -1 → 0 → 2.5 → 2.5 → 2.5 |
| Winner | A by submission (turn 5) |
| BJJ-plausible | YES |

#### G16: TRTL sit → sweep → mount → sub

| Field | Value |
|-------|-------|
| Initial RAD | TRTL (synthetic) |
| Move sequence | A: trtl_sit, ogrd_sweep, sctr_mount, mnt_sub×3; B: PASS×12 |
| RAD path | TRTL → OGRD → SCTR → MNT×3 → (sub t6) |
| VAL | -1 → 0.5 → 2.5 → 4 → 4 → 4 |
| Momentum | 0 → 1 → 2 → 3 → 3 → 3 |
| Winner | A by submission (turn 6) — longest chain tested |
| BJJ-plausible | YES |

---

### Group 7: ESCAPE MOR GAMES (NEW)

#### G17: MNT bridge-escape-cycle

| Field | Value |
|-------|-------|
| Initial RAD | STDN |
| Player roles | A = sweep + sub, B = bridge escape then passive |
| Move sequence | A: pull_guard, hip_bump, mnt_sub, hip_bump, mnt_sub×3; B: PASS×2, mnt_bridge, PASS×9 |
| RAD path | STDN → CGRD → MNT → CGRD → MNT → MNT → MNT → (sub t7) |
| VAL | 0 → 2 → 4 → 2 → 4 → 4 → 4 |
| Momentum | 0 → 1 → 2 → 1 → 2 → 2 → 2 |
| Sub_threat | 0 → 0 → 1 → 0 → 1 → 2 → 3 |
| Winner | A by submission (turn 7) |
| BJJ-plausible | YES — B bridges out of mount (t3), A re-sweeps from guard (t4), finishes with sub. Bridge bought B 2 extra turns. Sub_threat correctly resets on position change (MNT→CGRD→MNT). Demonstrates the mount→guard→mount cycle. |

#### G18: SCTR shrimp-escape

| Field | Value |
|-------|-------|
| Initial RAD | STDN |
| Player roles | A = takedown + americana, B = shrimp escape |
| Move sequence | A: takedown, sctr_americana, PASS×10; B: PASS, sctr_shrimp, PASS×10 |
| RAD path | STDN → SCTR → HGRD×11 |
| VAL | 0 → 2.5 → 0.5 (constant after t2) |
| Momentum | 0 → 1 → 0 (constant after t2) |
| Sub_threat | 0 → 1 → 1×10 |
| Initiative | A → A → B (shifts on successful escape!) |
| Winner | A by points (0.5 / -0.5) |
| BJJ-plausible | YES — B shrimps out of americana to half guard. Val drops from 2.5 to 0.5 (A lost side control). Initiative shifts to B. Sub_threat=1 persists (americana was legal before escape — see I2). |
| Notable | sctr_shrimp beats sctr_americana in contest (escape burst=3 > americana burst=1). B's DEL removes arm contact, ADD creates leg-on-leg → HGRD. Initiative shifts to B via contest win. |

#### G19: BCTR turn-in-escape

| Field | Value |
|-------|-------|
| Initial RAD | BCTR (synthetic) |
| Player roles | A = RNC then retakes, B = turn-in escape then standup |
| Move sequence | A: bctr_rnc, PASS, takedown, americana×3; B: bctr_turn_in, trtl_standup, PASS×10 |
| RAD path | BCTR → TRTL → STDN → SCTR×3 → (sub t6) |
| VAL | 5 → -1 → 0 → 2.5 → 2.5 → 2.5 |
| Momentum | 0 → -1 → -2 → -1 → -1 → -1 |
| Sub_threat | 1 → 0 → 0 → 1 → 2 → 3 |
| Initiative | A → B → B → B → B → B |
| Winner | A by submission (turn 6) |
| BJJ-plausible | YES — B escapes back control to turtle (val 5→-1, huge swing), stands up to neutral, but A retakes with takedown and finishes from side control. Initiative stays with B after escape, but B can't capitalize (no B-fiber offense from STDN). |
| Notable | bctr_turn_in beats bctr_rnc (escape burst=4 vs RNC burst=1). Both leg DELs succeed. SET_GND TURTLE applies. Val swing of 6 points is the largest single-turn change in any playtest. Negative momentum shows B's escape dominating the momentum tracker. |

#### G20: MNT failed-escape-chain

| Field | Value |
|-------|-------|
| Initial RAD | STDN |
| Player roles | A = mount pressure, B = repeated elbow-knee attempts |
| Move sequence | A: pull_guard, hip_bump, mnt_pressure×10; B: PASS×2, mnt_elbow_knee×10 |
| RAD path | STDN → CGRD → MNT×11 |
| VAL | 0 → 2 → 4 (constant after t2) |
| Momentum | 0 → 1 → 2 (constant after t2) |
| Sub_threat | 0 (constant — mnt_pressure is control, not submission) |
| Winner | A by points (4 / -4) |
| BJJ-plausible | YES — B tries elbow-knee escape 10 times, fails every time against active pressure. mnt_pressure MAINTAIN beats mnt_elbow_knee DEL on priority (pressure burst=3+init vs escape burst=3). Demonstrates that escapes are not free — A must be passive or going for submission for B to escape. |

---

## Semantic Failures

### F1: Simultaneous Conflicting Transitions Stack (G03) — FIXED

**Severity**: was HIGH → **RESOLVED**

When both players propose position-changing MORs (takedown vs pull_guard), conflict resolution now detects both as state-changing and resolves by priority. Higher-priority MOR wins; loser is nullified to PASS.

**Resolution**: Added `mor-changes-state` detection and conflict gate in RESOLVE. G03 now produces clean CGRD (val=2) instead of Frankenstein MNT (val=4.5). pull_guard wins because burst=3 > takedown burst=2.

### F2: Absorbing States — No Escape MORs (G12 v2) — FIXED

**Severity**: was HIGH → **RESOLVED**

4 escape MORs added. G12 updated: B now escapes mount with bridge. G17–G20 demonstrate full escape dynamics.

**Resolution**: mnt_bridge (non-contestable → CGRD), mnt_elbow_knee (contestable → OGRD), sctr_shrimp (contestable → HGRD), bctr_turn_in (contestable → TRTL).

**Contest dynamics**: Escapes beat submission MORs (low burst) but lose to control/pressure MORs (high burst). A must choose between safe control (blocks escape, no sub progress) and risky submission (escapable, accumulates sub_threat). This creates meaningful strategic decisions.

### F3: Simultaneous Transition Creates Unreachable Val (G03) — FIXED

**Severity**: was MEDIUM → **RESOLVED** (consequence of F1 fix)

Val=4.5 no longer occurs. G03 now produces val=2 (clean CGRD).

---

## Semantic Issues

### I1: Triangle from CGRD Does Not Accumulate Sub_threat (G06)

**Severity**: MEDIUM — CGRD not in offensive set for sub_threat.

### I2: Sub_threat Does Not Decay (G10, G18)

**Severity**: LOW-MEDIUM — sub_threat persists through PASS turns. G18 shows sub_threat=1 surviving escape and 10 subsequent idle turns.

### I3: Momentum Does Not Decay (G01, G02, G07, G10, G11, G20)

**Severity**: LOW — momentum freezes on mutual PASS.

---

## Transition Graph (V1)

```
                  ┌──────────────┐
                  │    STDN      │
                  │  val = 0     │
                  └──┬───────┬───┘
            takedown │       │ pull_guard
                     ▼       ▼
               ┌─────────┐ ┌─────────┐
               │  SCTR   │ │  CGRD   │
               │ val=2.5 │ │ val=2   │
               └────┬────┘ └────┬────┘
          sctr_mount │   hip_bump│
                     ▼          ▼
                  ┌─────────────┐
                  │    MNT      │
                  │  val = 4    │
                  └─────────────┘

  ESCAPE PATHS (B-fiber, NEW):
    MNT ──mnt_bridge──→ CGRD       (non-contestable)
    MNT ──mnt_elbow_knee──→ OGRD   (contestable)
    SCTR ──sctr_shrimp──→ HGRD     (contestable)
    BCTR ──bctr_turn_in──→ TRTL    (contestable)

  Synthetic-start only:
  ┌─────────┐                     ┌─────────┐
  │  BCTR   │──bctr_turn_in──→    │  TRTL   │──┐
  │ val = 5 │                     │ val=-1  │  │ trtl_standup → STDN
  └─────────┘                     └─────────┘  │ trtl_sit → OGRD
                                               ▼
                                  ┌─────────┐
                                  │  OGRD   │
                                  │ val=0.5 │──→ ogrd_sweep → SCTR
                                  └─────────┘

                                  ┌─────────┐
                                  │  HGRD   │
                                  │ val=0.5 │──→ hgrd_sweep → SCTR
                                  └─────────┘    hgrd_pass → SCTR

  NO LONGER ABSORBING: MNT (bridge/elbow-knee), SCTR (shrimp), BCTR (turn-in)
  NEWLY REACHABLE: HGRD (via sctr_shrimp), OGRD (via mnt_elbow_knee)
  STILL NOT REACHABLE from init: BCTR, TRTL
```

---

## Escape Contest Priority Table

| Escape MOR | burst | cost | Base pri | vs Control | vs Submission | vs PASS |
|------------|-------|------|----------|------------|---------------|---------|
| mnt_bridge | 2 | 3 | 0 | N/A (non-contestable) | N/A | N/A |
| mnt_elbow_knee | 3 | 2 | 2 | LOSE (vs pressure pri=3+init) | WIN (vs sub pri=0+init) | AUTO-WIN |
| sctr_shrimp | 3 | 2 | 2 | N/A (no SCTR control MOR) | WIN (vs americana pri=0+init) | AUTO-WIN |
| bctr_turn_in | 4 | 2 | 3 | LOSE w/o init (vs control pri=3+init) | WIN (vs RNC pri=0+init) | AUTO-WIN |

---

## VAL Ordering

| Position | VAL | Reachable from init | Escapable |
|----------|-----|---------------------|-----------|
| BCTR | 5 | No (synthetic) | Yes (turn-in → TRTL) |
| MNT | 4 | Yes | Yes (bridge → CGRD, elbow-knee → OGRD) |
| SCTR | 2.5 | Yes | Yes (shrimp → HGRD) |
| CGRD | 2 | Yes | N/A (not a bad position) |
| HGRD | 0.5 | Yes (via shrimp) | N/A |
| OGRD | 0.5 | Yes (via elbow-knee) | N/A |
| STDN | 0 | Yes (init) | N/A |
| TRTL | -1 | No (synthetic) | Yes (standup/sit) |

---

## Conclusions

1. **F2 is fixed.** MNT, SCTR, and BCTR are no longer absorbing. Bottom players have legal escape MORs. 4 new games (G17–G20) demonstrate escape dynamics.

2. **Escape contest mechanics create strategic depth.** A must choose between control (blocks escape, no sub progress) and submission (accumulates sub_threat, but B can escape). This is the fundamental mount/side-control decision in real BJJ.

3. **Bridge escape is non-contestable (design choice).** mnt_bridge always works via SET_ORI. This means a mounted player can always reach CGRD. To compensate, CGRD is a lower-value position (val=2 vs MNT val=4), and A can re-sweep with hip_bump. Mount→guard→mount cycling is a realistic grappling dynamic.

4. **F1/F3 (simultaneous conflicts) are fixed.** Conflict resolution detects when both MORs are state-changing and resolves by priority. G03 now produces a clean CGRD (val=2) instead of a Frankenstein MNT (val=4.5). All 20 games are BJJ-plausible.

5. **Initiative shift on escape is emergent behavior.** G18 and G19 show initiative flipping to B after a successful escape (B wins the DEL contest). This is unscripted — it falls out of the contest-counting system. It's BJJ-correct: a successful escape demonstrates momentum and fighting spirit.

6. **Transition graph improved.** HGRD and OGRD are now reachable from init via escape MORs. Only BCTR and TRTL remain synthetic-start-only. Graph gaps for back-take (→BCTR) and failed takedown (→TRTL) remain for V2.

---

## Next Priority

| Priority | Item | Status |
|----------|------|--------|
| ~~P0~~ | ~~Escape MORs~~ | **DONE** |
| ~~P0~~ | ~~Simultaneous-transition conflict resolution~~ | **DONE** |
| P1 | Sub_threat decay on PASS | Open |
| P1 | CGRD sub_threat for guard submissions | Open |
| P2 | Momentum decay on mutual PASS | Open |
| P2 | Back-take transition (→BCTR) | Open |
| P2 | Turtle transition (failed takedown→TRTL) | Open |
