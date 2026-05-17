"""Milestone 4: Curriculum Spine Selection.

Selects ~25 canonical roads from candidate_roads.json + source data.
Maps to fieldboard coordinates, analyzes checkpoints and failure topology,
classifies into spine / branch / network.

Output:
    fieldboard/data/curriculum_spine.json
    fieldboard/data/curriculum_spine_report.md

Usage:
    python -m fieldboard.curriculum_spine
"""

import json
from pathlib import Path

BASE = Path(__file__).resolve().parent
DATA = BASE / "data"

SOURCES = ["grapplemap", "bjjgraph", "flowstate", "bjj_graph_clj", "fsm"]

# ── Fieldboard coordinate mapping ──────────────────────────────────────

POSITION_MAP = {
    "closed guard":     "CGRD",
    "open guard":       "OGRD",
    "half guard":       "HGRD",
    "butterfly guard":  "OGRD.Butterfly",
    "butterfly":        "OGRD.Butterfly",
    "mount":            "MNT",
    "side control":     "SCTR",
    "back control":     "BCTR",
    "turtle":           "TRTL",
    "knee on belly":    "SCTR.KOB",
    "north-south":      "SCTR.NS",
    "standing":         "OGRD.Standing",
    "quarter guard":    "HGRD.Quarter",
    "deep half guard":  "HGRD.Deep",
    "knee shield":      "HGRD.KneeShield",
    "de la riva":       "OGRD.DLR",
    "reverse de la riva": "OGRD.RDLR",
    "x guard":          "OGRD.XGRD",
    "single leg x":     "OGRD.SLX",
    "50-50":            "OGRD.5050",
    "lasso":            "OGRD.Lasso",
    "spider":           "OGRD.Spider",
    "rubber guard":     "CGRD.Rubber",
    "collar sleeve":    "OGRD.ColSlv",
    "lapel guard":      "OGRD.Lapel",
}

ACTION_MAP = {
    "submission": "SUB",
    "sweep":      "SWP",
    "pass":       "TRZ",
    "transition": "TRZ",
    "escape":     "TRZ",
    "control":    "CTRL",
}


# ── Selected roads ─────────────────────────────────────────────────────
# Each road is manually curated from the candidate data + source edges.

