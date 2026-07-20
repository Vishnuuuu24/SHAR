#!/usr/bin/env python3
"""Run a short synthetic ResNet50 MPS training-path calibration for P0C."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import psutil
import torch
import torchvision

from core.device import assert_tensor_device, select_device
from core.reproducibility import seed_everything


def mps_memory() -> dict[str, int | None]:
    values: dict[str, int | None] = {}
    for name in ("current_allocated_memory", "driver_allocated_memory", "recommended_max_memory"):
        function = getattr(torch.mps, name, None)
        try:
            values[name] = int(function()) if function else None
        except RuntimeError:
            values[name] = None
    return values


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--warmup-steps", type=int, default=5)
    parser.add_argument("--measure-steps", type=int, default=20)
    parser.add_argument("--output-root", type=Path, default=REPO_ROOT / "results/p0c")
    args = parser.parse_args()
    if min(args.batch_size, args.warmup_steps, args.measure_steps) <= 0:
        parser.error("batch size and step counts must be positive")

    device, device_report = select_device(prefer_mps=True, allow_cpu_fallback=False)
    determinism = seed_everything(0, deterministic=True, warn_only=False)
    model = torchvision.models.resnet50(weights=None)
    model.fc = torch.nn.Linear(model.fc.in_features, 14)
    model = model.to(device).train()
    inputs = torch.randn(args.batch_size, 3, 64, 64, device=device)
    targets = torch.arange(args.batch_size, device=device) % 14
    optimizer = torch.optim.SGD(model.parameters(), lr=0.01)
    process = psutil.Process()
    rss_before = process.memory_info().rss
    memory_before = mps_memory()

    durations: list[float] = []
    losses: list[float] = []
    total_steps = args.warmup_steps + args.measure_steps
    started_at = datetime.now(timezone.utc)
    for step in range(total_steps):
        torch.mps.synchronize()
        started = time.perf_counter()
        optimizer.zero_grad(set_to_none=True)
        logits = model(inputs)
        loss = torch.nn.functional.cross_entropy(logits, targets)
        loss.backward()
        optimizer.step()
        torch.mps.synchronize()
        elapsed = time.perf_counter() - started
        assert_tensor_device(logits, device)
        if step >= args.warmup_steps:
            durations.append(elapsed)
            losses.append(float(loss.detach().cpu()))

    rss_after = process.memory_info().rss
    memory_after = mps_memory()
    median_step = statistics.median(durations)
    p90_step = sorted(durations)[max(0, int(len(durations) * 0.9) - 1)]
    parameter_count = sum(parameter.numel() for parameter in model.parameters())
    parameter_bytes = sum(parameter.numel() * parameter.element_size() for parameter in model.parameters())
    lock_path = REPO_ROOT / "requirements/p0c-lock.txt"
    config = {
        "batch_size": args.batch_size,
        "input_shape": [args.batch_size, 3, 64, 64],
        "classes": 14,
        "precision": "float32",
        "warmup_steps": args.warmup_steps,
        "measure_steps": args.measure_steps,
        "seed": 0,
        "model": "torchvision.models.resnet50(weights=None) with 14-logit linear head",
        "optimizer": "SGD(lr=0.01, momentum=0)",
    }
    report = {
        "schema_version": "1.0.0",
        "kind": "P0C synthetic MPS calibration; not a training or research result",
        "started_at_utc": started_at.isoformat(),
        "finished_at_utc": datetime.now(timezone.utc).isoformat(),
        "config": config,
        "config_sha256": hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest(),
        "environment_lock_sha256": hashlib.sha256(lock_path.read_bytes()).hexdigest(),
        "platform": platform.platform(),
        "torch": torch.__version__,
        "torchvision": torchvision.__version__,
        "device": device_report.to_dict(),
        "determinism": determinism.__dict__,
        "model": {
            "parameters": parameter_count,
            "parameter_bytes_float32": parameter_bytes,
            "estimated_model_plus_sgd_state_bytes": parameter_bytes * 2,
        },
        "measurements": {
            "median_step_seconds": median_step,
            "p90_step_seconds": p90_step,
            "min_step_seconds": min(durations),
            "max_step_seconds": max(durations),
            "images_per_second_median": args.batch_size / median_step,
            "loss_first": losses[0],
            "loss_last": losses[-1],
            "process_rss_before_bytes": rss_before,
            "process_rss_after_bytes": rss_after,
            "mps_memory_before": memory_before,
            "mps_memory_after": memory_after,
        },
        "estimate_method": {
            "formula": "remaining_batches * measured_median_step_seconds * overhead_factor",
            "recommended_overhead_factor_range": [1.15, 1.35],
            "example_only_not_a_run_estimate": {
                "batches": 1000,
                "seconds_low": 1000 * median_step * 1.15,
                "seconds_high": 1000 * median_step * 1.35,
            },
            "required_reestimate_threshold": "first full epoch differs by more than 20 percent",
        },
        "scope_assertions": {
            "uses_synthetic_inputs": True,
            "checkpoint_saved": False,
            "research_training": False,
            "headline_result": False,
        },
        "verdict": "PASS",
    }
    artifact_digest = hashlib.sha256(json.dumps(report, sort_keys=True).encode()).hexdigest()
    output_root = args.output_root if args.output_root.is_absolute() else REPO_ROOT / args.output_root
    output = output_root / f"calibration-{artifact_digest[:16]}"
    if output.exists():
        raise FileExistsError(f"immutable calibration already exists: {output}")
    output.mkdir(parents=True)
    (output / "calibration.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
