"""Milestone 3: Extract candidate roads from all parsed BJJ graph sources.

Loads all parsed edges, builds per-source adjacency graphs, runs BFS from
guard-like starts to submissions/dominant positions, does cross-source fuzzy
matching, scores candidates, and outputs candidate_roads.json + report.

Usage:
    python -m fieldboard.extract_roads
"""

import json
import re
from collections import defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parent
DATA = BASE / "data"

SOURCES = ["grapplemap", "bjjgraph", "flowstate", "bjj_graph_clj", "fsm"]

POSITION_ALIASES = {
    "full guard": "closed guard",
    "guard": "closed guard",
    "fullguard": "closed guard",
    "half guard top": "half guard",
    "half guard bottom": "half guard",
    "top half guard": "half guard",
    "side mount": "side control",
    "cross side": "side control",
    "sidecontrol": "side control",
    "side ctrl": "side control",
    "rear mount": "back control",
    "back mount": "back control",
    "back": "back control",
    "backcontrol": "back control",
    "low mount": "mount",
    "high mount": "mount",
    "s-mount": "mount",
    "modified mount": "mount",
    "3-4 mount": "mount",
    "north south": "north-south",
    "scarf hold": "kesa gatame",
    "rubber guard": "closed guard",
    "rubberguard": "closed guard",
    "butterfly": "butterfly guard",
    "standing position": "standing",
    "standing / neutral": "standing",
    "open guard": "open guard",
    "turtle": "turtle",
    "knee on belly": "knee on belly",
    "mount top": "mount",
    "side control top": "side control",
}

GUARD_KEYWORDS = [
    "closed guard", "guard", "butterfly", "dlr", "half guard",
    "open guard", "seated", "spider", "lasso", "x guard",
    "worm", "lapel", "rubber", "k guard", "reverse de la riva",
    "de la riva", "50-50", "5050",
]

DOMINANT_KEYWORDS = [
    "mount", "side control", "back control", "knee on belly",
    "north-south", "kesa gatame", "scarf",
]

CONTROL_POSITION_KEYWORDS = [
    "closed guard", "guard", "mount", "side control", "back control",
    "half guard", "knee on belly", "turtle", "north-south",
]

FIELDBOARD_HINTS = {
    "closed guard": "CGRD",
    "open guard": "OGRD",
    "half guard": "HGRD",
    "butterfly guard": "OGRD",
    "butterfly": "OGRD",
    "mount": "MNT",
    "side control": "SCTR",
    "back control": "BCTR",
    "turtle": "TRTL",
    "standing": "OGRD",
    "knee on belly": "SCTR",
    "north-south": "SCTR",
}

MAX_PATH_DEPTH = 10
MAX_PATHS_PER_START = 500


def _normalize_name(name):
    """Lowercase, strip slashes/punctuation, apply alias table."""
    if not name:
        return ""
    n = name.lower().strip()
    n = re.sub(r'\s*/\s*', ' / ', n)
    n = re.sub(r'\s+', ' ', n)

    # Try alias lookup on progressively simplified forms
    for candidate in [n, n.replace(" / ", " "), n.split(" / ")[0].strip()]:
        candidate = candidate.strip()
        if candidate in POSITION_ALIASES:
            return POSITION_ALIASES[candidate]

    # Strip top/bottom/w/ suffixes for matching
    simplified = re.sub(r'\s*[/(]\s*(top|bottom|w/.*)', '', n).strip()
    if simplified in POSITION_ALIASES:
        return POSITION_ALIASES[simplified]

    return simplified


def _is_guard_like(name):
    norm = _normalize_name(name)
    return any(kw in norm for kw in GUARD_KEYWORDS)


def _is_dominant(name):
    norm = _normalize_name(name)
    return any(kw in norm for kw in DOMINANT_KEYWORDS)


def _is_control_position(name):
    norm = _normalize_name(name)
    return any(kw in norm for kw in CONTROL_POSITION_KEYWORDS)


