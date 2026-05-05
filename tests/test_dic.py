from dic.body_parts import BodyPart, COCO_TO_BLISP, DEFAULT_AXIS_ENDPOINTS, LimbRef, AxisDef
from dic.relations import CON, neg_helicity
from dic.radicals import ALL_RADICALS, Radical


def test_coco_map_covers_17_keypoints():
    assert len(COCO_TO_BLISP) == 17
    for i in range(17):
        assert i in COCO_TO_BLISP


def test_coco_wrist_maps_to_wr_not_ha():
    assert COCO_TO_BLISP[9][0] == "Wr"
    assert COCO_TO_BLISP[10][0] == "Wr"


def test_all_body_parts_in_enum():
    for code in ["Le", "Ar", "Fo", "Hp", "Ha", "Sh", "To", "Hd", "Kn", "El", "Sn", "Wr", "Ba", "Ne"]:
        assert code in BodyPart.__members__


def test_torso_is_to_not_tr():
    assert "To" in BodyPart.__members__
    assert "Tr" not in BodyPart.__members__


def test_default_axis_endpoints_defined():
    for part in ["Le", "Ar", "To"]:
        assert part in DEFAULT_AXIS_ENDPOINTS
        from_pt, to_pt = DEFAULT_AXIS_ENDPOINTS[part]
        assert from_pt != to_pt


def test_all_radicals_have_contacts():
    for name, rad in ALL_RADICALS.items():
        assert isinstance(rad, Radical)
        assert len(rad.contacts) > 0, f"{name} has no contacts"


def test_radical_contacts_are_con():
    for name, rad in ALL_RADICALS.items():
        for con in rad.contacts:
            assert isinstance(con, CON), f"{name} has non-CON contact: {con}"


def test_radical_contacts_use_valid_parts():
    valid_parts = {p.value for p in BodyPart}
    for name, rad in ALL_RADICALS.items():
        for con in rad.contacts:
            assert con.attacker.limb_ref.part in valid_parts, f"{name}: bad attacker part {con.attacker.limb_ref.part}"
            assert con.axis.limb_ref.part in valid_parts, f"{name}: bad axis part {con.axis.limb_ref.part}"


def test_radical_helicities_valid():
    for name, rad in ALL_RADICALS.items():
        for con in rad.contacts:
            assert con.helicity in ("+", "-", "0"), f"{name}: bad helicity {con.helicity}"
        for con in rad.forbidden_contacts:
            assert con.helicity in ("+", "-", "0"), f"{name}: bad forbidden helicity {con.helicity}"


def test_neg_helicity():
    assert neg_helicity("+") == "-"
    assert neg_helicity("-") == "+"
    assert neg_helicity("0") == "0"


def test_limb_ref_str():
    assert str(LimbRef("Me", "Le", "-")) == "Me.Le-"
    assert str(LimbRef("Op", "To")) == "Op.To"


def test_axis_def_str():
    ref = LimbRef("Op", "Le", "+")
    axis = AxisDef(ref, "Fo", "Hp")
    assert str(axis) == "Op.Le+_{Fo->Hp}"


def test_con_str():
    con = CON(
        AxisDef(LimbRef("Me", "Le", "-"), "Fo", "Hp"),
        AxisDef(LimbRef("Op", "Le", "+"), "Fo", "Hp"),
        "d", "-",
    )
    assert "CON(" in str(con)
    assert "Me.Le-" in str(con)
    assert "Op.Le+" in str(con)


def test_mnt_and_bctr_share_contacts():
    """MNT and BCTR have identical required CON tuples; they differ in
    frame constraints and forbidden contacts (BCTR forbids Fo-Fo closure)."""
    from dic.radicals import MNT, BCTR
    assert MNT.contacts == BCTR.contacts
    assert MNT.frame_constraints != BCTR.frame_constraints
    assert len(BCTR.forbidden_contacts) == 1
    assert len(MNT.forbidden_contacts) == 0


