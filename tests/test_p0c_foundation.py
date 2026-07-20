from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import torch

from core.device import select_device
from core.provenance import REQUIRED_PROVENANCE_FIELDS, finalize_provenance, validate_provenance
from core.reproducibility import deterministic_noise_fixture, seed_everything, stable_sample_seed


REPO_ROOT = Path(__file__).resolve().parents[1]
FILE_DIGEST = hashlib.sha256(b"fixture-image").hexdigest()


class ReproducibilityTests(unittest.TestCase):
    def test_stable_seed_and_noise_repeat_in_process(self) -> None:
        args = ("Train/Abuse/frame.png", FILE_DIGEST, 7, "gaussian-fixture")
        self.assertEqual(stable_sample_seed(*args), stable_sample_seed(*args))
        self.assertTrue(np.array_equal(deterministic_noise_fixture(*args, (3, 8, 8)), deterministic_noise_fixture(*args, (3, 8, 8))))

    def test_noise_is_bitwise_stable_across_fresh_process(self) -> None:
        code = (
            "import hashlib; from core.reproducibility import deterministic_noise_fixture; "
            f"d={FILE_DIGEST!r}; a=deterministic_noise_fixture('Train/Abuse/frame.png',d,7,'gaussian-fixture',(3,8,8)); "
            "print(hashlib.sha256(a.tobytes()).hexdigest())"
        )
        outputs = [
            subprocess.check_output([sys.executable, "-c", code], cwd=REPO_ROOT, text=True).strip()
            for _ in range(2)
        ]
        self.assertEqual(outputs[0], outputs[1])

    def test_noise_is_stable_across_worker_counts(self) -> None:
        def make(index: int) -> bytes:
            return deterministic_noise_fixture(
                f"Train/Abuse/frame-{index}.png", FILE_DIGEST, 7, "gaussian-fixture", (3, 8, 8)
            ).tobytes()

        serial = [make(index) for index in range(8)]
        with ThreadPoolExecutor(max_workers=4) as executor:
            parallel = list(executor.map(make, range(8)))
        self.assertEqual(serial, parallel)

    def test_global_seed_repeats_python_numpy_and_torch(self) -> None:
        seed_everything(11)
        first_numpy = np.random.rand(4)
        first_torch = torch.rand(4)
        seed_everything(11)
        self.assertTrue(np.array_equal(first_numpy, np.random.rand(4)))
        self.assertTrue(torch.equal(first_torch, torch.rand(4)))


class DeviceTests(unittest.TestCase):
    def test_no_silent_cpu_fallback(self) -> None:
        if torch.backends.mps.is_available():
            device, report = select_device(prefer_mps=True, allow_cpu_fallback=False)
            self.assertEqual(device.type, "mps")
            self.assertEqual(report.selected, "mps")
        else:
            with self.assertRaisesRegex(RuntimeError, "refusing silent CPU fallback"):
                select_device(prefer_mps=True, allow_cpu_fallback=False)


class ProvenanceTests(unittest.TestCase):
    def good_record(self) -> dict:
        return {
            "run_id": "fixture-run",
            "run_kind": "smoke",
            "config_digest": "a" * 64,
            "code_revision": "fixture-revision",
            "seed": 0,
            "package_versions": {"torch": torch.__version__},
            "dataset_manifest_digest": "b" * 64,
            "annotation_version": "fixture-v1",
            "environment_digest": "c" * 64,
            "hardware": {"device": "fixture"},
            "metric_artifact_paths": ["metrics.json"],
        }

    def test_required_fields_match_contract(self) -> None:
        self.assertEqual(set(self.good_record()), REQUIRED_PROVENANCE_FIELDS)
        self.assertEqual(validate_provenance(self.good_record()), [])

    def test_missing_field_refuses_closure(self) -> None:
        record = self.good_record()
        record.pop("annotation_version")
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(ValueError, "annotation_version"):
                finalize_provenance(record, Path(temporary) / "provenance.json")

    def test_completed_provenance_is_immutable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "provenance.json"
            digest = finalize_provenance(self.good_record(), path)
            self.assertEqual(digest, hashlib.sha256(path.read_bytes()).hexdigest())
            with self.assertRaises(FileExistsError):
                finalize_provenance(self.good_record(), path)
            self.assertEqual(json.loads(path.read_text()), self.good_record())


if __name__ == "__main__":
    unittest.main()