def _fieldboard_hint(name):
    norm = _normalize_name(name)
    for kw, hint in FIELDBOARD_HINTS.items():
        if kw in norm:
            return hint
    return None


def load_all_edges():
    """Load edges from all sources, return dict of source -> edge list."""
    all_edges = {}
    for src in SOURCES:
        fp = DATA / src / "parsed" / "edges.json"
        if fp.exists():
            edges = json.load(open(fp))
            usable = [e for e in edges if e.get("from_name") and e.get("to_name")
                       and e.get("from_id") and e.get("to_id")]
            all_edges[src] = usable
    return all_edges


def build_adjacency(edges):
    """Build adjacency: from_name -> [(edge_name, to_name, edge_type)]."""
    adj = defaultdict(list)
    for e in edges:
        adj[e["from_name"]].append((e["name"], e["to_name"], e["edge_type"]))
    return dict(adj)


def _out_degree(adj, pos_name):
    return len(adj.get(pos_name, []))


def extract_paths(adj, source):
    """BFS from guard-like starts, collect paths to submissions or dominant positions."""
    starts = [pos for pos in adj if _is_guard_like(pos)]
    paths = []

    for start in starts:
        queue = [(start, [(start, None, None)])]
        visited_paths = set()
        count = 0

        while queue and count < MAX_PATHS_PER_START:
            current, path = queue.pop(0)
            if len(path) > MAX_PATH_DEPTH:
                continue

            for edge_name, to_name, edge_type in adj.get(current, []):
                # Avoid cycles
                path_positions = {step[0] for step in path}
                if to_name in path_positions:
                    continue

                new_path = path + [(to_name, edge_name, edge_type)]

                # Check if this path reaches a goal
                is_submission = edge_type == "submission"
                is_dominant = _is_dominant(to_name) and not _is_guard_like(to_name)

                if is_submission or is_dominant:
                    path_key = tuple(step[0] for step in new_path)
                    if path_key not in visited_paths:
                        visited_paths.add(path_key)
                        paths.append({
                            "source": source,
                            "path": new_path,
                            "ends_with_submission": is_submission,
                            "ends_with_dominant": is_dominant,
                        })
                        count += 1

                # Continue exploring (even if we found a goal — longer paths may exist)
                if len(new_path) < MAX_PATH_DEPTH:
                    queue.append((to_name, new_path))

    return paths


def _path_to_normalized_sequence(path_data):
    """Convert a path to a normalized position sequence for cross-source matching."""
    return tuple(_normalize_name(step[0]) for step in path_data["path"])


def _collapse_consecutive(norm_seq):
    """Collapse consecutive positions that normalize to the same name."""
    if not norm_seq:
        return norm_seq
    collapsed = [norm_seq[0]]
    for pos in norm_seq[1:]:
        if pos != collapsed[-1]:
            collapsed.append(pos)
    return tuple(collapsed)


def _path_signature(norm_seq):
    """Create a matching signature from a normalized sequence (collapsed)."""
    return _collapse_consecutive(norm_seq)


def group_roads(all_paths):
    """Group paths into roads by normalized position sequence."""
    road_groups = defaultdict(list)
    for p in all_paths:
        norm_seq = _path_to_normalized_sequence(p)
        sig = _path_signature(norm_seq)
        road_groups[sig].append(p)
    return road_groups


