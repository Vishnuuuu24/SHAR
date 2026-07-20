from __future__ import annotations

import unittest

from data.manifest import ManifestRow
from data.views import (
    EVENT_ONLY_VIEW_NAME,
    NOISY_PROXY_VIEW_NAME,
    build_ucf_evaluation_views,
    build_ucf_noisy_proxy_view,
)


ANNOTATION_DIGEST = "a" * 64


def row(
    name: str,
    label: str,
    inside: bool | None,
    *,
    split: str = "test",
    frame: int = 0,
) -> ManifestRow:
    return ManifestRow(
        filepath=f"files/{name}.png",
        source_dataset="fixture_ucf",
        source_video_id=name.split("-")[0],
        source_frame_index=frame,
        label=label,
        label_scope="video_inherited",
        label_source="fixture-folder-snapshot",
        annotation_version="folder-fixture-v1",
        inside_official_interval=inside,
        split=split,
        file_digest=(name.encode().hex() + "0" * 64)[:64],
    )


class EvaluationViewTests(unittest.TestCase):
    def test_event_only_excludes_outside_anomaly_and_keeps_normal(self) -> None:
        rows = [
            row("A-0", "Abuse", True, frame=0),
            row("A-1", "Abuse", False, frame=1),
            row("N-0", "Normal", None, frame=0),
            row("train-0", "Abuse", None, split="train", frame=0),
        ]
        views = build_ucf_evaluation_views(
            rows,
            official_annotation_version="official-fixture-v1",
            official_annotation_digest=ANNOTATION_DIGEST,
            source_dataset="fixture_ucf",
            allow_fixture_source=True,
            fixture_only=True,
        )
        self.assertEqual([item.filepath for item in views.event_only], ["files/A-0.png", "files/N-0.png"])
        self.assertEqual(len(views.noisy_proxy), 3)
        self.assertEqual(views.report["excluded_by_reason_counts"]["outside_official_interval"], 1)
        self.assertEqual(views.report["views"]["event_only"]["name"], EVENT_ONLY_VIEW_NAME)
        self.assertEqual(views.report["views"]["noisy_proxy"]["name"], NOISY_PROXY_VIEW_NAME)
        self.assertTrue(views.report["headline_claim_blocked"])
        self.assertFalse(views.report["ready_for_real_evaluation"])
        self.assertEqual(views.noisy_proxy[0].label_scope, "video_inherited")
        abuse = next(item for item in views.event_only if item.label == "Abuse")
        self.assertEqual(abuse.label_scope, "temporal_interval")
        self.assertEqual(abuse.label_source, "official-fixture-v1")

    def test_unresolved_anomalous_membership_is_a_hard_error(self) -> None:
        with self.assertRaisesRegex(ValueError, "unresolved interval"):
            build_ucf_evaluation_views(
                [row("A-0", "Abuse", None)],
                official_annotation_version="official-fixture-v1",
                official_annotation_digest=ANNOTATION_DIGEST,
                source_dataset="fixture_ucf",
                allow_fixture_source=True,
            )
        self.assertEqual(
            len(
                build_ucf_noisy_proxy_view(
                    [row("A-0", "Abuse", None)],
                    source_dataset="fixture_ucf",
                    allow_fixture_source=True,
                )
            ),
            1,
        )

    def test_contradictory_normal_interval_is_a_hard_error(self) -> None:
        with self.assertRaisesRegex(ValueError, "must be null"):
            build_ucf_noisy_proxy_view(
                [row("N-0", "Normal", True)], source_dataset="fixture_ucf", allow_fixture_source=True
            )
        with self.assertRaisesRegex(ValueError, "must be null"):
            build_ucf_noisy_proxy_view(
                [row("N-0", "Normal", False)], source_dataset="fixture_ucf", allow_fixture_source=True
            )

    def test_missing_frame_identity_and_duplicates_are_rejected(self) -> None:
        missing = row("A-0", "Abuse", True)
        missing = ManifestRow(**{**missing.to_dict(), "source_frame_index": None})
        with self.assertRaisesRegex(ValueError, "source-frame traceability"):
            build_ucf_noisy_proxy_view(
                [missing], source_dataset="fixture_ucf", allow_fixture_source=True
            )
        duplicate = row("A-0", "Abuse", True)
        with self.assertRaisesRegex(ValueError, "duplicate"):
            build_ucf_noisy_proxy_view(
                [duplicate, duplicate], source_dataset="fixture_ucf", allow_fixture_source=True
            )

        drifted = ManifestRow(
            **{
                **duplicate.to_dict(),
                "filepath": "files/drifted-path.png",
                "file_digest": "b" * 64,
            }
        )
        with self.assertRaisesRegex(ValueError, "duplicate source-frame"):
            build_ucf_noisy_proxy_view(
                [duplicate, drifted], source_dataset="fixture_ucf", allow_fixture_source=True
            )

    def test_unknown_label_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "unknown UCF label"):
            build_ucf_noisy_proxy_view(
                [row("X-0", "Unknown", True)], source_dataset="fixture_ucf", allow_fixture_source=True
            )

    def test_non_folder_provenance_input_is_rejected(self) -> None:
        mapped = row("A-0", "Abuse", True)
        mapped = ManifestRow(**{**mapped.to_dict(), "label_scope": "temporal_interval"})
        with self.assertRaisesRegex(ValueError, "video_inherited"):
            build_ucf_noisy_proxy_view(
                [mapped], source_dataset="fixture_ucf", allow_fixture_source=True
            )

    def test_external_test_rows_are_rejected(self) -> None:
        external = row("A-0", "Abuse", True)
        external = ManifestRow(**{**external.to_dict(), "source_dataset": "external"})
        with self.assertRaisesRegex(ValueError, "non-UCF"):
            build_ucf_noisy_proxy_view(
                [row("N-0", "Normal", None), external],
                source_dataset="fixture_ucf",
                allow_fixture_source=True,
            )

    def test_fixture_source_requires_explicit_override(self) -> None:
        with self.assertRaisesRegex(ValueError, "allow_fixture_source"):
            build_ucf_noisy_proxy_view([row("N-0", "Normal", None)], source_dataset="fixture_ucf")


if __name__ == "__main__":
    unittest.main()
