"""Strict P1A manifest loading with config-root and provenance enforcement."""

from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterator

from data.contracts import MANIFEST_FIELDS, validate_manifest_row
from data.inventory import sha256_file


@dataclass(frozen=True)
class ManifestRow:
    filepath: str
    source_dataset: str
    source_video_id: str
    source_frame_index: int | None
    label: str
    label_scope: str
    label_source: str
    annotation_version: str
    inside_official_interval: bool | None
    split: str
    file_digest: str

    def to_dict(self) -> dict:
        return asdict(self)


def _nullable_integer(value: str, field: str, line: int) -> int | None:
    if value == "":
        return None
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"line {line}: {field} must be an integer or empty") from exc


def _nullable_boolean(value: str, field: str, line: int) -> bool | None:
    normalized = value.strip().lower()
    if normalized == "":
        return None
    if normalized == "true":
        return True
    if normalized == "false":
        return False
    raise ValueError(f"line {line}: {field} must be true, false, or empty")


def resolve_manifest_path(row: ManifestRow, dataset_roots: dict[str, Path]) -> Path:
    if row.source_dataset not in dataset_roots:
        raise ValueError(f"no configured root for source_dataset={row.source_dataset}")
    root = dataset_roots[row.source_dataset].resolve()
    candidate = (root / row.filepath).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"manifest path escapes configured root: {row.filepath}") from exc
    return candidate


def load_manifest(
    manifest_path: Path,
    dataset_roots: dict[str, Path],
    *,
    verify_files: bool = True,
    verify_digests: bool = False,
) -> list[ManifestRow]:
    rows: list[ManifestRow] = []
    with manifest_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != MANIFEST_FIELDS:
            raise ValueError(f"manifest header/order must be exactly {MANIFEST_FIELDS}; found {reader.fieldnames}")
        for line, raw in enumerate(reader, start=2):
            typed = {
                **raw,
                "source_frame_index": _nullable_integer(raw["source_frame_index"], "source_frame_index", line),
                "inside_official_interval": _nullable_boolean(
                    raw["inside_official_interval"], "inside_official_interval", line
                ),
            }
            issues = validate_manifest_row(typed)
            if issues:
                raise ValueError(f"line {line}: {'; '.join(issues)}")
            row = ManifestRow(**typed)
            path = resolve_manifest_path(row, dataset_roots)
            if verify_files and not path.is_file():
                raise FileNotFoundError(f"line {line}: manifest file is missing: {path}")
            if verify_digests:
                digest, _, _ = sha256_file(path)
                if digest != row.file_digest:
                    raise ValueError(f"line {line}: content digest mismatch for {row.filepath}")
            rows.append(row)
    if not rows:
        raise ValueError("manifest must contain at least one row")
    return rows


def iter_split(rows: list[ManifestRow], split: str) -> Iterator[ManifestRow]:
    yield from (row for row in rows if row.split == split)
