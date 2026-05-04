# BJJ-BLISP: Image-to-Notation Position Recognition

## Context

Standalone BJJ notation/data project in `/home/ubuntu/BBJJ/` that outputs BLISP-compatible tuples and FPT records. Does NOT modify `/home/ubuntu/blisp`.

**Data source**: ViCoS BJJ dataset (120K images, 18 coarse classes, COCO 17-keypoint annotations). Current local state: 255 images (truncated zip), truncated annotations.json (4118 entries, 3 of 18 classes).

**Primitive design principle**: CON is the only primitive relation. Everything else is derived.

---

## Project Structure

```
BBJJ/
  dic/                    # dictionaries and type definitions
    __init__.py
    body_parts.py         # body part codes, COCO map, virtual axes
    relations.py          # CON primitive only
    frames.py             # frame constraints (y=-y', Z0, etc.)
    radicals.py           # explicit canonical radicals
    strokes.py            # allowed strokes per position (later)
  ops/                    # algebraic operations
    __init__.py
    tuple_ops.py          # HEL-FLIP, AX-SUB, AX-REV, POV-SWAP
    canon_ops.py          # CANON, RAD-OF, STK-OF (later)
    match_ops.py          # MATCH-RAD (later)
  data/                   # data loading and schemas
    __init__.py
    raw/                  # ViCoS dataset files -- NOT committed
      images/             # (255 images currently)
      annotations.json    # (truncated currently)
      images.zip
    schema.py             # data models for annotations, poses, FPT
    loader.py             # ViCoS annotation parser
    label_map.py          # ViCoS 18-class -> BLISP mapping (later)
    pov.py                # POV normalization (later)
  tools/                  # inference, annotation, training (later phases)
  tests/                  # pytest tests
    __init__.py
    test_dic.py           # dictionary validation
    test_ops.py           # involution laws
    test_schema.py        # round-trip serialization
  spec/                   # reference documents
  blisp/
    export/               # BLISP-compatible output (FPT records, tuples)
```

Move existing raw data:
- `BBJJ/images/` -> `BBJJ/data/raw/images/`
- `BBJJ/annotations.json` -> `BBJJ/data/raw/annotations.json`
- `BBJJ/images.zip` -> `BBJJ/data/raw/images.zip`
- `BBJJ/BJJ_BLISP_Notation_Framework_with_ISO_Dictionary.docx` -> `BBJJ/spec/`

Add `data/raw/` to `.gitignore`.

---

## Phase 0: Foundation -- Dictionary & Data Layer

### dic/body_parts.py

Body part enum with all codes from the spec:
- Le, Ar, Fo, Hp, Ha, Sh, To, Hd, Kn, El, Sn, Wr, Ba, Ne, Bk, LePair

COCO-to-BLISP keypoint mapping (17 keypoints):
```
COCO[0]     nose        -> Hd
COCO[1]     left_eye    -> Hd  (collapsed)
COCO[2]     right_eye   -> Hd  (collapsed)
COCO[3]     left_ear    -> Hd  (collapsed)
COCO[4]     right_ear   -> Hd  (collapsed)
COCO[5]     left_shoulder  -> Sh-
COCO[6]     right_shoulder -> Sh+
COCO[7]     left_elbow     -> El-
COCO[8]     right_elbow    -> El+
COCO[9]     left_wrist     -> Wr-   (NOT Ha)
COCO[10]    right_wrist    -> Wr+   (NOT Ha)
COCO[11]    left_hip       -> Hp-
COCO[12]    right_hip      -> Hp+
COCO[13]    left_knee      -> Kn-
COCO[14]    right_knee     -> Kn+
COCO[15]    left_ankle     -> Fo-
COCO[16]    right_ankle    -> Fo+
```

Virtual/inferred parts (not directly from COCO):
- Ha: hand, inferred as Wr + short distal extension
- Sn: shin, interpolated between Kn and Fo
- To: torso, centroid + orientation of {Sh-, Sh+, Hp-, Hp+}
- Ba: back surface, posterior of To frame
- Ne: neck, between Hd and Sh midpoint

