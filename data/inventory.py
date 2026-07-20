"""Deterministic, content-addressed local dataset inventory."""

from __future__ import annotations

import csv
import gzip
import hashlib
import itertools
import json
import os
import shutil
import struct
import subprocess
import tempfile
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Iterator

from data.contracts import (
    load_json,
    validate_access_registry,
    validate_manifest_schema,
    validate_task_contract,
)


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
CSV_FIELDS = [
    "dataset_id",
    "component_id",
    "relative_path",
    "size_bytes",
    "sha256",
    "extension",
    "width",
    "height",
    "status",
    "error",
]


@dataclass(frozen=True)
class FileItem:
    dataset_id: str
    component_id: str
    root: Path
    path: Path
    relative_path: str
    prohibited_symlink: bool = False


@dataclass(frozen=True)
class FileRecord:
    dataset_id: str
    component_id: str
    relative_path: str
    size_bytes: int | None
    sha256: str | None
    extension: str
    width: int | None
    height: int | None
    status: str
    error: str


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> tuple[str, bytes, int]:
    digest = hashlib.sha256()
    first = b""
    size = 0
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            if not first:
                first = chunk[:32]
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), first, size


def png_dimensions(header: bytes) -> tuple[int, int] | None:
    if len(header) < 24 or header[:8] != PNG_SIGNATURE or header[12:16] != b"IHDR":
        return None
    return struct.unpack(">II", header[16:24])


def _component_for(relative_path: str, rules: list[dict[str, str]], dataset_id: str) -> str:
    matches = [rule for rule in rules if relative_path == rule["prefix"] or relative_path.startswith(rule["prefix"] + "/")]
    if not matches:
        return f"{dataset_id}_unclassified"
    return max(matches, key=lambda rule: len(rule["prefix"]))["component_id"]


def _ignored(name: str, ignored_names: set[str], ignored_prefixes: tuple[str, ...]) -> bool:
    return name in ignored_names or name.startswith(ignored_prefixes)


def iter_file_items(
    root: Path,
    dataset: dict[str, Any],
    ignored_names: set[str],
    ignored_prefixes: tuple[str, ...],
) -> Iterator[FileItem]:
    include_extensions = {value.lower() for value in dataset.get("include_extensions", [])}
    rules = dataset.get("component_rules", [])

    def walk(directory: Path) -> Iterator[FileItem]:
        entries = sorted(os.scandir(directory), key=lambda entry: entry.name)
        for entry in entries:
            if _ignored(entry.name, ignored_names, ignored_prefixes):
                continue
            path = Path(entry.path)
            relative = path.relative_to(root).as_posix()
            if entry.is_symlink():
                yield FileItem(
                    dataset_id=dataset["dataset_id"],
                    component_id=_component_for(relative, rules, dataset["dataset_id"]),
                    root=root,
                    path=path,
                    relative_path=relative,
                    prohibited_symlink=True,
                )
            elif entry.is_dir(follow_symlinks=False):
                yield from walk(path)
            elif entry.is_file(follow_symlinks=False):
                extension = path.suffix.lower()
                if not include_extensions or extension in include_extensions:
                    yield FileItem(
                        dataset_id=dataset["dataset_id"],
                        component_id=_component_for(relative, rules, dataset["dataset_id"]),
                        root=root,
                        path=path,
                        relative_path=relative,
                    )

    yield from walk(root)


def inspect_file(item: FileItem) -> FileRecord:
    extension = PurePosixPath(item.relative_path).suffix.lower()
    if item.prohibited_symlink:
        return FileRecord(
            item.dataset_id,
            item.component_id,
            item.relative_path,
            None,
            None,
            extension,
            None,
            None,
            "error",
            "symlinks are prohibited and are never followed",
        )
    try:
        digest, header, size = sha256_file(item.path)
        dimensions = png_dimensions(header) if extension == ".png" else None
        if extension == ".png" and dimensions is None:
            return FileRecord(
                item.dataset_id,
                item.component_id,
                item.relative_path,
                size,
                digest,
                extension,
                None,
                None,
                "error",
                "invalid PNG signature or IHDR",
            )
        width, height = dimensions if dimensions else (None, None)
        return FileRecord(
            item.dataset_id,
            item.component_id,
            item.relative_path,
            size,
            digest,
            extension,
            width,
            height,
            "ok",
            "",
        )
    except (OSError, ValueError) as exc:
        return FileRecord(
            item.dataset_id,
            item.component_id,
            item.relative_path,
            None,
            None,
            extension,
            None,
            None,
            "error",
            f"{type(exc).__name__}: {exc}",
        )


