import pytest
from data.schema import Pose, Keypoint
from data.loader import DEFAULT_PATH
from data.label_map import normalize
from dic.body_parts import LimbRef, AxisDef
from dic.relations import CON
from dic.frames import FacingOpposed, FacingAligned, OnGround
from tools.axis_reconstruction import (
    reconstruct_axes, torso_length, torso_center, facing_direction,
    Vec2, point_to_segment_distance,
)
from tools.contact_inference import (
    infer_contacts, infer_frame_constraints, match_radical,
    InferredCON, InferredFrame,
)


# ── Vec2 tests ────────────────────────────────────────────────────

class TestVec2:
    def test_add(self):
        v = Vec2(1, 2) + Vec2(3, 4)
        assert v.x == 4 and v.y == 6

    def test_sub(self):
        v = Vec2(5, 7) - Vec2(2, 3)
        assert v.x == 3 and v.y == 4

    def test_length(self):
        assert Vec2(3, 4).length() == pytest.approx(5.0)

    def test_normalized(self):
        n = Vec2(0, 5).normalized()
        assert n.x == pytest.approx(0.0)
        assert n.y == pytest.approx(1.0)

    def test_cross_sign(self):
        assert Vec2(1, 0).cross(Vec2(0, 1)) > 0
        assert Vec2(1, 0).cross(Vec2(0, -1)) < 0

    def test_dot(self):
        assert Vec2(1, 0).dot(Vec2(0, 1)) == pytest.approx(0.0)
        assert Vec2(1, 0).dot(Vec2(1, 0)) == pytest.approx(1.0)

    def test_zero_normalized(self):
        n = Vec2(0, 0).normalized()
        assert n.x == 0 and n.y == 0


class TestPointToSegment:
    def test_perpendicular(self):
        d = point_to_segment_distance(Vec2(1, 1), Vec2(0, 0), Vec2(2, 0))
        assert d == pytest.approx(1.0)

    def test_at_endpoint(self):
        d = point_to_segment_distance(Vec2(3, 0), Vec2(0, 0), Vec2(2, 0))
        assert d == pytest.approx(1.0)

    def test_on_segment(self):
        d = point_to_segment_distance(Vec2(1, 0), Vec2(0, 0), Vec2(2, 0))
        assert d == pytest.approx(0.0)


# ── synthetic pose helpers ────────────────────────────────────────

def _standing_pose(x=0, y=0):
    """Upright figure, nose above shoulders, facing camera."""
    return Pose([
        Keypoint(x+100, y+50,  0.9),   # 0  nose
        Keypoint(x+102, y+48,  0.9),   # 1  l_eye
        Keypoint(x+98,  y+48,  0.9),   # 2  r_eye
        Keypoint(x+105, y+50,  0.9),   # 3  l_ear
        Keypoint(x+95,  y+50,  0.9),   # 4  r_ear
        Keypoint(x+85,  y+100, 0.9),   # 5  l_shoulder
        Keypoint(x+115, y+100, 0.9),   # 6  r_shoulder
        Keypoint(x+75,  y+150, 0.9),   # 7  l_elbow
        Keypoint(x+125, y+150, 0.9),   # 8  r_elbow
        Keypoint(x+70,  y+190, 0.9),   # 9  l_wrist
        Keypoint(x+130, y+190, 0.9),   # 10 r_wrist
        Keypoint(x+90,  y+200, 0.9),   # 11 l_hip
        Keypoint(x+110, y+200, 0.9),   # 12 r_hip
        Keypoint(x+85,  y+280, 0.9),   # 13 l_knee
        Keypoint(x+115, y+280, 0.9),   # 14 r_knee
        Keypoint(x+85,  y+360, 0.9),   # 15 l_ankle
        Keypoint(x+115, y+360, 0.9),   # 16 r_ankle
    ])


def _mount_poses():
    """Me on top straddling Op. Feet tucked near Op torso midline.
    Me faces up (nose above shoulders), Op faces down (nose below shoulders)."""
    me = Pose([
        Keypoint(200, 80,  0.9),   # nose (above shoulders -> facing up)
        Keypoint(202, 78,  0.9),
        Keypoint(198, 78,  0.9),
        Keypoint(205, 80,  0.9),
        Keypoint(195, 80,  0.9),
        Keypoint(180, 130, 0.9),   # l_shoulder
        Keypoint(220, 130, 0.9),   # r_shoulder
        Keypoint(170, 170, 0.9),   # l_elbow
        Keypoint(230, 170, 0.9),   # r_elbow
        Keypoint(165, 200, 0.9),   # l_wrist
        Keypoint(235, 200, 0.9),   # r_wrist
        Keypoint(185, 220, 0.9),   # l_hip
        Keypoint(215, 220, 0.9),   # r_hip
        Keypoint(170, 280, 0.9),   # l_knee (straddling)
        Keypoint(230, 280, 0.9),   # r_knee
        Keypoint(190, 330, 0.9),   # l_ankle (tucked near Op torso)
        Keypoint(210, 330, 0.9),   # r_ankle
    ])
    op = Pose([
        Keypoint(200, 380, 0.9),   # nose (below shoulders -> facing down)
        Keypoint(202, 382, 0.9),
        Keypoint(198, 382, 0.9),
        Keypoint(205, 385, 0.9),
        Keypoint(195, 385, 0.9),
        Keypoint(175, 290, 0.9),   # l_shoulder
        Keypoint(225, 290, 0.9),   # r_shoulder
        Keypoint(160, 320, 0.9),   # l_elbow
        Keypoint(240, 320, 0.9),   # r_elbow
        Keypoint(155, 350, 0.9),   # l_wrist
        Keypoint(245, 350, 0.9),   # r_wrist
        Keypoint(185, 370, 0.9),   # l_hip (high y = on ground)
        Keypoint(215, 370, 0.9),   # r_hip
        Keypoint(180, 440, 0.9),   # l_knee
        Keypoint(220, 440, 0.9),   # r_knee
        Keypoint(180, 500, 0.9),   # l_ankle
        Keypoint(220, 500, 0.9),   # r_ankle
    ])
    return me, op


