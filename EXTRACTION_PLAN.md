# BJJ Graph Library — Extraction Plan

## Corrected Positional Hierarchy

```
DEFENSE LAYERS                              PASS TERRITORY
Line 1: OGRD  — both legs free              SCTR — torso control from side
Line 2: CGRD  — both legs enclose hips      MNT  — straddle from above
Line 3: HGRD  — one leg trapped/penetrated  BCTR — chest-to-back behind
Shell:  TRTL  — guard failed
```

CGRD > HGRD because closed guard still fully encloses the hips.
Half guard has one leg already penetrated — closer to being passed.

---

## Milestones

### Milestone 1 — Data Acquisition
Download each source, preserve original structure, keep sources isolated.

### Milestone 2 — Minimal Structuring
Parse into queryable format: positions, transitions, submissions, sweeps, paths.
No ontology reconciliation. Original names preserved.

### Milestone 3 — Candidate Road Extraction
Extract all possible roads from parsed data, cross-source matching,
score and rank candidates. Output: candidate_roads.json + report.

### Milestone 4 — Curriculum Spine Selection
Select ~25 canonical roads (not the full graph). Map only those to the
fieldboard. Analyze checkpoints, failure topology, classify into
spine / branch / network. This is NOT graph completion — it is
pedagogical filtering.

### Milestone 4 — Curriculum-First Mapping
Map only selected pedagogical roads into (Position, SubTopology, Action).
Not the entire graph. Only useful roads.

### Milestone 5 — Curriculum Sequencing Engine
Transform selected roads into a coherent yearly teaching structure,
ordered by pedagogical dependency, checkpoint stability, reusable
mechanics, and duality progression. Output: road dependency graph,
curriculum ordering, year plan, checkpoint library.

---

## Milestone 1: Data Acquisition

### Directory Structure

```
BBJJ/
  fieldboard/
    data/
      grapplemap/          # Eelis/GrappleMap
        raw/               # Original files as downloaded
        parsed/            # Milestone 2 output
      bjjgraph/            # diogoseca/bjjgraph
        raw/
        parsed/
      bjj_graph_clj/       # daveyarwood/bjj-graph
        raw/
        parsed/
      flowstate/           # iphoenix227/Flow-State
        raw/
        parsed/
      cavani/              # fcavani/jiu-jitsu-graph
        raw/
        parsed/
    extract/               # Parser scripts (one per source)
```

Each source stays in its own directory. No merging.

### Source 1: GrappleMap

| Field | Value |
|-------|-------|
| Repo | `https://github.com/Eelis/GrappleMap` |
| License | Public Domain |
| Data file | `GrappleMap.txt` (2.67 MB, ~39K lines) |
| Positions | ~601 |
| Transitions | ~1,485 |
| Tags | 161 unique |

**What to download**:
```bash
git clone --depth 1 https://github.com/Eelis/GrappleMap.git \
  fieldboard/data/grapplemap/raw/repo
```

**Key file**: `GrappleMap.txt` — custom plaintext format.

**Format**:
- Entry = name line(s) + optional tags/properties/refs + indented data lines
- 1 frame (4 data lines) = position node
- N frames (4N data lines) = transition edge
- Tags are flat strings: `full_guard`, `half_guard`, `sweep`, `armbar`, etc.
- Properties: `top`, `bottom`, `sweep`, `bidirectional`
- First/last frames of transitions match position nodes (graph topology)
- Data lines are base-62 encoded 3D joint coordinates (2 players × 23 joints)

**What matters for us**:
- Position names + tags (what position is this?)
- Transition names + tags + properties (what technique? who moves? sweep?)
- from/to topology (which position → which position?)
- References (instructional citations — 1,058 of them)

**What we skip for now**:
- 3D coordinate decoding (useful later, not for Milestone 1-2)

### Source 2: bjjgraph (diogoseca)

| Field | Value |
|-------|-------|
| Repo | `https://github.com/diogoseca/bjjgraph` |
| License | PolyForm Noncommercial 1.0.0 |
| Data | Individual JSON files in Obsidian vault |
| Positions | 140 |
| Transitions | 1,072 |
| Submissions | 153 |

