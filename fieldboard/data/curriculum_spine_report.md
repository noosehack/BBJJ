# Curriculum Spine — Selected Roads

Generated: 2026-05-17
Total roads: 24
Spine: 9 | Branch: 8 | Network: 7

---

## SPINE ROADS (Beginner Highways)

### S1: Closed Guard Hip Bump Sweep to Mount Armbar

**Fieldboard**: CGRD.CTRL → MNT.SWP → MNT.CTRL → MNT.SUB
**Sources**: bjjgraph, flowstate, fsm (3)

**Sequence**:
  1. **Closed Guard** [CTRL] — posture control, collar grips
  1. **Mount** [SWP] — hip bump sweep / scissor sweep
  1. **Mount** [CTRL] — base, grapevines or heels
  1. **Armbar** [SUB] — isolate arm, hips high, extend

**Source evidence**:
  - bjjgraph: Hip Bump Sweep / 100% Sweep → Armbar from Mount
  - flowstate: Closed guard → Mount top → Armbar
  - fsm: FullGuard → Mount

**Checkpoints**:
  - Control: Posture break in closed guard; Mount base stabilization
  - Stabilization: Secure mount before attacking — grapevines or heel hooks on hips
  - Transition: Hip bump mechanic: sit up, post hand, sweep over shoulder
  - Submission: Isolate arm → figure-four grip → hips high → lean back to extend

**Failure topology** [SAFE]:
  - sweep_fails: Still in closed guard (safe)
  - mount_lost: Falls to half guard or guard — positions already taught
  - armbar_fails: Opponent stacks — return to mount or closed guard

**Duality**: Op learns: posture defense in guard, mount escape, armbar defense

**Reusable mechanics**: hip escape, bridge, posture control, arm isolation

### S2: Closed Guard Arm Drag to Back Control RNC

**Fieldboard**: CGRD.CTRL → BCTR.SWP → BCTR.CTRL → BCTR.SUB
**Sources**: bjjgraph, flowstate, fsm (3)

**Sequence**:
  1. **Closed Guard** [CTRL] — break posture, wrist control
  1. **Back Control** [SWP] — arm drag, climb to back
  1. **Back Control** [CTRL] — seatbelt grip, hooks in
  1. **Rear Naked Choke** [SUB] — hand fight, sink choke

**Source evidence**:
  - bjjgraph: Arm Drag Sweep → Rear Naked Choke
  - flowstate: Closed guard → Back control → RNC
  - fsm: FullGuard → BackControl → RNC

**Checkpoints**:
  - Control: Posture break in closed guard; Seatbelt + hooks in back control
  - Stabilization: Secure seatbelt grip before attacking choke
  - Transition: Arm drag: 2-on-1, pull arm across, hip out, climb behind
  - Submission: Clear collar defense → slide choking arm under chin → lock figure-four → squeeze

**Failure topology** [SAFE]:
  - drag_fails: Still in closed guard (safe)
  - back_lost: Opponent turns in — land in mount or closed guard (safe)
  - rnc_fails: Opponent defends chin — maintain back control, re-attack

**Duality**: Op learns: posture in guard, back escape (turn to guard), RNC defense

**Reusable mechanics**: arm drag, hip escape, seatbelt, back hooks

### S3: Half Guard Pass to Side Control Americana

**Fieldboard**: HGRD.CTRL → SCTR.TRZ → SCTR.CTRL → SCTR.SUB
**Sources**: bjjgraph, flowstate, bjj_graph_clj (3)

**Sequence**:
  1. **Half Guard** [CTRL] — crossface, underhook battle
  1. **Side Control** [TRZ] — knee slice / crossface pass
  1. **Side Control** [CTRL] — crossface + underhook, chest pressure
  1. **Americana** [SUB] — isolate near arm, figure-four, paint brush

**Source evidence**:
  - bjjgraph: Knee Slice Pass / Crossface Pass → Americana from Side Control
  - flowstate: Half guard → Side control → Americana
  - bjj_graph_clj: Half Guard → Side Mount

**Checkpoints**:
  - Control: Win underhook in half guard; Crossface + chest pressure in side control
  - Stabilization: Flatten opponent before passing — deny underhook
  - Transition: Knee slice: free trapped leg, slide knee across, clear to side control
  - Submission: Pin wrist to mat → figure-four grip → paint brush away from head

