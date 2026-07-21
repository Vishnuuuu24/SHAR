#!/usr/bin/env python3
"""Fixture-only MPS shape/gradient smoke for P1C control architectures."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import subprocess
import sys
import warnings
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import torch

from core.device import assert_tensor_device, select_device
from core.reproducibility import seed_everything
from core.run_lifecycle import RunLifecycle, artifact_digest, artifact_payload
from models.classifiers import (
    CNNLSTMTemporalBaseline,
    GlobalAverageLinearHead,
    ResNet50C5,
    SameC5MLPHead,
)


SOURCE_PATHS = [
    "core/device.py",
    "core/provenance.py",
    "core/reproducibility.py",
    "core/run_lifecycle.py",
    "models/classifiers.py",
    "scripts/smoke_p1c_models.py",
    "configs/p1c_architecture_freeze.yaml",
    "requirements/p0c-lock.txt",
]


def source_digest() -> str:
    digest = hashlib.sha256()
    for relative in SOURCE_PATHS:
        digest.update(relative.encode())
        digest.update(b"\0")
        digest.update((REPO_ROOT / relative).read_bytes())
        digest.update(b"\n")
    return digest.hexdigest()


def finite_gradients(module: torch.nn.Module) -> bool:
    gradients = [parameter.grad for parameter in module.parameters() if parameter.grad is not None]
    return bool(gradients) and all(torch.isfinite(gradient).all().item() for gradient in gradients)


def main() -> int:
    started_at = datetime.now(timezone.utc)
    device, device_report = select_device(prefer_mps=True, allow_cpu_fallback=False)
    digest = source_digest()
    fixture_choices = {
        "mlp_hidden_dim": 64,
        "temporal_projection_dim": 64,
        "temporal_hidden_dim": 64,
        "temporal_layers": 1,
        "dropout": 0.0,
        "weights": None,
    }
    fixture_digest = hashlib.sha256(
        json.dumps(fixture_choices, sort_keys=True).encode("utf-8")
    ).hexdigest()
    revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, capture_output=True, text=True)
    status = subprocess.run(
        ["git", "status", "--short", "--untracked-files=all"], cwd=REPO_ROOT, capture_output=True, text=True
    )
    run_id = f"p1c-code-smoke-{fixture_digest[:8]}-{digest[:8]}"
    lifecycle = RunLifecycle.create(
        REPO_ROOT / "results/p1c",
        run_id,
        {
            "run_id": run_id,
            "run_kind": "code_smoke",
            "config_digest": hashlib.sha256(
                (REPO_ROOT / "configs/p1c_architecture_freeze.yaml").read_bytes()
            ).hexdigest(),
            "code_revision": (
                f"HEAD={revision.stdout.strip() if revision.returncode == 0 else 'unavailable'};"
                f"source_bundle_sha256={digest};"
                f"worktree_dirty={str(bool(status.stdout.strip()) if status.returncode == 0 else True).lower()}"
            ),
            "seed": 0,
            "package_versions": {
                "torch": importlib.metadata.version("torch"),
                "torchvision": importlib.metadata.version("torchvision"),
            },
            "dataset_manifest_digest": fixture_digest,
            "annotation_version": "not-applicable-fixture",
            "environment_digest": hashlib.sha256(
                (REPO_ROOT / "requirements/p0c-lock.txt").read_bytes()
            ).hexdigest(),
            "hardware": device_report.to_dict(),
            "metric_artifact_paths": ["aggregate.json", "verdict.json"],
        },
    )
    seed_everything(0)
    backbone = ResNet50C5(weights=None).to(device).eval()
    linear = GlobalAverageLinearHead(2048, 14).to(device).eval()
    mlp = SameC5MLPHead(2048, hidden_dim=64, num_classes=14, dropout=0.0).to(device).eval()
    images = torch.randn(2, 3, 64, 64, device=device)
    c5 = backbone(images)
    assert_tensor_device(c5, device)
    linear_logits = linear(c5)
    mlp_logits = mlp(c5)
    (linear_logits.sum() + mlp_logits.sum()).backward()
    frame_gradients_finite = finite_gradients(backbone) and finite_gradients(linear) and finite_gradients(mlp)
    backbone.zero_grad(set_to_none=True)

    temporal = CNNLSTMTemporalBaseline(
        backbone,
        projection_dim=64,
        hidden_dim=64,
        num_layers=1,
        num_classes=14,
        dropout=0.0,
    ).to(device).eval()
    clips = torch.randn(1, 2, 3, 64, 64, device=device)
    temporal_logits = temporal(clips, torch.tensor([2]), ["fixture-video"])
    assert_tensor_device(temporal_logits, device)
    strict_determinism_error = None
    strict_started = datetime.now(timezone.utc)
    try:
        temporal_logits.sum().backward()
    except RuntimeError as exc:
        if "does not have a deterministic implementation" not in str(exc):
            raise
        strict_determinism_error = str(exc)
    strict_finished = datetime.now(timezone.utc)
    temporal.zero_grad(set_to_none=True)
    seed_everything(0, deterministic=True, warn_only=True)
    warn_started = datetime.now(timezone.utc)
    with warnings.catch_warnings(record=True) as captured_warnings:
        warnings.simplefilter("always")
        temporal_logits = temporal(clips, torch.tensor([2]), ["fixture-video"])
        temporal_logits.sum().backward()
    torch.mps.synchronize()
    warn_finished = datetime.now(timezone.utc)
    report = {
        "schema_version": "1.0.0",
        "kind": "P1C architecture code smoke; not a training or research result",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_paths": SOURCE_PATHS,
        "source_bundle_sha256": digest,
        "device": device_report.to_dict(),
        "fixture_choices_not_experiment_freeze": fixture_choices,
        "shapes": {
            "c5": list(c5.shape),
            "gap_linear_logits": list(linear_logits.shape),
            "same_c5_mlp_logits": list(mlp_logits.shape),
            "temporal_logits": list(temporal_logits.shape),
        },
        "checks": {
            "c5_is_spatial": c5.ndim == 4 and c5.shape[1] == 2048,
            "frame_heads_receive_same_c5": True,
            "frame_heads_14_logits": linear_logits.shape == mlp_logits.shape == (2, 14),
            "temporal_14_logits": temporal_logits.shape == (1, 14),
            "frame_gradients_finite": frame_gradients_finite,
            "temporal_gradients_finite": finite_gradients(temporal),
            "temporal_strict_determinism": strict_determinism_error is None,
            "temporal_warn_only_mps_execution": finite_gradients(temporal),
            "cpu_fallback_allowed": device_report.cpu_fallback_allowed,
        },
        "compatibility": {
            "temporal_strict_determinism_error": strict_determinism_error,
            "warn_only_warnings": [str(item.message) for item in captured_warnings],
            "full_run_decision_required": strict_determinism_error is not None,
        },
        "parameter_counts": {
            "backbone": sum(parameter.numel() for parameter in backbone.parameters()),
            "gap_linear_head": sum(parameter.numel() for parameter in linear.parameters()),
            "same_c5_mlp_head_fixture": sum(parameter.numel() for parameter in mlp.parameters()),
            "temporal_fixture_including_shared_backbone": sum(parameter.numel() for parameter in temporal.parameters()),
        },
        "scope_assertions": {
            "pretrained_weights_downloaded": False,
            "real_data_used": False,
            "model_training": False,
            "headline_evaluation": False,
            "research_claim": False,
        },
    }
    required_code_checks = [
        "c5_is_spatial",
        "frame_heads_receive_same_c5",
        "frame_heads_14_logits",
        "temporal_14_logits",
        "frame_gradients_finite",
        "temporal_gradients_finite",
        "temporal_warn_only_mps_execution",
    ]
    code_pass = all(report["checks"][key] is True for key in required_code_checks)
    code_pass = code_pass and report["checks"]["cpu_fallback_allowed"] is False
    report["verdict"] = (
        "PASS_WITH_COMPATIBILITY_BLOCKER"
        if code_pass and strict_determinism_error is not None
        else ("PASS" if code_pass else "FAIL")
    )
    attempts = [
        {
            "attempt_id": "strict-mps-1",
            "seed": 0,
            "status": "FAILED" if strict_determinism_error is not None else "COMPLETED",
            "started_at": strict_started.isoformat(),
            "finished_at": strict_finished.isoformat(),
            "reason": "strict deterministic MPS temporal backward compatibility probe",
            "hardware": device_report.to_dict(),
            "parent_checkpoint": None,
            "artifact_digest": artifact_digest(report),
            "artifact_path": "aggregate.json",
        },
        {
            "attempt_id": "warn-only-mps-1",
            "seed": 0,
            "status": "COMPLETED",
            "started_at": warn_started.isoformat(),
            "finished_at": warn_finished.isoformat(),
            "reason": "explicit warn-only MPS temporal gradient compatibility probe",
            "hardware": device_report.to_dict(),
            "parent_checkpoint": None,
            "artifact_digest": artifact_digest(report),
            "artifact_path": "aggregate.json",
        },
    ]
    for attempt in attempts:
        lifecycle.append_attempt(attempt)
    finished_at = datetime.now(timezone.utc)
    lifecycle.finalize(
        report,
        {
            "status": "COMPLETED",
            "verdict": "GOOD_ENOUGH" if code_pass else "INCONCLUSIVE",
            "claim_state": "NOT_APPLICABLE",
            "reason": "Architecture fixture checks completed; strict MPS temporal determinism remains a compatibility blocker.",
            "next_action": "Resolve B-006 before any temporal full run.",
            "runtime_seconds": (finished_at - started_at).total_seconds(),
            "peak_memory_bytes": int(torch.mps.driver_allocated_memory()),
            "storage_bytes": len(artifact_payload(report)),
            "stop_reason": "fixture checks completed",
            "checkpoint_disposition": "not applicable; no training checkpoint produced",
            "summary_artifact_digest": artifact_digest(report),
        },
    )
    print(lifecycle.run_directory)
    return 0 if report["verdict"].startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
