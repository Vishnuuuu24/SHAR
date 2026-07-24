from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path

import numpy as np
import torch

from core.reproducibility import stable_sample_seed
from data.degradations import (
    REGISTERED_GAUSSIAN_SIGMA_8BIT,
    REGISTERED_LEVELS,
    REGISTERED_LOW_LIGHT,
    REGISTERED_SALT_PEPPER_DENSITIES,
    REGISTERED_SPECKLE_VARIANCES,
    DegradationSpec,
    SampleKey,
    apply_degradation,
    apply_degradation_batch,
    gaussian_spec,
    identity_spec,
    low_light_spec,
    registered_degradation_specs,
    salt_and_pepper_spec,
    speckle_spec,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
FILE_DIGEST = hashlib.sha256(b"p2a-degradation-fixture").hexdigest()


def fixture_image(height: int = 24, width: int = 25) -> np.ndarray:
    return np.linspace(0.0, 1.0, height * width * 3, dtype=np.float32).reshape(
        height, width, 3
    )


def fixture_specs():
    # These explicit values exercise code paths only; B-007 still owns the
    # future experiment convention freeze.
    return registered_degradation_specs(
        gaussian_mean_8bit=0.0,
        gaussian_sampling_unit="element",
        salt_probability_given_corruption=0.5,
        salt_value=1.0,
        pepper_value=0.0,
        salt_pepper_density_mode="bernoulli",
        salt_pepper_sampling_unit="pixel_shared_channels",
        speckle_gaussian_mean=0.0,
        speckle_model="x_times_one_plus_gaussian",
        speckle_sampling_unit="element",
        low_light_operation_order="gamma_then_gaussian",
        low_light_gaussian_mean_8bit=0.0,
        low_light_clipping_sequence="clip_after_each_stage",
        low_light_noise_sampling_unit="element",
        clipping="clip_0_1",
    )


class WorkerCountFixture(torch.utils.data.Dataset):
    def __len__(self) -> int:
        return 8

    def __getitem__(self, index: int) -> np.ndarray:
        image = fixture_image(12, 13)
        sample = SampleKey(f"Train/Abuse/frame-{index}.png", FILE_DIGEST, 7)
        return np.stack(
            [
                apply_degradation(image, spec=spec, sample=sample)
                for spec in fixture_specs()[1:]
            ],
            axis=0,
        )


def collate_numpy(batch: list[np.ndarray]) -> np.ndarray:
    return np.stack(batch, axis=0)


class RegisteredContractTests(unittest.TestCase):
    def test_registered_levels_match_data_spec(self) -> None:
        self.assertEqual(REGISTERED_GAUSSIAN_SIGMA_8BIT, (10.0, 25.0, 50.0))
        self.assertEqual(REGISTERED_SALT_PEPPER_DENSITIES, (0.02, 0.05, 0.10))
        self.assertEqual(REGISTERED_SPECKLE_VARIANCES, (0.02, 0.05))
        self.assertEqual(dict(REGISTERED_LOW_LIGHT), {"gamma": 2.2, "gaussian_sigma_8bit": 15.0})
        self.assertEqual(set(REGISTERED_LEVELS), {
            "identity", "gaussian", "salt_and_pepper", "speckle", "low_light"
        })
        specs = fixture_specs()
        self.assertEqual(len(specs), 10)
        self.assertEqual(
            [spec.family for spec in specs],
            ["identity"] + ["gaussian"] * 3 + ["salt_and_pepper"] * 3
            + ["speckle"] * 2 + ["low_light"],
        )

    def test_ambiguous_semantics_have_no_hidden_defaults(self) -> None:
        with self.assertRaises(TypeError):
            gaussian_spec(sigma_8bit=10)  # type: ignore[call-arg]
        with self.assertRaises(TypeError):
            salt_and_pepper_spec(density=0.02)  # type: ignore[call-arg]
        with self.assertRaises(TypeError):
            speckle_spec(variance=0.02)  # type: ignore[call-arg]
        with self.assertRaises(TypeError):
            low_light_spec(gamma=2.2, gaussian_sigma_8bit=15)  # type: ignore[call-arg]

    def test_low_light_rejects_non_numeric_registered_values_cleanly(self) -> None:
        with self.assertRaisesRegex(TypeError, "gamma must be numeric"):
            low_light_spec(
                gamma="2.2",  # type: ignore[arg-type]
                gaussian_sigma_8bit=15,
                gaussian_mean_8bit=0.0,
                operation_order="gamma_then_gaussian",
                clipping_sequence="clip_after_each_stage",
                noise_sampling_unit="element",
                clipping="clip_0_1",
            )

    def test_unregistered_levels_and_unknown_algorithms_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "one of"):
            gaussian_spec(
                sigma_8bit=12, mean_8bit=0.0, sampling_unit="element", clipping="clip_0_1"
            )
        with self.assertRaisesRegex(ValueError, "one of"):
            salt_and_pepper_spec(
                density=0.03,
                salt_probability_given_corruption=0.5,
                salt_value=1.0,
                pepper_value=0.0,
                density_mode="bernoulli",
                sampling_unit="element",
                clipping="clip_0_1",
            )
        with self.assertRaisesRegex(ValueError, "speckle model"):
            speckle_spec(
                variance=0.02,
                gaussian_mean=0.0,
                model="implicit-default",  # type: ignore[arg-type]
                sampling_unit="element",
                clipping="clip_0_1",
            )
        with self.assertRaisesRegex(ValueError, "operation_order"):
            low_light_spec(
                gamma=2.2,
                gaussian_sigma_8bit=15,
                gaussian_mean_8bit=0.0,
                operation_order="implicit-default",  # type: ignore[arg-type]
                clipping_sequence="clip_after_each_stage",
                noise_sampling_unit="element",
                clipping="clip_0_1",
            )

    def test_transform_ids_are_canonical_distinct_and_seeded_by_core(self) -> None:
        specs = fixture_specs()
        self.assertEqual([spec.transform_id for spec in specs], [spec.transform_id for spec in fixture_specs()])
        self.assertEqual(len({spec.transform_id for spec in specs}), len(specs))
        self.assertEqual(identity_spec().transform_id, "shar:p2a-fixture-v1:identity:{}")
        self.assertEqual(
            specs[1].transform_id,
            'shar:p2a-fixture-v1:gaussian:{"clipping":"clip_0_1",'
            '"mean_8bit":0.0,"sampling_unit":"element","sigma_8bit":10.0}',
        )
        sample = SampleKey("Train/Abuse/frame-1.png", FILE_DIGEST, 7)
        for spec in specs:
            self.assertEqual(
                sample.seed_for(spec.transform_id),
                stable_sample_seed(
                    sample.relative_path,
                    sample.file_digest,
                    sample.global_seed,
                    spec.transform_id,
                ),
            )


class DegradationBehaviorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.image = fixture_image()
        self.sample = SampleKey("Train/Abuse/frame-1.png", FILE_DIGEST, 7)

    def test_all_registered_specs_are_repeatable_non_mutating_and_contract_preserving(self) -> None:
        for spec in fixture_specs():
            with self.subTest(spec=spec.transform_id):
                original = self.image.copy()
                first = apply_degradation(self.image, spec=spec, sample=self.sample)
                second = apply_degradation(self.image, spec=spec, sample=self.sample)
                self.assertTrue(np.array_equal(self.image, original))
                self.assertTrue(np.array_equal(first, second))
                self.assertEqual(first.shape, self.image.shape)
                self.assertEqual(first.dtype, np.float32)
                self.assertTrue(np.isfinite(first).all())
                self.assertGreaterEqual(float(first.min()), 0.0)
                self.assertLessEqual(float(first.max()), 1.0)
                self.assertFalse(np.shares_memory(first, self.image))

    def test_fixture_gaussian_bytes_have_a_stable_golden_digest(self) -> None:
        spec = gaussian_spec(
            sigma_8bit=10, mean_8bit=0.0, sampling_unit="element", clipping="clip_0_1"
        )
        output = apply_degradation(self.image, spec=spec, sample=self.sample)
        self.assertEqual(
            hashlib.sha256(output.tobytes()).hexdigest(),
            "f5b381e60b6695f048da0676b1a3e8dac0aae6a5e4cf9e6a92d214996fb9bd7c",
        )

    def test_every_sample_key_component_changes_the_stochastic_stream(self) -> None:
        spec = gaussian_spec(
            sigma_8bit=25, mean_8bit=0.0, sampling_unit="element", clipping="clip_0_1"
        )
        keys = (
            self.sample,
            SampleKey("Train/Abuse/frame-other.png", FILE_DIGEST, 7),
            SampleKey(
                "Train/Abuse/frame-1.png",
                hashlib.sha256(b"different-file-content").hexdigest(),
                7,
            ),
            SampleKey("Train/Abuse/frame-1.png", FILE_DIGEST, 8),
        )
        outputs = [apply_degradation(self.image, spec=spec, sample=key) for key in keys]
        digests = {hashlib.sha256(output.tobytes()).hexdigest() for output in outputs}
        self.assertEqual(len(digests), len(keys))

    def test_identity_is_bitwise_equal_but_returns_an_independent_array(self) -> None:
        output = apply_degradation(self.image, spec=identity_spec(), sample=self.sample)
        self.assertTrue(np.array_equal(output, self.image))
        self.assertFalse(np.shares_memory(output, self.image))

    def test_pixel_shared_salt_pepper_changes_whole_rgb_pixels(self) -> None:
        spec = salt_and_pepper_spec(
            density=0.10,
            salt_probability_given_corruption=0.5,
            salt_value=1.0,
            pepper_value=0.0,
            density_mode="bernoulli",
            sampling_unit="pixel_shared_channels",
            clipping="clip_0_1",
        )
        output = apply_degradation(self.image, spec=spec, sample=self.sample)
        changed = np.any(output != self.image, axis=-1)
        self.assertTrue(changed.any())
        for pixel in output[changed]:
            self.assertTrue(np.all(pixel == 0.0) or np.all(pixel == 1.0))

    def test_speckle_zero_input_remains_zero_for_explicit_multiplicative_model(self) -> None:
        zeros = np.zeros_like(self.image)
        spec = speckle_spec(
            variance=0.05,
            gaussian_mean=0.0,
            model="x_times_one_plus_gaussian",
            sampling_unit="element",
            clipping="clip_0_1",
        )
        output = apply_degradation(zeros, spec=spec, sample=self.sample)
        self.assertTrue(np.array_equal(output, zeros))

    def test_explicit_sampling_and_operation_choices_change_identity_and_output(self) -> None:
        element = gaussian_spec(
            sigma_8bit=25, mean_8bit=0.0, sampling_unit="element", clipping="clip_0_1"
        )
        shared = gaussian_spec(
            sigma_8bit=25,
            mean_8bit=0.0,
            sampling_unit="pixel_shared_channels",
            clipping="clip_0_1",
        )
        self.assertNotEqual(element.transform_id, shared.transform_id)
        self.assertFalse(
            np.array_equal(
                apply_degradation(self.image, spec=element, sample=self.sample),
                apply_degradation(self.image, spec=shared, sample=self.sample),
            )
        )
        gamma_first = low_light_spec(
            gamma=2.2,
            gaussian_sigma_8bit=15,
            gaussian_mean_8bit=0.0,
            operation_order="gamma_then_gaussian",
            clipping_sequence="clip_after_each_stage",
            noise_sampling_unit="element",
            clipping="clip_0_1",
        )
        noise_first = low_light_spec(
            gamma=2.2,
            gaussian_sigma_8bit=15,
            gaussian_mean_8bit=0.0,
            operation_order="gaussian_then_gamma",
            clipping_sequence="clip_after_each_stage",
            noise_sampling_unit="element",
            clipping="clip_0_1",
        )
        self.assertNotEqual(gamma_first.transform_id, noise_first.transform_id)
        self.assertFalse(
            np.array_equal(
                apply_degradation(self.image, spec=gamma_first, sample=self.sample),
                apply_degradation(self.image, spec=noise_first, sample=self.sample),
            )
        )

    def test_batch_helper_equals_stacking_independent_samples(self) -> None:
        images = np.stack((self.image, np.flip(self.image, axis=1).copy()), axis=0)
        samples = (
            self.sample,
            SampleKey("Train/Abuse/frame-2.png", FILE_DIGEST, 7),
        )
        spec = gaussian_spec(
            sigma_8bit=50, mean_8bit=0.0, sampling_unit="element", clipping="clip_0_1"
        )
        batch = apply_degradation_batch(images, spec=spec, samples=samples)
        independent = np.stack(
            [
                apply_degradation(images[index], spec=spec, sample=sample)
                for index, sample in enumerate(samples)
            ]
        )
        self.assertTrue(np.array_equal(batch, independent))
        self.assertEqual(batch.dtype, np.float32)

    def test_input_contract_rejects_layout_dtype_range_and_nonfinite_values(self) -> None:
        spec = identity_spec()
        invalid = (
            self.image.astype(np.float64),
            np.moveaxis(self.image, -1, 0),
            self.image[None, ...],
            np.full_like(self.image, 1.1),
            np.full_like(self.image, np.nan),
        )
        for image in invalid:
            with self.subTest(shape=image.shape, dtype=image.dtype):
                with self.assertRaises((TypeError, ValueError)):
                    apply_degradation(image, spec=spec, sample=self.sample)
        with self.assertRaisesRegex(ValueError, "one SampleKey"):
            apply_degradation_batch(
                np.stack((self.image, self.image)), spec=spec, samples=(self.sample,)
            )


