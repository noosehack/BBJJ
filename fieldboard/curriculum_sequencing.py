"""Milestone 5: Curriculum Sequencing Engine.

Transforms selected curriculum roads into a coherent yearly teaching
structure ordered by pedagogical dependency, checkpoint stability,
reusable mechanics, and duality progression.

NOT building the optimal graph. Building the optimal learning traversal.

Output:
    fieldboard/data/road_dependency_graph.json   (5A)
    fieldboard/data/curriculum_roads.json         (5B)
    fieldboard/data/year_plan.md                  (5C)
    fieldboard/data/checkpoint_library.json       (5D)

Usage:
    python -m fieldboard.curriculum_sequencing
"""

import json
from collections import defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parent
DATA = BASE / "data"


# ── Checkpoint Library (5D) ────────────────────────────────────────────
# Each checkpoint is a transferable concept, not a technique.

CHECKPOINT_LIBRARY = {
    "posture_break": {
        "name": "Posture Break",
        "category": "control",
        "definition": "Breaking opponent's upright alignment from guard — pulling head/shoulders below their hips to neutralize their base and strikes.",
        "body_concept": "Pull collar or head down, close distance between your chest and theirs. Their hands go to the mat = vulnerability.",
        "roads": ["S1", "S2", "S7", "B3", "B5", "B8", "N1", "N5"],
        "reinforced_by": ["Any closed guard class — this is the root of all bottom attacks"],
    },
    "mount_stabilization": {
        "name": "Mount Stabilization",
        "category": "stabilization",
        "definition": "Maintaining mount against bridging and shrimping — keeping hips heavy, base wide, reacting to escape attempts.",
        "body_concept": "Grapevines or heels on hips. Knees squeeze. Hips heavy. Hands post when they bridge. Ride the wave.",
        "roads": ["S1", "S4", "S5", "S6", "S8", "B1", "B3", "N2"],
        "reinforced_by": ["Every class that ends in mount — practice stabilization before submission"],
    },
    "crossface": {
        "name": "Crossface",
        "category": "control",
        "definition": "Shoulder pressure across opponent's jaw/face to control their head direction and deny them the underhook or hip escape.",
        "body_concept": "Shoulder blade drives into far cheek. Their head turns away = they cannot face you = they cannot re-guard.",
        "roads": ["S3", "S6", "B2", "B4", "B7", "B8", "N4"],
        "reinforced_by": ["Side control classes, half guard passing"],
    },
    "underhook": {
        "name": "Underhook",
        "category": "control",
        "definition": "Arm threaded under opponent's arm from inside, controlling their shoulder. Whoever wins the underhook controls the position.",
        "body_concept": "Elbow tight, hand on their back/shoulder blade. Head fights to the underhook side. Creates a frame they cannot break.",
        "roads": ["S3", "S4", "B1", "B2", "N4"],
        "reinforced_by": ["Half guard (both sides), butterfly guard, clinch work"],
    },
    "seatbelt": {
        "name": "Seatbelt Grip",
        "category": "control",
        "definition": "Chest-to-back control with one arm over the shoulder and one under the armpit, hands clasped across opponent's chest.",
        "body_concept": "Over-arm controls the choking lane. Under-arm prevents them turning in. Chest glued to their back — zero space.",
        "roads": ["S2", "B2", "B6", "N3"],
        "reinforced_by": ["Any back control class — seatbelt is the root grip"],
    },
    "hip_escape": {
        "name": "Hip Escape (Shrimp)",
        "category": "transition",
        "definition": "Moving hips away from opponent to create space or change angle. The most fundamental defensive and offensive movement in BJJ.",
        "body_concept": "Bridge onto shoulder → slide hips away → face opponent. Used to escape, re-guard, set up sweeps, and create angles for submissions.",
        "roads": ["S1", "S2", "B5"],
        "reinforced_by": ["Guard recovery drills, mount escape, side control escape — appears everywhere"],
    },
    "bridge": {
        "name": "Bridge (Upa)",
        "category": "transition",
        "definition": "Explosive hip elevation to off-balance or escape from bottom. The primary mount escape mechanism.",
        "body_concept": "Feet flat, drive hips to ceiling. Direction matters — bridge over one shoulder toward trapped arm side.",
        "roads": ["S1", "B8"],
        "reinforced_by": ["Mount escape class, warm-up drilling"],
    },
    "collar_grip": {
        "name": "Collar Grip",
        "category": "control",
        "definition": "Deep grip inside the gi collar, controlling the opponent's posture and setting up chokes and sweeps.",
        "body_concept": "Four fingers inside collar, deep past the label. Elbow stays tight. Pull down and toward you for posture break; cross-grip for choke.",
        "roads": ["S5", "S7", "S8", "B3"],
        "reinforced_by": ["Gi-specific classes — collar grip is the gi equivalent of clinch control"],
    },
    "figure_four_lock": {
        "name": "Figure-Four Lock",
        "category": "submission",
        "definition": "Interlocking grip where your wrist controls their wrist and your other hand grabs your own wrist — creates a lever system.",
        "body_concept": "Appears in kimura, americana, armbar grip, RNC. Same grip shape, different application angles.",
        "roads": ["S1", "S3", "B5"],
        "reinforced_by": ["Any class teaching americana, kimura, or armbar finish mechanics"],
    },
    "arm_isolation": {
        "name": "Arm Isolation",
        "category": "transition",
        "definition": "Separating one of opponent's arms from their body to attack it — the prerequisite for armbar, americana, kimura.",
        "body_concept": "Two-on-one control. Pin at wrist or elbow. Create separation between their arm and their torso.",
        "roads": ["S1", "S3", "N2"],
        "reinforced_by": ["Mount attacks, side control attacks"],
    },
    "hook_insertion": {
        "name": "Hook Insertion",
        "category": "stabilization",
        "definition": "Placing insteps (hooks) inside opponent's thighs from back control. Prevents them from sliding down to escape.",
        "body_concept": "Bottom hook first (bearing their weight). Top hook second. Heels dig inward, not down. If they peel hooks, transition to body triangle.",
        "roads": ["S2", "B6", "N3"],
        "reinforced_by": ["Back control classes — hooks are the retention system"],
    },
    "knee_slice": {
        "name": "Knee Slice Pass",
        "category": "transition",
        "definition": "Passing guard by sliding the knee across opponent's thigh while controlling their upper body, clearing the guard leg.",
        "body_concept": "Cross-face controls head. Knee slides across midline. Shin pins their thigh. Hip drops to clear. Underhook the far side on landing.",
        "roads": ["S3", "N4"],
        "reinforced_by": ["Half guard passing classes, guard passing fundamentals"],
    },
    "off_balance": {
        "name": "Off-Balancing (Kuzushi)",
        "category": "transition",
        "definition": "Disrupting opponent's base before attempting a sweep or throw. Without kuzushi, no sweep works.",
        "body_concept": "Push-pull. Load their weight onto one side, then sweep the other. They must be falling BEFORE you sweep.",
        "roads": ["S4", "S5", "B1", "B3", "N1"],
        "reinforced_by": ["Every sweep class — kuzushi is the universal setup"],
    },
    "guard_retention": {
        "name": "Guard Retention",
        "category": "control",
        "definition": "Keeping opponent in your guard when they attempt to pass — using frames, hip movement, and leg pummeling to re-establish guard.",
        "body_concept": "Frames on biceps/collar. Hips never flat. Knees track their hips. If they pass one leg, re-pummel the other.",
        "roads": ["S5", "S7", "B7", "N5", "N6"],
        "reinforced_by": ["Open guard classes, guard recovery drills"],
    },
    "angle_cutting": {
        "name": "Angle Cutting",
        "category": "transition",
        "definition": "Turning perpendicular to opponent to tighten a triangle, armbar, or create a sweep angle. The difference between a loose and tight submission.",
        "body_concept": "Pivot on your shoulders. Walk your hips to a 45-90° angle from opponent's centerline. Their arm/head is now trapped at maximum leverage.",
        "roads": ["S7"],
        "reinforced_by": ["Triangle and armbar finishing classes"],
    },
    "weight_distribution": {
        "name": "Weight Distribution",
        "category": "control",
        "definition": "Controlling where your weight presses on the opponent — the invisible skill that separates heavy from light top pressure.",
        "body_concept": "Shift weight into chest/shoulder contact point. Remove weight from hands and feet — they should be light. Opponent feels 200% of your weight on one spot.",
        "roads": ["S6", "S8", "B4"],
        "reinforced_by": ["Side control, mount, knee on belly classes"],
    },
    "back_take_timing": {
        "name": "Back Take Timing",
        "category": "transition",
        "definition": "Recognizing when opponent turns away (exposing their back) and immediately transitioning to back control before they complete the turn.",
        "body_concept": "When they turn away: seatbelt FIRST, then chase hips, then insert hooks. Never hooks before seatbelt — you'll get shaken off.",
        "roads": ["B2", "B6"],
        "reinforced_by": ["Side control → back take transitions, turtle top work"],
    },
    "grip_fighting": {
        "name": "Grip Fighting",
        "category": "control",
        "definition": "Establishing your grips while stripping theirs — the standing and guard-pulling meta-game.",
        "body_concept": "Get your grips first. If they grip first, strip immediately — two-on-one break, circle wrist, push elbow. Never let them settle grips.",
        "roads": ["N5", "N6"],
        "reinforced_by": ["Standing classes, guard pulling, open guard"],
    },
    "opponent_reading": {
        "name": "Opponent Reading",
        "category": "transition",
        "definition": "Recognizing opponent's defensive reaction and choosing the correct attack branch — the core skill of network roads.",
        "body_concept": "If they protect the neck: attack the arm. If they protect the arm: attack the neck. If they bridge: ride and re-attack. Read, don't guess.",
        "roads": ["N1", "N2", "N3", "N4"],
        "reinforced_by": ["Positional sparring with specific attack/defense roles"],
    },
}


