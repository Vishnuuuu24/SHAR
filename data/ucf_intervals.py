"""Fail-closed P0B mapping for UCF-Crime frame mirrors.

The official UCF-Crime text release records *source-video frame numbers*.  The
Kaggle mirror's ``<video_id>_<frame>.png`` names preserve those numbers, so
this module deliberately performs no sampling-rate conversion.  Interval ends
are treated as inclusive; the boundary is tested here rather than left to a
downstream manifest builder.

This module only maps and reports.  It never writes a manifest or decides an
experiment split.  Any anomalous Test frame that cannot be traced to exactly
one compatible official annotation is quarantined and therefore cannot reach
the P1B event-only view.
"""

from __future__ import annotations

import hashlib
import os
import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import Iterable


CANONICAL_UCF_LABELS = frozenset(
    {
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
    }
)
FOLDER_LABELS = {**{label: label for label in CANONICAL_UCF_LABELS if label != "Normal"}, "NormalVideos": "Normal"}
_FRAME_STEM_RE = re.compile(r"^(?P<video>.+)_(?P<frame>0|[1-9][0-9]*)$")


@dataclass(frozen=True, order=True)
class FrameInterval:
    """One inclusive interval in original source-video frame coordinates."""

    start: int
    end: int

    def __post_init__(self) -> None:
        if self.start < 0 or self.end < self.start:
            raise ValueError("official interval must have non-negative inclusive start <= end")

    def contains(self, source_frame_index: int) -> bool:
        return self.start <= source_frame_index <= self.end


@dataclass(frozen=True)
class OfficialTemporalAnnotation:
    source_video_id: str
    label: str
    intervals: tuple[FrameInterval, ...]
    source_line: int

    def contains(self, source_frame_index: int) -> bool:
        return any(interval.contains(source_frame_index) for interval in self.intervals)


@dataclass(frozen=True)
class FrameReference:
    """A parsed frame in the supplied Kaggle Train/Test mirror."""

    filepath: str
    split: str
    label: str
    source_video_id: str
    source_frame_index: int


@dataclass(frozen=True)
class MappedFrame:
    frame: FrameReference
    inside_official_interval: bool | None


@dataclass(frozen=True)
class QuarantinedFrame:
    filepath: str
    reason: str
    source_video_id: str | None = None
    source_frame_index: int | None = None


@dataclass(frozen=True)
class P0BMappingResult:
    """Deterministic P0B outcome; quarantined rows are never mapped rows."""

    mapped: tuple[MappedFrame, ...]
    quarantined: tuple[QuarantinedFrame, ...]
    source_split_leakage: dict[str, tuple[str, ...]]
    annotation_count: int

    @property
    def ready_for_manifest_materialization(self) -> bool:
        return bool(self.mapped) and not self.quarantined and not self.source_split_leakage

    def assert_ready_for_manifest_materialization(self) -> None:
        if self.source_split_leakage:
            raise ValueError(f"source-video split leakage: {sorted(self.source_split_leakage)}")
        if self.quarantined:
            raise ValueError(f"P0B has quarantined frames: {len(self.quarantined)}")
        if not self.mapped:
            raise ValueError("P0B produced no mapped frames")

    def report(self) -> dict:
        reason_counts = Counter(item.reason for item in self.quarantined)
        mapped_by_split = Counter(item.frame.split for item in self.mapped)
        event_membership = Counter(
            "inside" if item.inside_official_interval is True else "outside"
            for item in self.mapped
            if item.frame.split == "test" and item.frame.label != "Normal"
        )
        return {
            "schema_version": "1.0.0",
            "kind": "P0B UCF source-video and temporal-interval mapping report",
            "interval_coordinate_system": "official source-video frame index",
            "interval_boundary_semantics": "inclusive_start_inclusive_end",
            "annotation_count": self.annotation_count,
            "mapped_row_count": len(self.mapped),
            "mapped_by_outer_split": dict(sorted(mapped_by_split.items())),
            "anomalous_test_membership_counts": dict(sorted(event_membership.items())),
            "quarantined_row_count": len(self.quarantined),
            "quarantine_reason_counts": dict(sorted(reason_counts.items())),
            "quarantine": [asdict(item) for item in self.quarantined],
            "source_video_split_leakage": {
                source_video_id: list(splits)
                for source_video_id, splits in sorted(self.source_split_leakage.items())
            },
            "ready_for_manifest_materialization": self.ready_for_manifest_materialization,
            "scope_assertions": {
                "manifest_written": False,
                "model_training": False,
                "headline_evaluation": False,
            },
        }