**What to download**:
```bash
git clone --depth 1 https://github.com/diogoseca/bjjgraph.git \
  fieldboard/data/bjjgraph/raw/repo
```

**Key directory**: `content/` — contains `Positions/`, `Transitions/`, `Submissions/`, `Principles/`, `Systems/`

**Position JSON** (already structured):
```json
{
  "name": "Closed Guard",
  "slug": "closed-guard",
  "top": {
    "state_properties": {"position_type": "Defensive", "risk_level": "Medium"},
    "transitions": [{"transition": "Posture Recovery", "attempt_probability": 32}],
    "decision_tree": [...]
  },
  "bottom": { ... }
}
```

**Transition JSON**:
```json
{
  "name": "Americana",
  "from_position": "Side Control/Top",
  "outcomes": [
    {"to": "game-over", "probability": 55, "result": "success"},
    {"to": "Side Control/Top", "probability": 30, "result": "failure"},
    {"to": "Half Guard/Bottom", "probability": 15, "result": "counter"}
  ]
}
```

**What matters**: Already has perspective (`/Top`, `/Bottom`), probability weights, decision trees, outcome distributions. Richest metadata of any source.

### Source 3: bjj-graph (daveyarwood)

| Field | Value |
|-------|-------|
| Repo | `https://github.com/daveyarwood/bjj-graph` |
| License | None specified |
| Data | Clojure maps in `src/bjj_graph/v2.clj` |
| Positions | ~88 |
| Edges | ~200 |
| Submissions | ~12 terminal nodes |

**What to download**:
```bash
git clone --depth 1 https://github.com/daveyarwood/bjj-graph.git \
  fieldboard/data/bjj_graph_clj/raw/repo
```

**Key file**: `src/bjj_graph/v2.clj`

**Format** (Clojure map):
```clojure
"Guard"
{::transitions  ["Punch Block Stage 1.5" "Punch Block Stage 3"]
 "Hand on chest" "Straight Armlock (Guard)"
 "Upper body crush" "Giant Killer"}
```

- `::transitions` = unlabeled edges (positional transitions)
- Other key-value pairs = labeled edges (technique name → target position)
- `::submission? true` = terminal node

**What matters**: Based on Gracie Combatives — represents a well-known pedagogical path. Good for path extraction and beginner road validation.

### Source 4: Flow-State

| Field | Value |
|-------|-------|
| Repo | `https://github.com/iphoenix227/Flow-State---BJJ-Attack-Decision-Map` |
| License | None specified |
| Data | TypeScript arrays in `src/data/` |
| Positions | 16 |
| Actions | 169 |
| Edges | 525 |

**What to download**:
```bash
git clone --depth 1 \
  https://github.com/iphoenix227/Flow-State---BJJ-Attack-Decision-Map.git \
  fieldboard/data/flowstate/raw/repo
```

**Key files**: `src/data/positions.ts`, `src/data/edges.ts`, `src/data/attackingMap.ts`

**Edge schema** (TypeScript):
```typescript
{
  node_id: "CG-A-hip-bump-sweep",
  from_node_id: "CG-ROOT",
  next_node_id: "MNT-ROOT",
  outcome_type: "Sweep",
  gi_no_gi: "Both",
  skill_level: "White",
  chain_family: "hip_bump_chain",
  concept_tags: ["posture_breaking", "momentum"],
  grip_tags: ["collar_grip", "wrist_grip"]
}
```

**What matters**: `outcome_type` (Sweep/Submission/Takedown/Transition), `chain_family` (game paths), `skill_level`, `concept_tags`, `grip_tags`. Best edge metadata.

### Source 5: fcavani/jiu-jitsu-graph (small, validation only)

| Field | Value |
|-------|-------|
| Repo | `https://github.com/fcavani/jiu-jitsu-graph` |
| License | CC BY-NC 4.0 |
| Data | RDF N-Quad files |
| Positions | 11 |
| Moves | 38 |

**What to download**:
```bash
git clone --depth 1 https://github.com/fcavani/jiu-jitsu-graph.git \
  fieldboard/data/cavani/raw/repo
```

Has move classification (`sweep`, `submission`, `transition`, `pass`) and a training progression graph. Small but clean.

### Source 6: Graphling / BJJML