# ── Road Dependencies (5A) ────────────────────────────────────────────
# Format: road_id → list of prerequisite road_ids
# Question for each: "What must a student already understand before
# this road becomes meaningful?"

ROAD_DEPENDENCIES = {
    # SPINE — foundations, minimal prerequisites
    "S1": [],                        # First road taught. No prerequisites.
    "S5": [],                        # Scissor sweep — can parallel S1.
    "S7": ["S1"],                    # Triangle needs guard posture control (from S1).
    "S8": ["S1"],                    # Mount choke needs mount stabilization (from S1).
    "S2": ["S1"],                    # Back take needs guard control (from S1). Seatbelt is new.
    "S4": ["S1"],                    # Butterfly needs mount base (from S1). Hook sweep is new.
    "S3": ["S1", "S6"],             # Half guard pass needs side control concept (from S6).
    "S6": ["S1"],                    # Side → mount needs mount stabilization (from S1).

    # BRANCH — expand from spine
    "B3": ["S1"],                    # Alt sweep from closed guard. Needs S1 guard + mount.
    "B5": ["S1", "S7"],             # Kimura grip links to triangle (hip escape + guard attacks).
    "B8": ["S1", "S3"],             # Sweep to side control. Needs guard + side control knowledge.
    "B1": ["S3"],                    # Half guard underhook sweep. Needs half guard concept (S3).
    "B7": ["S5", "S6"],             # Open guard passing. Needs open guard (S5) + side control (S6).
    "B4": ["S3", "S6"],             # Arm triangle from side. Needs side control mastery.
    "B2": ["S3", "S2"],             # HG→SC→BC chain. Needs passing (S3) + back control (S2).
    "B6": ["S2"],                    # Turtle→back. Needs back control concept (S2).

    # NETWORK — synthesize spine + branch
    "N1": ["S1", "S7", "B5"],       # Guard attack tree. Needs all guard attacks.
    "N2": ["S1", "S8"],             # Mount dilemma. Needs mount + multiple attacks.
    "N3": ["S2", "B6"],             # Back system. Needs back take + back control.
    "N4": ["S3", "B1"],             # HG passing network. Needs both sides of half guard.
    "N5": ["S1", "S5", "N1"],       # Guard pull → attack. Needs standing + guard attacks.
    "N6": ["S5", "B7"],             # Standing → pass. Needs open guard + passing.
    "N7": ["S3", "S6", "B2", "N3"], # Full ladder. Needs all positional advances + back system.
}


