import pytest
from data.schema import Pose, Keypoint
from data.loader import DEFAULT_PATH
from data.label_map import normalize
from dic.frames import FacingOpposed, FacingAligned, OnGround
from tools.axis_reconstruction import (
    reconstruct_axes, torso_length, torso_center, facing_direction,
    Vec2, point_to_segment_distance,
)
from tools.contact_inference import (
    infer_contacts, infer_frame_constraints, match_radical,
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
    Shoulders spread vertically, torsos extend along x-axis."""
    me = Pose([
        Keypoint(250, 160, 0.9),   # 0  nose (right of sh_mid -> facing right)
        Keypoint(252, 158, 0.9),   # 1
        Keypoint(248, 158, 0.9),   # 2
        Keypoint(255, 160, 0.9),   # 3
        Keypoint(245, 160, 0.9),   # 4
        Keypoint(200, 180, 0.9),   # 5  l_shoulder
        Keypoint(200, 140, 0.9),   # 6  r_shoulder
        Keypoint(170, 195, 0.9),   # 7  l_elbow (wrapping Op)
        Keypoint(170, 125, 0.9),   # 8  r_elbow
        Keypoint(280, 185, 0.9),   # 9  l_wrist (grip on Op)
        Keypoint(280, 135, 0.9),   # 10 r_wrist
        Keypoint(130, 180, 0.9),   # 11 l_hip
        Keypoint(130, 140, 0.9),   # 12 r_hip
        Keypoint(200, 190, 0.9),   # 13 l_knee (hooking)
        Keypoint(200, 130, 0.9),   # 14 r_knee
        Keypoint(250, 185, 0.9),   # 15 l_ankle (hook on Op torso)
        Keypoint(250, 135, 0.9),   # 16 r_ankle (hook on Op torso)
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


# ── integration on real data ──────────────────────────────────────

from tools.contact_inference import PROXIMITY_THRESHOLD

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
