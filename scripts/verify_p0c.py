#!/usr/bin/env python3
"""Close P0C verification from immutable environment/calibration evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.provenance import validate_provenance
from core.reproducibility import deterministic_noise_fixture


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--environment", type=Path, required=True)
    parser.add_argument("--fresh-environment", type=Path, required=True)
    parser.add_argument("--calibration", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=REPO_ROOT / "results/p0c/verification-20260720.json")
    args = parser.parse_args()
    paths = {
        "environment": args.environment if args.environment.is_absolute() else REPO_ROOT / args.environment,
        "fresh_environment": args.fresh_environment if args.fresh_environment.is_absolute() else REPO_ROOT / args.fresh_environment,
        "calibration": args.calibration if args.calibration.is_absolute() else REPO_ROOT / args.calibration,
    }
    output = args.output if args.output.is_absolute() else REPO_ROOT / args.output
    if output.exists():
        raise FileExistsError(f"immutable P0C verification exists: {output}")
    environment = load(paths["environment"])
    fresh = load(paths["fresh_environment"])
    calibration = load(paths["calibration"])

    digest = hashlib.sha256(b"p0c-determinism-fixture").hexdigest()
    inputs = [(f"Train/Abuse/frame-{index}.png", digest, 17, "gaussian-fixture", (3, 16, 16)) for index in range(12)]
    serial = [hashlib.sha256(deterministic_noise_fixture(*item).tobytes()).hexdigest() for item in inputs]
    with ThreadPoolExecutor(max_workers=4) as executor:
        parallel = list(executor.map(lambda item: hashlib.sha256(deterministic_noise_fixture(*item).tobytes()).hexdigest(), inputs))
    subprocess_code = (
        "import hashlib; from core.reproducibility import deterministic_noise_fixture; "
        f"d={digest!r}; a=deterministic_noise_fixture('Train/Abuse/frame-0.png',d,17,'gaussian-fixture',(3,16,16)); "
        "print(hashlib.sha256(a.tobytes()).hexdigest())"
    )
    fresh_process_digest = subprocess.check_output(
        [sys.executable, "-c", subprocess_code], cwd=REPO_ROOT, text=True
    ).strip()

    provenance_fixture = {
        "run_id": "p0c-verification-fixture",
        "run_kind": "smoke",
        "config_digest": "a" * 64,
        "code_revision": "p0c-worktree",
        "seed": 0,
        "package_versions": environment["direct_import_versions"],
        "dataset_manifest_digest": "b" * 64,
        "annotation_version": "fixture-v1",
        "environment_digest": environment["environment_lock"]["sha256"],
        "hardware": environment["platform"],
        "metric_artifact_paths": ["fixture-metrics.json"],
    }
    missing_fixture = dict(provenance_fixture)
    missing_fixture.pop("annotation_version")
    provenance_pass = not validate_provenance(provenance_fixture) and bool(validate_provenance(missing_fixture))

    unit = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py", "-v"],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    vd7_pass = serial == parallel and serial[0] == fresh_process_digest and unit.returncode == 0
    vd8_pass = (
        environment.get("verdict") == "PASS"
        and environment.get("mps", {}).get("operation_smoke") == "PASS"
        and environment.get("mps", {}).get("device_report", {}).get("selected") == "mps"
        and not environment.get("mps", {}).get("device_report", {}).get("cpu_fallback_allowed")
        and fresh.get("verdict") == "PASS"
        and calibration.get("verdict") == "PASS"
        and calibration.get("device", {}).get("selected") == "mps"
        and not calibration.get("device", {}).get("cpu_fallback_allowed")
    )
    report = {
        "schema_version": "1.0.0",
        "kind": "P0C closure verification; not a research result",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "artifacts": {
            name: {"path": path.relative_to(REPO_ROOT).as_posix(), "sha256": sha256(path)}
            for name, path in paths.items()
        },
        "checks": {
            "V-D7": {
                "verdict": "PASS" if vd7_pass else "FAIL",
                "serial_parallel_match": serial == parallel,
                "fresh_process_match": serial[0] == fresh_process_digest,
                "fixture_digest": serial[0],
            },
            "V-D8": {
                "verdict": "PASS" if vd8_pass else "FAIL",
                "mps_selected": calibration.get("device", {}).get("selected"),
                "cpu_fallback_allowed": calibration.get("device", {}).get("cpu_fallback_allowed"),
                "median_images_per_second": calibration.get("measurements", {}).get("images_per_second_median"),
            },
            "provenance_writer": {
                "verdict": "PASS" if provenance_pass else "FAIL",
                "complete_fixture_accepted": not validate_provenance(provenance_fixture),
                "missing_fixture_refused": bool(validate_provenance(missing_fixture)),
            },
            "unit_tests": {
                "verdict": "PASS" if unit.returncode == 0 else "FAIL",
                "returncode": unit.returncode,
                "summary_tail": "\n".join((unit.stdout + unit.stderr).splitlines()[-5:]),
            },
        },
        "scope_assertions": {
            "research_training": False,
            "headline_evaluation": False,
            "benefit_claim": False,
        },
    }
    report["overall_verdict"] = (
        "PASS" if all(check["verdict"] == "PASS" for check in report["checks"].values()) else "FAIL"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["overall_verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