SELECTED_ROADS = [

    # ── SPINE ROADS (beginner highways) ─────────────────────────────

    {
        "id": "S1",
        "name": "Closed Guard Hip Bump Sweep to Mount Armbar",
        "tier": "spine",
        "sequence": [
            {"position": "Closed Guard", "action": "CTRL", "detail": "posture control, collar grips"},
            {"position": "Mount", "action": "SWP", "detail": "hip bump sweep / scissor sweep"},
            {"position": "Mount", "action": "CTRL", "detail": "base, grapevines or heels"},
            {"position": "Armbar", "action": "SUB", "detail": "isolate arm, hips high, extend"},
        ],
        "fieldboard": ["CGRD.CTRL", "MNT.SWP", "MNT.CTRL", "MNT.SUB"],
        "sources": ["bjjgraph", "flowstate", "fsm"],
        "source_techniques": {
            "bjjgraph": "Hip Bump Sweep / 100% Sweep → Armbar from Mount",
            "flowstate": "Closed guard → Mount top → Armbar",
            "fsm": "FullGuard → Mount",
        },
        "checkpoints": {
            "control": ["Posture break in closed guard", "Mount base stabilization"],
            "stabilization": ["Secure mount before attacking — grapevines or heel hooks on hips"],
            "transition": ["Hip bump mechanic: sit up, post hand, sweep over shoulder"],
            "submission": ["Isolate arm → figure-four grip → hips high → lean back to extend"],
        },
        "failure": {
            "sweep_fails": "Still in closed guard (safe)",
            "mount_lost": "Falls to half guard or guard — positions already taught",
            "armbar_fails": "Opponent stacks — return to mount or closed guard",
            "classification": "safe",
        },
        "mechanics": ["hip escape", "bridge", "posture control", "arm isolation"],
        "duality": "Op learns: posture defense in guard, mount escape, armbar defense",
    },

    {
        "id": "S2",
        "name": "Closed Guard Arm Drag to Back Control RNC",
        "tier": "spine",
        "sequence": [
            {"position": "Closed Guard", "action": "CTRL", "detail": "break posture, wrist control"},
            {"position": "Back Control", "action": "SWP", "detail": "arm drag, climb to back"},
            {"position": "Back Control", "action": "CTRL", "detail": "seatbelt grip, hooks in"},
            {"position": "Rear Naked Choke", "action": "SUB", "detail": "hand fight, sink choke"},
        ],
        "fieldboard": ["CGRD.CTRL", "BCTR.SWP", "BCTR.CTRL", "BCTR.SUB"],
        "sources": ["bjjgraph", "flowstate", "fsm"],
        "source_techniques": {
            "bjjgraph": "Arm Drag Sweep → Rear Naked Choke",
            "flowstate": "Closed guard → Back control → RNC",
            "fsm": "FullGuard → BackControl → RNC",
        },
        "checkpoints": {
            "control": ["Posture break in closed guard", "Seatbelt + hooks in back control"],
            "stabilization": ["Secure seatbelt grip before attacking choke"],
            "transition": ["Arm drag: 2-on-1, pull arm across, hip out, climb behind"],
            "submission": ["Clear collar defense → slide choking arm under chin → lock figure-four → squeeze"],
        },
        "failure": {
            "drag_fails": "Still in closed guard (safe)",
            "back_lost": "Opponent turns in — land in mount or closed guard (safe)",
            "rnc_fails": "Opponent defends chin — maintain back control, re-attack",
            "classification": "safe",
        },
        "mechanics": ["arm drag", "hip escape", "seatbelt", "back hooks"],
        "duality": "Op learns: posture in guard, back escape (turn to guard), RNC defense",
    },

    {
        "id": "S3",
        "name": "Half Guard Pass to Side Control Americana",
        "tier": "spine",
        "sequence": [
            {"position": "Half Guard", "action": "CTRL", "detail": "crossface, underhook battle"},
            {"position": "Side Control", "action": "TRZ", "detail": "knee slice / crossface pass"},
            {"position": "Side Control", "action": "CTRL", "detail": "crossface + underhook, chest pressure"},
            {"position": "Americana", "action": "SUB", "detail": "isolate near arm, figure-four, paint brush"},
        ],
        "fieldboard": ["HGRD.CTRL", "SCTR.TRZ", "SCTR.CTRL", "SCTR.SUB"],
        "sources": ["bjjgraph", "flowstate", "bjj_graph_clj"],
        "source_techniques": {
            "bjjgraph": "Knee Slice Pass / Crossface Pass → Americana from Side Control",
            "flowstate": "Half guard → Side control → Americana",
            "bjj_graph_clj": "Half Guard → Side Mount",
        },
        "checkpoints": {
            "control": ["Win underhook in half guard", "Crossface + chest pressure in side control"],
            "stabilization": ["Flatten opponent before passing — deny underhook"],
            "transition": ["Knee slice: free trapped leg, slide knee across, clear to side control"],
            "submission": ["Pin wrist to mat → figure-four grip → paint brush away from head"],
        },
        "failure": {
            "pass_fails": "Still in half guard top (safe)",
            "side_lost": "Opponent re-guards — back to half guard (safe)",
            "americana_fails": "Opponent straightens arm — transition to armbar or maintain control",
            "classification": "safe",
        },
        "mechanics": ["crossface", "underhook", "knee slice", "figure-four"],
        "duality": "Op learns: half guard retention, side control escape, americana defense",
    },

    {
        "id": "S4",
        "name": "Butterfly Sweep to Mount",
        "tier": "spine",
        "sequence": [
            {"position": "Butterfly Guard", "action": "CTRL", "detail": "double underhooks, head position"},
            {"position": "Mount", "action": "SWP", "detail": "elevator sweep — hook, off-balance, lift"},
            {"position": "Mount", "action": "CTRL", "detail": "stabilize base"},
        ],
        "fieldboard": ["OGRD.Butterfly.CTRL", "MNT.SWP", "MNT.CTRL"],
        "sources": ["bjjgraph", "fsm"],
        "source_techniques": {
            "bjjgraph": "Basic Butterfly Sweep / Elevator Sweep → Mount",
            "fsm": "Butterfly → Mount",
        },
        "checkpoints": {
            "control": ["Double underhooks seated, head on chest side"],
            "stabilization": ["Land in mount, immediately establish base"],
            "transition": ["Off-balance to one side → hook lift → roll over → land in mount"],
            "submission": [],
        },
        "failure": {
            "sweep_fails": "Still seated in butterfly (safe — re-grip, re-try)",
            "mount_lost": "Opponent bridges — fall to guard (safe)",
            "classification": "safe",
        },
        "mechanics": ["underhook", "butterfly hook", "off-balance", "mount base"],
        "duality": "Op learns: butterfly guard passing, mount escape",
    },

    {
        "id": "S5",
        "name": "Open Guard Scissor Sweep to Mount",
        "tier": "spine",
        "sequence": [
            {"position": "Open Guard", "action": "CTRL", "detail": "collar + sleeve grip"},
            {"position": "Mount", "action": "SWP", "detail": "scissor sweep — shin across, pull, kick"},
            {"position": "Mount", "action": "CTRL", "detail": "stabilize base"},
        ],
        "fieldboard": ["OGRD.CTRL", "MNT.SWP", "MNT.CTRL"],
        "sources": ["bjjgraph", "bjj_graph_clj"],
        "source_techniques": {
            "bjjgraph": "Scissor Sweep from Open Guard → Mount",
            "bjj_graph_clj": "Open Guard → Mount",
        },
        "checkpoints": {
            "control": ["Collar grip + sleeve grip, shin across belly"],
            "stabilization": ["Follow the sweep — post immediately on landing in mount"],
            "transition": ["Shin across belly → pull collar down → kick bottom leg → roll over"],
            "submission": [],
        },
        "failure": {
            "sweep_fails": "Still in open guard (safe — retain grips)",
            "classification": "safe",
        },
        "mechanics": ["scissor motion", "collar grip", "sleeve control"],
        "duality": "Op learns: open guard passing, scissor sweep defense (posture + base)",
    },

    {
        "id": "S6",
        "name": "Side Control to Mount Progression",
        "tier": "spine",
        "sequence": [
            {"position": "Side Control", "action": "CTRL", "detail": "crossface + underhook, heavy hips"},
            {"position": "Knee on Belly", "action": "TRZ", "detail": "insert knee, pressure"},
            {"position": "Mount", "action": "TRZ", "detail": "swing leg over, settle base"},
            {"position": "Mount", "action": "CTRL", "detail": "grapevines, posture"},
        ],
        "fieldboard": ["SCTR.CTRL", "SCTR.KOB.TRZ", "MNT.TRZ", "MNT.CTRL"],
        "sources": ["bjjgraph", "flowstate"],
        "source_techniques": {
            "bjjgraph": "Side Control → Knee on Belly → Mount / Arm Extraction to Mount",
            "flowstate": "Side control top → Mount top",
        },
        "checkpoints": {
            "control": ["Crossface + chest pressure in side control", "Knee pressure in KOB", "Mount base"],
            "stabilization": ["Each position is stable — can pause and consolidate"],
            "transition": ["Side → KOB: slide knee onto belly. KOB → Mount: swing far leg over"],
            "submission": [],
        },
        "failure": {
            "kob_lost": "Falls back to side control (safe)",
            "mount_lost": "Falls to half guard (safe — already taught)",
            "classification": "safe",
        },
        "mechanics": ["hip pressure", "knee ride", "weight distribution"],
        "duality": "Op learns: side control escape (frame, hip escape, re-guard), KOB escape",
    },

    {
        "id": "S7",
        "name": "Closed Guard Triangle Choke",
        "tier": "spine",
        "sequence": [
            {"position": "Closed Guard", "action": "CTRL", "detail": "posture break, control wrists"},
            {"position": "Triangle Setup", "action": "TRZ", "detail": "isolate one arm, hips up, leg over shoulder"},
            {"position": "Triangle Choke", "action": "SUB", "detail": "lock triangle, angle, squeeze"},
        ],
        "fieldboard": ["CGRD.CTRL", "CGRD.TRZ", "CGRD.SUB"],
        "sources": ["bjjgraph", "grapplemap", "flowstate"],
        "source_techniques": {
            "bjjgraph": "Cross Collar Choke / Triangle from Closed Guard",
            "grapplemap": "full guard → triangle",
            "flowstate": "Closed guard → Triangle",
        },
        "checkpoints": {
            "control": ["Posture break, wrist isolation"],
            "stabilization": ["Lock triangle figure-four before finishing"],
            "transition": ["Push one arm across → hips up → leg over far shoulder → lock ankles"],
            "submission": ["Cut angle → pull head down → squeeze knees"],
        },
        "failure": {
            "setup_fails": "Still in closed guard (safe)",
            "triangle_fails": "Opponent postures out of half-locked triangle — return to guard",
            "stacking": "Opponent stacks — can unlock and return to guard, or sweep to mount",
            "classification": "safe",
        },
        "mechanics": ["hip elevation", "angle cutting", "leg dexterity"],
        "duality": "Op learns: posture maintenance, triangle defense (stack, posture, hide arm)",
    },

    {
        "id": "S8",
        "name": "Mount Cross Collar Choke",
        "tier": "spine",
        "sequence": [
            {"position": "Mount", "action": "CTRL", "detail": "high mount, walk hands up"},
            {"position": "Mount", "action": "SUB", "detail": "feed first grip deep, second grip, squeeze"},
        ],
        "fieldboard": ["MNT.CTRL", "MNT.SUB"],
        "sources": ["bjjgraph", "flowstate", "grapplemap"],
        "source_techniques": {
            "bjjgraph": "Cross Collar Choke from High Mount",
            "flowstate": "Mount top → Cross-collar choke",
            "grapplemap": "mount → choke",
        },
        "checkpoints": {
            "control": ["High mount — walk knees to armpits"],
            "stabilization": ["Secure first grip deep in collar before attacking"],
            "transition": [],
            "submission": ["First hand deep in cross collar → second hand in → squeeze elbows together"],
        },
        "failure": {
            "grip_stripped": "Still in mount (safe)",
            "bridged_off": "Falls to guard (safe — already taught)",
            "classification": "safe",
        },
        "mechanics": ["mount pressure", "collar grip", "weight forward"],
        "duality": "Op learns: mount escape (trap and roll, elbow-knee), choke defense",
    },

    # ── BRANCH ROADS (intermediate expansions) ──────────────────────

    {
        "id": "B1",
        "name": "Half Guard Underhook Sweep to Mount",
        "tier": "branch",
        "sequence": [
            {"position": "Half Guard", "action": "CTRL", "detail": "win underhook, come to knees"},
            {"position": "Mount", "action": "SWP", "detail": "John Wayne sweep / underhook sweep"},
        ],
        "fieldboard": ["HGRD.CTRL", "MNT.SWP"],
        "sources": ["bjjgraph", "flowstate"],
        "source_techniques": {
            "bjjgraph": "John Wayne Sweep → Mount",
            "flowstate": "Half guard bottom → Mount top",
        },
        "checkpoints": {
            "control": ["Win underhook — get to hip, head under chin"],
            "stabilization": [],
            "transition": ["Come to knees → drive forward → sweep over trapped leg → land in mount"],
            "submission": [],
        },
        "failure": {
            "underhook_lost": "Still in half guard bottom (safe — re-pummel)",
            "sweep_fails": "Dogfight position — scramble back to half guard or re-attack",
            "classification": "recoverable",
        },
        "mechanics": ["underhook", "hip movement", "drive"],
        "duality": "Op learns: half guard top control, whizzer counter",
    },

    {
        "id": "B2",
        "name": "Half Guard to Side Control to Back Control",
        "tier": "branch",
        "sequence": [
            {"position": "Half Guard", "action": "CTRL", "detail": "top position, crossface"},
            {"position": "Side Control", "action": "TRZ", "detail": "pass half guard"},
            {"position": "Back Control", "action": "TRZ", "detail": "opponent turns away → take back"},
            {"position": "Rear Naked Choke", "action": "SUB", "detail": "seatbelt → RNC"},
        ],
        "fieldboard": ["HGRD.CTRL", "SCTR.TRZ", "BCTR.TRZ", "BCTR.SUB"],
        "sources": ["bjjgraph", "flowstate"],
        "source_techniques": {
            "bjjgraph": "Half Guard Pass → Side Control → Back Control → RNC",
            "flowstate": "Half guard → Side control → Back control",
        },
        "checkpoints": {
            "control": ["Crossface in half guard top", "Chest pressure in side control", "Seatbelt + hooks"],
            "stabilization": ["Secure each position before advancing"],
            "transition": ["Pass half → settle side control → opponent turns → slide hooks in"],
            "submission": ["Seatbelt → hand fight → sink RNC"],
        },
        "failure": {
            "pass_fails": "Still in half guard top (safe)",
            "back_lost": "Opponent turns in — land in mount or side control (safe)",
            "classification": "safe",
        },
        "mechanics": ["passing", "back take timing", "seatbelt"],
        "duality": "Op learns: half guard retention, side escape, back escape",
    },

    {
        "id": "B3",
        "name": "Closed Guard Flower Sweep to Mount",
        "tier": "branch",
        "sequence": [
            {"position": "Closed Guard", "action": "CTRL", "detail": "collar + sleeve grip"},
            {"position": "Mount", "action": "SWP", "detail": "flower sweep — collar pull, leg kick-over"},
        ],
        "fieldboard": ["CGRD.CTRL", "MNT.SWP"],
        "sources": ["bjjgraph"],
        "source_techniques": {
            "bjjgraph": "Flower Sweep → Mount",
        },
        "checkpoints": {
            "control": ["Deep collar grip + same-side sleeve grip"],
            "stabilization": [],
            "transition": ["Pull collar → kick far leg over → roll into mount"],
            "submission": [],
        },
        "failure": {
            "sweep_fails": "Still in closed guard (safe)",
            "classification": "safe",
        },
        "mechanics": ["collar grip", "leg dexterity", "momentum"],
        "duality": "Op learns: base and posture in closed guard",
    },

    {
        "id": "B4",
        "name": "Side Control Arm Triangle",
        "tier": "branch",
        "sequence": [
            {"position": "Side Control", "action": "CTRL", "detail": "heavy crossface, far underhook"},
            {"position": "Arm Triangle Setup", "action": "TRZ", "detail": "drive head to far side, lock head+arm"},
            {"position": "Arm Triangle", "action": "SUB", "detail": "hop to mount side, squeeze"},
        ],
        "fieldboard": ["SCTR.CTRL", "SCTR.TRZ", "SCTR.SUB"],
        "sources": ["bjjgraph"],
        "source_techniques": {
            "bjjgraph": "Arm Triangle from Top → Arm Triangle Finish",
        },
        "checkpoints": {
            "control": ["Heavy crossface — opponent's chin forced to far side"],
            "stabilization": ["Lock figure-four around head+arm before moving"],
            "transition": ["Walk around to opposite side or hop to mount → squeeze"],
            "submission": ["Gable grip → chest to floor → squeeze elbows"],
        },
        "failure": {
            "setup_fails": "Still in side control (safe)",
            "choke_fails": "Maintain side control — re-attack or transition",
            "classification": "safe",
        },
        "mechanics": ["crossface", "head-arm control", "squeeze mechanics"],
        "duality": "Op learns: frame defense, chin tuck, arm extraction",
    },

    {
        "id": "B5",
        "name": "Kimura Sweep from Closed Guard",
        "tier": "branch",
        "sequence": [
            {"position": "Closed Guard", "action": "CTRL", "detail": "break posture, wrist control"},
            {"position": "Kimura Grip", "action": "TRZ", "detail": "2-on-1 figure-four on far wrist"},
            {"position": "Mount or Side Control", "action": "SWP", "detail": "hip out → sweep with kimura grip"},
        ],
        "fieldboard": ["CGRD.CTRL", "CGRD.TRZ", "MNT.SWP"],
        "sources": ["bjjgraph"],
        "source_techniques": {
            "bjjgraph": "Kimura Sweep → Mount / Side Control",
        },
        "checkpoints": {
            "control": ["Posture break, isolate wrist"],
            "stabilization": ["Secure kimura grip — figure-four is locked before sweeping"],
            "transition": ["Hip out to kimura side → use grip leverage to sweep → land on top"],
            "submission": [],
        },
        "failure": {
            "grip_fails": "Still in closed guard (safe)",
            "sweep_fails": "Retain guard with kimura grip — can transition to armbar or triangle",
            "classification": "safe",
        },
        "mechanics": ["kimura grip (reusable — appears in half guard, side control)", "hip escape"],
        "duality": "Op learns: hand-on-mat defense, posture in guard",
    },

    {
        "id": "B6",
        "name": "Turtle to Back Take",
        "tier": "branch",
        "sequence": [
            {"position": "Turtle", "action": "CTRL", "detail": "opponent turtled, top position"},
            {"position": "Back Control", "action": "TRZ", "detail": "seatbelt → insert hooks"},
            {"position": "Rear Naked Choke", "action": "SUB", "detail": "hand fight → RNC"},
        ],
        "fieldboard": ["TRTL.CTRL", "BCTR.TRZ", "BCTR.SUB"],
        "sources": ["bjjgraph", "flowstate"],
        "source_techniques": {
            "bjjgraph": "Chair Sit to Back / Seatbelt from Turtle → RNC",
            "flowstate": "Turtle → Back control → RNC",
        },
        "checkpoints": {
            "control": ["Chest-to-back contact, seatbelt established"],
            "stabilization": ["Seatbelt first → then insert hooks one at a time"],
            "transition": ["Seatbelt grip → hip to mat → insert bottom hook → top hook"],
            "submission": ["Hand fight to clear collar grip → slide arm under chin → lock RNC"],
        },
        "failure": {
            "back_take_fails": "Opponent sits out — scramble to side control or re-engage turtle (recoverable)",
            "hooks_lost": "Opponent rolls — can land in mount if hooks are lost (safe)",
            "classification": "recoverable",
        },
        "mechanics": ["seatbelt", "hook insertion", "chair sit"],
        "duality": "Op learns: turtle defense (granby roll, sit-out, stand up)",
    },

    {
        "id": "B7",
        "name": "Open Guard Pass to Side Control",
        "tier": "branch",
        "sequence": [
            {"position": "Open Guard", "action": "CTRL", "detail": "standing, grip fighting"},
            {"position": "Side Control", "action": "TRZ", "detail": "toreando / over-under pass"},
            {"position": "Side Control", "action": "CTRL", "detail": "settle crossface + underhook"},
        ],
        "fieldboard": ["OGRD.CTRL", "SCTR.TRZ", "SCTR.CTRL"],
        "sources": ["bjjgraph", "flowstate"],
        "source_techniques": {
            "bjjgraph": "Various passes → Side Control",
            "flowstate": "Open guard → Side control top",
        },
        "checkpoints": {
            "control": ["Grip fighting standing — control pants/ankles", "Crossface in side control"],
            "stabilization": ["Clear legs completely before settling side control"],
            "transition": ["Grip ankles → push legs to one side → pass to opposite side → settle"],
            "submission": [],
        },
        "failure": {
            "pass_fails": "Opponent re-guards — still in open guard (safe)",
            "classification": "safe",
        },
        "mechanics": ["toreando grip", "leg clearing", "pressure passing"],
        "duality": "Op learns: guard retention, re-guarding, grip stripping",
    },

    {
        "id": "B8",
        "name": "Closed Guard to Side Control Sweep",
        "tier": "branch",
        "sequence": [
            {"position": "Closed Guard", "action": "CTRL", "detail": "posture break"},
            {"position": "Side Control", "action": "SWP", "detail": "100% sweep / balloon sweep"},
            {"position": "Side Control", "action": "CTRL", "detail": "settle crossface"},
            {"position": "Americana", "action": "SUB", "detail": "isolate arm, figure-four"},
        ],
        "fieldboard": ["CGRD.CTRL", "SCTR.SWP", "SCTR.CTRL", "SCTR.SUB"],
        "sources": ["bjjgraph", "flowstate"],
        "source_techniques": {
            "bjjgraph": "100% Sweep → Side Control → Americana",
            "flowstate": "Closed guard → Side control → Americana",
        },
        "checkpoints": {
            "control": ["Posture break in guard", "Crossface in side control"],
            "stabilization": ["Settle side control before attacking"],
            "transition": ["Overhook + far leg → bridge and roll → land in side control"],
            "submission": ["Pin wrist → figure-four → paint brush"],
        },
        "failure": {
            "sweep_fails": "Still in closed guard (safe)",
            "side_lost": "Opponent re-guards (safe)",
            "classification": "safe",
        },
        "mechanics": ["bridge and roll", "crossface", "americana"],
        "duality": "Op learns: guard posture, side control escape, americana defense",
    },

    # ── NETWORK ROADS (advanced adaptive) ───────────────────────────

    {
        "id": "N1",
        "name": "Closed Guard Attack Tree: Sweep-or-Submit",
        "tier": "network",
        "sequence": [
            {"position": "Closed Guard", "action": "CTRL", "detail": "posture break"},
            {"position": "Hip Bump / Kimura / Triangle", "action": "TRZ", "detail": "if posture: hip bump. If hand posts: kimura. If arm in: triangle"},
            {"position": "Mount (hip bump) or Guard Sub", "action": "SWP/SUB", "detail": "sweep leads to mount; grip leads to submission"},
        ],
        "fieldboard": ["CGRD.CTRL", "CGRD.TRZ", "MNT.SWP / CGRD.SUB"],
        "sources": ["bjjgraph", "flowstate", "grapplemap"],
        "source_techniques": {
            "bjjgraph": "Hip Bump Sweep / Kimura Sweep / Triangle chain",
            "flowstate": "Closed guard attack tree",
            "grapplemap": "full guard → various",
        },
        "checkpoints": {
            "control": ["Posture break is the root — everything flows from here"],
            "stabilization": [],
            "transition": ["Decision tree: read opponent's reaction, choose branch"],
            "submission": ["Triangle or kimura from failed sweep defense"],
        },
        "failure": {
            "all_fail": "Still in closed guard (safe — the safest position to fail from)",
            "classification": "safe",
        },
        "mechanics": ["posture break", "hip bump", "kimura grip", "triangle legs"],
        "duality": "Op learns: all guard defenses — posture, base, hand placement",
        "branching": {
            "opponent_postures": "hip bump sweep → mount",
            "opponent_hand_posts": "kimura grip → sweep or submit",
            "opponent_arm_across": "triangle → finish or sweep to mount",
        },
    },

    {
        "id": "N2",
        "name": "Mount Attack Cycle: Choke-Armbar Dilemma",
        "tier": "network",
        "sequence": [
            {"position": "Mount", "action": "CTRL", "detail": "high mount, hands walk up"},
            {"position": "Choke or Armbar", "action": "SUB", "detail": "if arms protect neck: armbar. If elbows flare: choke"},
        ],
        "fieldboard": ["MNT.CTRL", "MNT.SUB"],
        "sources": ["bjjgraph", "flowstate", "grapplemap"],
        "source_techniques": {
            "bjjgraph": "Cross Collar Choke / Americana / Armbar from Mount — choice tree",
            "flowstate": "Mount → Americana / Cross-collar choke",
            "grapplemap": "mount → choke / arm-triangle",
        },
        "checkpoints": {
            "control": ["High mount position"],
            "stabilization": [],
            "transition": ["Read opponent's arm defense — neck or arms?"],
            "submission": ["Choke: elbows open. Armbar: arms tight. Americana: arm pinned"],
        },
        "failure": {
            "bridged_off": "Land in guard (safe — taught in S1/S7)",
            "classification": "safe",
        },
        "mechanics": ["mount pressure", "opponent reading", "attack chains"],
        "duality": "Op learns: mount escape becomes urgent — bridge or elbow-knee",
        "branching": {
            "arms_protect_neck": "armbar — step over head, lean back",
            "elbows_flare": "cross collar choke or ezekiel",
            "arm_pinned": "americana — paint brush",
        },
    },

    {
        "id": "N3",
        "name": "Back Control Attack System",
        "tier": "network",
        "sequence": [
            {"position": "Back Control", "action": "CTRL", "detail": "seatbelt + hooks"},
            {"position": "RNC / Bow and Arrow / Armbar", "action": "SUB", "detail": "hand fight → attack"},
        ],
        "fieldboard": ["BCTR.CTRL", "BCTR.SUB"],
        "sources": ["bjjgraph", "fsm"],
        "source_techniques": {
            "bjjgraph": "RNC / Bow and Arrow Choke / Armbar from Back",
            "fsm": "BackControl → RNC",
        },
        "checkpoints": {
            "control": ["Seatbelt grip, both hooks in, chest glued to back"],
            "stabilization": ["Maintain hooks when opponent tries to escape"],
            "transition": ["Hand fight to clear collar defense"],
            "submission": ["RNC if chin exposed. Bow and arrow if lapel available. Armbar if arm isolatable"],
        },
        "failure": {
            "opponent_escapes": "Opponent turns in → land in mount (safe — already best position)",
            "hooks_lost": "Transition to body triangle or re-insert",
            "classification": "safe",
        },
        "mechanics": ["seatbelt", "hook retention", "hand fighting"],
        "duality": "Op learns: back escape — turn to guard, strip hooks, defend choke",
        "branching": {
            "chin_exposed": "RNC — slide arm under chin, lock, squeeze",
            "lapel_available": "bow and arrow — grab lapel, extend, squeeze",
            "arm_exposed": "armbar from back — control arm, swivel, extend",
        },
    },

    {
        "id": "N4",
        "name": "Half Guard Passing Network",
        "tier": "network",
        "sequence": [
            {"position": "Half Guard Top", "action": "CTRL", "detail": "crossface, deny underhook"},
            {"position": "Side Control / Mount / Back", "action": "TRZ", "detail": "multiple pass options"},
        ],
        "fieldboard": ["HGRD.CTRL", "SCTR.TRZ / MNT.TRZ / BCTR.TRZ"],
        "sources": ["bjjgraph", "flowstate", "bjj_graph_clj"],
        "source_techniques": {
            "bjjgraph": "Knee Slice / Body Lock / Leg Weave / Crossface Pass → various",
            "flowstate": "Top half guard → Side control / Mount",
            "bjj_graph_clj": "Half Guard → Side Mount",
        },
        "checkpoints": {
            "control": ["Win the underhook battle — this determines everything"],
            "stabilization": [],
            "transition": ["Read opponent's frame → choose pass → clear leg → settle"],
            "submission": [],
        },
        "failure": {
            "pass_fails": "Still in half guard top (safe — dominant position)",
            "swept": "Guard player sweeps — land in half guard bottom (recoverable)",
            "classification": "recoverable",
        },
        "mechanics": ["crossface", "underhook", "knee slice", "leg weave", "body lock"],
        "duality": "Op learns: half guard bottom game — underhook sweep, knee shield, re-guard",
        "branching": {
            "opponent_flat": "knee slice through → side control",
            "opponent_frames": "body lock → pass over or under",
            "opponent_underhooks": "whizzer → crossface → flatten → pass",
        },
    },

    {
        "id": "N5",
        "name": "Guard Pull to Sweep-or-Submit Chain",
        "tier": "network",
        "sequence": [
            {"position": "Standing", "action": "CTRL", "detail": "grip fight, pull guard"},
            {"position": "Closed Guard", "action": "TRZ", "detail": "pull to closed guard"},
            {"position": "Sweep → Mount OR Submit from Guard", "action": "SWP/SUB", "detail": "attack tree from S1/S7/N1"},
        ],
        "fieldboard": ["OGRD.Standing.CTRL", "CGRD.TRZ", "CGRD.SWP / CGRD.SUB"],
        "sources": ["bjjgraph", "flowstate", "bjj_graph_clj", "fsm"],
        "source_techniques": {
            "bjjgraph": "Standing → Closed Guard → attack chains",
            "flowstate": "Standing / Neutral → Closed guard → attacks",
            "bjj_graph_clj": "Standing → Guard → various",
            "fsm": "GUARD → FullGuard → various",
        },
        "checkpoints": {
            "control": ["Win grips standing", "Secure closed guard on landing"],
            "stabilization": ["Close guard immediately — don't settle in open guard if you want closed"],
            "transition": ["Grip → sit → pull into closed guard → immediate posture break"],
            "submission": [],
        },
        "failure": {
            "pull_fails": "Opponent sprawls — seated in open guard (recoverable)",
            "guard_passed": "Opponent passes during pull — land in half guard or side control bottom (risky if unprepared)",
            "classification": "recoverable",
        },
        "mechanics": ["grip fighting", "guard pulling", "immediate control"],
        "duality": "Op learns: guard pull defense — sprawl, pass on the way down",
    },

    {
        "id": "N6",
        "name": "Open Guard to Standing Takedown to Dominant",
        "tier": "network",
        "sequence": [
            {"position": "Open Guard", "action": "CTRL", "detail": "feet on hips, grip control"},
            {"position": "Standing", "action": "TRZ", "detail": "technical standup"},
            {"position": "Side Control / Mount", "action": "TRZ", "detail": "takedown → land on top"},
        ],
        "fieldboard": ["OGRD.CTRL", "OGRD.Standing.TRZ", "SCTR.TRZ / MNT.TRZ"],
        "sources": ["bjjgraph", "flowstate"],
        "source_techniques": {
            "bjjgraph": "Open Guard → Standing Position → Side Control / Mount",
            "flowstate": "Open guard → Standing / Neutral → Side control / Mount",
        },
        "checkpoints": {
            "control": ["Feet on hips, collar/sleeve or 2-on-1 grip"],
            "stabilization": [],
            "transition": ["Technical standup → re-engage with takedown or pull guard"],
            "submission": [],
        },
        "failure": {
            "standup_fails": "Opponent follows down — still in open guard (safe)",
            "takedown_fails": "Opponent defends — standing neutral (recoverable)",
            "classification": "recoverable",
        },
        "mechanics": ["technical standup", "grip fighting", "takedown"],
        "duality": "Op learns: open guard passing, takedown defense",
    },

    {
        "id": "N7",
        "name": "Positional Ladder: Guard → Side → Mount → Back → Finish",
        "tier": "network",
        "sequence": [
            {"position": "Half Guard / Open Guard", "action": "CTRL", "detail": "any guard"},
            {"position": "Side Control", "action": "TRZ", "detail": "pass guard"},
            {"position": "Mount", "action": "TRZ", "detail": "advance to mount"},
            {"position": "Back Control", "action": "TRZ", "detail": "opponent turns → take back"},
            {"position": "Rear Naked Choke", "action": "SUB", "detail": "finish"},
        ],
        "fieldboard": ["HGRD.CTRL", "SCTR.TRZ", "MNT.TRZ", "BCTR.TRZ", "BCTR.SUB"],
        "sources": ["bjjgraph", "flowstate"],
        "source_techniques": {
            "bjjgraph": "Half Guard → Side Control → Mount → Back Control → RNC",
            "flowstate": "Half guard → Side control → Mount → Back control → RNC",
        },
        "checkpoints": {
            "control": ["Every position is a stable checkpoint — can pause at any step"],
            "stabilization": ["Consolidate each position 3-5 seconds before advancing"],
            "transition": ["Pass → settle → advance → settle → advance → finish"],
            "submission": ["RNC from back control"],
        },
        "failure": {
            "at_any_step": "Falling back one step is always safe (mount → side → guard)",
            "classification": "safe",
        },
        "mechanics": ["All prior mechanics combined — this is the synthesis road"],
        "duality": "Op perspective IS the escape ladder: escape back → escape mount → escape side → re-guard",
    },
]


