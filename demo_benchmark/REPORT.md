# Benchmark Report

**Date**: 2026-05-07
**Deployed config**: ft-v2 posehead + NMS IoU=0.8
**Classifier**: MLP on 203 body-frame features (learned_geometry)

## Full 8-class benchmark (80 images, 10/class)

| Mode | Accuracy |
|------|----------|
| Ground-truth keypoints | **94.1%** (48/51 with available GT) |
| YOLO pipeline | **63.7%** overall, **67.1%** when detected (4 detection failures) |

### Per-class (YOLO pipeline)

| Class | Accuracy | Detection failures | Top confusion |
|-------|----------|--------------------|---------------|
| STND  | 100% | 0 | -- |
| OGRD  | 90%  | 0 | SCTR(1) |
| TRTL  | 80%  | 0 | HGRD(1), OGRD(1) |
| HGRD  | 60%  | 1 | SCTR(2), MNT(1) |
| BCTR  | 50%  | 2 | TKDN(2), HGRD(1) |
| SCTR  | 50%  | 0 | HGRD(4), CGRD(1) |
| CGRD  | 40%  | 1 | HGRD(3), OGRD(2) |
| MNT   | 40%  | 0 | HGRD(3), STND(1), OGRD(1) |

## 90-image entangled benchmark (30/class, MNT/SCTR/CGRD only)

| Metric | Value |
|--------|-------|
| Overall radical accuracy | **61%** (55/90) |
| Accuracy when detected | **70%** (55/79) |
| Mean PCK@0.2 | **72.8%** |
| Detection rate (2 athletes found) | 88% (79/90) |
| Good keypoint rate | 71% (64/90) |
| Missed athletes | 12% (11/90) |
| Bad keypoints | 17% (15/90) |

### Failure breakdown

| Failure type | Count | % |
|--------------|-------|---|
| OK (good detection + good kps) | 64 | 71% |
| Bad keypoints (cross-assignment) | 15 | 17% |
| Missed athlete (YOLO finds 1) | 11 | 12% |

### Top confusion patterns (classifier errors, not detection errors)

- **MNT -> HGRD**: 9 errors (largest single confusion pair)
- **SCTR -> HGRD**: 6 errors
- **CGRD -> SCTR**: 4 errors

## Bottleneck analysis

The classifier is not the bottleneck (94.1% on GT keypoints). The gap is entirely in pose detection:

1. **Missed athletes (11/90)**: YOLO cannot separate two people in extreme entanglement
2. **Bad keypoints (15/90)**: Two athletes detected but limbs cross-assigned between them
3. **Classifier confusion on bad keypoints**: When keypoints are noisy, MNT/SCTR/CGRD look similar to the classifier, and HGRD becomes a false attractor

## Next targets

- Overall radical accuracy >= 70% (currently 61%)
- Reduce MNT->HGRD confusion (9 errors)
- Reduce missed athletes (11/90 -> <5/90)
- Reduce bad keypoints (15/90 -> <8/90)
