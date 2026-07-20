"""Append-preserving attempt stream and immutable run closure for P1A."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.provenance import finalize_provenance, validate_provenance


ATTEMPT_FIELDS = {
    "attempt_id",
    "seed",
    "status",
    "started_at",
    "finished_at",
    "reason",
    "hardware",
    "parent_checkpoint",
    "artifact_digest",
}
FINAL_STATUSES = {"COMPLETED", "FAILED", "ABORTED", "INVALID"}
SHA256_LENGTH = 64
FINAL_VERDICT_FIELDS = {
    "status",
    "verdict",
    "claim_state",
    "reason",
    "next_action",
    "runtime_seconds",
    "peak_memory_bytes",
    "storage_bytes",
    "stop_reason",
    "checkpoint_disposition",
    "summary_artifact_digest",
}
STATUS_VERDICTS = {
    "COMPLETED": {"GOOD", "GOOD_ENOUGH", "BAD", "INCONCLUSIVE"},
    "FAILED": {"PENDING", "INCONCLUSIVE"},
    "ABORTED": {"PENDING", "INCONCLUSIVE"},
    "INVALID": {"INVALID"},
}
CLAIM_STATES = {"SUPPORTED", "NOT_SUPPORTED", "INCONCLUSIVE", "NOT_APPLICABLE"}


def artifact_payload(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def artifact_digest(value: dict[str, Any]) -> str:
    import hashlib

    return hashlib.sha256(artifact_payload(value)).hexdigest()


class RunLifecycle:
    def __init__(self, run_directory: Path):
        self.run_directory = run_directory
        self.manifest_path = run_directory / "run_manifest.json"
        self.attempts_path = run_directory / "attempts.jsonl"
        self.complete_marker = run_directory / ".complete"

    @classmethod
    def create(cls, root: Path, run_id: str, provenance: dict[str, Any]) -> "RunLifecycle":
        if provenance.get("run_id") != run_id:
            raise ValueError("run_id must match provenance run_id")
        issues = validate_provenance(provenance)
        if issues:
            raise ValueError("; ".join(issues))
        directory = root / run_id
        if directory.exists():
            raise FileExistsError(f"run already exists: {directory}")
        directory.mkdir(parents=True)
        lifecycle = cls(directory)
        finalize_provenance(provenance, lifecycle.manifest_path)
        lifecycle.attempts_path.touch(exist_ok=False)
        return lifecycle

    def _assert_mutable(self) -> None:
        if self.complete_marker.exists():
            raise RuntimeError(f"completed run is immutable: {self.run_directory}")

    def append_attempt(self, attempt: dict[str, Any]) -> None:
        self._assert_mutable()
        missing = ATTEMPT_FIELDS - set(attempt)
        if missing:
            raise ValueError(f"attempt missing fields: {sorted(missing)}")
        if attempt["status"] not in {"RUNNING", *FINAL_STATUSES}:
            raise ValueError("attempt status is not registered")
        if not isinstance(attempt["seed"], int) or isinstance(attempt["seed"], bool):
            raise ValueError("attempt seed must be an integer")
        for field in ("started_at", "reason"):
            if not isinstance(attempt[field], str) or not attempt[field]:
                raise ValueError(f"attempt {field} must be a non-empty string")
        if not isinstance(attempt["hardware"], dict):
            raise ValueError("attempt hardware must be an object")
        if attempt["parent_checkpoint"] is not None and not isinstance(attempt["parent_checkpoint"], str):
            raise ValueError("attempt parent_checkpoint must be null or a string")
        if attempt["status"] == "RUNNING":
            if attempt["finished_at"] is not None or attempt["artifact_digest"] is not None:
                raise ValueError("RUNNING attempt cannot have finish time or artifact digest")
        else:
            if not isinstance(attempt["finished_at"], str) or not attempt["finished_at"]:
                raise ValueError("final attempt requires finished_at")
            digest = attempt["artifact_digest"]
            if not isinstance(digest, str) or len(digest) != SHA256_LENGTH:
                raise ValueError("final attempt requires a SHA-256 artifact_digest")
        existing_ids = {
            json.loads(line)["attempt_id"]
            for line in self.attempts_path.read_text(encoding="utf-8").splitlines()
            if line
        }
        if attempt["attempt_id"] in existing_ids:
            raise ValueError(f"duplicate attempt_id: {attempt['attempt_id']}")
        payload = json.dumps(attempt, sort_keys=True) + "\n"
        descriptor = os.open(self.attempts_path, os.O_WRONLY | os.O_APPEND)
        try:
            os.write(descriptor, payload.encode("utf-8"))
            os.fsync(descriptor)
        finally:
            os.close(descriptor)

    def finalize(self, aggregate: dict[str, Any], verdict: dict[str, Any]) -> None:
        self._assert_mutable()
        attempts = [
            json.loads(line)
            for line in self.attempts_path.read_text(encoding="utf-8").splitlines()
            if line
        ]
        if not attempts:
            raise ValueError("cannot finalize a run with no attempts")
        if any(attempt["status"] == "RUNNING" for attempt in attempts):
            raise ValueError("cannot finalize while an attempt is RUNNING")
        missing = FINAL_VERDICT_FIELDS - set(verdict)
        if missing:
            raise ValueError(f"verdict missing closure fields: {sorted(missing)}")
        status = verdict["status"]
        if status not in STATUS_VERDICTS or verdict["verdict"] not in STATUS_VERDICTS[status]:
            raise ValueError("status/verdict combination is not registered")
        if verdict["claim_state"] not in CLAIM_STATES:
            raise ValueError("claim_state is not registered")
        for field in ("reason", "next_action", "stop_reason", "checkpoint_disposition"):
            if not isinstance(verdict[field], str) or not verdict[field]:
                raise ValueError(f"verdict {field} must be a non-empty string")
        if not isinstance(verdict["runtime_seconds"], (int, float)) or verdict["runtime_seconds"] < 0:
            raise ValueError("runtime_seconds must be non-negative")
        for field in ("peak_memory_bytes", "storage_bytes"):
            if not isinstance(verdict[field], int) or isinstance(verdict[field], bool) or verdict[field] < 0:
                raise ValueError(f"{field} must be a non-negative integer")
        aggregate_digest = artifact_digest(aggregate)
        if verdict["summary_artifact_digest"] != aggregate_digest:
            raise ValueError("summary_artifact_digest does not match aggregate.json")
        for name, value in (("aggregate.json", aggregate), ("verdict.json", verdict)):
            path = self.run_directory / name
            if path.exists():
                raise FileExistsError(f"final artifact exists: {path}")
            path.write_bytes(artifact_payload(value))
        self.complete_marker.write_text(
            json.dumps({"completed_at": datetime.now(timezone.utc).isoformat()}, sort_keys=True) + "\n",
            encoding="utf-8",
        )