**Failure topology** [SAFE]:
  - pass_fails: Still in half guard top (safe)
  - side_lost: Opponent re-guards — back to half guard (safe)
  - americana_fails: Opponent straightens arm — transition to armbar or maintain control

**Duality**: Op learns: half guard retention, side control escape, americana defense

**Reusable mechanics**: crossface, underhook, knee slice, figure-four

### S4: Butterfly Sweep to Mount

**Fieldboard**: OGRD.Butterfly.CTRL → MNT.SWP → MNT.CTRL
**Sources**: bjjgraph, fsm (2)

**Sequence**:
  1. **Butterfly Guard** [CTRL] — double underhooks, head position
  1. **Mount** [SWP] — elevator sweep — hook, off-balance, lift
  1. **Mount** [CTRL] — stabilize base

**Source evidence**:
  - bjjgraph: Basic Butterfly Sweep / Elevator Sweep → Mount
  - fsm: Butterfly → Mount

**Checkpoints**:
  - Control: Double underhooks seated, head on chest side
  - Stabilization: Land in mount, immediately establish base
  - Transition: Off-balance to one side → hook lift → roll over → land in mount

**Failure topology** [SAFE]:
  - sweep_fails: Still seated in butterfly (safe — re-grip, re-try)
  - mount_lost: Opponent bridges — fall to guard (safe)

**Duality**: Op learns: butterfly guard passing, mount escape

**Reusable mechanics**: underhook, butterfly hook, off-balance, mount base

### S5: Open Guard Scissor Sweep to Mount

**Fieldboard**: OGRD.CTRL → MNT.SWP → MNT.CTRL
**Sources**: bjjgraph, bjj_graph_clj (2)

**Sequence**:
  1. **Open Guard** [CTRL] — collar + sleeve grip
  1. **Mount** [SWP] — scissor sweep — shin across, pull, kick
  1. **Mount** [CTRL] — stabilize base

**Source evidence**:
  - bjjgraph: Scissor Sweep from Open Guard → Mount
  - bjj_graph_clj: Open Guard → Mount

**Checkpoints**:
  - Control: Collar grip + sleeve grip, shin across belly
  - Stabilization: Follow the sweep — post immediately on landing in mount
  - Transition: Shin across belly → pull collar down → kick bottom leg → roll over

**Failure topology** [SAFE]:
  - sweep_fails: Still in open guard (safe — retain grips)

**Duality**: Op learns: open guard passing, scissor sweep defense (posture + base)

**Reusable mechanics**: scissor motion, collar grip, sleeve control

### S6: Side Control to Mount Progression

**Fieldboard**: SCTR.CTRL → SCTR.KOB.TRZ → MNT.TRZ → MNT.CTRL
**Sources**: bjjgraph, flowstate (2)

**Sequence**:
  1. **Side Control** [CTRL] — crossface + underhook, heavy hips
  1. **Knee on Belly** [TRZ] — insert knee, pressure
  1. **Mount** [TRZ] — swing leg over, settle base
  1. **Mount** [CTRL] — grapevines, posture

**Source evidence**:
  - bjjgraph: Side Control → Knee on Belly → Mount / Arm Extraction to Mount
  - flowstate: Side control top → Mount top

**Checkpoints**:
  - Control: Crossface + chest pressure in side control; Knee pressure in KOB; Mount base
  - Stabilization: Each position is stable — can pause and consolidate
  - Transition: Side → KOB: slide knee onto belly. KOB → Mount: swing far leg over

**Failure topology** [SAFE]:
  - kob_lost: Falls back to side control (safe)
  - mount_lost: Falls to half guard (safe — already taught)

**Duality**: Op learns: side control escape (frame, hip escape, re-guard), KOB escape

**Reusable mechanics**: hip pressure, knee ride, weight distribution

### S7: Closed Guard Triangle Choke

**Fieldboard**: CGRD.CTRL → CGRD.TRZ → CGRD.SUB
**Sources**: bjjgraph, grapplemap, flowstate (3)

**Sequence**:
  1. **Closed Guard** [CTRL] — posture break, control wrists
  1. **Triangle Setup** [TRZ] — isolate one arm, hips up, leg over shoulder
  1. **Triangle Choke** [SUB] — lock triangle, angle, squeeze