def _back_control_poses():
    """Me behind Op, both facing right (side view). Me's feet hook Op torso.
    Shoulders spread vertically, torsos extend along x-axis.
    Both fighters at similar height (no ground detection) so BCTR's NotOnGround
    frame gets 0.5 confidence. Ankles bracket Op's torso axis."""
    me = Pose([
        Keypoint(250, 178, 0.9),   # 0  nose (right of sh_mid -> facing right)
        Keypoint(252, 176, 0.9),   # 1
        Keypoint(248, 176, 0.9),   # 2
        Keypoint(255, 178, 0.9),   # 3
        Keypoint(245, 178, 0.9),   # 4
        Keypoint(200, 190, 0.9),   # 5  l_shoulder
        Keypoint(200, 155, 0.9),   # 6  r_shoulder
        Keypoint(170, 205, 0.9),   # 7  l_elbow (wrapping Op)
        Keypoint(170, 145, 0.9),   # 8  r_elbow
        Keypoint(280, 190, 0.9),   # 9  l_wrist (grip on Op)
        Keypoint(280, 150, 0.9),   # 10 r_wrist
        Keypoint(130, 190, 0.9),   # 11 l_hip
        Keypoint(130, 155, 0.9),   # 12 r_hip
        Keypoint(220, 182, 0.9),   # 13 l_knee (hooking near Op hip-side)
        Keypoint(220, 148, 0.9),   # 14 r_knee (hooking near Op shoulder-side)
        Keypoint(260, 172, 0.9),   # 15 l_ankle (hook on Op torso, hip-side)
        Keypoint(260, 148, 0.9),   # 16 r_ankle (hook on Op torso, sh-side)
    ])
    op = Pose([
        Keypoint(370, 160, 0.9),   # 0  nose (right of sh_mid -> facing right)
        Keypoint(372, 158, 0.9),   # 1
        Keypoint(368, 158, 0.9),   # 2
        Keypoint(375, 160, 0.9),   # 3
        Keypoint(365, 160, 0.9),   # 4
        Keypoint(320, 180, 0.9),   # 5  l_shoulder
        Keypoint(320, 140, 0.9),   # 6  r_shoulder
        Keypoint(350, 195, 0.9),   # 7  l_elbow
        Keypoint(350, 125, 0.9),   # 8  r_elbow
        Keypoint(370, 200, 0.9),   # 9  l_wrist
        Keypoint(370, 120, 0.9),   # 10 r_wrist
        Keypoint(240, 180, 0.9),   # 11 l_hip
        Keypoint(240, 140, 0.9),   # 12 r_hip
        Keypoint(210, 190, 0.9),   # 13 l_knee
        Keypoint(210, 130, 0.9),   # 14 r_knee
        Keypoint(190, 195, 0.9),   # 15 l_ankle
        Keypoint(190, 125, 0.9),   # 16 r_ankle
    ])
    return me, op


# ── axis reconstruction tests ─────────────────────────────────────

class TestAxisReconstruction:
    def test_standing_produces_5_axes(self):
        axes = reconstruct_axes(_standing_pose(), "Me")
        assert len(axes) == 5  # Le-, Le+, Ar-, Ar+, To

    def test_axis_parts(self):
        axes = reconstruct_axes(_standing_pose(), "Me")
        parts = {a.limb_ref.part + a.limb_ref.sign for a in axes}
        assert parts == {"Le-", "Le+", "Ar-", "Ar+", "To"}

    def test_torso_length_positive(self):
        assert torso_length(_standing_pose()) > 0

    def test_torso_center_location(self):
        c = torso_center(_standing_pose(x=100))
        assert 190 < c.x < 210
        assert 140 < c.y < 160

    def test_low_confidence_excluded(self):
        pose = _standing_pose()
        pose.keypoints[15] = Keypoint(85, 360, 0.05)
        axes = reconstruct_axes(pose, "Me")
        parts = {a.limb_ref.part + a.limb_ref.sign for a in axes}
        assert "Le-" not in parts
        assert "Le+" in parts

    def test_axis_direction_points_proximal(self):
        axes = reconstruct_axes(_standing_pose(), "Me")
        for ax in axes:
            if ax.limb_ref.part == "Le":
                assert ax.direction.y < 0  # ankle->hip = upward = negative y

    def test_axis_length_reasonable(self):
        axes = reconstruct_axes(_standing_pose(), "Me")
        for ax in axes:
            assert ax.length > 10


# ── facing direction tests ────────────────────────────────────────

class TestFacingDirection:
    def test_mount_facing_opposed(self):
        me, op = _mount_poses()
        me_f = facing_direction(me)
        op_f = facing_direction(op)
        dot = me_f.dot(op_f)
        assert dot < -0.3, f"expected opposed facing, got dot={dot}"

    def test_back_control_facing_aligned(self):
        me, op = _back_control_poses()
        me_f = facing_direction(me)
        op_f = facing_direction(op)
        dot = me_f.dot(op_f)
        assert dot > 0.3, f"expected aligned facing, got dot={dot}"


# ── contact inference tests ───────────────────────────────────────

