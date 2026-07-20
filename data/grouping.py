"""Deterministic source-video grouping and sampler planning."""

from __future__ import annotations

import hashlib
import random
from collections import defaultdict
from dataclasses import dataclass

from data.manifest import ManifestRow


GroupKey = tuple[str, str]


@dataclass(frozen=True)
class GroupedSplit:
    assignments: dict[GroupKey, str]
    train_indices: list[int]
    validation_indices: list[int]
    class_counts: dict[str, dict[str, int]]


def _rank(label: str, group: GroupKey, seed: int) -> bytes:
    return hashlib.sha256(f"{seed}\0{label}\0{group[0]}\0{group[1]}".encode()).digest()


def source_grouped_split(rows: list[ManifestRow], validation_fraction: float = 0.1, seed: int = 0) -> GroupedSplit:
    if not 0 < validation_fraction < 1:
        raise ValueError("validation_fraction must be between zero and one")
    if not rows:
        raise ValueError("rows must not be empty")
    group_indices: dict[GroupKey, list[int]] = defaultdict(list)
    group_labels: dict[GroupKey, str] = {}
    for index, row in enumerate(rows):
        if row.split != "train":
            raise ValueError(
                f"source_grouped_split accepts only outer-Train rows; found split={row.split} at index {index}"
            )
        group = (row.source_dataset, row.source_video_id)
        prior = group_labels.setdefault(group, row.label)
        if prior != row.label:
            raise ValueError(f"source group has multiple labels: {group}")
        group_indices[group].append(index)

    label_groups: dict[str, list[GroupKey]] = defaultdict(list)
    for group, label in group_labels.items():
        label_groups[label].append(group)

    assignments: dict[GroupKey, str] = {}
    for label, groups in sorted(label_groups.items()):
        ranked = sorted(groups, key=lambda group: _rank(label, group, seed))
        total_rows = sum(len(group_indices[group]) for group in ranked)
        target_rows = max(1, round(total_rows * validation_fraction)) if len(ranked) > 1 else 0
        selected: set[GroupKey] = set()
        selected_rows = 0
        if target_rows:
            # Choose the closest single group first, then add only groups that
            # reduce absolute target error. At least one group remains Train.
            first = min(
                ranked,
                key=lambda group: (abs(len(group_indices[group]) - target_rows), _rank(label, group, seed)),
            )
            selected.add(first)
            selected_rows = len(group_indices[first])
            while len(selected) < len(ranked) - 1:
                candidates = [group for group in ranked if group not in selected]
                best = min(
                    candidates,
                    key=lambda group: (
                        abs(selected_rows + len(group_indices[group]) - target_rows),
                        _rank(label, group, seed),
                    ),
                )
                current_error = abs(selected_rows - target_rows)
                candidate_error = abs(selected_rows + len(group_indices[best]) - target_rows)
                if candidate_error >= current_error:
                    break
                selected.add(best)
                selected_rows += len(group_indices[best])
        for group in ranked:
            assignments[group] = "validation" if group in selected else "train"

    train_indices: list[int] = []
    validation_indices: list[int] = []
    class_counts: dict[str, dict[str, int]] = defaultdict(lambda: {"train": 0, "validation": 0})
    for group, indices in group_indices.items():
        split = assignments[group]
        (validation_indices if split == "validation" else train_indices).extend(indices)
        class_counts[group_labels[group]][split] += len(indices)
    return GroupedSplit(
        assignments=dict(sorted(assignments.items())),
        train_indices=sorted(train_indices),
        validation_indices=sorted(validation_indices),
        class_counts={label: counts for label, counts in sorted(class_counts.items())},
    )


class SourceGroupedSampler:
    """Yield row indices group-by-group without changing group membership."""

    def __init__(self, rows: list[ManifestRow], indices: list[int], *, seed: int = 0, shuffle: bool = True):
        groups: dict[GroupKey, list[int]] = defaultdict(list)
        for index in indices:
            row = rows[index]
            groups[(row.source_dataset, row.source_video_id)].append(index)
        self._groups = [(group, sorted(values)) for group, values in sorted(groups.items())]
        self._seed = seed
        self._shuffle = shuffle

    def __iter__(self):
        groups = list(self._groups)
        if self._shuffle:
            random.Random(self._seed).shuffle(groups)
        for _, indices in groups:
            yield from indices

    def __len__(self) -> int:
        return sum(len(indices) for _, indices in self._groups)
