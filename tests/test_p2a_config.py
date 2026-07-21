from __future__ import annotations

import inspect
import unittest
from pathlib import Path

import yaml

from eval.image_quality import psnr, ssim


REPO_ROOT = Path(__file__).resolve().parents[1]


class P2AScaffoldConfigTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = yaml.safe_load(
            (REPO_ROOT / "configs/p2a_scaffold.yaml").read_text(encoding="utf-8")
        )

    def test_restoration_config_keys_match_public_api_parameter_names(self) -> None:
        restoration = self.config["classical_restoration"]
        self.assertEqual(
            set(restoration),
            {"identity", "median", "gaussian_blur", "bilateral", "nlm", "output_policy"},
        )
        self.assertEqual(restoration["identity"], {"parameters": {}})
        self.assertEqual(set(restoration["median"]), {"kernel_size", "border_policy"})
        self.assertEqual(
            set(restoration["gaussian_blur"]),
            {"kernel_size", "sigma_x", "sigma_y", "border_type"},
        )
        self.assertEqual(
            set(restoration["bilateral"]),
            {"diameter", "sigma_color", "sigma_space", "border_type"},
        )
        self.assertEqual(
            set(restoration["nlm"]),
            {
                "h_luminance",
                "h_color",
                "template_window_size",
                "search_window_size",
                "quantization",
                "color_boundary",
                "border_policy",
            },
        )

    def test_metric_config_keys_match_required_keyword_names(self) -> None:
        quality = self.config["image_quality"]
        self.assertEqual(
            set(quality["psnr"]),
            set(inspect.signature(psnr).parameters) - {"clean_reference", "candidate"},
        )
        self.assertEqual(
            set(quality["ssim"]),
            set(inspect.signature(ssim).parameters) - {"clean_reference", "candidate"},
        )

    def test_degradation_config_exposes_every_unfrozen_semantic(self) -> None:
        degradations = self.config["degradations"]
        self.assertEqual(
            set(degradations["gaussian"]),
            {"sigma_8bit_levels", "mean_8bit", "sampling_unit", "clipping"},
        )
        self.assertEqual(
            set(degradations["salt_and_pepper"]),
            {
                "density_levels",
                "salt_probability_given_corruption",
                "salt_value",
                "pepper_value",
                "density_mode",
                "sampling_unit",
                "clipping",
            },
        )
        self.assertEqual(
            set(degradations["speckle"]),
            {"variance_levels", "gaussian_mean", "model", "sampling_unit", "clipping"},
        )
        self.assertEqual(
            set(degradations["low_light"]),
            {
                "gamma",
                "gaussian_sigma_8bit",
                "gaussian_mean_8bit",
                "operation_order",
                "clipping_sequence",
                "noise_sampling_unit",
                "clipping",
            },
        )


if __name__ == "__main__":
    unittest.main()