def test_dlr_slx_differ_only_in_helicity():
    """DLR and SLX have the same attacker and axis, opposite helicity."""
    from dic.radicals import DLR, SLX
    assert len(DLR.contacts) == 1
    assert len(SLX.contacts) == 1
    d = DLR.contacts[0]
    s = SLX.contacts[0]
    assert d.attacker == s.attacker
    assert d.axis == s.axis
    assert d.helicity != s.helicity


def test_omop_is_lsso_with_reversed_axis():
    """OMOP and LSSO share attacker/helicity; OMOP's axis is reversed."""
    from dic.radicals import LSSO, OMOP
    l = LSSO.contacts[0]
    o = OMOP.contacts[0]
    assert l.attacker == o.attacker
    assert l.helicity == o.helicity
    assert l.axis.limb_ref == o.axis.limb_ref
    assert l.axis.from_pt == o.axis.to_pt
    assert l.axis.to_pt == o.axis.from_pt


# ── SCTR structural tests ───────────────────────────────────────

def test_sctr_has_arm_to_torso_contact():
    """SCTR has one Me.Ar -> Op.To contact."""
    from dic.radicals import SCTR
    assert len(SCTR.contacts) == 1
    c = SCTR.contacts[0]
    assert c.attacker.limb_ref.role == "Me"
    assert c.attacker.limb_ref.part == "Ar"
    assert c.axis.limb_ref.role == "Op"
    assert c.axis.limb_ref.part == "To"


def test_sctr_requires_opponent_on_ground():
    """SCTR requires OnGround(Op.Ba)."""
    from dic.radicals import SCTR
    from dic.frames import OnGround
    ground = [f for f in SCTR.frame_constraints if isinstance(f, OnGround)]
    assert len(ground) == 1
    assert ground[0].part.role == "Op"
    assert ground[0].part.part == "Ba"


def test_sctr_no_facing_constraint():
    """SCTR does not require a specific facing direction."""
    from dic.radicals import SCTR
    from dic.frames import FacingAligned, FacingOpposed
    facing = [f for f in SCTR.frame_constraints
              if isinstance(f, (FacingAligned, FacingOpposed))]
    assert len(facing) == 0


def test_sctr_differs_from_mnt_by_limb():
    """MNT uses legs on torso, SCTR uses arms on torso."""
    from dic.radicals import MNT, SCTR
    for c in MNT.contacts:
        assert c.attacker.limb_ref.part == "Le"
    for c in SCTR.contacts:
        assert c.attacker.limb_ref.part == "Ar"


def test_sctr_v1_minimal():
    """Canonical SCTR has 1 CON + 1 FRM, no forbidden contacts."""
    from dic.radicals import SCTR
    assert len(SCTR.contacts) == 1
    assert len(SCTR.frame_constraints) == 1
    assert len(SCTR.forbidden_contacts) == 0
    assert len(SCTR.forbidden_bilateral) == 0


def test_sctr_strict_has_kbr_and_bilateral():
    """SCTR_STRICT adds NotKneeBracket + bilateral Le→To forbid."""
    from dic.radicals import SCTR_STRICT
    from dic.frames import NotKneeBracket
    kbr = [f for f in SCTR_STRICT.frame_constraints if isinstance(f, NotKneeBracket)]
    assert len(kbr) == 1
    assert len(SCTR_STRICT.forbidden_bilateral) == 2
    parts = {c.attacker.limb_ref.sign for c in SCTR_STRICT.forbidden_bilateral}
    assert parts == {"+", "-"}


def test_sctr_strict_not_in_all_radicals():
    """SCTR_STRICT is diagnostic only, not in the default radical dict."""
    from dic.radicals import ALL_RADICALS
    assert "SCTR_STRICT" not in ALL_RADICALS
    assert "SCTR" in ALL_RADICALS


# ── HGRD structural tests ───────────────────────────────────────