**Source evidence**:
  - bjjgraph: Cross Collar Choke / Triangle from Closed Guard
  - grapplemap: full guard → triangle
  - flowstate: Closed guard → Triangle

**Checkpoints**:
  - Control: Posture break, wrist isolation
  - Stabilization: Lock triangle figure-four before finishing
  - Transition: Push one arm across → hips up → leg over far shoulder → lock ankles
  - Submission: Cut angle → pull head down → squeeze knees

**Failure topology** [SAFE]:
  - setup_fails: Still in closed guard (safe)
  - triangle_fails: Opponent postures out of half-locked triangle — return to guard
  - stacking: Opponent stacks — can unlock and return to guard, or sweep to mount

**Duality**: Op learns: posture maintenance, triangle defense (stack, posture, hide arm)

**Reusable mechanics**: hip elevation, angle cutting, leg dexterity

### S8: Mount Cross Collar Choke

**Fieldboard**: MNT.CTRL → MNT.SUB
**Sources**: bjjgraph, flowstate, grapplemap (3)

**Sequence**:
  1. **Mount** [CTRL] — high mount, walk hands up
  1. **Mount** [SUB] — feed first grip deep, second grip, squeeze

**Source evidence**:
  - bjjgraph: Cross Collar Choke from High Mount
  - flowstate: Mount top → Cross-collar choke
  - grapplemap: mount → choke

**Checkpoints**:
  - Control: High mount — walk knees to armpits
  - Stabilization: Secure first grip deep in collar before attacking
  - Submission: First hand deep in cross collar → second hand in → squeeze elbows together

**Failure topology** [SAFE]:
  - grip_stripped: Still in mount (safe)
  - bridged_off: Falls to guard (safe — already taught)

**Duality**: Op learns: mount escape (trap and roll, elbow-knee), choke defense

**Reusable mechanics**: mount pressure, collar grip, weight forward

### S9: Collar-Sleeve Guard Pull to Closed Guard

**Fieldboard**: OGRD.ColSlv.CTRL → CGRD.TRZ
**Sources**: bjj_graph_clj, bjjgraph (2)

**Sequence**:
  1. **Collar-Sleeve** [CTRL] — collar grip + sleeve grip, foot on hip
  1. **Closed Guard** [TRZ] — pull to closed guard, lock feet

**Source evidence**:
  - bjj_graph_clj: Guard Pull (Gracie Combatives)
  - bjjgraph: Open Guard → Closed Guard transition

**Checkpoints**:
  - Control: Collar grip four fingers deep, sleeve grip at wrist — establish before pulling
  - Transition: Foot on hip to control distance, pull collar down, swing hips under, lock feet behind back

**Failure topology** [SAFE]:
  - pull_fails: Still in open guard (safe — retain grips, try again)
  - guard_not_closed: Feet don't lock — becomes open guard, not worse

**Duality**: Op learns: guard pull defense, posture when pulled, staying standing vs seated guard

**Reusable mechanics**: collar grip, sleeve grip, foot on hip, guard closing

---

## BRANCH ROADS (Intermediate Expansions)

### B1: Half Guard Underhook Sweep to Mount

**Fieldboard**: HGRD.CTRL → MNT.SWP
**Sources**: bjjgraph, flowstate (2)

**Sequence**:
  1. **Half Guard** [CTRL] — win underhook, come to knees
  1. **Mount** [SWP] — John Wayne sweep / underhook sweep

**Source evidence**:
  - bjjgraph: John Wayne Sweep → Mount
  - flowstate: Half guard bottom → Mount top

**Checkpoints**:
  - Control: Win underhook — get to hip, head under chin
  - Transition: Come to knees → drive forward → sweep over trapped leg → land in mount

**Failure topology** [RECOVERABLE]:
  - underhook_lost: Still in half guard bottom (safe — re-pummel)
  - sweep_fails: Dogfight position — scramble back to half guard or re-attack

**Duality**: Op learns: half guard top control, whizzer counter

**Reusable mechanics**: underhook, hip movement, drive

### B2: Half Guard to Side Control to Back Control

**Fieldboard**: HGRD.CTRL → SCTR.TRZ → BCTR.TRZ → BCTR.SUB
**Sources**: bjjgraph, flowstate (2)

**Sequence**:
  1. **Half Guard** [CTRL] — top position, crossface
  1. **Side Control** [TRZ] — pass half guard
  1. **Back Control** [TRZ] — opponent turns away → take back
  1. **Rear Naked Choke** [SUB] — seatbelt → RNC

