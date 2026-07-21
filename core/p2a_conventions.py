"""Fail-closed loader for a future owner-frozen P2A convention file.

The loader supplies no experiment defaults.  It accepts only the exact P2A
scaffold shape after every owner placeholder has been replaced, checks that
selected capabilities are implemented, and returns arguments for the existing
degradation, restoration, and image-quality APIs.
"""

from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

import cv2
import yaml

from data.degradations import DegradationSpec, registered_degradation_specs


class ConventionValidationError(ValueError):
    """Raised when a convention file is incomplete or unsupported."""


_TOP_LEVEL = {
    "schema_version",
    "status",
    "decision",
    "work_item",
    "approval",
    "fixture_contract_not_experiment_freeze",
    "experiment_image_contract",
    "degradations",
    "classical_restoration",
    "image_quality",
    "gates",
}
_PLACEHOLDER = re.compile(
    r"owner_required|placeholder|\btodo\b|\btbd\b|\bunset\b|replace[_ -]?me|change[_ -]?me|\$\{[^}]+\}|<[^>]+>",
    re.IGNORECASE,
)
_BORDERS = {
    "BORDER_REPLICATE": cv2.BORDER_REPLICATE,
    "BORDER_REFLECT": cv2.BORDER_REFLECT,
    "BORDER_REFLECT_101": cv2.BORDER_REFLECT_101,
}


class _UniqueKeyLoader(yaml.SafeLoader):
    pass


def _construct_mapping(loader: _UniqueKeyLoader, node: yaml.MappingNode, deep: bool = False) -> dict:
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise ConventionValidationError(f"duplicate YAML key: {key!r}")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping
)


@dataclass(frozen=True)
class FrozenP2AConventions:
    """Validated, immutable call arguments derived from an approved YAML file."""

    source_path: Path
    source_sha256: str
    image_contract: Mapping[str, Any]
    degradation_specs: tuple[DegradationSpec, ...]
    restoration_parameters: Mapping[str, Mapping[str, Any]]
    restoration_output_policy: str
    psnr_options: Mapping[str, Any]
    ssim_options: Mapping[str, Any]

    def restoration_arguments(self, method: str) -> dict[str, Any]:
        if method not in self.restoration_parameters:
            raise ValueError(f"unknown frozen restoration method: {method}")
        return {
            "method": method,
            "parameters": dict(self.restoration_parameters[method]),
            "output_policy": self.restoration_output_policy,
        }


def load_frozen_p2a_conventions(path: str | Path) -> FrozenP2AConventions:
    """Load and validate a future owner-approved P2A YAML convention file."""

    source = Path(path)
    payload, document = _read_yaml(source)
    unresolved = _placeholder_paths(document)
    if unresolved:
        raise ConventionValidationError(f"unresolved placeholder at {unresolved[0]}")
    root = _mapping(document, "$", _TOP_LEVEL)
    _literal(root["schema_version"], "1.0.0", "$.schema_version")
    _literal(root["status"], "OWNER_APPROVED", "$.status")
    _literal(root["decision"], "D-23", "$.decision")
    _literal(root["work_item"], "P2A-CODE-W1", "$.work_item")
    _validate_approval(root["approval"], scaffold_decision=root["decision"])
    _validate_fixture_contract(root["fixture_contract_not_experiment_freeze"])
    image_contract = _validate_image_contract(root["experiment_image_contract"])
    degradation_specs = _parse_degradations(root["degradations"])
    restoration_parameters, output_policy = _parse_restoration(root["classical_restoration"])
    psnr_options, ssim_options = _parse_quality(root["image_quality"])
    _validate_gates(root["gates"])
    return FrozenP2AConventions(
        source_path=source.resolve(),
        source_sha256=hashlib.sha256(payload).hexdigest(),
        image_contract=MappingProxyType(image_contract),
        degradation_specs=degradation_specs,
        restoration_parameters=MappingProxyType(
            {name: MappingProxyType(values) for name, values in restoration_parameters.items()}
        ),
        restoration_output_policy=output_policy,
        psnr_options=MappingProxyType(psnr_options),
        ssim_options=MappingProxyType(ssim_options),
    )


