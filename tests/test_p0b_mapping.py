from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from data.ucf_intervals import (
    FrameReference,
    OfficialTemporalAnnotation,
    FrameInterval,
    map_ucf_frame_references,
    parse_kaggle_frame_relative_path,
    parse_official_temporal_annotations,
    stream_map_ucf_frame_references,
)


def annotation(source_video_id: str, label: str, *intervals: tuple[int, int]) -> OfficialTemporalAnnotation:
    return OfficialTemporalAnnotation(
        source_video_id=source_video_id,
        label=label,
        intervals=tuple(FrameInterval(*interval) for interval in intervals),
        source_line=1,
    )


def frame(path: str) -> FrameReference:
    return parse_kaggle_frame_relative_path(path)


class OfficialTemporalAnnotationTests(unittest.TestCase):
    def test_parser_preserves_two_inclusive_intervals(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "Temporal_Anomaly_Annotation.txt"
            path.write_text(
                "Arson011_x264.mp4 Arson 150 420 680 1267\n"
                "Normal_Videos_003_x264.mp4 Normal -1 -1 -1 -1\n",
                encoding="utf-8",
            )
            parsed = parse_official_temporal_annotations(path)
        self.assertEqual(parsed["Arson011_x264"].intervals, (FrameInterval(150, 420), FrameInterval(680, 1267)))
        self.assertEqual(parsed["Normal_Videos_003_x264"].intervals, ())

    def test_parser_rejects_ambiguous_or_invalid_rows(self) -> None:
        cases = (
            "Abuse001_x264.mp4 Abuse 1 2 -1\n",
            "Abuse001_x264.mp4 Abuse -1 2 -1 -1\n",
            "Abuse001_x264.mp4 Abuse -1 -1 -1 -1\n",
            "Normal_Videos_001_x264.mp4 Normal 1 2 -1 -1\n",
        )
        for content in cases:
            with self.subTest(content=content), tempfile.TemporaryDirectory() as temporary:
                path = Path(temporary) / "bad.txt"
                path.write_text(content, encoding="utf-8")
                with self.assertRaises(ValueError):
                    parse_official_temporal_annotations(path)


class P0BMappingTests(unittest.TestCase):
    def test_streaming_mapping_preserves_boundaries_without_retaining_rows(self) -> None:
        annotations = {"Abuse001_x264": annotation("Abuse001_x264", "Abuse", (100, 110))}
        result = stream_map_ucf_frame_references(
            iter(
                [
                    frame("Test/Abuse/Abuse001_x264_99.png"),
                    frame("Test/Abuse/Abuse001_x264_100.png"),
                    frame("Test/Abuse/Abuse001_x264_110.png"),
                    frame("Test/Abuse/Abuse001_x264_111.png"),
                ]
            ),
            annotations,
        )
        self.assertTrue(result.ready_for_manifest_materialization)
        self.assertEqual(result.anomalous_test_membership_counts, {"inside": 2, "outside": 2})
        self.assertEqual(result.mapped_row_count, 4)
        self.assertEqual(result.report()["execution_mode"], "streaming_full_local_scan")

    def test_start_minus_one_start_end_end_plus_one_boundary_semantics(self) -> None:
        annotations = {"Abuse001_x264": annotation("Abuse001_x264", "Abuse", (100, 110))}
        result = map_ucf_frame_references(
            [
                frame("Test/Abuse/Abuse001_x264_99.png"),
                frame("Test/Abuse/Abuse001_x264_100.png"),
                frame("Test/Abuse/Abuse001_x264_110.png"),
                frame("Test/Abuse/Abuse001_x264_111.png"),
            ],
            annotations,
        )
        self.assertTrue(result.ready_for_manifest_materialization)
        membership = {item.frame.source_frame_index: item.inside_official_interval for item in result.mapped}
        self.assertEqual(membership, {99: False, 100: True, 110: True, 111: False})
        self.assertEqual(result.report()["interval_boundary_semantics"], "inclusive_start_inclusive_end")

    def test_train_and_normal_rows_remain_null_and_do_not_require_interval_rows(self) -> None:
        result = map_ucf_frame_references(
            [
                frame("Train/Abuse/Abuse999_x264_10.png"),
                frame("Test/NormalVideos/Normal_Videos_999_x264_20.png"),
            ],
            {},
        )
        self.assertTrue(result.ready_for_manifest_materialization)
        self.assertEqual([item.inside_official_interval for item in result.mapped], [None, None])

    def test_missing_or_mismatched_anomalous_annotations_are_quarantined(self) -> None:
        result = map_ucf_frame_references(
            [
                frame("Test/Abuse/Abuse404_x264_20.png"),
                frame("Test/Abuse/Abuse001_x264_20.png"),
            ],
            {"Abuse001_x264": annotation("Abuse001_x264", "Arson", (10, 30))},
        )
        self.assertFalse(result.ready_for_manifest_materialization)
        self.assertEqual(
            [item.reason for item in result.quarantined],
            ["official_annotation_label_mismatch", "missing_official_annotation_for_anomalous_test_source"],
        )
        with self.assertRaisesRegex(ValueError, "quarantined"):
            result.assert_ready_for_manifest_materialization()

    def test_duplicate_frames_and_source_video_outer_split_leakage_fail_closed(self) -> None:
        result = map_ucf_frame_references(
            [
                frame("Test/Abuse/Abuse001_x264_20.png"),
                frame("Train/Abuse/Abuse001_x264_20.png"),
                frame("Test/Arson/Arson001_x264_20.png"),
                frame("Test/Arson/Arson001_x264_20.png"),
            ],
            {
                "Abuse001_x264": annotation("Abuse001_x264", "Abuse", (10, 30)),
                "Arson001_x264": annotation("Arson001_x264", "Arson", (10, 30)),
            },
        )
        self.assertEqual(result.source_split_leakage, {"Abuse001_x264": ("test", "train")})
        self.assertEqual(
            [item.reason for item in result.quarantined],
            [
                "source_video_crosses_outer_splits",
                "duplicate_source_frame",
                "duplicate_source_frame",
                "source_video_crosses_outer_splits",
            ],
        )
        with self.assertRaisesRegex(ValueError, "split leakage"):
            result.assert_ready_for_manifest_materialization()

    def test_filename_contract_is_strict(self) -> None:
        good = frame("Test/NormalVideos/Normal_Videos_003_x264_0.png")
        self.assertEqual((good.split, good.label, good.source_video_id, good.source_frame_index), ("test", "Normal", "Normal_Videos_003_x264", 0))
        for path in (
            "Test/Abuse/not-a-source.png",
            "Test/Abuse/Abuse001_x264_-1.png",
            "Test/Abuse/Abuse001_1.png",
            "Train/Unknown/Unknown001_x264_1.png",
            "Train/Abuse/nested/Abuse001_x264_1.png",
        ):
            with self.subTest(path=path):
                with self.assertRaises(ValueError):
                    parse_kaggle_frame_relative_path(path)


if __name__ == "__main__":
    unittest.main()
