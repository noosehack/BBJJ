# Matboard Curriculum System — Full Briefing

Paste this into any LLM to explain the project. Everything below describes what's live at www.blawkops.com/dev/

---

## What This Is

A BJJ (Brazilian Jiu-Jitsu) curriculum system modeled as **graph traversal through constrained combat positions**. Instead of teaching techniques as isolated moves, the curriculum defines **roads** — multi-step paths through a position×action grid called the **matboard**. The system is designed for a 3-year white-to-purple progression.

The website at `/dev/` is an 8-page interactive visualization built with static HTML + JSON (no framework, no build system, served by nginx).

---

## Core Data Model

### Matboard
A grid of **7 fundamental positions × 4 action families**:

**Positions** (rows):
- **CGRD** — Closed Guard (defense tier)
- **OGRD** — Open Guard (defense tier, has subtopologies: DLR, RDLR, ColSlv, LassoSpider)
- **HGRD** — Half Guard (defense tier, has subtopologies: DpHalf, Lockdown, Knee Shield)
- **TRTL** — Turtle (defense tier)
- **SCTR** — Side Control (offense tier, has subtopologies: KoB, Kesa, North-South)
- **MNT** — Mount (offense tier, has subtopologies: Low, High, S-Mount)
- **BCTR** — Back Control (offense tier, has subtopologies: Hooks, BodyTri, Twister)

**Actions** (columns):
- **CTRL** — Control (stabilize the position)
- **TRZ** — Transition (move to a different position)
- **SWP** — Sweep (reverse top/bottom)
- **SUB** — Submission (finish)

A **matboard coordinate** looks like: `CGRD.CTRL`, `MNT.SUB`, `OGRD.ColSlv.CTRL`

### Roads
A **road** is a named sequence of matboard cells — a path through the grid. Each road has:
- **id**: S1–S9, B1–B8, N1–N7 (24 total)
- **tier**: spine, branch, or network
- **sequence**: ordered steps with position + action + detail text
- **matboard**: array of coordinates the road touches
- **checkpoints**: reusable structural concepts (control, stabilization, transition, submission)
- **failure topology**: what happens when the technique fails (safe / recoverable / risky)
- **duality**: what the opponent learns from this road (every road teaches attack AND defense)
- **mechanics**: reusable body movements (hip escape, bridge, underhook, etc.)
- **sources**: which BJJ knowledge graphs this road was derived from

### Road Tiers
- **Spine** (9 roads, Year 1 — Beginner): Linear sequences. Safe failure topology. Cover all 7 positions. Cognitive load is low — no decision trees.
- **Branch** (8 roads, Year 2 — Intermediate): Introduce new chains from familiar positions. Some recoverable failure paths.
- **Network** (7 roads, Year 3 — Advanced): Decision trees. Multiple branches based on opponent reaction. Risky failure possible.

### Checkpoints (19 total)
Reusable structural concepts that transfer across roads. Categories:
- **Control**: posture_break, mount_stabilization, crossface, underhook, seatbelt, collar_grip, guard_retention, weight_distribution, grip_fighting
- **Stabilization**: mount_stabilization, hook_insertion
- **Transition**: hip_escape, bridge, arm_isolation, knee_slice, off_balance, back_take_timing, angle_cutting, opponent_reading
- **Submission**: figure_four_lock

Each checkpoint lists which roads use it and how often it's reinforced.

### Dependency Graph
Roads have prerequisites. S1 is the root (no prerequisites). Most spine roads depend only on S1. Branch roads depend on 1-2 spine roads. Network roads depend on spine + branch roads. The deepest dependency chain is 4 levels.

### Curriculum Timeline
- Year 1 (Beginner): 9 spine roads across weeks 1–48. Covers 6 of 7 positions (TRTL is Year 2 only).
- Year 2 (Intermediate): 8 branch roads.
- Year 3 (Advanced): 7 network roads.

---

## The 24 Roads

### Spine Roads (Year 1)
- **S1**: Closed Guard Hip Bump Sweep to Mount Armbar (CGRD→MNT→MNT→MNT)
- **S2**: Closed Guard Arm Drag to Back Control RNC (CGRD→BCTR→BCTR→BCTR)
- **S3**: Half Guard Pass to Side Control Americana (HGRD→SCTR→SCTR→SCTR)
- **S4**: Mount Escape to Butterfly Sweep (MNT→OGRD→OGRD→MNT)
- **S5**: Open Guard Collar-Sleeve Sweep to Mount Cross Choke (OGRD→MNT→MNT→MNT)
- **S6**: Side Control Escape to Closed Guard (SCTR→HGRD→CGRD)
- **S7**: Closed Guard Triangle Choke (CGRD→CGRD→CGRD)
- **S8**: Mount Cross Choke with Americana Trap (MNT→MNT→MNT)
- **S9**: Collar-Sleeve Guard Pull to Closed Guard (OGRD.ColSlv→CGRD)