class FreshProcessDeterminismTests(unittest.TestCase):
    def test_outputs_are_bitwise_equal_across_dataloader_worker_counts(self) -> None:
        def collect(worker_count: int) -> np.ndarray:
            options = {
                "dataset": WorkerCountFixture(),
                "batch_size": 2,
                "shuffle": False,
                "num_workers": worker_count,
                "collate_fn": collate_numpy,
            }
            if worker_count:
                options["multiprocessing_context"] = "spawn"
            loader = torch.utils.data.DataLoader(**options)
            return np.concatenate(list(loader), axis=0)

        self.assertTrue(np.array_equal(collect(0), collect(2)))

    def test_all_registered_stochastic_outputs_are_bitwise_equal_across_fresh_processes(self) -> None:
        code = r'''
import hashlib
import json
import numpy as np
from data.degradations import SampleKey, apply_degradation, registered_degradation_specs

image = np.linspace(0.0, 1.0, 24 * 25 * 3, dtype=np.float32).reshape(24, 25, 3)
sample = SampleKey("Train/Abuse/frame-1.png", hashlib.sha256(b"p2a-degradation-fixture").hexdigest(), 7)
specs = registered_degradation_specs(
    gaussian_mean_8bit=0.0,
    gaussian_sampling_unit="element",
    salt_probability_given_corruption=0.5,
    salt_value=1.0,
    pepper_value=0.0,
    salt_pepper_density_mode="bernoulli",
    salt_pepper_sampling_unit="pixel_shared_channels",
    speckle_gaussian_mean=0.0,
    speckle_model="x_times_one_plus_gaussian",
    speckle_sampling_unit="element",
    low_light_operation_order="gamma_then_gaussian",
    low_light_gaussian_mean_8bit=0.0,
    low_light_clipping_sequence="clip_after_each_stage",
    low_light_noise_sampling_unit="element",
    clipping="clip_0_1",
)
print(json.dumps({
    spec.transform_id: hashlib.sha256(apply_degradation(image, spec=spec, sample=sample).tobytes()).hexdigest()
    for spec in specs
}, sort_keys=True))
'''
        outputs = [
            subprocess.check_output(
                [sys.executable, "-c", code], cwd=REPO_ROOT, text=True
            ).strip()
            for _ in range(2)
        ]
        self.assertEqual(outputs[0], outputs[1])
        digests = json.loads(outputs[0])
        self.assertEqual(len(digests), 10)
        self.assertTrue(all(len(value) == 64 for value in digests.values()))