No public repository found. Exists only as Medium blog posts describing a theoretical framework using FSMs and Statecharts. Position notation is a quadruple `(Family, State, Upper, Lower)`. Backend described as Django + PostgreSQL but never published.

**Action**: Skip for Milestone 1. Revisit if a repo surfaces.

### Download Script

```bash
#!/bin/bash
# fieldboard/download.sh
set -e

BASE="fieldboard/data"
mkdir -p "$BASE"

echo "=== GrappleMap ==="
git clone --depth 1 https://github.com/Eelis/GrappleMap.git \
  "$BASE/grapplemap/raw/repo" 2>/dev/null || echo "already cloned"

echo "=== bjjgraph ==="
git clone --depth 1 https://github.com/diogoseca/bjjgraph.git \
  "$BASE/bjjgraph/raw/repo" 2>/dev/null || echo "already cloned"

echo "=== bjj-graph (Clojure) ==="
git clone --depth 1 https://github.com/daveyarwood/bjj-graph.git \
  "$BASE/bjj_graph_clj/raw/repo" 2>/dev/null || echo "already cloned"

echo "=== Flow-State ==="
git clone --depth 1 \
  https://github.com/iphoenix227/Flow-State---BJJ-Attack-Decision-Map.git \
  "$BASE/flowstate/raw/repo" 2>/dev/null || echo "already cloned"

echo "=== fcavani ==="
git clone --depth 1 https://github.com/fcavani/jiu-jitsu-graph.git \
  "$BASE/cavani/raw/repo" 2>/dev/null || echo "already cloned"

echo "Done. Sources in $BASE/*/raw/repo/"
```

---

## Milestone 2: Minimal Structuring

One parser per source. Each parser reads raw data and writes a simple JSON
to `parsed/`. No cross-source merging. No ontology mapping.

### Common Output Schema

Every parser outputs two files: `positions.json` and `edges.json`.

**positions.json** — list of position nodes:
```json
[
  {
    "id": "gm_42",
    "name": "full guard",
    "source": "grapplemap",
    "tags": ["full_guard", "bottom_supine", "top_kneeling"],
    "properties": {},
    "raw": {}
  }
]
```

**edges.json** — list of transition/technique edges:
```json
[
  {
    "id": "gm_e_301",
    "name": "hip bump sweep",
    "source": "grapplemap",
    "from_id": "gm_42",
    "from_name": "full guard",
    "to_id": "gm_15",
    "to_name": "mount",
    "edge_type": "sweep",
    "tags": ["sweep"],
    "properties": {},
    "raw": {}
  }
]
```

`edge_type` uses only these values, inferred from source-native labels:
- `transition` — general position change
- `sweep` — reversal of top/bottom
- `submission` — terminal (to = "game-over" or similar)
- `escape` — defense to better position
- `pass` — guard → pass territory
- `unknown` — source doesn't classify it

The `raw` field preserves any source-specific data we don't want to lose
(probabilities, decision trees, grip tags, etc.).

### Parser: GrappleMap (`extract/grapplemap.py`)

```
Input:  grapplemap/raw/repo/GrappleMap.txt
Output: grapplemap/parsed/positions.json
        grapplemap/parsed/edges.json

Algorithm:
1. Split file into entries by detecting name lines
   (no leading whitespace, not tag/property/ref/note)
2. For each entry:
   - Parse name (may span multiple lines joined by \n)
   - Parse tags: "tags: a b c" → ["a", "b", "c"]
   - Parse properties: "properties: top sweep" → ["top", "sweep"]
   - Parse refs: "ref: ..." → [str]
   - Count data line groups (4 lines = 1 frame)
   - 1 frame → position node
   - >1 frames → transition edge
3. For transitions: determine from/to by matching first/last
   frame data against known position frame data (exact string match)
4. Classify edge_type:
   - "sweep" in properties → "sweep"
   - name contains submission keywords → "submission"
   - else → "transition"
5. Write positions.json, edges.json
```

### Parser: bjjgraph (`extract/bjjgraph.py`)