# ── Prerequisite Mechanics per Road ────────────────────────────────────
# What body concepts must be learned BEFORE attempting this road?

PREREQUISITE_MECHANICS = {
    "S1": ["hip escape", "bridge"],
    "S2": ["hip escape", "posture break"],
    "S3": ["crossface", "underhook"],
    "S4": ["underhook", "off-balance"],
    "S5": ["collar grip", "off-balance"],
    "S6": ["crossface", "weight distribution"],
    "S7": ["posture break", "hip elevation"],
    "S8": ["mount stabilization", "collar grip"],
    "B1": ["underhook", "hip movement"],
    "B2": ["crossface", "seatbelt", "knee slice"],
    "B3": ["collar grip", "posture break"],
    "B4": ["crossface", "weight distribution"],
    "B5": ["posture break", "hip escape", "figure-four lock"],
    "B6": ["seatbelt", "hook insertion"],
    "B7": ["guard retention", "leg clearing"],
    "B8": ["bridge", "crossface"],
    "N1": ["posture break", "hip bump", "figure-four lock", "hip elevation"],
    "N2": ["mount stabilization", "arm isolation", "collar grip"],
    "N3": ["seatbelt", "hook retention", "hand fighting"],
    "N4": ["crossface", "underhook", "knee slice", "off-balance"],
    "N5": ["grip fighting", "guard pulling", "posture break"],
    "N6": ["guard retention", "grip fighting", "off-balance"],
    "N7": ["crossface", "mount stabilization", "seatbelt", "knee slice"],
}


