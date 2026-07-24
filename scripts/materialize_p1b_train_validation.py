#!/usr/bin/env python3
"""Materialize immutable real-UCF P1B Train/validation manifests.

This is data preparation only.  It consumes P0A's checked frame inventory and
the owner-reaffirmed grouped split policy; it does not read Test rows, execute
a model, or produce an evaluation result.
"""

from __future__ import annotations

import csv
import gzip
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.run_lifecycle import RunLifecycle, artifact_digest
from data.contracts import MANIFEST_FIELDS
from data.manifest import ManifestRow
from data.train_validation import build_ucf_grouped_train_validation
from data.ucf_intervals import parse_kaggle_frame_relative_path
from data.views import UCF_SOURCE_DATASET


RUN_ID = "p1b-grouped-train-validation-57f3a29b-10pct-s0"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_manifest(path: Path, rows: tuple[ManifestRow, ...]) -> str:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=MANIFEST_FIELDS, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            values = row.to_dict()
            values["source_frame_index"] = "" if values["source_frame_index"] is None else values["source_frame_index"]
            values["inside_official_interval"] = ""
            writer.writerow(values)
    return _sha256(path)


def _load_outer_train_rows(inventory_path: Path) -> tuple[ManifestRow, ...]:
    rows: list[ManifestRow] = []
    with gzip.open(inventory_path, "rt", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"dataset_id", "relative_path", "sha256", "status", "width", "height"}
        if reader.fieldnames is None or not required.issubset(reader.fieldnames):
            raise ValueError("inventory CSV lacks required P1B materialization fields")
        for record in reader:
            if record["dataset_id"] != UCF_SOURCE_DATASET:
                continue
            if record["status"] != "ok" or record["width"] != "64" or record["height"] != "64":
                raise ValueError(f"inventory contains invalid UCF frame record: {record['relative_path']}")
            reference = parse_kaggle_frame_relative_path(record["relative_path"])
            if reference.split != "train":
                continue
            rows.append(
                ManifestRow(
                    filepath=reference.filepath,
                    source_dataset=UCF_SOURCE_DATASET,
                    source_video_id=reference.source_video_id,
                    source_frame_index=reference.source_frame_index,
                    label=reference.label,
                    label_scope="video_inherited",
                    label_source="kaggle-folder-mirror",
                    annotation_version="kaggle-folder-mirror-v1",
                    inside_official_interval=None,
                    split="train",
                    file_digest=record["sha256"],
                )
            )
    if not rows:
        raise ValueError("inventory did not yield any UCF outer-Train rows")
    return tuple(rows)


def main() -> int:
    p1b_config_path = REPO_ROOT / "configs/p1b_views.yaml"
    framework_config_path = REPO_ROOT / "configs/p1a_framework.yaml"
    p1b_config = yaml.safe_load(p1b_config_path.read_text(encoding="utf-8"))
    framework_config = yaml.safe_load(framework_config_path.read_text(encoding="utf-8"))
    split_config = framework_config["validation"]
    if split_config != p1b_config["train_validation"]["policy"]:
        raise ValueError("P1B policy copy does not exactly match the frozen P1A split configuration")
    if split_config.get("grouping_key") != "source_video_id":
        raise ValueError("P1B materialization requires source_video_id grouping")
    inventory_path = REPO_ROOT / p1b_config["inventory_csv_gz"]
    rows = _load_outer_train_rows(inventory_path)
    manifests = build_ucf_grouped_train_validation(
        rows,
        validation_fraction=split_config["fraction"],
        seed=split_config["seed"],
    )

    lifecycle = RunLifecycle.create(
        REPO_ROOT / "results/p1b",
        RUN_ID,
        {
            "run_id": RUN_ID,
            "run_kind": "materialization",
            "config_digest": _sha256(p1b_config_path),
            "code_revision": "local P1B grouped Train/validation materializer; no model execution",
            "seed": split_config["seed"],
            "package_versions": {"python": sys.version.split()[0], "PyYAML": yaml.__version__},
            "dataset_manifest_digest": manifests.report["source_manifest_sha256"],
            "annotation_version": "kaggle-folder-mirror-v1; no temporal interval labels used for Train/validation",
            "environment_digest": _sha256(REPO_ROOT / "requirements/p0c-lock.txt"),
            "hardware": {"device": "CPU metadata materialization; no model execution"},
            "metric_artifact_paths": ["aggregate.json", "verdict.json", "allocation_report.json"],
        },
    )
    started = datetime.now(timezone.utc)
    train_digest = _write_manifest(lifecycle.run_directory / "train_manifest.csv", manifests.train)
    validation_digest = _write_manifest(lifecycle.run_directory / "validation_manifest.csv", manifests.validation)
    report = {
        **manifests.report,
        "inventory_csv_gz": p1b_config["inventory_csv_gz"],
        "inventory_csv_gz_sha256": _sha256(inventory_path),
        "p1a_framework_config_sha256": _sha256(framework_config_path),
        "p1b_policy_registration": p1b_config["train_validation"]["registration"],
        "output_manifest_sha256": {"train_manifest.csv": train_digest, "validation_manifest.csv": validation_digest},
        "scope_assertions": {
            "model_training": False,
            "headline_evaluation": False,
            "metric_claim_made": False,
            "test_rows_read": False,
            "raw_redistribution_authorized": False,
        },
        "faculty_render_decision": {
            "rendered": False,
            "reason": "The fixed faculty examples are held-out Test frames; grouped outer-Train allocation adds no visual/model/annotation stage.",
            "next_trigger": "A registered P1C checkpoint or another closed artifact that changes a selected visual stage.",
        },
    }
    (lifecycle.run_directory / "allocation_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    finished = datetime.now(timezone.utc)
    lifecycle.append_attempt(
        {
            "attempt_id": "materialize-grouped-train-validation",
            "seed": split_config["seed"],
            "status": "COMPLETED",
            "started_at": started.isoformat(),
            "finished_at": finished.isoformat(),
            "reason": "Owner-reaffirmed 10% grouped outer-Train allocation materialized; no Test rows or model execution used",
            "hardware": {"device": "CPU metadata materialization"},
            "parent_checkpoint": None,
            "artifact_digest": _sha256(lifecycle.run_directory / "allocation_report.json"),
            "artifact_path": "allocation_report.json",
        }
    )
    lifecycle.finalize(
        report,
        {
            "status": "COMPLETED",
            "verdict": "GOOD_ENOUGH",
            "claim_state": "NOT_APPLICABLE",
            "reason": "Grouped outer-Train manifests closed with zero source-video overlap; no model result exists.",
            "next_action": "Register the P1C architecture/run policy and resolve its MPS determinism choice before a full training run.",
            "runtime_seconds": (finished - started).total_seconds(),
            "peak_memory_bytes": 0,
            "storage_bytes": sum(path.stat().st_size for path in lifecycle.run_directory.iterdir() if path.is_file()),
            "stop_reason": "P1B grouped Train/validation materialization completed",
            "checkpoint_disposition": "not applicable; no model execution",
            "summary_artifact_digest": artifact_digest(report),
        },
    )
    print(lifecycle.run_directory)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
