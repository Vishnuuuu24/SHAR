#!/usr/bin/env python3
"""Rebuild the P0C lock in a temporary venv and verify exact imports."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
import venv
import zipfile
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def normalized_lock(path: Path) -> set[str]:
    return {
        line.strip().lower()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, default=REPO_ROOT / "results/p0c/fresh-environment-project-20260720.json"
    )
    args = parser.parse_args()
    output = args.output if args.output.is_absolute() else REPO_ROOT / args.output
    if output.exists():
        raise FileExistsError(f"immutable fresh-environment report exists: {output}")
    lock_path = REPO_ROOT / "requirements/p0c-lock.txt"
    with tempfile.TemporaryDirectory(prefix="shar-p0c-fresh-") as temporary:
        temporary_root = Path(temporary)
        wheel_directory = temporary_root / "wheels"
        wheel_directory.mkdir()
        build = subprocess.run(
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
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        if build.returncode != 0:
            raise RuntimeError(f"project wheel build failed:\n{build.stdout}\n{build.stderr}")
        wheels = list(wheel_directory.glob("shar_research-*.whl"))
        if len(wheels) != 1:
            raise RuntimeError(f"expected exactly one project wheel; found {wheels}")
        wheel = wheels[0]
        with zipfile.ZipFile(wheel) as archive:
            wheel_members = sorted(archive.namelist())
        environment = Path(temporary) / "venv"
        venv.EnvBuilder(with_pip=True, clear=False).create(environment)
        python = environment / "bin/python"
        install = subprocess.run(
            [str(python), "-m", "pip", "install", "--disable-pip-version-check", "-r", str(lock_path)],
            check=False,
            capture_output=True,
            text=True,
        )
        if install.returncode != 0:
            raise RuntimeError(f"fresh lock install failed:\n{install.stdout}\n{install.stderr}")
        project_install = subprocess.run(
            [str(python), "-m", "pip", "install", "--no-deps", str(wheel)],
            check=False,
            capture_output=True,
            text=True,
        )
        if project_install.returncode != 0:
            raise RuntimeError(
                f"fresh project-wheel install failed:\n{project_install.stdout}\n{project_install.stderr}"
            )
        code = (
            "import json, numpy, PIL, psutil, torch, torchvision, yaml; "
            "import core.device, data.manifest, data.views, eval.metrics, models.classifiers; "
            "print(json.dumps({'numpy':numpy.__version__,'Pillow':PIL.__version__,"
            "'psutil':psutil.__version__,'torch':torch.__version__,'torchvision':torchvision.__version__,"
            "'PyYAML':yaml.__version__,'mps_built':torch.backends.mps.is_built(),"
            "'mps_available':torch.backends.mps.is_available(),"
            "'project_modules':['core.device','data.manifest','data.views','eval.metrics','models.classifiers']},"
            "sort_keys=True))"
        )
        import_check = subprocess.run(
            [str(python), "-I", "-c", code], cwd=temporary_root, check=True, capture_output=True, text=True
        )
        freeze = subprocess.run(
            [str(python), "-m", "pip", "freeze"], check=True, capture_output=True, text=True
        ).stdout
        frozen = {line.strip().lower() for line in freeze.splitlines() if line.strip()}
        dependency_freeze = {line for line in frozen if not line.startswith("shar-research")}
        expected = normalized_lock(lock_path)
        required_wheel_members = {
            "core/device.py",
            "data/manifest.py",
            "data/views.py",
            "eval/metrics.py",
            "models/classifiers.py",
        }
        report = {
            "schema_version": "1.0.0",
            "kind": "P0C fresh temporary environment reproduction; not a research result",
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "source_python": sys.version.split()[0],
            "lock_path": lock_path.relative_to(REPO_ROOT).as_posix(),
            "lock_sha256": hashlib.sha256(lock_path.read_bytes()).hexdigest(),
            "project_wheel_sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(),
            "project_wheel_members_verified": sorted(required_wheel_members),
            "project_wheel_members_missing": sorted(required_wheel_members - set(wheel_members)),
            "imports": json.loads(import_check.stdout),
            "expected_packages": sorted(expected),
            "frozen_packages": sorted(frozen),
            "missing_from_fresh_freeze": sorted(expected - dependency_freeze),
            "unexpected_in_fresh_freeze": sorted(dependency_freeze - expected),
        }
        report["verdict"] = (
            "PASS"
            if not report["missing_from_fresh_freeze"]
            and not report["unexpected_in_fresh_freeze"]
            and not report["project_wheel_members_missing"]
            else "FAIL"
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
