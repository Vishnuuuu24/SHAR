"""Strict UCF evaluation-view construction for P1B.

The builders are intentionally data-agnostic: P0B owns mapping source frames to
official intervals. P1B consumes only fully mapped manifest rows and refuses to
guess unresolved anomalous membership.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from dataclasses import dataclass, replace
from typing import Iterable

from data.contracts import MANIFEST_FIELDS
from data.manifest import ManifestRow


EVENT_ONLY_VIEW_NAME = "official-interval-derived event-only 14-label evaluation"
NOISY_PROXY_VIEW_NAME = "full-directory inherited-label noisy proxy"
CANONICAL_UCF_LABELS = (
    "Abuse",
    "Arrest",
    "Arson",
    "Assault",
    "Burglary",
    "Explosion",
    "Fighting",
    "RoadAccidents",
    "Robbery",
    "Shooting",
    "Shoplifting",
    "Stealing",
    "Vandalism",
    "Normal",
)
UCF_SOURCE_DATASET = "ucf_crime_kaggle_frames"


def _manifest_digest(rows: Iterable[ManifestRow]) -> str:
    digest = hashlib.sha256()
    for row in rows:
        digest.update(
            json.dumps(row.to_dict(), separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        )
        digest.update(b"\n")
    return digest.hexdigest()


def _identity(row: ManifestRow) -> tuple[str, str, int, str, str]:
    if row.source_frame_index is None:
        raise ValueError(f"test row lacks source-frame traceability: {row.filepath}")
    return (row.source_dataset, row.source_video_id, row.source_frame_index, row.filepath, row.file_digest)


def _source_frame_key(row: ManifestRow) -> tuple[str, str, int]:
    if row.source_frame_index is None:
        raise ValueError(f"test row lacks source-frame traceability: {row.filepath}")
    return (row.source_dataset, row.source_video_id, row.source_frame_index)


def _view_summary(name: str, rows: tuple[ManifestRow, ...]) -> dict:
    counts = Counter(row.label for row in rows)
    return {
        "name": name,
        "row_count": len(rows),
        "source_video_count": len({(row.source_dataset, row.source_video_id) for row in rows}),
        "class_counts": {label: counts.get(label, 0) for label in CANONICAL_UCF_LABELS},
        "manifest_digest": _manifest_digest(rows),
    }


@dataclass(frozen=True)
class UcfEvaluationViews:
    event_only: tuple[ManifestRow, ...]
    noisy_proxy: tuple[ManifestRow, ...]
    report: dict


def build_ucf_noisy_proxy_view(
    rows: Iterable[ManifestRow],
    *,
    source_dataset: str = UCF_SOURCE_DATASET,
    allow_fixture_source: bool = False,
) -> tuple[ManifestRow, ...]:
    """Return deterministic folder-provenance Test rows for proxy sensitivity use."""

    if not source_dataset:
        raise ValueError("source_dataset is required")
    if source_dataset != UCF_SOURCE_DATASET and not allow_fixture_source:
        raise ValueError(
            f"production UCF views require source_dataset={UCF_SOURCE_DATASET}; "
            "non-production fixtures require allow_fixture_source=True"
        )
    all_rows = tuple(rows)
    test_rows = tuple(
        sorted(
            (row for row in all_rows if row.split == "test" and row.source_dataset == source_dataset),
            key=_identity,
        )
    )
    unexpected_test = [
        row.source_dataset
        for row in all_rows
        if row.split == "test" and row.source_dataset != source_dataset
    ]
    if unexpected_test:
        raise ValueError(f"non-UCF test rows cannot enter UCF views: {sorted(set(unexpected_test))}")
    if not test_rows:
        raise ValueError("cannot build UCF evaluation views without test rows")
    seen: set[tuple[str, str, int]] = set()
    for row in test_rows:
        if row.label not in CANONICAL_UCF_LABELS:
            raise ValueError(f"unknown UCF label in test manifest: {row.label}")
        if row.label_scope != "video_inherited":
            raise ValueError(f"source Test rows must preserve video_inherited folder provenance: {row.filepath}")
        source_frame = _source_frame_key(row)
        if source_frame in seen:
            raise ValueError(f"duplicate source-frame identity: {source_frame}")
        seen.add(source_frame)
        if row.label == "Normal" and row.inside_official_interval is not None:
            raise ValueError(f"Normal row interval membership must be null: {row.filepath}")
    return test_rows


def build_ucf_evaluation_views(
    rows: Iterable[ManifestRow],
    *,
    official_annotation_version: str,
    official_annotation_digest: str,
    source_dataset: str = UCF_SOURCE_DATASET,
    allow_fixture_source: bool = False,
    fixture_only: bool = False,
) -> UcfEvaluationViews:
    """Build the two frozen UCF test views without inferring interval membership.

    Normal test-video frames always remain in the event-only view. Anomalous
    frames enter it only when ``inside_official_interval`` is exactly ``True``.
    The noisy proxy contains every test row. Any unresolved anomalous interval,
    contradictory Normal interval, duplicate frame identity, or unknown label is
    a hard error rather than a silent exclusion.
    """

    if not official_annotation_version:
        raise ValueError("official_annotation_version is required")
    if len(official_annotation_digest) != 64 or any(
        character not in "0123456789abcdef" for character in official_annotation_digest
    ):
        raise ValueError("official_annotation_digest must be a SHA-256 digest")
    test_rows = build_ucf_noisy_proxy_view(
        rows, source_dataset=source_dataset, allow_fixture_source=allow_fixture_source
    )

    event_only: list[ManifestRow] = []
    excluded_outside = 0
    for row in test_rows:
        if row.label == "Normal":
            event_only.append(row)
        elif row.inside_official_interval is True:
            event_only.append(
                replace(
                    row,
                    label_scope="temporal_interval",
                    label_source=official_annotation_version,
                    annotation_version=official_annotation_version,
                )
            )
        elif row.inside_official_interval is False:
            excluded_outside += 1
        else:
            raise ValueError(f"anomalous test row has unresolved interval membership: {row.filepath}")

    event_tuple = tuple(event_only)
    present = {row.label for row in event_tuple}
    missing = [label for label in CANONICAL_UCF_LABELS if label not in present]
    report = {
        "schema_version": "1.0.0",
        "kind": "P1B evaluation-view membership report",
        "traceability_fields": MANIFEST_FIELDS,
        "source_dataset": source_dataset,
        "source_manifest_sha256": _manifest_digest(test_rows),
        "membership_rule_version": "ucf-event-only-v1",
        "folder_mirror_versions": sorted({row.annotation_version for row in test_rows}),
        "official_annotation_version": official_annotation_version,
        "official_annotation_digest": official_annotation_digest,
        "test_input_row_count": len(test_rows),
        "excluded_by_reason_counts": {"outside_official_interval": excluded_outside},
        "unresolved_count": 0,
        "views": {
            "event_only": _view_summary(EVENT_ONLY_VIEW_NAME, event_tuple),
            "noisy_proxy": _view_summary(NOISY_PROXY_VIEW_NAME, test_rows),
        },
        "missing_headline_labels": missing,
        "headline_claim_blocked": bool(missing),
        "ready_for_real_evaluation": not fixture_only and not missing,
        "fixture_only": fixture_only,
    }
    return UcfEvaluationViews(event_only=event_tuple, noisy_proxy=test_rows, report=report)