def inspect_bounded(items: Iterable[FileItem], workers: int, batch_size: int = 512) -> Iterator[FileRecord]:
    iterator = iter(items)
    with ThreadPoolExecutor(max_workers=workers) as executor:
        while batch := list(itertools.islice(iterator, batch_size)):
            yield from executor.map(inspect_file, batch)


def _canonical_record(record: FileRecord) -> bytes:
    return (
        f"{record.dataset_id}\0{record.component_id}\0{record.relative_path}\0"
        f"{record.size_bytes}\0{record.sha256}\0{record.status}\n"
    ).encode("utf-8")


def _prefix_match(relative_path: str, prefix: str) -> bool:
    return relative_path == prefix or relative_path.startswith(prefix + "/")


def _check_expectations(dataset: dict[str, Any], summary: dict[str, Any], root: Path) -> list[str]:
    issues: list[str] = []
    expectations = dataset.get("expectations", {})
    if "total_files" in expectations and summary["file_count"] != expectations["total_files"]:
        issues.append(f"expected {expectations['total_files']} files, found {summary['file_count']}")
    for prefix, expected in expectations.get("prefix_counts", {}).items():
        actual = summary["prefix_counts"].get(prefix, 0)
        if actual != expected:
            issues.append(f"{prefix}: expected {expected} files, found {actual}")
    for parent, expected_children in expectations.get("required_child_directories", {}).items():
        parent_path = root / parent
        actual = sorted(
            entry.name for entry in os.scandir(parent_path) if entry.is_dir(follow_symlinks=False) and not entry.is_symlink()
        ) if parent_path.is_dir() else []
        if actual != sorted(expected_children):
            issues.append(f"{parent}: class directories differ; expected {sorted(expected_children)}, found {actual}")
    allowed_resolutions = set(expectations.get("allowed_resolutions", []))
    if allowed_resolutions:
        actual_resolutions = set(summary["resolution_counts"])
        if actual_resolutions != allowed_resolutions:
            issues.append(
                f"resolution distribution differs; expected {sorted(allowed_resolutions)}, found {sorted(actual_resolutions)}"
            )
    for check in expectations.get("prefix_extension_counts", []):
        key = f"{check['prefix']}|{check['extension'].lower()}"
        actual = summary["prefix_extension_counts"].get(key, 0)
        if actual != check["count"]:
            issues.append(f"{key}: expected {check['count']} files, found {actual}")
    if summary["error_count"]:
        issues.append(f"{summary['error_count']} files failed content inspection")
    return issues


def _dataset_summary_template() -> dict[str, Any]:
    return {
        "file_count": 0,
        "ok_count": 0,
        "error_count": 0,
        "total_bytes": 0,
        "component_counts": Counter(),
        "group_counts": Counter(),
        "extension_counts": Counter(),
        "resolution_counts": Counter(),
        "prefix_counts": Counter(),
        "prefix_extension_counts": Counter(),
        "errors": [],
    }


def _finalize_counters(summary: dict[str, Any]) -> dict[str, Any]:
    for key in (
        "component_counts",
        "group_counts",
        "extension_counts",
        "resolution_counts",
        "prefix_counts",
        "prefix_extension_counts",
    ):
        summary[key] = dict(sorted(summary[key].items()))
    return summary


def _git_provenance(repo_root: Path) -> dict[str, Any]:
    def run(*args: str) -> str:
        result = subprocess.run(
            ["git", *args], cwd=repo_root, check=False, capture_output=True, text=True
        )
        return result.stdout.strip() if result.returncode == 0 else "unavailable"

    return {
        "revision": run("rev-parse", "HEAD"),
        "worktree_status": run("status", "--short"),
    }


