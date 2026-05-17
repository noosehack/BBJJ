"""Parse daveyarwood/bjj-graph v2.clj Clojure map into positions.json and edges.json.

The Clojure map has string keys (position names) mapping to maps containing:
- ::transitions → vector of target position names (unlabeled edges)
- ::submission? → true (terminal node)
- Other keys → technique name : target position (labeled edges)

Usage:
    python -m fieldboard.extract.bjj_graph_clj
"""

import json
import re
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
RAW = BASE / "data" / "bjj_graph_clj" / "raw" / "repo" / "src" / "bjj_graph" / "v2.clj"
OUT = BASE / "data" / "bjj_graph_clj" / "parsed"


def parse():
    text = RAW.read_text()
    graphs = _extract_graphs(text)

    positions = []
    edges = []
    errors = []
    pos_ids = {}
    submissions = set()

    for graph_name, graph_data in graphs.items():
        for pos_name, pos_map in graph_data.items():
            if pos_name not in pos_ids:
                pid = f"clj_p{len(positions)}"
                pos_ids[pos_name] = pid
                is_sub = pos_map.get("::submission?", False)
                if is_sub:
                    submissions.add(pos_name)
                positions.append({
                    "id": pid,
                    "name": pos_name,
                    "source": "bjj_graph_clj",
                    "tags": [graph_name],
                    "properties": {
                        "graph": graph_name,
                        "is_submission": is_sub,
                    },
                    "raw": {},
                })

            for key, value in pos_map.items():
                if key == "::transitions":
                    for target in value:
                        if target not in pos_ids:
                            tid = f"clj_p{len(positions)}"
                            pos_ids[target] = tid
                            positions.append({
                                "id": tid,
                                "name": target,
                                "source": "bjj_graph_clj",
                                "tags": [graph_name],
                                "properties": {"graph": graph_name},
                                "raw": {},
                            })

                        edge_type = "submission" if target in submissions else "transition"
                        edges.append({
                            "id": f"clj_e{len(edges)}",
                            "name": f"{pos_name} -> {target}",
                            "source": "bjj_graph_clj",
                            "from_id": pos_ids[pos_name],
                            "from_name": pos_name,
                            "to_id": pos_ids[target],
                            "to_name": target,
                            "edge_type": edge_type,
                            "tags": [graph_name],
                            "properties": {"labeled": False},
                            "raw": {},
                        })

                elif key == "::submission?":
                    pass

                elif isinstance(value, str):
                    target = value
                    if target not in pos_ids:
                        tid = f"clj_p{len(positions)}"
                        pos_ids[target] = tid
                        positions.append({
                            "id": tid,
                            "name": target,
                            "source": "bjj_graph_clj",
                            "tags": [graph_name],
                            "properties": {"graph": graph_name},
                            "raw": {},
                        })

                    name_lower = key.lower()
                    if target in submissions:
                        edge_type = "submission"
                    elif "sweep" in name_lower:
                        edge_type = "sweep"
                    elif "escape" in name_lower:
                        edge_type = "escape"
                    elif "pass" in name_lower:
                        edge_type = "pass"
                    else:
                        edge_type = "transition"

                    edges.append({
                        "id": f"clj_e{len(edges)}",
                        "name": key,
                        "source": "bjj_graph_clj",
                        "from_id": pos_ids[pos_name],
                        "from_name": pos_name,
                        "to_id": pos_ids[target],
                        "to_name": target,
                        "edge_type": edge_type,
                        "tags": [graph_name],
                        "properties": {"labeled": True},
                        "raw": {},
                    })

    # Second pass: fix submission edges (targets now known)
    for e in edges:
        if e["to_name"] in submissions and e["edge_type"] != "submission":
            e["edge_type"] = "submission"

    OUT.mkdir(parents=True, exist_ok=True)
    _write(OUT / "positions.json", positions)
    _write(OUT / "edges.json", edges)

    n_sub = sum(1 for e in edges if e["edge_type"] == "submission")
    _write(OUT / "metadata.json", {
        "source": "bjj_graph_clj",
        "repo": "https://github.com/daveyarwood/bjj-graph",
        "license": "None specified",
        "positions": len(positions),
        "edges": len(edges),
        "submissions": n_sub,
        "graphs": list(graphs.keys()),
        "errors": len(errors),
    })

    return positions, edges, errors


def _extract_graphs(text):
    """Find all (def ...) forms and parse each Clojure map."""
    graphs = {}

    # Remove comments
    text_clean = re.sub(r';;.*$', '', text, flags=re.MULTILINE)

    # Find (def name { ... }) forms by matching balanced braces
    pattern = re.compile(r'\(def\s+([\w-]+)\s*\n?\s*\{')
    for m in pattern.finditer(text_clean):
        name = m.group(1)
        start = m.end() - 1  # at the opening {
        body = _extract_balanced(text_clean, start, '{', '}')
        if body:
            try:
                parsed = _parse_top_level_map(body)
                graphs[name] = parsed
            except Exception:
                pass

    # Handle merged: (def name (coll/deep-merge a b c))
    merge_pattern = re.compile(
        r'\(def\s+([\w-]+)\s*\n?\s*\(coll/deep-merge\s+([\w\s-]+)\)')
    for m in merge_pattern.finditer(text_clean):
        name = m.group(1)
        parts = m.group(2).strip().split()
        merged = {}
        for part in parts:
            if part in graphs:
                merged.update(graphs[part])
        if merged:
            graphs[name] = merged

    return graphs