```
Input:  bjjgraph/raw/repo/content/Positions/*.json
        bjjgraph/raw/repo/content/Transitions/*.json
        bjjgraph/raw/repo/content/Submissions/*.json
Output: bjjgraph/parsed/positions.json
        bjjgraph/parsed/edges.json

Algorithm:
1. Walk Positions/, load each JSON
   - Store name, slug, top/bottom state_properties
   - Preserve transitions list and decision_tree in raw
2. Walk Transitions/, load each JSON
   - Parse from_position (strip /Top or /Bottom suffix)
   - For each outcome: create edge to outcome.to
   - edge_type from outcome.result: "success" → check if game-over
   - Preserve probabilities, conditions, variants in raw
3. Walk Submissions/, load each JSON
   - edge_type = "submission"
   - to = "game-over"
4. Write positions.json, edges.json
```

### Parser: bjj-graph Clojure (`extract/bjj_graph_clj.py`)

```
Input:  bjj_graph_clj/raw/repo/src/bjj_graph/v2.clj
Output: bjj_graph_clj/parsed/positions.json
        bjj_graph_clj/parsed/edges.json

Algorithm:
1. Read v2.clj as text
2. Regex-parse the top-level Clojure map:
   - Position names are quoted strings
   - ::transitions → vector of target names (unlabeled edges)
   - ::submission? → terminal flag
   - Other keys → technique:target pairs (labeled edges)
3. Build position list from all unique names
4. Build edge list:
   - ::transitions entries → edge_type = "transition"
   - technique→target pairs → edge_type from name heuristic
   - targets with ::submission? → edge_type = "submission"
5. Write positions.json, edges.json
```

### Parser: Flow-State (`extract/flowstate.py`)

```
Input:  flowstate/raw/repo/src/data/positions.ts
        flowstate/raw/repo/src/data/edges.ts
        flowstate/raw/repo/src/data/attackingMap.ts
Output: flowstate/parsed/positions.json
        flowstate/parsed/edges.json

Algorithm:
1. Strip TypeScript type annotations from each file
   (remove "export const X: Type[] = " prefix, trailing ";")
2. Parse remaining JSON arrays
3. Positions: {position_id, position_name, position_family}
4. Edges from edges.ts: {node_id, from_node_id, next_node_id,
   edge_label, outcome_type, ...}
5. Enrich edges with attackingMap.ts data (join on node_id):
   {gi_no_gi, skill_level, concept_tags, chain_family, grip_tags}
6. Map outcome_type to edge_type:
   "Sweep" → "sweep", "Submission" → "submission",
   "Takedown" → "transition", "Transition" → "transition"
7. Preserve all extra fields in raw
8. Write positions.json, edges.json
```

### Parser: fcavani (`extract/cavani.py`)

```
Input:  cavani/raw/repo/*.rdf
Output: cavani/parsed/positions.json
        cavani/parsed/edges.json

Algorithm:
1. Parse N-Quad triples: _:subject <predicate> "object" .
2. Build entity map from triples
3. Filter by dgraph.type == "Position" or "Move"
4. For moves: read "class" field → edge_type mapping:
   "sweep" → "sweep", "submission" → "submission",
   "transition"/"pass" → "transition", "escape" → "escape"
5. Write positions.json, edges.json
```

### What Each Parser Preserves

| Source | Positions | Edges | Extra preserved in `raw` |
|--------|-----------|-------|--------------------------|
| GrappleMap | name, tags, frame data hash | name, tags, properties, refs, from/to | 3D frame data (as string), line numbers |
| bjjgraph | name, slug, top/bottom properties | name, from, outcomes, conditions | probabilities, decision_tree, variants |
| bjj-graph-clj | name, submission flag | technique name, from, to | — |
| Flow-State | name, family | name, from, to, outcome_type | skill_level, gi/nogi, chain_family, concept_tags, grip_tags |
| fcavani | name, type, points | name, class, to, points | multilingual names (pt/en) |

---

## Milestone 3: Candidate Road Extraction

**Prerequisite**: Milestone 2 complete (all `parsed/` directories populated).

**Output**: `fieldboard/data/candidate_roads.json` + `fieldboard/data/candidate_roads_report.md`

This milestone does NOT produce final curriculum. It produces an exploration
artifact: a ranked list of candidate roads for human review.

### Candidate Road Schema

