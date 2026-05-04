"""Tests for BLISP s-expression FPT export and CLI."""

import json
import subprocess
import sys
from pathlib import Path

import pytest
from tools.annotate import FPTRecord
from tools.blisp_export import fpt_to_sexpr, export_sexpr


def _sample_record():
    return FPTRecord(
        image="1400294", frame=294,
        vicos_label="back1", blisp_label="BCTR", ambiguity="medium",
        radical_match="BCTR", match_confidence=17.26,
        contacts=[
            {
                "attacker": "Me.Le+", "attacker_axis": "Fo->Hp",
                "axis": "Op.To", "axis_orient": "Hp->Sh",
                "depth": "d1", "helicity": "-",
                "confidence": 0.541, "distance": 0.058,
            },
            {
                "attacker": "Me.Le-", "attacker_axis": "Fo->Hp",
                "axis": "Op.To", "axis_orient": "Hp->Sh",
                "depth": "d2", "helicity": "+",
                "confidence": 0.509, "distance": 0.047,
            },
        ],
        frame_constraints=[
            {"type": "FacingAligned", "confidence": 0.985},
            {"type": "NotOnGround", "confidence": 0.5, "part": "Op.Ba"},
        ],
        all_matches=[
            {"radical": "BCTR", "confidence": 17.26},
            {"radical": "SLX", "confidence": 11.29},
        ],
    )


class TestSexprFormat:
    def test_contains_knd(self):
        s = fpt_to_sexpr(_sample_record())
        assert ":KND POS" in s

    def test_contains_nam(self):
        s = fpt_to_sexpr(_sample_record())
        assert ':NAM "video14_frame000294"' in s

    def test_contains_cmpn(self):
        s = fpt_to_sexpr(_sample_record())
        assert ":CMPN {" in s

    def test_contains_con_section(self):
        s = fpt_to_sexpr(_sample_record())
        assert "(CON Me.Le+ Op.To 0.541 -)" in s
        assert "(CON Me.Le- Op.To 0.509 +)" in s

    def test_contains_frm_section(self):
        s = fpt_to_sexpr(_sample_record())
        assert "(EQ y y')" in s
        assert "(NOT (Z0 Op.Ba))" in s

    def test_contains_rad(self):
        s = fpt_to_sexpr(_sample_record())
        assert "RAD BCTR" in s

    def test_contains_conf_section(self):
        s = fpt_to_sexpr(_sample_record())
        assert "(BCTR 17.26)" in s
        assert "(SLX 11.29)" in s

    def test_contains_axs_section(self):
        s = fpt_to_sexpr(_sample_record())
        assert "(AXS Me.Le+_{Fo->Hp})" in s
        assert "(AXS Op.To_{Hp->Sh})" in s

    def test_none_radical_outputs_none(self):
        r = _sample_record()
        r.radical_match = None
        s = fpt_to_sexpr(r)
        assert "RAD NONE" in s

    def test_empty_contacts_skips_sections(self):
        r = FPTRecord(
            image="0000001", frame=1,
            vicos_label="standing", blisp_label="STND", ambiguity="none",
            radical_match=None, match_confidence=0.0,
        )
        s = fpt_to_sexpr(r)
        assert ":KND POS" in s
        assert "CON (" not in s
        assert "AXS (" not in s

    def test_facing_opposed_format(self):
        r = _sample_record()
        r.frame_constraints = [{"type": "FacingOpposed", "confidence": 0.8}]
        s = fpt_to_sexpr(r)
        assert "(EQ y (NEG y'))" in s

    def test_on_ground_format(self):
        r = _sample_record()
        r.frame_constraints = [{"type": "OnGround", "confidence": 0.9, "part": "Op.Ba"}]
        s = fpt_to_sexpr(r)
        assert "(Z0 Op.Ba)" in s

    def test_closure_con_helicity_zero(self):
        r = _sample_record()
        r.contacts.append({
            "attacker": "Me.Fo-", "attacker_axis": "Fo->Kn",
            "axis": "Me.Fo+", "axis_orient": "Fo->Kn",
            "depth": "deep", "helicity": "0",
            "confidence": 0.25, "distance": 0.12,
        })
        s = fpt_to_sexpr(r)
        assert "(CON Me.Fo- Me.Fo+ 0.25 0)" in s

    def test_starts_with_fpt_paren(self):
        s = fpt_to_sexpr(_sample_record())
        assert s.startswith("(FPT")
        assert s.rstrip().endswith(")")


class TestSexprExport:
    def test_export_creates_file(self, tmp_path):
        out = tmp_path / "test.sexpr"
        export_sexpr([_sample_record()], out)
        assert out.exists()
        content = out.read_text()
        assert "(FPT" in content
        assert "RAD BCTR" in content

    def test_export_multiple_records(self, tmp_path):
        out = tmp_path / "multi.sexpr"
        r1 = _sample_record()
        r2 = _sample_record()
        r2.image = "0000060"
        r2.frame = 60
        r2.radical_match = "DLR"
        export_sexpr([r1, r2], out)
        content = out.read_text()
        assert content.count("(FPT") == 2
        assert "RAD BCTR" in content
        assert "RAD DLR" in content


class TestJsonRoundTrip:
    def test_json_export_load_preserves_radical(self, tmp_path):
        from tools.annotate import export_fpt, load_fpt
        out = tmp_path / "rt.json"
        r = _sample_record()
        export_fpt([r], out)
        loaded = load_fpt(out)
        assert len(loaded) == 1
        assert loaded[0].radical_match == "BCTR"
        assert loaded[0].match_confidence == 17.26
        assert len(loaded[0].contacts) == 2
        assert len(loaded[0].frame_constraints) == 2


class TestPersistedExportHasFinalRad:
    def test_persisted_records_use_post_temporal_rad(self):
        from tools.temporal import apply_persistence
        records = []
        for i in range(20):
            r = FPTRecord(
                image="14_test.jpg", frame=i,
                vicos_label="back1", blisp_label="BCTR", ambiguity="medium",
                radical_match="BCTR" if i != 5 else "MNT",
                match_confidence=15.0,
                all_matches=[{"radical": "BCTR" if i != 5 else "MNT", "confidence": 15.0}],
            )
            records.append(r)
        persisted = apply_persistence(records, min_frames=3)
        for r in persisted:
            s = fpt_to_sexpr(r)
            assert "RAD BCTR" in s, f"frame {r.frame} has wrong RAD in s-expression"


class TestCLISmoke:
    def _run(self, *args):
        result = subprocess.run(
            [sys.executable, "cli.py", *args],
            capture_output=True, text=True, timeout=10,
        )
        return result

    def test_dic(self):
        r = self._run("--dic")
        assert r.returncode == 0
        assert "BCTR" in r.stdout
        assert "CGRD" in r.stdout
        assert "MNT" in r.stdout

    def test_rad(self):
        r = self._run("--rad", "CGRD")
        assert r.returncode == 0
        assert "CGRD" in r.stdout
        assert "CON(" in r.stdout

    def test_rad_unknown(self):
        r = self._run("--rad", "ZZZZZ")
        assert r.returncode != 0

    def test_help(self):
        r = self._run("--help")
        assert r.returncode == 0
        assert "--dic" in r.stdout
        assert "--rad" in r.stdout
        assert "--eval" in r.stdout

    def test_match_not_found(self):
        result = subprocess.run(
            [sys.executable, "cli.py", "--match", "9999999"],
            capture_output=True, text=True, timeout=60,
        )
        assert result.returncode != 0