class TestContactInference:
    def test_mount_produces_contacts(self):
        me, op = _mount_poses()
        contacts = infer_contacts(me, op)
        assert len(contacts) > 0

    def test_contacts_sorted_by_confidence(self):
        me, op = _mount_poses()
        contacts = infer_contacts(me, op)
        for i in range(len(contacts) - 1):
            assert contacts[i].confidence >= contacts[i + 1].confidence

    def test_contact_has_valid_helicity(self):
        me, op = _mount_poses()
        for c in infer_contacts(me, op):
            assert c.con.helicity in ("+", "-")

    def test_contact_distance_normalized(self):
        me, op = _mount_poses()
        for c in infer_contacts(me, op):
            assert 0 <= c.distance <= PROXIMITY_THRESHOLD
            assert c.confidence > 0

    def test_back_control_produces_contacts(self):
        me, op = _back_control_poses()
        contacts = infer_contacts(me, op)
        assert len(contacts) > 0


# ── frame constraint inference tests ──────────────────────────────

class TestFrameConstraints:
    def test_mount_facing_opposed(self):
        me, op = _mount_poses()
        frames = infer_frame_constraints(me, op)
        types = [type(f.constraint) for f in frames]
        assert FacingOpposed in types

    def test_mount_op_on_ground(self):
        me, op = _mount_poses()
        frames = infer_frame_constraints(me, op)
        ground = [f for f in frames if isinstance(f.constraint, OnGround)]
        assert len(ground) >= 1
        assert ground[0].constraint.part.role == "Op"
        assert ground[0].constraint.part.part == "Ba"

    def test_back_control_facing_aligned(self):
        me, op = _back_control_poses()
        frames = infer_frame_constraints(me, op)
        types = [type(f.constraint) for f in frames]
        assert FacingAligned in types


# ── radical matching tests ────────────────────────────────────────

class TestRadicalMatching:
    def test_match_returns_results(self):
        me, op = _mount_poses()
        contacts = infer_contacts(me, op)
        frames = infer_frame_constraints(me, op)
        matches = match_radical(contacts, frames)
        assert len(matches) > 0

    def test_matches_sorted_by_confidence(self):
        me, op = _mount_poses()
        contacts = infer_contacts(me, op)
        frames = infer_frame_constraints(me, op)
        matches = match_radical(contacts, frames)
        for i in range(len(matches) - 1):
            assert matches[i].confidence >= matches[i + 1].confidence

    def test_mount_best_match_has_frame_constraints(self):
        me, op = _mount_poses()
        contacts = infer_contacts(me, op)
        frames = infer_frame_constraints(me, op)
        matches = match_radical(contacts, frames)
        if matches:
            best = matches[0]
            assert best.radical_name in ("MNT", "BCTR")

    def test_mount_matches_mnt_not_single_con(self):
        """Mount with both Le CONs + FacingOpposed + OnGround must match MNT first."""
        me, op = _mount_poses()
        contacts = infer_contacts(me, op)
        frames = infer_frame_constraints(me, op)
        matches = match_radical(contacts, frames)
        assert len(matches) > 0
        assert matches[0].radical_name == "MNT"
        assert matches[0].confidence > matches[-1].confidence

    def test_back_control_matches_bctr(self):
        """Same CON pattern but FacingAligned must match BCTR, not MNT."""
        me, op = _back_control_poses()
        contacts = infer_contacts(me, op)
        frames = infer_frame_constraints(me, op)
        matches = match_radical(contacts, frames)
        assert len(matches) > 0
        assert matches[0].radical_name == "BCTR"

    def test_single_con_matches_when_no_multi_con(self):
        """Two standing figures should match single-CON radicals, not MNT/BCTR."""
        me = _standing_pose(x=0, y=0)
        op = _standing_pose(x=50, y=0)
        contacts = infer_contacts(me, op)
        frames = infer_frame_constraints(me, op)
        matches = match_radical(contacts, frames)
        if matches:
            assert matches[0].radical_name not in ("MNT", "BCTR")


# ── cycle / forbidden contact tests ──────────────────────────────

from tools.contact_inference import _has_forbidden_contact, PROXIMITY_THRESHOLD
from dic.frames import NotOnGround


def _fo_closure_con(conf=0.5, dist=0.1):
    fo_l = AxisDef(LimbRef("Me", "Fo", "-"), "Fo", "Kn")
    fo_r = AxisDef(LimbRef("Me", "Fo", "+"), "Fo", "Kn")
    return InferredCON(CON(fo_l, fo_r, "deep", "0"), conf, dist)


def _le_to_cons():
    """Standard Le+→To and Le-→To contacts for mount/guard/back control."""
    le_plus = AxisDef(LimbRef("Me", "Le", "+"), "Fo", "Hp")
    le_minus = AxisDef(LimbRef("Me", "Le", "-"), "Fo", "Hp")
    op_to = AxisDef(LimbRef("Op", "To", ""), "Hp", "Sh")
    return [
        InferredCON(CON(le_plus, op_to, "d1", "-"), 0.5, 0.1),
        InferredCON(CON(le_minus, op_to, "d2", "+"), 0.5, 0.1),
    ]


def _not_on_ground_op():
    return [InferredFrame(NotOnGround(LimbRef("Op", "Ba")), 0.8)]


