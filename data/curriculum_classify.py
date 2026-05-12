"""Classify GB1 techniques by type and map to defense axis."""

from data.curriculum_map import CURRICULUM, TEACHING_ORDER, TRANSITIONS

# technique type: sweep, sub, pass, escape, control, transition
TECH_TYPE = {
    # STND — Self-Defense (standing)
    1: "escape",       # SD: Escape Sidemount with Punches (ground SD, mapped to SCTR)
    4: "escape",       # SD: Escape Sidemount with Punches + Bridge (ground SD, mapped to SCTR)
    7: "escape",       # SD: Escape Side Standing Headlock + Rear Takedown
    10: "escape",      # SD: Escape Rear Headlock
    13: "transition",  # SD: Jab Slip to Double Leg Takedown
    16: "transition",  # SD: Cross Punch Slip to Single Leg Takedown
    19: "escape",      # SD: Double Lapel Grab Escape + Outside Hook Takedown
    22: "escape",      # SD: Throat Grab Escape + Body Lock Takedown
    25: "escape",      # SD: Blocking Punches from Closed Guard (ground SD, mapped to CGRD)
    28: "escape",      # SD: Blocking Punches from Closed Guard + Upkick
    31: "transition",  # SD: Escape Guard + Pass + Mount + Escape (full drill)
    34: "escape",      # SD: Headlock Escape Taking the Back
    37: "transition",  # SD: Distance Management + Body Lock Takedown
    40: "transition",  # SD: Distance Management + Double Leg
    43: "transition",  # SD: Blocking Hooks + Body Lock Takedown
    46: "transition",  # SD: Jab Slip + Bodylock Clinch + Takedown
    49: "escape",      # SD: Blocking Punches from Turtle (mapped to TRTL)
    52: "escape",      # SD: Block Punches from Turtle (mapped to TRTL)
    55: "sub",         # SD: Standing Guillotine
    58: "escape",      # SD: Escape Side Headlock Standing with Punches
    61: "transition",  # SD: Block Hook Punch + Hip Throw
    64: "transition",  # SD: Slip Hook Punch + Bodylock Takedown
    67: "escape",      # SD: Front Bear Hug Escape + Hip Throw
    70: "escape",      # SD: Rear Bear Hug Escape + Rear Takedown
    73: "escape",      # SD: Blocking Punches from Guard + Triangle (mapped to CGRD)
    76: "escape",      # SD: Distance Management from Guard (mapped to CGRD)
    79: "escape",      # SD: Front Headlock Escape to Turtle
    82: "escape",      # SD: Headlock Roll Reversal + Armbar
    85: "escape",      # SD: Block Front Kick + Elbow Strike
    88: "transition",  # SD: Blocking Round Kick + Inside Hook Takedown
    91: "escape",      # SD: Rear Bear Hug Under Arms Escape
    94: "escape",      # SD: Rear Bear Hug Escape + Leg Lock
    2: "control",      # Pulling to Closed Guard
    3: "sweep",        # Scissor Sweep
    5: "sub",          # X Collar Choke
    6: "sub",          # X Collar Choke thumbs
    8: "escape",       # Escape Sidemount → CGRD
    9: "escape",       # Escape Sidemount → CGRD
    11: "escape",      # Escape Sidemount → TRTL
    12: "transition",  # Double Leg from Turtle
    14: "pass",        # Safe Posture + Opening Guard
    15: "pass",        # One Arm Under Leg Pass
    17: "pass",        # One Arm Under Leg Pass standing
    18: "pass",        # Knee Slide Pass
    20: "escape",      # Escape Mount → HGRD
    21: "sweep",       # Half Guard Sweep underhook
    23: "escape",      # Escape Mount → CGRD
    24: "escape",      # KoB Escape
    26: "sweep",       # Pull Feet Sweep
    27: "sweep",       # Waiter Sweep
    29: "sweep",       # Tripod Sweep
    30: "sweep",       # Outside Hook Sweep
    32: "escape",      # Recovering Guard rear turtle
    33: "escape",      # Recovering Guard front turtle
    35: "escape",      # Bridge Escape from Back
    36: "escape",      # Bridge Escape from Back
    38: "pass",        # Over the Leg Pass
    39: "pass",        # Half Guard Pass
    41: "pass",        # Spider Bull-Fight Pass
    42: "pass",        # Spider Bull-Fight Pass hips
    44: "transition",  # SCTR → MNT leg over
    45: "sub",         # Uppercut Choke
    47: "transition",  # SCTR → MNT knee slide
    48: "sub",         # Spinning Armbar
    50: "sweep",       # Pendulum Sweep
    51: "sub",         # Straight Armbar from CGRD
    53: "transition",  # Take Back from CGRD
    54: "sub",         # Triangle
    56: "sub",         # X Choke from Mount
    57: "control",     # Technical Mount
    59: "sub",         # Straight Armbar from Mount
    60: "sub",         # Key Lock from Mount
    62: "pass",        # Open Guard on Knees
    63: "pass",        # Knee Slide Controlling Sleeve
    65: "pass",        # Opening Guard Standing
    66: "pass",        # Guard Pass Standing Arms Under
    68: "control",     # Seatbelt Grip
    69: "sub",         # Cock Choke
    71: "transition",  # Taking Back from Turtle
    72: "sub",         # Two Collars / RNC
    74: "sweep",       # Sit-Up Sweep
    75: "sub",         # Kimura
    77: "control",     # Spider Guard Control
    78: "sweep",       # Spider Guard Sweep
    80: "escape",      # Escape Sidemount → HGRD
    81: "sweep",       # Half Guard Sweep underhook (repeat)
    83: "escape",      # Escape Sidemount anticipating pass
    84: "escape",      # Escape Sidemount inversion
    86: "pass",        # Open Guard Standing pants
    87: "pass",        # Leg Drag Pass
    89: "pass",        # Open Guard Knees pants
    90: "pass",        # Two Arms Under Leg Pass knees
    92: "escape",      # Escape Mount → CGRD
    93: "escape",      # KoB Escape → CGRD
    95: "escape",      # Escape Mount → Take Back
    96: "escape",      # KoB Escape → OGRD
}