```json
{
  "name": "Closed guard scissor sweep to mount",
  "source_paths": [
    {
      "source": "grapplemap",
      "raw_sequence": ["closed guard", "scissor sweep", "mount"]
    },
    {
      "source": "bjjgraph",
      "raw_sequence": ["Closed Guard/Bottom", "Scissor Sweep", "Mount/Top"]
    }
  ],
  "source_count": 2,
  "sequence_length": 3,
  "control_checkpoints": [
    "closed guard posture control",
    "mount stabilization"
  ],
  "branching_notes": "short path, low decision load",
  "beginner_reason": "clear control → sweep → dominant position sequence",
  "fieldboard_hint": ["CGRD.CTRL", "CGRD.SWP", "MNT.CTRL"],
  "score": 4.5,
  "status": "candidate"
}
```

Fields:
- `name`: human-readable label (not canonical — just descriptive)
- `source_paths`: raw sequences as they appear in each source, preserving original names
- `source_count`: how many sources contain this road (or a close variant)
- `sequence_length`: number of steps
- `control_checkpoints`: positions in the sequence where CTRL is implied (stable holds before advancing)
- `branching_notes`: free text — how many alternatives exist at each step
- `beginner_reason`: why this road looks pedagogically useful (or empty if unclear)
- `fieldboard_hint`: lightweight hint toward our ontology — NOT a binding mapping, just a suggestion for Milestone 4
- `score`: simple numeric score (see below)
- `status`: always `"candidate"` at this stage

### Scoring

Simple formula, no fake empirical probabilities:

```
score = source_count × 2.0
      + control_checkpoint_count × 1.5
      - sequence_length_penalty
      - branching_complexity_penalty
```

Where:
- `source_count`: number of sources containing this road (1–5)
- `control_checkpoint_count`: number of stable positions in the sequence where CTRL makes sense
- `sequence_length_penalty`: `max(0, sequence_length - 5) × 0.5` (no penalty ≤5 steps, 0.5 per step beyond)
- `branching_complexity_penalty`: average out-degree at each position in the path, scaled: `avg_out_degree × 0.3`

The score is a rough ordering signal, not ground truth. It exists so the
report can sort candidates and a human can scan from top to bottom.

### Road Extraction Logic (`fieldboard/extract_roads.py`)

```
Input:  all parsed/edges.json files
Output: fieldboard/data/candidate_roads.json
        fieldboard/data/candidate_roads_report.md

Algorithm:

1. Load all edges from all sources into a unified edge list
   (still preserving source field — no merging of names)

2. Build per-source adjacency graphs:
   adj[source][from_name] → [(edge_name, to_name, edge_type)]

3. Identify "guard-like" start positions per source:
   Names containing: guard, butterfly, dlr, half, turtle, seated
   (loose string matching — not ontology)

4. Identify "finish" edges per source:
   edge_type == "submission"

5. Per source: BFS/DFS from each guard-like start, max depth 10
   Collect all paths that reach a submission edge
   Also collect paths that reach dominant positions
   (names containing: mount, side control, back control, knee on belly)

6. Deduplicate within source:
   Two paths are "same road" if their position sequence matches
   after lowercasing and stripping minor variants

7. Cross-source matching:
   Two roads from different sources are "same road" if their
   position sequences align after fuzzy name matching:
   - "full guard" ≈ "Closed Guard" ≈ "Guard"
   - "mount" ≈ "Mount/Top" ≈ "Mount"
   Use a small alias table (not full ontology — just ~30 obvious aliases)

8. For each unique road:
   a. Count source_count
   b. Identify control checkpoints:
      positions that are known stable holds (guard, mount, side control, back)
   c. Compute branching_notes from avg out-degree at each step
   d. Generate fieldboard_hint by loose keyword matching:
      "closed guard" → "CGRD", "mount" → "MNT", "sweep" → "SWP", etc.
   e. Compute score
   f. If sequence_length ≤ 6 and has ≥1 control checkpoint:
      set beginner_reason

9. Sort by score descending
10. Write candidate_roads.json (all candidates)
11. Write candidate_roads_report.md (top 20 for human review)
```

### Alias Table (for cross-source matching only — NOT ontology)