**Source evidence**:
  - bjjgraph: Half Guard Pass → Side Control → Back Control → RNC
  - flowstate: Half guard → Side control → Back control

**Checkpoints**:
  - Control: Crossface in half guard top; Chest pressure in side control; Seatbelt + hooks
  - Stabilization: Secure each position before advancing
  - Transition: Pass half → settle side control → opponent turns → slide hooks in
  - Submission: Seatbelt → hand fight → sink RNC

**Failure topology** [SAFE]:
  - pass_fails: Still in half guard top (safe)
  - back_lost: Opponent turns in — land in mount or side control (safe)

**Duality**: Op learns: half guard retention, side escape, back escape

**Reusable mechanics**: passing, back take timing, seatbelt

### B3: Closed Guard Flower Sweep to Mount

**Fieldboard**: CGRD.CTRL → MNT.SWP
**Sources**: bjjgraph (1)

**Sequence**:
  1. **Closed Guard** [CTRL] — collar + sleeve grip
  1. **Mount** [SWP] — flower sweep — collar pull, leg kick-over

**Source evidence**:
  - bjjgraph: Flower Sweep → Mount

**Checkpoints**:
  - Control: Deep collar grip + same-side sleeve grip
  - Transition: Pull collar → kick far leg over → roll into mount

**Failure topology** [SAFE]:
  - sweep_fails: Still in closed guard (safe)

**Duality**: Op learns: base and posture in closed guard

**Reusable mechanics**: collar grip, leg dexterity, momentum

### B4: Side Control Arm Triangle

**Fieldboard**: SCTR.CTRL → SCTR.TRZ → SCTR.SUB
**Sources**: bjjgraph (1)

**Sequence**:
  1. **Side Control** [CTRL] — heavy crossface, far underhook
  1. **Arm Triangle Setup** [TRZ] — drive head to far side, lock head+arm
  1. **Arm Triangle** [SUB] — hop to mount side, squeeze

**Source evidence**:
  - bjjgraph: Arm Triangle from Top → Arm Triangle Finish

**Checkpoints**:
  - Control: Heavy crossface — opponent's chin forced to far side
  - Stabilization: Lock figure-four around head+arm before moving
  - Transition: Walk around to opposite side or hop to mount → squeeze
  - Submission: Gable grip → chest to floor → squeeze elbows

**Failure topology** [SAFE]:
  - setup_fails: Still in side control (safe)
  - choke_fails: Maintain side control — re-attack or transition

**Duality**: Op learns: frame defense, chin tuck, arm extraction

**Reusable mechanics**: crossface, head-arm control, squeeze mechanics

### B5: Kimura Sweep from Closed Guard

**Fieldboard**: CGRD.CTRL → CGRD.TRZ → MNT.SWP
**Sources**: bjjgraph (1)

**Sequence**:
  1. **Closed Guard** [CTRL] — break posture, wrist control
  1. **Kimura Grip** [TRZ] — 2-on-1 figure-four on far wrist
  1. **Mount or Side Control** [SWP] — hip out → sweep with kimura grip

**Source evidence**:
  - bjjgraph: Kimura Sweep → Mount / Side Control

**Checkpoints**:
  - Control: Posture break, isolate wrist
  - Stabilization: Secure kimura grip — figure-four is locked before sweeping
  - Transition: Hip out to kimura side → use grip leverage to sweep → land on top

**Failure topology** [SAFE]:
  - grip_fails: Still in closed guard (safe)
  - sweep_fails: Retain guard with kimura grip — can transition to armbar or triangle

**Duality**: Op learns: hand-on-mat defense, posture in guard

**Reusable mechanics**: kimura grip (reusable — appears in half guard, side control), hip escape

### B6: Turtle to Back Take

**Fieldboard**: TRTL.CTRL → BCTR.TRZ → BCTR.SUB
**Sources**: bjjgraph, flowstate (2)

**Sequence**:
  1. **Turtle** [CTRL] — opponent turtled, top position
  1. **Back Control** [TRZ] — seatbelt → insert hooks
  1. **Rear Naked Choke** [SUB] — hand fight → RNC

**Source evidence**:
  - bjjgraph: Chair Sit to Back / Seatbelt from Turtle → RNC
  - flowstate: Turtle → Back control → RNC