### Branch Roads (Year 2)
- **B1**: Butterfly Hook Sweep to Knee Cut Pass (OGRD→SCTR→SCTR)
- **B2**: Side Control to Back Take via Nearside Underhook (SCTR→BCTR→BCTR)
- **B3**: Open Guard Overhead Sweep to Mount (OGRD→MNT→MNT)
- **B4**: Side Control Americana-to-Armbar Chain (SCTR→SCTR→SCTR)
- **B5**: Closed Guard Kimura Sweep to Top Kimura (CGRD→MNT→MNT)
- **B6**: Turtle Breakdown to Back Control (TRTL→BCTR→BCTR)
- **B7**: De La Riva Sweep to Leg Drag Pass (OGRD→SCTR→SCTR)
- **B8**: Mount Escape Elbow-Knee to Half Guard Sweep (MNT→HGRD→HGRD)

### Network Roads (Year 3)
- **N1**: Butterfly Guard Decision Tree (OGRD→varies based on opponent reaction)
- **N2**: Mount Attack System (MNT→decision tree: armbar/choke/americana)
- **N3**: Back Attack System (BCTR→decision tree: RNC/armbar/collar choke)
- **N4**: Half Guard Passing Network (HGRD→multiple pass options)
- **N5**: Open Guard Retention System (OGRD→re-guard/sweep/submit based on pressure)
- **N6**: De La Riva/RDLR Guard System (OGRD→sweep/back take/submit)
- **N7**: Side Control Submission Network (SCTR→multiple attack chains)

---

## The 8 /dev Pages

### Original 3 Pages (dev.css styling)
1. **Matboard Viewer** (`index.html`): Interactive 7×4 grid. Click cells to see which roads touch them. Expandable subtopologies. Tooltip shows road count.
2. **Road Viewer** (`roads.html`): List of all 24 roads with tier filters. Click a road to highlight its path on the matboard with numbered steps. Detail panel shows sequence, sources, failure, duality, mechanics, checkpoints, branching.
3. **Curriculum Timeline** (`curriculum.html`): 3-year Gantt chart. Checkpoint library with category filters. Click timeline bars for road detail.

### Experimental 5 Pages (tac.css "combat terminal" styling)
4. **Lab / Operations Room** (`lab.html`): 4-quadrant synchronized dashboard. Multi-road overlay with checkboxes and preset groups (spine/branch/network/mount-focused/guard/back-control/safe-fail). Density markers on overlapping cells. Stats bar. All panels (matboard, sequence vectors, checkpoints, dependency graph, failure topology, curriculum timeline) sync when roads are toggled.
5. **Compare** (`compare.html`): Philosophy comparison matrix (GB, Roger Gracie, Danaher, AOJ, Matboard) across 8 dimensions with 1-5 conceptual ratings. Plus computed structural metrics section: road counts, cell coverage, action split, failure profile, checkpoint reuse, dependency depth.
6. **Spines** (`spines.html`): Spine road map with inline coordinate vectors. Click to trace path on matboard.
7. **Checkpoints** (`checkpoints.html`): Checkpoint explorer with category filters. Detail panel with definition, body concept, roads. Week-revisit timeline bars. Position reinforcement chart. Full 24-road × 19-checkpoint dot matrix.
8. **Paths** (`paths.html`): Path debugger. Select a road to trace its sequence step-by-step, see failure topology diagram, branching points, and dependency chain (prerequisites + unlocks).

---

## Design Philosophy

- **"Navigation through constrained combat graphs"** — BJJ positions are nodes, techniques are edges, curriculum is graph traversal
- **Visual aesthetic**: "combat systems terminal" — Bloomberg terminal, chess opening explorer, graph debugger. Monospace labels, thin borders, compact spacing, sparse. NOT a startup dashboard or flashy martial arts site.
- **Architecture**: Static HTML + vanilla JS + JSON data files. No framework, no build system. Served by nginx.
- **Duality principle**: Every road teaches both attack (Me perspective) and defense (Opponent perspective)
- **Failure topology**: Every road explicitly documents what happens when things go wrong — safe (return to known position), recoverable (fall to weaker but known position), risky (end up in bad position)
- **Checkpoint reuse**: The 19 checkpoints are structural concepts (like posture_break, underhook, hip_escape) that appear across multiple roads, creating reinforcement through repetition

---

## Data Sources

The road structures were synthesized from multiple BJJ knowledge graphs:
- BJJ Graph (knowledge graph of techniques)
- Flow State (transition data)
- FSM models (finite state machine position transitions)
- Gracie Barra GB1 curriculum (96 techniques)
- ViCoS BJJ dataset (position recognition, 120K frames)
- Various competition and instructional analysis
