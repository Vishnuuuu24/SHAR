"""Explicit device selection; SHAR never silently falls back from MPS."""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from typing import Any

import torch


@dataclass(frozen=True)
class DeviceReport:
    selected: str
    mps_built: bool
    mps_available: bool
    cpu_fallback_allowed: bool
    mps_fallback_environment: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def select_device(*, prefer_mps: bool = True, allow_cpu_fallback: bool = False) -> tuple[torch.device, DeviceReport]:
    mps_built = torch.backends.mps.is_built()
    mps_available = torch.backends.mps.is_available()
    fallback_environment = os.environ.get("PYTORCH_ENABLE_MPS_FALLBACK")
    if fallback_environment == "1" and not allow_cpu_fallback:
        raise RuntimeError("PYTORCH_ENABLE_MPS_FALLBACK=1 is prohibited unless CPU fallback is explicitly allowed")
    if prefer_mps and mps_available:
        selected = "mps"
    elif prefer_mps and not allow_cpu_fallback:
        raise RuntimeError(
            f"MPS requested but unavailable (built={mps_built}, available={mps_available}); "
            "refusing silent CPU fallback"
        )
    else:
        selected = "cpu"
    report = DeviceReport(
        selected=selected,
        mps_built=mps_built,
        mps_available=mps_available,
        cpu_fallback_allowed=allow_cpu_fallback,
        mps_fallback_environment=fallback_environment,
    )
    return torch.device(selected), report


def assert_tensor_device(value: torch.Tensor, expected: torch.device) -> None:
    if value.device.type != expected.type:
        raise RuntimeError(f"tensor device drift: expected {expected.type}, found {value.device.type}")