Axis definitions as `LimbRef` and `AxisDef` types:
- `Le-` = Fo- -> Kn- -> Hp- (left leg, distal to proximal)
- `Le+` = Fo+ -> Kn+ -> Hp+ (right leg)
- `Ar-` = Wr- -> El- -> Sh- (left arm)
- `Ar+` = Wr+ -> El+ -> Sh+ (right arm)
- `To`  = {Hp-, Hp+, Sh-, Sh+} frame, Hp->Sh orientation

`LimbRef` dataclass: `(role: "Me"|"Op", part: str, sign: "+"|"-")`
`AxisDef` dataclass: `(limb_ref: LimbRef, from_point: str, to_point: str)`

### dic/relations.py

Single primitive -- frozen dataclass:
```python
@dataclass(frozen=True)
class CON:
    attacker: LimbRef          # e.g. Me.Le-
    axis: AxisDef              # e.g. Op.Le+_{Fo->Hp}
    depth: str                 # symbolic depth label (d, d1, d2, etc.)
    helicity: str              # "+" or "-"
```

No other relation types as dataclasses. GRP, HOOK, CLP are future macros/views only.

### dic/frames.py

Frame constraint predicates -- frozen dataclasses:
```python
@dataclass(frozen=True)
class FacingOpposed:       # y = -y'
    """Me faces Op, Op faces Me"""

@dataclass(frozen=True)
class FacingAligned:       # y = y'
    """Same facing direction (e.g. back control)"""

@dataclass(frozen=True)
class OnGround:            # Z0(X)
    part: LimbRef           # body part that is grounded

@dataclass(frozen=True)
class NotOnGround:         # ¬Z0(X)
    part: LimbRef           # body part that is elevated
```

### dic/radicals.py

Each radical is a `Radical` dataclass containing:
- `name`: position code string
- `frame_constraints`: list of frame predicates
- `contacts`: list of CON tuples

All radicals are explicit literals. No auto-generation.

```
MNT = Radical("MNT", 
  frames=[FacingOpposed(), OnGround(Op.Ba)],
  contacts=[
    CON(Me.Le+, Op.To_{Hp->Sh}, "d1", "-"),
    CON(Me.Le-, Op.To_{Hp->Sh}, "d2", "+"),
  ])

BCTR = Radical("BCTR",
  frames=[FacingAligned(), NotOnGround(Op.Ba)],
  contacts=[
    CON(Me.Le+, Op.To_{Hp->Sh}, "d1", "-"),
    CON(Me.Le-, Op.To_{Hp->Sh}, "d2", "+"),
  ])

DLR = Radical("DLR",
  contacts=[CON(Me.Le-, Op.Le+_{Fo->Hp}, "d", "-")])

SLX = Radical("SLX",
  contacts=[CON(Me.Le-, Op.Le+_{Fo->Hp}, "d", "+")])

RDLR = Radical("RDLR",
  contacts=[CON(Me.Le-, Op.Le-_{Fo->Hp}, "d", "-")])

LSSO = Radical("LSSO",
  contacts=[CON(Me.Le-, Op.Ar+_{Wr->Sh}, "d", "+")])

OMOP = Radical("OMOP",
  contacts=[CON(Me.Le-, REV(Op.Ar+_{Wr->Sh}), "d", "+")])
```

Remaining radicals (SCTR, GRD, HGRD, 5050, TRI, KMR, BFLY, KGRD) -- stubbed with TODO, to be filled in as explicit canonical forms.

### data/loader.py

- Parse truncated annotations.json using regex recovery (already tested)
- Schema: `{position: str, image: str, frame: int, pose1: [[x,y,c]*17], pose2: [[x,y,c]*17]}`
- Preserve pose1/pose2 identity (do not swap at load time)
- Return list of typed annotation objects

