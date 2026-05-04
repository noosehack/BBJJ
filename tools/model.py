"""MLP baseline for keypoint → RAD classification."""

import torch
import torch.nn as nn


class RadicalMLP(nn.Module):
    """102 → 256 → 128 → n_classes MLP with dropout and ReLU."""

    def __init__(self, n_classes: int, n_features: int = 102, dropout: float = 0.2):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(n_features, 256),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(128, n_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)
