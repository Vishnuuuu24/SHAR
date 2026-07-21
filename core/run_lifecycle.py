"""Append-preserving attempt stream and immutable run closure for P1A."""

from __future__ import annotations

import json
import hashlib
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
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
    "artifact_path",
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
    return hashlib.sha256(artifact_payload(value)).hexdigest()


def _atomic_write_or_verify(path: Path, payload: bytes) -> None:
    """Write one closure component atomically, or verify a recoverable partial write."""
    if path.exists():
        if path.read_bytes() != payload:
            raise FileExistsError(f"existing final artifact differs: {path}")
        return
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


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
            if (
                attempt["finished_at"] is not None
                or attempt["artifact_digest"] is not None
                or attempt["artifact_path"] is not None
            ):
                raise ValueError("RUNNING attempt cannot have finish time or artifact reference")
        else:
            if not isinstance(attempt["finished_at"], str) or not attempt["finished_at"]:
                raise ValueError("final attempt requires finished_at")
            digest = attempt["artifact_digest"]
            if not isinstance(digest, str) or len(digest) != SHA256_LENGTH:
                raise ValueError("final attempt requires a SHA-256 artifact_digest")
            artifact_path = attempt["artifact_path"]
            if not isinstance(artifact_path, str) or not artifact_path:
                raise ValueError("final attempt requires artifact_path")
            pure = PurePosixPath(artifact_path)
            if (
                pure.is_absolute()
                or ".." in pure.parts
                or "\\" in artifact_path
                or pure.as_posix() != artifact_path
            ):
                raise ValueError("artifact_path must be a canonical relative POSIX path")
        existing_events = [
            json.loads(line)
            for line in self.attempts_path.read_text(encoding="utf-8").splitlines()
            if line
        ]
        latest_by_id: dict[str, dict[str, Any]] = {}
        for event in existing_events:
            latest_by_id[event["attempt_id"]] = event
        previous = latest_by_id.get(attempt["attempt_id"])
        if previous is not None:
            if previous["status"] != "RUNNING" or attempt["status"] == "RUNNING":
                raise ValueError(f"attempt_id is already final: {attempt['attempt_id']}")
            for field in ("seed", "started_at", "parent_checkpoint"):
                if attempt[field] != previous[field]:
                    raise ValueError(f"attempt transition changed immutable field: {field}")
        payload = json.dumps(attempt, sort_keys=True) + "\n"
        descriptor = os.open(self.attempts_path, os.O_WRONLY | os.O_APPEND)
        try:
            os.write(descriptor, payload.encode("utf-8"))
            os.fsync(descriptor)
        finally:
            os.close(descriptor)

    def finalize(self, aggregate: dict[str, Any], verdict: dict[str, Any]) -> None:
        self._assert_mutable()
        attempt_events = [
            json.loads(line)
            for line in self.attempts_path.read_text(encoding="utf-8").splitlines()
            if line
        ]
        if not attempt_events:
            raise ValueError("cannot finalize a run with no attempts")
        latest_attempts: dict[str, dict[str, Any]] = {}
        for event in attempt_events:
            latest_attempts[event["attempt_id"]] = event
        if any(attempt["status"] == "RUNNING" for attempt in latest_attempts.values()):
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
            _atomic_write_or_verify(self.run_directory / name, artifact_payload(value))
        for attempt in latest_attempts.values():
            artifact_path = self.run_directory / attempt["artifact_path"]
            if not artifact_path.is_file():
                raise ValueError(f"attempt artifact does not exist: {attempt['artifact_path']}")
            actual_digest = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
            if actual_digest != attempt["artifact_digest"]:
                raise ValueError(
                    f"attempt artifact digest mismatch: {attempt['attempt_id']}"
                )
        closure_names = (
            "run_manifest.json",
            "attempts.jsonl",
            "aggregate.json",
            "verdict.json",
        )
        closure_digests = {
            name: hashlib.sha256((self.run_directory / name).read_bytes()).hexdigest()
            for name in closure_names
        }
        _atomic_write_or_verify(
            self.complete_marker,
            (
                json.dumps(
                    {
                        "schema_version": "2.0.0",
                        "completed_at": datetime.now(timezone.utc).isoformat(),
                        "files_sha256": closure_digests,
                    },
                    sort_keys=True,
                )
                + "\n"
            ).encode("utf-8"),
        )
