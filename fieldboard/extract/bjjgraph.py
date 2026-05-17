"""Parse diogoseca/bjjgraph JSON files into positions.json and edges.json.

Reads from content/Positions/*.json, content/Transitions/*.json,
content/Submissions/*.json.

Usage:
    python -m fieldboard.extract.bjjgraph
"""

import json
import glob
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
RAW = BASE / "data" / "bjjgraph" / "raw" / "repo" / "content"
OUT = BASE / "data" / "bjjgraph" / "parsed"


def parse():
    positions = []
    edges = []
    errors = []
    pos_slugs = {}

    # Positions
    for fp in sorted(glob.glob(str(RAW / "Positions" / "*.json"))):
        try:
            d = json.load(open(fp))
        except Exception as e:
            errors.append({"file": fp, "error": str(e)})
            continue

        pid = f"bg_p{len(positions)}"
        name = d.get("name", Path(fp).stem)
        slug = d.get("slug", "")
        pos_slugs[name] = pid

        top = d.get("top") or {}
        bottom = d.get("bottom") or {}

        positions.append({
            "id": pid,
            "name": name,
            "source": "bjjgraph",
            "tags": d.get("key_principles", [])[:5],
            "properties": {
                "slug": slug,
                "top_type": (top.get("state_properties") or {}).get("position_type", ""),
                "top_risk": (top.get("state_properties") or {}).get("risk_level", ""),
                "bottom_type": (bottom.get("state_properties") or {}).get("position_type", ""),
                "bottom_risk": (bottom.get("state_properties") or {}).get("risk_level", ""),
            },
            "raw": {
                "file": Path(fp).name,
                "top_transitions": top.get("transitions", []),
                "bottom_transitions": bottom.get("transitions", []),
                "related_positions": d.get("related_positions", []),
                "description": (d.get("description") or "")[:200],
            },
        })

    # Transitions
    for fp in sorted(glob.glob(str(RAW / "Transitions" / "*.json"))):
        try:
            d = json.load(open(fp))
        except Exception as e:
            errors.append({"file": fp, "error": str(e)})
            continue

        name = d.get("name", Path(fp).stem)
        from_raw = d.get("from_position", "")
        from_name = from_raw.split("/")[0].strip() if "/" in from_raw else from_raw
        from_perspective = from_raw.split("/")[1].strip() if "/" in from_raw else ""
        from_id = pos_slugs.get(from_name)

        outcomes = d.get("outcomes", [])
        for oi, outcome in enumerate(outcomes):
            to_raw = outcome.get("to", "")
            to_name = to_raw.split("/")[0].strip() if "/" in to_raw else to_raw
            to_id = pos_slugs.get(to_name)
            result = outcome.get("result", "")

            if to_raw == "game-over":
                edge_type = "submission"
                to_name = "game-over"
                to_id = None
            elif "sweep" in name.lower():
                edge_type = "sweep"
            elif "escape" in name.lower() or "recovery" in name.lower():
                edge_type = "escape"
            elif "pass" in name.lower():
                edge_type = "pass"
            else:
                edge_type = "transition"

            edges.append({
                "id": f"bg_e{len(edges)}",
                "name": name,
                "source": "bjjgraph",
                "from_id": from_id,
                "from_name": from_name,
                "to_id": to_id,
                "to_name": to_name,
                "edge_type": edge_type,
                "tags": d.get("tags", []),
                "properties": {
                    "from_perspective": from_perspective,
                    "result": result,
                    "probability": outcome.get("probability"),
                    "success_rate": d.get("success_rate"),
                },
                "raw": {
                    "file": Path(fp).name,
                    "outcome_index": oi,
                    "from_position_raw": from_raw,
                    "to_raw": to_raw,
                    "conditions": d.get("conditions", [])[:3],
                },
            })

    # Submissions
    for fp in sorted(glob.glob(str(RAW / "Submissions" / "*.json"))):
        try:
            d = json.load(open(fp))
        except Exception as e:
            errors.append({"file": fp, "error": str(e)})
            continue

        name = d.get("name", Path(fp).stem)
        from_raw = d.get("from_position", "")
        from_name = from_raw.split("/")[0].strip() if "/" in from_raw else from_raw
        from_perspective = from_raw.split("/")[1].strip() if "/" in from_raw else ""
        from_id = pos_slugs.get(from_name)

        edges.append({
            "id": f"bg_e{len(edges)}",
            "name": name,
            "source": "bjjgraph",
            "from_id": from_id,
            "from_name": from_name,
            "to_id": None,
            "to_name": "game-over",
            "edge_type": "submission",
            "tags": d.get("tags", []),
            "properties": {
                "from_perspective": from_perspective,
                "success_rate": d.get("success_rate"),
                "submission_type": d.get("submission_type", ""),
                "submission_category": d.get("submission_category", ""),
                "target_area": d.get("target_area", ""),
            },
            "raw": {
                "file": Path(fp).name,
                "from_position_raw": from_raw,
            },
        })

    OUT.mkdir(parents=True, exist_ok=True)
    _write(OUT / "positions.json", positions)
    _write(OUT / "edges.json", edges)

    n_sub = sum(1 for e in edges if e["edge_type"] == "submission")
    n_sweep = sum(1 for e in edges if e["edge_type"] == "sweep")
    n_escape = sum(1 for e in edges if e["edge_type"] == "escape")
    n_pass = sum(1 for e in edges if e["edge_type"] == "pass")

    _write(OUT / "metadata.json", {
        "source": "bjjgraph",
        "repo": "https://github.com/diogoseca/bjjgraph",
        "license": "PolyForm Noncommercial 1.0.0",
        "positions": len(positions),
        "edges": len(edges),
        "submissions": n_sub,
        "sweeps": n_sweep,
        "escapes": n_escape,
        "passes": n_pass,
        "transitions": len(edges) - n_sub - n_sweep - n_escape - n_pass,
        "errors": len(errors),
        "error_details": errors[:20],
    })

    return positions, edges, errors


def _write(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


if __name__ == "__main__":
    positions, edges, errors = parse()
    print(f"bjjgraph: {len(positions)} positions, {len(edges)} edges, "
          f"{len(errors)} errors")
    n_sub = sum(1 for e in edges if e["edge_type"] == "submission")
    n_sweep = sum(1 for e in edges if e["edge_type"] == "sweep")
    print(f"  Types: {len(edges) - n_sub - n_sweep} transition/escape/pass, "
          f"{n_sub} submission, {n_sweep} sweep")
