#!/usr/bin/env python3
"""Record exact P0C imports, platform, MPS visibility, and operation smoke results."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import numpy as np
import PIL
import psutil
import torch
import torchvision
import yaml

from core.device import assert_tensor_device, select_device


PACKAGES = [
    "filelock",
    "fsspec",
    "Jinja2",
    "MarkupSafe",
    "mpmath",
    "networkx",
    "numpy",
    "pillow",
    "psutil",
    "PyYAML",
    "setuptools",
    "sympy",
    "torch",
    "torchvision",
    "typing_extensions",
]


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_report(require_mps: bool) -> dict:
    lock_path = REPO_ROOT / "requirements/p0c-lock.txt"
    report = {
        "schema_version": "1.0.0",
        "kind": "P0C environment compatibility check; not a research result",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "python": {
            "version": platform.python_version(),
            "implementation": platform.python_implementation(),
            "executable": str(Path(sys.executable).relative_to(REPO_ROOT)),
        },
        "platform": {
            "platform": platform.platform(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "mac_version": platform.mac_ver()[0],
            "logical_cpu_count": psutil.cpu_count(logical=True),
            "physical_cpu_count": psutil.cpu_count(logical=False),
            "total_memory_bytes": psutil.virtual_memory().total,
        },
        "packages": {name: importlib.metadata.version(name) for name in PACKAGES},
        "direct_import_versions": {
            "torch": torch.__version__,
            "torchvision": torchvision.__version__,
            "numpy": np.__version__,
            "Pillow": PIL.__version__,
            "PyYAML": yaml.__version__,
            "psutil": psutil.__version__,
        },
        "environment_lock": {
            "path": lock_path.relative_to(REPO_ROOT).as_posix(),
            "sha256": sha256_file(lock_path),
        },
        "mps": {
            "built": torch.backends.mps.is_built(),
            "available": torch.backends.mps.is_available(),
            "fallback_environment": os.environ.get("PYTORCH_ENABLE_MPS_FALLBACK"),
            "operation_smoke": "NOT_RUN",
        },
    }
    if torch.backends.mps.is_available():
        device, device_report = select_device(prefer_mps=True, allow_cpu_fallback=False)
        convolution = torch.nn.Conv2d(3, 8, kernel_size=3, padding=1).to(device)
        value = torch.randn(4, 3, 32, 32, device=device, requires_grad=True)
        result = torch.nn.functional.adaptive_avg_pool2d(torch.relu(convolution(value)), (1, 1)).sum()
        result.backward()
        torch.mps.synchronize()
        assert_tensor_device(value, device)
        assert_tensor_device(result, device)
        if value.grad is None:
            raise RuntimeError("MPS smoke backward produced no input gradient")
        assert_tensor_device(value.grad, device)
        report["mps"]["device_report"] = device_report.to_dict()
        report["mps"]["operation_smoke"] = "PASS"
        report["mps"]["tested_operations"] = ["conv2d", "relu", "adaptive_avg_pool2d", "sum", "backward"]
    elif require_mps:
        report["mps"]["operation_smoke"] = "BLOCKED"
        report["mps"]["blocker"] = "MPS is built into torch but unavailable to this process"
    report["verdict"] = (
        "PASS"
        if report["mps"]["operation_smoke"] == "PASS"
        else ("BLOCKED" if require_mps else "PASS_WITHOUT_MPS")
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--require-mps", action="store_true")
    args = parser.parse_args()
    report = build_report(args.require_mps)
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        output = args.output if args.output.is_absolute() else REPO_ROOT / args.output
        if output.exists():
            raise FileExistsError(f"immutable environment report exists: {output}")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0 if report["verdict"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