class TestCycleMatching:
    def test_cgrd_positive_with_closure(self):
        """Le+→To, Le-→To, Fo-→Fo+ closure → must match CGRD."""
        contacts = _le_to_cons() + [_fo_closure_con()]
        frames = _not_on_ground_op()
        matches = match_radical(contacts, frames)
        names = [m.radical_name for m in matches]
        assert "CGRD" in names
        assert matches[0].radical_name == "CGRD"

    def test_cgrd_negative_without_closure(self):
        """Le+→To, Le-→To, NO closure → must NOT match CGRD."""
        contacts = _le_to_cons()
        frames = _not_on_ground_op()
        matches = match_radical(contacts, frames)
        names = [m.radical_name for m in matches]
        assert "CGRD" not in names

    def test_bctr_positive_without_closure(self):
        """Le+→To, Le-→To, no closure, FacingAligned → must match BCTR."""
        from dic.frames import FacingAligned
        contacts = _le_to_cons()
        frames = _not_on_ground_op() + [InferredFrame(FacingAligned(), 0.9)]
        matches = match_radical(contacts, frames)
        assert matches[0].radical_name == "BCTR"

    def test_bctr_negative_with_closure(self):
        """Le+→To, Le-→To, WITH closure → BCTR must be forbidden."""
        from dic.frames import FacingAligned
        contacts = _le_to_cons() + [_fo_closure_con()]
        frames = _not_on_ground_op() + [InferredFrame(FacingAligned(), 0.9)]
        matches = match_radical(contacts, frames)
        names = [m.radical_name for m in matches]
        assert "BCTR" not in names

    def test_opponent_self_con_preserved(self):
        """Op→Op CON must be accepted and stored."""
        op_ha = AxisDef(LimbRef("Op", "Ha", "+"), "Ha", "Wr")
        op_wr = AxisDef(LimbRef("Op", "Wr", "-"), "Wr", "El")
        con = CON(op_ha, op_wr, "d", "0")
        ic = InferredCON(con, 0.6, 0.15)
        assert ic.con.attacker.limb_ref.role == "Op"
        assert ic.con.axis.limb_ref.role == "Op"
        assert ic.confidence == 0.6

    def test_closure_helicity_is_zero(self):
        """Inferred closure CON must have helicity 0."""
        me, op = _mount_poses()
        contacts = infer_contacts(me, op)
        closures = [c for c in contacts
                    if c.con.attacker.limb_ref.role == "Me"
                    and c.con.axis.limb_ref.role == "Me"]
        for c in closures:
            assert c.con.helicity == "0"


# ── SCTR matching tests ──────────────────────────────────────────

from dic.frames import KneeBracket, NotKneeBracket


def _ar_to_cons():
    """Standard Ar+→To and Ar-→To contacts for side control."""
    ar_plus = AxisDef(LimbRef("Me", "Ar", "+"), "Wr", "Sh")
    ar_minus = AxisDef(LimbRef("Me", "Ar", "-"), "Wr", "Sh")
    op_to = AxisDef(LimbRef("Op", "To", ""), "Hp", "Sh")
    return [
        InferredCON(CON(ar_plus, op_to, "d1", "-"), 0.5, 0.08),
        InferredCON(CON(ar_minus, op_to, "d2", "+"), 0.5, 0.10),
    ]


def _on_ground_op():
    from dic.frames import OnGround
    return [InferredFrame(OnGround(LimbRef("Op", "Ba", "")), 0.9)]


class TestSCTRMatching:
    def test_sctr_positive(self):
        """Ar→To + Z0(Op.Ba) → must match SCTR."""
        contacts = _ar_to_cons()
        frames = _on_ground_op()
        matches = match_radical(contacts, frames)
        names = [m.radical_name for m in matches]
        assert "SCTR" in names
        assert matches[0].radical_name == "SCTR"

    def test_sctr_outscores_single_con_radicals(self):
        """SCTR (1 CON + 1 FRM) must outscore DLR/SLX (1 CON + 0 FRM)."""
        contacts = _ar_to_cons()
        frames = _on_ground_op()
        matches = match_radical(contacts, frames)
        sctr = [m for m in matches if m.radical_name == "SCTR"]
        single = [m for m in matches if m.radical_name in ("DLR", "SLX", "RDLR", "LSSO", "OMOP")]
        assert len(sctr) == 1
        if single:
            assert sctr[0].confidence > single[0].confidence

    def test_sctr_does_not_match_without_ground(self):
        """SCTR requires OnGround(Op.Ba); without it, SCTR must not match."""
        contacts = _ar_to_cons()
        frames = _not_on_ground_op()
        matches = match_radical(contacts, frames)
        names = [m.radical_name for m in matches]
        assert "SCTR" not in names

    def test_sctr_does_not_match_without_arm_contacts(self):
        """SCTR requires arm-to-torso; leg-to-torso must not trigger SCTR."""
        contacts = _le_to_cons()
        frames = _on_ground_op()
        matches = match_radical(contacts, frames)
        names = [m.radical_name for m in matches]
        assert "SCTR" not in names

    def test_sctr_with_single_arm_still_matches(self):
        """Even with just one arm on torso, SCTR should match (partial credit)."""
        ar_plus = AxisDef(LimbRef("Me", "Ar", "+"), "Wr", "Sh")
        op_to = AxisDef(LimbRef("Op", "To", ""), "Hp", "Sh")
        contacts = [InferredCON(CON(ar_plus, op_to, "d1", "-"), 0.5, 0.08)]
        frames = _on_ground_op()
        matches = match_radical(contacts, frames)
        names = [m.radical_name for m in matches]
        assert "SCTR" in names

    def test_mnt_outscores_sctr_when_legs_present(self):
        """MNT (2 CON + 2 FRM) outscores SCTR (1 CON + 1 FRM) with facing."""
        from dic.frames import FacingOpposed
        contacts = _le_to_cons() + _ar_to_cons()
        frames = _on_ground_op() + [InferredFrame(FacingOpposed(), 0.95)]
        matches = match_radical(contacts, frames)
        mnt = [m for m in matches if m.radical_name == "MNT"]
        sctr = [m for m in matches if m.radical_name == "SCTR"]
        assert len(mnt) == 1
        assert len(sctr) == 1
        assert mnt[0].confidence > sctr[0].confidence

    def test_mnt_outscores_sctr_even_without_facing(self):
        """MNT with MISSING_FACING_PENALTY still outscores SCTR."""
        contacts = _le_to_cons() + _ar_to_cons()
        frames = _on_ground_op()
        matches = match_radical(contacts, frames)
        mnt = [m for m in matches if m.radical_name == "MNT"]
        sctr = [m for m in matches if m.radical_name == "SCTR"]
        assert len(mnt) == 1
        assert len(sctr) == 1
        assert mnt[0].confidence > sctr[0].confidence