**Checkpoints**:
  - Control: Chest-to-back contact, seatbelt established
  - Stabilization: Seatbelt first → then insert hooks one at a time
  - Transition: Seatbelt grip → hip to mat → insert bottom hook → top hook
  - Submission: Hand fight to clear collar grip → slide arm under chin → lock RNC

**Failure topology** [RECOVERABLE]:
  - back_take_fails: Opponent sits out — scramble to side control or re-engage turtle (recoverable)
  - hooks_lost: Opponent rolls — can land in mount if hooks are lost (safe)

**Duality**: Op learns: turtle defense (granby roll, sit-out, stand up)

**Reusable mechanics**: seatbelt, hook insertion, chair sit

### B7: Open Guard Pass to Side Control

**Fieldboard**: OGRD.CTRL → SCTR.TRZ → SCTR.CTRL
**Sources**: bjjgraph, flowstate (2)

**Sequence**:
  1. **Open Guard** [CTRL] — standing, grip fighting
  1. **Side Control** [TRZ] — toreando / over-under pass
  1. **Side Control** [CTRL] — settle crossface + underhook

**Source evidence**:
  - bjjgraph: Various passes → Side Control
  - flowstate: Open guard → Side control top

**Checkpoints**:
  - Control: Grip fighting standing — control pants/ankles; Crossface in side control
  - Stabilization: Clear legs completely before settling side control
  - Transition: Grip ankles → push legs to one side → pass to opposite side → settle

**Failure topology** [SAFE]:
  - pass_fails: Opponent re-guards — still in open guard (safe)

**Duality**: Op learns: guard retention, re-guarding, grip stripping

**Reusable mechanics**: toreando grip, leg clearing, pressure passing

### B8: Closed Guard to Side Control Sweep

**Fieldboard**: CGRD.CTRL → SCTR.SWP → SCTR.CTRL → SCTR.SUB
**Sources**: bjjgraph, flowstate (2)

**Sequence**:
  1. **Closed Guard** [CTRL] — posture break
  1. **Side Control** [SWP] — 100% sweep / balloon sweep
  1. **Side Control** [CTRL] — settle crossface
  1. **Americana** [SUB] — isolate arm, figure-four

**Source evidence**:
  - bjjgraph: 100% Sweep → Side Control → Americana
  - flowstate: Closed guard → Side control → Americana

**Checkpoints**:
  - Control: Posture break in guard; Crossface in side control
  - Stabilization: Settle side control before attacking
  - Transition: Overhook + far leg → bridge and roll → land in side control
  - Submission: Pin wrist → figure-four → paint brush

**Failure topology** [SAFE]:
  - sweep_fails: Still in closed guard (safe)
  - side_lost: Opponent re-guards (safe)

**Duality**: Op learns: guard posture, side control escape, americana defense

**Reusable mechanics**: bridge and roll, crossface, americana

---

## NETWORK ROADS (Advanced Systems)

### N1: Closed Guard Attack Tree: Sweep-or-Submit

**Fieldboard**: CGRD.CTRL → CGRD.TRZ → MNT.SWP / CGRD.SUB
**Sources**: bjjgraph, flowstate, grapplemap (3)

**Sequence**:
  1. **Closed Guard** [CTRL] — posture break
  1. **Hip Bump / Kimura / Triangle** [TRZ] — if posture: hip bump. If hand posts: kimura. If arm in: triangle
  1. **Mount (hip bump) or Guard Sub** [SWP/SUB] — sweep leads to mount; grip leads to submission

**Source evidence**:
  - bjjgraph: Hip Bump Sweep / Kimura Sweep / Triangle chain
  - flowstate: Closed guard attack tree
  - grapplemap: full guard → various

**Checkpoints**:
  - Control: Posture break is the root — everything flows from here
  - Transition: Decision tree: read opponent's reaction, choose branch
  - Submission: Triangle or kimura from failed sweep defense

**Failure topology** [SAFE]:
  - all_fail: Still in closed guard (safe — the safest position to fail from)

**Duality**: Op learns: all guard defenses — posture, base, hand placement

**Decision tree**:
  - If opponent_postures: hip bump sweep → mount
  - If opponent_hand_posts: kimura grip → sweep or submit
  - If opponent_arm_across: triangle → finish or sweep to mount

