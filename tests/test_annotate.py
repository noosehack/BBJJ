import pytest
import json
from pathlib import Path
from dataclasses import asdict

from data.schema import Annotation, Pose, Keypoint
from data.loader import DEFAULT_PATH
from data.label_map import normalize
from tools.annotate import (
    annotate_one, annotate_batch, export_fpt, load_fpt, FPTRecord,
    _serialize_con, _serialize_frame,
)
from tools.evaluate import evaluate, BLISP_TO_RADICALS


# ── synthetic helpers (reuse from test_contact) ──────────────────

def _make_pose(marker: float) -> Pose:
    return Pose([Keypoint(marker, marker, 1.0)] * 17)


def _mount_poses():
    me = Pose([
        Keypoint(200, 80,  0.9),
        Keypoint(202, 78,  0.9),
        Keypoint(198, 78,  0.9),
        Keypoint(205, 80,  0.9),
        Keypoint(195, 80,  0.9),
        Keypoint(180, 130, 0.9),
        Keypoint(220, 130, 0.9),
        Keypoint(170, 170, 0.9),
        Keypoint(230, 170, 0.9),
        Keypoint(165, 200, 0.9),
        Keypoint(235, 200, 0.9),
        Keypoint(185, 220, 0.9),
        Keypoint(215, 220, 0.9),
        Keypoint(170, 280, 0.9),
        Keypoint(230, 280, 0.9),
        Keypoint(190, 330, 0.9),
        Keypoint(210, 330, 0.9),
    ])
    op = Pose([
        Keypoint(200, 380, 0.9),
        Keypoint(202, 382, 0.9),
        Keypoint(198, 382, 0.9),
        Keypoint(205, 385, 0.9),
        Keypoint(195, 385, 0.9),
        Keypoint(175, 290, 0.9),
        Keypoint(225, 290, 0.9),
        Keypoint(160, 320, 0.9),
        Keypoint(240, 320, 0.9),
        Keypoint(155, 350, 0.9),
        Keypoint(245, 350, 0.9),
        Keypoint(185, 370, 0.9),
        Keypoint(215, 370, 0.9),
        Keypoint(180, 440, 0.9),
        Keypoint(220, 440, 0.9),
        Keypoint(180, 500, 0.9),
        Keypoint(220, 500, 0.9),
    ])
    return me, op


# ── FPTRecord tests ──────────────────────────────────────────────

class TestAnnotateOne:
    def test_mount_produces_fpt_record(self):
        me, op = _mount_poses()
        ann = Annotation("mount1", "0000001", 1, me, op)
        norm = normalize(ann)
        rec = annotate_one(norm)
        assert isinstance(rec, FPTRecord)
        assert rec.image == "0000001"
        assert rec.blisp_label == "MNT"
        assert rec.radical_match is not None
        assert rec.match_confidence > 0

    def test_mount_has_contacts(self):
        me, op = _mount_poses()
        ann = Annotation("mount1", "0000001", 1, me, op)
        rec = annotate_one(normalize(ann))
        assert len(rec.contacts) > 0

    def test_mount_has_frame_constraints(self):
        me, op = _mount_poses()
        ann = Annotation("mount1", "0000001", 1, me, op)
        rec = annotate_one(normalize(ann))
        assert len(rec.frame_constraints) > 0
        types = [f["type"] for f in rec.frame_constraints]
        assert "FacingOpposed" in types

    def test_missing_pose_returns_empty_record(self):
        ann = Annotation("mount2", "0000002", 1, _make_pose(1.0), None)
        rec = annotate_one(normalize(ann))
        assert rec.radical_match is None
        assert rec.match_confidence == 0.0
        assert rec.contacts == []

    def test_all_matches_sorted(self):
        me, op = _mount_poses()
        ann = Annotation("mount1", "0000001", 1, me, op)
        rec = annotate_one(normalize(ann))
        for i in range(len(rec.all_matches) - 1):
            assert rec.all_matches[i]["confidence"] >= rec.all_matches[i + 1]["confidence"]


class TestAnnotateBatch:
    def test_batch_produces_records(self):
        me, op = _mount_poses()
        anns = [
            Annotation("mount1", "0000001", 1, me, op),
            Annotation("mount2", "0000002", 1, op, me),
        ]
        records = annotate_batch(anns)
        assert len(records) == 2
        assert all(isinstance(r, FPTRecord) for r in records)


# ── serialization tests ──────────────────────────────────────────