TYPE_COLORS = {
    "sweep": "#f1c40f",
    "sub": "#e74c3c",
    "pass": "#3498db",
    "escape": "#2ecc71",
    "control": "#e67e22",
    "transition": "#9b59b6",
}

TYPE_LABELS = {
    "sweep": "Sweep",
    "sub": "Submission",
    "pass": "Pass",
    "escape": "Escape",
    "control": "Control",
    "transition": "Transition",
}


def summary():
    """Print classified summary."""
    for pos in TEACHING_ORDER:
        c = CURRICULUM[pos]
        print(f"\n═══ {pos} — {c['label']} (Level {c['level']}) ═══")

        all_techs = []
        for phase in ("control", "attack_defend", "transit_react"):
            for num, name, persp in c[phase]:
                ttype = TECH_TYPE.get(num, "?")
                all_techs.append((num, name, persp, phase, ttype))

        by_type = {}
        for num, name, persp, phase, ttype in all_techs:
            by_type.setdefault(ttype, []).append((num, name, persp))

        for ttype in ("sweep", "sub", "pass", "escape", "control", "transition"):
            if ttype in by_type:
                print(f"  {TYPE_LABELS[ttype]:12s} ({len(by_type[ttype])})")
                for num, name, persp in by_type[ttype]:
                    print(f"    {num:2d}. [{persp}] {name}")


def counts():
    """Type counts per position."""
    print(f"{'':6s} {'sweep':>6s} {'sub':>6s} {'pass':>6s} {'esc':>6s} {'ctrl':>6s} {'trans':>6s} {'total':>6s}")
    print("  " + "─" * 48)
    totals = {t: 0 for t in TYPE_COLORS}
    grand = 0
    for pos in TEACHING_ORDER:
        c = CURRICULUM[pos]
        row = {t: 0 for t in TYPE_COLORS}
        for phase in ("control", "attack_defend", "transit_react"):
            for num, name, persp in c[phase]:
                ttype = TECH_TYPE.get(num, "?")
                if ttype in row:
                    row[ttype] += 1
        total = sum(row.values())
        grand += total
        for t in row:
            totals[t] += row[t]
        print(f"  {pos:5s} {row['sweep']:6d} {row['sub']:6d} {row['pass']:6d} {row['escape']:6d} {row['control']:6d} {row['transition']:6d} {total:6d}")
    print("  " + "─" * 48)
    print(f"  {'TOTAL':5s} {totals['sweep']:6d} {totals['sub']:6d} {totals['pass']:6d} {totals['escape']:6d} {totals['control']:6d} {totals['transition']:6d} {grand:6d}")


if __name__ == "__main__":
    counts()
    summary()
