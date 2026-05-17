"""Parse fcavani/jiu-jitsu-graph RDF files into positions.json and edges.json.

N-Quad format: _:subject <predicate> value .
Values are either _:references or "strings"@lang .

Usage:
    python -m fieldboard.extract.cavani
"""

import json
import re
import glob
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
RAW = BASE / "data" / "cavani" / "raw" / "repo"
OUT = BASE / "data" / "cavani" / "parsed"


def _parse_rdf_files():
    entities = {}
    for fp in sorted(glob.glob(str(RAW / "*.rdf"))):
        for line in open(fp):
            line = line.strip()
            if not line or not line.endswith('.'):
                continue
            line = line[:-1].strip()

            m = re.match(r'(_:\w+)\s+<(\w[\w.]*)>\s+(.*)', line)
            if not m:
                continue

            subj = m.group(1)
            pred = m.group(2)
            obj_raw = m.group(3).strip()

            if subj not in entities:
                entities[subj] = {"_id": subj}

            # Parse object
            if obj_raw.startswith('_:'):
                obj_val = obj_raw
                lang = None
            elif obj_raw.startswith('"'):
                lang_match = re.match(r'"(.*)"(?:@(\w+))?', obj_raw)
                if lang_match:
                    obj_val = lang_match.group(1)
                    lang = lang_match.group(2)
                else:
                    obj_val = obj_raw.strip('"')
                    lang = None
            else:
                obj_val = obj_raw
                lang = None

            ent = entities[subj]
            key = f"{pred}@{lang}" if lang else pred
            if key in ent:
                if isinstance(ent[key], list):
                    ent[key].append(obj_val)
                else:
                    ent[key] = [ent[key], obj_val]
            else:
                ent[key] = obj_val

    return entities


def parse():
    entities = _parse_rdf_files()

    positions = []
    edges = []
    errors = []
    pos_ids = {}

    # Find position entities
    for eid, ent in entities.items():
        dtype = ent.get("dgraph.type", "")
        if dtype == "Position":
            name_en = ent.get("name@en", "")
            name_pt = ent.get("name@pt", "")
            name = name_en if name_en else name_pt
            if isinstance(name, list):
                name = name[0]

            pid = f"cav_p{len(positions)}"
            pos_ids[eid] = pid
            positions.append({
                "id": pid,
                "name": name,
                "source": "cavani",
                "tags": [],
                "properties": {
                    "rdf_id": eid,
                    "points": ent.get("points", ""),
                },
                "raw": {
                    "name_pt": name_pt if isinstance(name_pt, str) else (name_pt[0] if name_pt else ""),
                    "name_en": name_en if isinstance(name_en, str) else (name_en[0] if name_en else ""),
                    "description": ent.get("description@pt", ""),
                },
            })

    # Basics entities (class types: sweep, submission, etc.)
    class_map = {}
    for eid, ent in entities.items():
        if ent.get("dgraph.type") == "Basics":
            name_en = ent.get("name@en", "")
            name_pt = ent.get("name@pt", "")
            name = name_en if name_en else name_pt
            if isinstance(name, list):
                name = name[0]
            class_map[eid] = name.lower()

    # Find move entities
    for eid, ent in entities.items():
        if ent.get("dgraph.type") != "Move":
            continue

        name_en = ent.get("name@en", "")
        name_pt = ent.get("name@pt", "")
        name = name_en if name_en else name_pt
        if isinstance(name, list):
            name = name[0]

        move_class_ref = ent.get("class", "")
        move_class = class_map.get(move_class_ref, "unknown")

        # Map class to edge_type
        if move_class in ("submission", "finalização", "finalizacao"):
            edge_type = "submission"
        elif move_class in ("sweep", "raspagem"):
            edge_type = "sweep"
        elif move_class in ("pass", "passagem"):
            edge_type = "pass"
        elif move_class in ("transition", "transição", "transicao"):
            edge_type = "transition"
        elif move_class in ("escape",):
            edge_type = "escape"
        else:
            edge_type = "transition"

        # Find target position
        to_refs = ent.get("to", [])
        if isinstance(to_refs, str):
            to_refs = [to_refs]

        for to_ref in to_refs:
            to_id = pos_ids.get(to_ref)
            to_name = ""
            if to_ref in entities:
                tn = entities[to_ref].get("name@en", entities[to_ref].get("name@pt", ""))
                to_name = tn[0] if isinstance(tn, list) else tn

            edges.append({
                "id": f"cav_e{len(edges)}",
                "name": name,
                "source": "cavani",
                "from_id": None,
                "from_name": "",
                "to_id": to_id,
                "to_name": to_name,
                "edge_type": edge_type,
                "tags": [],
                "properties": {
                    "rdf_id": eid,
                    "move_class": move_class,
                    "points": ent.get("points", ""),
                },
                "raw": {
                    "name_pt": name_pt if isinstance(name_pt, str) else (name_pt[0] if name_pt else ""),
                    "name_en": name_en if isinstance(name_en, str) else (name_en[0] if name_en else ""),
                },
            })

    OUT.mkdir(parents=True, exist_ok=True)
    _write(OUT / "positions.json", positions)
    _write(OUT / "edges.json", edges)

    n_sub = sum(1 for e in edges if e["edge_type"] == "submission")
    _write(OUT / "metadata.json", {
        "source": "cavani",
        "repo": "https://github.com/fcavani/jiu-jitsu-graph",
        "license": "CC BY-NC 4.0",
        "positions": len(positions),
        "edges": len(edges),
        "submissions": n_sub,
        "rdf_entities": len(entities),
        "errors": len(errors),
    })

    return positions, edges, errors


def _write(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


if __name__ == "__main__":
    positions, edges, errors = parse()
    print(f"cavani: {len(positions)} positions, {len(edges)} edges, "
          f"{len(errors)} errors")
