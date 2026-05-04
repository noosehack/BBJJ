import pytest
from pathlib import Path
from data.loader import load_annotations, verify_images, DEFAULT_PATH
from data.schema import Annotation, Pose, Keypoint


ANNOTATIONS_EXIST = DEFAULT_PATH.exists()
skip_no_data = pytest.mark.skipif(not ANNOTATIONS_EXIST, reason="data/raw/annotations.json not present")


@skip_no_data
class TestLoader:
    @pytest.fixture(scope="class")
    def annotations(self):
        return load_annotations()

    def test_loads_without_error(self, annotations):
        assert annotations is not None

    def test_total_count(self, annotations):
        assert len(annotations) == 120_279

    def test_unique_images(self, annotations):
        unique = set(a.image for a in annotations)
        assert len(unique) == 120_279

    def test_all_entries_are_annotations(self, annotations):
        for a in annotations[:100]:
            assert isinstance(a, Annotation)

    def test_18_vicos_classes(self, annotations):
        classes = set(a.position for a in annotations)
        assert len(classes) == 18

    def test_expected_classes_present(self, annotations):
        classes = set(a.position for a in annotations)
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
        assert classes == expected

    def test_pose_has_17_keypoints(self, annotations):
        for a in annotations[:200]:
            if a.pose1:
                assert len(a.pose1.keypoints) == 17
            if a.pose2:
                assert len(a.pose2.keypoints) == 17

    def test_keypoint_values_are_numeric(self, annotations):
        a = annotations[0]
        pose = a.pose1 or a.pose2
        assert pose is not None
        kp = pose.keypoints[0]
        assert isinstance(kp.x, float)
        assert isinstance(kp.y, float)
        assert isinstance(kp.confidence, float)

    def test_image_ids_are_7_digit_strings(self, annotations):
        for a in annotations[:500]:
            assert len(a.image) == 7
            assert a.image.isdigit()

    def test_frames_are_positive(self, annotations):
        for a in annotations[:500]:
            assert a.frame > 0


@skip_no_data
class TestImageVerification:
    @pytest.fixture(scope="class")
    def annotations(self):
        return load_annotations()

    def test_all_images_found(self, annotations):
        found, missing, _ = verify_images(annotations)
        assert found == 120_279
        assert missing == 0
