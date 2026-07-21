"""Classical P2A restoration methods with an explicit, uniform contract.

The public functions intentionally have no experiment-parameter defaults.  A
caller must name the method and provide every parameter used by that method.
All methods consume and return finite ``float32`` HWC RGB arrays in ``[0, 1]``.
"""

from __future__ import annotations

from collections.abc import Mapping
from numbers import Integral, Real

import cv2
import numpy as np
from numpy.typing import NDArray


FloatImage = NDArray[np.float32]
ParameterValue = str | int | float | tuple[int, int]
RESTORATION_METHODS = frozenset(
    {"identity", "median", "gaussian_blur", "bilateral", "nlm"}
)

_SUPPORTED_BORDER_TYPES = frozenset(
    {
        cv2.BORDER_REPLICATE,
        cv2.BORDER_REFLECT,
        cv2.BORDER_REFLECT_101,
    }
)


def validate_float32_hwc_rgb(image: np.ndarray, *, argument_name: str) -> None:
    """Validate the canonical P2A image representation without modifying it."""

    if not isinstance(image, np.ndarray):
        raise TypeError(f"{argument_name} must be a numpy.ndarray")
    if image.dtype != np.float32:
        raise TypeError(f"{argument_name} must have dtype float32")
    if image.ndim != 3 or image.shape[2] != 3 or image.shape[0] < 1 or image.shape[1] < 1:
        raise ValueError(f"{argument_name} must have non-empty HWC RGB shape [H,W,3]")
    if not np.isfinite(image).all():
        raise ValueError(f"{argument_name} must contain only finite values")
    if np.any(image < 0.0) or np.any(image > 1.0):
        raise ValueError(f"{argument_name} values must be in [0,1]")


def restore_image(
    image: np.ndarray,
    *,
    method: str,
    parameters: Mapping[str, ParameterValue],
    output_policy: str,
) -> FloatImage:
    """Apply one registered classical method to one canonical RGB image.

    Required parameter mappings are:

    - ``identity``: ``{}``
    - ``median``: ``kernel_size`` and explicit OpenCV fixed-border policy
    - ``gaussian_blur``: ``kernel_size=(height, width)``, ``sigma_x``, ``sigma_y``,
      and OpenCV ``border_type``
    - ``bilateral``: ``diameter``, ``sigma_color`` (on the ``[0,1]`` scale),
      ``sigma_space``, and OpenCV ``border_type``
    - ``nlm``: ``h_luminance`` and ``h_color`` (on OpenCV's 8-bit scale),
      ``template_window_size``, ``search_window_size``, explicit quantization,
      RGB/BGR library-boundary policy, and pinned-library border policy

    OpenCV's colored NLM accepts only 8-bit three-channel input (BGR at the
    OpenCV boundary). That method therefore uses a fixed, documented
    round-to-nearest ``[0,255]`` conversion and converts its result back to the
    canonical representation. ``output_policy`` makes final clipping explicit.
    """

    validate_float32_hwc_rgb(image, argument_name="image")
    if not isinstance(method, str) or method not in RESTORATION_METHODS:
        raise ValueError(f"method must be one of {sorted(RESTORATION_METHODS)}")
    if not isinstance(parameters, Mapping):
        raise TypeError("parameters must be a mapping")
    if output_policy not in {"clip_0_1", "reject_out_of_range"}:
        raise ValueError("output_policy must be 'clip_0_1' or 'reject_out_of_range'")

    source = np.ascontiguousarray(image.copy())
    if method == "identity":
        _require_exact_keys(parameters, expected=frozenset())
        restored = source.copy()
    elif method == "median":
        _require_exact_keys(
            parameters, expected=frozenset({"kernel_size", "border_policy"})
        )
        _required_literal(
            parameters,
            "border_policy",
            "opencv_median_fixed_replicate",
        )
        kernel_size = _required_odd_integer(parameters, "kernel_size", minimum=3)
        if kernel_size not in {3, 5}:
            raise ValueError("median kernel_size must be 3 or 5 for float32 OpenCV input")
        restored = cv2.medianBlur(source, kernel_size)
    elif method == "gaussian_blur":
        _require_exact_keys(
            parameters,
            expected=frozenset({"kernel_size", "sigma_x", "sigma_y", "border_type"}),
        )
        kernel_size = _required_odd_kernel(parameters, "kernel_size")
        sigma_x = _required_positive_real(parameters, "sigma_x")
        sigma_y = _required_positive_real(parameters, "sigma_y")
        border_type = _required_border_type(parameters, "border_type")
        # OpenCV expects (width, height), while the public contract names the
        # tuple (height, width) to match NumPy image dimensions.
        restored = cv2.GaussianBlur(
            source,
            (kernel_size[1], kernel_size[0]),
            sigmaX=sigma_x,
            sigmaY=sigma_y,
            borderType=border_type,
        )
    elif method == "bilateral":
        _require_exact_keys(
            parameters,
            expected=frozenset({"diameter", "sigma_color", "sigma_space", "border_type"}),
        )
        diameter = _required_positive_integer(parameters, "diameter")
        sigma_color = _required_positive_real(parameters, "sigma_color")
        sigma_space = _required_positive_real(parameters, "sigma_space")
        border_type = _required_border_type(parameters, "border_type")
        restored = cv2.bilateralFilter(
            source,
            d=diameter,
            sigmaColor=sigma_color,
            sigmaSpace=sigma_space,
            borderType=border_type,
        )
    else:
        _require_exact_keys(
            parameters,
            expected=frozenset(
                {"h_luminance", "h_color", "template_window_size", "search_window_size"}
                | {"quantization", "color_boundary", "border_policy"}
            ),
        )
        h_luminance = _required_positive_real(parameters, "h_luminance")
        h_color = _required_positive_real(parameters, "h_color")
        template_window_size = _required_odd_integer(
            parameters, "template_window_size", minimum=3
        )
        search_window_size = _required_odd_integer(
            parameters, "search_window_size", minimum=3
        )
        if search_window_size < template_window_size:
            raise ValueError("search_window_size must be at least template_window_size")
        _required_literal(parameters, "quantization", "round_to_nearest_uint8")
        _required_literal(parameters, "color_boundary", "rgb_to_bgr_for_opencv_nlm")
        _required_literal(parameters, "border_policy", "opencv_nlm_library_fixed")
        source_uint8_rgb = np.rint(source * np.float32(255.0)).astype(np.uint8)
        # OpenCV's colored NLM interprets its three channels as BGR.  Convert
        # explicitly at the library boundary so the public contract stays RGB.
        source_uint8_bgr = np.ascontiguousarray(source_uint8_rgb[..., ::-1])
        restored_uint8_bgr = cv2.fastNlMeansDenoisingColored(
            source_uint8_bgr,
            None,
            h_luminance,
            h_color,
            template_window_size,
            search_window_size,
        )
        restored_uint8_rgb = np.ascontiguousarray(restored_uint8_bgr[..., ::-1])
        restored = restored_uint8_rgb.astype(np.float32) / np.float32(255.0)

    output = np.asarray(restored, dtype=np.float32)
    if output.shape != image.shape:
        raise RuntimeError(
            f"restoration changed shape from {tuple(image.shape)} to {tuple(output.shape)}"
        )
    if not np.isfinite(output).all():
        raise RuntimeError("restoration produced non-finite values")
    if output_policy == "clip_0_1":
        output = np.clip(output, np.float32(0.0), np.float32(1.0))
    elif output_policy == "reject_out_of_range":
        if np.any(output < 0.0) or np.any(output > 1.0):
            raise RuntimeError("restoration output is outside [0,1]")
    output = np.ascontiguousarray(output)
    if output.dtype != np.float32:
        raise RuntimeError("restoration did not preserve float32 dtype")
    return output


