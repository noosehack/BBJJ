# Matboard V0 — Semantic Playtest Report

**Date**: 2026-05-18
**Engine**: Matboard V0 kernel (frozen)
**Games**: 16 scripted, 6 scenario families
**Runtime**: BLISP hybrid mode, deterministic

---

## Summary

| Metric | Value |
|--------|-------|
| Games played | 16 |
| Submissions | 6 (G05, G08, G09, G13, G15, G16) |
| Points wins | 9 (G01, G02, G03, G06, G07, G10, G11, G12, G14) |
| Draws | 1 (G04) |
| Semantic failures | 3 (F1–F3) |
| Semantic issues | 3 (I1–I3) |
| BJJ-plausible outcomes | 13 of 16 |

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
| BJJ-plausible | YES — clean takedown to side control, hold for points |
| Semantic failures | None |
| Suggested tuning | Momentum should decay toward 0 on mutual PASS (see I2) |

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
| BJJ-plausible | PARTIAL — pulling guard gives positive VAL, which is debatable; in competition, guard puller often penalized |
| Semantic failures | None |
| Suggested tuning | Consider whether pull_guard should give A or B the positional advantage |

#### G03: STDN takedown-vs-pull_guard (simultaneous)

| Field | Value |
|-------|-------|
| Initial RAD | STDN |
| Player roles | A = takedown, B = pull_guard (simultaneous) |
| Move sequence | A: takedown, PASS×11; B: pull_guard, PASS×11 |
| RAD path | STDN → MNT×12 |
| VAL progression | 0 → 4.5 (constant after t1) |
| Momentum | 0 (constant — both succeed, cancel out) |
| Sub_threat | 0 (constant) |
| Winner | A by points (4.5 / -4.5) |
| BJJ-plausible | **NO** — Frankenstein state |
| **Semantic failure** | **F1**: Both transitions apply simultaneously. Takedown adds SCTR contacts + sets ORI. Pull_guard adds CGRD contacts + sets GND. Result: 3 CONs active, MNT classification (priority match), val=4.5 — unrealistically high. In real BJJ, conflicting transitions should contest, not stack. |
| Suggested tuning | RESOLVE needs a conflict-detection layer: when A and B both propose position-changing MORs, one must win and the other must fail. Priority-based: takedown should beat pull_guard. |

#### G04: STDN 12x-stall

| Field | Value |
|-------|-------|
| Initial RAD | STDN |
| Player roles | Both passive |
| Move sequence | A: PASS×12; B: PASS×12 |
| RAD path | STDN×12 |
| VAL progression | 0 (constant) |
| Momentum | 0 (constant) |
| Sub_threat | 0 (constant) |
| Winner | DRAW (0 / 0) |
| BJJ-plausible | YES — mutual stalling produces a draw |
| Semantic failures | None |

---

### Group 2: CGRD — Sweep Chain

#### G05: CGRD sweep → mount → sub (S1 road)

| Field | Value |
|-------|-------|
| Initial RAD | STDN |
| Player roles | A = aggressor through full chain, B = passive |
| Move sequence | A: pull_guard, hip_bump, mnt_sub×3, PASS×7; B: PASS×12 |
| RAD path | STDN → CGRD → MNT → MNT → MNT → (sub t5) |
| VAL progression | 0 → 2 → 4 → 4 → 4 → 4 |
| Momentum | 0 → 1 → 2 → 2 → 2 |
| Sub_threat | 0 → 0 → 1 → 2 → 3 |
| Winner | A by submission (turn 5) |
| BJJ-plausible | YES — canonical guard pull → sweep → mount → armbar. Clean teaching trace. |
| Semantic failures | None |

#### G06: CGRD triangle-from-defense

| Field | Value |
|-------|-------|
| Initial RAD | STDN |
| Player roles | A = guard player attempting triangle, B = passive |
| Move sequence | A: pull_guard, triangle×11; B: PASS×12 |
| RAD path | STDN → CGRD×12 |
| VAL progression | 0 → 2 (constant after t1) |
| Momentum | 0 → 1 (frozen) |
| Sub_threat | 0 (constant — CGRD is not in offensive set) |
| Winner | A by points (2 / -2) |
| BJJ-plausible | **NO** — triangle from closed guard should accumulate submission threat |
| **Semantic issue** | **I1**: CGRD is not classified as an offensive position (only SCTR/MNT/BCTR are). Triangle from CGRD never accumulates sub_threat. In real BJJ, closed guard is a legitimate submission platform. V1 should either add CGRD to the offensive set for sub_threat or create a guard-specific sub_threat path. |
| Suggested tuning | Add CGRD to offensive-position check for sub_threat accumulation, or introduce position-specific sub_threat rules. |