def test_hgrd_has_bilateral_le_to_le():
    """HGRD has two Me.Le → Op.Le contacts (both legs on same Op leg)."""
    from dic.radicals import HGRD
    assert len(HGRD.contacts) == 2
    for c in HGRD.contacts:
        assert c.attacker.limb_ref.role == "Me"
        assert c.attacker.limb_ref.part == "Le"
        assert c.axis.limb_ref.role == "Op"
        assert c.axis.limb_ref.part == "Le"


def test_hgrd_both_legs_target_same_op_leg():
    """Both inter-body contacts target the same Op.Le sign."""
    from dic.radicals import HGRD
    inter = [c for c in HGRD.contacts if c.axis.limb_ref.role == "Op"]
    ax_signs = {c.axis.limb_ref.sign for c in inter}
    assert len(ax_signs) == 1, f"Expected same Op.Le target, got signs: {ax_signs}"


def test_hgrd_uses_different_me_legs():
    """HGRD uses Me.Le+ and Me.Le- (both attacker legs)."""
    from dic.radicals import HGRD
    inter = [c for c in HGRD.contacts if c.axis.limb_ref.role == "Op"]
    att_signs = {c.attacker.limb_ref.sign for c in inter}
    assert att_signs == {"+", "-"}


def test_hgrd_no_closure():
    """HGRD does not require ankle closure (unlike CGRD)."""
    from dic.radicals import HGRD
    closure = [c for c in HGRD.contacts
               if c.attacker.limb_ref.role == "Me"
               and c.axis.limb_ref.role == "Me"]
    assert len(closure) == 0


def test_hgrd_requires_me_on_ground():
    """HGRD requires OnGround(Me.Ba) — bottom player."""
    from dic.radicals import HGRD
    from dic.frames import OnGround
    ground = [f for f in HGRD.frame_constraints if isinstance(f, OnGround)]
    assert len(ground) == 1
    assert ground[0].part.role == "Me"
    assert ground[0].part.part == "Ba"


def test_hgrd_requires_facing_opposed():
    """HGRD requires FacingOpposed."""
    from dic.radicals import HGRD
    from dic.frames import FacingOpposed
    facing = [f for f in HGRD.frame_constraints if isinstance(f, FacingOpposed)]
    assert len(facing) == 1


def test_hgrd_differs_from_cgrd_by_target():
    """HGRD targets Op.Le (leg entanglement), CGRD targets Op.To (torso wrap).
    CGRD has Fo-Fo closure, HGRD does not."""
    from dic.radicals import HGRD, CGRD
    for c in HGRD.contacts:
        assert c.axis.limb_ref.part == "Le"
    cgrd_inter = [c for c in CGRD.contacts if c.axis.limb_ref.role == "Op"]
    for c in cgrd_inter:
        assert c.axis.limb_ref.part == "To"
    cgrd_closure = [c for c in CGRD.contacts if c.axis.limb_ref.role == "Me"]
    assert len(cgrd_closure) == 1
    hgrd_closure = [c for c in HGRD.contacts if c.axis.limb_ref.role == "Me"]
    assert len(hgrd_closure) == 0


def test_hgrd_differs_from_dlr_by_count():
    """DLR has 1 contact, HGRD has 2 (bilateral leg entanglement)."""
    from dic.radicals import HGRD, DLR
    assert len(DLR.contacts) == 1
    assert len(HGRD.contacts) == 2


def test_hgrd_in_all_radicals():
    from dic.radicals import ALL_RADICALS
    assert "HGRD" in ALL_RADICALS
    assert "HGRD_L" in ALL_RADICALS


def test_hgrd_l_mirrors_hgrd():
    """HGRD_L targets Op.Le- (mirror of HGRD targeting Op.Le+)."""
    from dic.radicals import HGRD, HGRD_L
    assert len(HGRD_L.contacts) == len(HGRD.contacts)
    assert HGRD_L.frame_constraints == HGRD.frame_constraints
    for c in HGRD_L.contacts:
        assert c.axis.limb_ref.sign == "-"
    for c in HGRD.contacts:
        assert c.axis.limb_ref.sign == "+"


# ── 5050 radical tests ───────────────────────────────────────────

