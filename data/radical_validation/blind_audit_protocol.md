# Blind Audit Protocol for Radical Constraint Validation

## Purpose

Determine whether claimed body-contact relations genuinely exist in images, without knowledge of the expected radical, dataset label, or system verdict. This breaks the circularity of the current pipeline, which assumes all required contacts are correct and classifies every detection failure as "perception."

## Protocol

### Phase 1: Sample Selection

**Stratified adversarial sampling.** For each of the 7 evaluable radicals, select 50 images:

- 15 where the pipeline says "all constraints met" (system says OK)
- 15 where the pipeline says "required contact failed, keypoints adequate" (system says C — the contested category)
- 10 where the pipeline says "required contact failed, keypoints bad" (system says B)
- 10 where the pipeline says "forbidden contact violated" (system says D)

Total: 350 images.

Selection within each stratum: random with seed, reproducible.

### Phase 2: Stimulus Preparation

For each image, prepare a stimulus packet containing:

1. The image (cropped to bounding box of both fighters, no labels)
2. The COCO keypoint skeleton overlaid on the image (colored by confidence: green > 0.5, yellow 0.3-0.5, red < 0.3)
3. A list of body-contact questions (see annotation form below)

**What the annotator does NOT see:**
- The dataset label (mount, guard, etc.)
- The system's radical assignment
- The system's constraint verdicts
- The radical name or definition
- Any scoring information

### Phase 3: Annotation Form

For each image, the annotator answers concrete physical questions. Each question is binary or ternary. No BJJ terminology is used — only body-part contact descriptions.

#### Contact Questions (for each candidate contact in the radical)

Format: "Is [body part A of person X] in physical contact with or pressing against [body part B of person Y]?"

Specific questions per radical:

**For MNT/BCTR/CGRD (leg-around-torso contacts):**
- Q1: "Is the RIGHT LEG (thigh-to-foot) of Person 1 wrapped around or pressing against the TORSO (hip-to-shoulder) of Person 2?" [Yes / Borderline / No]
- Q2: "Is the LEFT LEG (thigh-to-foot) of Person 1 wrapped around or pressing against the TORSO (hip-to-shoulder) of Person 2?" [Yes / Borderline / No]

**For CGRD (ankle closure):**
- Q3: "Are Person 1's ankles crossed or locked together behind Person 2?" [Yes / Borderline / No / Cannot determine from this view]

**For SCTR (arm contact + leg exclusion):**
- Q4: "Is the RIGHT ARM (wrist-to-shoulder) of Person 1 pressing against or draped across the TORSO of Person 2?" [Yes / Borderline / No]
- Q5: "Is either LEG of Person 1 hooked around, entangled with, or wrapped around either LEG of Person 2?" [Yes / Borderline / No]

**For TRTL (torso-on-torso):**
- Q6: "Is the CHEST/TORSO of Person 2 pressing against the BACK/TORSO of Person 1?" [Yes / Borderline / No]

**For HGRD (leg-on-leg):**
- Q7: "Is a LEG of Person 1 hooked around or entangled with a LEG of Person 2?" [Yes / Borderline / No]

#### Frame Questions (for all radicals)

- Q8: "Are the two people FACING EACH OTHER (chests toward each other)?" [Yes / No / Sideways/Perpendicular / Cannot determine]
- Q9: "Are the two people FACING THE SAME DIRECTION (one behind the other)?" [Yes / No / Cannot determine]
- Q10: "Which person's hips are LOWER (closer to the ground/mat)?" [Person 1 / Person 2 / About the same / Cannot determine]

#### Image Quality

- Q11: "Can you clearly see both people's body positions?" [Yes / Partially (some parts occluded) / No (too obscured)]
- Q12: "Do the keypoint skeletons appear correctly placed on the bodies?" [Yes / Mostly / Several are wrong / Badly misaligned]

### Phase 4: Decision Rules

Each annotator response maps to a constraint assessment:

