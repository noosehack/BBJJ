"""Tests for sequence-aware temporal smoothing."""

import pytest
from copy import copy
from tools.annotate import FPTRecord
from tools.temporal import (
    group_by_sequence, smooth_scores, weighted_smooth,
    apply_persistence, flicker_rate,
)


def _rec(image: str, frame: int, radical: str | None, conf: float,
         all_matches: list[dict] | None = None,
         frame_constraints: list[dict] | None = None) -> FPTRecord:
    if all_matches is None and radical is not None:
        all_matches = [{"radical": radical, "confidence": conf}]
    return FPTRecord(
        image=image, frame=frame,
        vicos_label="test", blisp_label="TEST", ambiguity="none",
        radical_match=radical, match_confidence=conf,
        all_matches=all_matches or [],
        frame_constraints=frame_constraints or [],
    )


class TestGroupBySequence:
    def test_groups_by_image_prefix(self):
        records = [_rec("00_img1.jpg", 1, "DLR", 0.5),
                   _rec("00_img2.jpg", 2, "DLR", 0.6),
                   _rec("14_img1.jpg", 1, "BCTR", 0.7)]
        groups = group_by_sequence(records)
        assert set(groups.keys()) == {"00", "14"}
        assert len(groups["00"]) == 2
        assert len(groups["14"]) == 1

    def test_sorts_by_frame(self):
        records = [_rec("00_img3.jpg", 30, "DLR", 0.5),
                   _rec("00_img1.jpg", 10, "DLR", 0.6),
                   _rec("00_img2.jpg", 20, "DLR", 0.7)]
        groups = group_by_sequence(records)
        frames = [r.frame for r in groups["00"]]
        assert frames == [10, 20, 30]


class TestSmoothScores:
    def test_passthrough_no_matches(self):
        records = [_rec("00_a.jpg", i, None, 0.0) for i in range(5)]
        result = smooth_scores(records, k=2)
        assert len(result) == 5
        for r in result:
            assert r.radical_match is None

    def test_constant_scores_unchanged(self):
        matches = [{"radical": "DLR", "confidence": 0.8},
                   {"radical": "SLX", "confidence": 0.2}]
        records = [_rec("00_a.jpg", i, "DLR", 0.8, list(matches)) for i in range(10)]
        result = smooth_scores(records, k=3)
        for r in result:
            assert r.radical_match == "DLR"
            assert r.match_confidence == pytest.approx(0.8, abs=0.01)

    def test_smoothing_averages_window(self):
        records = []
        for i in range(7):
            if i == 3:
                records.append(_rec("00_a.jpg", i, "SLX", 1.0,
                                    [{"radical": "SLX", "confidence": 1.0},
                                     {"radical": "DLR", "confidence": 0.0}]))
            else:
                records.append(_rec("00_a.jpg", i, "DLR", 1.0,
                                    [{"radical": "DLR", "confidence": 1.0},
                                     {"radical": "SLX", "confidence": 0.0}]))
        result = smooth_scores(records, k=3)
        # Frame 3 spike should be averaged out: 6 DLR neighbors + 1 SLX
        assert result[3].radical_match == "DLR"

    def test_preserves_record_count(self):
        records = [_rec("00_a.jpg", i, "DLR", 0.5,
                        [{"radical": "DLR", "confidence": 0.5}]) for i in range(20)]
        records += [_rec("14_a.jpg", i, "BCTR", 0.6,
                         [{"radical": "BCTR", "confidence": 0.6}]) for i in range(10)]
        result = smooth_scores(records, k=3)
        assert len(result) == 30

    def test_different_sequences_independent(self):
        r1 = [_rec("00_a.jpg", i, "DLR", 1.0,
                    [{"radical": "DLR", "confidence": 1.0}]) for i in range(5)]
        r2 = [_rec("14_a.jpg", i, "BCTR", 1.0,
                    [{"radical": "BCTR", "confidence": 1.0}]) for i in range(5)]
        result = smooth_scores(r1 + r2, k=3)
        vid00 = [r for r in result if r.image.startswith("00")]
        vid14 = [r for r in result if r.image.startswith("14")]
        for r in vid00:
            assert r.radical_match == "DLR"
        for r in vid14:
            assert r.radical_match == "BCTR"