**Reusable mechanics**: posture break, hip bump, kimura grip, triangle legs

### N2: Mount Attack Cycle: Choke-Armbar Dilemma

**Fieldboard**: MNT.CTRL → MNT.SUB
**Sources**: bjjgraph, flowstate, grapplemap (3)

**Sequence**:
  1. **Mount** [CTRL] — high mount, hands walk up
  1. **Choke or Armbar** [SUB] — if arms protect neck: armbar. If elbows flare: choke

**Source evidence**:
  - bjjgraph: Cross Collar Choke / Americana / Armbar from Mount — choice tree
  - flowstate: Mount → Americana / Cross-collar choke
  - grapplemap: mount → choke / arm-triangle

**Checkpoints**:
  - Control: High mount position
  - Transition: Read opponent's arm defense — neck or arms?
  - Submission: Choke: elbows open. Armbar: arms tight. Americana: arm pinned

**Failure topology** [SAFE]:
  - bridged_off: Land in guard (safe — taught in S1/S7)

**Duality**: Op learns: mount escape becomes urgent — bridge or elbow-knee

**Decision tree**:
  - If arms_protect_neck: armbar — step over head, lean back
  - If elbows_flare: cross collar choke or ezekiel
  - If arm_pinned: americana — paint brush

**Reusable mechanics**: mount pressure, opponent reading, attack chains

### N3: Back Control Attack System

**Fieldboard**: BCTR.CTRL → BCTR.SUB
**Sources**: bjjgraph, fsm (2)

**Sequence**:
  1. **Back Control** [CTRL] — seatbelt + hooks
  1. **RNC / Bow and Arrow / Armbar** [SUB] — hand fight → attack

**Source evidence**:
  - bjjgraph: RNC / Bow and Arrow Choke / Armbar from Back
  - fsm: BackControl → RNC

**Checkpoints**:
  - Control: Seatbelt grip, both hooks in, chest glued to back
  - Stabilization: Maintain hooks when opponent tries to escape
  - Transition: Hand fight to clear collar defense
  - Submission: RNC if chin exposed. Bow and arrow if lapel available. Armbar if arm isolatable

**Failure topology** [SAFE]:
  - opponent_escapes: Opponent turns in → land in mount (safe — already best position)
  - hooks_lost: Transition to body triangle or re-insert

**Duality**: Op learns: back escape — turn to guard, strip hooks, defend choke

**Decision tree**:
  - If chin_exposed: RNC — slide arm under chin, lock, squeeze
  - If lapel_available: bow and arrow — grab lapel, extend, squeeze
  - If arm_exposed: armbar from back — control arm, swivel, extend

**Reusable mechanics**: seatbelt, hook retention, hand fighting

### N4: Half Guard Passing Network

**Fieldboard**: HGRD.CTRL → SCTR.TRZ / MNT.TRZ / BCTR.TRZ
**Sources**: bjjgraph, flowstate, bjj_graph_clj (3)

**Sequence**:
  1. **Half Guard Top** [CTRL] — crossface, deny underhook
  1. **Side Control / Mount / Back** [TRZ] — multiple pass options

**Source evidence**:
  - bjjgraph: Knee Slice / Body Lock / Leg Weave / Crossface Pass → various
  - flowstate: Top half guard → Side control / Mount
  - bjj_graph_clj: Half Guard → Side Mount

**Checkpoints**:
  - Control: Win the underhook battle — this determines everything
  - Transition: Read opponent's frame → choose pass → clear leg → settle

**Failure topology** [RECOVERABLE]:
  - pass_fails: Still in half guard top (safe — dominant position)
  - swept: Guard player sweeps — land in half guard bottom (recoverable)

**Duality**: Op learns: half guard bottom game — underhook sweep, knee shield, re-guard

**Decision tree**:
  - If opponent_flat: knee slice through → side control
  - If opponent_frames: body lock → pass over or under
  - If opponent_underhooks: whizzer → crossface → flatten → pass

**Reusable mechanics**: crossface, underhook, knee slice, leg weave, body lock

### N5: Guard Pull to Sweep-or-Submit Chain

**Fieldboard**: OGRD.Standing.CTRL → CGRD.TRZ → CGRD.SWP / CGRD.SUB
**Sources**: bjjgraph, flowstate, bjj_graph_clj, fsm (4)