def _count_by_tier(roads):
    counts = {"spine": 0, "branch": 0, "network": 0}
    for r in roads:
        counts[r["tier"]] += 1
    return counts


def _generate_report(roads):
    lines = [
        "# Curriculum Spine — Selected Roads",
        "",
        f"Generated: 2026-05-17",
        f"Total roads: {len(roads)}",
    ]
    counts = _count_by_tier(roads)
    lines.append(f"Spine: {counts['spine']} | Branch: {counts['branch']} | Network: {counts['network']}")
    lines.append("")

    for tier_name, tier_label in [("spine", "SPINE ROADS (Beginner Highways)"),
                                   ("branch", "BRANCH ROADS (Intermediate Expansions)"),
                                   ("network", "NETWORK ROADS (Advanced Systems)")]:
        tier_roads = [r for r in roads if r["tier"] == tier_name]
        lines.append(f"---")
        lines.append(f"")
        lines.append(f"## {tier_label}")
        lines.append("")

        for r in tier_roads:
            lines.append(f"### {r['id']}: {r['name']}")
            lines.append("")

            # Fieldboard path
            fb = r["fieldboard"]
            if isinstance(fb, list):
                lines.append(f"**Fieldboard**: {' → '.join(fb)}")
            else:
                lines.append(f"**Fieldboard**: {fb}")

            # Sources
            lines.append(f"**Sources**: {', '.join(r['sources'])} ({len(r['sources'])})")
            lines.append("")

            # Sequence
            lines.append("**Sequence**:")
            for step in r["sequence"]:
                lines.append(f"  1. **{step['position']}** [{step['action']}] — {step['detail']}")
            lines.append("")

            # Source techniques
            lines.append("**Source evidence**:")
            for src, tech in r["source_techniques"].items():
                lines.append(f"  - {src}: {tech}")
            lines.append("")

            # Checkpoints
            cp = r["checkpoints"]
            lines.append("**Checkpoints**:")
            if cp.get("control"):
                lines.append(f"  - Control: {'; '.join(cp['control'])}")
            if cp.get("stabilization"):
                lines.append(f"  - Stabilization: {'; '.join(cp['stabilization'])}")
            if cp.get("transition"):
                lines.append(f"  - Transition: {'; '.join(cp['transition'])}")
            if cp.get("submission"):
                lines.append(f"  - Submission: {'; '.join(cp['submission'])}")
            lines.append("")

            # Failure
            f = r["failure"]
            lines.append(f"**Failure topology** [{f['classification'].upper()}]:")
            for k, v in f.items():
                if k != "classification":
                    lines.append(f"  - {k}: {v}")
            lines.append("")

            # Duality
            lines.append(f"**Duality**: {r['duality']}")
            lines.append("")

            # Branching (network only)
            if "branching" in r:
                lines.append("**Decision tree**:")
                for cond, action in r["branching"].items():
                    lines.append(f"  - If {cond}: {action}")
                lines.append("")

            # Mechanics
            lines.append(f"**Reusable mechanics**: {', '.join(r['mechanics'])}")
            lines.append("")

    # Summary table
    lines.append("---")
    lines.append("")
    lines.append("## Summary: All Roads")
    lines.append("")
    lines.append("| ID | Name | Tier | Steps | Sources | Failure | Fieldboard |")
    lines.append("|----|------|------|-------|---------|---------|------------|")
    for r in roads:
        fb = r["fieldboard"]
        if isinstance(fb, list):
            fb_str = " → ".join(fb)
        else:
            fb_str = fb
        lines.append(
            f"| {r['id']} | {r['name']} | {r['tier']} | "
            f"{len(r['sequence'])} | {len(r['sources'])} | "
            f"{r['failure']['classification']} | {fb_str} |"
        )
    lines.append("")

    # Position coverage
    lines.append("## Position Coverage")
    lines.append("")
    positions_covered = set()
    for r in roads:
        for step in r["sequence"]:
            pos = step["position"].lower()
            for key in ["closed guard", "open guard", "half guard", "butterfly",
                        "mount", "side control", "back control", "turtle",
                        "knee on belly", "standing"]:
                if key in pos:
                    positions_covered.add(key)
    all_positions = {"closed guard", "open guard", "half guard", "butterfly",
                     "mount", "side control", "back control", "turtle",
                     "knee on belly", "standing"}
    covered = positions_covered & all_positions
    missing = all_positions - positions_covered
    lines.append(f"Covered: {', '.join(sorted(covered))}")
    if missing:
        lines.append(f"Not covered: {', '.join(sorted(missing))}")
    else:
        lines.append("All fundamental positions covered.")
    lines.append("")

    # Mechanic reuse
    lines.append("## Mechanic Reuse")
    lines.append("")
    from collections import Counter
    mech_count = Counter()
    for r in roads:
        for m in r["mechanics"]:
            mech_count[m] += 1
    for m, c in mech_count.most_common(15):
        bar = "█" * c
        lines.append(f"  {m:30s} {bar} ({c} roads)")
    lines.append("")

    return "\n".join(lines)


