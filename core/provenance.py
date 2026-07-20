"""Minimal immutable provenance closure used by future run lifecycles."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any


REQUIRED_PROVENANCE_FIELDS = {
    "run_id",
    "run_kind",
    "config_digest",
    "code_revision",
    "seed",
    "package_versions",
    "dataset_manifest_digest",
    "annotation_version",
    "environment_digest",
    "hardware",
    "metric_artifact_paths",
}


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def validate_provenance(record: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    missing = REQUIRED_PROVENANCE_FIELDS - set(record)
    if missing:
        issues.append(f"missing required fields: {sorted(missing)}")
    for field in REQUIRED_PROVENANCE_FIELDS - {"seed", "metric_artifact_paths", "package_versions", "hardware"}:
        if field in record and (not isinstance(record[field], str) or not record[field]):
            issues.append(f"{field} must be a non-empty string")
    if "seed" in record and (isinstance(record["seed"], bool) or not isinstance(record["seed"], int)):
        issues.append("seed must be an integer")
    if "package_versions" in record and not isinstance(record["package_versions"], dict):
        issues.append("package_versions must be an object")
    if "hardware" in record and not isinstance(record["hardware"], dict):
        issues.append("hardware must be an object")
    paths = record.get("metric_artifact_paths")
    if paths is not None and (not isinstance(paths, list) or any(not isinstance(path, str) or not path for path in paths)):
        issues.append("metric_artifact_paths must be a list of non-empty strings")
    return issues


def finalize_provenance(record: dict[str, Any], destination: Path) -> str:
    issues = validate_provenance(record)
    if issues:
        raise ValueError("; ".join(issues))
    if destination.exists():
        raise FileExistsError(f"immutable provenance already exists: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(record, indent=2, sort_keys=True) + "\n"
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{destination.name}.", dir=destination.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
