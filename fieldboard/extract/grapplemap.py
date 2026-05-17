"""Parse GrappleMap.txt into positions.json and edges.json.

GrappleMap format:
- Entry = name line + tags + optional properties/refs/notes + indented data lines
- Position = 1 frame (4 data lines), no properties line
- Transition = properties line + N frames (4N data lines)
- `...` separators split an entry into multiple transition variants
  (each variant gets its own properties/refs/data block)

Usage:
    python -m fieldboard.extract.grapplemap
"""

import json
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
RAW = BASE / "data" / "grapplemap" / "raw" / "repo" / "GrappleMap.txt"
OUT = BASE / "data" / "grapplemap" / "parsed"

SUB_KEYWORDS = {
    "armbar", "triangle", "choke", "kimura", "americana", "guillotine",
    "darce", "anaconda", "heel_hook", "knee_bar", "toe_hold", "ezekiel",
    "omoplata", "arm_triangle", "gogoplata", "twister", "calf_slicer",
    "wrist_lock", "neck_crank", "rear_naked_choke", "peruvian_necktie",
    "north_south_choke", "baseball_bat_choke", "loop_choke", "cross_choke",
    "bow_and_arrow", "clock_choke", "paper_cutter", "monoplata",
    "baratoplata", "buggy_choke", "d_arce", "von_flue",
}


def _is_name_line(line):
    if not line or line[0] in (' ', '\t'):
        return False
    for prefix in ("tags:", "properties:", "ref:", "todo:", "note:"):
        if line.startswith(prefix):
            return False
    if line.startswith("..."):
        return False
    return True


def _frame_hash(frame_lines):
    return "|".join(frame_lines)


def _data_to_frames(data_lines):
    frames = []
    for i in range(0, len(data_lines) - 3, 4):
        frames.append(data_lines[i:i + 4])
    return frames


def _classify_edge(name, tags, properties):
    name_lower = name.lower()
    tag_set = set(tags)
    if tag_set & SUB_KEYWORDS:
        return "submission"
    for kw in SUB_KEYWORDS:
        if kw.replace("_", " ") in name_lower:
            return "submission"
    if "sweep" in properties:
        return "sweep"
    if "sweep" in name_lower:
        return "sweep"
    return "transition"


def parse():
    text = RAW.read_text()
    lines = text.splitlines()

    # Phase 1: split into top-level entries (name → next name)
    entry_starts = []
    for i, line in enumerate(lines):
        if _is_name_line(line):
            entry_starts.append(i)

    raw_entries = []
    for idx, start in enumerate(entry_starts):
        end = entry_starts[idx + 1] if idx + 1 < len(entry_starts) else len(lines)
        raw_entries.append({"start": start, "lines": lines[start:end]})

    # Phase 2: parse each entry
    positions = []
    edges = []
    errors = []
    pos_frames = {}

    for entry in raw_entries:
        try:
            name, tags, blocks = _parse_entry_blocks(entry["lines"])
        except Exception as e:
            errors.append({"line": entry["start"] + 1, "error": str(e)})
            continue

        # A block with no properties line and exactly 1 frame = position
        # A block with a properties line or >1 frame = transition
        if len(blocks) == 1 and not blocks[0]["properties"] and len(blocks[0]["frames"]) == 1:
            pid = f"gm_p{len(positions)}"
            fh = _frame_hash(blocks[0]["frames"][0])
            positions.append({
                "id": pid,
                "name": name,
                "source": "grapplemap",
                "tags": tags,
                "properties": {},
                "raw": {
                    "line_nr": entry["start"] + 1,
                    "frame_hash": fh,
                },
            })
            pos_frames[fh] = (pid, name)
        else:
            for bi, block in enumerate(blocks):
                if not block["frames"]:
                    errors.append({"line": entry["start"] + 1,
                                   "error": f"block {bi} has no frames"})
                    continue

                first_fh = _frame_hash(block["frames"][0])
                last_fh = _frame_hash(block["frames"][-1])
                from_pos = pos_frames.get(first_fh, (None, None))
                to_pos = pos_frames.get(last_fh, (None, None))
                edge_type = _classify_edge(name, tags, block["properties"])

                edges.append({
                    "id": f"gm_e{len(edges)}",
                    "name": name,
                    "source": "grapplemap",
                    "from_id": from_pos[0],
                    "from_name": from_pos[1],
                    "to_id": to_pos[0],
                    "to_name": to_pos[1],
                    "edge_type": edge_type,
                    "tags": tags,
                    "properties": {
                        "who_moves": block["properties"],
                        "frame_count": len(block["frames"]),
                    },
                    "raw": {
                        "line_nr": entry["start"] + 1,
                        "variant": bi,
                        "refs": block["refs"],
                    },
                })

    OUT.mkdir(parents=True, exist_ok=True)
    _write(OUT / "positions.json", positions)
    _write(OUT / "edges.json", edges)
    _write(OUT / "metadata.json", {
        "source": "grapplemap",
        "repo": "https://github.com/Eelis/GrappleMap",
        "license": "Public Domain",
        "raw_file": "GrappleMap.txt",
        "raw_lines": len(lines),
        "entries_parsed": len(raw_entries),
        "positions": len(positions),
        "edges": len(edges),
        "submissions": sum(1 for e in edges if e["edge_type"] == "submission"),
        "sweeps": sum(1 for e in edges if e["edge_type"] == "sweep"),
        "errors": len(errors),
        "error_details": errors[:20],
        "unmatched_from": sum(1 for e in edges if e["from_id"] is None),
        "unmatched_to": sum(1 for e in edges if e["to_id"] is None),
    })

    return positions, edges, errors