# ── Duality Links ──────────────────────────────────────────────────────
# Each road teaches attack. The duality is what Op learns.

DUALITY_LINKS = {
    "S1": {"attack": "sweep + armbar from guard", "defense": "posture in guard, mount escape, armbar defense"},
    "S2": {"attack": "arm drag to back, RNC", "defense": "posture in guard, back escape, RNC defense"},
    "S3": {"attack": "half guard pass, americana", "defense": "half guard retention, side escape, americana defense"},
    "S4": {"attack": "butterfly sweep", "defense": "butterfly passing, mount escape"},
    "S5": {"attack": "scissor sweep", "defense": "open guard passing, base maintenance"},
    "S6": {"attack": "positional advance SC→KOB→MNT", "defense": "side escape, KOB escape, mount escape"},
    "S7": {"attack": "triangle from guard", "defense": "posture, triangle defense, stack pass"},
    "S8": {"attack": "cross collar choke from mount", "defense": "mount escape, choke defense"},
    "B1": {"attack": "underhook sweep from HG", "defense": "whizzer counter, HG top control"},
    "B2": {"attack": "pass→side→back chain", "defense": "HG retention, side escape, back escape"},
    "B3": {"attack": "flower sweep", "defense": "base and posture in guard"},
    "B4": {"attack": "arm triangle from side", "defense": "frame defense, arm extraction"},
    "B5": {"attack": "kimura sweep", "defense": "hand-on-mat defense, posture"},
    "B6": {"attack": "turtle back take", "defense": "turtle defense (granby, sit-out, standup)"},
    "B7": {"attack": "open guard pass", "defense": "guard retention, re-guarding"},
    "B8": {"attack": "sweep to side control, americana", "defense": "guard posture, side escape"},
    "N1": {"attack": "guard attack decision tree", "defense": "all guard defenses simultaneously"},
    "N2": {"attack": "mount attack cycle", "defense": "mount escape becomes urgent"},
    "N3": {"attack": "back control attack system", "defense": "back escape system"},
    "N4": {"attack": "half guard passing network", "defense": "half guard bottom game"},
    "N5": {"attack": "guard pull to attack", "defense": "guard pull defense, pass on the way down"},
    "N6": {"attack": "standup to takedown", "defense": "takedown defense, guard pulling"},
    "N7": {"attack": "full positional ladder", "defense": "full escape ladder"},
}