class TestApplyPersistence:
    def test_stable_label_passes_through(self):
        records = [_rec("00_a.jpg", i, "DLR", 0.8) for i in range(10)]
        result = apply_persistence(records, min_frames=3)
        assert all(r.radical_match == "DLR" for r in result)

    def test_brief_switch_suppressed(self):
        records = [_rec("00_a.jpg", i, "DLR", 0.8) for i in range(5)]
        records += [_rec("00_a.jpg", i, "BCTR", 0.9) for i in range(5, 7)]
        records += [_rec("00_a.jpg", i, "DLR", 0.8) for i in range(7, 12)]
        result = apply_persistence(records, min_frames=3)
        labels = [r.radical_match for r in result]
        assert all(l == "DLR" for l in labels)

    def test_sustained_switch_accepted(self):
        records = [_rec("00_a.jpg", i, "DLR", 0.8) for i in range(5)]
        records += [_rec("00_a.jpg", i, "BCTR", 0.9) for i in range(5, 10)]
        result = apply_persistence(records, min_frames=3)
        labels = [r.radical_match for r in result]
        # First 5 are DLR, then transition: frames 5,6 suppressed (DLR), frame 7+ is BCTR
        assert labels[:5] == ["DLR"] * 5
        assert labels[-1] == "BCTR"

    def test_none_initial_label(self):
        records = [_rec("00_a.jpg", i, None, 0.0) for i in range(3)]
        records += [_rec("00_a.jpg", i, "DLR", 0.8) for i in range(3, 8)]
        result = apply_persistence(records, min_frames=3)
        assert result[0].radical_match is None

    def test_none_gaps_inherit_stable(self):
        """None frames after a stable label should inherit that label."""
        records = [_rec("00_a.jpg", i, "DLR", 0.8) for i in range(5)]
        records += [_rec("00_a.jpg", i, None, 0.0) for i in range(5, 10)]
        records += [_rec("00_a.jpg", i, "DLR", 0.8) for i in range(10, 15)]
        result = apply_persistence(records, min_frames=3)
        labels = [r.radical_match for r in result]
        assert all(l == "DLR" for l in labels)

    def test_none_gaps_dont_reset_pending(self):
        """None frames between pending label frames shouldn't break the count."""
        records = [_rec("00_a.jpg", i, "DLR", 0.8) for i in range(5)]
        # 2 BCTR, then None gap, then more BCTR — the pending count continues
        records += [_rec("00_a.jpg", 5, "BCTR", 0.9)]
        records += [_rec("00_a.jpg", 6, "BCTR", 0.9)]
        records += [_rec("00_a.jpg", 7, None, 0.0)]
        records += [_rec("00_a.jpg", 8, "BCTR", 0.9)]
        records += [_rec("00_a.jpg", i, "BCTR", 0.9) for i in range(9, 14)]
        result = apply_persistence(records, min_frames=3)
        # None gap doesn't reset pending, so BCTR should eventually become stable
        assert result[-1].radical_match == "BCTR"

    def test_preserves_record_count(self):
        records = [_rec("00_a.jpg", i, "DLR", 0.8) for i in range(5)]
        records += [_rec("14_a.jpg", i, "BCTR", 0.9) for i in range(5)]
        result = apply_persistence(records, min_frames=3)
        assert len(result) == 10

    def test_sequences_independent(self):
        r1 = [_rec("00_a.jpg", i, "DLR", 0.8) for i in range(5)]
        r2 = [_rec("14_a.jpg", i, "BCTR", 0.9) for i in range(5)]
        result = apply_persistence(r1 + r2, min_frames=3)
        vid00 = [r for r in result if r.image.startswith("00")]
        vid14 = [r for r in result if r.image.startswith("14")]
        assert all(r.radical_match == "DLR" for r in vid00)
        assert all(r.radical_match == "BCTR" for r in vid14)


def _wrec(image, frame, radical, score, frame_conf,
          all_matches=None):
    """Helper building records with frame constraints for weighted tests."""
    if all_matches is None and radical is not None:
        all_matches = [{"radical": radical, "confidence": score}]
    fc = [{"type": "NotOnGround", "confidence": frame_conf, "part": "Op.Ba"}]
    return _rec(image, frame, radical, score,
                all_matches=all_matches or [],
                frame_constraints=fc)


