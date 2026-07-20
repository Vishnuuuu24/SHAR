"""P1C mandatory frame and temporal control architectures."""

from __future__ import annotations

from collections.abc import Sequence

import torch
from torch import nn
from torchvision.models import ResNet50_Weights, resnet50


class ResNet50C5(nn.Module):
    """Return the spatial ResNet50 layer4/C5 map before global pooling."""

    out_channels = 2048

    def __init__(self, weights: ResNet50_Weights | None = None):
        super().__init__()
        network = resnet50(weights=weights)
        self.features = nn.Sequential(
            network.conv1,
            network.bn1,
            network.relu,
            network.maxpool,
            network.layer1,
            network.layer2,
            network.layer3,
            network.layer4,
        )
        self.weights_name = weights.name if weights is not None else None

    def forward(self, images: torch.Tensor) -> torch.Tensor:
        if images.ndim != 4 or images.shape[1] != 3:
            raise ValueError("ResNet50C5 expects [batch, 3, height, width]")
        features = self.features(images)
        if features.ndim != 4 or features.shape[1] != self.out_channels:
            raise RuntimeError(f"unexpected C5 shape: {tuple(features.shape)}")
        return features


class GlobalAverageLinearHead(nn.Module):
    def __init__(self, in_channels: int, num_classes: int):
        super().__init__()
        if in_channels <= 0 or num_classes <= 1:
            raise ValueError("in_channels must be positive and num_classes must exceed one")
        self.pool = nn.AdaptiveAvgPool2d((1, 1))
        self.classifier = nn.Linear(in_channels, num_classes)

    def forward(self, c5: torch.Tensor) -> torch.Tensor:
        if c5.ndim != 4:
            raise ValueError("GAP+linear head requires a spatial [B,C,H,W] C5 tensor")
        return self.classifier(torch.flatten(self.pool(c5), 1))


class SameC5MLPHead(nn.Module):
    """C5 -> GAP -> MLP control; it never reshapes a GAP vector as spatial data."""

    def __init__(self, in_channels: int, hidden_dim: int, num_classes: int, dropout: float):
        super().__init__()
        if min(in_channels, hidden_dim, num_classes) <= 0 or num_classes <= 1:
            raise ValueError("channel/hidden/class dimensions are invalid")
        if not 0 <= dropout < 1:
            raise ValueError("dropout must be in [0,1)")
        self.pool = nn.AdaptiveAvgPool2d((1, 1))
        self.mlp = nn.Sequential(
            nn.Linear(in_channels, hidden_dim),
            nn.ReLU(inplace=False),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, num_classes),
        )

    def forward(self, c5: torch.Tensor) -> torch.Tensor:
        if c5.ndim != 4:
            raise ValueError("same-C5 MLP head requires a spatial [B,C,H,W] C5 tensor")
        return self.mlp(torch.flatten(self.pool(c5), 1))


class FrameClassifier(nn.Module):
    def __init__(self, backbone: ResNet50C5, head: nn.Module):
        super().__init__()
        self.backbone = backbone
        self.head = head

    def forward(self, images: torch.Tensor) -> torch.Tensor:
        return self.head(self.backbone(images))


class CNNLSTMTemporalBaseline(nn.Module):
    """Source-video sequence baseline using shared C5 frame features and an LSTM."""

    def __init__(
        self,
        backbone: ResNet50C5,
        projection_dim: int,
        hidden_dim: int,
        num_layers: int,
        num_classes: int,
        dropout: float,
    ):
        super().__init__()
        if min(projection_dim, hidden_dim, num_layers, num_classes) <= 0 or num_classes <= 1:
            raise ValueError("temporal architecture dimensions are invalid")
        if not 0 <= dropout < 1:
            raise ValueError("dropout must be in [0,1)")
        self.backbone = backbone
        self.pool = nn.AdaptiveAvgPool2d((1, 1))
        self.projection = nn.Linear(backbone.out_channels, projection_dim)
        self.lstm = nn.LSTM(
            input_size=projection_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0.0,
        )
        self.classifier = nn.Linear(hidden_dim, num_classes)

    def forward(
        self,
        clips: torch.Tensor,
        lengths: torch.Tensor,
        source_video_ids: Sequence[str],
    ) -> torch.Tensor:
        if clips.ndim != 5 or clips.shape[2] != 3:
            raise ValueError("temporal baseline expects [batch,time,3,height,width]")
        batch, time = clips.shape[:2]
        if lengths.shape != (batch,):
            raise ValueError("lengths must contain one value per clip")
        if len(source_video_ids) != batch or any(not value for value in source_video_ids):
            raise ValueError("source_video_ids must identify every source-grouped clip")
        if torch.any(lengths < 1) or torch.any(lengths > time):
            raise ValueError("clip lengths must be within [1,time]")
        frames = clips.reshape(batch * time, *clips.shape[2:])
        c5 = self.backbone(frames)
        frame_features = torch.flatten(self.pool(c5), 1)
        projected = self.projection(frame_features).reshape(batch, time, -1)
        outputs, _ = self.lstm(projected)
        gather_index = (lengths.to(outputs.device) - 1).view(batch, 1, 1).expand(-1, 1, outputs.shape[-1])
        final = outputs.gather(1, gather_index).squeeze(1)
        return self.classifier(final)