class ConstructorAndIdentityTests(unittest.TestCase):
    def test_direct_spec_construction_cannot_bypass_registered_schema(self) -> None:
        with self.assertRaisesRegex(ValueError, "parameters must be exactly"):
            DegradationSpec("gaussian", {})
        with self.assertRaisesRegex(ValueError, "one of"):
            DegradationSpec(
                "gaussian",
                {
                    "sigma_8bit": 12.0,
                    "mean_8bit": 0.0,
                    "sampling_unit": "element",
                    "clipping": "clip_0_1",
                },
            )
        with self.assertRaisesRegex(ValueError, "unexpected"):
            DegradationSpec(
                "identity", {"unused_parameter_that_changes_seed_only": 1}
            )
        with self.assertRaisesRegex(ValueError, "algorithm_version"):
            DegradationSpec("identity", {}, algorithm_version="invented-version")

    def test_sample_key_requires_canonical_relative_posix_path(self) -> None:
        invalid_paths = (
            "/absolute/frame.png",
            "Train\\Abuse\\frame.png",
            "Train/../frame.png",
            "Train/./Abuse/frame.png",
            "Train//Abuse/frame.png",
        )
        for path in invalid_paths:
            with self.subTest(path=path):
                with self.assertRaisesRegex(ValueError, "canonical relative POSIX"):
                    SampleKey(path, FILE_DIGEST, 0)


if __name__ == "__main__":
    unittest.main()
