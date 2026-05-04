import pytest
from dic.radicals import ALL_RADICALS, Radical
from dic.relations import CON
from ops.tuple_ops import (
    hel_flip, ax_rev, pov_swap_con,
    hel_flip_radical, pov_swap_radical,
)


# ── involution laws on individual CON tuples ──────────────────────

class TestHELFlipInvolution:
    @pytest.mark.parametrize("name", ALL_RADICALS.keys())
    def test_hel_flip_twice_is_identity(self, name):
        rad = ALL_RADICALS[name]
        for con in rad.contacts:
            assert hel_flip(hel_flip(con)) == con


class TestAXRevInvolution:
    @pytest.mark.parametrize("name", ALL_RADICALS.keys())
    def test_ax_rev_twice_is_identity(self, name):
        rad = ALL_RADICALS[name]
        for con in rad.contacts:
            assert ax_rev(ax_rev(con)) == con


class TestPOVSwapCONInvolution:
    @pytest.mark.parametrize("name", ALL_RADICALS.keys())
    def test_pov_swap_twice_is_identity(self, name):
        rad = ALL_RADICALS[name]
        for con in rad.contacts:
            result = pov_swap_con(pov_swap_con(con))
            assert result == con, (
                f"{name}: POV-SWAP^2 failed\n"
                f"  original:  {con}\n"
                f"  swapped:   {pov_swap_con(con)}\n"
                f"  swapped^2: {result}"
            )


# ── involution laws on full radicals ──────────────────────────────

class TestRadicalHELFlipInvolution:
    @pytest.mark.parametrize("name", ALL_RADICALS.keys())
    def test_hel_flip_radical_twice_is_identity(self, name):
        rad = ALL_RADICALS[name]
        assert hel_flip_radical(hel_flip_radical(rad)) == rad


class TestRadicalPOVSwapInvolution:
    @pytest.mark.parametrize("name", ALL_RADICALS.keys())
    def test_pov_swap_radical_twice_is_identity(self, name):
        rad = ALL_RADICALS[name]
        result = pov_swap_radical(pov_swap_radical(rad))
        assert result == rad, (
            f"{name}: radical POV-SWAP^2 failed\n"
            f"  original:  {rad}\n"
            f"  swapped:   {pov_swap_radical(rad)}\n"
            f"  swapped^2: {result}"
        )


# ── algebraic relationship tests ─────────────────────────────────

class TestAlgebraicRelationships:
    def test_dlr_hel_flip_gives_slx_structure(self):
        """HEL-FLIP on DLR's CON produces the same structure as SLX's CON."""
        from dic.radicals import DLR, SLX
        flipped = hel_flip(DLR.contacts[0])
        slx_con = SLX.contacts[0]
        assert flipped.attacker == slx_con.attacker
        assert flipped.axis == slx_con.axis
        assert flipped.helicity == slx_con.helicity

    def test_lsso_ax_rev_gives_omop_structure(self):
        """AX-REV on LSSO's CON produces the same structure as OMOP's CON."""
        from dic.radicals import LSSO, OMOP
        reversed_con = ax_rev(LSSO.contacts[0])
        omop_con = OMOP.contacts[0]
        assert reversed_con.attacker == omop_con.attacker
        assert reversed_con.axis == omop_con.axis
        assert reversed_con.helicity == omop_con.helicity

    def test_pov_swap_preserves_facing(self):
        """FacingOpposed stays FacingOpposed under POV-SWAP."""
        from dic.radicals import MNT
        swapped = pov_swap_radical(MNT)
        facing = [fc for fc in swapped.frame_constraints
                  if type(fc).__name__ == "FacingOpposed"]
        assert len(facing) == 1

    def test_pov_swap_flips_ground_role(self):
        """OnGround(Op.Ba) becomes OnGround(Me.Ba) under POV-SWAP."""
        from dic.radicals import MNT
        from dic.frames import OnGround
        swapped = pov_swap_radical(MNT)
        ground = [fc for fc in swapped.frame_constraints
                  if isinstance(fc, OnGround)]
        assert len(ground) == 1
        assert ground[0].part.role == "Me"
        assert ground[0].part.part == "Ba"