class TestSerialization:
    def test_contact_serialization_keys(self):
        from tools.contact_inference import infer_contacts
        me, op = _mount_poses()
        contacts = infer_contacts(me, op)
        if contacts:
            d = _serialize_con(contacts[0])
            assert "attacker" in d
            assert "axis" in d
            assert "depth" in d
            assert "helicity" in d
            assert "confidence" in d
            assert "distance" in d

    def test_frame_serialization_keys(self):
        from tools.contact_inference import infer_frame_constraints
        me, op = _mount_poses()
        frames = infer_frame_constraints(me, op)
        if frames:
            d = _serialize_frame(frames[0])
            assert "type" in d
            assert "confidence" in d


# ── FPT export/import round-trip ─────────────────────────────────

class TestFPTRoundTrip:
    def test_export_creates_file(self, tmp_path):
        me, op = _mount_poses()
        ann = Annotation("mount1", "0000001", 1, me, op)
        rec = annotate_one(normalize(ann))
        out = tmp_path / "test.json"
        export_fpt([rec], out)
        assert out.exists()

    def test_round_trip_preserves_data(self, tmp_path):
        me, op = _mount_poses()
        anns = [
            Annotation("mount1", "0000001", 1, me, op),
            Annotation("back1", "0000003", 2, _make_pose(1.0), None),
        ]
        records = annotate_batch(anns)
        out = tmp_path / "rt.json"
        export_fpt(records, out)
        loaded = load_fpt(out)
        assert len(loaded) == len(records)
        for orig, back in zip(records, loaded):
            assert orig.image == back.image
            assert orig.blisp_label == back.blisp_label
            assert orig.radical_match == back.radical_match
            assert orig.match_confidence == back.match_confidence

    def test_export_is_valid_json(self, tmp_path):
        me, op = _mount_poses()
        ann = Annotation("mount1", "0000001", 1, me, op)
        rec = annotate_one(normalize(ann))
        out = tmp_path / "valid.json"
        export_fpt([rec], out)
        with open(out) as f:
            data = json.load(f)
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["blisp_label"] == "MNT"


# ── evaluation tests ─────────────────────────────────────────────

class TestEvaluation:
    def test_evaluate_returns_metrics(self):
        me, op = _mount_poses()
        anns = [Annotation("mount1", "0000001", 1, me, op)]
        records = annotate_batch(anns)
        result = evaluate(records)
        assert "total" in result
        assert "per_class" in result
        assert result["total"] == 1

    def test_evaluate_per_class_has_mnt(self):
        me, op = _mount_poses()
        anns = [Annotation("mount1", "0000001", 1, me, op)]
        records = annotate_batch(anns)
        result = evaluate(records)
        assert "MNT" in result["per_class"]
        cls = result["per_class"]["MNT"]
        assert cls["count"] == 1
        assert cls["has_match"] == 1

    def test_blisp_to_radicals_covers_all_labels(self):
        from data.label_map import VICOS_TO_BLISP
        all_blisp = set(v["blisp"] for v in VICOS_TO_BLISP.values())
        for label in all_blisp:
            assert label in BLISP_TO_RADICALS, f"{label} missing from BLISP_TO_RADICALS"

    def test_missing_pose_counted_but_not_matched(self):
        ann = Annotation("mount1", "0000010", 1, _make_pose(1.0), None)
        records = annotate_batch([ann])
        result = evaluate(records)
        cls = result["per_class"]["MNT"]
        assert cls["count"] == 1
        assert cls["has_match"] == 0


# ── integration on real data ─────────────────────────────────────

ANNOTATIONS_EXIST = DEFAULT_PATH.exists()
skip_no_data = pytest.mark.skipif(not ANNOTATIONS_EXIST, reason="data/raw not present")


@skip_no_data
class TestAnnotateRealData:
    @pytest.fixture(scope="class")
    def sample_records(self):
        from data.loader import load_annotations
        from collections import defaultdict
        all_anns = load_annotations()
        by_class = defaultdict(list)
        for a in all_anns:
            if a.pose1 and a.pose2:
                by_class[a.position].append(a)
        sample = []
        for cls, anns in by_class.items():
            sample.extend(anns[:5])
        return annotate_batch(sample)

    def test_all_produce_records(self, sample_records):
        assert len(sample_records) > 0
        assert all(isinstance(r, FPTRecord) for r in sample_records)

    def test_most_have_matches(self, sample_records):
        matched = sum(1 for r in sample_records if r.radical_match is not None)
        assert matched / len(sample_records) > 0.5

    def test_contacts_are_serializable(self, sample_records):
        for r in sample_records:
            json.dumps(asdict(r))

    def test_evaluate_runs(self, sample_records):
        result = evaluate(sample_records)
        assert result["total"] == len(sample_records)
        assert len(result["per_class"]) > 0
