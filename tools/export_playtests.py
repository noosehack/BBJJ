#!/usr/bin/env python3
"""Parse BLISP playtest output into JSON for the matboard visualizer."""
import json, re, subprocess, sys

BLISP_CMD = [
    "blisp",
    "--load", "matboard/types.blisp",
    "--load", "matboard/radicals.blisp",
    "--load", "matboard/morphisms.blisp",
    "--load", "matboard/resolve.blisp",
    "--load", "matboard/footprints.blisp",
    "--load", "matboard/playtest_harness.blisp",
    "--load", "matboard/playtest_games.blisp",
]

def run_playtests():
    r = subprocess.run(BLISP_CMD, capture_output=True, text=True)
    return (r.stdout + r.stderr).splitlines()

def parse(lines):
    games = []
    current = None
    for raw in lines:
        line = raw.strip().strip('"').strip()
        m = re.search(r"GAME: (.+?) ══", line)
        if m:
            if current:
                games.append(current)
            current = {"label": m.group(1).strip(), "turns": []}
            continue
        m = re.match(
            r"Turn (\d+): (.+?) vs (.+?) \| (\w+) . (\w+) \| val (.+)", line
        )
        if m and current is not None:
            turn = {
                "turn": int(m.group(1)),
                "mor_a": m.group(2),
                "mor_b": m.group(3),
                "pos_before": m.group(4),
                "pos_after": m.group(5),
                "val": float(m.group(6)),
            }
            current["turns"].append(turn)
            continue
        m = re.match(r"sub=(\d+) mom=(-?\d+) init=(\w+)", line)
        if m and current is not None and current["turns"]:
            t = current["turns"][-1]
            t["sub_threat"] = int(m.group(1))
            t["momentum"] = int(m.group(2))
            t["initiative"] = m.group(3)
            continue
        if "SUBMISSION" in line and current is not None and current["turns"]:
            current["submission_turn"] = current["turns"][-1]["turn"]
            continue
        m = re.search(
            r"Result: (.+?) by (.+?) \| final val A=(.+?) B=(.+?) \| turns=(\d+)",
            line,
        )
        if m and current is not None:
            current["winner"] = m.group(1)
            current["condition"] = m.group(2)
            current["final_val_a"] = float(m.group(3))
            current["final_val_b"] = float(m.group(4))
            current["num_turns"] = int(m.group(5))
    if current:
        games.append(current)
    return games

def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "data/matboard/playtests_p1.json"
    lines = run_playtests()
    games = parse(lines)
    with open(out, "w") as f:
        json.dump({"version": "v4-P1", "games": games}, f, indent=2)
    print(f"Exported {len(games)} games to {out}")

if __name__ == "__main__":
    main()
