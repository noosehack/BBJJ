"""Tests for MLP model and training utilities."""

import numpy as np
import torch

from tools.model import RadicalMLP
from tools.train import confusion_matrix


class TestRadicalMLP:

    def test_output_shape(self):
        model = RadicalMLP(n_classes=9)
        x = torch.randn(4, 102)
        out = model(x)
        assert out.shape == (4, 9)

    def test_single_sample(self):
        model = RadicalMLP(n_classes=9)
        x = torch.randn(1, 102)
        out = model(x)
        assert out.shape == (1, 9)

    def test_gradient_flows(self):
        model = RadicalMLP(n_classes=9)
        x = torch.randn(8, 102)
        y = torch.randint(0, 9, (8,))
        loss = torch.nn.CrossEntropyLoss()(model(x), y)
        loss.backward()
        for p in model.parameters():
            assert p.grad is not None
            assert p.grad.abs().sum() > 0

    def test_eval_deterministic(self):
        model = RadicalMLP(n_classes=9)
        model.eval()
        x = torch.randn(4, 102)
        out1 = model(x)
        out2 = model(x)
        assert torch.allclose(out1, out2)

    def test_custom_features(self):
        model = RadicalMLP(n_classes=5, n_features=50, dropout=0.1)
        x = torch.randn(2, 50)
        assert model(x).shape == (2, 5)


class TestConfusionMatrix:

    def test_basic(self):
        y_true = np.array([0, 0, 1, 1, 2])
        y_pred = np.array([0, 1, 1, 1, 2])
        cm = confusion_matrix(y_true, y_pred, 3)
        assert cm[0, 0] == 1
        assert cm[0, 1] == 1
        assert cm[1, 1] == 2
        assert cm[2, 2] == 1
        assert cm.sum() == 5

    def test_perfect(self):
        y = np.array([0, 1, 2, 0, 1])
        cm = confusion_matrix(y, y, 3)
        assert np.all(cm == np.diag(np.diag(cm)))

    def test_empty_class(self):
        y_true = np.array([0, 0, 1])
        y_pred = np.array([0, 0, 1])
        cm = confusion_matrix(y_true, y_pred, 4)
        assert cm.shape == (4, 4)
        assert cm[2].sum() == 0
        assert cm[3].sum() == 0
