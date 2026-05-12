"""GB1 Curriculum (96 techniques) mapped to radicals and phases.

Each technique is (gb1_number, name, perspective):
  perspective = "Me" (playing the position) or "Op" (opposing it)

Phases:
  define   — what structurally defines this position (radical)
  control  — maintain / stabilise the position
  attack_defend — submissions, sweeps (Me) / survival, frames (Op)
  transit_react — move to next position (Me) / react to opponent's move (Op)

Streams: SD = Self-Defense/Takedowns, SP = Sport Jiu-Jitsu
"""

TEACHING_ORDER = ["STND", "CGRD", "OGRD", "HGRD", "SCTR", "MNT", "TRTL", "BCTR"]

CURRICULUM = {
    # ── Level 4: Standing ─────────────────────────────────────────
    "STND": {
        "level": 4,
        "label": "Standing",
        "define": (
            "FacingOpposed, NotOnGround(Me.Ba), NotOnGround(Op.Ba). "
            "No leg entanglement, no torso wrap. Neutral engagement."
        ),
        "control": [],
        "attack_defend": [
            # Me attacks from standing — takedowns (counter-attack sequences)
            (13, "Jab Slip to Double Leg Takedown", "Me"),
            (16, "Cross Punch Slip to Single Leg Takedown", "Me"),
            (37, "Distance Management with the Arm + Front Push Kick + Body Lock Takedown + Sidemount Control", "Me"),
            (40, "Distance Management with the Arm + Jab + Cross + Double Leg", "Me"),
            (43, "Blocking the Hook Punches + Body Lock Takedown + Armbar", "Me"),
            (46, "Jab Slip + Bodylock Clinch + Rear Bodylock + Wrist Control + Forward Takedown", "Me"),
            (61, "Block Hook Punch + Hip Throw + Straight Armbar with Knee on Belly", "Me"),
            (64, "Slip the Hook Punch + Bodylock Takedown + Transition to the Mount", "Me"),
            (88, "Blocking with High Round Kick + Inside Hook Takedown + Straight Footlock", "Me"),
            (55, "Standing Guillotine", "Me"),
            # Op attacks Me standing — strike defense
            (85, "Block Front Kick + Elbow Strike", "Op"),
            # Op attacks Me standing — headlock escapes
            (7, "Escape from Side Standing Headlock + Rear Takedown + Technical Mount + Armbar", "Op"),
            (10, "Escape from Rear Headlock with Forward Takedown & Outside Hook Takedown", "Op"),
            (34, "Headlock Escape Taking the Back + Shoulder Lock", "Op"),
            (58, "Escape Side Headlock Standing with Punches", "Op"),
            (79, "Escape from Front Headlock to Turtle + Inversion + Technical Mount + Straight Armbar", "Op"),
            (82, "Headlock Escape Roll Reversal + Armbar", "Op"),
            # Op attacks Me standing — clinch & hold escapes
            (19, "Double Lapel Grab Escape + Outside Hook Takedown + Mount + Straight Armbar", "Op"),
            (22, "Two Hand Throat Grab Escape + Block Knee Strike + Jab Slip + Body Lock Takedown + Mount", "Op"),
            (67, "Escape from Front Bear Hug Over the Arms + Hip Throw + Knee on Belly", "Op"),
            (70, "Escape from Rear Bear Hug Over the Arms + Rear Takedown + Sidemount Control", "Op"),
            (91, "Escape from Rear Bear Hug Under the Arms + Break Grips + Outside Hook Takedown + Sidemount", "Op"),
            (94, "Rear Bear Hug Escape Over the Arm + Hook on the Leg + Hand on the Floor + Leg Lock", "Op"),
        ],
        "transit_react": [],
    },

    # ── Level 1: Hips ─────────────────────────────────────────────
    "CGRD": {
        "level": 1,
        "label": "Closed Guard (Hips)",
        "define": (
            "FacingOpposed, NotOnGround(Op.Ba). "
            "Both legs wrap torso with feet locked (Me.Le+→Op.To, Me.Le-→Op.To, "
            "Me.Fo-→Me.Fo+ closure). Helicity -, +, 0."
        ),
        "control": [],
        "attack_defend": [
            # Me attacks from closed guard (guard stays closed)
            (3, "Scissor Sweep", "Me"),
            (5, "X Collar Choke from Closed Guard", "Me"),
            (6, "X Collar Choke from Closed Guard with Thumbs Inside Collar", "Me"),
            (50, "Pendulum Sweep", "Me"),
            (51, "Straight Armbar from Closed Guard when Opponent Defends Pendulum Sweep", "Me"),
            (53, "Take the Back from Closed Guard", "Me"),
            (54, "Triangle from Closed Guard Controlling the Sleeve and Wrist", "Me"),
            (74, "Sit-Up Sweep from Closed Guard", "Me"),
            (75, "Kimura from Closed Guard", "Me"),
            # SD: Op strikes from inside guard, Me defends
            (25, "Blocking Punches from the Closed Guard + Distance Management + Control the Arms + Armbar", "Op"),
            (28, "Blocking Punches from the Closed Guard + Distance Management + Upkick + Technical Lift", "Op"),
            (73, "Blocking Punches from Closed Guard Bottom + Clinch + Triangle Choke", "Op"),
            (76, "Distance Management from Closed Guard Bottom + Knee Shield + Upkick + Technical Lift", "Op"),
        ],
        "transit_react": [
            # Op breaks posture / opens guard (CGRD → OGRD)
            (14, "Safe Posture + Opening the Guard with Knees + Elbows Closed", "Op"),
            (62, "Open the Guard on the Knees with Two Hands on the Belt", "Op"),
            (65, "Opening the Guard Standing Up Controlling the Collar and Hip", "Op"),
            # Op passes guard (CGRD → SCTR)
            (15, "One Arm Under the Leg Guard Pass + Sidemount Control Blocking Hip and Controlling Shoulder", "Op"),
            (17, "One Arm Under the Leg Guard Pass + Standing Up Holding the Sleeve", "Op"),
            (18, "Knee Slide Guard Pass + Sidemount", "Op"),
            (63, "Knee Slide Guard Pass Controlling the Sleeve", "Op"),
            (66, "Guard Pass Standing Up with Both Arms Under the Legs", "Op"),
            # SD: Full sequence drill
            (31, "Escape from the Closed Guard + Pass the Guard + Side Mount Control + Mount + Bridge Mount Escape (Repeating)", "Op"),
        ],
    },

    # ── Level 3: Feet ─────────────────────────────────────────────
    "OGRD": {
        "level": 3,
        "label": "Open Guard (Feet)",
        "define": (
            "FacingOpposed, OnGround(Me.Ba). "
            "Superclass: feet/legs engaged as first line of defense. "
            "Subtypes (DLR, SLX, RDLR, LSSO, OMOP) each add one CON."
        ),
        "control": [
            (77, "Spider Guard Control with Opponent Bullfighting or Posturing", "Me"),
        ],
        "attack_defend": [
            (26, "Pull Feet Sweep with Opponent Standing", "Me"),
            (27, "Waiter Sweep", "Me"),
            (29, "Tripod Sweep", "Me"),
            (30, "Outside Hook Sweep when Opponent Defends Tripod Sweep", "Me"),
            (78, "Spider Guard Sweep with Opponent on his Knees", "Me"),
        ],
        "transit_react": [
            # Me transitions to closed guard (OGRD → CGRD close)
            (2, "Pulling to the Closed Guard Using the Foot on the Hip", "Me"),
            # Op passes open guard (OGRD → SCTR/MNT pass)
            (38, "Open the Guard on the Knees + Over the Leg Guard Pass", "Op"),
            (41, "Spider Guard Bull-Fight Pass — Turning the Wheel + Sidemount Control", "Op"),
            (42, "Spider Guard Bull-Fight Pass with Hips Forward + Sidemount Control", "Op"),
            (86, "Open the Guard Standing Up with Two Hands on the Pants", "Op"),
            (87, "Leg Drag Guard Pass", "Op"),
            (89, "Open the Guard on the Knees with both Hands on the Pants", "Op"),
            (90, "Two Arms Under the Leg Guard Pass on the Knees", "Op"),
        ],
    },

    # ── Level 2: Knees ────────────────────────────────────────────
    "HGRD": {
        "level": 2,
        "label": "Half Guard (Knees)",
        "define": (
            "FacingOpposed, OnGround(Me.Ba). "
            "One leg entangles opponent's leg (Me.Le→Op.Le, unsigned, helicity -)."
        ),
        "control": [],
        "attack_defend": [
            (21, "Half Guard Sweep using the Underhook and Controlling Opponent's Foot", "Me"),
            (81, "Half Guard Sweep Using the Underhook and Controlling Opponent's Foot", "Me"),
        ],
        "transit_react": [
            # Op passes half guard
            (39, "Half Guard Pass Using the Hook + Transition to Mount", "Op"),
        ],
    },

    # ── Level 0: Passed ───────────────────────────────────────────
    "SCTR": {
        "level": 0,
        "label": "Side Control (Passed)",
        "define": (
            "OnGround(Op.Ba). "
            "Arm wraps torso (Me.Ar+→Op.To, helicity -). "
            "Forbidden: Me.Le→Op.Le (that would be half guard)."
        ),
        "control": [],
        "attack_defend": [
            # Me attacks from side control
            (45, "Uppercut Choke with the Opponent's Arm Trapped", "Me"),
            (48, "Spinning Armbar from Sidemount", "Me"),
            # Op defends / escapes side control
            (8, "Escape from Sidemount Recovering the Closed Guard", "Op"),
            (9, "Escape from Sidemount when Opponent Bridges Hip and Head + Recovering Closed Guard Using Leg Over Top", "Op"),
            (80, "Escape from Sidemount Control with Opponent + Recovering Half Guard", "Op"),
            (83, "Escape from Sidemount Anticipating the Guard Pass + Elbow Control + Recovering the Guard", "Op"),
            (84, "Escape from Sidemount Anticipating the Guard Pass + Inversion with Hand on Belt", "Op"),
            # SD: Escape sidemount with punches
            (1, "Escape from Sidemount with Punches + Recovering the Guard + Technical Lift", "Op"),
            (4, "Escape from Sidemount with Punches + Bridge + Technical Lift", "Op"),
        ],
        "transit_react": [
            # Me advances (SCTR → MNT)
            (44, "Transition to the Mount Switching the Passing Leg Over", "Me"),
            (47, "Transition to the Mount Sliding the Knee Over the Belly", "Me"),
            # Op escapes (SCTR → CGRD/HGRD/TRTL recover)
            (11, "Escape from Sidemount to Turtle Position", "Op"),
        ],
    },

    "MNT": {
        "level": 0,
        "label": "Mount (Passed)",
        "define": (
            "FacingOpposed, OnGround(Op.Ba). "
            "Both legs wrap torso (Me.Le+→Op.To, Me.Le-→Op.To, helicity -, +)."
        ),
        "control": [
            (57, "Technical Mount + Two Collars Choke", "Me"),
        ],
        "attack_defend": [
            # Me attacks from mount
            (56, "X Choke from the Mount with Four Fingers Inside Collar & Thumb Inside Collar", "Me"),
            (59, "Straight Armbar from the Mount", "Me"),
            (60, "Key Lock from the Mount", "Me"),
            # Op defends / escapes mount
            (20, "Escape from Mount Control with Opponent + Recovering Half Guard", "Op"),
            (23, "Escape from Mount Using the Elbows when Opponent Does Not Open Knee + Recovering Full Guard", "Op"),
            (92, "Escape from Mount Using the Elbows when Opponent Opens Knee + Recovering Closed Guard", "Op"),
            (95, "Escape from Mount Using Elbows when Opponent Initiates Transition to Mount + Take the Back", "Op"),
        ],
        "transit_react": [
            # Knee on belly (MNT variant)
            (24, "Knee on Belly Escape Pushing the Belt Knot + Half Technical Lift + Ankle Pick", "Op"),
            (93, "Knee on Belly Escape from Mount Using Elbows when Opponent Opens Knee + Recovering Closed Guard (Repeating)", "Op"),
            (96, "Knee on Belly Escape Turning the Back + Open Guard", "Op"),
        ],
    },

    "TRTL": {
        "level": 0,
        "label": "Turtle (Passed)",
        "define": (
            "FacingAligned. "
            "Torso-to-torso contact (Op.To→Me.To, helicity 0). "
            "Forbidden: Op legs wrapping Me torso (that would be back control)."
        ),
        "control": [],
        "attack_defend": [
            (12, "Double Leg Takedown from Turtle Position", "Op"),
            # SD: Block punches from turtle
            (49, "Blocking Punches from the Turtle Position + Recovering the Guard", "Op"),
            (52, "Block Punches from Turtle Position + Transition to Turtle + Recovering the Guard", "Op"),
        ],
        "transit_react": [
            # Me recovers guard from turtle (TRTL → OGRD recover)
            (32, "Recovering the Guard from the Rear Turtle Position", "Me"),
            (33, "Recovering the Guard from the Front Turtle Position", "Me"),
            # Op takes back from turtle (TRTL → BCTR advance)
            (71, "Taking the Back from Turtle Position Using the Lapel Grip", "Op"),
        ],
    },

    "BCTR": {
        "level": 0,
        "label": "Back Control (Passed)",
        "define": (
            "FacingAligned, NotOnGround(Op.Ba). "
            "Both legs wrap torso (Me.Le+→Op.To, Me.Le-→Op.To, helicity -, +). "
            "Forbidden: Me.Fo closure (that would be closed guard from behind)."
        ),
        "control": [
            (68, "Mount Seatbelt Grip Opening the Space for the Hook", "Me"),
        ],
        "attack_defend": [
            # Me attacks from back
            (69, "Cock Choke", "Me"),
            (72, "Two Collars Choke & Rear Naked Choke", "Me"),
            # Op defends / escapes back
            (35, "Bridge Escape from the Back Position using the Bridge + Avoiding the Mount + Recovering the Guard", "Op"),
            (36, "Bridge Escape from the Back Position using the Bridge + Mount (Taking Turns)", "Op"),
        ],
        "transit_react": [],
    },
}


