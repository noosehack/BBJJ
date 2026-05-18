"""Head-to-head: Claude Vision vs Geometry Classifier on BJJ positions.

Selects a shuffled sample of images from 6 fundamental positions,
classifies each with both Claude Vision (raw pixels) and the geometry
classifier (YOLO keypoints -> body-frame features -> MLP), then compares.
"""

import base64
import json
import os
import random
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import anthropic

from tools.infer_image import YoloPoseBackend, select_athletes
from tools.geometry_classifier import classify_both_pov

FINE_MAP = {
    "mount1": "MNT", "mount2": "MNT",
    "side_control1": "SCTR", "side_control2": "SCTR",
    "back1": "BCTR", "back2": "BCTR",
    "closed_guard1": "CGRD", "closed_guard2": "CGRD",
    "open_guard1": "OGRD", "open_guard2": "OGRD",
    "half_guard1": "HGRD", "half_guard2": "HGRD",
}

TARGET = ["MNT", "SCTR", "BCTR", "CGRD", "OGRD", "HGRD"]

VLM_PROMPT = """Look at this BJJ (Brazilian Jiu-Jitsu) image. Classify the position into exactly one of these categories:

- MNT (mount): one athlete sitting on top of the other's torso, the bottom person is on their back
- SCTR (side control): top athlete lying across the bottom athlete's torso from the side, chest-to-chest, perpendicular
- BCTR (back control): one athlete behind the other, chest-to-back, often with hooks (legs wrapped around)
- CGRD (closed guard): bottom athlete on their back with legs wrapped around the top athlete's waist
- OGRD (open guard): bottom athlete on their back with legs in front of/on the top athlete but not locked around waist
- HGRD (half guard): bottom athlete on their back with legs tangled around one of the top athlete's legs

Respond with ONLY the code (MNT, SCTR, BCTR, CGRD, OGRD, or HGRD). Nothing else."""


def load_sample(n_per_class=10, seed=42):
    random.seed(seed)
    with open("data/raw/annotations.json") as f:
        anns = json.load(f)

    by_class = defaultdict(list)
    for a in anns:
        pos = a["position"]
        fine = FINE_MAP.get(pos)
        if fine not in TARGET:
            continue
        img_path = f"data/raw/images/{a['image']}.jpg"
        if not os.path.exists(img_path):
            continue
        by_class[fine].append({"image": a["image"], "position": pos, "fine": fine, "img_path": img_path})

    sample = []
    for cls in sorted(TARGET):
        items = by_class[cls]
        random.shuffle(items)
        seen_vids = set()
        picked = []
        for item in items:
            vid = item["image"][:2]
            if vid not in seen_vids or len(picked) < n_per_class:
                seen_vids.add(vid)
                picked.append(item)
            if len(picked) >= n_per_class:
                break
        sample.extend(picked)

    random.shuffle(sample)
    return sample


def classify_vlm(client, img_path):
    with open(img_path, "rb") as f:
        img_data = base64.standard_b64encode(f.read()).decode("utf-8")

    ext = Path(img_path).suffix.lower()
    media_type = "image/jpeg" if ext in (".jpg", ".jpeg") else "image/png"

    resp = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=10,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": img_data}},
                {"type": "text", "text": VLM_PROMPT},
            ],
        }],
    )
    raw = resp.content[0].text.strip().upper()
    for t in TARGET:
        if t in raw:
            return t
    return raw