```python
POSITION_ALIASES = {
    "full guard":       "closed guard",
    "guard":            "closed guard",
    "half guard top":   "half guard",
    "half guard bottom":"half guard",
    "side mount":       "side control",
    "cross side":       "side control",
    "rear mount":       "back control",
    "back mount":       "back control",
    "back":             "back control",
    "low mount":        "mount",
    "high mount":       "mount",
    "s-mount":          "mount",
    "north south":      "north-south",
    "scarf hold":       "kesa gatame",
}
```

This table is intentionally small and conservative. It only exists to detect
"same road, different naming" across sources. It does NOT resolve into our
fundamental positions — that happens in Milestone 4.

### Report Format (`candidate_roads_report.md`)

```markdown
# Candidate Roads — Top 20

Generated: 2026-05-16
Sources: grapplemap (601 pos, 1485 edges), bjjgraph (140 pos, 1072 edges), ...

## Road 1: Closed Guard → Scissor Sweep → Mount → Armbar
- Score: 7.5
- Sources: grapplemap, bjjgraph, flowstate (3/5)
- Length: 4 steps
- Control checkpoints: closed guard posture, mount stabilization
- Branching: low (2-3 alternatives at each step)
- Beginner: yes — classic control → sweep → dominant → finish
- Hint: CGRD.CTRL → CGRD.SWP → MNT.CTRL → MNT.SUB

## Road 2: Butterfly Guard → Hook Sweep → Side Control → Americana
- Score: 6.0
- Sources: grapplemap, bjjgraph (2/5)
- Length: 4 steps
- ...

## Road 3: ...
...
```

### Queries (interactive, run after candidate_roads.json exists)

These are ad-hoc exploration queries, not part of the pipeline:

**Query 1**: What positions exist across sources?
```python
# Load all parsed/positions.json, print name + source
# Identify naming variations for the same position
```

**Query 2**: What transitions exist from position X?
```python
# Given a position name (fuzzy), find all edges where from_name matches
```

**Query 3**: What chains/families exist? (Flow-State specific)
```python
# Group Flow-State edges by chain_family field
# Each chain = a pre-identified game path candidate
```

**Query 4**: Cross-source agreement on specific transitions
```python
# For a given transition name, show all sources that have it
# with their original from/to names
```

**Query 5**: Which candidate roads match the PDF's example roads?
```python
# Compare candidate_roads.json against the 3 roads in the fieldboard PDF:
# Road 1: ColSlv → Closed → Scissor Sweep → Mount → Armbar
# Road 2: Butterfly → Hook Sweep → Side Control → Americana
# Road 3: KneeShield → Dogfight → Old School Sweep → Side → Mount → Armbar
```

---

## Milestone 4: Curriculum Spine Selection

### What this milestone is NOT

- Full ontology completion.
- Full graph normalization.
- Mapping every technique.
- Building the universal BJJ graph.

We are NOT building "the complete graph of BJJ."

### What this milestone IS

Selecting the smallest set of roads that teaches the largest amount of
useful BJJ understanding.

We ARE building "a pedagogically optimized traversal subset."

We only care about roads that are: valid, robust, low-entropy,
high-probability, and pedagogically stable.

---

### 4A — Select canonical roads only

Choose approximately:

- **5–10 beginner spine roads**
- **5–10 intermediate branch roads**
- **5–10 advanced network roads**

No more.

Selection criteria (all must be present for spine roads, relaxed for branch/network):

1. **Cross-source recurrence**: appears in ≥2 independent datasets
2. **Strong control checkpoints**: stable positions where the student can
   pause, assess, and consolidate before advancing
3. **Low branching complexity**: few decision points, clear "what next"
4. **Safe failure recovery**: if the sequence fails, student lands somewhere
   recoverable (still in guard, not stacked/passed)
5. **Reusable mechanics**: body mechanics transfer to other roads
   (e.g., hip escape appears in guard recovery AND mount escape)
6. **Duality richness**: teaches both Me and Op perspective —
   same road viewed as attack also reveals the defense

### 4B — Map ONLY selected roads to the fieldboard

Only after selection: map these roads into:

```
(FundamentalPosition, SubTopology, Action)
```

