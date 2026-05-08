import pytest
from pathlib import Path
from data.label_map import (
    VICOS_TO_BLISP, ALL_VICOS_CLASSES,
    blisp_label, ambiguity, normalize, _parse_suffix,
)
from data.loader import load_annotations, DEFAULT_PATH
from data.schema import Annotation, Pose, Keypoint


# ── unit tests (no data needed) ──────────────────────────────────

class TestMapping:
    def test_18_vicos_classes_in_map(self):
        assert len(VICOS_TO_BLISP) == 18

    def test_all_expected_classes(self):
        expected = {
            "standing", "takedown1", "takedown2",
            "open_guard1", "open_guard2",
            "closed_guard1", "closed_guard2",
            "half_guard1", "half_guard2",
            "5050_guard",
            "side_control1", "side_control2",
            "mount1", "mount2",
            "back1", "back2",
            "turtle1", "turtle2",
        }
        assert ALL_VICOS_CLASSES == expected

    def test_every_class_has_blisp_label(self):
        for cls in ALL_VICOS_CLASSES:
            assert isinstance(blisp_label(cls), str)
            assert len(blisp_label(cls)) > 0

    def test_every_class_has_ambiguity(self):
        valid = {"none", "low", "medium", "high"}
        for cls in ALL_VICOS_CLASSES:
            assert ambiguity(cls) in valid

    def test_unknown_class_raises(self):
        with pytest.raises(ValueError):
            blisp_label("nonexistent")

    def test_blisp_labels_are_expected(self):
        expected_labels = {"STND", "TKDN", "OGRD", "CGRD", "HGRD", "5050",
                           "SCTR", "MNT", "BCTR", "TRTL"}
        actual = {blisp_label(c) for c in ALL_VICOS_CLASSES}
        assert actual == expected_labels


class TestParseSuffix:
    def test_suffix_1(self):
        assert _parse_suffix("mount1") == "1"

    def test_suffix_2(self):
        assert _parse_suffix("mount2") == "2"

    def test_no_suffix(self):
        assert _parse_suffix("standing") is None
        assert _parse_suffix("5050_guard") is None


class TestPOVNormalization:
    def _make_pose(self, marker: float) -> Pose:
        return Pose([Keypoint(marker, marker, 1.0)] * 17)

    def test_suffix1_me_is_pose1(self):
        p1 = self._make_pose(1.0)
        p2 = self._make_pose(2.0)
        ann = Annotation("mount1", "0000001", 1, p1, p2)
        norm = normalize(ann)
        assert norm.me_pose is p1
        assert norm.op_pose is p2

    def test_suffix2_me_is_pose2(self):
        p1 = self._make_pose(1.0)
        p2 = self._make_pose(2.0)
        ann = Annotation("mount2", "0000001", 1, p1, p2)
        norm = normalize(ann)
        assert norm.me_pose is p2
        assert norm.op_pose is p1

    def test_no_suffix_defaults_pose1(self):
        p1 = self._make_pose(1.0)
        p2 = self._make_pose(2.0)
        ann = Annotation("standing", "0000001", 1, p1, p2)
        norm = normalize(ann)
        assert norm.me_pose is p1
        assert norm.op_pose is p2

    def test_5050_no_suffix_defaults_pose1(self):
        p1 = self._make_pose(1.0)
        p2 = self._make_pose(2.0)
        ann = Annotation("5050_guard", "0000001", 1, p1, p2)
        norm = normalize(ann)
        assert norm.me_pose is p1
        assert norm.op_pose is p2

    def test_missing_pose_handled(self):
        p1 = self._make_pose(1.0)
        ann = Annotation("mount2", "0000001", 1, p1, None)
        norm = normalize(ann)
        assert norm.me_pose is None
        assert norm.op_pose is p1

    def test_blisp_label_propagated(self):
        ann = Annotation("open_guard1", "0000001", 1, None, None)
        norm = normalize(ann)
        assert norm.blisp_label == "OGRD"
        assert norm.ambiguity == "high"


# ── integration tests (need data) ────────────────────────────────

ANNOTATIONS_EXIST = DEFAULT_PATH.exists()
skip_no_data = pytest.mark.skipif(not ANNOTATIONS_EXIST, reason="data/raw not present")


@skip_no_data
class TestNormalizationOnRealData:
    @pytest.fixture(scope="class")
    def annotations(self):
        return load_annotations()

    def test_all_annotations_normalize(self, annotations):
        for a in annotations:
            norm = normalize(a)
            assert norm.blisp_label is not None

    def test_no_unknown_classes(self, annotations):
        classes = set(a.position for a in annotations)
        assert classes == ALL_VICOS_CLASSES
