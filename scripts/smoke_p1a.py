#!/usr/bin/env python3
"""Close an immutable fixture-only P1A framework smoke artifact."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import yaml

from core.run_lifecycle import RunLifecycle, artifact_digest
from data.grouping import SourceGroupedSampler, source_grouped_split
from data.manifest import load_manifest
from eval.metrics import classification_metrics, video_clustered_macro_f1_ci


SOURCE_PATHS = [
    "core/provenance.py",
    "core/run_lifecycle.py",
    "data/contracts.py",
    "data/grouping.py",
    "data/manifest.py",
    "eval/metrics.py",
    "scripts/smoke_p1a.py",
]


def source_bundle_digest() -> str:
    digest = hashlib.sha256()
    for relative in SOURCE_PATHS:
        path = REPO_ROOT / relative
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\n")
    return digest.hexdigest()


def code_revision(source_digest: str) -> str:
    result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, capture_output=True, text=True)
    head = result.stdout.strip() if result.returncode == 0 else "unavailable"
    status = subprocess.run(
        ["git", "status", "--short", "--untracked-files=all"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    dirty = bool(status.stdout.strip()) if status.returncode == 0 else True
    return f"HEAD={head};source_bundle_sha256={source_digest};worktree_dirty={str(dirty).lower()}"


def main() -> int:
    config_path = REPO_ROOT / "configs/p1a_framework.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    fixture_root = REPO_ROOT / "tests/fixtures/p1a"
    manifest_path = fixture_root / "manifest.csv"
    manifest_digest = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    source_digest = source_bundle_digest()
    environment_digest = hashlib.sha256((REPO_ROOT / "requirements/p0c-lock.txt").read_bytes()).hexdigest()
    run_id = f"p1a-framework-smoke-{manifest_digest[:8]}-{source_digest[:8]}"
    provenance = {
        "run_id": run_id,
        "run_kind": "smoke",
        "config_digest": hashlib.sha256(config_path.read_bytes()).hexdigest(),
        "code_revision": code_revision(source_digest),
        "seed": config["validation"]["seed"],
        "package_versions": {
            "numpy": importlib.metadata.version("numpy"),
            "PyYAML": importlib.metadata.version("PyYAML"),
            "torch": importlib.metadata.version("torch"),
        },
        "dataset_manifest_digest": manifest_digest,
        "annotation_version": "fixture-v1",
        "environment_digest": environment_digest,
        "hardware": {"device": "fixture-only; no model execution"},
        "metric_artifact_paths": ["aggregate.json", "verdict.json"],
    }
    lifecycle = RunLifecycle.create(REPO_ROOT / "results/p1a", run_id, provenance)
    rows = load_manifest(manifest_path, {"fixture": fixture_root}, verify_files=True, verify_digests=True)
    split = source_grouped_split(rows, validation_fraction=0.5, seed=config["validation"]["seed"])
    sampler_indices = list(SourceGroupedSampler(rows, split.train_indices, seed=0, shuffle=True))
    truth = ["Abuse", "Abuse", "Normal", "Normal"]
    prediction = ["Abuse", "Normal", "Normal", "Normal"]
    videos = ["A1", "A2", "N1", "N2"]
    metrics = classification_metrics(truth, prediction, ["Abuse", "Normal"])
    metrics["video_clustered_macro_f1_ci"] = video_clustered_macro_f1_ci(
        truth, prediction, videos, ["Abuse", "Normal"], iterations=200, seed=0
    )
    aggregate = {
        "kind": "P1A fixture smoke; not a research result",
        "manifest_rows": len(rows),
        "manifest_digest": manifest_digest,
        "source_bundle_paths": SOURCE_PATHS,
        "source_bundle_sha256": source_digest,
        "train_indices": split.train_indices,
        "validation_indices": split.validation_indices,
        "class_counts": split.class_counts,
        "zero_group_leakage": not (
            {
                (rows[index].source_dataset, rows[index].source_video_id) for index in split.train_indices
            }
            & {
                (rows[index].source_dataset, rows[index].source_video_id) for index in split.validation_indices
            }
        ),
        "sampler_indices": sampler_indices,
        "metrics_fixture": metrics,
        "scope_assertions": {
            "real_ucf_manifest": False,
            "interval_mapping": False,
            "model_training": False,
            "headline_evaluation": False,
        },
    }
    started_at = datetime.now(timezone.utc)
    finished_at = datetime.now(timezone.utc)
    lifecycle.append_attempt(
        {
            "attempt_id": "fixture-1",
            "seed": 0,
            "status": "COMPLETED",
            "started_at": started_at.isoformat(),
            "finished_at": finished_at.isoformat(),
            "reason": "P1A fixture-only framework verification; no training",
            "hardware": {"device": "fixture-only"},
            "parent_checkpoint": None,
            "artifact_digest": artifact_digest(aggregate),
            "artifact_path": "aggregate.json",
        }
    )
    lifecycle.finalize(
        aggregate,
        {
            "status": "COMPLETED",
            "verdict": "GOOD_ENOUGH",
            "claim_state": "NOT_APPLICABLE",
            "reason": "All P1A fixture framework checks completed; no research claim was evaluated.",
            "next_action": "Close P1A after full test verification; P1B real completion remains blocked by B-001.",
            "runtime_seconds": (finished_at - started_at).total_seconds(),
            "peak_memory_bytes": 0,
            "storage_bytes": 0,
            "stop_reason": "fixture checks completed",
            "checkpoint_disposition": "not applicable; no model execution",
            "summary_artifact_digest": artifact_digest(aggregate),
        },
    )
    print(lifecycle.run_directory)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
