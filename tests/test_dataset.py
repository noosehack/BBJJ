"""Tests for keypoint normalization and dataset construction."""

import math
import numpy as np
import pytest

from data.schema import Pose, Keypoint
from tools.build_dataset import (
    normalize_keypoints, extract_symbolic_features, DEFAULT_SPLITS,
    N_SYM_FEATURES, RADICAL_SCORE_SCALE,
)
from tools.annotate import FPTRecord
from tools.axis_reconstruction import L_SHOULDER, R_SHOULDER, L_HIP, R_HIP


def _make_pose(overrides: dict[int, tuple[float, float, float]] | None = None) -> Pose:
    """Build a COCO 17-keypoint pose with configurable positions."""
    defaults = {
        0:  (300, 200, 0.9),   # nose
        1:  (290, 195, 0.5),   # left_eye
        2:  (310, 195, 0.5),   # right_eye
        3:  (280, 200, 0.5),   # left_ear
        4:  (320, 200, 0.5),   # right_ear
        5:  (270, 260, 0.9),   # left_shoulder
        6:  (330, 260, 0.9),   # right_shoulder
        7:  (250, 310, 0.8),   # left_elbow
        8:  (350, 310, 0.8),   # right_elbow
        9:  (240, 360, 0.7),   # left_wrist
        10: (360, 360, 0.7),   # right_wrist
        11: (280, 370, 0.9),   # left_hip
        12: (320, 370, 0.9),   # right_hip
        13: (270, 440, 0.8),   # left_knee
        14: (330, 440, 0.8),   # right_knee
        15: (265, 510, 0.7),   # left_ankle
        16: (335, 510, 0.7),   # right_ankle
    }
    if overrides:
        defaults.update(overrides)
    kps = [Keypoint(x=v[0], y=v[1], confidence=v[2]) for v in [defaults[i] for i in range(17)]]
    return Pose(keypoints=kps)


# ── normalization tests ─────────────────────────────────────────

class TestNormalizeKeypoints:

    def test_output_shape(self):
        me = _make_pose()
        op = _make_pose()
        result = normalize_keypoints(me, op)
        assert result.shape == (34, 3)
        assert result.dtype == np.float32

    def test_me_torso_centered(self):
        """After normalization, Me's torso center should be near origin."""
        me = _make_pose()
        op = _make_pose()
        result = normalize_keypoints(me, op)
        me_kps = result[:17]
        torso_idxs = [L_SHOULDER, R_SHOULDER, L_HIP, R_HIP]
        cx = np.mean(me_kps[torso_idxs, 0])
        cy = np.mean(me_kps[torso_idxs, 1])
        assert abs(cx) < 0.01
        assert abs(cy) < 0.01

    def test_torso_vertical(self):
        """After normalization, Me's hip→shoulder should point along -y."""
        me = _make_pose()
        op = _make_pose()
        result = normalize_keypoints(me, op)
        me_kps = result[:17]
        hip_mid = np.mean(me_kps[[L_HIP, R_HIP], :2], axis=0)
        sh_mid = np.mean(me_kps[[L_SHOULDER, R_SHOULDER], :2], axis=0)
        direction = sh_mid - hip_mid
        length = np.linalg.norm(direction)
        assert length > 0.5
        unit = direction / length
        assert abs(unit[0]) < 0.05, f"x-component should be ~0, got {unit[0]}"
        assert unit[1] < -0.9, f"y-component should be ~-1, got {unit[1]}"

    def test_torso_unit_length(self):
        """After normalization, Me's torso length should be ~1.0."""
        me = _make_pose()
        op = _make_pose()
        result = normalize_keypoints(me, op)
        me_kps = result[:17]
        hip_mid = np.mean(me_kps[[L_HIP, R_HIP], :2], axis=0)
        sh_mid = np.mean(me_kps[[L_SHOULDER, R_SHOULDER], :2], axis=0)
        length = np.linalg.norm(sh_mid - hip_mid)
        assert abs(length - 1.0) < 0.05

    def test_confidence_preserved(self):
        """Confidence values pass through unchanged."""
        me = _make_pose()
        op = _make_pose()
        result = normalize_keypoints(me, op)
        for j in range(17):
            assert result[j, 2] == pytest.approx(me.keypoints[j].confidence, abs=1e-5)
            assert result[17 + j, 2] == pytest.approx(op.keypoints[j].confidence, abs=1e-5)

    def test_rotated_pose_still_normalizes(self):
        """A 45-degree tilted pose should still normalize to vertical."""
        angle = math.pi / 4
        cos_a, sin_a = math.cos(angle), math.sin(angle)

        def rotate(x, y, cx=300, cy=350):
            dx, dy = x - cx, y - cy
            return cx + cos_a * dx - sin_a * dy, cy + sin_a * dx + cos_a * dy

        overrides = {}
        base = _make_pose()
        for i, kp in enumerate(base.keypoints):
            rx, ry = rotate(kp.x, kp.y)
            overrides[i] = (rx, ry, kp.confidence)

        tilted = _make_pose(overrides)
        op = _make_pose()
        result = normalize_keypoints(tilted, op)
        me_kps = result[:17]
        hip_mid = np.mean(me_kps[[L_HIP, R_HIP], :2], axis=0)
        sh_mid = np.mean(me_kps[[L_SHOULDER, R_SHOULDER], :2], axis=0)
        direction = sh_mid - hip_mid
        unit = direction / np.linalg.norm(direction)
        assert abs(unit[0]) < 0.05
        assert unit[1] < -0.9

    def test_flat_returns_102_values(self):
        """Flattened output has 102 values (34 × 3)."""
        me = _make_pose()
        op = _make_pose()
        result = normalize_keypoints(me, op)
        flat = result.flatten()
        assert flat.shape == (102,)