class TestSCTRStrictDiagnostic:
    """SCTR_STRICT is not in ALL_RADICALS but can be used as a diagnostic."""

    def test_strict_blocked_by_kbr(self):
        """SCTR_STRICT requires NotKneeBracket; KBR present blocks it."""
        from dic.radicals import SCTR_STRICT
        from dic.frames import OnGround
        contacts = _ar_to_cons()
        frames = [
            InferredFrame(OnGround(LimbRef("Op", "Ba", "")), 0.9),
            InferredFrame(KneeBracket(LimbRef("Op", "To", "")), 0.8),
        ]
        matches = match_radical(contacts, frames, {"SCTR_STRICT": SCTR_STRICT})
        names = [m.radical_name for m in matches]
        assert "SCTR_STRICT" not in names

    def test_strict_blocked_by_bilateral_le(self):
        """SCTR_STRICT bilateral forbid blocks when both Le→To present."""
        from dic.radicals import SCTR_STRICT
        contacts = _le_to_cons() + _ar_to_cons()
        frames = _on_ground_op() + [InferredFrame(NotKneeBracket(LimbRef("Op", "To", "")), 0.7)]
        matches = match_radical(contacts, frames, {"SCTR_STRICT": SCTR_STRICT})
        names = [m.radical_name for m in matches]
        assert "SCTR_STRICT" not in names

    def test_strict_passes_with_single_le(self):
        """Single Le→To does NOT trigger SCTR_STRICT bilateral forbid."""
        from dic.radicals import SCTR_STRICT
        le_plus = AxisDef(LimbRef("Me", "Le", "+"), "Fo", "Hp")
        op_to = AxisDef(LimbRef("Op", "To", ""), "Hp", "Sh")
        single_le = [InferredCON(CON(le_plus, op_to, "d1", "-"), 0.3, 0.15)]
        contacts = single_le + _ar_to_cons()
        frames = _on_ground_op() + [InferredFrame(NotKneeBracket(LimbRef("Op", "To", "")), 0.7)]
        matches = match_radical(contacts, frames, {"SCTR_STRICT": SCTR_STRICT})
        names = [m.radical_name for m in matches]
        assert "SCTR_STRICT" in names


def _side_control_poses():
    """Me perpendicular on top of Op. Me's arms wrap Op's torso.
    Op is on back (hips high y). Me's knees sprawled to one side,
    NOT bracketing Op's torso (key for NOT KBR)."""
    me = Pose([
        Keypoint(220, 120, 0.9),   # 0  nose
        Keypoint(222, 118, 0.9),   # 1
        Keypoint(218, 118, 0.9),   # 2
        Keypoint(225, 120, 0.9),   # 3
        Keypoint(215, 120, 0.9),   # 4
        Keypoint(190, 160, 0.9),   # 5  l_shoulder
        Keypoint(250, 160, 0.9),   # 6  r_shoulder
        Keypoint(175, 200, 0.9),   # 7  l_elbow (reaching under Op head)
        Keypoint(265, 200, 0.9),   # 8  r_elbow (underhook side)
        Keypoint(200, 250, 0.9),   # 9  l_wrist (on Op torso area)
        Keypoint(240, 250, 0.9),   # 10 r_wrist (on Op torso area)
        Keypoint(180, 280, 0.9),   # 11 l_hip
        Keypoint(260, 280, 0.9),   # 12 r_hip
        Keypoint(100, 350, 0.9),   # 13 l_knee (sprawled far from Op torso)
        Keypoint(80,  380, 0.9),   # 14 r_knee (sprawled far)
        Keypoint(70,  410, 0.9),   # 15 l_ankle
        Keypoint(50,  440, 0.9),   # 16 r_ankle
    ])
    op = Pose([
        Keypoint(120, 300, 0.9),   # 0  nose (to the side, below shoulders)
        Keypoint(122, 302, 0.9),   # 1
        Keypoint(118, 302, 0.9),   # 2
        Keypoint(125, 305, 0.9),   # 3
        Keypoint(115, 305, 0.9),   # 4
        Keypoint(170, 230, 0.9),   # 5  l_shoulder
        Keypoint(230, 230, 0.9),   # 6  r_shoulder
        Keypoint(150, 280, 0.9),   # 7  l_elbow
        Keypoint(250, 280, 0.9),   # 8  r_elbow
        Keypoint(140, 320, 0.9),   # 9  l_wrist
        Keypoint(260, 320, 0.9),   # 10 r_wrist
        Keypoint(180, 340, 0.9),   # 11 l_hip (high y -> on ground)
        Keypoint(220, 340, 0.9),   # 12 r_hip
        Keypoint(175, 420, 0.9),   # 13 l_knee
        Keypoint(225, 420, 0.9),   # 14 r_knee
        Keypoint(170, 490, 0.9),   # 15 l_ankle
        Keypoint(230, 490, 0.9),   # 16 r_ankle
    ])
    return me, op