def _parse_entry_blocks(entry_lines):
    """Parse an entry into name, tags, and a list of blocks.

    Each block represents one transition variant (or the single position).
    Blocks are separated by `...` lines.
    """
    name = entry_lines[0].replace("\\n", " / ")
    tags = []
    blocks = []
    current_block = {"properties": [], "refs": [], "data_lines": [], "frames": []}

    i = 1
    while i < len(entry_lines):
        line = entry_lines[i]

        if line.startswith("tags:"):
            tags = line[5:].strip().split()
        elif line.startswith("properties:"):
            current_block["properties"] = line[11:].strip().split()
        elif line.startswith("ref:"):
            current_block["refs"].append(line[4:].strip())
        elif line.startswith("todo:") or line.startswith("note:"):
            pass
        elif line.startswith("..."):
            current_block["frames"] = _data_to_frames(current_block["data_lines"])
            blocks.append(current_block)
            current_block = {"properties": [], "refs": [], "data_lines": [], "frames": []}
        elif line.startswith("    "):
            current_block["data_lines"].append(line.strip())
        i += 1

    current_block["frames"] = _data_to_frames(current_block["data_lines"])
    blocks.append(current_block)

    # Remove empty leading block if first block before any data is empty
    blocks = [b for b in blocks if b["frames"] or b["properties"]]
    if not blocks:
        blocks = [{"properties": [], "refs": [], "data_lines": [], "frames": []}]

    # Clean up: remove data_lines from output
    for b in blocks:
        del b["data_lines"]

    return name, tags, blocks


def _write(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


if __name__ == "__main__":
    positions, edges, errors = parse()
    print(f"GrappleMap: {len(positions)} positions, {len(edges)} edges, "
          f"{len(errors)} errors")
    unmatched_from = sum(1 for e in edges if e["from_id"] is None)
    unmatched_to = sum(1 for e in edges if e["to_id"] is None)
    print(f"  From matched: {len(edges) - unmatched_from}/{len(edges)}")
    print(f"  To matched: {len(edges) - unmatched_to}/{len(edges)}")
    subs = sum(1 for e in edges if e["edge_type"] == "submission")
    sweeps = sum(1 for e in edges if e["edge_type"] == "sweep")
    print(f"  Types: {len(edges) - subs - sweeps} transition, "
          f"{subs} submission, {sweeps} sweep")
    if errors:
        print(f"  First errors:")
        for e in errors[:5]:
            print(f"    Line {e['line']}: {e['error']}")
