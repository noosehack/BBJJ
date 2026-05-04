import json
from pathlib import Path
from data.schema import Annotation, Pose


DEFAULT_PATH = Path(__file__).parent / "raw" / "annotations.json"


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
