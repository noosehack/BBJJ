"""Phase 4+5: Pose geometry analysis and resolution sensitivity for grappling."""

import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from data.schema import Pose, Keypoint
from tools.axis_reconstruction import torso_center, torso_length, Vec2

COCO_NAMES = [
    "nose", "left_eye", "right_eye", "left_ear", "right_ear",
    "left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
    "left_wrist", "right_wrist", "left_hip", "right_hip",
    "left_knee", "right_knee", "left_ankle", "right_ankle",
]


def analyze_geometry(raw_kps, label="Person"):
    """Analyze pose geometry to detect COCO-prior violations."""
    kps = [(x, y, c) for x, y, c in raw_kps]

    # Torso orientation (COCO assumes roughly vertical)
    sh_mid_x = (kps[5][0] + kps[6][0]) / 2
    sh_mid_y = (kps[5][1] + kps[6][1]) / 2
    hp_mid_x = (kps[11][0] + kps[12][0]) / 2
    hp_mid_y = (kps[11][1] + kps[12][1]) / 2

    dx = hp_mid_x - sh_mid_x
    dy = hp_mid_y - sh_mid_y
    import math
    torso_angle = math.degrees(math.atan2(dx, dy))  # 0=vertical, 90=horizontal

    # Leg compactness: how close are knees/ankles to hips?
    pose = Pose.from_raw(raw_kps)
    tl = torso_length(pose)

    knee_to_hip = []
    ankle_to_knee = []
    ankle_to_hip = []
    for side in [(13, 11, 15), (14, 12, 16)]:  # (knee, hip, ankle)
        ki, hi, ai = side
        if kps[ki][2] > 0.1 and kps[hi][2] > 0.1:
            d = math.sqrt((kps[ki][0]-kps[hi][0])**2 + (kps[ki][1]-kps[hi][1])**2)
            knee_to_hip.append(d / max(tl, 1))
        if kps[ai][2] > 0.1 and kps[ki][2] > 0.1:
            d = math.sqrt((kps[ai][0]-kps[ki][0])**2 + (kps[ai][1]-kps[ki][1])**2)
            ankle_to_knee.append(d / max(tl, 1))
        if kps[ai][2] > 0.1 and kps[hi][2] > 0.1:
            d = math.sqrt((kps[ai][0]-kps[hi][0])**2 + (kps[ai][1]-kps[hi][1])**2)
            ankle_to_hip.append(d / max(tl, 1))

    # Limb crossing: do left/right legs cross over?
    knee_crossed = False
    if kps[13][2] > 0.1 and kps[14][2] > 0.1:
        # In COCO, left knee x should be > right knee x (left = image-right for facing camera)
        # For side-lying, this assumption breaks
        knee_crossed = abs(kps[13][0] - kps[14][0]) < 20  # knees nearly overlapping

    # Keypoints outside detection bbox
    visible = [(x, y) for x, y, c in kps if c > 0.1]
    if visible:
        bbox_w = max(x for x, y in visible) - min(x for x, y in visible)
        bbox_h = max(y for x, y in visible) - min(y for x, y in visible)
    else:
        bbox_w, bbox_h = 0, 0

    print(f"\n  {label}:")
    print(f"    Torso angle from vertical: {torso_angle:.1f}° (0=upright, 90=horizontal)")
    print(f"    Torso length: {tl:.1f}px")
    print(f"    Knee-to-hip dist (norm): {[f'{d:.2f}' for d in knee_to_hip]}")
    print(f"    Ankle-to-knee dist (norm): {[f'{d:.2f}' for d in ankle_to_knee]}")
    print(f"    Ankle-to-hip dist (norm): {[f'{d:.2f}' for d in ankle_to_hip]}")
    print(f"    Knees crossed/overlapping: {knee_crossed}")
    print(f"    Keypoint bbox: {bbox_w:.0f} x {bbox_h:.0f}")

    # Geometric violations for COCO standing prior
    violations = []
    if abs(torso_angle) > 45:
        violations.append(f"NON-UPRIGHT torso ({torso_angle:.0f}°)")
    if knee_to_hip and max(knee_to_hip) < 0.5:
        violations.append(f"COMPRESSED knees (norm dist {max(knee_to_hip):.2f} < 0.5)")
    if ankle_to_knee and max(ankle_to_knee) < 0.3:
        violations.append(f"COMPRESSED ankles (norm dist {max(ankle_to_knee):.2f} < 0.3)")
    if knee_crossed:
        violations.append("CROSSED knees (overlapping)")

    if violations:
        print(f"    COCO-PRIOR VIOLATIONS: {', '.join(violations)}")
    else:
        print(f"    No COCO-prior violations detected")

    return {
        "torso_angle": torso_angle,
        "knee_to_hip": knee_to_hip,
        "ankle_to_knee": ankle_to_knee,
        "violations": violations,
    }


def main():
    from ultralytics import YOLO
    model_path = str(Path(__file__).resolve().parent.parent / "models_pose" / "bjj_v2_posehead" / "weights" / "best.pt")
    model = YOLO(model_path)

    image_path = sys.argv[1]
    print(f"=== POSE GEOMETRY ANALYSIS: {image_path} ===")

    results = model(image_path, verbose=False, conf=0.01)
    for r in results:
        if r.keypoints is None:
            continue
        for ki, kps in enumerate(r.keypoints.data):
            box_conf = float(r.boxes.conf[ki]) if r.boxes is not None else 0.0
            if box_conf < 0.01:
                continue
            raw = [[float(kp[0]), float(kp[1]), float(kp[2])] for kp in kps]
            analyze_geometry(raw, f"Person {ki+1} (box_conf={box_conf:.4f})")

    # Compare with COCO standing baseline
    print(f"\n\n=== COCO STANDING PRIOR REFERENCE ===")
    print(f"  In standing humans:")
    print(f"    Torso angle: ~0° (upright)")
    print(f"    Knee-to-hip normalized distance: ~0.8-1.2")
    print(f"    Ankle-to-knee normalized distance: ~0.8-1.2")
    print(f"    Knees: never overlapping")
    print(f"\n  In grappling (this image):")
    print(f"    Torso angle: often 45-90° (side-lying, inverted)")
    print(f"    Knee-to-hip: can be 0.2-0.5 (bent/folded)")
    print(f"    Ankle-to-knee: can be 0.1-0.3 (compressed)")
    print(f"    Knees: frequently overlapping (entangled)")


if __name__ == "__main__":
    main()
