"""Task-local multiclass metrics and source-video cluster bootstrap."""

from __future__ import annotations

from collections import defaultdict
from typing import Sequence

import numpy as np


def confusion_matrix(y_true: Sequence[str], y_pred: Sequence[str], labels: Sequence[str]) -> np.ndarray:
    if len(y_true) != len(y_pred) or not y_true:
        raise ValueError("y_true and y_pred must be non-empty and have equal length")
    if len(set(labels)) != len(labels) or not labels:
        raise ValueError("labels must be non-empty and unique")
    index = {label: position for position, label in enumerate(labels)}
    matrix = np.zeros((len(labels), len(labels)), dtype=np.int64)
    for truth, prediction in zip(y_true, y_pred, strict=True):
        if truth not in index or prediction not in index:
            raise ValueError(f"unregistered label in metric inputs: truth={truth}, prediction={prediction}")
        matrix[index[truth], index[prediction]] += 1
    return matrix


def classification_metrics(y_true: Sequence[str], y_pred: Sequence[str], labels: Sequence[str]) -> dict:
    matrix = confusion_matrix(y_true, y_pred, labels)
    per_class: dict[str, dict[str, float | int]] = {}
    for position, label in enumerate(labels):
        true_positive = int(matrix[position, position])
        false_positive = int(matrix[:, position].sum() - true_positive)
        false_negative = int(matrix[position, :].sum() - true_positive)
        support = int(matrix[position, :].sum())
        precision = true_positive / (true_positive + false_positive) if true_positive + false_positive else 0.0
        recall = true_positive / (true_positive + false_negative) if true_positive + false_negative else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_class[label] = {"precision": precision, "recall": recall, "f1": f1, "support": support}
    return {
        "accuracy": float(np.trace(matrix) / matrix.sum()),
        "macro_precision": float(np.mean([values["precision"] for values in per_class.values()])),
        "macro_recall": float(np.mean([values["recall"] for values in per_class.values()])),
        "macro_f1": float(np.mean([values["f1"] for values in per_class.values()])),
        "per_class": per_class,
        "confusion_matrix": matrix.tolist(),
        "labels": list(labels),
    }


def video_clustered_macro_f1_ci(
    y_true: Sequence[str],
    y_pred: Sequence[str],
    source_video_ids: Sequence[str],
    labels: Sequence[str],
    *,
    iterations: int = 1000,
    seed: int = 0,
) -> dict:
    if not (len(y_true) == len(y_pred) == len(source_video_ids)):
        raise ValueError("truth, prediction, and source_video_ids must have equal length")
    if iterations < 100:
        raise ValueError("cluster bootstrap requires at least 100 iterations")
    clusters: dict[str, list[int]] = defaultdict(list)
    for index, video_id in enumerate(source_video_ids):
        clusters[video_id].append(index)
    cluster_ids = sorted(clusters)
    if len(cluster_ids) < 2:
        raise ValueError("cluster bootstrap requires at least two source videos")
    generator = np.random.Generator(np.random.PCG64(seed))
    values: list[float] = []
    for _ in range(iterations):
        sampled = generator.choice(cluster_ids, size=len(cluster_ids), replace=True)
        indices = [index for cluster in sampled for index in clusters[str(cluster)]]
        truth = [y_true[index] for index in indices]
        prediction = [y_pred[index] for index in indices]
        values.append(classification_metrics(truth, prediction, labels)["macro_f1"])
    return {
        "estimate": classification_metrics(y_true, y_pred, labels)["macro_f1"],
        "lower_95": float(np.percentile(values, 2.5)),
        "upper_95": float(np.percentile(values, 97.5)),
        "iterations": iterations,
        "seed": seed,
        "cluster_count": len(cluster_ids),
        "resampling_unit": "source_video_id",
    }