---

## Phase 1: Algebraic Operations

### ops/tuple_ops.py

Four operations on CON tuples:

**HEL-FLIP**: Flip helicity, preserve everything else.
```
HEL-FLIP(CON(a, b, d, h)) -> CON(a, b, d, NEG(h))
```

**AX-SUB**: Substitute the target axis with a new one.
```
AX-SUB(CON(a, b, d, h), c) -> CON(a, c, d, h)
```

**AX-REV**: Reverse the axis orientation (swap from/to endpoints).
```
AX-REV(CON(a, AXS(x, p, q), d, h)) -> CON(a, AXS(x, q, p), d, h)
```

**POV-SWAP**: Swap attacker/axis and flip helicity, then rename Me<->Op.
```
POV-SWAP(CON(a, b, d, h)) -> CON(b, a, d, NEG(h))  [then Me<->Op rename]
```

For radicals with multiple CON tuples (MNT, BCTR): apply the operation to each CON in the radical. Frame constraints also transform under POV-SWAP (FacingOpposed stays FacingOpposed; OnGround(Op.Ba) becomes OnGround(Me.Ba) after role swap).

### tests/test_ops.py

Involution law tests over ALL defined radicals (MNT, BCTR, DLR, SLX, RDLR, LSSO, OMOP):

```python
def test_hel_flip_involution():
    for rad in ALL_RADICALS:
        assert hel_flip(hel_flip(rad)) == rad

def test_pov_swap_involution():
    for rad in ALL_RADICALS:
        assert pov_swap(pov_swap(rad)) == rad

def test_ax_rev_involution():
    for rad in ALL_RADICALS:
        for con in rad.contacts:
            assert ax_rev(ax_rev(con)) == con
```

Additional algebraic tests:
- DLR under HEL-FLIP produces SLX-like structure (same axis, opposite helicity)
- LSSO under AX-REV produces OMOP-like structure
- MNT under POV-SWAP: Me/Op swap, frame constraints transform correctly

---

## Phase 6: Temporal Smoothing

Default pipeline: `raw frame predictions → persist N=8 → labels`

Persistence filter (N=8) with None-bridging is the canonical temporal method.
None frames inherit the last stable label (no-observation, not no-position).

Results on target videos (00-02: GRD_CLP, 14-15: BCTR):

| Metric | Baseline | Persist N=8 |
|---|---|---|
| BCTR | 21.2% | 60.0% |
| GRD_CLP | 27.5% | 54.6% |
| GRD | 59.6% | 84.5% |
| Compatible | 37.0% | 67.3% |
| Flicker | 0.2114 | 0.0100 |

### Weighted smoothing (experimental, `--wsmooth K`)

Weighted smoothing is inappropriate for CGRD/BCTR because lower-specificity
radicals appear in more frames and dominate accumulated scores. Persistence-only
better preserves high-specificity radicals across intermittent missing CONs.

Useful for broad GRD-family stability (GRD 84.5% → 91.8% with wsmooth k=8 +
persist N=8) but regresses CGRD/BCTR discrimination (GRD_CLP 54.6% → 43.2%).
Not part of the default evaluation pipeline.

---

## Phases 2-7 (unchanged from previous plan)

Deferred until Phase 0+1 pass all tests. See previous plan for details on:
- Phase 2: Dataset label mapping (ViCoS -> BLISP)
- Phase 3: Keypoint-to-contact inference engine
- Phase 4: Annotation tooling
- Phase 5: Training pipeline
- Phase 6: Algebraic law validation
- Phase 7: CLI interface

---

## Verification (Phase 0+1)

1. `pytest tests/test_dic.py` -- every body part code resolves, every radical parses, COCO map covers all 17 keypoints
2. `pytest tests/test_ops.py` -- all three involution laws pass on all 7 radicals
3. Manual check: print each radical and its POV-SWAPped form, verify they make BJJ sense