# ── Cross-position transitions ────────────────────────────────────
# Techniques that explicitly cross between two radicals.
# (gb1_num, name, from_radical, to_radical, perspective)

TRANSITIONS = [
    # Takedowns (SD): STND → ground
    (13, "Jab Slip to Double Leg Takedown", "STND", "SCTR", "Me"),
    (16, "Cross Punch Slip to Single Leg Takedown", "STND", "SCTR", "Me"),
    (37, "Distance Management + Body Lock Takedown + Sidemount", "STND", "SCTR", "Me"),
    (40, "Distance Management + Double Leg", "STND", "SCTR", "Me"),
    (43, "Blocking Hooks + Body Lock Takedown", "STND", "SCTR", "Me"),
    (46, "Bodylock Clinch + Forward Takedown", "STND", "SCTR", "Me"),
    (61, "Block Hook Punch + Hip Throw", "STND", "MNT", "Me"),
    (64, "Slip Hook Punch + Bodylock Takedown + Mount", "STND", "MNT", "Me"),
    (88, "Blocking Round Kick + Inside Hook Takedown", "STND", "SCTR", "Me"),
    # Guard closing: OGRD → CGRD
    (2, "Pulling to Closed Guard", "OGRD", "CGRD", "Me"),
    # Guard passing: CGRD → SCTR
    (15, "One Arm Under Leg Guard Pass + Sidemount", "CGRD", "SCTR", "Op"),
    (18, "Knee Slide Guard Pass + Sidemount", "CGRD", "SCTR", "Op"),
    (63, "Knee Slide Guard Pass Controlling Sleeve", "CGRD", "SCTR", "Op"),
    (66, "Guard Pass Standing Both Arms Under Legs", "CGRD", "SCTR", "Op"),
    # Open guard passing: OGRD → SCTR
    (38, "Over the Leg Guard Pass", "OGRD", "SCTR", "Op"),
    (41, "Spider Guard Bull-Fight Pass + Sidemount", "OGRD", "SCTR", "Op"),
    (42, "Spider Guard Bull-Fight Pass Hips Forward + Sidemount", "OGRD", "SCTR", "Op"),
    # Half guard passing: HGRD → MNT
    (39, "Half Guard Pass Using Hook + Transition to Mount", "HGRD", "MNT", "Op"),
    # Side control advance: SCTR → MNT
    (44, "Transition to Mount Switching Passing Leg Over", "SCTR", "MNT", "Me"),
    (47, "Transition to Mount Sliding Knee Over Belly", "SCTR", "MNT", "Me"),
    # Side control escape: SCTR → CGRD
    (8, "Escape Sidemount Recovering Closed Guard", "SCTR", "CGRD", "Op"),
    (80, "Escape Sidemount Recovering Half Guard", "SCTR", "HGRD", "Op"),
    # Side control escape: SCTR → TRTL
    (11, "Escape Sidemount to Turtle", "SCTR", "TRTL", "Op"),
    # Mount escape: MNT → CGRD/HGRD
    (20, "Escape Mount Recovering Half Guard", "MNT", "HGRD", "Op"),
    (23, "Escape Mount Recovering Full Guard", "MNT", "CGRD", "Op"),
    (92, "Escape Mount Recovering Closed Guard", "MNT", "CGRD", "Op"),
    # Turtle recovery: TRTL → OGRD
    (32, "Recovering Guard from Rear Turtle", "TRTL", "OGRD", "Me"),
    (33, "Recovering Guard from Front Turtle", "TRTL", "OGRD", "Me"),
    # Turtle → Back control: TRTL → BCTR
    (71, "Taking Back from Turtle Using Lapel Grip", "TRTL", "BCTR", "Op"),
    # Back escape: BCTR → CGRD
    (35, "Bridge Escape from Back + Recovering Guard", "BCTR", "CGRD", "Op"),
]