def score_road(road_paths, all_adj):
    """Score a candidate road."""
    sources = set(p["source"] for p in road_paths)
    source_count = len(sources)

    # Use first path as representative
    rep = road_paths[0]
    positions_in_path = [step[0] for step in rep["path"]]
    norm_seq = _collapse_consecutive(
        tuple(_normalize_name(p) for p in positions_in_path))
    sequence_length = len(norm_seq)

    # Control checkpoints — count unique normalized fundamental positions
    seen_checkpoints = set()
    for pos in positions_in_path:
        norm = _normalize_name(pos)
        if _is_control_position(pos) and norm not in seen_checkpoints:
            seen_checkpoints.add(norm)
    checkpoint_count = min(len(seen_checkpoints), 5)

    # Branching complexity: average out-degree across sources at each step
    total_degree = 0
    degree_count = 0
    for p in road_paths:
        src = p["source"]
        adj = all_adj.get(src, {})
        for step in p["path"]:
            d = _out_degree(adj, step[0])
            if d > 0:
                total_degree += d
                degree_count += 1
    avg_out_degree = total_degree / max(degree_count, 1)

    # Scoring: multi-source agreement is king
    length_penalty = max(0, sequence_length - 5) * 1.0
    branching_penalty = avg_out_degree * 0.2
    shortness_bonus = max(0, 5 - sequence_length) * 0.5

    score = (source_count * 4.0
             + checkpoint_count * 1.0
             + shortness_bonus
             - length_penalty
             - branching_penalty)

    return {
        "source_count": source_count,
        "sequence_length": sequence_length,
        "checkpoint_count": checkpoint_count,
        "avg_out_degree": round(avg_out_degree, 1),
        "length_penalty": round(length_penalty, 1),
        "branching_penalty": round(branching_penalty, 1),
        "score": round(score, 2),
    }


def build_candidate_road(norm_seq, road_paths, scoring, all_adj):
    """Build a candidate road JSON object."""
    rep = road_paths[0]
    # Use collapsed positions for display and hints
    raw_positions = [step[0] for step in rep["path"]]
    collapsed_norm = _collapse_consecutive(
        tuple(_normalize_name(p) for p in raw_positions))
    positions = raw_positions

    # Build source_paths
    source_paths = []
    seen_sources = set()
    for p in road_paths:
        if p["source"] not in seen_sources:
            seen_sources.add(p["source"])
            source_paths.append({
                "source": p["source"],
                "raw_sequence": [step[0] for step in p["path"]],
            })

    # Control checkpoints — unique normalized names only
    checkpoints = []
    seen_cp = set()
    for pos in positions:
        if _is_control_position(pos):
            norm = _normalize_name(pos)
            if norm not in seen_cp:
                seen_cp.add(norm)
                checkpoints.append(norm)

    # Branching notes
    avg_deg = scoring["avg_out_degree"]
    if avg_deg < 5:
        branching = f"low ({avg_deg} avg alternatives per step)"
    elif avg_deg < 15:
        branching = f"moderate ({avg_deg} avg alternatives per step)"
    else:
        branching = f"high ({avg_deg} avg alternatives per step)"

    # Beginner reason
    beginner_reason = ""
    if scoring["sequence_length"] <= 6 and scoring["checkpoint_count"] >= 1:
        ends = "submission" if rep["ends_with_submission"] else "dominant position"
        beginner_reason = (
            f"Short {scoring['sequence_length']}-step path with "
            f"{scoring['checkpoint_count']} control checkpoint(s), ending in {ends}"
        )

    # Fieldboard hints
    hints = []
    for i, pos in enumerate(positions):
        hint = _fieldboard_hint(pos)
        edge_type = rep["path"][i][2] if i > 0 else None
        if hint:
            if edge_type == "submission":
                hints.append(f"{hint}.SUB")
            elif edge_type == "sweep":
                hints.append(f"{hint}.SWP")
            elif i == 0 or _is_control_position(pos):
                hints.append(f"{hint}.CTRL")
            else:
                hints.append(f"{hint}.TRZ")

    # Name from collapsed normalized sequence
    name_parts = []
    prev_norm = None
    for i, pos in enumerate(positions):
        norm = _normalize_name(pos)
        if norm == prev_norm:
            continue
        prev_norm = norm
        if i > 0:
            edge_name = rep["path"][i][1]
            edge_type = rep["path"][i][2]
            if edge_type in ("submission", "sweep") and edge_name:
                name_parts.append(edge_name)
                continue
        name_parts.append(norm.title())

    name = " → ".join(name_parts)

    return {
        "name": name,
        "source_paths": source_paths,
        "source_count": scoring["source_count"],
        "sequence_length": scoring["sequence_length"],
        "control_checkpoints": checkpoints,
        "branching_notes": branching,
        "beginner_reason": beginner_reason,
        "fieldboard_hint": hints,
        "score": scoring["score"],
        "status": "candidate",
    }


