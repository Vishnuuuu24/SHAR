#!/usr/bin/env python3
"""Run the portable, dataset-free SHAR repository verification suite.

This command is intentionally rerunnable and writes only to temporary
directories. It does not inspect licensed media, validate UCF mappings, run
models on MPS, or produce research evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
import zipfile
from dataclasses import asdict, dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
SKIPPED_DIRECTORY_NAMES = {".git", ".venv", "Datasets", "__pycache__", "build"}
PYTHON_SOURCE_ROOTS = ("core", "data", "eval", "models", "scripts", "tests")
REQUIRED_IMPORTS = (
    "cv2",
    "numpy",
    "PIL",
    "psutil",
    "skimage",
    "yaml",
    "torch",
    "torchvision",
    "core.device",
    "core.p2a_conventions",
    "core.provenance",
    "core.run_lifecycle",
    "data.manifest",
    "data.ucf_intervals",
    "data.degradations",
    "data.faculty_visual_pack",
    "data.train_validation",
    "data.views",
    "eval.image_quality",
    "eval.metrics",
    "models.classifiers",
    "models.restoration",
)
REQUIRED_WHEEL_MEMBERS = {
    "core/__init__.py",
    "core/device.py",
    "core/p2a_conventions.py",
    "core/provenance.py",
    "core/reproducibility.py",
    "core/run_lifecycle.py",
    "data/__init__.py",
    "data/contracts.py",
    "data/degradations.py",
    "data/faculty_visual_pack.py",
    "data/grouping.py",
    "data/inventory.py",
    "data/manifest.py",
    "data/train_validation.py",
    "data/ucf_intervals.py",
    "data/views.py",
    "eval/__init__.py",
    "eval/image_quality.py",
    "eval/metrics.py",
    "models/__init__.py",
    "models/classifiers.py",
    "models/restoration.py",
}
ATTEMPT_REQUIRED_FIELDS = {
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
ATTEMPT_STATUSES = {"RUNNING", "COMPLETED", "FAILED", "ABORTED", "INVALID"}
FINAL_ATTEMPT_STATUSES = ATTEMPT_STATUSES - {"RUNNING"}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
MARKDOWN_INLINE_LINK_RE = re.compile(r"!?\[[^\]\n]*\]\(([^)\n]+)\)")
MARKDOWN_REFERENCE_LINK_RE = re.compile(r"^\s*\[[^\]\n]+\]:\s*(<[^>]+>|\S+)", re.MULTILINE)
OWNER_PLACEHOLDER_RE = re.compile(
    r"(?:OWNER(?:_|\s|-)?(?:REQUIRED|SELECTION|PREREGISTRATION)|owner_required|"
    r"required_before_full_run)",
    re.IGNORECASE,
)


@dataclass
class CheckResult:
    name: str
    passed: bool
    details: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _is_skipped(path: Path, root: Path) -> bool:
    try:
        parts = path.relative_to(root).parts
    except ValueError:
        return True
    return any(part in SKIPPED_DIRECTORY_NAMES for part in parts)


def _files_with_suffixes(root: Path, suffixes: set[str]) -> Iterable[Path]:
    matches: list[Path] = []
    for directory, child_directories, filenames in os.walk(root, topdown=True):
        child_directories[:] = sorted(
            name for name in child_directories if name not in SKIPPED_DIRECTORY_NAMES
        )
        directory_path = Path(directory)
        for filename in sorted(filenames):
            path = directory_path / filename
            if path.suffix.lower() in suffixes:
                matches.append(path)
    yield from sorted(matches)


def _relative(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)


def _run(command: list[str], *, cwd: Path, environment: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    merged_environment = os.environ.copy()
    if environment:
        merged_environment.update(environment)
    return subprocess.run(
        command,
        cwd=cwd,
        env=merged_environment,
        check=False,
        capture_output=True,
        text=True,
    )


def _command_result(name: str, process: subprocess.CompletedProcess[str]) -> CheckResult:
    output = (process.stdout + process.stderr).strip()
    details: dict[str, Any] = {"returncode": process.returncode}
    if output:
        details["output_tail"] = "\n".join(output.splitlines()[-20:])
    return CheckResult(
        name=name,
        passed=process.returncode == 0,
        details=details,
        errors=[] if process.returncode == 0 else [f"command failed with return code {process.returncode}"],
    )


def check_unittests(root: Path = REPO_ROOT) -> CheckResult:
    process = _run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py", "-v"],
        cwd=root,
        environment={"PYTHONDONTWRITEBYTECODE": "1"},
    )
    return _command_result("unittest_discovery", process)


def check_compileall(root: Path = REPO_ROOT) -> CheckResult:
    existing_roots = [name for name in PYTHON_SOURCE_ROOTS if (root / name).is_dir()]
    with tempfile.TemporaryDirectory(prefix="shar-compileall-") as temporary:
        process = _run(
            [sys.executable, "-m", "compileall", "-q", *existing_roots],
            cwd=root,
            environment={"PYTHONPYCACHEPREFIX": str(Path(temporary) / "pycache")},
        )
    result = _command_result("compileall", process)
    result.details["source_roots"] = existing_roots
    return result


def check_pip(root: Path = REPO_ROOT) -> CheckResult:
    return _command_result("pip_check", _run([sys.executable, "-m", "pip", "check"], cwd=root))


def check_serialized_syntax(root: Path = REPO_ROOT) -> CheckResult:
    errors: list[str] = []
    counts = {"json": 0, "jsonl": 0, "yaml": 0}
    for path in _files_with_suffixes(root, {".json", ".jsonl", ".yaml", ".yml"}):
        relative = _relative(path, root)
        try:
            if path.suffix.lower() == ".json":
                counts["json"] += 1
                json.loads(path.read_text(encoding="utf-8"))
            elif path.suffix.lower() == ".jsonl":
                counts["jsonl"] += 1
                for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
                    if line.strip():
                        try:
                            json.loads(line)
                        except json.JSONDecodeError as exc:
                            errors.append(f"{relative}:{line_number}: {exc}")
            else:
                counts["yaml"] += 1
                yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError, yaml.YAMLError) as exc:
            errors.append(f"{relative}: {exc}")
    return CheckResult("serialized_syntax", not errors, counts, errors)


def check_required_imports(root: Path = REPO_ROOT) -> CheckResult:
    code = (
        "import importlib, json; "
        f"names={list(REQUIRED_IMPORTS)!r}; "
        "loaded={name:getattr(importlib.import_module(name),'__file__',None) for name in names}; "
        "print(json.dumps(loaded,sort_keys=True))"
    )
    process = _run(
        [sys.executable, "-c", code],
        cwd=root,
        environment={"PYTHONDONTWRITEBYTECODE": "1"},
    )
    result = _command_result("required_imports", process)
    if process.returncode == 0:
        try:
            result.details["modules"] = json.loads(process.stdout)
        except json.JSONDecodeError as exc:
            result.passed = False
            result.errors.append(f"import smoke returned invalid JSON: {exc}")
    return result


def check_wheel(root: Path = REPO_ROOT) -> CheckResult:
    errors: list[str] = []
    details: dict[str, Any] = {}
    with tempfile.TemporaryDirectory(prefix="shar-wheel-check-") as temporary:
        temporary_root = Path(temporary)
        source = temporary_root / "source"
        source.mkdir()
        shutil.copy2(root / "pyproject.toml", source / "pyproject.toml")
        for package in ("core", "data", "eval", "models"):
            shutil.copytree(
                root / package,
                source / package,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
            )
        wheel_directory = temporary_root / "wheels"
        wheel_directory.mkdir()
        build = _run(
            [
                sys.executable,
                "-m",
                "pip",
                "wheel",
                ".",
                "--no-deps",
                "--no-build-isolation",
                "--wheel-dir",
                str(wheel_directory),
            ],
            cwd=source,
            environment={"PYTHONDONTWRITEBYTECODE": "1"},
        )
        details["build_returncode"] = build.returncode
        if build.returncode != 0:
            errors.append("wheel build failed: " + "\n".join((build.stdout + build.stderr).splitlines()[-20:]))
            return CheckResult("wheel_build_and_import", False, details, errors)
        wheels = sorted(wheel_directory.glob("shar_research-*.whl"))
        if len(wheels) != 1:
            errors.append(f"expected one shar_research wheel, found {len(wheels)}")
            return CheckResult("wheel_build_and_import", False, details, errors)
        wheel = wheels[0]
        details["wheel_sha256"] = hashlib.sha256(wheel.read_bytes()).hexdigest()
        with zipfile.ZipFile(wheel) as archive:
            members = set(archive.namelist())
        missing_members = sorted(REQUIRED_WHEEL_MEMBERS - members)
        details["verified_member_count"] = len(REQUIRED_WHEEL_MEMBERS)
        details["missing_members"] = missing_members
        if missing_members:
            errors.append(f"wheel is missing required members: {missing_members}")

        target = temporary_root / "installed"
        install = _run(
            [sys.executable, "-m", "pip", "install", "--no-deps", "--target", str(target), str(wheel)],
            cwd=temporary_root,
            environment={"PYTHONDONTWRITEBYTECODE": "1"},
        )
        details["install_returncode"] = install.returncode
        if install.returncode != 0:
            errors.append("wheel target install failed: " + "\n".join((install.stdout + install.stderr).splitlines()[-20:]))
        else:
            project_modules = [name for name in REQUIRED_IMPORTS if name.split(".")[0] in {"core", "data", "eval", "models"}]
            code = (
                "import importlib,json,sys,pathlib; "
                f"target=pathlib.Path({str(target)!r}).resolve(); sys.path.insert(0,str(target)); "
                f"names={project_modules!r}; "
                "loaded={name:str(pathlib.Path(importlib.import_module(name).__file__).resolve()) for name in names}; "
                "assert all(pathlib.Path(path).is_relative_to(target) for path in loaded.values()), loaded; "
                "print(json.dumps(loaded,sort_keys=True))"
            )
            smoke = _run(
                [sys.executable, "-c", code],
                cwd=temporary_root,
                environment={"PYTHONDONTWRITEBYTECODE": "1"},
            )
            details["import_returncode"] = smoke.returncode
            if smoke.returncode != 0:
                errors.append("installed-wheel import smoke failed: " + "\n".join((smoke.stdout + smoke.stderr).splitlines()[-20:]))
            else:
                details["installed_module_origins"] = json.loads(smoke.stdout)
    return CheckResult("wheel_build_and_import", not errors, details, errors)


def _markdown_targets(text: str) -> Iterable[str]:
    yield from MARKDOWN_INLINE_LINK_RE.findall(text)
    yield from MARKDOWN_REFERENCE_LINK_RE.findall(text)


def _local_markdown_target(raw_target: str) -> str | None:
    target = raw_target.strip()
    if target.startswith("<") and ">" in target:
        target = target[1 : target.index(">")]
    else:
        target = target.split(maxsplit=1)[0]
    if not target or target.startswith("#"):
        return None
    parsed = urllib.parse.urlsplit(target)
    if parsed.scheme or parsed.netloc:
        return None
    return urllib.parse.unquote(parsed.path)


def find_markdown_link_issues(root: Path = REPO_ROOT) -> list[str]:
    issues: list[str] = []
    for path in _files_with_suffixes(root, {".md"}):
        for raw_target in _markdown_targets(path.read_text(encoding="utf-8")):
            local_target = _local_markdown_target(raw_target)
            if not local_target:
                continue
            destination = Path(local_target)
            if not destination.is_absolute():
                destination = path.parent / destination
            if not destination.exists():
                issues.append(f"{_relative(path, root)} -> {raw_target}")
    return issues


def check_markdown_links(root: Path = REPO_ROOT) -> CheckResult:
    issues = find_markdown_link_issues(root)
    markdown_count = sum(1 for _ in _files_with_suffixes(root, {".md"}))
    return CheckResult(
        "local_markdown_links",
        not issues,
        {"markdown_files": markdown_count},
        [f"missing local Markdown target: {issue}" for issue in issues],
    )


def _walk_strings(value: Any, path: str = "$") -> Iterable[tuple[str, str]]:
    if isinstance(value, str):
        yield path, value
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _walk_strings(item, f"{path}[{index}]")
    elif isinstance(value, dict):
        for key, item in value.items():
            yield from _walk_strings(item, f"{path}.{key}")


def find_config_placeholders(root: Path = REPO_ROOT) -> list[str]:
    placeholders: list[str] = []
    config_root = root / "configs"
    if not config_root.exists():
        return placeholders
    for path in _files_with_suffixes(config_root, {".yaml", ".yml", ".json"}):
        try:
            value = (
                json.loads(path.read_text(encoding="utf-8"))
                if path.suffix.lower() == ".json"
                else yaml.safe_load(path.read_text(encoding="utf-8"))
            )
        except (json.JSONDecodeError, yaml.YAMLError):
            continue
        for value_path, text_value in _walk_strings(value):
            if OWNER_PLACEHOLDER_RE.search(text_value):
                placeholders.append(f"{_relative(path, root)}:{value_path}={text_value}")
    return placeholders


def check_config_placeholders(root: Path = REPO_ROOT) -> CheckResult:
    placeholders = find_config_placeholders(root)
    return CheckResult(
        "config_owner_placeholders",
        True,
        {"placeholder_count": len(placeholders), "placeholders": placeholders},
        warnings=(
            ["Owner placeholders are expected to block full runs until resolved; fixture/code checks may continue."]
            if placeholders
            else []
        ),
    )


def _artifact_payload(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _declared_invalid_artifacts(
    root: Path, results_root: Path
) -> tuple[set[str], list[str]]:
    declared: set[str] = set()
    unresolved: dict[str, str] = {}

    def normalized_paths(values: Iterable[Any]) -> list[str]:
        paths: list[str] = []
        for value in values:
            if isinstance(value, dict):
                value = value.get("path")
            if isinstance(value, str) and value:
                paths.append(Path(value).as_posix().rstrip("/"))
        return paths

    def validate_replacement(path_value: Any, digest_value: Any) -> tuple[bool, str]:
        if not isinstance(path_value, str) or not path_value:
            return False, "missing replacement path"
        pure = PurePosixPath(path_value)
        if (
            pure.is_absolute()
            or ".." in pure.parts
            or "\\" in path_value
            or pure.as_posix() != path_value
            or not pure.parts
            or pure.parts[0] != "results"
        ):
            return False, "replacement must be a canonical repository-relative results path"
        if not isinstance(digest_value, str) or not SHA256_RE.fullmatch(digest_value):
            return False, "missing replacement aggregate SHA-256"
        replacement = root / path_value
        required = {
            "run_manifest.json",
            "attempts.jsonl",
            "aggregate.json",
            "verdict.json",
            ".complete",
        }
        if any(not (replacement / name).is_file() for name in required):
            return False, f"replacement is not a complete lifecycle closure: {path_value}"
        aggregate = replacement / "aggregate.json"
        if hashlib.sha256(aggregate.read_bytes()).hexdigest() != digest_value:
            return False, f"replacement aggregate digest mismatch: {path_value}"
        try:
            manifest = json.loads((replacement / "run_manifest.json").read_text(encoding="utf-8"))
            verdict = json.loads((replacement / "verdict.json").read_text(encoding="utf-8"))
            complete = json.loads((replacement / ".complete").read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            return False, f"replacement closure JSON is invalid: {exc}"
        if manifest.get("run_id") != replacement.name:
            return False, "replacement manifest run_id does not match its directory"
        if verdict.get("summary_artifact_digest") != digest_value:
            return False, "replacement verdict does not bind the declared aggregate"
        closure_digests = complete.get("files_sha256") if isinstance(complete, dict) else None
        if closure_digests is not None:
            closure_names = {
                "run_manifest.json",
                "attempts.jsonl",
                "aggregate.json",
                "verdict.json",
            }
            if set(closure_digests) != closure_names:
                return False, "replacement authenticated closure has incomplete file coverage"
            for name in closure_names:
                actual = hashlib.sha256((replacement / name).read_bytes()).hexdigest()
                if closure_digests.get(name) != actual:
                    return False, f"replacement authenticated closure mismatch for {name}"
        return True, ""

    for path in sorted(results_root.rglob("*.json")):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            continue
        if not isinstance(record, dict):
            continue
        targets: list[str] = []
        replacement_path: Any = None
        replacement_digest: Any = None
        if record.get("status") == "INVALID":
            targets.extend(
                normalized_paths(
                    [record.get("artifact"), record.get("invalid_artifact")]
                    + list(record.get("invalid_artifacts", []))
                )
            )
            replacement_path = record.get("replacement_artifact") or record.get("replacement")
            replacement_digest = record.get("replacement_aggregate_sha256")
        retained = normalized_paths(record.get("invalid_smokes_retained", []))
        if retained:
            targets.extend(retained)
            replacement_path = record.get("valid_smoke") or record.get("valid_fixture_smoke")
            replacement_digest = record.get("valid_smoke_aggregate_sha256") or record.get(
                "valid_fixture_aggregate_sha256"
            )
        if not targets:
            continue
        replacement_ok, reason = validate_replacement(replacement_path, replacement_digest)
        if replacement_ok:
            declared.update(targets)
        else:
            for target in targets:
                unresolved[target] = f"{_relative(path, root)}: {reason}"
    errors = [
        f"invalid artifact supersession is not authenticated for {target}: {reason}"
        for target, reason in sorted(unresolved.items())
        if target not in declared
    ]
    return declared, errors


def audit_immutable_artifacts(root: Path = REPO_ROOT) -> tuple[dict[str, Any], list[str], list[str]]:
    results_root = root / "results"
    errors: list[str] = []
    warnings: list[str] = []
    if results_root.exists():
        declared_invalid, supersession_errors = _declared_invalid_artifacts(root, results_root)
        errors.extend(supersession_errors)
    else:
        declared_invalid = set()
    complete_directories = sorted(marker.parent for marker in results_root.rglob(".complete")) if results_root.exists() else []
    audited: list[str] = []
    retained_invalid: list[str] = []
    for directory in complete_directories:
        relative_directory = _relative(directory, root)
        if relative_directory in declared_invalid:
            retained_invalid.append(relative_directory)
            continue
        required = {
            "run_manifest.json",
            "attempts.jsonl",
            "aggregate.json",
            "verdict.json",
            ".complete",
        }
        missing = sorted(name for name in required if not (directory / name).is_file())
        if missing:
            errors.append(f"{relative_directory}: missing closure files {missing}")
            continue
        try:
            manifest = json.loads((directory / "run_manifest.json").read_text(encoding="utf-8"))
            aggregate = json.loads((directory / "aggregate.json").read_text(encoding="utf-8"))
            verdict = json.loads((directory / "verdict.json").read_text(encoding="utf-8"))
            complete = json.loads((directory / ".complete").read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            errors.append(f"{relative_directory}: invalid closure JSON: {exc}")
            continue
        if manifest.get("run_id") != directory.name:
            errors.append(
                f"{relative_directory}: run_manifest run_id {manifest.get('run_id')!r} does not match directory"
            )
        metric_paths = manifest.get("metric_artifact_paths")
        if not isinstance(metric_paths, list) or not metric_paths:
            errors.append(f"{relative_directory}: metric_artifact_paths must be a non-empty list")
        else:
            for metric_path in metric_paths:
                if not isinstance(metric_path, str) or not metric_path or not (directory / metric_path).is_file():
                    errors.append(f"{relative_directory}: missing metric artifact {metric_path!r}")
        closure_names = {
            "run_manifest.json",
            "attempts.jsonl",
            "aggregate.json",
            "verdict.json",
        }
        closure_digests = complete.get("files_sha256") if isinstance(complete, dict) else None
        if isinstance(closure_digests, dict):
            if set(closure_digests) != closure_names:
                errors.append(
                    f"{relative_directory}: .complete files_sha256 must cover {sorted(closure_names)}"
                )
            else:
                for name in sorted(closure_names):
                    expected_file_digest = closure_digests.get(name)
                    actual_file_digest = hashlib.sha256((directory / name).read_bytes()).hexdigest()
                    if expected_file_digest != actual_file_digest:
                        errors.append(
                            f"{relative_directory}: authenticated closure digest mismatch for {name}"
                        )
        else:
            warnings.append(
                f"{relative_directory}: legacy .complete marker does not authenticate manifest/attempt files"
            )
        expected_digest = hashlib.sha256(_artifact_payload(aggregate)).hexdigest()
        if verdict.get("summary_artifact_digest") != expected_digest:
            errors.append(f"{relative_directory}: verdict summary digest does not match aggregate.json")

        attempts: list[dict[str, Any]] = []
        for line_number, line in enumerate(
            (directory / "attempts.jsonl").read_text(encoding="utf-8").splitlines(), start=1
        ):
            if not line.strip():
                continue
            try:
                attempt = json.loads(line)
            except json.JSONDecodeError as exc:
                errors.append(f"{relative_directory}/attempts.jsonl:{line_number}: {exc}")
                continue
            attempts.append(attempt)
            missing_fields = ATTEMPT_REQUIRED_FIELDS - set(attempt)
            if missing_fields:
                errors.append(
                    f"{relative_directory}/attempts.jsonl:{line_number}: missing fields {sorted(missing_fields)}"
                )
            if attempt.get("status") not in ATTEMPT_STATUSES:
                errors.append(
                    f"{relative_directory}/attempts.jsonl:{line_number}: invalid status {attempt.get('status')!r}"
                )
            digest = attempt.get("artifact_digest")
            if attempt.get("status") in FINAL_ATTEMPT_STATUSES and (
                not isinstance(digest, str) or not SHA256_RE.fullmatch(digest)
            ):
                errors.append(
                    f"{relative_directory}/attempts.jsonl:{line_number}: invalid artifact_digest"
                )
            artifact_path = attempt.get("artifact_path")
            if attempt.get("status") == "RUNNING":
                if artifact_path is not None:
                    errors.append(
                        f"{relative_directory}/attempts.jsonl:{line_number}: RUNNING event has artifact_path"
                    )
            elif attempt.get("status") in FINAL_ATTEMPT_STATUSES:
                if artifact_path is None:
                    warnings.append(
                        f"{relative_directory}/attempts.jsonl:{line_number}: legacy terminal event has no artifact_path"
                    )
                elif not isinstance(artifact_path, str) or not artifact_path:
                    errors.append(
                        f"{relative_directory}/attempts.jsonl:{line_number}: invalid artifact_path"
                    )
                else:
                    pure_artifact_path = PurePosixPath(artifact_path)
                    if (
                        pure_artifact_path.is_absolute()
                        or ".." in pure_artifact_path.parts
                        or "\\" in artifact_path
                        or pure_artifact_path.as_posix() != artifact_path
                    ):
                        errors.append(
                            f"{relative_directory}/attempts.jsonl:{line_number}: artifact_path is not canonical relative POSIX"
                        )
                    else:
                        artifact = directory / artifact_path
                        if not artifact.is_file():
                            errors.append(
                                f"{relative_directory}/attempts.jsonl:{line_number}: artifact_path does not exist"
                            )
                        elif isinstance(digest, str) and SHA256_RE.fullmatch(digest):
                            actual_attempt_digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
                            if actual_attempt_digest != digest:
                                errors.append(
                                    f"{relative_directory}/attempts.jsonl:{line_number}: artifact_digest does not match artifact_path"
                                )
        if not attempts:
            errors.append(f"{relative_directory}: attempts.jsonl is empty")
        else:
            latest_by_id: dict[str, dict[str, Any]] = {}
            for attempt in attempts:
                attempt_id = attempt.get("attempt_id")
                if isinstance(attempt_id, str) and attempt_id:
                    latest_by_id[attempt_id] = attempt
            for attempt_id, attempt in sorted(latest_by_id.items()):
                if attempt.get("status") not in FINAL_ATTEMPT_STATUSES:
                    errors.append(
                        f"{relative_directory}/attempts.jsonl: attempt {attempt_id!r} has no terminal event"
                    )
        audited.append(relative_directory)

    incomplete_streams: list[str] = []
    retained_invalid_incomplete: list[str] = []
    if results_root.exists():
        all_incomplete_streams = sorted(
            _relative(path.parent, root)
            for path in results_root.rglob("attempts.jsonl")
            if not (path.parent / ".complete").exists()
        )
        incomplete_streams = [path for path in all_incomplete_streams if path not in declared_invalid]
        retained_invalid_incomplete = [path for path in all_incomplete_streams if path in declared_invalid]
    if retained_invalid or retained_invalid_incomplete:
        warnings.append(
            "Known invalid artifacts were retained under explicit supersession records and excluded from valid-closure checks: "
            + ", ".join(sorted(retained_invalid + retained_invalid_incomplete))
        )
    if incomplete_streams:
        warnings.append(
            "Attempt streams without lifecycle .complete markers were not treated as valid closures: "
            + ", ".join(incomplete_streams)
        )
    summary = {
        "complete_run_count": len(complete_directories),
        "audited_runs": audited,
        "retained_invalid_run_count": len(retained_invalid) + len(retained_invalid_incomplete),
        "incomplete_attempt_stream_count": len(incomplete_streams),
    }
    return summary, errors, warnings


def check_immutable_artifacts(root: Path = REPO_ROOT) -> CheckResult:
    summary, errors, warnings = audit_immutable_artifacts(root)
    return CheckResult("immutable_artifact_audit", not errors, summary, errors, warnings)


def run_all(root: Path = REPO_ROOT, *, include_wheel: bool = True) -> list[CheckResult]:
    checks = [
        check_serialized_syntax(root),
        check_markdown_links(root),
        check_config_placeholders(root),
        check_immutable_artifacts(root),
        check_compileall(root),
        check_pip(root),
        check_required_imports(root),
        check_unittests(root),
    ]
    if include_wheel:
        checks.append(check_wheel(root))
    return checks


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skip-wheel",
        action="store_true",
        help="Skip the temporary wheel build/import smoke (intended only for focused local diagnosis).",
    )
    args = parser.parse_args()
    results = run_all(REPO_ROOT, include_wheel=not args.skip_wheel)
    report = {
        "schema_version": "1.0.0",
        "kind": "rerunnable dataset-free repository verification; not research evidence",
        "scope_assertions": {
            "licensed_dataset_files_read": False,
            "dataset_mapping_validated": False,
            "mps_validated": False,
            "model_training": False,
            "research_claim": False,
            "repository_evidence_rewritten": False,
        },
        "checks": [asdict(result) for result in results],
        "overall_verdict": "PASS" if all(result.passed for result in results) else "FAIL",
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["overall_verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
