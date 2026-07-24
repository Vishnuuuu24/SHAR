#!/usr/bin/env python3
"""Materialize local real-UCF P1B Test manifests and frozen evaluation views.

This is deterministic data preparation, not model training or evaluation.  It
uses the completed P0A inventory's file digests and the verified P0B mapping
rules, and writes licensed filename manifests only to a Git-ignored run folder.
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
from data.ucf_intervals import parse_kaggle_frame_relative_path, parse_official_temporal_annotations
from data.views import UCF_SOURCE_DATASET, build_ucf_evaluation_views
from data.faculty_visual_pack import render_p1b_membership_update


RUN_ID = "p1b-real-views-57f3a29b-3b954241"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_manifest(path: Path, rows: tuple[ManifestRow, ...]) -> str:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=MANIFEST_FIELDS, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            values = row.to_dict()
            values["source_frame_index"] = "" if values["source_frame_index"] is None else values["source_frame_index"]
            interval = values["inside_official_interval"]
            values["inside_official_interval"] = "" if interval is None else str(interval).lower()
            writer.writerow(values)
    return _sha256(path)


def _load_test_rows(inventory_path: Path, annotations: dict) -> tuple[ManifestRow, ...]:
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
            if reference.split != "test":
                continue
            if reference.label == "Normal":
                membership = None
            else:
                annotation = annotations.get(reference.source_video_id)
                if annotation is None or annotation.label != reference.label:
                    raise ValueError(f"missing/mismatched official annotation for {reference.filepath}")
                membership = annotation.contains(reference.source_frame_index)
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
                    inside_official_interval=membership,
                    split="test",
                    file_digest=record["sha256"],
                )
            )
    if not rows:
        raise ValueError("inventory did not yield any UCF Test rows")
    return tuple(rows)


def main() -> int:
    config_path = REPO_ROOT / "configs/p1b_views.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    inventory_path = REPO_ROOT / config["inventory_csv_gz"]
    mapping_path = REPO_ROOT / config["p0b_mapping_report"]
    annotation_path = REPO_ROOT / config["official_annotation_text"]
    mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
    annotation_digest = _sha256(annotation_path)
    if (
        mapping.get("ready_for_manifest_materialization") is not True
        or mapping.get("official_annotation_sha256") != annotation_digest
        or mapping.get("source_dataset") != UCF_SOURCE_DATASET
        or mapping.get("mapped_by_outer_split", {}).get("test") != 111308
    ):
        raise ValueError("P0B report is not valid for P1B real-manifest materialization")
    annotations = parse_official_temporal_annotations(annotation_path)
    rows = _load_test_rows(inventory_path, annotations)
    if len(rows) != mapping["mapped_by_outer_split"]["test"]:
        raise ValueError(f"Test-row count {len(rows)} disagrees with P0B mapping report")
    views = build_ucf_evaluation_views(
        rows,
        official_annotation_version=config["annotation_version"],
        official_annotation_digest=annotation_digest,
    )
    if not views.report["ready_for_real_evaluation"]:
        raise ValueError("P1B views are not ready for real evaluation")

    lifecycle = RunLifecycle.create(
        REPO_ROOT / "results/p1b",
        RUN_ID,
        {
            "run_id": RUN_ID,
            "run_kind": "materialization",
            "config_digest": _sha256(config_path),
            "code_revision": "local P1B manifest materializer; no model execution",
            "seed": 0,
            "package_versions": {"python": sys.version.split()[0], "PyYAML": yaml.__version__},
            "dataset_manifest_digest": views.report["source_manifest_sha256"],
            "annotation_version": config["annotation_version"],
            "environment_digest": _sha256(REPO_ROOT / "requirements/p0c-lock.txt"),
            "hardware": {"device": "CPU metadata materialization; no model execution"},
            "metric_artifact_paths": ["aggregate.json", "verdict.json", "view_report.json"],
        },
    )
    started = datetime.now(timezone.utc)
    source_digest = _write_manifest(lifecycle.run_directory / "source_test_manifest.csv", rows)
    event_digest = _write_manifest(lifecycle.run_directory / "event_only_test_manifest.csv", views.event_only)
    noisy_digest = _write_manifest(lifecycle.run_directory / "noisy_proxy_test_manifest.csv", views.noisy_proxy)
    report = {
        **views.report,
        "kind": "P1B real UCF manifest and evaluation-view materialization; not model evaluation",
        "p0b_mapping_report": config["p0b_mapping_report"],
        "p0b_mapping_report_sha256": _sha256(mapping_path),
        "inventory_csv_gz": config["inventory_csv_gz"],
        "inventory_csv_gz_sha256": _sha256(inventory_path),
        "output_manifest_sha256": {
            "source_test_manifest.csv": source_digest,
            "event_only_test_manifest.csv": event_digest,
            "noisy_proxy_test_manifest.csv": noisy_digest,
        },
        "scope_assertions": {
            "model_training": False,
            "headline_evaluation": False,
            "metric_claim_made": False,
            "raw_redistribution_authorized": False,
        },
    }
    (lifecycle.run_directory / "view_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    finished = datetime.now(timezone.utc)
    lifecycle.append_attempt(
        {
            "attempt_id": "materialize-test-views",
            "seed": 0,
            "status": "COMPLETED",
            "started_at": started.isoformat(),
            "finished_at": finished.isoformat(),
            "reason": "Verified P0A inventory plus P0B mapping materialized real Test manifests/views; no model execution",
            "hardware": {"device": "CPU metadata materialization"},
            "parent_checkpoint": None,
            "artifact_digest": _sha256(lifecycle.run_directory / "view_report.json"),
            "artifact_path": "view_report.json",
        }
    )
    lifecycle.finalize(
        report,
        {
            "status": "COMPLETED",
            "verdict": "GOOD_ENOUGH",
            "claim_state": "NOT_APPLICABLE",
            "reason": "Real P1B manifests and frozen membership views materialized with zero unresolved intervals; no model result exists.",
            "next_action": "Register grouped train/validation manifests before P1C training; render the D-25 P1B membership preview.",
            "runtime_seconds": (finished - started).total_seconds(),
            "peak_memory_bytes": 0,
            "storage_bytes": sum(path.stat().st_size for path in lifecycle.run_directory.iterdir() if path.is_file()),
            "stop_reason": "P1B Test-view materialization completed",
            "checkpoint_disposition": "not applicable; no model execution",
            "summary_artifact_digest": artifact_digest(report),
        },
    )
    render_p1b_membership_update(
        REPO_ROOT,
        REPO_ROOT / "configs/faculty_progress_visual_pack.yaml",
        lifecycle.run_directory,
    )
    print(lifecycle.run_directory)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
