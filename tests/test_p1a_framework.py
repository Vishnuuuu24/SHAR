from __future__ import annotations

import csv
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from core.run_lifecycle import RunLifecycle, artifact_digest
from data.grouping import SourceGroupedSampler, source_grouped_split
from data.manifest import load_manifest
from eval.metrics import classification_metrics, video_clustered_macro_f1_ci


REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = REPO_ROOT / "tests/fixtures/p1a"
MANIFEST = FIXTURE_ROOT / "manifest.csv"


def provenance(run_id: str) -> dict:
    return {
        "run_id": run_id,
        "run_kind": "smoke",
        "config_digest": "a" * 64,
        "code_revision": "fixture-revision",
        "seed": 0,
        "package_versions": {"framework": "fixture"},
        "dataset_manifest_digest": hashlib.sha256(MANIFEST.read_bytes()).hexdigest(),
        "annotation_version": "fixture-v1",
        "environment_digest": "b" * 64,
        "hardware": {"device": "fixture"},
        "metric_artifact_paths": ["aggregate.json", "verdict.json"],
    }


class ManifestTests(unittest.TestCase):
    def test_fixture_manifest_loads_and_digests_match(self) -> None:
        rows = load_manifest(MANIFEST, {"fixture": FIXTURE_ROOT}, verify_files=True, verify_digests=True)
        self.assertEqual(len(rows), 4)
        self.assertEqual({row.label for row in rows}, {"Abuse", "Normal"})

    def test_manifest_requires_configured_root(self) -> None:
        with self.assertRaisesRegex(ValueError, "no configured root"):
            load_manifest(MANIFEST, {}, verify_files=True)

    def test_manifest_rejects_header_drift_and_digest_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bad_header = Path(temporary) / "bad-header.csv"
            lines = MANIFEST.read_text().splitlines()
            bad_header.write_text(lines[0].replace("filepath,source_dataset", "source_dataset,filepath") + "\n")
            with self.assertRaisesRegex(ValueError, "header/order"):
                load_manifest(bad_header, {"fixture": FIXTURE_ROOT}, verify_files=False)

            bad_digest = Path(temporary) / "bad-digest.csv"
            bad_digest.write_text(MANIFEST.read_text().replace("c74b2e25", "074b2e25", 1))
            with self.assertRaisesRegex(ValueError, "content digest mismatch"):
                load_manifest(bad_digest, {"fixture": FIXTURE_ROOT}, verify_digests=True)


class GroupingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.rows = load_manifest(MANIFEST, {"fixture": FIXTURE_ROOT}, verify_digests=True)

    def test_grouped_split_is_deterministic_stratified_and_leak_free(self) -> None:
        first = source_grouped_split(self.rows, validation_fraction=0.5, seed=3)
        second = source_grouped_split(self.rows, validation_fraction=0.5, seed=3)
        self.assertEqual(first, second)
        train_groups = {(self.rows[index].source_dataset, self.rows[index].source_video_id) for index in first.train_indices}
        validation_groups = {
            (self.rows[index].source_dataset, self.rows[index].source_video_id) for index in first.validation_indices
        }
        self.assertFalse(train_groups & validation_groups)
        self.assertEqual(first.class_counts["Abuse"], {"train": 1, "validation": 1})
        self.assertEqual(first.class_counts["Normal"], {"train": 1, "validation": 1})

    def test_grouped_split_rejects_outer_test_rows(self) -> None:
        test_row = type(self.rows[0])(**{**self.rows[0].to_dict(), "split": "test"})
        with self.assertRaisesRegex(ValueError, "only outer-Train"):
            source_grouped_split([test_row], validation_fraction=0.1, seed=0)

    def test_grouped_split_chooses_closest_uneven_group(self) -> None:
        base = self.rows[0]
        uneven = []
        for video, count in (("large", 80), ("small-a", 10), ("small-b", 10)):
            for frame in range(count):
                uneven.append(
                    type(base)(
                        **{
                            **base.to_dict(),
                            "filepath": f"files/{video}-{frame}.txt",
                            "source_video_id": video,
                            "source_frame_index": frame,
                            "file_digest": f"{frame:064x}",
                        }
                    )
                )
        split = source_grouped_split(uneven, validation_fraction=0.1, seed=0)
        self.assertEqual(len(split.validation_indices), 10)
        self.assertEqual(len(split.train_indices), 90)

    def test_source_grouped_sampler_keeps_each_group_contiguous(self) -> None:
        rows = self.rows + self.rows
        indices = list(SourceGroupedSampler(rows, list(range(len(rows))), seed=4, shuffle=True))
        positions: dict[str, list[int]] = {}
        for position, index in enumerate(indices):
            positions.setdefault(rows[index].source_video_id, []).append(position)
        for values in positions.values():
            self.assertEqual(values, list(range(min(values), max(values) + 1)))