| Annotator Response | Constraint Status |
|---|---|
| "Yes" to a required contact question | Contact CONFIRMED present |
| "No" to a required contact question | Contact CONFIRMED absent |
| "Borderline" | Contact AMBIGUOUS |
| "Cannot determine from this view" | Contact UNOBSERVABLE |
| "Yes" to a forbidden contact question | Forbidden contact CONFIRMED violated |
| "No" to a forbidden contact question | Forbidden contact CONFIRMED clear |

**Classification rules (applied after annotation, not shown to annotator):**

| Annotator says contact present | System says contact detected | Diagnosis |
|---|---|---|
| Yes | Yes | Concordant: both agree contact exists |
| Yes | No | Pipeline false negative (genuine C — perception failure) |
| No | No | Concordant: contact genuinely absent |
| No | Yes | Pipeline false positive |
| Borderline | Either | Ambiguous — exclude from analysis |
| Unobservable | Either | Genuine observability limitation |

**The critical test:** For required contacts where the system says "C (2D failure)":
- If annotator says "Yes" → confirmed C (contact exists but pipeline missed it)
- If annotator says "No" → THIS IS A NOTATION FAILURE (D), not a perception failure
- If annotator says "Borderline" → ambiguous, cannot determine
- If annotator says "Unobservable" → confirmed C (cannot assess from this view)

### Phase 5: Inter-Annotator Agreement

**Minimum:** 2 independent annotators per image.

**Agreement metric:** Cohen's kappa (κ) per question type.

**Expected κ ranges:**
- Contact questions (Q1-Q7): expect κ > 0.6 (substantial agreement). Physical contact is usually visually clear.
- Frame questions (Q8-Q10): expect κ > 0.4 (moderate agreement). Facing direction is harder to judge from a single image.
- Quality questions (Q11-Q12): expect κ > 0.7.

**Disagreement resolution:** For images where annotators disagree on a contact question, a third annotator breaks the tie. If all three give different answers, the image is marked AMBIGUOUS and excluded.

### Phase 6: Analysis

**Primary analysis:** For each radical constraint, compute:

1. **Annotator confirmation rate:** Of the samples where the system says the contact should be present (based on the dataset tag), how often do annotators confirm it IS present?
2. **Pipeline detection rate on confirmed contacts:** Of the contacts annotators confirm exist, how often does the pipeline detect them?
3. **True C rate:** contacts confirmed present by annotators but missed by pipeline
4. **True D rate:** contacts confirmed absent by annotators (notation is wrong)
5. **Ambiguity rate:** contacts where annotators cannot agree or say "borderline"

**The honest validation rate** = (annotator-confirmed contacts that pipeline also detects) / (annotator-confirmed contacts). This is the C-vs-D separation that the current pipeline cannot compute.

## Sampling Strategy

```python
# Reproducible sampling
import random
rng = random.Random(42)

for radical in EVALUABLE_RADICALS:
    class_samples = get_samples_for_class(radical)
    
    ok_samples = [s for s in class_samples if system_verdict(s) == "OK"]
    c_samples = [s for s in class_samples if system_verdict(s) == "C" 
                 and keypoints_adequate(s)]
    b_samples = [s for s in class_samples if system_verdict(s) == "B"]
    d_samples = [s for s in class_samples if system_verdict(s) == "D"]
    
    selected = (
        rng.sample(ok_samples, min(15, len(ok_samples))) +
        rng.sample(c_samples, min(15, len(c_samples))) +
        rng.sample(b_samples, min(10, len(b_samples))) +
        rng.sample(d_samples, min(10, len(d_samples)))
    )
```

## What This Protocol Can Determine

1. Whether required contacts genuinely exist when the pipeline fails to detect them (true C vs D separation)
2. Whether the notation's required contacts are invariant to the tagged position or merely typical
3. Whether the "100% clean validation" is real or an artifact of circular exclusion
4. Whether facing-direction constraints are genuinely present (annotator judgment vs pipeline projection)
5. Whether forbidden contact violations are genuine (are SCTR legs really entangled, or just nearby?)

## What This Protocol Cannot Determine

1. Whether the dataset tags themselves are correct (that requires BJJ expertise, which breaks blinding)
2. Whether the radical decomposition is optimal (that's a theory question, not an annotation question)
3. 3D contact relationships that are invisible from any 2D view