class TestWeightedSmooth:
    def test_high_conf_frame_dominates(self):
        """A high-confidence frame should outweigh many low-confidence ones."""
        records = []
        for i in range(7):
            if i == 3:
                records.append(_wrec("00_a.jpg", i, "CGRD", 30.0, 0.9,
                                     [{"radical": "CGRD", "confidence": 30.0},
                                      {"radical": "BCTR", "confidence": 15.0}]))
            else:
                records.append(_wrec("00_a.jpg", i, "BCTR", 15.0, 0.3,
                                     [{"radical": "BCTR", "confidence": 15.0},
                                      {"radical": "CGRD", "confidence": 10.0}]))
        result = weighted_smooth(records, k=1)
        # Frame 3: CGRD=30*0.9=27, BCTR=15*0.9=13.5 from self
        #   + neighbors at low conf: BCTR=15*0.3=4.5, CGRD=10*0.3=3.0 each
        # CGRD total = 27 + 3.0 + 3.0 = 33, BCTR total = 13.5 + 4.5 + 4.5 = 22.5
        assert result[3].radical_match == "CGRD"

    def test_none_bridging(self):
        """None frames should get labels from neighbors."""
        records = [_wrec("00_a.jpg", i, "DLR", 10.0, 0.8) for i in range(3)]
        records += [_rec("00_a.jpg", i, None, 0.0) for i in range(3, 6)]
        records += [_wrec("00_a.jpg", i, "DLR", 10.0, 0.8) for i in range(6, 9)]
        result = weighted_smooth(records, k=3)
        for r in result:
            assert r.radical_match == "DLR"

    def test_sums_not_averages(self):
        """Weighted smooth sums scores, so more evidence = higher total."""
        records = [_wrec("00_a.jpg", i, "DLR", 10.0, 0.8,
                         [{"radical": "DLR", "confidence": 10.0}]) for i in range(5)]
        result = weighted_smooth(records, k=2)
        # Middle frame sees 5 neighbors: 5 * 10.0 * 0.8 = 40.0
        assert result[2].match_confidence == pytest.approx(40.0, abs=0.1)

    def test_preserves_record_count(self):
        records = [_wrec("00_a.jpg", i, "DLR", 10.0, 0.8) for i in range(10)]
        records += [_wrec("14_a.jpg", i, "BCTR", 10.0, 0.9) for i in range(5)]
        result = weighted_smooth(records, k=3)
        assert len(result) == 15

    def test_sequences_independent(self):
        r1 = [_wrec("00_a.jpg", i, "DLR", 10.0, 0.8,
                     [{"radical": "DLR", "confidence": 10.0}]) for i in range(5)]
        r2 = [_wrec("14_a.jpg", i, "BCTR", 10.0, 0.9,
                     [{"radical": "BCTR", "confidence": 10.0}]) for i in range(5)]
        result = weighted_smooth(r1 + r2, k=3)
        vid00 = [r for r in result if r.image.startswith("00")]
        vid14 = [r for r in result if r.image.startswith("14")]
        for r in vid00:
            assert r.radical_match == "DLR"
        for r in vid14:
            assert r.radical_match == "BCTR"

    def test_spike_suppressed_by_window(self):
        """A single-frame spike in a stable run should be outvoted."""
        records = []
        for i in range(9):
            if i == 4:
                records.append(_wrec("00_a.jpg", i, "SLX", 12.0, 0.8,
                                     [{"radical": "SLX", "confidence": 12.0},
                                      {"radical": "DLR", "confidence": 8.0}]))
            else:
                records.append(_wrec("00_a.jpg", i, "DLR", 11.0, 0.8,
                                     [{"radical": "DLR", "confidence": 11.0},
                                      {"radical": "SLX", "confidence": 5.0}]))
        result = weighted_smooth(records, k=3)
        assert result[4].radical_match == "DLR"


class TestFlickerRate:
    def test_no_flicker(self):
        records = [_rec("00_a.jpg", i, "DLR", 0.8) for i in range(10)]
        rates = flicker_rate(records)
        assert rates["overall"] == 0.0

    def test_constant_flicker(self):
        records = []
        for i in range(10):
            lab = "DLR" if i % 2 == 0 else "BCTR"
            records.append(_rec("00_a.jpg", i, lab, 0.8))
        rates = flicker_rate(records)
        assert rates["00"] == pytest.approx(0.9, abs=0.01)

    def test_single_switch(self):
        records = [_rec("00_a.jpg", i, "DLR", 0.8) for i in range(5)]
        records += [_rec("00_a.jpg", i, "BCTR", 0.8) for i in range(5, 10)]
        rates = flicker_rate(records)
        assert rates["00"] == pytest.approx(1 / 10, abs=0.01)

    def test_multi_video(self):
        r1 = [_rec("00_a.jpg", i, "DLR", 0.8) for i in range(10)]
        r2 = []
        for i in range(10):
            lab = "DLR" if i % 2 == 0 else "BCTR"
            r2.append(_rec("14_a.jpg", i, lab, 0.8))
        rates = flicker_rate(r1 + r2)
        assert rates["00"] == 0.0
        assert rates["14"] > 0.5
