from dataclasses import dataclass
from typing import Optional


@dataclass
class Keypoint:
    x: float
    y: float
    confidence: float


@dataclass
class Pose:
    keypoints: list[Keypoint]  # 17 COCO keypoints

    @classmethod
    def from_raw(cls, raw: list[list[float]]) -> "Pose":
        return cls([Keypoint(pt[0], pt[1], pt[2]) for pt in raw])


@dataclass
class Annotation:
    position: str           # ViCoS label e.g. "open_guard1"
    image: str              # 7-digit image ID e.g. "0000001"
    frame: int
    pose1: Optional[Pose]   # first athlete (may be absent)
    pose2: Optional[Pose]   # second athlete (may be absent)