@dataclass(frozen=True)
class P0BStreamingMappingResult:
    """Constant-memory summary for mapping the complete local frame mirror.

    The detailed ``P0BMappingResult`` remains the fixture-level API.  This
    summary is used only for full local scans: retaining 1.38 million Python
    frame objects merely to produce a report is not a valid Phase-0 workflow.
    Quarantine examples are bounded; their counts, rather than an unbounded
    in-memory list, remain authoritative for the fail-closed gate.
    """

    mapped_row_count: int
    mapped_by_outer_split: dict[str, int]
    anomalous_test_membership_counts: dict[str, int]
    quarantine_reason_counts: dict[str, int]
    quarantine_examples: tuple[QuarantinedFrame, ...]
    source_video_split_leakage: dict[str, tuple[str, ...]]
    annotation_count: int

    @property
    def quarantined_row_count(self) -> int:
        return sum(self.quarantine_reason_counts.values())

    @property
    def ready_for_manifest_materialization(self) -> bool:
        return (
            self.mapped_row_count > 0
            and self.quarantined_row_count == 0
            and not self.source_video_split_leakage
        )

    def assert_ready_for_manifest_materialization(self) -> None:
        if self.source_video_split_leakage:
            raise ValueError(f"source-video split leakage: {sorted(self.source_video_split_leakage)}")
        if self.quarantined_row_count:
            raise ValueError(f"P0B has quarantined frames: {self.quarantined_row_count}")
        if not self.mapped_row_count:
            raise ValueError("P0B produced no mapped frames")

    def report(self) -> dict:
        return {
            "schema_version": "1.1.0",
            "kind": "P0B UCF source-video and temporal-interval mapping report",
            "execution_mode": "streaming_full_local_scan",
            "interval_coordinate_system": "official source-video frame index",
            "interval_boundary_semantics": "inclusive_start_inclusive_end",
            "annotation_count": self.annotation_count,
            "mapped_row_count": self.mapped_row_count,
            "mapped_by_outer_split": dict(sorted(self.mapped_by_outer_split.items())),
            "anomalous_test_membership_counts": dict(
                sorted(self.anomalous_test_membership_counts.items())
            ),
            "quarantined_row_count": self.quarantined_row_count,
            "quarantine_reason_counts": dict(sorted(self.quarantine_reason_counts.items())),
            "quarantine_examples": [asdict(item) for item in self.quarantine_examples],
            "source_video_split_leakage": {
                source_video_id: list(splits)
                for source_video_id, splits in sorted(self.source_video_split_leakage.items())
            },
            "ready_for_manifest_materialization": self.ready_for_manifest_materialization,
            "scope_assertions": {
                "manifest_written": False,
                "model_training": False,
                "headline_evaluation": False,
            },
        }


def annotation_sha256(annotation_path: Path) -> str:
    """Return the digest of the exact official text file parsed by P0B."""

    return hashlib.sha256(annotation_path.read_bytes()).hexdigest()


def _parse_interval_pair(start_token: str, end_token: str, *, line_number: int) -> FrameInterval | None:
    try:
        start, end = int(start_token), int(end_token)
    except ValueError as exc:
        raise ValueError(f"annotation line {line_number}: interval bounds must be integers") from exc
    if (start, end) == (-1, -1):
        return None
    if start < 0 or end < 0:
        raise ValueError(f"annotation line {line_number}: absent interval must be exactly -1 -1")
    return FrameInterval(start, end)