# ── split coverage tests ────────────────────────────────────────

class TestSplits:

    def test_all_videos_assigned(self):
        """Every video ID 00-15 appears in exactly one split."""
        all_vids = set()
        for vids in DEFAULT_SPLITS.values():
            for v in vids:
                assert v not in all_vids, f"video {v} in multiple splits"
                all_vids.add(v)
        expected = {f"{i:02d}" for i in range(16)}
        assert all_vids == expected

    def test_no_empty_splits(self):
        for split, vids in DEFAULT_SPLITS.items():
            assert len(vids) > 0, f"{split} has no videos"

    def test_train_largest(self):
        assert len(DEFAULT_SPLITS["train"]) > len(DEFAULT_SPLITS["val"])
        assert len(DEFAULT_SPLITS["train"]) > len(DEFAULT_SPLITS["test"])


# ── symbolic feature tests ──────────────────────────────────────

CLASS_NAMES = ["BCTR", "CGRD", "DLR", "LSSO", "MNT", "OMOP", "RDLR", "SCTR", "SLX"]


def _make_fpt_record(**overrides) -> FPTRecord:
    defaults = dict(
        image="0600001", frame=1,
        vicos_label="mount1", blisp_label="MNT", ambiguity="low",
        radical_match="MNT", match_confidence=15.0,
        contacts=[
            {"attacker": "Me.Le+", "attacker_axis": "Fo->Hp",
             "axis": "Op.To", "axis_orient": "Hp->Sh",
             "depth": "deep", "helicity": "-",
             "confidence": 0.52, "distance": 0.04},
            {"attacker": "Me.Le-", "attacker_axis": "Fo->Hp",
             "axis": "Op.To", "axis_orient": "Hp->Sh",
             "depth": "mid", "helicity": "+",
             "confidence": 0.39, "distance": 0.11},
        ],
        frame_constraints=[
            {"type": "FacingOpposed", "confidence": 0.87},
            {"type": "OnGround", "confidence": 0.71, "part": "Op.Ba"},
            {"type": "NotOnGround", "confidence": 0.71, "part": "Me.Ba"},
        ],
        all_matches=[
            {"radical": "MNT", "confidence": 15.0},
            {"radical": "BCTR", "confidence": 12.5},
            {"radical": "SLX", "confidence": 9.1},
        ],
    )
    defaults.update(overrides)
    return FPTRecord(**defaults)


