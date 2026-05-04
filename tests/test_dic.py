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
            assert con.helicity in ("+", "-"), f"{name}: bad helicity {con.helicity}"


def test_neg_helicity():
    assert neg_helicity("+") == "-"
    assert neg_helicity("-") == "+"


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
    """MNT and BCTR have identical CON tuples; only frame constraints differ."""
    from dic.radicals import MNT, BCTR
    assert MNT.contacts == BCTR.contacts
    assert MNT.frame_constraints != BCTR.frame_constraints


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