def classify_pipeline(yolo, img_path):
    try:
        detections = yolo.detect(img_path)
        raw_a, raw_b = select_athletes(detections, nms_iou=0.8)
        result = classify_both_pov(raw_a, raw_b)
        return result.radical, result.confidence
    except Exception as e:
        return "DETECT_FAIL", 0.0


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    sample = load_sample(n_per_class=n)
    print(f"Sample: {len(sample)} images ({n}/class, {len(TARGET)} classes)")
    for cls in sorted(TARGET):
        print(f"  {cls}: {sum(1 for s in sample if s['fine'] == cls)}")

    client = anthropic.Anthropic()
    yolo = YoloPoseBackend("models_pose/bjj_v2_posehead/weights/best.pt")

    results = []
    vlm_correct = 0
    clf_correct = 0

    print(f"\n{'#':>3s} {'TRUE':>5s} {'VLM':>5s} {'CLF':>5s} {'VLM':>4s} {'CLF':>4s}  IMAGE")
    print(f"{'':>3s} {'':>5s} {'':>5s} {'':>5s} {'ok?':>4s} {'ok?':>4s}  {'':>5s}")
    print("-" * 65)

    for i, item in enumerate(sample):
        true = item["fine"]
        img = item["img_path"]

        vlm_pred = classify_vlm(client, img)
        clf_pred, clf_conf = classify_pipeline(yolo, img)

        vlm_ok = vlm_pred == true
        clf_ok = clf_pred == true
        if vlm_ok:
            vlm_correct += 1
        if clf_ok:
            clf_correct += 1

        vlm_mark = "Y" if vlm_ok else "n"
        clf_mark = "Y" if clf_ok else "n"

        print(f"{i+1:>3d} {true:>5s} {vlm_pred:>5s} {clf_pred:>5s} {vlm_mark:>4s} {clf_mark:>4s}  {item['image']}")

        results.append({
            "image": item["image"], "true": true,
            "vlm": vlm_pred, "clf": clf_pred, "clf_conf": clf_conf,
            "vlm_correct": vlm_ok, "clf_correct": clf_ok,
        })

        # Rate limit (tier-dependent, be safe)
        time.sleep(0.5)

    n_total = len(results)
    print(f"\n{'='*65}")
    print(f"  RESULTS: {n_total} images")
    print(f"{'='*65}")
    print(f"  Claude Vision:       {vlm_correct}/{n_total} = {vlm_correct/n_total:.1%}")
    print(f"  Geometry Classifier: {clf_correct}/{n_total} = {clf_correct/n_total:.1%}")

    # Per-class breakdown
    print(f"\n  {'Class':>5s} {'VLM':>8s} {'CLF':>8s} {'VLM confused':>30s} {'CLF confused':>30s}")
    print(f"  {'-'*5} {'-'*8} {'-'*8} {'-'*30} {'-'*30}")
    for cls in sorted(TARGET):
        cr = [r for r in results if r["true"] == cls]
        nc = len(cr)
        vc = sum(1 for r in cr if r["vlm_correct"])
        cc = sum(1 for r in cr if r["clf_correct"])
        v_conf = Counter(r["vlm"] for r in cr if not r["vlm_correct"])
        c_conf = Counter(r["clf"] for r in cr if not r["clf_correct"])
        v_str = ", ".join(f"{k}({v})" for k, v in v_conf.most_common(3)) or "--"
        c_str = ", ".join(f"{k}({v})" for k, v in c_conf.most_common(3)) or "--"
        print(f"  {cls:>5s} {vc:>3d}/{nc:<3d} {cc:>3d}/{nc:<3d} {v_str:>30s} {c_str:>30s}")

    # Agreement analysis
    both_right = sum(1 for r in results if r["vlm_correct"] and r["clf_correct"])
    vlm_only = sum(1 for r in results if r["vlm_correct"] and not r["clf_correct"])
    clf_only = sum(1 for r in results if not r["vlm_correct"] and r["clf_correct"])
    both_wrong = sum(1 for r in results if not r["vlm_correct"] and not r["clf_correct"])

    print(f"\n  Agreement:")
    print(f"    Both correct:     {both_right:>3d} ({both_right/n_total:.0%})")
    print(f"    VLM only correct: {vlm_only:>3d} ({vlm_only/n_total:.0%})")
    print(f"    CLF only correct: {clf_only:>3d} ({clf_only/n_total:.0%})")
    print(f"    Both wrong:       {both_wrong:>3d} ({both_wrong/n_total:.0%})")

    out = Path("demo_benchmark")
    out.mkdir(exist_ok=True)
    with open(out / "vlm_vs_classifier.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n  Saved: demo_benchmark/vlm_vs_classifier.json")


if __name__ == "__main__":
    main()