def restore_batch(
    images: np.ndarray,
    *,
    method: str,
    parameters: Mapping[str, ParameterValue],
    output_policy: str,
) -> FloatImage:
    """Apply ``restore_image`` independently to each item in an NHWC batch."""

    if not isinstance(images, np.ndarray):
        raise TypeError("images must be a numpy.ndarray")
    if images.dtype != np.float32:
        raise TypeError("images must have dtype float32")
    if images.ndim != 4 or images.shape[0] < 1 or images.shape[3] != 3:
        raise ValueError("images must have non-empty NHWC RGB shape [N,H,W,3]")
    if not np.isfinite(images).all():
        raise ValueError("images must contain only finite values")
    if np.any(images < 0.0) or np.any(images > 1.0):
        raise ValueError("images values must be in [0,1]")

    return np.stack(
        [
            restore_image(
                image, method=method, parameters=parameters, output_policy=output_policy
            )
            for image in images
        ],
        axis=0,
    ).astype(np.float32, copy=False)


def _require_exact_keys(
    parameters: Mapping[str, ParameterValue], *, expected: frozenset[str]
) -> None:
    keys = set(parameters)
    if keys != expected:
        missing = sorted(expected - keys)
        unexpected = sorted(keys - expected)
        raise ValueError(
            f"parameters must have exactly {sorted(expected)}; "
            f"missing={missing}, unexpected={unexpected}"
        )


def _required_positive_integer(parameters: Mapping[str, ParameterValue], key: str) -> int:
    value = parameters[key]
    if isinstance(value, bool) or not isinstance(value, Integral) or value <= 0:
        raise ValueError(f"{key} must be a positive integer")
    return int(value)


def _required_odd_integer(
    parameters: Mapping[str, ParameterValue], key: str, *, minimum: int
) -> int:
    value = _required_positive_integer(parameters, key)
    if value < minimum or value % 2 == 0:
        raise ValueError(f"{key} must be an odd integer >= {minimum}")
    return value


def _required_positive_real(parameters: Mapping[str, ParameterValue], key: str) -> float:
    value = parameters[key]
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{key} must be a finite positive number")
    value = float(value)
    if not np.isfinite(value) or value <= 0.0:
        raise ValueError(f"{key} must be a finite positive number")
    return value


def _required_odd_kernel(
    parameters: Mapping[str, ParameterValue], key: str
) -> tuple[int, int]:
    value = parameters[key]
    if not isinstance(value, tuple) or len(value) != 2:
        raise ValueError(f"{key} must be an explicit (height, width) tuple")
    height, width = value
    if any(isinstance(item, bool) or not isinstance(item, Integral) for item in value):
        raise ValueError(f"{key} entries must be integers")
    if height < 1 or width < 1 or height % 2 == 0 or width % 2 == 0:
        raise ValueError(f"{key} entries must be positive odd integers")
    return int(height), int(width)


def _required_border_type(parameters: Mapping[str, ParameterValue], key: str) -> int:
    value = parameters[key]
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise ValueError(f"{key} must be an explicit supported OpenCV border integer")
    value = int(value)
    if value not in _SUPPORTED_BORDER_TYPES:
        raise ValueError(f"{key} is not a supported OpenCV border type")
    return value


def _required_literal(
    parameters: Mapping[str, ParameterValue], key: str, expected: str
) -> str:
    value = parameters[key]
    if value != expected:
        raise ValueError(f"{key} must explicitly equal {expected}")
    return expected