def unresolved_convention_fields(path: str | Path) -> tuple[str, ...]:
    """Return every unresolved owner field without authorizing execution."""

    _, document = _read_yaml(Path(path))
    return tuple(_placeholder_paths(document))


def _read_yaml(source: Path) -> tuple[bytes, Any]:
    try:
        payload = source.read_bytes()
        document = yaml.load(payload.decode("utf-8"), Loader=_UniqueKeyLoader)
    except ConventionValidationError:
        raise
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise ConventionValidationError(f"cannot load convention YAML: {exc}") from exc
    return payload, document


def _placeholder_paths(value: Any, path: str = "$") -> list[str]:
    unresolved: list[str] = []
    if isinstance(value, str) and _PLACEHOLDER.search(value):
        unresolved.append(path)
    if isinstance(value, Mapping):
        for key, child in value.items():
            unresolved.extend(_placeholder_paths(child, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            unresolved.extend(_placeholder_paths(child, f"{path}[{index}]"))
    return unresolved


def _mapping(value: Any, path: str, keys: set[str]) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ConventionValidationError(f"{path} must be a mapping")
    actual = set(value)
    if actual != keys:
        raise ConventionValidationError(
            f"{path} keys mismatch: missing={sorted(keys - actual)}, unexpected={sorted(actual - keys)}"
        )
    return value


def _literal(value: Any, expected: Any, path: str) -> None:
    if value != expected or isinstance(value, bool) != isinstance(expected, bool):
        raise ConventionValidationError(f"{path} must equal {expected!r}")


def _nonempty(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ConventionValidationError(f"{path} must be a non-empty string")
    return value


def _number(value: Any, path: str, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConventionValidationError(f"{path} must be numeric")
    result = float(value)
    if not math.isfinite(result) or (positive and result <= 0):
        raise ConventionValidationError(f"{path} must be finite{' and positive' if positive else ''}")
    return result


def _exact_sequence(value: Any, expected: list[Any], path: str) -> None:
    if not isinstance(value, list) or value != expected:
        raise ConventionValidationError(f"{path} must equal {expected!r}")


def _choice(value: Any, path: str, capabilities: list[str]) -> str:
    node = _mapping(value, path, {"owner_selection", "implemented_capabilities"})
    _exact_sequence(node["implemented_capabilities"], capabilities, f"{path}.implemented_capabilities")
    selected = _nonempty(node["owner_selection"], f"{path}.owner_selection")
    if selected not in capabilities:
        raise ConventionValidationError(f"{path}.owner_selection is not implemented")
    return selected


def _validate_fixture_contract(value: Any) -> None:
    node = _mapping(value, "$.fixture_contract_not_experiment_freeze", {"color", "layout", "dtype", "range"})
    for key, expected in (("color", "RGB"), ("layout", "HWC"), ("dtype", "float32")):
        _literal(node[key], expected, f"$.fixture_contract_not_experiment_freeze.{key}")
    _exact_sequence(node["range"], [0.0, 1.0], "$.fixture_contract_not_experiment_freeze.range")


def _validate_approval(value: Any, *, scaffold_decision: str) -> None:
    path = "$.approval"
    node = _mapping(value, path, {"state", "owner", "approved_at", "decision_record"})
    _literal(node["state"], "OWNER_APPROVED", f"{path}.state")
    _nonempty(node["owner"], f"{path}.owner")
    decision_record = _nonempty(node["decision_record"], f"{path}.decision_record")
    if not re.fullmatch(r"D-\d{2,}", decision_record):
        raise ConventionValidationError(
            f"{path}.decision_record must be a project decision ID"
        )
    if decision_record == scaffold_decision:
        raise ConventionValidationError(
            f"{path}.decision_record must identify the later convention-freeze decision"
        )
    approved_at = _nonempty(node["approved_at"], f"{path}.approved_at")
    try:
        parsed = datetime.fromisoformat(approved_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ConventionValidationError(
            f"{path}.approved_at must be an ISO-8601 timestamp"
        ) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ConventionValidationError(
            f"{path}.approved_at must include an explicit timezone"
        )


def _validate_image_contract(value: Any) -> dict[str, Any]:
    keys = {"color", "layout", "dtype", "range", "clipping_point", "quantization_point", "border_mode"}
    node = _mapping(value, "$.experiment_image_contract", keys)
    for key, expected in (("color", "RGB"), ("layout", "HWC"), ("dtype", "float32")):
        _literal(node[key], expected, f"$.experiment_image_contract.{key}")
    _exact_sequence(node["range"], [0.0, 1.0], "$.experiment_image_contract.range")
    for key in ("clipping_point", "quantization_point", "border_mode"):
        _nonempty(node[key], f"$.experiment_image_contract.{key}")
    return dict(node)


def _parse_degradations(value: Any) -> tuple[DegradationSpec, ...]:
    root = _mapping(value, "$.degradations", {"identity", "gaussian", "salt_and_pepper", "speckle", "low_light"})
    identity = _mapping(root["identity"], "$.degradations.identity", {"levels"})
    _exact_sequence(identity["levels"], ["none"], "$.degradations.identity.levels")
    gaussian = _mapping(root["gaussian"], "$.degradations.gaussian", {"sigma_8bit_levels", "mean_8bit", "sampling_unit", "clipping"})
    _exact_sequence(gaussian["sigma_8bit_levels"], [10, 25, 50], "$.degradations.gaussian.sigma_8bit_levels")
    salt = _mapping(root["salt_and_pepper"], "$.degradations.salt_and_pepper", {"density_levels", "salt_probability_given_corruption", "salt_value", "pepper_value", "density_mode", "sampling_unit", "clipping"})
    _exact_sequence(salt["density_levels"], [0.02, 0.05, 0.10], "$.degradations.salt_and_pepper.density_levels")
    speckle = _mapping(root["speckle"], "$.degradations.speckle", {"variance_levels", "gaussian_mean", "model", "sampling_unit", "clipping"})
    _exact_sequence(speckle["variance_levels"], [0.02, 0.05], "$.degradations.speckle.variance_levels")
    low = _mapping(root["low_light"], "$.degradations.low_light", {"gamma", "gaussian_sigma_8bit", "gaussian_mean_8bit", "operation_order", "clipping_sequence", "noise_sampling_unit", "clipping"})
    _literal(low["gamma"], 2.2, "$.degradations.low_light.gamma")
    _literal(low["gaussian_sigma_8bit"], 15, "$.degradations.low_light.gaussian_sigma_8bit")
    sampling = {"element", "pixel_shared_channels"}
    for path, selected in (("gaussian", gaussian["sampling_unit"]), ("salt_and_pepper", salt["sampling_unit"]), ("speckle", speckle["sampling_unit"]), ("low_light", low["noise_sampling_unit"])):
        if selected not in sampling:
            raise ConventionValidationError(f"$.degradations.{path} sampling unit is not implemented")
    for name, node in (("gaussian", gaussian), ("salt_and_pepper", salt), ("speckle", speckle), ("low_light", low)):
        _literal(node["clipping"], "clip_0_1", f"$.degradations.{name}.clipping")
    try:
        return registered_degradation_specs(
            gaussian_mean_8bit=_number(gaussian["mean_8bit"], "$.degradations.gaussian.mean_8bit"),
            gaussian_sampling_unit=gaussian["sampling_unit"],
            salt_probability_given_corruption=_number(salt["salt_probability_given_corruption"], "$.degradations.salt_and_pepper.salt_probability_given_corruption"),
            salt_value=_number(salt["salt_value"], "$.degradations.salt_and_pepper.salt_value"),
            pepper_value=_number(salt["pepper_value"], "$.degradations.salt_and_pepper.pepper_value"),
            salt_pepper_density_mode=_choice(salt["density_mode"], "$.degradations.salt_and_pepper.density_mode", ["bernoulli"]),
            salt_pepper_sampling_unit=salt["sampling_unit"],
            speckle_gaussian_mean=_number(speckle["gaussian_mean"], "$.degradations.speckle.gaussian_mean"),
            speckle_model=_choice(speckle["model"], "$.degradations.speckle.model", ["x_times_one_plus_gaussian"]),
            speckle_sampling_unit=speckle["sampling_unit"],
            low_light_operation_order=low["operation_order"],
            low_light_gaussian_mean_8bit=_number(low["gaussian_mean_8bit"], "$.degradations.low_light.gaussian_mean_8bit"),
            low_light_clipping_sequence=_choice(low["clipping_sequence"], "$.degradations.low_light.clipping_sequence", ["clip_after_each_stage"]),
            low_light_noise_sampling_unit=low["noise_sampling_unit"],
            clipping="clip_0_1",
        )
    except (TypeError, ValueError) as exc:
        raise ConventionValidationError(f"unsupported degradation convention: {exc}") from exc


def _parse_restoration(value: Any) -> tuple[dict[str, dict[str, Any]], str]:
    methods = {"identity", "median", "gaussian_blur", "bilateral", "nlm", "output_policy"}
    root = _mapping(value, "$.classical_restoration", methods)
    identity = _mapping(root["identity"], "$.classical_restoration.identity", {"parameters"})
    _mapping(identity["parameters"], "$.classical_restoration.identity.parameters", set())
    median = _mapping(root["median"], "$.classical_restoration.median", {"kernel_size", "border_policy"})
    gaussian = _mapping(root["gaussian_blur"], "$.classical_restoration.gaussian_blur", {"kernel_size", "sigma_x", "sigma_y", "border_type"})
    bilateral = _mapping(root["bilateral"], "$.classical_restoration.bilateral", {"diameter", "sigma_color", "sigma_space", "border_type"})
    nlm = _mapping(root["nlm"], "$.classical_restoration.nlm", {"h_luminance", "h_color", "template_window_size", "search_window_size", "quantization", "color_boundary", "border_policy"})
    median_kernel = _positive_odd_int(median["kernel_size"], "$.classical_restoration.median.kernel_size")
    if median_kernel not in {3, 5}:
        raise ConventionValidationError("median kernel_size is not implemented for float32 input")
    gaussian_kernel = _kernel(gaussian["kernel_size"], "$.classical_restoration.gaussian_blur.kernel_size")
    parameters = {
        "identity": {},
        "median": {"kernel_size": median_kernel, "border_policy": _choice(median["border_policy"], "$.classical_restoration.median.border_policy", ["opencv_median_fixed_replicate"])},
        "gaussian_blur": {"kernel_size": gaussian_kernel, "sigma_x": _number(gaussian["sigma_x"], "$.classical_restoration.gaussian_blur.sigma_x", positive=True), "sigma_y": _number(gaussian["sigma_y"], "$.classical_restoration.gaussian_blur.sigma_y", positive=True), "border_type": _border(gaussian["border_type"], "$.classical_restoration.gaussian_blur.border_type")},
        "bilateral": {"diameter": _positive_int(bilateral["diameter"], "$.classical_restoration.bilateral.diameter"), "sigma_color": _number(bilateral["sigma_color"], "$.classical_restoration.bilateral.sigma_color", positive=True), "sigma_space": _number(bilateral["sigma_space"], "$.classical_restoration.bilateral.sigma_space", positive=True), "border_type": _border(bilateral["border_type"], "$.classical_restoration.bilateral.border_type")},
        "nlm": {"h_luminance": _number(nlm["h_luminance"], "$.classical_restoration.nlm.h_luminance", positive=True), "h_color": _number(nlm["h_color"], "$.classical_restoration.nlm.h_color", positive=True), "template_window_size": _positive_odd_int(nlm["template_window_size"], "$.classical_restoration.nlm.template_window_size"), "search_window_size": _positive_odd_int(nlm["search_window_size"], "$.classical_restoration.nlm.search_window_size"), "quantization": _choice(nlm["quantization"], "$.classical_restoration.nlm.quantization", ["round_to_nearest_uint8"]), "color_boundary": _choice(nlm["color_boundary"], "$.classical_restoration.nlm.color_boundary", ["rgb_to_bgr_for_opencv_nlm"]), "border_policy": _choice(nlm["border_policy"], "$.classical_restoration.nlm.border_policy", ["opencv_nlm_library_fixed"])},
    }
    if parameters["nlm"]["search_window_size"] < parameters["nlm"]["template_window_size"]:
        raise ConventionValidationError("NLM search_window_size must be at least template_window_size")
    output = _choice(root["output_policy"], "$.classical_restoration.output_policy", ["clip_0_1", "reject_out_of_range"])
    return parameters, output


def _positive_int(value: Any, path: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ConventionValidationError(f"{path} must be a positive integer")
    return value


def _positive_odd_int(value: Any, path: str) -> int:
    result = _positive_int(value, path)
    if result < 3 or result % 2 == 0:
        raise ConventionValidationError(f"{path} must be an odd integer >= 3")
    return result


def _kernel(value: Any, path: str) -> tuple[int, int]:
    if not isinstance(value, list) or len(value) != 2:
        raise ConventionValidationError(f"{path} must be a two-item YAML sequence")
    return (_positive_odd_int(value[0], f"{path}[0]"), _positive_odd_int(value[1], f"{path}[1]"))


def _border(value: Any, path: str) -> int:
    if value not in _BORDERS:
        raise ConventionValidationError(f"{path} must be one of {sorted(_BORDERS)}")
    return _BORDERS[value]


def _parse_quality(value: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    root = _mapping(value, "$.image_quality", {"psnr", "ssim"})
    psnr = _mapping(root["psnr"], "$.image_quality.psnr", {"data_range"})
    ssim = _mapping(root["ssim"], "$.image_quality.ssim", {"data_range", "channel_axis", "win_size", "gaussian_weights", "sigma", "use_sample_covariance", "k1", "k2"})
    for node, path in ((psnr, "$.image_quality.psnr"), (ssim, "$.image_quality.ssim")):
        if _number(node["data_range"], f"{path}.data_range", positive=True) != 1.0:
            raise ConventionValidationError(f"{path}.data_range must equal 1.0")
    if isinstance(ssim["channel_axis"], bool) or ssim["channel_axis"] not in {-1, 2}:
        raise ConventionValidationError("$.image_quality.ssim.channel_axis must be -1 or 2")
    win_size = _positive_odd_int(ssim["win_size"], "$.image_quality.ssim.win_size")
    for key in ("gaussian_weights", "use_sample_covariance"):
        if not isinstance(ssim[key], bool):
            raise ConventionValidationError(f"$.image_quality.ssim.{key} must be boolean")
    options = {"data_range": 1.0, "channel_axis": ssim["channel_axis"], "win_size": win_size, "gaussian_weights": ssim["gaussian_weights"], "sigma": _number(ssim["sigma"], "$.image_quality.ssim.sigma", positive=True), "use_sample_covariance": ssim["use_sample_covariance"], "k1": _number(ssim["k1"], "$.image_quality.ssim.k1", positive=True), "k2": _number(ssim["k2"], "$.image_quality.ssim.k2", positive=True)}
    return {"data_range": 1.0}, options


def _validate_gates(value: Any) -> None:
    root = _mapping(value, "$.gates", {"code_closure_requires", "real_or_full_execution_requires", "prohibited"})
    _literal(root["code_closure_requires"], "B-007", "$.gates.code_closure_requires")
    _exact_sequence(root["real_or_full_execution_requires"], ["P1C_run_complete", "frozen_phase_1_classifier", "B-001_resolved"], "$.gates.real_or_full_execution_requires")
    _exact_sequence(root["prohibited"], ["real_dataset_execution", "P2B_or_P2C_execution", "benefit_or_native_noise_claim", "entropy_specific_ESVDAE"], "$.gates.prohibited")
