from __future__ import annotations

import inspect
import math
import unittest

import numpy as np
from skimage.metrics import peak_signal_noise_ratio, structural_similarity

from eval.image_quality import psnr, ssim


# These settings and arrays are fixture-only validation inputs. They are not
# experiment defaults, registered study parameters, or research results.
FIXTURE_SSIM_OPTIONS = {
    "data_range": 1.0,
    "channel_axis": -1,
    "win_size": 7,
    "gaussian_weights": False,
    "sigma": 1.5,
    "use_sample_covariance": True,
    "k1": 0.01,
    "k2": 0.03,
}


def fixture_only_pair() -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(20260720)
    clean = rng.random((9, 11, 3), dtype=np.float32)
    candidate = np.clip(clean * np.float32(0.85) + np.float32(0.04), 0.0, 1.0)
    return clean, candidate.astype(np.float32, copy=False)


class ImageQualityTests(unittest.TestCase):
    def test_psnr_matches_hand_calculation(self) -> None:
        clean = np.zeros((7, 7, 3), dtype=np.float32)
        candidate = np.full_like(clean, 0.5)
        expected = 10.0 * math.log10(1.0 / 0.25)
        self.assertAlmostEqual(psnr(clean, candidate, data_range=1.0), expected, places=6)

    def test_psnr_matches_direct_scikit_image_call(self) -> None:
        clean, candidate = fixture_only_pair()
        expected = peak_signal_noise_ratio(clean, candidate, data_range=1.0)
        self.assertAlmostEqual(psnr(clean, candidate, data_range=1.0), float(expected), places=12)

    def test_ssim_matches_direct_scikit_image_call(self) -> None:
        clean, candidate = fixture_only_pair()
        expected = structural_similarity(
            clean,
            candidate,
            data_range=FIXTURE_SSIM_OPTIONS["data_range"],
            channel_axis=FIXTURE_SSIM_OPTIONS["channel_axis"],
            win_size=FIXTURE_SSIM_OPTIONS["win_size"],
            gaussian_weights=FIXTURE_SSIM_OPTIONS["gaussian_weights"],
            sigma=FIXTURE_SSIM_OPTIONS["sigma"],
            use_sample_covariance=FIXTURE_SSIM_OPTIONS["use_sample_covariance"],
            K1=FIXTURE_SSIM_OPTIONS["k1"],
            K2=FIXTURE_SSIM_OPTIONS["k2"],
            gradient=False,
            full=False,
        )
        actual = ssim(clean, candidate, **FIXTURE_SSIM_OPTIONS)
        self.assertAlmostEqual(actual, float(expected), places=12)

    def test_ssim_identical_image_hand_invariant_is_one(self) -> None:
        clean, _ = fixture_only_pair()
        self.assertEqual(ssim(clean, clean.copy(), **FIXTURE_SSIM_OPTIONS), 1.0)

    def test_ssim_nontrivial_constant_pair_matches_independent_formula(self) -> None:
        clean = np.full((9, 11, 3), 0.2, dtype=np.float32)
        candidate = np.full_like(clean, 0.4)
        options = dict(FIXTURE_SSIM_OPTIONS)
        options["gaussian_weights"] = False
        c1 = (options["k1"] * options["data_range"]) ** 2
        expected = (2.0 * 0.2 * 0.4 + c1) / (0.2**2 + 0.4**2 + c1)
        self.assertAlmostEqual(ssim(clean, candidate, **options), expected, places=6)

    def test_metrics_require_clean_reference_first_and_explicit_options(self) -> None:
        clean, candidate = fixture_only_pair()
        forward = psnr(clean, candidate, data_range=1.0)
        reverse = psnr(candidate, clean, data_range=1.0)
        # Symmetric fixture metrics cannot detect argument reversal numerically;
        # the semantic order is enforced by the public parameter names.
        self.assertEqual(forward, reverse)
        self.assertEqual(list(inspect.signature(psnr).parameters)[:2], ["clean_reference", "candidate"])
        self.assertEqual(list(inspect.signature(ssim).parameters)[:2], ["clean_reference", "candidate"])
        for function in (psnr, ssim):
            for parameter in inspect.signature(function).parameters.values():
                self.assertIs(parameter.default, inspect.Parameter.empty)

    def test_shape_dtype_nonfinite_and_range_mismatches_are_rejected(self) -> None:
        clean, candidate = fixture_only_pair()
        with self.assertRaisesRegex(ValueError, "identical shapes"):
            psnr(clean, candidate[:, :-1], data_range=1.0)
        with self.assertRaisesRegex(TypeError, "float32"):
            psnr(clean, candidate.astype(np.float64), data_range=1.0)
        nonfinite = candidate.copy()
        nonfinite[0, 0, 0] = np.inf
        with self.assertRaisesRegex(ValueError, "finite"):
            psnr(clean, nonfinite, data_range=1.0)
        out_of_range = candidate.copy()
        out_of_range[0, 0, 0] = -0.1
        with self.assertRaisesRegex(ValueError, r"\[0,1\]"):
            ssim(clean, out_of_range, **FIXTURE_SSIM_OPTIONS)

    def test_metric_options_are_validated_explicitly(self) -> None:
        clean, candidate = fixture_only_pair()
        with self.assertRaisesRegex(ValueError, "data_range"):
            psnr(clean, candidate, data_range=0.0)
        with self.assertRaisesRegex(ValueError, "must equal 1.0"):
            psnr(clean, candidate, data_range=255.0)
        options = dict(FIXTURE_SSIM_OPTIONS)
        options["win_size"] = 4
        with self.assertRaisesRegex(ValueError, "win_size"):
            ssim(clean, candidate, **options)
        options = dict(FIXTURE_SSIM_OPTIONS)
        options["channel_axis"] = 0
        with self.assertRaisesRegex(ValueError, "channel_axis"):
            ssim(clean, candidate, **options)
        options = dict(FIXTURE_SSIM_OPTIONS)
        options["k2"] = float("nan")
        with self.assertRaisesRegex(ValueError, "k2"):
            ssim(clean, candidate, **options)


if __name__ == "__main__":
    unittest.main()