class TestSCTRSyntheticPose:
    def test_side_control_arm_contacts_detected(self):
        """Side control must produce Me.Ar -> Op.To contacts."""
        me, op = _side_control_poses()
        contacts = infer_contacts(me, op)
        ar_to_to = [c for c in contacts
                    if c.con.attacker.limb_ref.role == "Me"
                    and c.con.attacker.limb_ref.part == "Ar"
                    and c.con.axis.limb_ref.role == "Op"
                    and c.con.axis.limb_ref.part == "To"]
        assert len(ar_to_to) >= 1

    def test_side_control_not_kbr_detected(self):
        """Side control with sprawled knees must produce NotKneeBracket."""
        me, op = _side_control_poses()
        frames = infer_frame_constraints(me, op)
        nkbr = [f for f in frames if isinstance(f.constraint, NotKneeBracket)]
        assert len(nkbr) == 1, f"Expected NotKneeBracket, got: {[type(f.constraint).__name__ for f in frames]}"

    def test_mount_straddle_kbr_detected(self):
        """Mount with knees straddling (one near head, one near hip) must produce KneeBracket."""
        me_base, op = _mount_poses()
        kps = list(me_base.keypoints)
        kps[13] = Keypoint(170, 300, 0.9)   # l_knee near Op shoulders (y=290)
        kps[14] = Keypoint(230, 360, 0.9)   # r_knee near Op hips (y=370)
        kps[15] = Keypoint(170, 340, 0.9)   # l_ankle
        kps[16] = Keypoint(230, 400, 0.9)   # r_ankle
        me = Pose(kps)
        frames = infer_frame_constraints(me, op)
        kbr = [f for f in frames if isinstance(f.constraint, KneeBracket)]
        assert len(kbr) == 1, f"Expected KneeBracket, got: {[type(f.constraint).__name__ for f in frames]}"


# ── HGRD matching tests ───────────────────────────────────────────

def _bilateral_le_le_cons():
    """Both Me legs on Op.Le+ — half guard pattern (without closure)."""
    me_le_plus = AxisDef(LimbRef("Me", "Le", "+"), "Fo", "Hp")
    me_le_minus = AxisDef(LimbRef("Me", "Le", "-"), "Fo", "Hp")
    op_le_plus = AxisDef(LimbRef("Op", "Le", "+"), "Fo", "Hp")
    return [
        InferredCON(CON(me_le_plus, op_le_plus, "d1", "-"), 0.5, 0.08),
        InferredCON(CON(me_le_minus, op_le_plus, "d2", "-"), 0.5, 0.10),
    ]


def _fo_closure():
    """Foot closure — ankles locked together (cycle edge)."""
    fo_l = AxisDef(LimbRef("Me", "Fo", "-"), "Fo", "Kn")
    fo_r = AxisDef(LimbRef("Me", "Fo", "+"), "Fo", "Kn")
    return InferredCON(CON(fo_l, fo_r, "deep", "0"), 0.6, 0.05)


def _hgrd_contacts():
    """Full HGRD contact set: bilateral Le→Le on same Op leg."""
    return _bilateral_le_le_cons()


def _on_ground_me():
    from dic.frames import OnGround
    return [InferredFrame(OnGround(LimbRef("Me", "Ba", "")), 0.9)]


def _facing_opposed():
    from dic.frames import FacingOpposed
    return [InferredFrame(FacingOpposed(), 0.85)]


class TestHGRDMatching:

    def test_hgrd_positive(self):
        """Bilateral Le→Le + OnGround(Me) + FacingOpposed → HGRD."""
        contacts = _hgrd_contacts()
        frames = _on_ground_me() + _facing_opposed()
        matches = match_radical(contacts, frames)
        names = [m.radical_name for m in matches]
        assert "HGRD" in names

    def test_hgrd_outscores_dlr(self):
        """HGRD (2 CON + 2 FRM) outscores DLR (1 CON + 0 FRM)."""
        contacts = _hgrd_contacts()
        frames = _on_ground_me() + _facing_opposed()
        matches = match_radical(contacts, frames)
        hgrd = [m for m in matches if m.radical_name == "HGRD"]
        dlr = [m for m in matches if m.radical_name == "DLR"]
        assert len(hgrd) == 1
        if dlr:
            assert hgrd[0].confidence > dlr[0].confidence

    def test_hgrd_fails_without_ground(self):
        """HGRD requires OnGround(Me.Ba); without it, HGRD must not match."""
        from dic.frames import NotOnGround
        contacts = _hgrd_contacts()
        frames = [InferredFrame(NotOnGround(LimbRef("Me", "Ba", "")), 0.9)] + _facing_opposed()
        matches = match_radical(contacts, frames)
        names = [m.radical_name for m in matches]
        assert "HGRD" not in names
        assert "HGRD_L" not in names

    def test_hgrd_fails_with_single_le(self):
        """Single Le→Le should not match HGRD (needs 2 distinct Le→Le contacts)."""
        me_le_minus = AxisDef(LimbRef("Me", "Le", "-"), "Fo", "Hp")
        op_le_plus = AxisDef(LimbRef("Op", "Le", "+"), "Fo", "Hp")
        contacts = [
            InferredCON(CON(me_le_minus, op_le_plus, "d", "-"), 0.5, 0.08),
        ]
        frames = _on_ground_me() + _facing_opposed()
        matches = match_radical(contacts, frames)
        names = [m.radical_name for m in matches]
        assert "HGRD" not in names
        assert "HGRD_L" not in names

    def test_hgrd_does_not_match_le_to_to(self):
        """Le→To contacts should not trigger HGRD."""
        contacts = _le_to_cons()
        frames = _on_ground_me() + _facing_opposed()
        matches = match_radical(contacts, frames)
        names = [m.radical_name for m in matches]
        assert "HGRD" not in names
        assert "HGRD_L" not in names

    def test_hgrd_does_not_cross_sign(self):
        """Contacts on Op.Le+ must not match HGRD_L (which requires Op.Le-)."""
        contacts = _hgrd_contacts()  # targets Op.Le+
        frames = _on_ground_me() + _facing_opposed()
        matches = match_radical(contacts, frames)
        names = [m.radical_name for m in matches]
        assert "HGRD" in names
        assert "HGRD_L" not in names

    def test_hgrd_coexists_with_dlr(self):
        """Both HGRD and DLR can match the same frame — HGRD ranks higher."""
        contacts = _hgrd_contacts()
        frames = _on_ground_me() + _facing_opposed()
        matches = match_radical(contacts, frames)
        names = [m.radical_name for m in matches]
        assert "HGRD" in names
        dlr_matches = [n for n in names if n in ("DLR", "SLX", "RDLR")]
        assert len(dlr_matches) > 0
        assert names.index("HGRD") < names.index(dlr_matches[0])


