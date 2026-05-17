"""Parse ianwessen/jiu-jitsu-state-machine FSL file into positions.json and edges.json.

FSL format:
  StateA 'Technique' -> StateB;     (one-way labeled)
  StateA -> StateB;                 (one-way unlabeled)
  StateA <=> StateB;                (bidirectional)
  StateA 'Technique' => StateB;     (terminal/final)

Usage:
    python -m fieldboard.extract.fsm
"""

import json
import re
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
RAW = BASE / "data" / "fsm" / "raw" / "repo" / "bjjsm.fsl"
OUT = BASE / "data" / "fsm" / "parsed"


def parse():
    text = RAW.read_text()
    positions = []
    edges = []
    pos_ids = {}

    def _ensure_pos(name):
        if name not in pos_ids:
            pid = f"fsm_p{len(positions)}"
            pos_ids[name] = pid
            positions.append({
                "id": pid,
                "name": name,
                "source": "fsm",
                "tags": [],
                "properties": {},
                "raw": {},
            })
        return pos_ids[name]

    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("//") or line.startswith("machine_") or line.startswith("jssm_") or line.startswith("graph_"):
            continue
        line = line.rstrip(";").strip()
        if not line:
            continue

        # Labeled: StateA 'Label' -> StateB
        m = re.match(r"(\w+)\s+'([^']+)'\s*(->|<=>|=>)\s*(\w+)", line)
        if m:
            from_name, label, arrow, to_name = m.groups()
            from_id = _ensure_pos(from_name)
            to_id = _ensure_pos(to_name)

            label_lower = label.lower()
            if to_name == "Submission" or arrow == "=>":
                edge_type = "submission"
            elif "sweep" in label_lower:
                edge_type = "sweep"
            else:
                edge_type = "transition"

            edges.append({
                "id": f"fsm_e{len(edges)}",
                "name": label,
                "source": "fsm",
                "from_id": from_id,
                "from_name": from_name,
                "to_id": to_id,
                "to_name": to_name,
                "edge_type": edge_type,
                "tags": [],
                "properties": {"arrow": arrow},
                "raw": {},
            })

            if arrow == "<=>":
                edges.append({
                    "id": f"fsm_e{len(edges)}",
                    "name": f"{label} (reverse)",
                    "source": "fsm",
                    "from_id": to_id,
                    "from_name": to_name,
                    "to_id": from_id,
                    "to_name": from_name,
                    "edge_type": edge_type,
                    "tags": [],
                    "properties": {"arrow": "<=>", "reverse": True},
                    "raw": {},
                })
            continue

        # Unlabeled: StateA -> StateB
        m = re.match(r"(\w+)\s*(->|<=>|=>)\s*(\w+)", line)
        if m:
            from_name, arrow, to_name = m.groups()
            from_id = _ensure_pos(from_name)
            to_id = _ensure_pos(to_name)

            if to_name == "Submission" or arrow == "=>":
                edge_type = "submission"
            else:
                edge_type = "transition"

            edges.append({
                "id": f"fsm_e{len(edges)}",
                "name": f"{from_name} -> {to_name}",
                "source": "fsm",
                "from_id": from_id,
                "from_name": from_name,
                "to_id": to_id,
                "to_name": to_name,
                "edge_type": edge_type,
                "tags": [],
                "properties": {"arrow": arrow},
                "raw": {},
            })

            if arrow == "<=>":
                edges.append({
                    "id": f"fsm_e{len(edges)}",
                    "name": f"{to_name} -> {from_name}",
                    "source": "fsm",
                    "from_id": to_id,
                    "from_name": to_name,
                    "to_id": from_id,
                    "to_name": from_name,
                    "edge_type": edge_type,
                    "tags": [],
                    "properties": {"arrow": "<=>", "reverse": True},
                    "raw": {},
                })

    OUT.mkdir(parents=True, exist_ok=True)
    _write(OUT / "positions.json", positions)
    _write(OUT / "edges.json", edges)

    n_sub = sum(1 for e in edges if e["edge_type"] == "submission")
    _write(OUT / "metadata.json", {
        "source": "fsm",
        "repo": "https://github.com/ianwessen/jiu-jitsu-state-machine",
        "license": "MIT",
        "positions": len(positions),
        "edges": len(edges),
        "submissions": n_sub,
        "errors": 0,
    })

    return positions, edges, []


def _write(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


if __name__ == "__main__":
    positions, edges, _ = parse()
    print(f"FSM: {len(positions)} positions, {len(edges)} edges")