class TestSymbolicFeatures:

    def test_output_shape(self):
        r = _make_fpt_record()
        feat = extract_symbolic_features(r, CLASS_NAMES)
        assert feat.shape == (N_SYM_FEATURES,)
        assert feat.dtype == np.float32

    def test_radical_scores_populated(self):
        r = _make_fpt_record()
        feat = extract_symbolic_features(r, CLASS_NAMES)
        mnt_idx = CLASS_NAMES.index("MNT")
        bctr_idx = CLASS_NAMES.index("BCTR")
        assert feat[mnt_idx] == pytest.approx(15.0 / RADICAL_SCORE_SCALE, abs=1e-4)
        assert feat[bctr_idx] == pytest.approx(12.5 / RADICAL_SCORE_SCALE, abs=1e-4)
        omop_idx = CLASS_NAMES.index("OMOP")
        assert feat[omop_idx] == 0.0

    def test_frame_constraints_mapped(self):
        r = _make_fpt_record()
        feat = extract_symbolic_features(r, CLASS_NAMES)
        assert feat[9] == pytest.approx(0.87, abs=1e-3)   # FacingOpposed
        assert feat[10] == 0.0                              # FacingAligned
        assert feat[11] == pytest.approx(0.71, abs=1e-3)   # OnGround Op.Ba
        assert feat[14] == pytest.approx(0.71, abs=1e-3)   # NotOnGround Me.Ba

    def test_contact_summary(self):
        r = _make_fpt_record()
        feat = extract_symbolic_features(r, CLASS_NAMES)
        assert feat[17] == pytest.approx(2 / 8.0, abs=1e-4)    # n_contacts / 8
        assert feat[18] == pytest.approx(0.52, abs=1e-3)        # max confidence
        assert feat[19] == pytest.approx((0.52 + 0.39) / 2, abs=1e-3)  # mean

    def test_closure_flag_off(self):
        r = _make_fpt_record()
        feat = extract_symbolic_features(r, CLASS_NAMES)
        assert feat[20] == 0.0
        assert feat[21] == 0.0

    def test_closure_flag_on(self):
        contacts = [
            {"attacker": "Me.Fo-", "attacker_axis": "Fo->Kn",
             "axis": "Me.Fo+", "axis_orient": "Fo->Kn",
             "depth": "deep", "helicity": "0",
             "confidence": 0.8, "distance": 0.05},
        ]
        r = _make_fpt_record(contacts=contacts)
        feat = extract_symbolic_features(r, CLASS_NAMES)
        assert feat[20] == 1.0
        assert feat[21] == pytest.approx(0.8, abs=1e-3)

    def test_top_contacts_padded(self):
        """With only 2 contacts, slots 3-4 should be zero."""
        r = _make_fpt_record()
        feat = extract_symbolic_features(r, CLASS_NAMES)
        assert feat[22] == pytest.approx(0.52, abs=1e-3)  # contact 0 conf
        assert feat[23] == pytest.approx(0.04, abs=1e-3)  # contact 0 dist
        assert feat[24] == pytest.approx(0.39, abs=1e-3)  # contact 1 conf
        assert feat[25] == pytest.approx(0.11, abs=1e-3)  # contact 1 dist
        assert feat[26] == 0.0  # contact 2 (padding)
        assert feat[27] == 0.0

    def test_empty_record(self):
        """Record with no contacts/frames/matches should produce all zeros."""
        r = _make_fpt_record(contacts=[], frame_constraints=[], all_matches=[])
        feat = extract_symbolic_features(r, CLASS_NAMES)
        assert feat.sum() == 0.0