def run():
    roads = SELECTED_ROADS

    counts = _count_by_tier(roads)
    print(f"Selected roads: {len(roads)}")
    print(f"  Spine:   {counts['spine']}")
    print(f"  Branch:  {counts['branch']}")
    print(f"  Network: {counts['network']}")

    # Write JSON
    out_json = DATA / "curriculum_spine.json"
    with open(out_json, "w") as f:
        json.dump(roads, f, indent=2)
    print(f"\nWrote {out_json}")

    # Write report
    report = _generate_report(roads)
    out_report = DATA / "curriculum_spine_report.md"
    out_report.write_text(report)
    print(f"Wrote {out_report}")

    # Validate: check all sources referenced actually exist in parsed data
    print("\nValidation:")
    for r in roads:
        for src in r["sources"]:
            fp = DATA / src / "parsed" / "edges.json"
            if not fp.exists():
                print(f"  WARNING: {r['id']} references {src} but no parsed data found")

    # Failure safety
    safe = sum(1 for r in roads if r["failure"]["classification"] == "safe")
    recoverable = sum(1 for r in roads if r["failure"]["classification"] == "recoverable")
    risky = sum(1 for r in roads if r["failure"]["classification"] == "risky")
    print(f"  Failure: {safe} safe, {recoverable} recoverable, {risky} risky")

    # Mechanic reuse
    from collections import Counter
    mech_count = Counter()
    for r in roads:
        for m in r["mechanics"]:
            mech_count[m] += 1
    top_mechs = mech_count.most_common(5)
    print(f"  Top mechanics: {', '.join(f'{m}({c})' for m, c in top_mechs)}")


if __name__ == "__main__":
    run()
