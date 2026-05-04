import json
from pathlib import Path
from data.schema import Annotation, Pose


DEFAULT_PATH = Path(__file__).parent / "raw" / "annotations.json"
DEFAULT_IMAGE_DIR = Path(__file__).parent / "raw" / "images"


def load_annotations(path: Path = DEFAULT_PATH) -> list[Annotation]:
    with open(path) as f:
        raw = json.load(f)

    annotations = []
    for entry in raw:
        pose1 = Pose.from_raw(entry["pose1"]) if "pose1" in entry else None
        pose2 = Pose.from_raw(entry["pose2"]) if "pose2" in entry else None
        annotations.append(Annotation(
            position=entry["position"],
            image=entry["image"],
            frame=entry["frame"],
            pose1=pose1,
            pose2=pose2,
        ))
    return annotations


def image_path(image_id: str, image_dir: Path = DEFAULT_IMAGE_DIR) -> Path:
    return image_dir / f"{image_id}.jpg"


def verify_images(
    annotations: list[Annotation],
    image_dir: Path = DEFAULT_IMAGE_DIR,
) -> tuple[int, int, list[str]]:
    """Check which annotation image IDs have corresponding files on disk.

    Returns (found, missing_count, missing_ids_sample).
    """
    found = 0
    missing = []
    for ann in annotations:
        if image_path(ann.image, image_dir).exists():
            found += 1
        else:
            missing.append(ann.image)
    sample = missing[:20]
    return found, len(missing), sample