def _digest_paths(paths: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in paths:
        digest.update(path.name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\n")
    return digest.hexdigest()


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def calibrate(repo_root: Path, config_path: Path, file_limit: int, workers: int) -> dict[str, Any]:
    config = load_json(config_path)
    ignored_names = set(config.get("ignored_names", []))
    ignored_prefixes = tuple(config.get("ignored_prefixes", []))
    dataset = config["datasets"][0]
    root = repo_root / dataset["root"]
    items = itertools.islice(iter_file_items(root, dataset, ignored_names, ignored_prefixes), file_limit)
    started = time.perf_counter()
    records = list(inspect_bounded(items, workers))
    elapsed = time.perf_counter() - started
    ok = sum(record.status == "ok" for record in records)
    rate = len(records) / elapsed if elapsed else 0.0
    expected_total = sum(item.get("expectations", {}).get("total_files", 0) for item in config["datasets"])
    return {
        "kind": "P0A inventory calibration; not a research result",
        "sample_files": len(records),
        "ok_files": ok,
        "elapsed_seconds": round(elapsed, 3),
        "files_per_second": round(rate, 2),
        "expected_configured_files": expected_total,
        "projected_seconds_at_sample_rate": round(expected_total / rate, 1) if rate else None,
        "workers": workers,
    }


def build_inventory(repo_root: Path, config_path: Path, output_root: Path, workers: int) -> Path:
    config = load_json(config_path)
    access_path = repo_root / "data/registry/dataset_access.json"
    task_path = repo_root / "data/registry/task_contract.json"
    schema_path = repo_root / "data/schemas/frame_manifest_row.schema.json"
    access = load_json(access_path)
    task = load_json(task_path)
    schema = load_json(schema_path)
    contract_issues = {
        "access_registry": validate_access_registry(access),
        "task_contract": validate_task_contract(task),
        "manifest_schema": validate_manifest_schema(schema),
    }

    output_root.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=".inventory-tmp-", dir=output_root))
    inventory_csv = temporary / "inventory_files.csv.gz"
    aggregate = hashlib.sha256()
    dataset_summaries: list[dict[str, Any]] = []
    ignored_names = set(config.get("ignored_names", []))
    ignored_prefixes = tuple(config.get("ignored_prefixes", []))
    started_at = datetime.now(timezone.utc)
    started_clock = time.perf_counter()

    try:
        with inventory_csv.open("wb") as raw:
            with gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as compressed:
                import io

                with io.TextIOWrapper(compressed, encoding="utf-8", newline="") as text_handle:
                    writer = csv.DictWriter(text_handle, fieldnames=CSV_FIELDS, lineterminator="\n")
                    writer.writeheader()
                    for dataset in config["datasets"]:
                        root = repo_root / dataset["root"]
                        if not root.is_dir():
                            raise FileNotFoundError(f"dataset root is missing: {root}")
                        state = _dataset_summary_template()
                        dataset_digest = hashlib.sha256()
                        expectations = dataset.get("expectations", {})
                        prefixes = list(expectations.get("prefix_counts", {}))
                        prefixes.extend(item["prefix"] for item in expectations.get("prefix_extension_counts", []))
                        prefixes = sorted(set(prefixes))
                        group_depth = int(dataset.get("group_depth", 2))
                        items = iter_file_items(root, dataset, ignored_names, ignored_prefixes)
                        for record in inspect_bounded(items, workers):
                            writer.writerow(asdict(record))
                            canonical = _canonical_record(record)
                            aggregate.update(canonical)
                            dataset_digest.update(canonical)
                            state["file_count"] += 1
                            state["ok_count"] += record.status == "ok"
                            state["error_count"] += record.status != "ok"
                            state["total_bytes"] += record.size_bytes or 0
                            state["component_counts"][record.component_id] += 1
                            parts = PurePosixPath(record.relative_path).parts
                            group = "/".join(parts[:group_depth])
                            state["group_counts"][group] += 1
                            state["extension_counts"][record.extension] += 1
                            if record.width is not None and record.height is not None:
                                state["resolution_counts"][f"{record.width}x{record.height}"] += 1
                            for prefix in prefixes:
                                if _prefix_match(record.relative_path, prefix):
                                    state["prefix_counts"][prefix] += 1
                                    state["prefix_extension_counts"][f"{prefix}|{record.extension}"] += 1
                            if record.status != "ok" and len(state["errors"]) < 100:
                                state["errors"].append(
                                    {"relative_path": record.relative_path, "error": record.error}
                                )
                        _finalize_counters(state)
                        state["dataset_id"] = dataset["dataset_id"]
                        state["root"] = dataset["root"]
                        state["content_tree_sha256"] = dataset_digest.hexdigest()
                        state["expectation_issues"] = _check_expectations(dataset, state, root)
                        dataset_summaries.append(state)

        combined_digest = aggregate.hexdigest()
        finished_at = datetime.now(timezone.utc)
        scanner_files = [repo_root / "data/inventory.py", repo_root / "data/contracts.py"]
        summary = {
            "schema_version": "1.0.0",
            "kind": "P0A local content inventory; not a training or research result",
            "started_at_utc": started_at.isoformat(),
            "finished_at_utc": finished_at.isoformat(),
            "elapsed_seconds": round(time.perf_counter() - started_clock, 3),
            "workers": workers,
            "config_path": config_path.relative_to(repo_root).as_posix(),
            "config_sha256": hashlib.sha256(config_path.read_bytes()).hexdigest(),
            "scanner_sha256": _digest_paths(scanner_files),
            "git": _git_provenance(repo_root),
            "combined_content_tree_sha256": combined_digest,
            "datasets": dataset_summaries,
        }
        _write_json(temporary / "inventory_summary.json", summary)
        _write_json(temporary / "license_access_snapshot.json", access)
        schema_approval = {
            "schema": schema_path.relative_to(repo_root).as_posix(),
            "schema_sha256": hashlib.sha256(schema_path.read_bytes()).hexdigest(),
            "column_order": schema["x-column-order"],
            "inside_official_interval_null_semantics": task["manifest_contract"]["null_semantics"]["inside_official_interval"],
            "quarantine_semantics": task["split_contract"]["unresolved_rule"],
            "teacher_resolution": task["teacher_boundary"],
            "issues": contract_issues["manifest_schema"] + contract_issues["task_contract"],
        }
        schema_approval["verdict"] = "PASS" if not schema_approval["issues"] else "FAIL"
        _write_json(temporary / "schema_approval.json", schema_approval)

        ucf_summary = next(item for item in dataset_summaries if item["dataset_id"] == "ucf_crime_kaggle_frames")
        local_terms_unknown = [
            f"{dataset['dataset_id']}/{component['component_id']}"
            for dataset in access["datasets"]
            for component in dataset["components"]
            if component["access_status"].startswith("present_local")
            and component["license_evidence_digest"] is None
        ]
        vd1_issues = ucf_summary["expectation_issues"]
        vd5_issues = contract_issues["manifest_schema"] + contract_issues["task_contract"]
        vd6_issues = contract_issues["access_registry"]
        verification = {
            "schema_version": "1.0.0",
            "inventory_digest": combined_digest,
            "checks": {
                "V-D1": {"verdict": "PASS" if not vd1_issues else "FAIL", "issues": vd1_issues},
                "V-D5": {"verdict": "PASS" if not vd5_issues else "FAIL", "issues": vd5_issues},
                "V-D6": {
                    "verdict": "BLOCKED" if local_terms_unknown else ("PASS" if not vd6_issues else "FAIL"),
                    "issues": vd6_issues,
                    "pending_local_license_evidence": local_terms_unknown,
                    "safety_action": "Affected use and all raw redistribution remain blocked until terms evidence is supplied.",
                },
            },
            "scope_assertions": {
                "interval_mapping_performed": False,
                "training_performed": False,
                "headline_evaluation_performed": False,
                "benefit_claim_made": False,
            },
        }
        verdicts = {check["verdict"] for check in verification["checks"].values()}
        verification["overall_verdict"] = "PASS" if verdicts == {"PASS"} else ("BLOCKED" if "BLOCKED" in verdicts and "FAIL" not in verdicts else "FAIL")
        _write_json(temporary / "verification.json", verification)

        artifact_hashes = {}
        for artifact in sorted(temporary.iterdir(), key=lambda path: path.name):
            if artifact.is_file():
                artifact_hashes[artifact.name] = hashlib.sha256(artifact.read_bytes()).hexdigest()
        _write_json(temporary / "artifact_hashes.json", artifact_hashes)

        final = output_root / f"inventory-{combined_digest[:16]}"
        if final.exists():
            reproduction_path = output_root / f"reproduction-{combined_digest[:16]}.json"
            if reproduction_path.exists():
                raise FileExistsError(f"reproduction evidence already exists: {reproduction_path}")
            existing_summary = load_json(final / "inventory_summary.json")
            existing_csv_digest = hashlib.sha256((final / "inventory_files.csv.gz").read_bytes()).hexdigest()
            candidate_csv_digest = hashlib.sha256(inventory_csv.read_bytes()).hexdigest()
            reproduction = {
                "schema_version": "1.0.0",
                "kind": "P0A unchanged-data reproducibility check; not a research result",
                "verified_at_utc": datetime.now(timezone.utc).isoformat(),
                "existing_artifact": final.relative_to(repo_root).as_posix(),
                "existing_content_tree_sha256": existing_summary["combined_content_tree_sha256"],
                "candidate_content_tree_sha256": combined_digest,
                "existing_inventory_csv_sha256": existing_csv_digest,
                "candidate_inventory_csv_sha256": candidate_csv_digest,
                "content_tree_match": existing_summary["combined_content_tree_sha256"] == combined_digest,
                "byte_identical_detailed_inventory": existing_csv_digest == candidate_csv_digest,
            }
            reproduction["verdict"] = (
                "PASS"
                if reproduction["content_tree_match"] and reproduction["byte_identical_detailed_inventory"]
                else "FAIL"
            )
            _write_json(reproduction_path, reproduction)
            shutil.rmtree(temporary)
            if reproduction["verdict"] != "PASS":
                raise RuntimeError(f"inventory reproducibility failed: {reproduction_path}")
            return final
        os.replace(temporary, final)
        return final
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