**Sequence**:
  1. **Standing** [CTRL] — grip fight, pull guard
  1. **Closed Guard** [TRZ] — pull to closed guard
  1. **Sweep → Mount OR Submit from Guard** [SWP/SUB] — attack tree from S1/S7/N1

**Source evidence**:
  - bjjgraph: Standing → Closed Guard → attack chains
  - flowstate: Standing / Neutral → Closed guard → attacks
  - bjj_graph_clj: Standing → Guard → various
  - fsm: GUARD → FullGuard → various

**Checkpoints**:
  - Control: Win grips standing; Secure closed guard on landing
  - Stabilization: Close guard immediately — don't settle in open guard if you want closed
  - Transition: Grip → sit → pull into closed guard → immediate posture break

**Failure topology** [RECOVERABLE]:
  - pull_fails: Opponent sprawls — seated in open guard (recoverable)
  - guard_passed: Opponent passes during pull — land in half guard or side control bottom (risky if unprepared)

**Duality**: Op learns: guard pull defense — sprawl, pass on the way down

**Reusable mechanics**: grip fighting, guard pulling, immediate control

### N6: Open Guard to Standing Takedown to Dominant

**Fieldboard**: OGRD.CTRL → OGRD.Standing.TRZ → SCTR.TRZ / MNT.TRZ
**Sources**: bjjgraph, flowstate (2)

**Sequence**:
  1. **Open Guard** [CTRL] — feet on hips, grip control
  1. **Standing** [TRZ] — technical standup
  1. **Side Control / Mount** [TRZ] — takedown → land on top

**Source evidence**:
  - bjjgraph: Open Guard → Standing Position → Side Control / Mount
  - flowstate: Open guard → Standing / Neutral → Side control / Mount

**Checkpoints**:
  - Control: Feet on hips, collar/sleeve or 2-on-1 grip
  - Transition: Technical standup → re-engage with takedown or pull guard

**Failure topology** [RECOVERABLE]:
  - standup_fails: Opponent follows down — still in open guard (safe)
  - takedown_fails: Opponent defends — standing neutral (recoverable)

**Duality**: Op learns: open guard passing, takedown defense

**Reusable mechanics**: technical standup, grip fighting, takedown

### N7: Positional Ladder: Guard → Side → Mount → Back → Finish

**Fieldboard**: HGRD.CTRL → SCTR.TRZ → MNT.TRZ → BCTR.TRZ → BCTR.SUB
**Sources**: bjjgraph, flowstate (2)

**Sequence**:
  1. **Half Guard / Open Guard** [CTRL] — any guard
  1. **Side Control** [TRZ] — pass guard
  1. **Mount** [TRZ] — advance to mount
  1. **Back Control** [TRZ] — opponent turns → take back
  1. **Rear Naked Choke** [SUB] — finish

**Source evidence**:
  - bjjgraph: Half Guard → Side Control → Mount → Back Control → RNC
  - flowstate: Half guard → Side control → Mount → Back control → RNC

**Checkpoints**:
  - Control: Every position is a stable checkpoint — can pause at any step
  - Stabilization: Consolidate each position 3-5 seconds before advancing
  - Transition: Pass → settle → advance → settle → advance → finish
  - Submission: RNC from back control

**Failure topology** [SAFE]:
  - at_any_step: Falling back one step is always safe (mount → side → guard)

**Duality**: Op perspective IS the escape ladder: escape back → escape mount → escape side → re-guard

**Reusable mechanics**: All prior mechanics combined — this is the synthesis road

---

## Summary: All Roads