# ── bottleneck scoring tests ──────────────────────────────────────

class TestBottleneckScoring:

    def test_strong_single_beats_weak_bilateral(self):
        """A strong DLR (1 CON, high quality) must beat weak HGRD (2 CON, low quality)."""
        me_le_plus = AxisDef(LimbRef("Me", "Le", "+"), "Fo", "Hp")
        me_le_minus = AxisDef(LimbRef("Me", "Le", "-"), "Fo", "Hp")
        op_le_plus = AxisDef(LimbRef("Op", "Le", "+"), "Fo", "Hp")
        contacts = [
            InferredCON(CON(me_le_minus, op_le_plus, "d", "-"), 0.8, 0.05),
            InferredCON(CON(me_le_plus, op_le_plus, "d1", "-"), 0.15, 0.25),
        ]
        frames = _on_ground_me() + _facing_opposed()
        matches = match_radical(contacts, frames)
        names = [m.radical_name for m in matches]
        dlr_idx = names.index("DLR") if "DLR" in names else len(names)
        hgrd_idx = names.index("HGRD") if "HGRD" in names else len(names)
        assert dlr_idx < hgrd_idx, f"DLR should rank above HGRD: {names[:5]}"

    def test_strong_bilateral_still_beats_single(self):
        """When both HGRD contacts are strong, HGRD should beat DLR."""
        contacts = _hgrd_contacts()  # both at 0.5 confidence
        frames = _on_ground_me() + _facing_opposed()
        matches = match_radical(contacts, frames)
        names = [m.radical_name for m in matches]
        assert "HGRD" in names
        dlr_matches = [n for n in names if n in ("DLR", "SLX", "RDLR")]
        if dlr_matches:
            assert names.index("HGRD") < names.index(dlr_matches[0])

    def test_cgrd_dominates_with_closure(self):
        """CGRD with 3 strong contacts (incl. closure) outscores 1-contact radicals."""
        from dic.frames import NotOnGround
        me_le_plus = AxisDef(LimbRef("Me", "Le", "+"), "Fo", "Hp")
        me_le_minus = AxisDef(LimbRef("Me", "Le", "-"), "Fo", "Hp")
        op_to = AxisDef(LimbRef("Op", "To", ""), "Hp", "Sh")
        fo_l = AxisDef(LimbRef("Me", "Fo", "-"), "Fo", "Kn")
        fo_r = AxisDef(LimbRef("Me", "Fo", "+"), "Fo", "Kn")
        contacts = [
            InferredCON(CON(me_le_plus, op_to, "d1", "-"), 0.6, 0.08),
            InferredCON(CON(me_le_minus, op_to, "d2", "+"), 0.6, 0.10),
            InferredCON(CON(fo_l, fo_r, "d3", "0"), 0.5, 0.05),
        ]
        frames = [InferredFrame(NotOnGround(LimbRef("Op", "Ba", "")), 0.7)]
        matches = match_radical(contacts, frames)
        names = [m.radical_name for m in matches]
        assert names[0] == "CGRD"


# ── closure memory tests ─────────────────────────────────────────