def test_5050_has_bilateral_cross_le():
    """5050 has two contacts: each Me leg hooks a DIFFERENT Op leg."""
    from dic.radicals import FIFTY_FIFTY
    assert len(FIFTY_FIFTY.contacts) == 2
    ax_signs = {c.axis.limb_ref.sign for c in FIFTY_FIFTY.contacts}
    atk_signs = {c.attacker.limb_ref.sign for c in FIFTY_FIFTY.contacts}
    assert atk_signs == {"+", "-"}, "Must use both Me legs"
    assert ax_signs == {"+", "-"}, "Must target different Op legs"


def test_5050_uses_le_to_le():
    """Both contacts are Le→Le (leg-to-leg)."""
    from dic.radicals import FIFTY_FIFTY
    for c in FIFTY_FIFTY.contacts:
        assert c.attacker.limb_ref.part == "Le"
        assert c.axis.limb_ref.part == "Le"


def test_5050_no_frame_constraints():
    """5050 has no frame constraints (bilateral cross is sufficient)."""
    from dic.radicals import FIFTY_FIFTY
    assert len(FIFTY_FIFTY.frame_constraints) == 0


def test_5050_forbids_bilateral_le_to_to():
    """5050 is blocked when both Me legs wrap Op's torso (BCTR/MNT signal)."""
    from dic.radicals import FIFTY_FIFTY
    assert len(FIFTY_FIFTY.forbidden_bilateral) == 2
    for fb in FIFTY_FIFTY.forbidden_bilateral:
        assert fb.attacker.limb_ref.part == "Le"
        assert fb.axis.limb_ref.part == "To"


def test_5050_differs_from_hgrd_by_target():
    """5050 targets different Op legs (cross); HGRD targets same Op leg."""
    from dic.radicals import FIFTY_FIFTY, HGRD
    hgrd_targets = {c.axis.limb_ref.sign for c in HGRD.contacts}
    fifty_targets = {c.axis.limb_ref.sign for c in FIFTY_FIFTY.contacts}
    assert len(hgrd_targets) == 1, "HGRD both contacts target same Op leg"
    assert len(fifty_targets) == 2, "5050 contacts target different Op legs"


def test_5050_in_all_radicals():
    from dic.radicals import ALL_RADICALS
    assert "5050" in ALL_RADICALS


# ── intra-body CON / cycle tests ─────────────────────────────────

def test_cgrd_has_intra_body_closure():
    """CGRD must include a Me→Me Fo-Fo CON with helicity 0."""
    from dic.radicals import CGRD
    closure = [c for c in CGRD.contacts
               if c.attacker.limb_ref.role == "Me"
               and c.axis.limb_ref.role == "Me"]
    assert len(closure) == 1
    c = closure[0]
    assert c.attacker.limb_ref.part == "Fo"
    assert c.axis.limb_ref.part == "Fo"
    assert c.helicity == "0"
    assert c.depth == "d3"


def test_bctr_forbids_closure():
    """BCTR must explicitly forbid the Fo-Fo closure CON."""
    from dic.radicals import BCTR
    assert len(BCTR.forbidden_contacts) == 1
    f = BCTR.forbidden_contacts[0]
    assert f.attacker.limb_ref.role == "Me"
    assert f.axis.limb_ref.role == "Me"
    assert f.attacker.limb_ref.part == "Fo"
    assert f.axis.limb_ref.part == "Fo"
    assert f.helicity == "0"


def test_opponent_self_connection_accepted():
    """CON must accept Op→Op pairs (structural test)."""
    op_ha = AxisDef(LimbRef("Op", "Ha", "+"), "Ha", "Wr")
    op_wr = AxisDef(LimbRef("Op", "Wr", "-"), "Wr", "El")
    con = CON(op_ha, op_wr, "d", "0")
    assert con.attacker.limb_ref.role == "Op"
    assert con.axis.limb_ref.role == "Op"
    assert con.helicity == "0"
    assert str(con).startswith("CON(")
