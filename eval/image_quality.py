"""Explicit clean-reference-first image-quality metrics for P2A."""

from __future__ import annotations

from numbers import Real

import numpy as np
from skimage.metrics import peak_signal_noise_ratio, structural_similarity


def psnr(
    clean_reference: np.ndarray,
    candidate: np.ndarray,
    *,
    data_range: float,
) -> float:
    """Return PSNR with the uncorrupted image supplied first."""

    _validate_pair(clean_reference, candidate)
    checked_data_range = _validate_positive_finite(data_range, argument_name="data_range")
    return float(
        peak_signal_noise_ratio(
            clean_reference,
            candidate,
            data_range=checked_data_range,
        )
    )


def ssim(
    clean_reference: np.ndarray,
    candidate: np.ndarray,
    *,
    data_range: float,
    channel_axis: int,
    win_size: int,
    gaussian_weights: bool,
    sigma: float,
    use_sample_covariance: bool,
    k1: float,
    k2: float,
) -> float:
    """Return SSIM with every scientifically relevant option explicit."""

    _validate_pair(clean_reference, candidate)
    checked_data_range = _validate_positive_finite(data_range, argument_name="data_range")
    if isinstance(channel_axis, bool) or not isinstance(channel_axis, int):
        raise TypeError("channel_axis must be an integer")
    if channel_axis not in (-1, 2):
        raise ValueError("channel_axis must identify the HWC RGB channel axis (-1 or 2)")
    if isinstance(win_size, bool) or not isinstance(win_size, int):
        raise TypeError("win_size must be an integer")
    if win_size < 3 or win_size % 2 == 0:
        raise ValueError("win_size must be an odd integer >= 3")
    if win_size > min(clean_reference.shape[0], clean_reference.shape[1]):
        raise ValueError("win_size cannot exceed either spatial image dimension")
    if not isinstance(gaussian_weights, bool):
        raise TypeError("gaussian_weights must be bool")
    checked_sigma = _validate_positive_finite(sigma, argument_name="sigma")
    if not isinstance(use_sample_covariance, bool):
        raise TypeError("use_sample_covariance must be bool")
    checked_k1 = _validate_positive_finite(k1, argument_name="k1")
    checked_k2 = _validate_positive_finite(k2, argument_name="k2")

    return float(
        structural_similarity(
            clean_reference,
            candidate,
            data_range=checked_data_range,
            channel_axis=channel_axis,
            win_size=win_size,
            gaussian_weights=gaussian_weights,
            sigma=checked_sigma,
            use_sample_covariance=use_sample_covariance,
            K1=checked_k1,
            K2=checked_k2,
            gradient=False,
            full=False,
        )
    )


def _validate_pair(clean_reference: np.ndarray, candidate: np.ndarray) -> None:
    _validate_image(clean_reference, argument_name="clean_reference")
    _validate_image(candidate, argument_name="candidate")
    if clean_reference.shape != candidate.shape:
        raise ValueError("clean_reference and candidate must have identical shapes")
    if clean_reference.dtype != candidate.dtype:
        raise TypeError("clean_reference and candidate must have identical dtypes")


def _validate_image(image: np.ndarray, *, argument_name: str) -> None:
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


def _validate_positive_finite(value: float, *, argument_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError(f"{argument_name} must be a real number")
    checked = float(value)
    if not np.isfinite(checked) or checked <= 0.0:
        raise ValueError(f"{argument_name} must be finite and positive")
    if argument_name == "data_range" and checked != 1.0:
        raise ValueError("data_range must equal 1.0 for the float32 [0,1] image contract")
    return checked