def generate_report(candidates, all_edges):
    """Generate markdown report for top 20 candidates."""
    lines = ["# Candidate Roads — Top 20", ""]
    lines.append(f"Generated: 2026-05-16")
    lines.append(f"Sources: " + ", ".join(
        f"{src} ({len(edges)} usable edges)"
        for src, edges in sorted(all_edges.items())
    ))
    lines.append(f"Total candidates: {len(candidates)}")
    lines.append("")

    for i, c in enumerate(candidates[:20], 1):
        lines.append(f"## Road {i}: {c['name']}")
        lines.append(f"- **Score**: {c['score']}")
        sources = ", ".join(sp["source"] for sp in c["source_paths"])
        lines.append(f"- **Sources**: {sources} ({c['source_count']}/{len(SOURCES)})")
        lines.append(f"- **Length**: {c['sequence_length']} steps")
        if c["control_checkpoints"]:
            lines.append(f"- **Control checkpoints**: {', '.join(c['control_checkpoints'])}")
        lines.append(f"- **Branching**: {c['branching_notes']}")
        if c["beginner_reason"]:
            lines.append(f"- **Beginner**: yes — {c['beginner_reason']}")
        if c["fieldboard_hint"]:
            lines.append(f"- **Hint**: {' → '.join(c['fieldboard_hint'])}")

        # Show raw sequences from each source
        if len(c["source_paths"]) > 1:
            lines.append("- **Source sequences**:")
            for sp in c["source_paths"]:
                lines.append(f"  - {sp['source']}: {' → '.join(sp['raw_sequence'])}")
        lines.append("")

    return "\n".join(lines)


def run():
    all_edges = load_all_edges()
    print("Loaded edges:")
    for src, edges in sorted(all_edges.items()):
        print(f"  {src}: {len(edges)} usable edges")

    # Build per-source adjacency
    all_adj = {}
    for src, edges in all_edges.items():
        all_adj[src] = build_adjacency(edges)

    # Extract paths per source
    all_paths = []
    for src, adj in all_adj.items():
        paths = extract_paths(adj, src)
        print(f"  {src}: {len(paths)} raw paths extracted")
        all_paths.extend(paths)

    print(f"\nTotal raw paths: {len(all_paths)}")

    # Group into roads by normalized sequence
    road_groups = group_roads(all_paths)
    print(f"Unique roads (after normalization): {len(road_groups)}")

    # Score and build candidates
    candidates = []
    for norm_seq, road_paths in road_groups.items():
        scoring = score_road(road_paths, all_adj)
        candidate = build_candidate_road(norm_seq, road_paths, scoring, all_adj)
        candidates.append(candidate)

    # Sort by score descending
    candidates.sort(key=lambda c: -c["score"])

    # Write outputs
    out_roads = DATA / "candidate_roads.json"
    with open(out_roads, "w") as f:
        json.dump(candidates, f, indent=2)
    print(f"\nWrote {len(candidates)} candidates to {out_roads}")

    report = generate_report(candidates, all_edges)
    out_report = DATA / "candidate_roads_report.md"
    out_report.write_text(report)
    print(f"Wrote report to {out_report}")

    # Summary
    multi_source = [c for c in candidates if c["source_count"] > 1]
    beginner = [c for c in candidates if c["beginner_reason"]]
    print(f"\nSummary:")
    print(f"  Total candidates: {len(candidates)}")
    print(f"  Multi-source (>1): {len(multi_source)}")
    print(f"  Beginner-friendly: {len(beginner)}")
    print(f"  Top score: {candidates[0]['score'] if candidates else 'N/A'}")

    return candidates


if __name__ == "__main__":
    run()
