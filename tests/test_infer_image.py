"""Tests for tools/infer_image.py — image-to-algebra inference pipeline."""

import json
import pytest

from tools.infer_image import (
    PrecomputedBackend,
    select_athletes,
    assign_pov,
    infer_image,
    format_output,
    InferenceResult,
    _bbox_area,
    _mean_conf,
)


def _make_pose(x_offset=0, y_offset=0, conf=0.9):
    """Generate a synthetic COCO-17 keypoint array for one person."""
    base = [
        [150, 100],  # 0  nose
        [155, 95],   # 1  left_eye
        [145, 95],   # 2  right_eye
        [165, 100],  # 3  left_ear
        [135, 100],  # 4  right_ear
        [180, 160],  # 5  left_shoulder
        [120, 160],  # 6  right_shoulder
        [200, 220],  # 7  left_elbow
        [100, 220],  # 8  right_elbow
        [210, 280],  # 9  left_wrist
        [90, 280],   # 10 right_wrist
        [170, 300],  # 11 left_hip
        [130, 300],  # 12 right_hip
        [175, 400],  # 13 left_knee
        [125, 400],  # 14 right_knee
        [178, 500],  # 15 left_ankle
        [122, 500],  # 16 right_ankle
    ]
    return [[x + x_offset, y + y_offset, conf] for x, y in base]


def _make_two_athletes():
    """Two well-separated poses facing each other."""
    return [_make_pose(x_offset=0), _make_pose(x_offset=300)]


# ── athlete selection ───────────────────────────────────────────

class TestSelectAthletes:
    def test_exactly_two_athletes(self):
        a, b = _make_two_athletes()
        sel_a, sel_b = select_athletes([a, b])
        assert len(sel_a) == 17
        assert len(sel_b) == 17

    def test_fewer_than_two_raises(self):
        with pytest.raises(ValueError, match="Need two athletes"):
            select_athletes([_make_pose()])

    def test_zero_detections_raises(self):
        with pytest.raises(ValueError, match="Need two athletes"):
            select_athletes([])

    def test_three_selects_two_largest(self):
        big_a = _make_pose(x_offset=0, conf=0.95)
        big_b = _make_pose(x_offset=300, conf=0.95)
        small = [[x * 0.3, y * 0.3, 0.5] for x, y, _ in _make_pose(x_offset=600)]
        sel_a, sel_b = select_athletes([big_a, big_b, small])
        area_a = _bbox_area(sel_a)
        area_b = _bbox_area(sel_b)
        area_small = _bbox_area(small)
        assert area_a > area_small
        assert area_b > area_small

    def test_low_confidence_filtered(self):
        good_a = _make_pose(conf=0.9)
        good_b = _make_pose(x_offset=300, conf=0.9)
        ghost = _make_pose(x_offset=600, conf=0.05)
        sel_a, sel_b = select_athletes([good_a, good_b, ghost])
        assert len(sel_a) == 17
        assert len(sel_b) == 17


# ── bbox and confidence helpers ─────────────────────────────────

class TestHelpers:
    def test_bbox_area_positive(self):
        p = _make_pose()
        assert _bbox_area(p) > 0

    def test_bbox_area_low_conf(self):
        p = [[0, 0, 0.01] for _ in range(17)]
        assert _bbox_area(p) == 0.0

    def test_mean_conf(self):
        p = _make_pose(conf=0.8)
        assert abs(_mean_conf(p) - 0.8) < 0.01

    def test_mean_conf_empty(self):
        assert _mean_conf([]) == 0.0


# ── precomputed backend ─────────────────────────────────────────

class TestPrecomputedBackend:
    def test_dict_format(self, tmp_path):
        a, b = _make_two_athletes()
        p = tmp_path / "kp.json"
        p.write_text(json.dumps({"pose1": a, "pose2": b}))
        backend = PrecomputedBackend(str(p))
        persons = backend.detect("dummy.jpg")
        assert len(persons) == 2
        assert len(persons[0]) == 17
        assert len(persons[1]) == 17

    def test_list_of_persons_format(self, tmp_path):
        a, b = _make_two_athletes()
        p = tmp_path / "kp.json"
        p.write_text(json.dumps([a, b]))
        backend = PrecomputedBackend(str(p))
        persons = backend.detect("dummy.jpg")
        assert len(persons) == 2

    def test_single_person_list(self, tmp_path):
        a = _make_pose()
        p = tmp_path / "kp.json"
        p.write_text(json.dumps(a))
        backend = PrecomputedBackend(str(p))
        persons = backend.detect("dummy.jpg")
        assert len(persons) == 1
        assert len(persons[0]) == 17


# ── full inference pipeline ─────────────────────────────────────

class TestInference:
    def _run_with_precomputed(self, tmp_path, pov="both"):
        a, b = _make_two_athletes()
        kp_path = tmp_path / "kp.json"
        kp_path.write_text(json.dumps({"pose1": a, "pose2": b}))
        return infer_image(
            image_path="test_image.jpg",
            backend="precomputed",
            keypoints_json=str(kp_path),
            pov_strategy=pov,
        )

    def test_returns_inference_result(self, tmp_path):
        result = self._run_with_precomputed(tmp_path)
        assert isinstance(result, InferenceResult)

    def test_has_contacts(self, tmp_path):
        result = self._run_with_precomputed(tmp_path)
        assert isinstance(result.contacts, list)

    def test_has_frame_constraints(self, tmp_path):
        result = self._run_with_precomputed(tmp_path)
        assert isinstance(result.frame_constraints, list)

    def test_fpt_record_populated(self, tmp_path):
        result = self._run_with_precomputed(tmp_path)
        fpt = result.fpt_record
        assert fpt.image == "test_image"
        assert isinstance(fpt.contacts, list)
        assert isinstance(fpt.frame_constraints, list)

    def test_pov_label_assigned(self, tmp_path):
        result = self._run_with_precomputed(tmp_path)
        assert result.pov_label != ""

    def test_top_is_me_strategy(self, tmp_path):
        result = self._run_with_precomputed(tmp_path, pov="top_is_me")
        assert "top" in result.pov_label.lower()

    def test_left_is_me_strategy(self, tmp_path):
        result = self._run_with_precomputed(tmp_path, pov="left_is_me")
        assert "left" in result.pov_label.lower()


# ── output formats ──────────────────────────────────────────────

class TestOutputFormats:
    @pytest.fixture
    def result(self, tmp_path):
        a, b = _make_two_athletes()
        kp_path = tmp_path / "kp.json"
        kp_path.write_text(json.dumps({"pose1": a, "pose2": b}))
        return infer_image(
            image_path="test_image.jpg",
            backend="precomputed",
            keypoints_json=str(kp_path),
        )

    def test_summary_format(self, result):
        text = format_output(result, "summary")
        assert "RAD" in text
        assert "CONF" in text
        assert "POV" in text
        assert "CON:" in text
        assert "FRM:" in text

    def test_json_format(self, result):
        text = format_output(result, "json")
        data = json.loads(text)
        assert "image" in data
        assert "contacts" in data
        assert "frame_constraints" in data

    def test_sexpr_format(self, result):
        text = format_output(result, "sexpr")
        assert "FPT" in text

    def test_unknown_format_raises(self, result):
        with pytest.raises(ValueError, match="Unknown format"):
            format_output(result, "nonexistent")