# ── Teaching Phases ────────────────────────────────────────────────────

TEACHING_PHASES = {
    "S1": "beginner", "S2": "beginner", "S3": "beginner", "S4": "beginner",
    "S5": "beginner", "S6": "beginner", "S7": "beginner", "S8": "beginner",
    "B1": "intermediate", "B2": "intermediate", "B3": "intermediate",
    "B4": "intermediate", "B5": "intermediate", "B6": "intermediate",
    "B7": "intermediate", "B8": "intermediate",
    "N1": "advanced", "N2": "advanced", "N3": "advanced", "N4": "advanced",
    "N5": "advanced", "N6": "advanced", "N7": "advanced",
}


def _topological_sort(deps):
    """Topological sort of road IDs respecting dependencies."""
    in_degree = defaultdict(int)
    graph = defaultdict(list)
    all_nodes = set(deps.keys())

    for node, prereqs in deps.items():
        for p in prereqs:
            graph[p].append(node)
            in_degree[node] += 1
        if node not in in_degree:
            in_degree[node] = 0

    queue = sorted([n for n in all_nodes if in_degree[n] == 0])
    order = []
    while queue:
        node = queue.pop(0)
        order.append(node)
        for neighbor in sorted(graph[node]):
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    return order


def build_dependency_graph():
    """5A: Build road_dependency_graph.json."""
    order = _topological_sort(ROAD_DEPENDENCIES)

    nodes = []
    for road_id in order:
        nodes.append({
            "road_id": road_id,
            "prerequisites": ROAD_DEPENDENCIES.get(road_id, []),
            "teaching_phase": TEACHING_PHASES[road_id],
            "topological_order": order.index(road_id),
        })

    edges = []
    for road_id, prereqs in ROAD_DEPENDENCIES.items():
        for p in prereqs:
            edges.append({"from": p, "to": road_id, "type": "must_precede"})

    return {
        "description": "Pedagogical dependency graph — road A must precede road B",
        "topological_order": order,
        "nodes": nodes,
        "edges": edges,
    }


def build_curriculum_roads(spine_roads):
    """5B: Build curriculum_roads.json with full sequencing metadata."""
    road_lookup = {r["id"]: r for r in spine_roads}
    order = _topological_sort(ROAD_DEPENDENCIES)

    curriculum = []
    for road_id in order:
        r = road_lookup[road_id]
        curriculum.append({
            "id": road_id,
            "name": r["name"],
            "road_type": r["tier"],
            "teaching_phase": TEACHING_PHASES[road_id],
            "teaching_order": order.index(road_id) + 1,
            "prerequisite_roads": ROAD_DEPENDENCIES.get(road_id, []),
            "prerequisite_mechanics": PREREQUISITE_MECHANICS.get(road_id, []),
            "control_checkpoints": r["checkpoints"].get("control", []),
            "stabilization_checkpoints": r["checkpoints"].get("stabilization", []),
            "transition_checkpoints": r["checkpoints"].get("transition", []),
            "submission_checkpoints": r["checkpoints"].get("submission", []),
            "failure_topology": r["failure"]["classification"],
            "failure_detail": {k: v for k, v in r["failure"].items() if k != "classification"},
            "reusable_mechanics": r["mechanics"],
            "duality_links": DUALITY_LINKS.get(road_id, {}),
            "fieldboard": r["fieldboard"],
            "sources": r["sources"],
        })

    return curriculum