Using the corrected hierarchy:
```
Defense: OGRD → CGRD → HGRD → TRTL
Pass:    SCTR → MNT → BCTR
```

Do NOT map the full graph. Only map the selected curriculum roads.
The fieldboard should remain sparse and readable.

### 4C — Checkpoint analysis

For every selected road, explicitly identify:

- **Control checkpoints**: stable positions where you hold and assess
  (e.g., closed guard posture control, mount base stabilization)
- **Stabilization checkpoints**: moments where you secure a new position
  before advancing (e.g., crossface after passing to side control)
- **Transition checkpoints**: the mechanics that move you between positions
  (e.g., hip bump setup, underhook battle)
- **Submission checkpoints**: the final sequence that finishes
  (e.g., isolate arm → secure figure-four → extend for armbar)

Examples:
- Posture break before scissor sweep
- Mount stabilization before armbar setup
- Chest connection before rear naked choke
- Seatbelt grip before back control hooks

The point: good roads contain stable learning checkpoints.

### 4D — Failure topology analysis

For every road: analyze where students land if the sequence fails.

Examples:
- Scissor sweep failure → still in closed guard (safe)
- Butterfly sweep failure → seated scramble / open guard (recoverable)
- Armbar from guard failure → guard retained or opponent postures up (safe)
- Flying triangle failure → stacked / passed (dangerous)

This is pedagogically critical.

**Beginner roads must fail safely.** Failure should return to a known
position, ideally one already taught. Advanced roads may have riskier
failure states because the student already knows recovery.

Failure topology classification:
- **Safe**: failure returns to starting position or a previously-taught position
- **Recoverable**: failure lands in a neutral scramble; student needs
  re-engagement but is not in danger
- **Risky**: failure puts student in disadvantage (passed, flattened, submitted)

Spine roads should be Safe. Branch roads can be Recoverable.
Network roads may include Risky paths if the reward justifies the risk.

### 4E — Road classification

Classify selected roads into three tiers:

**Spine roads** (beginner highways):
- Low entropy — few decisions, clear path
- Stable checkpoints — can pause and consolidate at each step
- Short sequences — 3–5 steps
- Reusable mechanics — hip escape, bridge, shrimp, frame
- Safe failure — lands back in guard or neutral
- High cross-source agreement

**Branch roads** (intermediate expansions):
- Optional expansions branching from spine roads
- Moderate branching — 2–3 alternatives at decision points
- More reaction-based — responding to opponent's counter
- Build on spine mechanics but add new tools
- Recoverable failure

**Network roads** (advanced adaptive systems):
- High branching — multiple live reads at each step
- Opponent modeling — path depends on opponent's reaction
- Dynamic traversal — may loop, backtrack, or chain
- Connects multiple spine/branch roads into a coherent game
- May include risky paths with high reward

---

## Implementation Order

```
Milestone 1: (complete)
  Step 1: Create directory structure + download script
  Step 2: Run downloads
  Step 3: Verify raw data exists and is readable

Milestone 2: (complete)
  Step 4: Write parsers for all 6 sources
  Step 5: Verify all parsed/ directories populated
  Step 6: Generate PARSE_REPORT.md and README.md

Milestone 3: (complete)
  Step 7: Write extract_roads.py (BFS/DFS + cross-source matching)
  Step 8: Generate candidate_roads.json (18,170 candidates, 50 multi-source)
  Step 9: Generate candidate_roads_report.md (top 20 for human review)

Milestone 4:
  Step 10: 4A — Select ~25 canonical roads from candidates
           (5-10 spine, 5-10 branch, 5-10 network)
  Step 11: 4B — Map selected roads to fieldboard coordinates
  Step 12: 4C — Checkpoint analysis for each selected road
  Step 13: 4D — Failure topology analysis for each selected road
  Step 14: 4E — Classify roads into spine / branch / network
  Step 15: Human review — validate selections make BJJ sense
```

---

## Notes

- Graphling/BJJML has no public repo. Skip unless one surfaces.
- acenji/fight-encyclopedia has schema documentation but no actual technique
  data published yet. Skip.
- GrappleMap's 3D coordinate data is valuable for future pose/animation work
  but is not needed for graph extraction. Preserve as opaque strings for now.
