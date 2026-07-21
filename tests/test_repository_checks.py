from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts.check_repository import (
    _artifact_payload,
    audit_immutable_artifacts,
    check_serialized_syntax,
    find_config_placeholders,
    find_markdown_link_issues,
)


class RepositorySyntaxTests(unittest.TestCase):
    def test_json_jsonl_and_yaml_syntax_scan(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "config.yaml").write_text("name: fixture\n", encoding="utf-8")
            (root / "record.json").write_text('{"ok": true}\n', encoding="utf-8")
            (root / "events.jsonl").write_text('{"event": 1}\n{"event": 2}\n', encoding="utf-8")
            self.assertTrue(check_serialized_syntax(root).passed)
            (root / "events.jsonl").write_text('{"event": 1}\nnot-json\n', encoding="utf-8")
            result = check_serialized_syntax(root)
            self.assertFalse(result.passed)
            self.assertIn("events.jsonl:2", result.errors[0])


class MarkdownLinkTests(unittest.TestCase):
    def test_local_links_accept_existing_and_report_missing_targets(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            docs = root / "docs"
            docs.mkdir()
            (docs / "exists.md").write_text("fixture\n", encoding="utf-8")
            index = docs / "index.md"
            index.write_text(
                "[valid](exists.md)\n[anchor](#section)\n[web](https://example.com)\n[bad](missing.md)\n",
                encoding="utf-8",
            )
            self.assertEqual(find_markdown_link_issues(root), ["docs/index.md -> missing.md"])


class PlaceholderTests(unittest.TestCase):
    def test_owner_placeholders_are_reported_without_interpreting_values(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            configs = root / "configs"
            configs.mkdir()
            (configs / "experiment.yaml").write_text(
                "model:\n  hidden_dim: OWNER_PREREGISTRATION_REQUIRED\n  seed: 0\n",
                encoding="utf-8",
            )
            placeholders = find_config_placeholders(root)
            self.assertEqual(len(placeholders), 1)
            self.assertIn("$.model.hidden_dim", placeholders[0])


class ImmutableArtifactAuditTests(unittest.TestCase):
    def _make_closed_run(self, root: Path, run_name: str = "fixture-run") -> Path:
        run = root / "results" / "fixture" / run_name
        run.mkdir(parents=True)
        aggregate = {"metric": 1.0}
        digest = hashlib.sha256(_artifact_payload(aggregate)).hexdigest()
        (run / "run_manifest.json").write_text(
            json.dumps(
                {
                    "run_id": run_name,
                    "metric_artifact_paths": ["aggregate.json", "verdict.json"],
                }
            )
            + "\n",
            encoding="utf-8",
        )
        (run / "aggregate.json").write_bytes(_artifact_payload(aggregate))
        (run / "verdict.json").write_text(
            json.dumps({"summary_artifact_digest": digest}) + "\n", encoding="utf-8"
        )
        (run / "attempts.jsonl").write_text(
            json.dumps(
                {
                    "attempt_id": "fixture-1",
                    "seed": 0,
                    "status": "COMPLETED",
                    "started_at": "2026-07-20T00:00:00Z",
                    "finished_at": "2026-07-20T00:00:01Z",
                    "reason": "fixture",
                    "hardware": {},
                    "parent_checkpoint": None,
                    "artifact_digest": digest,
                    "artifact_path": "aggregate.json",
                }
            )
            + "\n",
            encoding="utf-8",
        )
        closure_names = (
            "run_manifest.json",
            "attempts.jsonl",
            "aggregate.json",
            "verdict.json",
        )
        (run / ".complete").write_text(
            json.dumps(
                {
                    "schema_version": "2.0.0",
                    "completed_at": "2026-07-20T00:00:01Z",
                    "files_sha256": {
                        name: hashlib.sha256((run / name).read_bytes()).hexdigest()
                        for name in closure_names
                    },
                }
            )
            + "\n",
            encoding="utf-8",
        )
        return run

    def test_valid_closure_passes_and_digest_drift_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run = self._make_closed_run(root)
            summary, errors, warnings = audit_immutable_artifacts(root)
            self.assertEqual(summary["complete_run_count"], 1)
            self.assertEqual(errors, [])
            self.assertEqual(warnings, [])

            (run / "aggregate.json").write_text('{"metric":2.0}\n', encoding="utf-8")
            _, errors, _ = audit_immutable_artifacts(root)
            self.assertTrue(any("summary digest" in error for error in errors))

    def test_running_attempt_is_not_a_valid_immutable_closure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run = self._make_closed_run(root)
            attempt = json.loads((run / "attempts.jsonl").read_text(encoding="utf-8"))
            attempt["status"] = "RUNNING"
            (run / "attempts.jsonl").write_text(json.dumps(attempt) + "\n", encoding="utf-8")
            _, errors, _ = audit_immutable_artifacts(root)
            self.assertTrue(any("has no terminal event" in error for error in errors))

    def test_authenticated_closure_detects_manifest_and_attempt_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run = self._make_closed_run(root)
            manifest = json.loads((run / "run_manifest.json").read_text(encoding="utf-8"))
            manifest["config_digest"] = "tampered"
            (run / "run_manifest.json").write_text(json.dumps(manifest) + "\n", encoding="utf-8")
            _, errors, _ = audit_immutable_artifacts(root)
            self.assertTrue(any("digest mismatch for run_manifest.json" in error for error in errors))

            run = self._make_closed_run(root / "second")
            attempt = json.loads((run / "attempts.jsonl").read_text(encoding="utf-8"))
            attempt["seed"] = 99
            (run / "attempts.jsonl").write_text(json.dumps(attempt) + "\n", encoding="utf-8")
            _, errors, _ = audit_immutable_artifacts(root / "second")
            self.assertTrue(any("digest mismatch for attempts.jsonl" in error for error in errors))

    def test_running_then_completed_events_form_a_valid_closure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run = self._make_closed_run(root)
            completed = json.loads((run / "attempts.jsonl").read_text(encoding="utf-8"))
            running = dict(completed)
            running["status"] = "RUNNING"
            running["finished_at"] = None
            running["artifact_digest"] = None
            running["artifact_path"] = None
            (run / "attempts.jsonl").write_text(
                json.dumps(running) + "\n" + json.dumps(completed) + "\n",
                encoding="utf-8",
            )
            complete = json.loads((run / ".complete").read_text(encoding="utf-8"))
            complete["files_sha256"]["attempts.jsonl"] = hashlib.sha256(
                (run / "attempts.jsonl").read_bytes()
            ).hexdigest()
            (run / ".complete").write_text(json.dumps(complete) + "\n", encoding="utf-8")
            _, errors, warnings = audit_immutable_artifacts(root)
            self.assertEqual(errors, [])
            self.assertEqual(warnings, [])

    def test_explicitly_superseded_invalid_closure_is_retained_without_failing_current_audit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run = self._make_closed_run(root)
            (run / "aggregate.json").write_text('{"tampered":true}\n', encoding="utf-8")
            replacement = self._make_closed_run(root, "replacement")
            replacement_aggregate = replacement / "aggregate.json"
            supersession = root / "results" / "fixture" / "supersession.json"
            supersession.write_text(
                json.dumps(
                    {
                        "status": "INVALID",
                        "invalid_artifact": "results/fixture/fixture-run",
                        "replacement_artifact": "results/fixture/replacement",
                        "replacement_aggregate_sha256": hashlib.sha256(
                            replacement_aggregate.read_bytes()
                        ).hexdigest(),
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            summary, errors, warnings = audit_immutable_artifacts(root)
            self.assertEqual(errors, [])
            self.assertEqual(summary["retained_invalid_run_count"], 1)
            self.assertTrue(any("supersession" in warning for warning in warnings))

    def test_unauthenticated_supersession_does_not_waive_invalid_closure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run = self._make_closed_run(root)
            (run / "aggregate.json").write_text('{"tampered":true}\n', encoding="utf-8")
            supersession = root / "results" / "fixture" / "supersession.json"
            supersession.write_text(
                json.dumps(
                    {
                        "status": "INVALID",
                        "invalid_artifact": "results/fixture/fixture-run",
                        "replacement_artifact": "results/fixture/missing",
                        "replacement_aggregate_sha256": "a" * 64,
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            _, errors, _ = audit_immutable_artifacts(root)
            self.assertTrue(any("supersession is not authenticated" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