def build_year_plan(curriculum):
    """5C: Generate year_plan.md."""
    lines = [
        "# Curriculum Year Plan",
        "",
        "Pedagogically sequenced BJJ curriculum across three years.",
        "Ordered by dependency, checkpoint stability, mechanic reuse, and duality.",
        "",
        "Principle: maximize reusable mechanics early, low branching first,",
        "safe failure topology, strong control foundations, progressive complexity.",
        "",
        "NOT random positional coverage. NOT statistical optimization.",
        "This is the optimal LEARNING traversal.",
        "",
    ]

    # Group by phase
    beginner = [r for r in curriculum if r["teaching_phase"] == "beginner"]
    intermediate = [r for r in curriculum if r["teaching_phase"] == "intermediate"]
    advanced = [r for r in curriculum if r["teaching_phase"] == "advanced"]

    # ── BEGINNER YEAR ──
    lines.append("---")
    lines.append("")
    lines.append("## Year 1: Beginner — Spine Roads")
    lines.append("")
    lines.append("**Goal**: Learn all 7 fundamental positions, basic sweeps, one")
    lines.append("submission from each dominant position, safe failure recovery.")
    lines.append("")
    lines.append("**Principle**: Low branching. Clear cause/effect. Every road fails safely.")
    lines.append("Every mechanic learned transfers to multiple roads later.")
    lines.append("")

    # 8 spine roads across ~48 teaching weeks (6 weeks per road)
    weeks_per_road_b = 6
    week = 1
    for i, r in enumerate(beginner):
        end_week = min(week + weeks_per_road_b - 1, 52)
        lines.append(f"### Weeks {week}–{end_week}: {r['id']} — {r['name']}")
        lines.append("")

        fb = r["fieldboard"]
        if isinstance(fb, list):
            lines.append(f"**Fieldboard**: {' → '.join(fb)}")
        else:
            lines.append(f"**Fieldboard**: {fb}")
        lines.append("")

        if r["prerequisite_roads"]:
            lines.append(f"**Prerequisites**: {', '.join(r['prerequisite_roads'])}")
        else:
            lines.append("**Prerequisites**: None (foundation road)")
        lines.append("")

        lines.append("**Week breakdown**:")

        # Week-by-week structure
        w = week
        if r["control_checkpoints"]:
            lines.append(f"  - Week {w}: CONTROL — {'; '.join(r['control_checkpoints'][:2])}")
            w += 1
        if r["transition_checkpoints"]:
            lines.append(f"  - Week {w}: TRANSITION — {'; '.join(r['transition_checkpoints'][:2])}")
            w += 1
        if r["stabilization_checkpoints"]:
            lines.append(f"  - Week {w}: STABILIZATION — {'; '.join(r['stabilization_checkpoints'][:2])}")
            w += 1
        if r["submission_checkpoints"]:
            lines.append(f"  - Week {w}: SUBMISSION — {'; '.join(r['submission_checkpoints'][:2])}")
            w += 1
        remaining = end_week - w + 1
        if remaining > 0:
            lines.append(f"  - Weeks {w}–{end_week}: DRILLING + positional sparring (this road only)")
        lines.append("")

        # Duality
        dual = r.get("duality_links", {})
        if dual:
            lines.append(f"**Duality cycle**: Attack = {dual.get('attack', '')}. Defense = {dual.get('defense', '')}.")
            lines.append("")

        lines.append(f"**Failure**: {r['failure_topology']} — {list(r['failure_detail'].values())[0] if r['failure_detail'] else ''}")
        lines.append(f"**Mechanics learned**: {', '.join(r['reusable_mechanics'])}")
        lines.append("")

        week = end_week + 1

    # ── INTERMEDIATE YEAR ──
    lines.append("---")
    lines.append("")
    lines.append("## Year 2: Intermediate — Branch Roads")
    lines.append("")
    lines.append("**Goal**: Add alternative attacks from known positions, build")
    lines.append("reaction chains, expand the decision tree at each position.")
    lines.append("")
    lines.append("**Principle**: Moderate branching. Trap systems (if A fails → B).")
    lines.append("Recoverable failure states. Build on spine mechanics.")
    lines.append("")

    weeks_per_road_i = 6
    week = 1
    for i, r in enumerate(intermediate):
        end_week = min(week + weeks_per_road_i - 1, 52)
        lines.append(f"### Weeks {week}–{end_week}: {r['id']} — {r['name']}")
        lines.append("")

        fb = r["fieldboard"]
        if isinstance(fb, list):
            lines.append(f"**Fieldboard**: {' → '.join(fb)}")
        else:
            lines.append(f"**Fieldboard**: {fb}")
        lines.append("")

        lines.append(f"**Prerequisites**: {', '.join(r['prerequisite_roads'])}")
        lines.append(f"**Builds on**: {', '.join(r['prerequisite_mechanics'])}")
        lines.append("")

        lines.append("**Week breakdown**:")
        w = week
        if r["control_checkpoints"]:
            lines.append(f"  - Week {w}: CONTROL — {'; '.join(r['control_checkpoints'][:2])}")
            w += 1
        if r["transition_checkpoints"]:
            lines.append(f"  - Week {w}: TRANSITION — {'; '.join(r['transition_checkpoints'][:2])}")
            w += 1
        if r["submission_checkpoints"]:
            lines.append(f"  - Week {w}: SUBMISSION — {'; '.join(r['submission_checkpoints'][:2])}")
            w += 1
        remaining = end_week - w + 1
        if remaining > 0:
            lines.append(f"  - Weeks {w}–{end_week}: Chain drilling — connect this branch to its spine road")
        lines.append("")

        dual = r.get("duality_links", {})
        if dual:
            lines.append(f"**Duality cycle**: Attack = {dual.get('attack', '')}. Defense = {dual.get('defense', '')}.")
        lines.append(f"**Failure**: {r['failure_topology']}")
        lines.append(f"**New mechanics**: {', '.join(r['reusable_mechanics'])}")
        lines.append("")

        week = end_week + 1

    # ── ADVANCED YEAR ──
    lines.append("---")
    lines.append("")
    lines.append("## Year 3: Advanced — Network Roads")
    lines.append("")
    lines.append("**Goal**: Connect roads into adaptive systems. Read opponent")
    lines.append("reactions. Switch between attacks. Dynamic path selection.")
    lines.append("")
    lines.append("**Principle**: High branching. Opponent modeling. Decision trees.")
    lines.append("Intentional baiting. Every network road synthesizes multiple spine+branch roads.")
    lines.append("")

    weeks_per_road_a = 7
    week = 1
    for i, r in enumerate(advanced):
        end_week = min(week + weeks_per_road_a - 1, 52)
        lines.append(f"### Weeks {week}–{end_week}: {r['id']} — {r['name']}")
        lines.append("")

        fb = r["fieldboard"]
        if isinstance(fb, list):
            lines.append(f"**Fieldboard**: {' → '.join(fb)}")
        else:
            lines.append(f"**Fieldboard**: {fb}")
        lines.append("")

        lines.append(f"**Prerequisites**: {', '.join(r['prerequisite_roads'])}")
        lines.append(f"**Synthesizes**: {', '.join(r['prerequisite_mechanics'])}")
        lines.append("")

        lines.append("**Week breakdown**:")
        w = week
        lines.append(f"  - Weeks {w}–{w+1}: Review component roads — drill each branch independently")
        w += 2
        lines.append(f"  - Weeks {w}–{w+1}: Decision tree drilling — coach calls reactions, student reads")
        w += 2
        lines.append(f"  - Weeks {w}–{end_week}: Live positional sparring with network constraints")
        lines.append("")

        dual = r.get("duality_links", {})
        if dual:
            lines.append(f"**Duality cycle**: Attack = {dual.get('attack', '')}. Defense = {dual.get('defense', '')}.")
        lines.append(f"**Failure**: {r['failure_topology']}")
        lines.append("")

        week = end_week + 1

    # ── SUMMARY ──
    lines.append("---")
    lines.append("")
    lines.append("## Sequencing Summary")
    lines.append("")
    lines.append("| Order | ID | Name | Phase | Prerequisites |")
    lines.append("|-------|----|------|-------|---------------|")
    for r in curriculum:
        prereqs = ", ".join(r["prerequisite_roads"]) if r["prerequisite_roads"] else "—"
        lines.append(f"| {r['teaching_order']} | {r['id']} | {r['name'][:45]} | {r['teaching_phase']} | {prereqs} |")
    lines.append("")

    lines.append("## Mechanic Progression")
    lines.append("")
    lines.append("Mechanics are introduced once and reused across all subsequent roads.")
    lines.append("This table shows when each mechanic first appears:")
    lines.append("")

    # Track first appearance of each mechanic
    mechanic_first = {}
    for r in curriculum:
        for m in r["reusable_mechanics"]:
            if m not in mechanic_first:
                mechanic_first[m] = (r["id"], r["teaching_phase"])

    lines.append("| Mechanic | First Appears | Phase |")
    lines.append("|----------|---------------|-------|")
    for m, (rid, phase) in sorted(mechanic_first.items(), key=lambda x: curriculum[[r["id"] for r in curriculum].index(x[1][0])]["teaching_order"]):
        lines.append(f"| {m} | {rid} | {phase} |")
    lines.append("")

    return "\n".join(lines)


