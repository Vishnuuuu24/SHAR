from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path

import numpy as np
import yaml

from core.p2a_conventions import (
    ConventionValidationError,
    load_frozen_p2a_conventions,
    unresolved_convention_fields,
)
from data.degradations import SampleKey, apply_degradation
from eval.image_quality import psnr, ssim
from models.restoration import RESTORATION_METHODS, restore_image


ROOT = Path(__file__).resolve().parents[1]
SCAFFOLD = ROOT / "configs/p2a_scaffold.yaml"


def fixture_only_frozen_document() -> dict:
    """Fixture choices test interfaces only; they are not experiment values."""
    document = yaml.safe_load(SCAFFOLD.read_text(encoding="utf-8"))
    document["status"] = "OWNER_APPROVED"
    document["approval"] = {
        "state": "OWNER_APPROVED",
        "owner": "synthetic-test-owner-not-an-experiment-approval",
        "approved_at": "2026-07-21T00:00:00+05:30",
        "decision_record": "D-25",
    }
    document["experiment_image_contract"] = {
        "color": "RGB",
        "layout": "HWC",
        "dtype": "float32",
        "range": [0.0, 1.0],
        "clipping_point": "fixture_only_explicit_transform_boundary",
        "quantization_point": "fixture_only_nlm_boundary",
        "border_mode": "fixture_only_per_method",
    }
    d = document["degradations"]
    d["gaussian"].update(mean_8bit=0.0, sampling_unit="element", clipping="clip_0_1")
    d["salt_and_pepper"].update(
        salt_probability_given_corruption=0.5,
        salt_value=1.0,
        pepper_value=0.0,
        density_mode={"owner_selection": "bernoulli", "implemented_capabilities": ["bernoulli"]},
        sampling_unit="pixel_shared_channels",
        clipping="clip_0_1",
    )
    d["speckle"].update(
        gaussian_mean=0.0,
        model={"owner_selection": "x_times_one_plus_gaussian", "implemented_capabilities": ["x_times_one_plus_gaussian"]},
        sampling_unit="element",
        clipping="clip_0_1",
    )
    d["low_light"].update(
        gaussian_mean_8bit=0.0,
        operation_order="gamma_then_gaussian",
        clipping_sequence={"owner_selection": "clip_after_each_stage", "implemented_capabilities": ["clip_after_each_stage"]},
        noise_sampling_unit="element",
        clipping="clip_0_1",
    )
    r = document["classical_restoration"]
    r["median"] = {"kernel_size": 3, "border_policy": {"owner_selection": "opencv_median_fixed_replicate", "implemented_capabilities": ["opencv_median_fixed_replicate"]}}
    r["gaussian_blur"] = {"kernel_size": [3, 5], "sigma_x": 0.8, "sigma_y": 1.1, "border_type": "BORDER_REFLECT_101"}
    r["bilateral"] = {"diameter": 3, "sigma_color": 0.1, "sigma_space": 1.5, "border_type": "BORDER_REFLECT"}
    r["nlm"] = {
        "h_luminance": 3.0,
        "h_color": 3.0,
        "template_window_size": 3,
        "search_window_size": 7,
        "quantization": {"owner_selection": "round_to_nearest_uint8", "implemented_capabilities": ["round_to_nearest_uint8"]},
        "color_boundary": {"owner_selection": "rgb_to_bgr_for_opencv_nlm", "implemented_capabilities": ["rgb_to_bgr_for_opencv_nlm"]},
        "border_policy": {"owner_selection": "opencv_nlm_library_fixed", "implemented_capabilities": ["opencv_nlm_library_fixed"]},
    }
    r["output_policy"] = {"owner_selection": "clip_0_1", "implemented_capabilities": ["clip_0_1", "reject_out_of_range"]}
    document["image_quality"] = {
        "psnr": {"data_range": 1.0},
        "ssim": {"data_range": 1.0, "channel_axis": -1, "win_size": 7, "gaussian_weights": False, "sigma": 1.5, "use_sample_covariance": True, "k1": 0.01, "k2": 0.03},
    }
    return document


