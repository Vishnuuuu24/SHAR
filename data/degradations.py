"""Deterministic, parameter-explicit P2A degradation primitives.

This module is fixture/code scaffolding under D-23, not an experiment freeze.
Every public transform accepts only an HWC RGB ``float32`` NumPy array in
``[0, 1]``.  Ambiguous corruption choices are required arguments so that a
future experiment cannot inherit an undocumented default.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import PurePosixPath
from types import MappingProxyType
from typing import Literal, Mapping, Sequence, TypeAlias

import numpy as np

from core.reproducibility import stable_sample_seed


DegradationFamily: TypeAlias = Literal[
    "identity", "gaussian", "salt_and_pepper", "speckle", "low_light"
]
SamplingUnit: TypeAlias = Literal["element", "pixel_shared_channels"]
ClippingPolicy: TypeAlias = Literal["clip_0_1"]
ParameterValue: TypeAlias = str | int | float

ALGORITHM_VERSION = "p2a-fixture-v1"
REGISTERED_GAUSSIAN_SIGMA_8BIT = (10.0, 25.0, 50.0)
REGISTERED_SALT_PEPPER_DENSITIES = (0.02, 0.05, 0.10)
REGISTERED_SPECKLE_VARIANCES = (0.02, 0.05)
REGISTERED_LOW_LIGHT = MappingProxyType({"gamma": 2.2, "gaussian_sigma_8bit": 15.0})
REGISTERED_LEVELS = MappingProxyType(
    {
        "identity": ("none",),
        "gaussian": REGISTERED_GAUSSIAN_SIGMA_8BIT,
        "salt_and_pepper": REGISTERED_SALT_PEPPER_DENSITIES,
        "speckle": REGISTERED_SPECKLE_VARIANCES,
        "low_light": ((2.2, 15.0),),
    }
)

_FAMILIES = frozenset(REGISTERED_LEVELS)
_SAMPLING_UNITS = frozenset(("element", "pixel_shared_channels"))
_CLIPPING_POLICIES = frozenset(("clip_0_1",))


@dataclass(frozen=True)
class SampleKey:
    """Stable per-image identity used by every stochastic degradation."""

    relative_path: str
    file_digest: str
    global_seed: int

    def __post_init__(self) -> None:
        pure_path = PurePosixPath(self.relative_path)
        if (
            pure_path.is_absolute()
            or ".." in pure_path.parts
            or "\\" in self.relative_path
            or pure_path.as_posix() != self.relative_path
        ):
            raise ValueError("relative_path must be a canonical relative POSIX path")
        # Keep validation and seed semantics centralized in core.reproducibility.
        stable_sample_seed(
            self.relative_path,
            self.file_digest,
            self.global_seed,
            "sample-key-validation",
        )

    def seed_for(self, transform_id: str) -> int:
        return stable_sample_seed(
            self.relative_path,
            self.file_digest,
            self.global_seed,
            transform_id,
        )


@dataclass(frozen=True)
class DegradationSpec:
    """Immutable degradation identity with canonical, explicit parameters."""

    family: DegradationFamily
    parameters: Mapping[str, ParameterValue]
    algorithm_version: str = ALGORITHM_VERSION
    transform_id: str = field(init=False)

    def __post_init__(self) -> None:
        if self.family not in _FAMILIES:
            raise ValueError(f"unsupported degradation family: {self.family}")
        if self.algorithm_version != ALGORITHM_VERSION:
            raise ValueError(f"algorithm_version must equal implemented version {ALGORITHM_VERSION}")
        if not isinstance(self.parameters, Mapping):
            raise TypeError("parameters must be a mapping")
        canonical: dict[str, ParameterValue] = {}
        for name, value in self.parameters.items():
            if not isinstance(name, str) or not name:
                raise ValueError("parameter names must be non-empty strings")
            if isinstance(value, bool) or not isinstance(value, (str, int, float)):
                raise TypeError(f"unsupported parameter value for {name}")
            if isinstance(value, float) and not math.isfinite(value):
                raise ValueError(f"parameter {name} must be finite")
            canonical[name] = value
        canonical = dict(sorted(canonical.items()))
        _validate_family_parameters(self.family, canonical)
        object.__setattr__(self, "parameters", MappingProxyType(canonical))
        payload = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
        object.__setattr__(
            self,
            "transform_id",
            f"shar:{self.algorithm_version}:{self.family}:{payload}",
        )


def _require_registered(value: float, registered: tuple[float, ...], name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be numeric")
    result = float(value)
    if result not in registered:
        raise ValueError(f"{name} must be one of {registered}")
    return result


def _validate_sampling_unit(sampling_unit: SamplingUnit) -> str:
    if sampling_unit not in _SAMPLING_UNITS:
        raise ValueError(f"sampling_unit must be one of {sorted(_SAMPLING_UNITS)}")
    return sampling_unit


def _validate_clipping(clipping: ClippingPolicy) -> str:
    if clipping not in _CLIPPING_POLICIES:
        raise ValueError(f"clipping must be one of {sorted(_CLIPPING_POLICIES)}")
    return clipping


def _unit_interval(value: float, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be numeric")
    result = float(value)
    if not math.isfinite(result) or not 0.0 <= result <= 1.0:
        raise ValueError(f"{name} must be finite and in [0,1]")
    return result


def _finite_number(value: ParameterValue, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be numeric")
    checked = float(value)
    if not math.isfinite(checked):
        raise ValueError(f"{name} must be finite")
    return checked


def _validate_family_parameters(
    family: DegradationFamily, parameters: Mapping[str, ParameterValue]
) -> None:
    expected = {
        "identity": frozenset(),
        "gaussian": frozenset({"sigma_8bit", "mean_8bit", "sampling_unit", "clipping"}),
        "salt_and_pepper": frozenset(
            {
                "density",
                "salt_probability_given_corruption",
                "salt_value",
                "pepper_value",
                "density_mode",
                "sampling_unit",
                "clipping",
            }
        ),
        "speckle": frozenset(
            {"variance", "gaussian_mean", "model", "sampling_unit", "clipping"}
        ),
        "low_light": frozenset(
            {
                "gamma",
                "gaussian_sigma_8bit",
                "gaussian_mean_8bit",
                "operation_order",
                "clipping_sequence",
                "noise_sampling_unit",
                "clipping",
            }
        ),
    }[family]
    keys = frozenset(parameters)
    if keys != expected:
        raise ValueError(
            f"{family} parameters must be exactly {sorted(expected)}; "
            f"missing={sorted(expected - keys)}, unexpected={sorted(keys - expected)}"
        )
    if family == "identity":
        return
    _validate_clipping(str(parameters["clipping"]))
    sampling_key = "noise_sampling_unit" if family == "low_light" else "sampling_unit"
    _validate_sampling_unit(str(parameters[sampling_key]))
    if family == "gaussian":
        _require_registered(
            parameters["sigma_8bit"], REGISTERED_GAUSSIAN_SIGMA_8BIT, "sigma_8bit"
        )
        _finite_number(parameters["mean_8bit"], "mean_8bit")
    elif family == "salt_and_pepper":
        _require_registered(
            parameters["density"], REGISTERED_SALT_PEPPER_DENSITIES, "density"
        )
        for name in ("salt_probability_given_corruption", "salt_value", "pepper_value"):
            _unit_interval(parameters[name], name)
        if parameters["density_mode"] != "bernoulli":
            raise ValueError("unsupported salt-and-pepper density_mode")
    elif family == "speckle":
        _require_registered(
            parameters["variance"], REGISTERED_SPECKLE_VARIANCES, "variance"
        )
        _finite_number(parameters["gaussian_mean"], "gaussian_mean")
        if parameters["model"] != "x_times_one_plus_gaussian":
            raise ValueError("unsupported speckle model")
    else:
        if _finite_number(parameters["gamma"], "gamma") != REGISTERED_LOW_LIGHT["gamma"]:
            raise ValueError(f"gamma must equal {REGISTERED_LOW_LIGHT['gamma']}")
        if _finite_number(
            parameters["gaussian_sigma_8bit"], "gaussian_sigma_8bit"
        ) != REGISTERED_LOW_LIGHT["gaussian_sigma_8bit"]:
            raise ValueError(
                "gaussian_sigma_8bit must equal "
                f"{REGISTERED_LOW_LIGHT['gaussian_sigma_8bit']}"
            )
        _finite_number(parameters["gaussian_mean_8bit"], "gaussian_mean_8bit")
        if parameters["operation_order"] not in {"gamma_then_gaussian", "gaussian_then_gamma"}:
            raise ValueError("unsupported low-light operation_order")
        if parameters["clipping_sequence"] != "clip_after_each_stage":
            raise ValueError("unsupported low-light clipping_sequence")


def identity_spec() -> DegradationSpec:
    return DegradationSpec("identity", {})


def gaussian_spec(
    *,
    sigma_8bit: float,
    mean_8bit: float,
    sampling_unit: SamplingUnit,
    clipping: ClippingPolicy,
) -> DegradationSpec:
    if isinstance(mean_8bit, bool) or not isinstance(mean_8bit, (int, float)):
        raise TypeError("mean_8bit must be numeric")
    checked_mean = float(mean_8bit)
    if not math.isfinite(checked_mean):
        raise ValueError("mean_8bit must be finite")
    return DegradationSpec(
        "gaussian",
        {
            "sigma_8bit": _require_registered(
                sigma_8bit, REGISTERED_GAUSSIAN_SIGMA_8BIT, "sigma_8bit"
            ),
            "mean_8bit": checked_mean,
            "sampling_unit": _validate_sampling_unit(sampling_unit),
            "clipping": _validate_clipping(clipping),
        },
    )


def salt_and_pepper_spec(
    *,
    density: float,
    salt_probability_given_corruption: float,
    salt_value: float,
    pepper_value: float,
    density_mode: Literal["bernoulli"],
    sampling_unit: SamplingUnit,
    clipping: ClippingPolicy,
) -> DegradationSpec:
    if density_mode != "bernoulli":
        raise ValueError("unsupported salt-and-pepper density_mode")
    return DegradationSpec(
        "salt_and_pepper",
        {
            "density": _require_registered(
                density, REGISTERED_SALT_PEPPER_DENSITIES, "density"
            ),
            "salt_probability_given_corruption": _unit_interval(
                salt_probability_given_corruption, "salt_probability_given_corruption"
            ),
            "salt_value": _unit_interval(salt_value, "salt_value"),
            "pepper_value": _unit_interval(pepper_value, "pepper_value"),
            "density_mode": density_mode,
            "sampling_unit": _validate_sampling_unit(sampling_unit),
            "clipping": _validate_clipping(clipping),
        },
    )


def speckle_spec(
    *,
    variance: float,
    gaussian_mean: float,
    model: Literal["x_times_one_plus_gaussian"],
    sampling_unit: SamplingUnit,
    clipping: ClippingPolicy,
) -> DegradationSpec:
    if model != "x_times_one_plus_gaussian":
        raise ValueError("unsupported speckle model")
    if isinstance(gaussian_mean, bool) or not isinstance(gaussian_mean, (int, float)):
        raise TypeError("gaussian_mean must be numeric")
    mean = float(gaussian_mean)
    if not math.isfinite(mean):
        raise ValueError("gaussian_mean must be finite")
    return DegradationSpec(
        "speckle",
        {
            "variance": _require_registered(
                variance, REGISTERED_SPECKLE_VARIANCES, "variance"
            ),
            "gaussian_mean": mean,
            "model": model,
            "sampling_unit": _validate_sampling_unit(sampling_unit),
            "clipping": _validate_clipping(clipping),
        },
    )


def low_light_spec(
    *,
    gamma: float,
    gaussian_sigma_8bit: float,
    gaussian_mean_8bit: float,
    operation_order: Literal["gamma_then_gaussian", "gaussian_then_gamma"],
    clipping_sequence: Literal["clip_after_each_stage"],
    noise_sampling_unit: SamplingUnit,
    clipping: ClippingPolicy,
) -> DegradationSpec:
    if float(gamma) != REGISTERED_LOW_LIGHT["gamma"]:
        raise ValueError(f"gamma must equal {REGISTERED_LOW_LIGHT['gamma']}")
    if float(gaussian_sigma_8bit) != REGISTERED_LOW_LIGHT["gaussian_sigma_8bit"]:
        raise ValueError(
            "gaussian_sigma_8bit must equal "
            f"{REGISTERED_LOW_LIGHT['gaussian_sigma_8bit']}"
        )
    if operation_order not in {"gamma_then_gaussian", "gaussian_then_gamma"}:
        raise ValueError("unsupported low-light operation_order")
    if clipping_sequence != "clip_after_each_stage":
        raise ValueError("unsupported low-light clipping_sequence")
    return DegradationSpec(
        "low_light",
        {
            "gamma": float(gamma),
            "gaussian_sigma_8bit": float(gaussian_sigma_8bit),
            "gaussian_mean_8bit": _finite_number(
                gaussian_mean_8bit, "gaussian_mean_8bit"
            ),
            "operation_order": operation_order,
            "clipping_sequence": clipping_sequence,
            "noise_sampling_unit": _validate_sampling_unit(noise_sampling_unit),
            "clipping": _validate_clipping(clipping),
        },
    )


def registered_degradation_specs(
    *,
    gaussian_mean_8bit: float,
    gaussian_sampling_unit: SamplingUnit,
    salt_probability_given_corruption: float,
    salt_value: float,
    pepper_value: float,
    salt_pepper_density_mode: Literal["bernoulli"],
    salt_pepper_sampling_unit: SamplingUnit,
    speckle_gaussian_mean: float,
    speckle_model: Literal["x_times_one_plus_gaussian"],
    speckle_sampling_unit: SamplingUnit,
    low_light_operation_order: Literal["gamma_then_gaussian", "gaussian_then_gamma"],
    low_light_gaussian_mean_8bit: float,
    low_light_clipping_sequence: Literal["clip_after_each_stage"],
    low_light_noise_sampling_unit: SamplingUnit,
    clipping: ClippingPolicy,
) -> tuple[DegradationSpec, ...]:
    """Build every registered level while requiring unresolved semantics."""

    specs: list[DegradationSpec] = [identity_spec()]
    specs.extend(
        gaussian_spec(
            sigma_8bit=sigma,
            mean_8bit=gaussian_mean_8bit,
            sampling_unit=gaussian_sampling_unit,
            clipping=clipping,
        )
        for sigma in REGISTERED_GAUSSIAN_SIGMA_8BIT
    )
    specs.extend(
        salt_and_pepper_spec(
            density=density,
            salt_probability_given_corruption=salt_probability_given_corruption,
            salt_value=salt_value,
            pepper_value=pepper_value,
            density_mode=salt_pepper_density_mode,
            sampling_unit=salt_pepper_sampling_unit,
            clipping=clipping,
        )
        for density in REGISTERED_SALT_PEPPER_DENSITIES
    )
    specs.extend(
        speckle_spec(
            variance=variance,
            gaussian_mean=speckle_gaussian_mean,
            model=speckle_model,
            sampling_unit=speckle_sampling_unit,
            clipping=clipping,
        )
        for variance in REGISTERED_SPECKLE_VARIANCES
    )
    specs.append(
        low_light_spec(
            gamma=REGISTERED_LOW_LIGHT["gamma"],
            gaussian_sigma_8bit=REGISTERED_LOW_LIGHT["gaussian_sigma_8bit"],
            gaussian_mean_8bit=low_light_gaussian_mean_8bit,
            operation_order=low_light_operation_order,
            clipping_sequence=low_light_clipping_sequence,
            noise_sampling_unit=low_light_noise_sampling_unit,
            clipping=clipping,
        )
    )
    return tuple(specs)


def _validate_image(image: np.ndarray, *, batched: bool) -> None:
    if not isinstance(image, np.ndarray):
        raise TypeError("image must be a NumPy array")
    expected_dimensions = 4 if batched else 3
    expected_layout = "[batch,height,width,3]" if batched else "[height,width,3]"
    if image.ndim != expected_dimensions or image.shape[-1] != 3:
        raise ValueError(f"image must have RGB HWC layout {expected_layout}")
    if any(dimension <= 0 for dimension in image.shape):
        raise ValueError("image dimensions must be positive")
    if image.dtype != np.float32:
        raise TypeError("image dtype must be float32")
    if not np.isfinite(image).all():
        raise ValueError("image values must be finite")
    if np.any(image < 0.0) or np.any(image > 1.0):
        raise ValueError("image values must be in [0,1]")


def _noise_shape(image: np.ndarray, sampling_unit: str) -> tuple[int, ...]:
    return image.shape if sampling_unit == "element" else (*image.shape[:2], 1)


def _standard_normal(
    generator: np.random.Generator,
    image: np.ndarray,
    sampling_unit: str,
) -> np.ndarray:
    return generator.standard_normal(_noise_shape(image, sampling_unit), dtype=np.float32)


def _clip_float32(image: np.ndarray, clipping: str) -> np.ndarray:
    if clipping != "clip_0_1":
        raise ValueError(f"unsupported clipping policy: {clipping}")
    return np.clip(image, np.float32(0.0), np.float32(1.0)).astype(np.float32, copy=False)


def apply_degradation(
    clean: np.ndarray,
    *,
    spec: DegradationSpec,
    sample: SampleKey,
) -> np.ndarray:
    """Apply one parameter-explicit degradation without mutating ``clean``."""

    _validate_image(clean, batched=False)
    if not isinstance(spec, DegradationSpec):
        raise TypeError("spec must be a DegradationSpec")
    if not isinstance(sample, SampleKey):
        raise TypeError("sample must be a SampleKey")
    parameters = spec.parameters
    if spec.family == "identity":
        if parameters:
            raise ValueError("identity does not accept parameters")
        return clean.copy()

    generator = np.random.Generator(np.random.PCG64(sample.seed_for(spec.transform_id)))
    if spec.family == "gaussian":
        noise = _standard_normal(generator, clean, str(parameters["sampling_unit"]))
        sigma = np.float32(float(parameters["sigma_8bit"]) / 255.0)
        mean = np.float32(float(parameters["mean_8bit"]) / 255.0)
        result = clean + mean + noise * sigma
        return _clip_float32(result, str(parameters["clipping"]))

    if spec.family == "salt_and_pepper":
        if parameters["density_mode"] != "bernoulli":
            raise ValueError("unsupported salt-and-pepper density_mode")
        shape = _noise_shape(clean, str(parameters["sampling_unit"]))
        occurrence = generator.random(shape, dtype=np.float32)
        selection = generator.random(shape, dtype=np.float32)
        corrupted = occurrence < np.float32(parameters["density"])
        salt = corrupted & (
            selection < np.float32(parameters["salt_probability_given_corruption"])
        )
        pepper = corrupted & ~salt
        result = clean.copy()
        if shape[-1] == 1:
            salt = np.broadcast_to(salt, clean.shape)
            pepper = np.broadcast_to(pepper, clean.shape)
        result[pepper] = np.float32(parameters["pepper_value"])
        result[salt] = np.float32(parameters["salt_value"])
        return _clip_float32(result, str(parameters["clipping"]))

    if spec.family == "speckle":
        if parameters["model"] != "x_times_one_plus_gaussian":
            raise ValueError("unsupported speckle model")
        standard = _standard_normal(generator, clean, str(parameters["sampling_unit"]))
        mean = np.float32(parameters["gaussian_mean"])
        scale = np.float32(math.sqrt(float(parameters["variance"])))
        result = clean * (np.float32(1.0) + mean + standard * scale)
        return _clip_float32(result, str(parameters["clipping"]))

    if spec.family == "low_light":
        standard = _standard_normal(generator, clean, str(parameters["noise_sampling_unit"]))
        sigma = np.float32(float(parameters["gaussian_sigma_8bit"]) / 255.0)
        mean = np.float32(float(parameters["gaussian_mean_8bit"]) / 255.0)
        gamma = np.float32(parameters["gamma"])
        order = parameters["operation_order"]
        if parameters["clipping_sequence"] != "clip_after_each_stage":
            raise ValueError("unsupported low-light clipping_sequence")
        if order == "gamma_then_gaussian":
            darkened = _clip_float32(
                np.power(clean, gamma, dtype=np.float32), str(parameters["clipping"])
            )
            result = darkened + mean + standard * sigma
        elif order == "gaussian_then_gamma":
            noisy = _clip_float32(clean + mean + standard * sigma, str(parameters["clipping"]))
            result = np.power(noisy, gamma, dtype=np.float32)
        else:
            raise ValueError("unsupported low-light operation_order")
        return _clip_float32(result, str(parameters["clipping"]))

    raise ValueError(f"unsupported degradation family: {spec.family}")


def apply_degradation_batch(
    clean_batch: np.ndarray,
    *,
    spec: DegradationSpec,
    samples: Sequence[SampleKey],
) -> np.ndarray:
    """Apply one spec independently to an RGB BHWC batch in stable order."""

    _validate_image(clean_batch, batched=True)
    if len(samples) != clean_batch.shape[0]:
        raise ValueError("samples must contain exactly one SampleKey per image")
    if any(not isinstance(sample, SampleKey) for sample in samples):
        raise TypeError("samples must contain only SampleKey values")
    return np.stack(
        [
            apply_degradation(clean_batch[index], spec=spec, sample=sample)
            for index, sample in enumerate(samples)
        ],
        axis=0,
    ).astype(np.float32, copy=False)
