# BJJ Graph Library — Parsed Data

Six open-source BJJ graph/transition datasets, each parsed into a common schema.

## Sources

| Source | Repo | Positions | Edges | License |
|--------|------|-----------|-------|---------|
| grapplemap | Eelis/GrappleMap | 596 | 1,490 | Public Domain |
| bjjgraph | diogoseca/bjjgraph | 85 | 3,528 | PolyForm NC 1.0 |
| flowstate | iphoenix227/Flow-State | 16 | 175 | None specified |
| bjj_graph_clj | daveyarwood/bjj-graph | 90 | 206 | None specified |
| cavani | fcavani/jiu-jitsu-graph | 12 | 14 | CC BY-NC 4.0 |
| fsm | ianwessen/jiu-jitsu-state-machine | 12 | 25 | MIT |
| **Total** | | **811** | **5,438** | |

## Directory Layout

```
fieldboard/data/
  {source}/
    raw/repo/         # cloned source repository
    parsed/
      positions.json  # position nodes
      edges.json      # transition/technique edges
      metadata.json   # source info, counts, errors
  PARSE_REPORT.md     # detailed validation report
  README.md           # this file
```

## Common Schema

### positions.json

```json
{
  "id": "src_p0",
  "name": "Original Position Name",
  "source": "source_name",
  "tags": [],
  "properties": {},
  "raw": {}
}
```

### edges.json

```json
{
  "id": "src_e0",
  "name": "Technique Name",
  "source": "source_name",
  "from_id": "src_p0",
  "from_name": "From Position",
  "to_id": "src_p1",
  "to_name": "To Position",
  "edge_type": "transition|submission|sweep|escape|pass",
  "tags": [],
  "properties": {},
  "raw": {}
}
```

### Edge Types

| Type | Count | % |
|------|-------|---|
| transition | 4,416 | 81.2% |
| sweep | 418 | 7.7% |
| submission | 397 | 7.3% |
| escape | 171 | 3.1% |
| pass | 36 | 0.7% |

Edge types come from source-native labels. No cross-source ontology normalization has been applied.

## Parsers

Each source has a parser in `fieldboard/extract/`:

```
python -m fieldboard.extract.grapplemap
python -m fieldboard.extract.bjjgraph
python -m fieldboard.extract.flowstate
python -m fieldboard.extract.bjj_graph_clj
python -m fieldboard.extract.cavani
python -m fieldboard.extract.fsm
```

## Known Limitations

- **No cross-source normalization**: Position names are source-original. "full guard" (GrappleMap) = "Closed Guard" (bjjgraph) = "Guard" (clj) = "FullGuard" (FSM).
- **GrappleMap from/to matching**: Only 16% of edges have both endpoints resolved. Full resolution requires 3D reorientation-invariant matching.
- **bjjgraph edge inflation**: 3,528 edges from ~1,200 unique techniques (each outcome is a separate edge).

See `PARSE_REPORT.md` for full details.
