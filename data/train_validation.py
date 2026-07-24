"""Deterministic P1B outer-Train allocation for UCF manifests."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from dataclasses import dataclass, replace
from typing import Iterable

from data.grouping import source_grouped_split
from data.manifest import ManifestRow
from data.views import CANONICAL_UCF_LABELS, UCF_SOURCE_DATASET


def _identity(row: ManifestRow) -> tuple[str, str, int, str, str]:
    if row.source_frame_index is None:
        raise ValueError(f"train row lacks source-frame traceability: {row.filepath}")
    return (row.source_dataset, row.source_video_id, row.source_frame_index, row.filepath, row.file_digest)


def _manifest_digest(rows: Iterable[ManifestRow]) -> str:
    digest = hashlib.sha256()
    for row in rows:
        digest.update(json.dumps(row.to_dict(), separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


@dataclass(frozen=True)
class UcfTrainValidationManifests:
    train: tuple[ManifestRow, ...]
    validation: tuple[ManifestRow, ...]
    report: dict


def build_ucf_grouped_train_validation(
    rows: Iterable[ManifestRow], *, validation_fraction: float, seed: int
) -> UcfTrainValidationManifests:
    """Allocate only outer-Train UCF rows without source-video leakage.

    This preserves inherited folder-label provenance.  It neither reads nor
    selects from the held-out Test split, so it is safe before P1C training.
    """

    source_rows = tuple(sorted(rows, key=_identity))
    if not source_rows:
        raise ValueError("cannot allocate an empty UCF Train manifest")
    seen: set[tuple[str, str, int, str, str]] = set()
    for row in source_rows:
        if row.source_dataset != UCF_SOURCE_DATASET:
            raise ValueError(f"P1B Train allocation requires UCF rows: {row.filepath}")
        if row.split != "train":
            raise ValueError(f"P1B Train allocation accepts only outer-Train rows: {row.filepath}")
        if row.label not in CANONICAL_UCF_LABELS:
            raise ValueError(f"unknown UCF label in Train manifest: {row.filepath}")
        if row.label_scope != "video_inherited" or row.inside_official_interval is not None:
            raise ValueError(f"Train provenance must remain inherited and interval-null: {row.filepath}")
        identity = _identity(row)
        if identity in seen:
            raise ValueError(f"duplicate source-frame identity in Train manifest: {row.filepath}")
        seen.add(identity)

    allocation = source_grouped_split(list(source_rows), validation_fraction=validation_fraction, seed=seed)
    train = tuple(replace(source_rows[index], split="train") for index in allocation.train_indices)
    validation = tuple(replace(source_rows[index], split="validation") for index in allocation.validation_indices)
    train_groups = {(row.source_dataset, row.source_video_id) for row in train}
    validation_groups = {(row.source_dataset, row.source_video_id) for row in validation}
    overlap = sorted(train_groups & validation_groups)
    if overlap:
        raise ValueError(f"source-video leakage after allocation: {overlap[:3]}")
    train_labels = Counter(row.label for row in train)
    validation_labels = Counter(row.label for row in validation)
    missing_train = [label for label in CANONICAL_UCF_LABELS if not train_labels[label]]
    if missing_train:
        raise ValueError(f"allocation removed a class from Train: {missing_train}")
    return UcfTrainValidationManifests(
        train=train,
        validation=validation,
        report={
            "schema_version": "1.0.0",
            "kind": "P1B grouped outer-Train allocation; not model training or evaluation",
            "source_dataset": UCF_SOURCE_DATASET,
            "source_manifest_sha256": _manifest_digest(source_rows),
            "validation_fraction": validation_fraction,
            "seed": seed,
            "grouping_key": "source_video_id",
            "source_row_count": len(source_rows),
            "train_row_count": len(train),
            "validation_row_count": len(validation),
            "train_source_video_count": len(train_groups),
            "validation_source_video_count": len(validation_groups),
            "source_video_overlap_count": len(overlap),
            "class_counts": {
                label: {"train": train_labels[label], "validation": validation_labels[label]}
                for label in CANONICAL_UCF_LABELS
            },
            "assignment_count": len(allocation.assignments),
            "prohibited": ["frame-random split", "test-guided tuning"],
        },
    )
