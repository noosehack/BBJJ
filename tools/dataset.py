"""PyTorch Dataset for BLISP keypoint → RAD classification."""

import json
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import Dataset


class BJJDataset(Dataset):
    """Keypoint → radical classification dataset.

    Each sample: X = (102,) float32 normalized keypoints, y = int64 radical index.
    With symbolic=True: X = (132,) concatenation of keypoints + 30-dim symbolic features.
    """

    def __init__(self, data_dir: str | Path, split: str = "train", symbolic: bool = False):
        data_dir = Path(data_dir)
        data = np.load(data_dir / f"{split}.npz")
        kps = torch.from_numpy(data["X"])

        if symbolic and "X_sym" in data:
            sym = torch.from_numpy(data["X_sym"])
            self.features = torch.cat([kps, sym], dim=1)
        else:
            self.features = kps

        self.labels = torch.from_numpy(data["y"])
        self.symbolic = symbolic

        with open(data_dir / "info.json") as f:
            info = json.load(f)
        self.class_names: list[str] = info["class_names"]
        self.class_to_idx: dict[str, int] = info["class_to_idx"]
        self.n_classes: int = info["n_classes"]
        self.n_features: int = self.features.shape[1]

        meta_path = data_dir / f"{split}_meta.json"
        self.meta: list[dict] | None = None
        if meta_path.exists():
            with open(meta_path) as f:
                self.meta = json.load(f)

    def __len__(self) -> int:
        return len(self.labels)

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, torch.Tensor]:
        return self.features[idx], self.labels[idx]

    def class_weights(self) -> torch.Tensor:
        """Inverse-frequency weights for imbalanced classes."""
        counts = torch.bincount(self.labels, minlength=self.n_classes).float()
        counts = counts.clamp(min=1)
        weights = 1.0 / counts
        return weights / weights.sum() * self.n_classes

    def label_name(self, idx: int) -> str:
        return self.class_names[idx]
