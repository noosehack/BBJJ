"""Parse Flow-State TypeScript data files into positions.json and edges.json.

Reads positions.ts, edges.ts, actions.ts. Strips TS type annotations and
parses the resulting JSON arrays.

Usage:
    python -m fieldboard.extract.flowstate
"""

import json
import re
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
RAW = BASE / "data" / "flowstate" / "raw" / "repo" / "src" / "data"
OUT = BASE / "data" / "flowstate" / "parsed"


def _parse_ts_array(filepath):
    text = filepath.read_text()
    match = re.search(r'=\s*(\[.*\])\s*;?\s*$', text, re.DOTALL)
    if not match:
        return []
    raw = match.group(1)
    lines = raw.split('\n')
    cleaned = []
    for line in lines:
        line = re.sub(r'//.*$', '', line)
        line = line.replace('→', '->')  # →
        # Quote unquoted keys at start of line (after whitespace)
        # Only match: `  key_name:` pattern, not content inside strings
        line = re.sub(r'^(\s*)(\w[\w_]*)\s*:', r'\1"\2":', line)
        cleaned.append(line)
    raw = '\n'.join(cleaned)
    raw = raw.replace("'", '"')
    raw = re.sub(r',\s*([}\]])', r'\1', raw)
    # Fix embedded quotes in string values: "Chain "attack": kimura"
    # Replace interior double quotes with single quotes
    raw = _fix_embedded_quotes(raw)
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        # Find problem line and try to fix
        problem_line = e.lineno
        lines2 = raw.split('\n')
        if 0 < problem_line <= len(lines2):
            lines2[problem_line - 1] = re.sub(r'"([^"]*)"([^",:\[\]{}]+)"', r'"\1\2"', lines2[problem_line - 1])
        return json.loads('\n'.join(lines2))


def _fix_embedded_quotes(text):
    result = []
    i = 0
    while i < len(text):
        if text[i] == '"':
            # Find the matching close quote
            j = i + 1
            while j < len(text):
                if text[j] == '\\':
                    j += 2
                    continue
                if text[j] == '"':
                    # Is this the real end? Check what follows
                    after = text[j + 1:j + 20].lstrip()
                    if after and after[0] in (',', '}', ']', '\n', '\r', ':'):
                        break
                    # Not the end — this is an embedded quote, escape it
                    result.append(text[i:j])
                    result.append("'")
                    i = j + 1
                    continue
                j += 1
            result.append(text[i:j + 1])
            i = j + 1
        else:
            result.append(text[i])
            i += 1
    return ''.join(result)


def parse():
    positions = []
    edges = []
    errors = []

    # Positions
    raw_positions = _parse_ts_array(RAW / "positions.ts")
    pos_map = {}
    for rp in raw_positions:
        pid = rp.get("position_id", f"fs_p{len(positions)}")
        name = rp.get("position_name", "")
        family = rp.get("position_family", "")
        pos_map[pid] = name
        positions.append({
            "id": pid,
            "name": name,
            "source": "flowstate",
            "tags": [family] if family else [],
            "properties": {"position_family": family},
            "raw": rp,
        })

    # Actions (nodes between positions)
    raw_actions = _parse_ts_array(RAW / "actions.ts")
    action_map = {}
    for ra in raw_actions:
        aid = ra.get("parent_action_id", "")
        action_map[aid] = ra

    # Edges
    raw_edges = _parse_ts_array(RAW / "edges.ts")
    for re_item in raw_edges:
        node_id = re_item.get("node_id", "")
        from_node = re_item.get("from_node_id", "")
        to_node = re_item.get("next_node_id")
        label = re_item.get("edge_label", "")
        outcome = re_item.get("outcome_type", "")

        # Resolve from action to its position
        action_info = action_map.get(from_node, {})
        from_position = action_info.get("start_position", "")
        from_pos_id = None
        for pid, pname in pos_map.items():
            if pname.lower() == from_position.lower():
                from_pos_id = pid
                break

        to_pos_name = pos_map.get(to_node, to_node)
        to_pos_id = to_node if to_node in pos_map else None

        # Classify edge type from outcome_type
        outcome_lower = outcome.lower() if outcome else ""
        if "submission" in outcome_lower or "finish" in outcome_lower:
            edge_type = "submission"
        elif "sweep" in outcome_lower or "reversal" in outcome_lower:
            edge_type = "sweep"
        elif "escape" in outcome_lower:
            edge_type = "escape"
        elif "pass" in outcome_lower:
            edge_type = "pass"
        elif "takedown" in outcome_lower:
            edge_type = "transition"
        else:
            edge_type = "transition"

        edges.append({
            "id": f"fs_e{len(edges)}",
            "name": action_info.get("your_action", label),
            "source": "flowstate",
            "from_id": from_pos_id,
            "from_name": from_position or from_node,
            "to_id": to_pos_id,
            "to_name": to_pos_name,
            "edge_type": edge_type,
            "tags": [],
            "properties": {
                "outcome_type": outcome,
                "is_terminal": re_item.get("is_terminal", ""),
                "priority_rank": re_item.get("priority_rank"),
                "counter_if_fails": re_item.get("counter_if_fails", ""),
            },
            "raw": {
                "node_id": node_id,
                "from_node_id": from_node,
                "next_node_id": to_node,
                "edge_label": label,
                "action": action_info if action_info else None,
                "gi_no_gi": action_info.get("gi_no_gi", ""),
                "skill_level": action_info.get("skill_level", ""),
                "chain_family": action_info.get("chain_family", ""),
            },
        })

    OUT.mkdir(parents=True, exist_ok=True)
    _write(OUT / "positions.json", positions)
    _write(OUT / "edges.json", edges)

    n_sub = sum(1 for e in edges if e["edge_type"] == "submission")
    n_sweep = sum(1 for e in edges if e["edge_type"] == "sweep")

    _write(OUT / "metadata.json", {
        "source": "flowstate",
        "repo": "https://github.com/iphoenix227/Flow-State---BJJ-Attack-Decision-Map",
        "license": "None specified",
        "positions": len(positions),
        "edges": len(edges),
        "actions_loaded": len(action_map),
        "submissions": n_sub,
        "sweeps": n_sweep,
        "errors": len(errors),
    })

    return positions, edges, errors


def _write(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


if __name__ == "__main__":
    positions, edges, errors = parse()
    print(f"Flow-State: {len(positions)} positions, {len(edges)} edges, "
          f"{len(errors)} errors")
