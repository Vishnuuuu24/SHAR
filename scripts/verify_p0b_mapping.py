#!/usr/bin/env python3
"""Build a P0B mapping/quarantine report; this command never writes a manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from data.ucf_intervals import (
    annotation_sha256,
    iter_kaggle_frame_references,
    parse_official_temporal_annotations,
)


REQUIRED_CONFIG = {
    "schema_version": "1.0.0",
    "source_dataset": "ucf_crime_kaggle_frames",
    "interval_coordinate_system": "official_source_video_frame_index",
    "interval_boundary_semantics": "inclusive_start_inclusive_end",
    "quarantine_policy": "exclude_from_any_manifest_until_resolved",
}


def _configured_path(value: object, field: str) -> Path:
    if not isinstance(value, str) or not value:
        raise ValueError(f"P0B config {field} must be a non-empty relative path")
    candidate = (REPO_ROOT / value).resolve()
    try:
        candidate.relative_to(REPO_ROOT)
    except ValueError as exc:
        raise ValueError(f"P0B config {field} escapes repository root") from exc
    return candidate


def load_config(path: Path) -> dict:
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(config, dict):
        raise ValueError("P0B config must be a mapping")
    for key, expected in REQUIRED_CONFIG.items():
        if config.get(key) != expected:
            raise ValueError(f"P0B config {key} must equal {expected!r}")
    gates = config.get("gates")
    if not isinstance(gates, dict) or not gates.get("require_zero_source_video_split_leakage") or not gates.get(
        "require_zero_quarantined_frames"
    ):
        raise ValueError("P0B config must fail closed on leakage and quarantined frames")
    return config


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=REPO_ROOT / "configs/p0b_mapping.yaml")
    parser.add_argument("--report", type=Path, required=True, help="JSON report path; no manifest is created")
    args = parser.parse_args()

    config_path = args.config.resolve()
    config = load_config(config_path)
    frame_root = _configured_path(config.get("frame_root"), "frame_root")
    annotation_path = _configured_path(config.get("official_annotation_text"), "official_annotation_text")
    if not frame_root.is_dir() or not annotation_path.is_file():
        raise FileNotFoundError("configured P0B frame root or official annotation text is unavailable")

    annotations = parse_official_temporal_annotations(annotation_path)
    entries = iter_kaggle_frame_references(frame_root)
    from data.ucf_intervals import stream_map_ucf_frame_references

    result = stream_map_ucf_frame_references(entries, annotations)
    report = result.report()
    report.update(
        {
            "source_dataset": config["source_dataset"],
            "annotation_version": config.get("annotation_version"),
            "official_annotation_sha256": annotation_sha256(annotation_path),
            "p0b_config_sha256": hashlib.sha256(config_path.read_bytes()).hexdigest(),
            "frame_root": frame_root.relative_to(REPO_ROOT).as_posix(),
            "official_annotation_text": annotation_path.relative_to(REPO_ROOT).as_posix(),
        }
    )
    report_path = args.report.resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=report_path.parent, delete=False) as handle:
        handle.write(json.dumps(report, indent=2, sort_keys=True) + "\n")
        temporary_path = Path(handle.name)
    temporary_path.replace(report_path)
    result.assert_ready_for_manifest_materialization()
    print(report_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