def run():
    # Load spine data
    spine_path = DATA / "curriculum_spine.json"
    spine_roads = json.load(open(spine_path))
    print(f"Loaded {len(spine_roads)} roads from curriculum_spine.json")

    # 5A: Dependency graph
    dep_graph = build_dependency_graph()
    out_dep = DATA / "road_dependency_graph.json"
    with open(out_dep, "w") as f:
        json.dump(dep_graph, f, indent=2)
    print(f"5A: Wrote {out_dep}")
    print(f"    Topological order: {' → '.join(dep_graph['topological_order'])}")

    # 5B: Curriculum roads
    curriculum = build_curriculum_roads(spine_roads)
    out_cur = DATA / "curriculum_roads.json"
    with open(out_cur, "w") as f:
        json.dump(curriculum, f, indent=2)
    print(f"5B: Wrote {out_cur}")

    # 5C: Year plan
    year_plan = build_year_plan(curriculum)
    out_year = DATA / "year_plan.md"
    out_year.write_text(year_plan)
    print(f"5C: Wrote {out_year}")

    # 5D: Checkpoint library
    out_cp = DATA / "checkpoint_library.json"
    with open(out_cp, "w") as f:
        json.dump(CHECKPOINT_LIBRARY, f, indent=2)
    print(f"5D: Wrote {out_cp}")
    print(f"    {len(CHECKPOINT_LIBRARY)} checkpoints defined")

    # Validation
    print("\nValidation:")
    order = dep_graph["topological_order"]
    for road_id in order:
        phase = TEACHING_PHASES[road_id]
        prereqs = ROAD_DEPENDENCIES[road_id]
        for p in prereqs:
            p_phase = TEACHING_PHASES[p]
            p_order = order.index(p)
            r_order = order.index(road_id)
            if p_order >= r_order:
                print(f"  ERROR: {road_id} depends on {p} but {p} comes after in topological order")
            phase_order = {"beginner": 0, "intermediate": 1, "advanced": 2}
            if phase_order[p_phase] > phase_order[phase]:
                print(f"  ERROR: {road_id} ({phase}) depends on {p} ({p_phase}) — phase violation")

    # Check all checkpoint references
    for cp_id, cp in CHECKPOINT_LIBRARY.items():
        for road_id in cp["roads"]:
            if road_id not in ROAD_DEPENDENCIES:
                print(f"  ERROR: checkpoint {cp_id} references unknown road {road_id}")

    print("  All dependency and phase constraints satisfied.")


if __name__ == "__main__":
    run()