| ID | Name | Tier | Steps | Sources | Failure | Fieldboard |
|----|------|------|-------|---------|---------|------------|
| S1 | Closed Guard Hip Bump Sweep to Mount Armbar | spine | 4 | 3 | safe | CGRD.CTRL → MNT.SWP → MNT.CTRL → MNT.SUB |
| S2 | Closed Guard Arm Drag to Back Control RNC | spine | 4 | 3 | safe | CGRD.CTRL → BCTR.SWP → BCTR.CTRL → BCTR.SUB |
| S3 | Half Guard Pass to Side Control Americana | spine | 4 | 3 | safe | HGRD.CTRL → SCTR.TRZ → SCTR.CTRL → SCTR.SUB |
| S4 | Butterfly Sweep to Mount | spine | 3 | 2 | safe | OGRD.Butterfly.CTRL → MNT.SWP → MNT.CTRL |
| S5 | Open Guard Scissor Sweep to Mount | spine | 3 | 2 | safe | OGRD.CTRL → MNT.SWP → MNT.CTRL |
| S6 | Side Control to Mount Progression | spine | 4 | 2 | safe | SCTR.CTRL → SCTR.KOB.TRZ → MNT.TRZ → MNT.CTRL |
| S7 | Closed Guard Triangle Choke | spine | 3 | 3 | safe | CGRD.CTRL → CGRD.TRZ → CGRD.SUB |
| S8 | Mount Cross Collar Choke | spine | 2 | 3 | safe | MNT.CTRL → MNT.SUB |
| S9 | Collar-Sleeve Guard Pull to Closed Guard | spine | 2 | 2 | safe | OGRD.ColSlv.CTRL → CGRD.TRZ |
| B1 | Half Guard Underhook Sweep to Mount | branch | 2 | 2 | recoverable | HGRD.CTRL → MNT.SWP |
| B2 | Half Guard to Side Control to Back Control | branch | 4 | 2 | safe | HGRD.CTRL → SCTR.TRZ → BCTR.TRZ → BCTR.SUB |
| B3 | Closed Guard Flower Sweep to Mount | branch | 2 | 1 | safe | CGRD.CTRL → MNT.SWP |
| B4 | Side Control Arm Triangle | branch | 3 | 1 | safe | SCTR.CTRL → SCTR.TRZ → SCTR.SUB |
| B5 | Kimura Sweep from Closed Guard | branch | 3 | 1 | safe | CGRD.CTRL → CGRD.TRZ → MNT.SWP |
| B6 | Turtle to Back Take | branch | 3 | 2 | recoverable | TRTL.CTRL → BCTR.TRZ → BCTR.SUB |
| B7 | Open Guard Pass to Side Control | branch | 3 | 2 | safe | OGRD.CTRL → SCTR.TRZ → SCTR.CTRL |
| B8 | Closed Guard to Side Control Sweep | branch | 4 | 2 | safe | CGRD.CTRL → SCTR.SWP → SCTR.CTRL → SCTR.SUB |
| N1 | Closed Guard Attack Tree: Sweep-or-Submit | network | 3 | 3 | safe | CGRD.CTRL → CGRD.TRZ → MNT.SWP / CGRD.SUB |
| N2 | Mount Attack Cycle: Choke-Armbar Dilemma | network | 2 | 3 | safe | MNT.CTRL → MNT.SUB |
| N3 | Back Control Attack System | network | 2 | 2 | safe | BCTR.CTRL → BCTR.SUB |
| N4 | Half Guard Passing Network | network | 2 | 3 | recoverable | HGRD.CTRL → SCTR.TRZ / MNT.TRZ / BCTR.TRZ |
| N5 | Guard Pull to Sweep-or-Submit Chain | network | 3 | 4 | recoverable | OGRD.Standing.CTRL → CGRD.TRZ → CGRD.SWP / CGRD.SUB |
| N6 | Open Guard to Standing Takedown to Dominant | network | 3 | 2 | recoverable | OGRD.CTRL → OGRD.Standing.TRZ → SCTR.TRZ / MNT.TRZ |
| N7 | Positional Ladder: Guard → Side → Mount → Back → Finish | network | 5 | 2 | safe | HGRD.CTRL → SCTR.TRZ → MNT.TRZ → BCTR.TRZ → BCTR.SUB |

## Position Coverage

Covered: back control, butterfly, closed guard, half guard, knee on belly, mount, open guard, side control, standing, turtle
All fundamental positions covered.

## Mechanic Reuse

  seatbelt                       ████ (4 roads)
  crossface                      ████ (4 roads)
  underhook                      ████ (4 roads)
  collar grip                    ████ (4 roads)
  hip escape                     ███ (3 roads)
  knee slice                     ██ (2 roads)
  leg dexterity                  ██ (2 roads)
  mount pressure                 ██ (2 roads)
  grip fighting                  ██ (2 roads)
  bridge                         █ (1 roads)
  posture control                █ (1 roads)
  arm isolation                  █ (1 roads)
  arm drag                       █ (1 roads)
  back hooks                     █ (1 roads)
  figure-four                    █ (1 roads)
