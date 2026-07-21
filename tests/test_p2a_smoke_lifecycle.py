from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from core.run_lifecycle import RunLifecycle
from scripts.check_repository import audit_immutable_artifacts
from scripts.smoke_p2a_scaffold import _finalize_failure


class P2ASmokeFailureLifecycleTests(unittest.TestCase):
    def test_exception_path_closes_failed_attempt_and_authenticates_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_id = "p2a-failure-fixture"
            lifecycle = RunLifecycle.create(
                root / "results/p2a",
                run_id,
                {
                    "run_id": run_id,
                    "run_kind": "code_smoke",
                    "config_digest": "a" * 64,
                    "code_revision": "fixture",
                    "seed": 0,
                    "package_versions": {},
                    "dataset_manifest_digest": "b" * 64,
                    "annotation_version": "not-applicable-fixture",
                    "environment_digest": "c" * 64,
                    "hardware": {"device": "fixture"},
                    "metric_artifact_paths": ["aggregate.json", "verdict.json"],
                },
            )
            started_at = datetime.now(timezone.utc)
            common = {
                "attempt_id": "synthetic-fixture-1",
                "seed": 0,
                "started_at": started_at.isoformat(),
                "reason": "fixture failure-path test",
                "hardware": {"device": "fixture"},
                "parent_checkpoint": None,
            }
            lifecycle.append_attempt(
                {
                    **common,
                    "status": "RUNNING",
                    "finished_at": None,
                    "artifact_digest": None,
                    "artifact_path": None,
                }
            )
            _finalize_failure(lifecycle, common, started_at, ValueError("fixture failure"))

            events = [
                json.loads(line)
                for line in lifecycle.attempts_path.read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual([event["status"] for event in events], ["RUNNING", "FAILED"])
            self.assertEqual(
                events[-1]["artifact_digest"],
                hashlib.sha256((lifecycle.run_directory / "aggregate.json").read_bytes()).hexdigest(),
            )
            verdict = json.loads(
                (lifecycle.run_directory / "verdict.json").read_text(encoding="utf-8")
            )
            self.assertEqual(verdict["status"], "FAILED")
            self.assertTrue(lifecycle.complete_marker.is_file())
            _, errors, _ = audit_immutable_artifacts(root)
            self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