class TestClosureMemory:

    def _make_norm(self, image, frame, has_pose=True):
        from data.label_map import NormalizedAnnotation
        if has_pose:
            me = Pose([Keypoint(0, 0, 0.9)] * 17)
            op = Pose([Keypoint(0, 0, 0.9)] * 17)
        else:
            me, op = None, None
        return NormalizedAnnotation(
            vicos_position="closed_guard1", blisp_label="GRD_CLP",
            ambiguity="low", image=image, frame=frame,
            me_pose=me, op_pose=op,
        )

    def _make_contacts_with_closure(self, conf=0.5):
        from tools.contact_inference import InferredCON
        fo_l = AxisDef(LimbRef("Me", "Fo", "-"), "Fo", "Kn")
        fo_r = AxisDef(LimbRef("Me", "Fo", "+"), "Fo", "Kn")
        return [InferredCON(CON(fo_l, fo_r, "deep", "0"), conf, 0.05)]

    def _make_contacts_without_closure(self):
        le = AxisDef(LimbRef("Me", "Le", "+"), "Fo", "Hp")
        op_to = AxisDef(LimbRef("Op", "To", ""), "Hp", "Sh")
        return [InferredCON(CON(le, op_to, "d1", "-"), 0.5, 0.1)]

    def test_fills_one_frame_gap(self):
        """Closure in frames 1 and 3 should inject into frame 2."""
        from tools.annotate import _inject_closure_memory, _find_closure_conf
        n1 = self._make_norm("0100001", 1)
        n2 = self._make_norm("0100002", 2)
        n3 = self._make_norm("0100003", 3)
        c1 = self._make_contacts_with_closure(0.6)
        c2 = self._make_contacts_without_closure()
        c3 = self._make_contacts_with_closure(0.4)
        per_frame = [
            (n1, c1, []),
            (n2, c2, []),
            (n3, c3, []),
        ]
        _inject_closure_memory(per_frame, k=3)
        assert _find_closure_conf(per_frame[0][1]) == 0.6
        injected = _find_closure_conf(per_frame[1][1])
        assert injected > 0, "Frame 2 should have injected closure"
        assert injected < 0.6, "Injected closure should be decayed"
        assert _find_closure_conf(per_frame[2][1]) == 0.4

    def test_does_not_cross_video_boundary(self):
        """Closure in video 01 must not leak into video 02."""
        from tools.annotate import _inject_closure_memory, _find_closure_conf
        n_v1 = self._make_norm("0100010", 10)
        n_v2 = self._make_norm("0200001", 1)
        c_v1 = self._make_contacts_with_closure(0.8)
        c_v2 = self._make_contacts_without_closure()
        per_frame = [
            (n_v1, c_v1, []),
            (n_v2, c_v2, []),
        ]
        _inject_closure_memory(per_frame, k=5)
        assert _find_closure_conf(per_frame[0][1]) == 0.8
        assert _find_closure_conf(per_frame[1][1]) == 0.0

    def test_does_not_affect_hgrd(self):
        """Injecting closure should not help HGRD match (HGRD has no closure req)."""
        from tools.annotate import _inject_closure_memory
        from tools.contact_inference import InferredCON, InferredFrame

        me_le_minus = AxisDef(LimbRef("Me", "Le", "-"), "Fo", "Hp")
        op_le_plus = AxisDef(LimbRef("Op", "Le", "+"), "Fo", "Hp")
        single_le = [InferredCON(CON(me_le_minus, op_le_plus, "d", "-"), 0.5, 0.08)]

        n1 = self._make_norm("0100001", 1)
        n2 = self._make_norm("0100002", 2)
        c1 = self._make_contacts_with_closure(0.8)
        per_frame = [
            (n1, c1, []),
            (n2, list(single_le), []),
        ]
        _inject_closure_memory(per_frame, k=3)

        frames = _on_ground_me() + _facing_opposed()
        matches_after = match_radical(per_frame[1][1], frames)
        names = [m.radical_name for m in matches_after]
        assert "HGRD" not in names
        assert "HGRD_L" not in names

    def test_decay_is_distance_proportional(self):
        """Closer frames provide stronger closure evidence."""
        from tools.annotate import _inject_closure_memory, _find_closure_conf
        norms = [self._make_norm(f"01000{i:02d}", i) for i in range(1, 8)]
        contacts = [self._make_contacts_without_closure() for _ in range(7)]
        contacts[0] = self._make_contacts_with_closure(0.6)
        per_frame = [(n, c, []) for n, c in zip(norms, contacts)]
        _inject_closure_memory(per_frame, k=5)
        conf_at_1 = _find_closure_conf(per_frame[1][1])
        conf_at_3 = _find_closure_conf(per_frame[3][1])
        assert conf_at_1 > conf_at_3 > 0

    def test_no_injection_when_closure_exists(self):
        """Frames that already have closure should not get a second one."""
        from tools.annotate import _inject_closure_memory, _find_closure_conf
        n1 = self._make_norm("0100001", 1)
        n2 = self._make_norm("0100002", 2)
        c1 = self._make_contacts_with_closure(0.8)
        c2 = self._make_contacts_with_closure(0.3)
        per_frame = [
            (n1, c1, []),
            (n2, c2, []),
        ]
        _inject_closure_memory(per_frame, k=3)
        assert _find_closure_conf(per_frame[1][1]) == 0.3
        closure_count = sum(
            1 for c in per_frame[1][1]
            if c.con.helicity == "0" and c.con.attacker.limb_ref.part == "Fo"
        )
        assert closure_count == 1


# ── integration on real data ──────────────────────────────────────

ANNOTATIONS_EXIST = DEFAULT_PATH.exists()
skip_no_data = pytest.mark.skipif(not ANNOTATIONS_EXIST, reason="data/raw not present")


@skip_no_data
class TestContactOnRealData:
    @pytest.fixture(scope="class")
    def samples(self):
        from data.loader import load_annotations
        from collections import defaultdict
        all_anns = load_annotations()
        by_class = defaultdict(list)
        for a in all_anns:
            if a.pose1 and a.pose2:
                by_class[a.position].append(a)
        out = []
        for cls, anns in by_class.items():
            out.extend(anns[:3])
        return out

    def test_contacts_inferred_without_error(self, samples):
        for ann in samples:
            n = normalize(ann)
            if n.me_pose and n.op_pose:
                contacts = infer_contacts(n.me_pose, n.op_pose)
                assert isinstance(contacts, list)

    def test_frame_constraints_without_error(self, samples):
        for ann in samples:
            n = normalize(ann)
            if n.me_pose and n.op_pose:
                frames = infer_frame_constraints(n.me_pose, n.op_pose)
                assert isinstance(frames, list)

    def test_radical_matching_without_error(self, samples):
        for ann in samples[:18]:
            n = normalize(ann)
            if n.me_pose and n.op_pose:
                contacts = infer_contacts(n.me_pose, n.op_pose)
                frames = infer_frame_constraints(n.me_pose, n.op_pose)
                matches = match_radical(contacts, frames)
                assert isinstance(matches, list)
