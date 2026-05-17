# Parse Report — BJJ Graph Library

Generated: 2026-05-16

## Summary

| Source | Positions | Edges | Submissions | Sweeps | Errors | License |
|--------|-----------|-------|-------------|--------|--------|---------|
| grapplemap | 596 | 1,490 | 103 | 53 | 43 | Public Domain |
| bjjgraph | 85 | 3,528 | 220 | 336 | 0 | PolyForm NC 1.0 |
| flowstate | 16 | 175 | 62 | 29 | 0 | None specified |
| bjj_graph_clj | 90 | 206 | 2 | 0 | 0 | None specified |
| cavani | 12 | 14 | 2 | 0 | 0 | CC BY-NC 4.0 |
| fsm | 12 | 25 | 8 | 0 | 0 | MIT |
| **Total** | **811** | **5,438** | **397** | **418** | **43** | |

## Per-Source Details

### GrappleMap (Eelis/GrappleMap)

- **Raw file**: `GrappleMap.txt` (39,098 lines)
- **Positions**: 596 (3D joint coordinate frames for 2 players)
- **Edges**: 1,490 transitions (multi-frame animation keyframes)
- **Edge types**: 1,334 transition, 103 submission, 53 sweep
- **From/to matching**: 232/1,490 (16%) fully matched via exact frame comparison
  - GrappleMap uses reorientation-invariant 3D matching in C++ which we don't replicate
  - 850/1,490 (57%) have at least one side matched
  - All edges retain name + tags for querying regardless of from/to resolution
- **Errors**: 43 (empty frame blocks in variant-split transitions — non-critical)
- **Tags**: 161 unique position/technique/body-orientation tags
- **References**: Instructional citations preserved in edge `raw.refs`

### bjjgraph (diogoseca/bjjgraph)

- **Raw files**: 140 position JSONs, 1,072 transition JSONs, 153 submission JSONs
- **Positions**: 85 unique (some JSON files describe the same position from top/bottom)
  - Note: 140 files → 85 positions because top/bottom variants are in the same file
  - But not all 140 map to unique positions due to naming
- **Edges**: 3,528 (each transition JSON has multiple outcomes = multiple edges)
  - Each outcome (success/failure/counter) creates a separate edge
- **Edge types**: 2,972 transition, 220 submission, 336 sweep
- **Extra metadata preserved**: probability weights, decision trees, state properties,
  risk levels, conditions, variants
- **Perspective**: Preserved as `from_perspective` (Top/Bottom suffix from `from_position`)
- **Errors**: 0

### Flow-State (iphoenix227/Flow-State)

- **Raw files**: `positions.ts`, `edges.ts`, `actions.ts` (TypeScript)
- **Positions**: 16 root positions (Standing, guards, pins, back, turtle, leg entanglement)
- **Edges**: 175 (action-to-outcome chains)
- **Edge types**: 84 transition, 62 submission, 29 sweep
- **Extra metadata preserved**: gi/no-gi, skill_level (White→Black), chain_family,
  concept_tags, grip_tags, priority_rank, counter_if_fails
- **Errors**: 0

### bjj-graph (daveyarwood/bjj-graph)

- **Raw file**: `v2.clj` (568 lines, Clojure)
- **Positions**: 90 (includes intermediate states like "Mount + headlock")
- **Edges**: 206 (labeled technique edges + unlabeled transitions)
- **Submissions**: 2 terminal nodes (Americana Armlock, Rear Naked Choke + others via graph)
  - Note: low submission count because many techniques lead TO submission nodes via
    ::transitions edges, which are typed as "transition" not "submission"
- **Graphs parsed**: combatives, bonus-slices, blue-belt, plus merged `all`
- **Based on**: Gracie University Combatives + Blue Belt curriculum
- **Errors**: 0

### cavani (fcavani/jiu-jitsu-graph)

- **Raw files**: 11 RDF N-Quad files
- **Positions**: 12 (closed guard, half guard, mount, side control, etc.)
- **Edges**: 14 (moves with class: sweep/submission/transition/pass)
- **Submissions**: 2
- **Language**: Bilingual (Portuguese/English names preserved)
- **Small dataset** — author had blue belt, project archived
- **Errors**: 0

### FSM (ianwessen/jiu-jitsu-state-machine)

- **Raw file**: `bjjsm.fsl` (40 lines)
- **Positions**: 12 (FullGuard, Mount, BackControl, SideControl, etc.)
- **Edges**: 25 (includes bidirectional edges expanded to 2)
- **Submissions**: 8 (all edges targeting "Submission" node)
- **Arrow types**: `->` one-way, `<=>` bidirectional, `=>` terminal
- **Errors**: 0

## Edge Type Distribution

| Type | Count | % |
|------|-------|---|
| transition | 4,416 | 81.2% |
| submission | 397 | 7.3% |
| sweep | 418 | 7.7% |
| escape | 171 | 3.1% |
| pass | 36 | 0.7% |
| **Total** | **5,438** | |

## Known Limitations

1. **GrappleMap from/to resolution**: Only 16% of edges have both endpoints matched.
   The full graph requires 3D reorientation-invariant matching (C++ code in the repo).
   Names and tags are still usable for Milestone 3 queries.

2. **bjjgraph edge inflation**: 3,528 edges from 1,072 transition files because each
   outcome (success/failure/counter) is a separate edge. The unique technique count
   is closer to ~1,200.

3. **bjj-graph-clj submission detection**: Only 2 explicit `::submission?` nodes,
   but many techniques lead to submissions through transition chains. The graph
   structure captures this even though edge_type doesn't.

4. **cavani sparse**: Only 14 edges. Useful for cross-validation, not as a primary source.

5. **No ontology normalization**: Position names are source-original.
   "full guard" (GrappleMap) = "Closed Guard" (bjjgraph) = "Guard" (clj) = "FullGuard" (FSM).
   Cross-source queries require fuzzy name matching.

## Files Produced

Each source has three files in `fieldboard/data/{source}/parsed/`:
- `positions.json` — position nodes with original names, tags, properties
- `edges.json` — transition/technique edges with from/to, type, tags
- `metadata.json` — source info, counts, error details
