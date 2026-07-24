from __future__ import annotations

import unittest

import torch
from torch import nn

from models.classifiers import (
    CNNLSTMTemporalBaseline,
    GlobalAverageLinearHead,
    ResNet50C5,
    SameC5MLPHead,
)


class TinyC5(nn.Module):
    out_channels = 16

    def __init__(self):
        super().__init__()
        self.features = nn.Conv2d(3, self.out_channels, kernel_size=3, padding=1)

    def forward(self, images: torch.Tensor) -> torch.Tensor:
        return self.features(images)


class FrameControlTests(unittest.TestCase):
    def test_resnet50_returns_spatial_c5_not_gap_vector(self) -> None:
        backbone = ResNet50C5(weights=None).eval()
        with torch.no_grad():
            c5 = backbone(torch.randn(1, 3, 64, 64))
        self.assertEqual(c5.shape, (1, 2048, 2, 2))

    def test_both_heads_consume_identical_spatial_c5_and_return_14_logits(self) -> None:
        c5 = torch.randn(2, 16, 4, 4, requires_grad=True)
        linear = GlobalAverageLinearHead(16, 14)
        mlp = SameC5MLPHead(16, hidden_dim=8, num_classes=14, dropout=0.0)
        linear_logits = linear(c5)
        mlp_logits = mlp(c5)
        self.assertEqual(linear_logits.shape, (2, 14))
        self.assertEqual(mlp_logits.shape, (2, 14))
        (linear_logits.sum() + mlp_logits.sum()).backward()
        self.assertIsNotNone(c5.grad)
        self.assertTrue(torch.isfinite(c5.grad).all())

    def test_heads_reject_gap_vector_as_spatial_input(self) -> None:
        vector = torch.randn(2, 2048)
        with self.assertRaisesRegex(ValueError, "spatial"):
            GlobalAverageLinearHead(2048, 14)(vector)
        with self.assertRaisesRegex(ValueError, "spatial"):
            SameC5MLPHead(2048, 32, 14, 0.0)(vector)


class TemporalControlTests(unittest.TestCase):
    def setUp(self) -> None:
        self.model = CNNLSTMTemporalBaseline(
            TinyC5(),
            projection_dim=8,
            hidden_dim=6,
            num_layers=1,
            num_classes=14,
            dropout=0.0,
        )

    def test_source_grouped_temporal_forward_and_gradient(self) -> None:
        clips = torch.randn(2, 3, 3, 16, 16, requires_grad=True)
        logits = self.model(clips, torch.tensor([3, 2]), ["video-a", "video-b"])
        self.assertEqual(logits.shape, (2, 14))
        logits.sum().backward()
        self.assertIsNotNone(clips.grad)
        self.assertTrue(torch.isfinite(clips.grad).all())

    def test_temporal_model_requires_one_source_id_per_sequence(self) -> None:
        clips = torch.randn(2, 3, 3, 16, 16)
        with self.assertRaisesRegex(ValueError, "source_video_ids"):
            self.model(clips, torch.tensor([3, 3]), ["only-one"])
        with self.assertRaisesRegex(ValueError, "lengths"):
            self.model(clips, torch.tensor([3, 0]), ["a", "b"])

    def test_temporal_model_rejects_non_integral_lengths_before_gather(self) -> None:
        clips = torch.randn(2, 3, 3, 16, 16)
        with self.assertRaisesRegex(TypeError, "integer dtype"):
            self.model(clips, torch.tensor([3.0, 2.0]), ["a", "b"])


if __name__ == "__main__":
    unittest.main()
