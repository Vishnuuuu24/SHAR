from __future__ import annotations

import inspect
import unittest

import cv2
import numpy as np

from models.restoration import RESTORATION_METHODS, restore_batch, restore_image


# These values exercise implementation contracts only. They are deliberately
# fixture-only and are not registered experiment parameters or research results.
FIXTURE_METHOD_PARAMETERS = {
    "identity": {},
    "median": {
        "kernel_size": 3,
        "border_policy": "opencv_median_fixed_replicate",
    },
    "gaussian_blur": {
        "kernel_size": (3, 5),
        "sigma_x": 0.8,
        "sigma_y": 1.1,
        "border_type": cv2.BORDER_REFLECT_101,
    },
    "bilateral": {
        "diameter": 3,
        "sigma_color": 0.1,
        "sigma_space": 1.5,
        "border_type": cv2.BORDER_REFLECT,
    },
    "nlm": {
        "h_luminance": 3.0,
        "h_color": 3.0,
        "template_window_size": 3,
        "search_window_size": 7,
        "quantization": "round_to_nearest_uint8",
        "color_boundary": "rgb_to_bgr_for_opencv_nlm",
        "border_policy": "opencv_nlm_library_fixed",
    },
}


def fixture_only_image() -> np.ndarray:
    rng = np.random.default_rng(20260720)
    return rng.random((11, 13, 3), dtype=np.float32)