def _extract_balanced(text, start, open_ch, close_ch):
    if text[start] != open_ch:
        return None
    depth = 0
    i = start
    while i < len(text):
        if text[i] == '"':
            i += 1
            while i < len(text) and text[i] != '"':
                if text[i] == '\\':
                    i += 1
                i += 1
            i += 1
            continue
        if text[i] == open_ch:
            depth += 1
        elif text[i] == close_ch:
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
        i += 1
    return None


def _parse_top_level_map(text):
    """Parse a Clojure map where keys are strings and values are inner maps."""
    result = {}
    text = text.strip()
    if text.startswith('{'):
        text = text[1:]
    if text.endswith('}'):
        text = text[:-1]

    tokens = _tokenize(text)
    i = 0
    current_key = None

    while i < len(tokens):
        tok = tokens[i]
        if tok == '{':
            # Parse inner map
            inner_tokens = []
            depth = 1
            i += 1
            while i < len(tokens) and depth > 0:
                if tokens[i] == '{':
                    depth += 1
                elif tokens[i] == '}':
                    depth -= 1
                    if depth == 0:
                        break
                inner_tokens.append(tokens[i])
                i += 1
            i += 1  # skip closing }
            if current_key is not None:
                result[current_key] = _tokens_to_map(inner_tokens)
                current_key = None
        elif tok == '}':
            i += 1
        elif current_key is None:
            current_key = tok
            i += 1
        else:
            # Value is a string (shouldn't happen at top level but handle it)
            i += 1
            current_key = None

    return result


def _parse_clj_map(text):
    """Simple Clojure map parser for string-keyed maps."""
    result = {}
    text = text.strip()
    if text.startswith("{"):
        text = text[1:]
    if text.endswith("}"):
        text = text[:-1]

    # Remove comments
    text = re.sub(r';;.*$', '', text, flags=re.MULTILINE)

    tokens = _tokenize(text)
    i = 0
    current_key = None

    while i < len(tokens):
        token = tokens[i]

        if token == "::transitions":
            i += 1
            vec, i = _parse_vector(tokens, i)
            result["::transitions"] = vec
        elif token == "::submission?":
            i += 1
            if i < len(tokens) and tokens[i] == "true":
                result["::submission?"] = True
                i += 1
        elif current_key is None:
            current_key = token
            i += 1
        else:
            result[current_key] = token
            current_key = None
            i += 1

    return result


def _tokenize(text):
    tokens = []
    i = 0
    while i < len(text):
        if text[i] in ' \t\n\r,':
            i += 1
        elif text[i] == '"':
            j = i + 1
            while j < len(text) and text[j] != '"':
                if text[j] == '\\':
                    j += 1
                j += 1
            tokens.append(text[i + 1:j])
            i = j + 1
        elif text[i:i + 2] == '::':
            j = i + 2
            while j < len(text) and text[j] not in ' \t\n\r,{}[]':
                j += 1
            tokens.append(text[i:j])
            i = j
        elif text[i] == '[':
            tokens.append('[')
            i += 1
        elif text[i] == ']':
            tokens.append(']')
            i += 1
        elif text[i] == '{':
            tokens.append('{')
            i += 1
        elif text[i] == '}':
            tokens.append('}')
            i += 1
        else:
            j = i
            while j < len(text) and text[j] not in ' \t\n\r,{}[]"':
                j += 1
            tokens.append(text[i:j])
            i = j

    return tokens


def _parse_vector(tokens, i):
    if i >= len(tokens) or tokens[i] != '[':
        return [], i
    i += 1
    items = []
    while i < len(tokens) and tokens[i] != ']':
        items.append(tokens[i])
        i += 1
    if i < len(tokens):
        i += 1
    return items, i


def _parse_clj_top_level(text):
    """Parse a top-level Clojure map where keys are strings and values are maps."""
    result = {}
    text = re.sub(r';;.*$', '', text, flags=re.MULTILINE)

    # Find the outer braces
    start = text.index('{')
    depth = 0
    entries = []
    current_key = None
    i = start + 1

    tokens = _tokenize(text[start + 1:])
    ti = 0
    while ti < len(tokens):
        if tokens[ti] == '}' and depth == 0:
            break
        elif tokens[ti] == '{':
            inner_start = ti
            depth = 1
            ti += 1
            while ti < len(tokens) and depth > 0:
                if tokens[ti] == '{':
                    depth += 1
                elif tokens[ti] == '}':
                    depth -= 1
                ti += 1
            inner_tokens = tokens[inner_start + 1:ti - 1]
            if current_key is not None:
                result[current_key] = _tokens_to_map(inner_tokens)
                current_key = None
        else:
            if current_key is None:
                current_key = tokens[ti]
            ti += 1

    return result


def _tokens_to_map(tokens):
    result = {}
    i = 0
    current_key = None
    while i < len(tokens):
        if tokens[i] == "::transitions":
            i += 1
            vec, i = _parse_vector(tokens, i)
            result["::transitions"] = vec
        elif tokens[i] == "::submission?":
            i += 1
            if i < len(tokens) and tokens[i] == "true":
                result["::submission?"] = True
                i += 1
        elif tokens[i] in ('{', '}'):
            i += 1
        elif current_key is None:
            current_key = tokens[i]
            i += 1
        else:
            result[current_key] = tokens[i]
            current_key = None
            i += 1
    return result


def _write(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


if __name__ == "__main__":
    positions, edges, errors = parse()
    print(f"bjj-graph-clj: {len(positions)} positions, {len(edges)} edges, "
          f"{len(errors)} errors")
    n_sub = sum(1 for e in edges if e["edge_type"] == "submission")
    print(f"  Submissions: {n_sub}")