class MetricTests(unittest.TestCase):
    def test_hand_calculated_multiclass_metrics(self) -> None:
        result = classification_metrics(
            ["Abuse", "Abuse", "Normal", "Normal"],
            ["Abuse", "Normal", "Normal", "Normal"],
            ["Abuse", "Normal"],
        )
        self.assertEqual(result["confusion_matrix"], [[1, 1], [0, 2]])
        self.assertAlmostEqual(result["accuracy"], 0.75)
        self.assertAlmostEqual(result["per_class"]["Abuse"]["f1"], 2 / 3)
        self.assertAlmostEqual(result["per_class"]["Normal"]["f1"], 0.8)
        self.assertAlmostEqual(result["macro_f1"], (2 / 3 + 0.8) / 2)

    def test_bootstrap_resamples_source_videos(self) -> None:
        result = video_clustered_macro_f1_ci(
            ["Abuse", "Abuse", "Normal", "Normal"],
            ["Abuse", "Normal", "Normal", "Normal"],
            ["A1", "A2", "N1", "N2"],
            ["Abuse", "Normal"],
            iterations=200,
            seed=5,
        )
        self.assertEqual(result["resampling_unit"], "source_video_id")
        self.assertEqual(result["cluster_count"], 4)
        self.assertLessEqual(result["lower_95"], result["estimate"])
        self.assertGreaterEqual(result["upper_95"], result["estimate"])


class RunLifecycleTests(unittest.TestCase):
    def test_lifecycle_is_append_preserving_and_immutable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            lifecycle = RunLifecycle.create(Path(temporary), "fixture-run", provenance("fixture-run"))
            aggregate = {"metric": 1.0}
            lifecycle.append_attempt(
                {
                    "attempt_id": "a1",
                    "seed": 0,
                    "status": "COMPLETED",
                    "started_at": "2026-07-20T00:00:00Z",
                    "finished_at": "2026-07-20T00:00:01Z",
                    "reason": "fixture",
                    "hardware": {"device": "fixture"},
                    "parent_checkpoint": None,
                    "artifact_digest": artifact_digest(aggregate),
                }
            )
            lifecycle.finalize(
                aggregate,
                {
                    "status": "COMPLETED",
                    "verdict": "GOOD_ENOUGH",
                    "claim_state": "NOT_APPLICABLE",
                    "reason": "fixture passed",
                    "next_action": "none",
                    "runtime_seconds": 1.0,
                    "peak_memory_bytes": 0,
                    "storage_bytes": 0,
                    "stop_reason": "completed",
                    "checkpoint_disposition": "not applicable",
                    "summary_artifact_digest": artifact_digest(aggregate),
                },
            )
            with self.assertRaisesRegex(RuntimeError, "immutable"):
                lifecycle.append_attempt(
                    {
                        "attempt_id": "a2",
                        "seed": 1,
                        "status": "FAILED",
                        "started_at": "2026-07-20T00:00:01Z",
                        "finished_at": "2026-07-20T00:00:02Z",
                        "reason": "must fail",
                        "hardware": {},
                        "parent_checkpoint": None,
                        "artifact_digest": "a" * 64,
                    }
                )

    def test_lifecycle_refuses_missing_provenance_and_running_attempt(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bad = provenance("bad")
            bad.pop("annotation_version")
            with self.assertRaisesRegex(ValueError, "annotation_version"):
                RunLifecycle.create(Path(temporary), "bad", bad)

            lifecycle = RunLifecycle.create(Path(temporary), "running", provenance("running"))
            lifecycle.append_attempt(
                {
                    "attempt_id": "a1",
                    "seed": 0,
                    "status": "RUNNING",
                    "started_at": "2026-07-20T00:00:00Z",
                    "finished_at": None,
                    "reason": "fixture",
                    "hardware": {},
                    "parent_checkpoint": None,
                    "artifact_digest": None,
                }
            )
            with self.assertRaisesRegex(ValueError, "RUNNING"):
                lifecycle.finalize(
                    {},
                    {
                        "status": "COMPLETED",
                        "verdict": "GOOD",
                        "claim_state": "NOT_APPLICABLE",
                        "reason": "fixture",
                        "next_action": "none",
                        "runtime_seconds": 0,
                        "peak_memory_bytes": 0,
                        "storage_bytes": 0,
                        "stop_reason": "completed",
                        "checkpoint_disposition": "not applicable",
                        "summary_artifact_digest": artifact_digest({}),
                    },
                )

    def test_lifecycle_rejects_bad_status_verdict_and_summary_digest(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            aggregate = {"metric": 1.0}
            lifecycle = RunLifecycle.create(Path(temporary), "bad-verdict", provenance("bad-verdict"))
            lifecycle.append_attempt(
                {
                    "attempt_id": "a1",
                    "seed": 0,
                    "status": "COMPLETED",
                    "started_at": "2026-07-20T00:00:00Z",
                    "finished_at": "2026-07-20T00:00:01Z",
                    "reason": "fixture",
                    "hardware": {},
                    "parent_checkpoint": None,
                    "artifact_digest": artifact_digest(aggregate),
                }
            )
            verdict = {
                "status": "COMPLETED",
                "verdict": "INVALID",
                "claim_state": "NOT_APPLICABLE",
                "reason": "fixture",
                "next_action": "none",
                "runtime_seconds": 1,
                "peak_memory_bytes": 0,
                "storage_bytes": 0,
                "stop_reason": "completed",
                "checkpoint_disposition": "not applicable",
                "summary_artifact_digest": "0" * 64,
            }
            with self.assertRaisesRegex(ValueError, "status/verdict"):
                lifecycle.finalize(aggregate, verdict)


if __name__ == "__main__":
    unittest.main()