class RestorationContractTests(unittest.TestCase):
    def test_every_registered_method_preserves_contract_and_input(self) -> None:
        self.assertEqual(set(FIXTURE_METHOD_PARAMETERS), set(RESTORATION_METHODS))
        for method, parameters in FIXTURE_METHOD_PARAMETERS.items():
            with self.subTest(method=method):
                image = fixture_only_image()
                before = image.copy()
                output = restore_image(
                    image, method=method, parameters=parameters, output_policy="clip_0_1"
                )
                np.testing.assert_array_equal(image, before)
                self.assertEqual(output.shape, image.shape)
                self.assertEqual(output.dtype, np.float32)
                self.assertTrue(np.isfinite(output).all())
                self.assertGreaterEqual(float(output.min()), 0.0)
                self.assertLessEqual(float(output.max()), 1.0)

    def test_batch_is_exactly_equivalent_to_independent_images(self) -> None:
        first = fixture_only_image()
        second = np.flip(first, axis=1).copy()
        images = np.stack((first, second))
        before = images.copy()
        for method, parameters in FIXTURE_METHOD_PARAMETERS.items():
            with self.subTest(method=method):
                batched = restore_batch(
                    images, method=method, parameters=parameters, output_policy="clip_0_1"
                )
                independent = np.stack(
                    [
                        restore_image(
                            image,
                            method=method,
                            parameters=parameters,
                            output_policy="clip_0_1",
                        )
                        for image in images
                    ]
                )
                np.testing.assert_array_equal(batched, independent)
                np.testing.assert_array_equal(images, before)

    def test_identity_returns_an_independent_exact_copy(self) -> None:
        image = fixture_only_image()
        output = restore_image(
            image, method="identity", parameters={}, output_policy="clip_0_1"
        )
        np.testing.assert_array_equal(output, image)
        self.assertFalse(np.shares_memory(output, image))

    def test_nlm_matches_explicit_rgb_bgr_opencv_boundary(self) -> None:
        image = fixture_only_image()
        parameters = FIXTURE_METHOD_PARAMETERS["nlm"]
        source_uint8_rgb = np.rint(image * np.float32(255.0)).astype(np.uint8)
        source_uint8_bgr = np.ascontiguousarray(source_uint8_rgb[..., ::-1])
        expected_bgr = cv2.fastNlMeansDenoisingColored(
            source_uint8_bgr,
            None,
            parameters["h_luminance"],
            parameters["h_color"],
            parameters["template_window_size"],
            parameters["search_window_size"],
        )
        expected_rgb = np.ascontiguousarray(expected_bgr[..., ::-1]).astype(np.float32) / np.float32(
            255.0
        )
        actual = restore_image(
            image, method="nlm", parameters=parameters, output_policy="clip_0_1"
        )
        np.testing.assert_array_equal(actual, expected_rgb)

    def test_median_gaussian_and_bilateral_match_direct_opencv_calls(self) -> None:
        image = fixture_only_image()
        median = restore_image(
            image,
            method="median",
            parameters=FIXTURE_METHOD_PARAMETERS["median"],
            output_policy="clip_0_1",
        )
        np.testing.assert_array_equal(median, cv2.medianBlur(image, 3))

        gaussian_parameters = FIXTURE_METHOD_PARAMETERS["gaussian_blur"]
        gaussian = restore_image(
            image,
            method="gaussian_blur",
            parameters=gaussian_parameters,
            output_policy="clip_0_1",
        )
        expected_gaussian = cv2.GaussianBlur(
            image,
            (5, 3),
            sigmaX=gaussian_parameters["sigma_x"],
            sigmaY=gaussian_parameters["sigma_y"],
            borderType=gaussian_parameters["border_type"],
        )
        np.testing.assert_array_equal(gaussian, expected_gaussian)

        bilateral_parameters = FIXTURE_METHOD_PARAMETERS["bilateral"]
        bilateral = restore_image(
            image,
            method="bilateral",
            parameters=bilateral_parameters,
            output_policy="clip_0_1",
        )
        expected_bilateral = cv2.bilateralFilter(
            image,
            d=bilateral_parameters["diameter"],
            sigmaColor=bilateral_parameters["sigma_color"],
            sigmaSpace=bilateral_parameters["sigma_space"],
            borderType=bilateral_parameters["border_type"],
        )
        np.testing.assert_array_equal(bilateral, expected_bilateral)

    def test_public_entry_points_have_no_experiment_defaults(self) -> None:
        for function in (restore_image, restore_batch):
            signature = inspect.signature(function)
            self.assertIs(signature.parameters["method"].default, inspect.Parameter.empty)
            self.assertIs(signature.parameters["parameters"].default, inspect.Parameter.empty)
            self.assertIs(signature.parameters["output_policy"].default, inspect.Parameter.empty)

    def test_methods_require_exact_parameter_sets(self) -> None:
        image = fixture_only_image()
        with self.assertRaisesRegex(ValueError, "missing=.*kernel_size"):
            restore_image(image, method="median", parameters={}, output_policy="clip_0_1")
        with self.assertRaisesRegex(ValueError, "unexpected=.*fixture_only"):
            restore_image(
                image,
                method="identity",
                parameters={"fixture_only": 1},
                output_policy="clip_0_1",
            )
        with self.assertRaisesRegex(ValueError, "method must be one of"):
            restore_image(
                image, method="unknown", parameters={}, output_policy="clip_0_1"
            )

    def test_invalid_filter_parameters_are_rejected_before_opencv(self) -> None:
        image = fixture_only_image()
        with self.assertRaisesRegex(ValueError, "odd integer"):
            restore_image(
                image,
                method="median",
                parameters={
                    "kernel_size": 4,
                    "border_policy": "opencv_median_fixed_replicate",
                },
                output_policy="clip_0_1",
            )
        with self.assertRaisesRegex(ValueError, "must be 3 or 5"):
            restore_image(
                image,
                method="median",
                parameters={
                    "kernel_size": 9,
                    "border_policy": "opencv_median_fixed_replicate",
                },
                output_policy="clip_0_1",
            )
        gaussian = dict(FIXTURE_METHOD_PARAMETERS["gaussian_blur"])
        gaussian["sigma_x"] = 0.0
        with self.assertRaisesRegex(ValueError, "sigma_x"):
            restore_image(
                image,
                method="gaussian_blur",
                parameters=gaussian,
                output_policy="clip_0_1",
            )
        nlm = dict(FIXTURE_METHOD_PARAMETERS["nlm"])
        nlm["search_window_size"] = 1
        with self.assertRaisesRegex(ValueError, "search_window_size"):
            restore_image(image, method="nlm", parameters=nlm, output_policy="clip_0_1")

    def test_invalid_images_are_rejected(self) -> None:
        image = fixture_only_image()
        with self.assertRaisesRegex(TypeError, "float32"):
            restore_image(
                image.astype(np.float64),
                method="identity",
                parameters={},
                output_policy="clip_0_1",
            )
        with self.assertRaisesRegex(ValueError, "HWC RGB"):
            restore_image(
                image[:, :, 0], method="identity", parameters={}, output_policy="clip_0_1"
            )
        nonfinite = image.copy()
        nonfinite[0, 0, 0] = np.nan
        with self.assertRaisesRegex(ValueError, "finite"):
            restore_image(
                nonfinite, method="identity", parameters={}, output_policy="clip_0_1"
            )
        out_of_range = image.copy()
        out_of_range[0, 0, 0] = 1.1
        with self.assertRaisesRegex(ValueError, r"\[0,1\]"):
            restore_image(
                out_of_range, method="identity", parameters={}, output_policy="clip_0_1"
            )

    def test_output_policy_is_explicit_and_validated(self) -> None:
        image = fixture_only_image()
        with self.assertRaisesRegex(ValueError, "output_policy"):
            restore_image(image, method="identity", parameters={}, output_policy="implicit")
        output = restore_image(
            image,
            method="identity",
            parameters={},
            output_policy="reject_out_of_range",
        )
        np.testing.assert_array_equal(output, image)


if __name__ == "__main__":
    unittest.main()