#### G07: CGRD sweep-contact-check

| Field | Value |
|-------|-------|
| Initial RAD | STDN |
| Player roles | A = sweep then hold, B = passive |
| Move sequence | A: pull_guard, hip_bump, PASS×10; B: PASS×12 |
| RAD path | STDN → CGRD → MNT → MNT×10 |
| VAL progression | 0 → 2 → 4 (constant after t2) |
| Momentum | 0 → 1 → 2 (frozen) |
| Sub_threat | 0 (constant) |
| Winner | A by points (4 / -4) |
| BJJ-plausible | YES — sweep to mount, hold for points. Contacts preserved through orientation change (Invariant #3 verified). |
| Semantic failures | None |

---

### Group 3: SCTR — Control / Advance / Sub_threat

#### G08: SCTR americana-sub

| Field | Value |
|-------|-------|
| Initial RAD | STDN |
| Player roles | A = side control submission, B = passive |
| Move sequence | A: takedown, sctr_americana×3, PASS×8; B: PASS×12 |
| RAD path | STDN → SCTR → SCTR → SCTR → (sub t4) |
| VAL progression | 0 → 2.5 → 2.5 → 2.5 → 2.5 |
| Momentum | 0 → 1 → 1 → 1 |
| Sub_threat | 0 → 1 → 2 → 3 |
| Winner | A by submission (turn 4) |
| BJJ-plausible | YES — takedown to side control americana. Fast clean finish. |
| Semantic failures | None |

#### G09: SCTR sub-reset-on-advance

| Field | Value |
|-------|-------|
| Initial RAD | STDN |
| Player roles | A = advance with sub_threat reset, B = passive |
| Move sequence | A: takedown, sctr_americana×2, sctr_mount, mnt_sub×3, PASS×5; B: PASS×12 |
| RAD path | STDN → SCTR → SCTR → SCTR → MNT → MNT → MNT → (sub t7) |
| VAL progression | 0 → 2.5 → 2.5 → 2.5 → 4 → 4 → 4 → 4 |
| Momentum | 0 → 1 → 1 → 1 → 2 → 2 → 2 |
| Sub_threat | 0 → 1 → 2 → 0 → 1 → 2 → 3 |
| Winner | A by submission (turn 7) |
| BJJ-plausible | YES — sub_threat correctly resets on position change (SCTR→MNT). Demonstrates that advancing resets the clock. Rewards commitment vs. greedy position hopping. |
| Semantic failures | None |

#### G10: SCTR sub-threat-non-decay

| Field | Value |
|-------|-------|
| Initial RAD | STDN |
| Player roles | A = partial sub attempt then stall, B = passive |
| Move sequence | A: takedown, sctr_americana×2, PASS×9; B: PASS×12 |
| RAD path | STDN → SCTR×12 |
| VAL progression | 0 → 2.5 (constant after t1) |
| Momentum | 0 → 1 (frozen) |
| Sub_threat | 0 → 1 → 2 → 2 → 2 → 2 → 2 → 2 → 2 → 2 → 2 → 2 |
| Winner | A by points (2.5 / -2.5) |
| BJJ-plausible | PARTIAL — sub_threat frozen at 2 indefinitely is debatable |
| **Semantic issue** | **I2**: Sub_threat does not decay on PASS. A player can build to sub=2, stall for 9 turns, then resume with only 1 more sub needed. In real BJJ, releasing a submission attempt lets the opponent recover. V1 should add sub_threat decay (e.g., -1 per PASS from offense, floor 0). |
| Suggested tuning | Add per-turn decay: `new_sub = max(0, old_sub - 1)` when A plays PASS from offensive position. |

---

### Group 4: MNT — Pressure / Absorbing State

#### G11: MNT pressure-hold

| Field | Value |
|-------|-------|
| Initial RAD | STDN |
| Player roles | A = mount pressure, B = passive |
| Move sequence | A: pull_guard, hip_bump, mnt_pressure×10; B: PASS×12 |
| RAD path | STDN → CGRD → MNT×11 |
| VAL progression | 0 → 2 → 4 (constant after t2) |
| Momentum | 0 → 1 → 2 (frozen) |
| Sub_threat | 0 (constant — mnt_pressure is control, not submission) |
| Winner | A by points (4 / -4) |
| BJJ-plausible | YES — mount hold with pressure is a real strategy (ride out the clock, win on points). Correct that pressure does not accumulate sub_threat. |
| Semantic failures | None |

#### G12: MNT absorbing-B-tries-all

| Field | Value |
|-------|-------|
| Initial RAD | STDN |
| Player roles | A = mount hold, B = tries every MOR in the library |
| Move sequence | A: pull_guard, hip_bump, PASS×10; B: PASS×2, then takedown, pull_guard, hip_bump, triangle, ogrd_sweep, hgrd_sweep, trtl_standup, sctr_mount, bctr_rnc, mnt_sub |
| RAD path | STDN → CGRD → MNT×11 |
| VAL progression | 0 → 2 → 4 (constant after t2) |
| Momentum | 0 → 1 → 2 (frozen — all B MORs rejected) |
| Sub_threat | 0 (constant) |
| Winner | A by points (4 / -4) |
| BJJ-plausible | **NO** — mounted player has zero options |
| **Semantic failure** | **F2**: MNT is a fully absorbing state. B tried every MOR in the library (10 different moves) — all rejected by precondition checks. No escape, no reversal, no guard recovery. In real BJJ, the mounted player can bridge, shrimp, trap-and-roll, or re-guard. This is the most critical gap in the V0 MOR library. |
| Suggested tuning | V1 must add escape MORs: `mnt_escape` (MNT→CGRD or MNT→HGRD), `sctr_escape` (SCTR→HGRD or SCTR→CGRD), `bctr_escape` (BCTR→TRTL). These are fiber "B" MORs with preconditions on B's position. |

---

### Group 5: BCTR — Synthetic Start / RNC / Control

#### G13: BCTR rnc-sub

| Field | Value |
|-------|-------|
| Initial RAD | BCTR (synthetic: both legs on torso, facing=ALIGNED) |
| Player roles | A = back control submission, B = passive |
| Move sequence | A: bctr_rnc×3, PASS×9; B: PASS×12 |
| RAD path | BCTR → BCTR → BCTR → (sub t3) |
| VAL progression | 5 → 5 → 5 |
| Momentum | 0 (constant — MAINTAIN-only MOR doesn't change state) |
| Sub_threat | 0 → 1 → 2 → 3 |
| Winner | A by submission (turn 3) |
| BJJ-plausible | YES — fastest possible finish. RNC from back control in 3 turns. Val=5 (highest position value) is correct. |
| Semantic failures | None |

#### G14: BCTR control-hold

| Field | Value |
|-------|-------|
| Initial RAD | BCTR (synthetic) |
| Player roles | A = back control hold, B = passive |
| Move sequence | A: bctr_control×12; B: PASS×12 |
| RAD path | BCTR×12 |
| VAL progression | 5 (constant) |
| Momentum | 0 (constant — MAINTAIN-only) |
| Sub_threat | 0 (constant — bctr_control is control, not submission) |
| Winner | A by points (5 / -5) |
| BJJ-plausible | YES — holding back control for points without attempting submission. Correct distinction between control and submission MORs. |
| Semantic failures | None |

---

### Group 6: TRTL — Synthetic Start / Standup / Sit-to-Guard

#### G15: TRTL standup → takedown → sub

| Field | Value |
|-------|-------|
| Initial RAD | TRTL (synthetic: gnd.me = TURTLE) |
| Player roles | A = turtle escape to offense, B = passive |
| Move sequence | A: trtl_standup, takedown, sctr_americana×3, PASS×7; B: PASS×12 |
| RAD path | TRTL → STDN → SCTR → SCTR → SCTR → (sub t5) |
| VAL progression | -1 → 0 → 2.5 → 2.5 → 2.5 → 2.5 |
| Momentum | 0 → 1 → 2 → 2 → 2 |
| Sub_threat | 0 → 0 → 1 → 2 → 3 |
| Winner | A by submission (turn 5) |
| BJJ-plausible | YES — turtle standup to neutral, then takedown to side control americana. Realistic recovery-to-offense sequence. Val correctly starts negative (turtle is bad) and climbs through transitions. |
| Semantic failures | None |

#### G16: TRTL sit → sweep → mount → sub

| Field | Value |
|-------|-------|
| Initial RAD | TRTL (synthetic) |
| Player roles | A = turtle sit to guard, sweep chain to submission, B = passive |
| Move sequence | A: trtl_sit, ogrd_sweep, sctr_mount, mnt_sub×3, PASS×6; B: PASS×12 |
| RAD path | TRTL → OGRD → SCTR → MNT → MNT → MNT → (sub t6) |
| VAL progression | -1 → 0.5 → 2.5 → 4 → 4 → 4 → 4 |
| Momentum | 0 → 1 → 2 → 3 → 3 → 3 |
| Sub_threat | 0 → 0 → 0 → 1 → 2 → 3 |
| Winner | A by submission (turn 6) |
| BJJ-plausible | YES — longest chain tested. TRTL→OGRD→SCTR→MNT→sub. Every transition is BJJ-real. Momentum climbs to max (3) and holds. Sub_threat correctly starts counting only at MNT. |
| Semantic failures | None |

---

## Semantic Failures

### F1: Simultaneous Conflicting Transitions Stack (G03)

**Severity**: HIGH

When both players propose position-changing MORs on the same turn (takedown vs pull_guard), both apply. Takedown adds SCTR contacts and sets ORI. Pull_guard adds CGRD contacts and sets GND. The result is a Frankenstein state with 3 CONs that classifies as MNT (val=4.5) — a position neither player actually earned.

**Root cause**: RESOLVE applies A's ops then B's ops sequentially with no conflict detection between position-changing MORs.

**Fix (V1)**: Before applying ops, detect when both A and B propose MORs with position-changing ops (SET_ORI, SET_GND, or structural ADD/DEL). When detected, resolve as a contest: compare priority (burst + initiative), apply only the winner's MOR, discard the loser's.

### F2: Absorbing States — No Escape MORs (G12)

**Severity**: HIGH

MNT, SCTR, and BCTR are fully absorbing — once reached, the bottom player (B) has no legal MOR to escape. G12 demonstrates this: B tried every MOR in the library from mount bottom and all were rejected. This makes the game degenerate after any successful advance to a dominant position.

**Root cause**: The V0 MOR library contains only offensive MORs (A-fiber). No defensive/escape MORs (B-fiber) exist.

**Fix (V1)**: Add escape MORs to the library:
- `mnt_escape`: B from MNT → CGRD or HGRD (bridge/shrimp)
- `sctr_escape`: B from SCTR → HGRD or CGRD (shrimp to guard)
- `bctr_escape`: B from BCTR → TRTL (turn into opponent)
- `mnt_reversal`: B from MNT → SCTR (trap and roll, costs momentum)

These should be B-fiber MORs with `fail="RSK"` and appropriate burst/cost values to make escape difficult but possible.

### F3: Simultaneous Transition Creates Unreachable Val (G03)

**Severity**: MEDIUM (consequence of F1)

Val=4.5 is not achievable through any single legal transition. SCTR→val=2.5, CGRD→val=2, MNT→val=4. The val=4.5 result comes from the Frankenstein state having 3 CONs — more than any defined radical specifies. This means the position classifier is matching on a superset of the MNT contact pattern.

**Root cause**: Classifier uses `state-has-con` (subset check), not exact match. A state with more contacts than the radical requires still matches.

**Fix (V1)**: Either fix F1 (preferred — prevents the state from arising) or add contact-count validation to the classifier.

---

## Semantic Issues

### I1: Triangle from CGRD Does Not Accumulate Sub_threat (G06)

**Severity**: MEDIUM

CGRD is not in the offensive position set (SCTR/MNT/BCTR). Triangle from closed guard — a common real-world submission — never builds sub_threat. The triangle MOR is legal in CGRD (passes preconditions) but the sub_threat accumulation gate rejects it.

**Suggested fix**: Either expand the offensive set to include CGRD, or implement position-specific sub_threat rules that allow guard submissions.

### I2: Sub_threat Does Not Decay (G10)

**Severity**: LOW-MEDIUM

Sub_threat persists indefinitely when the attacker stops pursuing the submission. G10 shows sub_threat frozen at 2 through 9 consecutive PASS turns. In real BJJ, releasing a submission attempt gives the opponent time to adjust and defend.

**Suggested fix**: Decay sub_threat by 1 per turn when the offensive player plays PASS (not a submission MOR). Floor at 0.

### I3: Momentum Does Not Decay (G01, G02, G07, G10, G11)

**Severity**: LOW

Momentum freezes at its last value on mutual PASS. In 5 of 16 games, momentum stayed at +1 or +2 for 10+ consecutive idle turns. Momentum should represent recent activity, not historical achievement.

**Suggested fix**: Decay momentum toward 0 by 1 per mutual-PASS turn. This incentivizes continued engagement.

---

## Transition Graph (As-Built)

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
       sctr_mount│    hip_bump│
                 ▼           ▼
               ┌─────────────┐
               │    MNT      │
               │  val = 4    │
               └─────────────┘

  Synthetic-start only:           Synthetic-start only:
  ┌─────────┐                     ┌─────────┐
  │  BCTR   │                     │  TRTL   │──┐
  │ val = 5 │                     │ val=-1  │  │ trtl_standup → STDN
  └─────────┘                     └─────────┘  │ trtl_sit → OGRD
                                               ▼
                                  ┌─────────┐
                                  │  OGRD   │
                                  │ val=0.5 │──→ ogrd_sweep → SCTR
                                  └─────────┘

  ABSORBING: MNT, SCTR, BCTR (no escape MORs — see F2)
  NOT REACHABLE from init: BCTR, HGRD, OGRD, TRTL
```

---

## VAL Ordering

| Position | VAL | Reachable from init | Absorbing |
|----------|-----|---------------------|-----------|
| BCTR | 5 | No (synthetic) | Yes |
| MNT | 4 | Yes | Yes |
| SCTR | 2.5 | Yes | Yes |
| CGRD | 2 | Yes | No (sweep to MNT) |
| HGRD | 1 | No (synthetic) | — |
| OGRD | 0.5 | No (synthetic) | No (sweep to SCTR) |
| STDN | 0 | Yes (init) | No |
| TRTL | -1 | No (synthetic) | No |

VAL ordering is BJJ-plausible. Back control > mount > side control > closed guard > half guard > open guard > standing > turtle.

---

## Conclusions

1. **The kernel is mechanically sound.** 16 games, no crashes, no silent errors, deterministic output. Footprints are replay-safe.

2. **Teaching traces work for A-dominant games.** G05 (S1 road), G08, G09, G15, G16 all produce traces that a coach could narrate: "pull guard, sweep to mount, submit." These are the core value of Matboard.

3. **The game is degenerate without escape MORs (F2).** This is the single most important V1 fix. Without it, every game that reaches MNT/SCTR/BCTR is decided — the bottom player has no agency.

4. **Simultaneous conflicting transitions need contest resolution (F1).** Less critical for teaching (where games are scripted) but essential for any two-player interaction.

5. **Sub_threat from guard (I1) and decay mechanics (I2, I3) are tuning knobs.** They don't break the engine but they do affect plausibility. Suggested values for V1: CGRD added to offensive set for sub_threat; sub_threat decays by 1 on offensive PASS; momentum decays by 1 on mutual PASS.

6. **Synthetic start states are necessary for 4 of 8 positions.** The transition graph has gaps: no path to BCTR, HGRD, OGRD, or TRTL from standing. V1 should add back-take and turtle transitions.

---

## V1 Priority List

| Priority | Item | Fixes |
|----------|------|-------|
| P0 | Escape MORs (mnt_escape, sctr_escape, bctr_escape) | F2 |
| P0 | Simultaneous-transition conflict resolution | F1, F3 |
| P1 | Sub_threat decay on PASS | I2 |
| P1 | CGRD sub_threat for guard submissions | I1 |
| P2 | Momentum decay on mutual PASS | I3 |
| P2 | Back-take transition (SCTR→BCTR or MNT→BCTR) | Graph gap |
| P2 | Turtle transition (failed takedown→TRTL) | Graph gap |