def parse_official_temporal_annotations(annotation_path: Path) -> dict[str, OfficialTemporalAnnotation]:
    """Parse the official six-column UCF-Crime TXT release without guessing.

    Its columns are ``video_file label start1 end1 start2 end2``.  Source video
    IDs are stored without ``.mp4`` to match the Kaggle frame filename prefix.
    """

    annotations: dict[str, OfficialTemporalAnnotation] = {}
    with annotation_path.open("r", encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            stripped = raw_line.strip()
            if not stripped:
                continue
            columns = stripped.split()
            if len(columns) != 6:
                raise ValueError(f"annotation line {line_number}: expected six columns, found {len(columns)}")
            video_filename, label, start_1, end_1, start_2, end_2 = columns
            if not video_filename.endswith(".mp4"):
                raise ValueError(f"annotation line {line_number}: official video name must end in .mp4")
            source_video_id = video_filename.removesuffix(".mp4")
            if not source_video_id or label not in CANONICAL_UCF_LABELS:
                raise ValueError(f"annotation line {line_number}: unregistered source video or label")
            intervals = tuple(
                interval
                for interval in (
                    _parse_interval_pair(start_1, end_1, line_number=line_number),
                    _parse_interval_pair(start_2, end_2, line_number=line_number),
                )
                if interval is not None
            )
            if label == "Normal" and intervals:
                raise ValueError(f"annotation line {line_number}: Normal source cannot have anomaly intervals")
            if label != "Normal" and not intervals:
                raise ValueError(f"annotation line {line_number}: anomalous source needs at least one interval")
            if source_video_id in annotations:
                raise ValueError(f"annotation line {line_number}: duplicate source video {source_video_id}")
            annotations[source_video_id] = OfficialTemporalAnnotation(
                source_video_id=source_video_id,
                label=label,
                intervals=intervals,
                source_line=line_number,
            )
    if not annotations:
        raise ValueError("official annotation file contains no rows")
    return annotations


def parse_kaggle_frame_relative_path(relative_path: str | Path) -> FrameReference:
    """Parse one mirror path of the exact ``Train|Test/Class/video_frame.png`` form."""

    raw_path = str(relative_path).replace("\\", "/")
    pure_path = PurePosixPath(raw_path)
    if pure_path.is_absolute() or ".." in pure_path.parts or len(pure_path.parts) != 3:
        raise ValueError("frame path must be a relative Train|Test/Class/file.png path")
    outer, folder_label, filename = pure_path.parts
    split_lookup = {"Train": "train", "Test": "test"}
    if outer not in split_lookup:
        raise ValueError("frame path must start with Train or Test")
    if folder_label not in FOLDER_LABELS:
        raise ValueError(f"unregistered UCF folder label: {folder_label}")
    if not filename.endswith(".png"):
        raise ValueError("UCF frame file must end in .png")
    match = _FRAME_STEM_RE.fullmatch(filename.removesuffix(".png"))
    if not match:
        raise ValueError("frame filename must be <source_video_id>_<nonnegative_frame>.png")
    source_video_id = match.group("video")
    if not source_video_id.endswith("_x264"):
        raise ValueError("frame source video ID must preserve the official _x264 suffix")
    return FrameReference(
        filepath=pure_path.as_posix(),
        split=split_lookup[outer],
        label=FOLDER_LABELS[folder_label],
        source_video_id=source_video_id,
        source_frame_index=int(match.group("frame")),
    )


def discover_kaggle_frame_references(frame_root: Path) -> tuple[list[FrameReference], list[QuarantinedFrame]]:
    """Discover PNGs without following symlinks; malformed paths are quarantined."""

    references: list[FrameReference] = []
    quarantined: list[QuarantinedFrame] = []
    for path in sorted(frame_root.rglob("*.png")):
        relative_path = path.relative_to(frame_root).as_posix()
        if path.is_symlink():
            quarantined.append(QuarantinedFrame(relative_path, "symlink_not_allowed"))
            continue
        try:
            references.append(parse_kaggle_frame_relative_path(relative_path))
        except ValueError as exc:
            quarantined.append(QuarantinedFrame(relative_path, f"invalid_frame_path:{exc}"))
    return references, quarantined


def iter_kaggle_frame_references(frame_root: Path) -> Iterable[FrameReference | QuarantinedFrame]:
    """Yield local frame references in stable order without materializing them.

    Filesystem traversal is explicitly sorted and never follows symlinks.  It
    is deliberately restricted to PNGs, matching the frozen Kaggle-mirror
    contract, and is suitable for the complete 1.38-million-frame scan.
    """

    def walk(directory: Path) -> Iterable[Path]:
        with os.scandir(directory) as entries:
            ordered = sorted(entries, key=lambda entry: entry.name)
        for entry in ordered:
            path = Path(entry.path)
            if entry.is_symlink():
                if entry.is_file():
                    yield path
                continue
            if entry.is_dir(follow_symlinks=False):
                yield from walk(path)
            elif entry.is_file(follow_symlinks=False) and path.suffix == ".png":
                yield path

    for path in walk(frame_root):
        relative_path = path.relative_to(frame_root).as_posix()
        if path.is_symlink():
            yield QuarantinedFrame(relative_path, "symlink_not_allowed")
            continue
        try:
            yield parse_kaggle_frame_relative_path(relative_path)
        except ValueError as exc:
            yield QuarantinedFrame(relative_path, f"invalid_frame_path:{exc}")


def stream_map_ucf_frame_references(
    entries: Iterable[FrameReference | QuarantinedFrame],
    annotations: dict[str, OfficialTemporalAnnotation],
    *,
    max_quarantine_examples: int = 100,
) -> P0BStreamingMappingResult:
    """Map a sorted full mirror using bounded memory and fail-closed counts."""
    if isinstance(max_quarantine_examples, bool) or not isinstance(max_quarantine_examples, int) or max_quarantine_examples < 1:
        raise ValueError("max_quarantine_examples must be a positive integer")

    mapped_by_split: Counter[str] = Counter()
    membership: Counter[str] = Counter()
    quarantine_counts: Counter[str] = Counter()
    quarantine_examples: list[QuarantinedFrame] = []
    source_splits: dict[str, set[str]] = defaultdict(set)
    source_frame_counts: Counter[str] = Counter()
    duplicate_source_frame_counts: Counter[str] = Counter()
    completed_sources: set[str] = set()
    current_source: str | None = None
    current_indices: set[int] = set()

    def quarantine(item: QuarantinedFrame) -> None:
        quarantine_counts[item.reason] += 1
        if len(quarantine_examples) < max_quarantine_examples:
            quarantine_examples.append(item)

    for entry in entries:
        if isinstance(entry, QuarantinedFrame):
            quarantine(entry)
            continue
        frame = entry
        source_splits[frame.source_video_id].add(frame.split)
        source_frame_counts[frame.source_video_id] += 1
        if frame.source_video_id != current_source:
            if current_source is not None:
                completed_sources.add(current_source)
            if frame.source_video_id in completed_sources:
                quarantine(
                    QuarantinedFrame(
                        frame.filepath,
                        "source_video_not_contiguous_in_sorted_mirror",
                        frame.source_video_id,
                        frame.source_frame_index,
                    )
                )
                continue
            current_source = frame.source_video_id
            current_indices = set()
        if frame.source_frame_index in current_indices:
            duplicate_source_frame_counts[frame.source_video_id] += 1
            quarantine(
                QuarantinedFrame(
                    frame.filepath,
                    "duplicate_source_frame",
                    frame.source_video_id,
                    frame.source_frame_index,
                )
            )
            continue
        current_indices.add(frame.source_frame_index)
        if frame.split == "test" and frame.label != "Normal":
            annotation = annotations.get(frame.source_video_id)
            if annotation is None:
                quarantine(
                    QuarantinedFrame(
                        frame.filepath,
                        "missing_official_annotation_for_anomalous_test_source",
                        frame.source_video_id,
                        frame.source_frame_index,
                    )
                )
                continue
            if annotation.label != frame.label:
                quarantine(
                    QuarantinedFrame(
                        frame.filepath,
                        "official_annotation_label_mismatch",
                        frame.source_video_id,
                        frame.source_frame_index,
                    )
                )
                continue
            membership["inside" if annotation.contains(frame.source_frame_index) else "outside"] += 1
        mapped_by_split[frame.split] += 1

    leakage = {
        source_video_id: tuple(sorted(splits))
        for source_video_id, splits in source_splits.items()
        if len(splits) > 1
    }
    if leakage:
        for source_video_id in leakage:
            quarantine_counts["source_video_crosses_outer_splits"] += source_frame_counts[source_video_id]
            if len(quarantine_examples) < max_quarantine_examples:
                quarantine_examples.append(
                    QuarantinedFrame(
                        f"<source:{source_video_id}>",
                        "source_video_crosses_outer_splits",
                        source_video_id,
                    )
                )
    # A row is counted only after duplicate/mapping checks above, so no later
    # subtraction is needed (and doing so would undercount the valid rows).
    mapped_row_count = sum(mapped_by_split.values())
    return P0BStreamingMappingResult(
        mapped_row_count=mapped_row_count,
        mapped_by_outer_split=dict(mapped_by_split),
        anomalous_test_membership_counts=dict(membership),
        quarantine_reason_counts=dict(quarantine_counts),
        quarantine_examples=tuple(quarantine_examples),
        source_video_split_leakage=leakage,
        annotation_count=len(annotations),
    )


def _ordered_quarantine(items: Iterable[QuarantinedFrame]) -> tuple[QuarantinedFrame, ...]:
    return tuple(sorted(items, key=lambda item: (item.filepath, item.reason, item.source_video_id or "", item.source_frame_index or -1)))


def map_ucf_frame_references(
    frames: Iterable[FrameReference],
    annotations: dict[str, OfficialTemporalAnnotation],
    *,
    pre_quarantined: Iterable[QuarantinedFrame] = (),
) -> P0BMappingResult:
    """Map supplied frame references, quarantining every unresolved condition.

    Train rows keep their weak video-inherited provenance and have no interval
    membership.  Test Normal rows also have null membership.  Only anomalous
    Test rows are eligible for an official inclusive interval lookup.
    """

    frame_list = sorted(frames, key=lambda item: (item.filepath, item.source_video_id, item.source_frame_index))
    quarantined = list(pre_quarantined)
    source_splits: dict[str, set[str]] = defaultdict(set)
    source_frame_paths: dict[tuple[str, int], list[FrameReference]] = defaultdict(list)
    for frame in frame_list:
        source_splits[frame.source_video_id].add(frame.split)
        source_frame_paths[(frame.source_video_id, frame.source_frame_index)].append(frame)

    leaking_sources = {
        source_video_id: tuple(sorted(splits))
        for source_video_id, splits in source_splits.items()
        if len(splits) > 1
    }
    duplicate_keys = {key for key, values in source_frame_paths.items() if len(values) > 1}
    mapped: list[MappedFrame] = []
    for frame in frame_list:
        frame_key = (frame.source_video_id, frame.source_frame_index)
        if frame.source_video_id in leaking_sources:
            quarantined.append(
                QuarantinedFrame(
                    frame.filepath,
                    "source_video_crosses_outer_splits",
                    frame.source_video_id,
                    frame.source_frame_index,
                )
            )
            continue
        if frame_key in duplicate_keys:
            quarantined.append(
                QuarantinedFrame(
                    frame.filepath,
                    "duplicate_source_frame",
                    frame.source_video_id,
                    frame.source_frame_index,
                )
            )
            continue
        if frame.split == "train" or frame.label == "Normal":
            mapped.append(MappedFrame(frame, None))
            continue
        annotation = annotations.get(frame.source_video_id)
        if annotation is None:
            quarantined.append(
                QuarantinedFrame(
                    frame.filepath,
                    "missing_official_annotation_for_anomalous_test_source",
                    frame.source_video_id,
                    frame.source_frame_index,
                )
            )
            continue
        if annotation.label != frame.label:
            quarantined.append(
                QuarantinedFrame(
                    frame.filepath,
                    "official_annotation_label_mismatch",
                    frame.source_video_id,
                    frame.source_frame_index,
                )
            )
            continue
        mapped.append(MappedFrame(frame, annotation.contains(frame.source_frame_index)))
    return P0BMappingResult(
        mapped=tuple(sorted(mapped, key=lambda item: (item.frame.filepath, item.frame.source_video_id, item.frame.source_frame_index))),
        quarantined=_ordered_quarantine(quarantined),
        source_split_leakage=dict(sorted(leaking_sources.items())),
        annotation_count=len(annotations),
    )
