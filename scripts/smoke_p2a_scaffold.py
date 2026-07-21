#!/usr/bin/env python3
"""Close an immutable, synthetic-only P2A interface smoke artifact.

The numeric choices in this script exercise code paths only. They are recorded
as fixture settings and must never be promoted to experiment defaults or used
to resolve B-007.
"""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import math
import subprocess
import sys
import warnings
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import cv2
import numpy as np
import psutil

from core.run_lifecycle import RunLifecycle, artifact_digest, artifact_payload
from data.degradations import SampleKey, apply_degradation, registered_degradation_specs
from eval.image_quality import psnr, ssim
from models.restoration import restore_image


SOURCE_PATHS = [
    "core/provenance.py",
    "core/reproducibility.py",
    "core/run_lifecycle.py",
    "data/degradations.py",
    "eval/image_quality.py",
    "models/restoration.py",
    "scripts/smoke_p2a_scaffold.py",
    "configs/p2a_scaffold.yaml",
    "requirements/p0c-lock.txt",
]

FIXTURE_DEGRADATION_CHOICES = {
    "gaussian_mean_8bit": 0.0,
    "gaussian_sampling_unit": "element",
    "salt_probability_given_corruption": 0.5,
    "salt_value": 1.0,
    "pepper_value": 0.0,
    "salt_pepper_density_mode": "bernoulli",
    "salt_pepper_sampling_unit": "pixel_shared_channels",
    "speckle_gaussian_mean": 0.0,
    "speckle_model": "x_times_one_plus_gaussian",
    "speckle_sampling_unit": "element",
    "low_light_operation_order": "gamma_then_gaussian",
    "low_light_gaussian_mean_8bit": 0.0,
    "low_light_clipping_sequence": "clip_after_each_stage",
    "low_light_noise_sampling_unit": "element",
    "clipping": "clip_0_1",
}

FIXTURE_RESTORATION_CHOICES = {
    "identity": {},
    "median": {
        "kernel_size": 3,
        "border_policy": "opencv_median_fixed_replicate",
    },
    "gaussian_blur": {
        "kernel_size": (3, 3),
        "sigma_x": 0.8,
        "sigma_y": 0.8,
        "border_type": cv2.BORDER_REFLECT_101,
    },
    "bilateral": {
        "diameter": 3,
        "sigma_color": 0.1,
        "sigma_space": 1.0,
        "border_type": cv2.BORDER_REFLECT_101,
    },
    "nlm": {
        "h_luminance": 3.0,
        "h_color": 3.0,
        "template_window_size": 3,
        "search_window_size": 7,
        "quantization": "round_to_nearest_uint8",
        "color_boundary": "rgb_to_bgr_for_opencv_nlm",
        "border_policy": "opencv_nlm_library_fixed",
    },
}

FIXTURE_METRIC_CHOICES = {
    "data_range": 1.0,
    "channel_axis": -1,
    "win_size": 7,
    "gaussian_weights": True,
    "sigma": 1.5,
    "use_sample_covariance": False,
    "k1": 0.01,
    "k2": 0.03,
}


def _digest_paths() -> str:
    digest = hashlib.sha256()
    for relative in SOURCE_PATHS:
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update((REPO_ROOT / relative).read_bytes())
        digest.update(b"\n")
    return digest.hexdigest()


