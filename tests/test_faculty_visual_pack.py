from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np
import yaml

from data.faculty_visual_pack import render_faculty_visual_pack


class FacultyVisualPackTests(unittest.TestCase):
    def test_renders_three_predeclared_video_examples_with_temporal_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            video_root = root / "Datasets/UCF Crime Official/raw/UCF_Crimes"
            examples = [
                ("example_01_abuse", "Abuse", "Abuse001_x264", 3, [1, 5]),
                ("example_02_road", "RoadAccidents", "RoadAccidents001_x264", 4, [2, 6]),
                ("example_03_robbery", "Robbery", "Robbery001_x264", 5, [3, 7]),
            ]
            for _, label, video_id, _, _ in examples:
                directory = video_root / "Videos" / label
                directory.mkdir(parents=True, exist_ok=True)
                writer = cv2.VideoWriter(
                    str(directory / f"{video_id}.mp4"),
                    cv2.VideoWriter_fourcc(*"mp4v"),
                    10.0,
                    (16, 12),
                )
                self.assertTrue(writer.isOpened())
                for value in range(10):
                    writer.write(np.full((12, 16, 3), value * 20, dtype=np.uint8))
                writer.release()

            annotation_path = (
                root
                / "Datasets/UCF Crime Official/annotations/Temporal_Anomaly_Annotation_For_Testing_Videos/Txt_formate/Temporal_Anomaly_Annotation.txt"
            )
            annotation_path.parent.mkdir(parents=True)
            annotation_path.write_text(
                "\n".join(
                    f"{video_id}.mp4  {label}  {interval_[0]}  {interval_[1]}  -1  -1"
                    for _, label, video_id, _, interval_ in examples
                )
                + "\n",
                encoding="utf-8",
            )
            config = {
                "schema_version": "1.0.0",
                "kind": "faculty_progress_visual_pack",
                "decision": "D-25",
                "run_class": "faculty_preview",
                "status": "PRESENTATION_ONLY_NOT_RESEARCH_EVIDENCE",
                "video_root": "Datasets/UCF Crime Official/raw/UCF_Crimes",
                "official_annotation_text": annotation_path.relative_to(root).as_posix(),
                "output_root": "results/faculty_progress/fixture-pack",
                "display_width": 32,
                "global_seed": 9,
                "scope_assertions": {
                    "training_performed": False,
                    "learned_model_rendered": False,
                    "metric_or_benefit_claim_made": False,
                    "pixel_or_instance_mask_rendered": False,
                    "raw_redistribution_authorized": False,
                },
                "examples": [
                    {
                        "id": identifier,
                        "video_relative_path": f"Videos/{label}/{video_id}.mp4",
                        "expected_label": label,
                        "expected_source_video_id": video_id,
                        "expected_frame_index": frame_index,
                        "expected_interval": interval_,
                    }
                    for identifier, label, video_id, frame_index, interval_ in examples
                ],
                "preview_noise": {
                    "family": "gaussian",
                    "sigma_8bit": 25.0,
                    "mean_8bit": 0.0,
                    "sampling_unit": "element",
                    "clipping": "clip_0_1",
                },
                "preview_restoration": {
                    "output_policy": "clip_0_1",
                    "median": {
                        "kernel_size": 3,
                        "border_policy": "opencv_median_fixed_replicate",
                    },
                    "bilateral": {
                        "diameter": 3,
                        "sigma_color": 0.1,
                        "sigma_space": 1.0,
                        "border_type": "reflect_101",
                    },
                },
            }
            config_path = root / "faculty-preview.yaml"
            config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

            output = render_faculty_visual_pack(root, config_path)
            manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(len(manifest["examples"]), 3)
            self.assertFalse(manifest["scope_assertions"]["training_performed"])
            self.assertFalse(manifest["scope_assertions"]["pixel_or_instance_mask_rendered"])
            self.assertTrue((output / "faculty_progress_contact_sheet.png").is_file())
            for example in manifest["examples"]:
                self.assertTrue(example["inside_official_interval"])
                self.assertEqual(example["source_frame_resolution"], [16, 12])
                for path in example["rendered_files"].values():
                    self.assertTrue((output / path).is_file())
            with self.assertRaises(FileExistsError):
                render_faculty_visual_pack(root, config_path)
