#!/usr/bin/env python3
"""Create immutable fixture-only evidence for the P1B view builders."""

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

from core.run_lifecycle import RunLifecycle, artifact_digest
from data.manifest import ManifestRow
from data.views import CANONICAL_UCF_LABELS, build_ucf_evaluation_views


SOURCE_PATHS = [
    "core/provenance.py",
    "core/run_lifecycle.py",
    "data/contracts.py",
    "data/manifest.py",
    "data/views.py",
    "scripts/smoke_p1b_views.py",
    "configs/p1b_views.yaml",
    "requirements/p0c-lock.txt",
]


def digest_paths(paths: list[str]) -> str:
    digest = hashlib.sha256()
    for relative in paths:
        digest.update(relative.encode("utf-8") + b"\0")
        digest.update((REPO_ROOT / relative).read_bytes() + b"\n")
    return digest.hexdigest()


def fixture_rows() -> list[ManifestRow]:
    rows: list[ManifestRow] = []
    for label_index, label in enumerate(CANONICAL_UCF_LABELS):
        memberships = (None,) if label == "Normal" else (True, False)
        for frame, inside in enumerate(memberships):
            identity = f"{label}-{label_index}-{frame}"
            rows.append(
                ManifestRow(
                    filepath=f"fixture/{identity}.png",
                    source_dataset="fixture_ucf",
                    source_video_id=f"{label}-video",
                    source_frame_index=frame,
                    label=label,
                    label_scope="video_inherited",
                    label_source="fixture-folder-snapshot",
                    annotation_version="folder-fixture-v1",
                    inside_official_interval=inside,
                    split="test",
                    file_digest=hashlib.sha256(identity.encode("utf-8")).hexdigest(),
                )
            )
    return rows


def main() -> int:
    config_path = REPO_ROOT / "configs/p1b_views.yaml"
    source_digest = digest_paths(SOURCE_PATHS)
    rows = fixture_rows()
    fixture_digest = hashlib.sha256(
        json.dumps([row.to_dict() for row in rows], sort_keys=True).encode("utf-8")
    ).hexdigest()
    revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, capture_output=True, text=True)
    status = subprocess.run(
        ["git", "status", "--short", "--untracked-files=all"], cwd=REPO_ROOT, capture_output=True, text=True
    )
    run_id = f"p1b-view-smoke-{fixture_digest[:8]}-{source_digest[:8]}"
    lifecycle = RunLifecycle.create(
        REPO_ROOT / "results/p1b",
        run_id,
        {
            "run_id": run_id,
            "run_kind": "smoke",
            "config_digest": hashlib.sha256(config_path.read_bytes()).hexdigest(),
            "code_revision": (
                f"HEAD={revision.stdout.strip() if revision.returncode == 0 else 'unavailable'};"
                f"source_bundle_sha256={source_digest};"
                f"worktree_dirty={str(bool(status.stdout.strip()) if status.returncode == 0 else True).lower()}"
            ),
            "seed": 0,
            "package_versions": {"python": sys.version.split()[0], "PyYAML": importlib.metadata.version("PyYAML")},
            "dataset_manifest_digest": fixture_digest,
            "annotation_version": "fixture-v1",
            "environment_digest": hashlib.sha256((REPO_ROOT / "requirements/p0c-lock.txt").read_bytes()).hexdigest(),
            "hardware": {"device": "fixture-only; no model execution"},
            "metric_artifact_paths": ["aggregate.json", "verdict.json"],
        },
    )
    views = build_ucf_evaluation_views(
        rows,
        official_annotation_version="official-fixture-v1",
        official_annotation_digest=hashlib.sha256(b"official-fixture-v1").hexdigest(),
        source_dataset="fixture_ucf",
        allow_fixture_source=True,
        fixture_only=True,
    )
    aggregate = {
        **views.report,
        "source_bundle_paths": SOURCE_PATHS,
        "source_bundle_sha256": source_digest,
        "scope_assertions": {
            "real_ucf_manifest": False,
            "official_interval_mapping": False,
            "headline_evaluation": False,
            "model_training": False,
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
            "reason": "P1B fixture-only view-membership verification; no real UCF manifest or evaluation",
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
            "reason": "Fixture membership rules passed; this is not P1B real-data completion.",
            "next_action": "Acquire/register official UCF temporal annotations and complete P0B before real P1B manifests.",
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
