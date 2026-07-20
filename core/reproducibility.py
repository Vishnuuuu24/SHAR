"""Central deterministic seed policy for SHAR."""

from __future__ import annotations

import hashlib
import os
import random
from dataclasses import dataclass

import numpy as np
import torch


@dataclass(frozen=True)
class DeterminismReport:
    seed: int
    deterministic_algorithms: bool
    warn_only: bool
    python_hash_seed: str


def stable_sample_seed(
    relative_path: str,
    file_digest: str,
    global_seed: int,
    transform_id: str,
) -> int:
    """Derive the DATA_SPEC seed from an unambiguous SHA-256 record."""
    if not relative_path or not transform_id:
        raise ValueError("relative_path and transform_id must be non-empty")
    if len(file_digest) != 64 or any(character not in "0123456789abcdef" for character in file_digest):
        raise ValueError("file_digest must be a lowercase SHA-256")
    if isinstance(global_seed, bool) or not isinstance(global_seed, int) or global_seed < 0:
        raise ValueError("global_seed must be a non-negative integer")
    payload = "\0".join((relative_path, file_digest, str(global_seed), transform_id)).encode("utf-8")
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big", signed=False)


def deterministic_noise_fixture(
    relative_path: str,
    file_digest: str,
    global_seed: int,
    transform_id: str,
    shape: tuple[int, ...],
) -> np.ndarray:
    """Generate a bitwise fixture used to validate the future noise-seed path."""
    if not shape or any(dimension <= 0 for dimension in shape):
        raise ValueError("shape must contain positive dimensions")
    seed = stable_sample_seed(relative_path, file_digest, global_seed, transform_id)
    generator = np.random.Generator(np.random.PCG64(seed))
    return generator.standard_normal(shape, dtype=np.float32)


def seed_everything(seed: int, *, deterministic: bool = True, warn_only: bool = False) -> DeterminismReport:
    if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
        raise ValueError("seed must be a non-negative integer")
    random.seed(seed)
    np.random.seed(seed % (2**32))
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.use_deterministic_algorithms(deterministic, warn_only=warn_only)
    return DeterminismReport(
        seed=seed,
        deterministic_algorithms=torch.are_deterministic_algorithms_enabled(),
        warn_only=warn_only,
        python_hash_seed=os.environ.get("PYTHONHASHSEED", "not_runtime_mutable"),
    )


def dataloader_worker_seed(worker_id: int, global_seed: int) -> int:
    if worker_id < 0:
        raise ValueError("worker_id must be non-negative")
    return (global_seed + worker_id) % (2**32)


def seed_dataloader_worker(worker_id: int) -> None:
    worker_seed = torch.initial_seed() % (2**32)
    np.random.seed(worker_seed)
    random.seed(worker_seed)