class FrozenConventionLoaderTests(unittest.TestCase):
    def load_document(self, document: dict):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "conventions.yaml"
            path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
            return load_frozen_p2a_conventions(path)

    def test_current_scaffold_fails_closed_on_owner_placeholders(self) -> None:
        unresolved = unresolved_convention_fields(SCAFFOLD)
        self.assertIn("$.approval.owner", unresolved)
        self.assertIn("$.experiment_image_contract.color", unresolved)
        self.assertIn("$.image_quality.ssim.k2", unresolved)
        with self.assertRaisesRegex(ConventionValidationError, "unresolved placeholder"):
            load_frozen_p2a_conventions(SCAFFOLD)

    def test_validated_output_calls_every_target_api(self) -> None:
        frozen = self.load_document(fixture_only_frozen_document())
        self.assertEqual(len(frozen.degradation_specs), 10)
        self.assertEqual(set(frozen.restoration_parameters), set(RESTORATION_METHODS))
        image = np.random.default_rng(7).random((9, 11, 3), dtype=np.float32)
        sample = SampleKey("fixture/frame.png", "a" * 64, 7)
        for spec in frozen.degradation_specs:
            output = apply_degradation(image, spec=spec, sample=sample)
            self.assertEqual(output.shape, image.shape)
        for method in RESTORATION_METHODS:
            output = restore_image(image, **frozen.restoration_arguments(method))
            self.assertEqual(output.shape, image.shape)
        candidate = np.clip(image * np.float32(0.9), 0.0, 1.0)
        self.assertIsInstance(psnr(image, candidate, **frozen.psnr_options), float)
        self.assertEqual(ssim(image, image, **frozen.ssim_options), 1.0)

    def test_exact_schema_and_capability_drift_are_rejected(self) -> None:
        extra = fixture_only_frozen_document()
        extra["unexpected"] = True
        with self.assertRaisesRegex(ConventionValidationError, "keys mismatch"):
            self.load_document(extra)
        drift = fixture_only_frozen_document()
        drift["degradations"]["speckle"]["model"]["implemented_capabilities"].append("unsupported")
        with self.assertRaisesRegex(ConventionValidationError, "implemented_capabilities"):
            self.load_document(drift)
        unavailable = fixture_only_frozen_document()
        unavailable["classical_restoration"]["output_policy"]["owner_selection"] = "unsupported"
        with self.assertRaisesRegex(ConventionValidationError, "not implemented"):
            self.load_document(unavailable)

    def test_approval_metadata_is_mandatory_and_timezone_aware(self) -> None:
        wrong_state = fixture_only_frozen_document()
        wrong_state["approval"]["state"] = "NOT_APPROVED"
        with self.assertRaisesRegex(ConventionValidationError, "OWNER_APPROVED"):
            self.load_document(wrong_state)
        naive_time = fixture_only_frozen_document()
        naive_time["approval"]["approved_at"] = "2026-07-21T00:00:00"
        with self.assertRaisesRegex(ConventionValidationError, "explicit timezone"):
            self.load_document(naive_time)
        scaffold_decision = fixture_only_frozen_document()
        scaffold_decision["approval"]["decision_record"] = "D-23"
        with self.assertRaisesRegex(ConventionValidationError, "later convention-freeze"):
            self.load_document(scaffold_decision)

    def test_placeholder_forms_and_duplicate_yaml_keys_are_rejected(self) -> None:
        for marker in ("owner_required", "TBD", "${OWNER_VALUE}", "<fill-me>"):
            with self.subTest(marker=marker):
                document = fixture_only_frozen_document()
                document["experiment_image_contract"]["border_mode"] = marker
                with self.assertRaisesRegex(ConventionValidationError, "unresolved placeholder"):
                    self.load_document(document)
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "duplicate.yaml"
            path.write_text("schema_version: 1.0.0\nschema_version: 1.0.0\n", encoding="utf-8")
            with self.assertRaisesRegex(ConventionValidationError, "duplicate YAML key"):
                load_frozen_p2a_conventions(path)

    def test_module_specific_invalid_values_are_rejected_before_calls(self) -> None:
        invalid = fixture_only_frozen_document()
        invalid["classical_restoration"]["gaussian_blur"]["kernel_size"] = [4, 5]
        with self.assertRaisesRegex(ConventionValidationError, "odd integer"):
            self.load_document(invalid)
        invalid = fixture_only_frozen_document()
        invalid["image_quality"]["ssim"]["data_range"] = 255
        with self.assertRaisesRegex(ConventionValidationError, "must equal 1.0"):
            self.load_document(invalid)
        invalid = fixture_only_frozen_document()
        invalid["degradations"]["low_light"]["operation_order"] = "unsupported"
        with self.assertRaisesRegex(ConventionValidationError, "unsupported degradation convention"):
            self.load_document(invalid)


if __name__ == "__main__":
    unittest.main()