def _code_revision(source_digest: str) -> str:
    revision = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, capture_output=True, text=True
    )
    status = subprocess.run(
        ["git", "status", "--short", "--untracked-files=all"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    head = revision.stdout.strip() if revision.returncode == 0 else "unavailable"
    dirty = bool(status.stdout.strip()) if status.returncode == 0 else True
    return f"HEAD={head};source_bundle_sha256={source_digest};worktree_dirty={str(dirty).lower()}"


def _fixture_image() -> np.ndarray:
    y, x = np.mgrid[0:16, 0:16].astype(np.float32)
    return np.stack(
        (x / np.float32(15.0), y / np.float32(15.0), (x + y) / np.float32(30.0)),
        axis=-1,
    ).astype(np.float32)


def _metric_record(clean: np.ndarray, candidate: np.ndarray) -> dict[str, object]:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        psnr_value = psnr(clean, candidate, data_range=FIXTURE_METRIC_CHOICES["data_range"])
    ssim_value = ssim(clean, candidate, **FIXTURE_METRIC_CHOICES)
    return {
        "psnr": psnr_value if math.isfinite(psnr_value) else None,
        "psnr_state": "finite" if math.isfinite(psnr_value) else "positive_infinity_exact_match",
        "ssim": ssim_value,
    }


def _execute_matrix(
    fixture_digest: str,
) -> tuple[tuple[object, ...], list[dict[str, object]]]:
    clean = _fixture_image()
    sample = SampleKey("synthetic/gradient-v1", fixture_digest, 0)
    specs = registered_degradation_specs(**FIXTURE_DEGRADATION_CHOICES)
    matrix: list[dict[str, object]] = []
    for spec in specs:
        degraded = apply_degradation(clean, spec=spec, sample=sample)
        for method, parameters in FIXTURE_RESTORATION_CHOICES.items():
            restored = restore_image(
                degraded,
                method=method,
                parameters=parameters,
                output_policy="clip_0_1",
            )
            matrix.append(
                {
                    "transform_id": spec.transform_id,
                    "restoration_method": method,
                    "output_sha256": hashlib.sha256(restored.tobytes()).hexdigest(),
                    "shape": list(restored.shape),
                    "dtype": str(restored.dtype),
                    "range": [float(restored.min()), float(restored.max())],
                    "metrics": _metric_record(clean, restored),
                }
            )
    return specs, matrix


def _finalize_failure(
    lifecycle: RunLifecycle,
    attempt_common: dict[str, object],
    started_at: datetime,
    exception: Exception,
) -> None:
    failed_at = datetime.now(timezone.utc)
    failure = {
        "schema_version": "1.0.0",
        "kind": "P2A synthetic fixture smoke failure; not research evidence",
        "exception_type": type(exception).__name__,
        "exception_message": str(exception),
        "failed_at": failed_at.isoformat(),
        "scope_assertions": {
            "real_data_used": False,
            "model_training": False,
            "research_claim": False,
        },
    }
    (lifecycle.run_directory / "failure.json").write_bytes(artifact_payload(failure))
    lifecycle.append_attempt(
        {
            **attempt_common,
            "status": "FAILED",
            "finished_at": failed_at.isoformat(),
            "artifact_digest": artifact_digest(failure),
            "artifact_path": "aggregate.json",
        }
    )
    lifecycle.finalize(
        failure,
        {
            "status": "FAILED",
            "verdict": "INCONCLUSIVE",
            "claim_state": "NOT_APPLICABLE",
            "reason": "The synthetic interface smoke failed technically; no research claim was evaluated.",
            "next_action": "Review failure.json and create a superseding run after correcting the defect.",
            "runtime_seconds": (failed_at - started_at).total_seconds(),
            "peak_memory_bytes": psutil.Process().memory_info().rss,
            "storage_bytes": len(artifact_payload(failure)),
            "stop_reason": f"technical exception: {type(exception).__name__}",
            "checkpoint_disposition": "not applicable; no model training",
            "summary_artifact_digest": artifact_digest(failure),
        },
    )


def main() -> int:
    started_at = datetime.now(timezone.utc)
    source_digest = _digest_paths()
    fixture_payload = {
        "degradations": FIXTURE_DEGRADATION_CHOICES,
        "restorations": FIXTURE_RESTORATION_CHOICES,
        "metrics": FIXTURE_METRIC_CHOICES,
        "image": "deterministic-16x16-rgb-gradient-v1",
    }
    fixture_digest = hashlib.sha256(
        json.dumps(fixture_payload, sort_keys=True).encode("utf-8")
    ).hexdigest()
    run_id = f"p2a-scaffold-smoke-{fixture_digest[:8]}-{source_digest[:8]}"
    config_path = REPO_ROOT / "configs/p2a_scaffold.yaml"
    lock_path = REPO_ROOT / "requirements/p0c-lock.txt"
    existing = REPO_ROOT / "results/p2a" / run_id
    if existing.exists():
        if not (existing / ".complete").is_file():
            raise FileExistsError(f"existing smoke is incomplete and requires review: {existing}")
        from scripts.check_repository import audit_immutable_artifacts

        _, audit_errors, _ = audit_immutable_artifacts(REPO_ROOT)
        if audit_errors:
            raise RuntimeError("existing immutable smoke failed repository artifact audit")
        existing_verdict = json.loads((existing / "verdict.json").read_text(encoding="utf-8"))
        if existing_verdict.get("status") != "COMPLETED":
            raise RuntimeError(f"existing smoke closed unsuccessfully and requires supersession: {existing}")
        replay_specs, replay_matrix = _execute_matrix(fixture_digest)
        stored_aggregate = json.loads((existing / "aggregate.json").read_text(encoding="utf-8"))
        if (
            stored_aggregate.get("registered_degradation_count") != len(replay_specs)
            or stored_aggregate.get("matrix") != replay_matrix
        ):
            raise RuntimeError(f"live replay differs from immutable smoke: {existing}")
        print(existing)
        return 0
    lifecycle = RunLifecycle.create(
        REPO_ROOT / "results/p2a",
        run_id,
        {
            "run_id": run_id,
            "run_kind": "code_smoke",
            "config_digest": hashlib.sha256(config_path.read_bytes()).hexdigest(),
            "code_revision": _code_revision(source_digest),
            "seed": 0,
            "package_versions": {
                "numpy": importlib.metadata.version("numpy"),
                "opencv-python-headless": importlib.metadata.version("opencv-python-headless"),
                "scikit-image": importlib.metadata.version("scikit-image"),
            },
            "dataset_manifest_digest": fixture_digest,
            "annotation_version": "not-applicable-synthetic-fixture",
            "environment_digest": hashlib.sha256(lock_path.read_bytes()).hexdigest(),
            "hardware": {"device": "CPU; synthetic fixture only"},
            "metric_artifact_paths": ["aggregate.json", "verdict.json"],
        },
    )
    attempt_started = datetime.now(timezone.utc)
    attempt_common = {
        "attempt_id": "synthetic-fixture-1",
        "seed": 0,
        "started_at": attempt_started.isoformat(),
        "reason": "P2A synthetic fixture interface matrix; no dataset, training, or claim",
        "hardware": {"device": "CPU; synthetic fixture only"},
        "parent_checkpoint": None,
    }
    lifecycle.append_attempt(
        {
            **attempt_common,
            "status": "RUNNING",
            "finished_at": None,
            "artifact_digest": None,
            "artifact_path": None,
        }
    )
    try:
        specs, matrix = _execute_matrix(fixture_digest)
    except Exception as exc:
        _finalize_failure(lifecycle, attempt_common, attempt_started, exc)
        raise

    aggregate = {
        "schema_version": "1.0.0",
        "kind": "P2A synthetic fixture interface smoke; not an experiment or research result",
        "source_paths": SOURCE_PATHS,
        "source_bundle_sha256": source_digest,
        "fixture_choices_not_experiment_freeze": fixture_payload,
        "registered_degradation_count": len(specs),
        "registered_restoration_count": len(FIXTURE_RESTORATION_CHOICES),
        "matrix_entry_count": len(matrix),
        "matrix": matrix,
        "checks": {
            "all_registered_degradations_exercised": len(specs) == 10,
            "all_registered_restorations_exercised": len(FIXTURE_RESTORATION_CHOICES) == 5,
            "complete_matrix": len(matrix) == 50,
            "all_outputs_float32_hwc_rgb": all(
                row["dtype"] == "float32" and row["shape"] == [16, 16, 3] for row in matrix
            ),
            "all_outputs_in_unit_interval": all(
                row["range"][0] >= 0.0 and row["range"][1] <= 1.0 for row in matrix
            ),
        },
        "scope_assertions": {
            "real_data_used": False,
            "dataset_mapping_validated": False,
            "experiment_conventions_frozen": False,
            "model_training": False,
            "restoration_benefit_claim": False,
            "research_claim": False,
        },
        "blocker": "B-007 owner convention freeze remains required before P2A code closure or real execution",
    }
    passed = all(aggregate["checks"].values())
    finished_at = datetime.now(timezone.utc)
    lifecycle.append_attempt(
        {
            **attempt_common,
            "status": "COMPLETED" if passed else "FAILED",
            "finished_at": finished_at.isoformat(),
            "artifact_digest": artifact_digest(aggregate),
            "artifact_path": "aggregate.json",
        }
    )
    lifecycle.finalize(
        aggregate,
        {
            "status": "COMPLETED" if passed else "FAILED",
            "verdict": "GOOD_ENOUGH" if passed else "INCONCLUSIVE",
            "claim_state": "NOT_APPLICABLE",
            "reason": "Synthetic interfaces passed their fixture matrix; no experiment claim was evaluated.",
            "next_action": "Owner must resolve B-007 before P2A code closure or real execution.",
            "runtime_seconds": (finished_at - started_at).total_seconds(),
            "peak_memory_bytes": psutil.Process().memory_info().rss,
            "storage_bytes": len(artifact_payload(aggregate)),
            "stop_reason": "synthetic fixture matrix completed",
            "checkpoint_disposition": "not applicable; no model training",
            "summary_artifact_digest": artifact_digest(aggregate),
        },
    )
    print(lifecycle.run_directory)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
