"""Standard-library validation for the P0A data contracts."""

from __future__ import annotations

import json
import re
from pathlib import Path, PurePosixPath
from typing import Any


MANIFEST_FIELDS = [
    "filepath",
    "source_dataset",
    "source_video_id",
    "source_frame_index",
    "label",
    "label_scope",
    "label_source",
    "annotation_version",
    "inside_official_interval",
    "split",
    "file_digest",
]

LABEL_SCOPES = {
    "video_inherited",
    "temporal_interval",
    "box",
    "instance_mask",
    "atomic_action",
    "teacher_roi",
}
SPLITS = {"train", "validation", "test"}
ROLES = {"core", "conditional", "optional", "watch"}
COMPONENT_TYPES = {"media", "annotations"}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def validate_manifest_schema(schema: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if schema.get("x-column-order") != MANIFEST_FIELDS:
        issues.append("manifest x-column-order does not match the frozen eleven fields")
    if schema.get("required") != MANIFEST_FIELDS:
        issues.append("manifest required fields do not match the frozen eleven fields")
    if set(schema.get("properties", {})) != set(MANIFEST_FIELDS):
        issues.append("manifest properties contain missing or unexpected fields")
    if schema.get("additionalProperties") is not False:
        issues.append("manifest schema must reject additional properties")
    return issues


def validate_manifest_row(row: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if list(row) != MANIFEST_FIELDS:
        issues.append("row fields/order do not match the frozen manifest contract")

    path_value = row.get("filepath")
    if not isinstance(path_value, str) or not path_value:
        issues.append("filepath must be a non-empty relative POSIX path")
    else:
        pure = PurePosixPath(path_value)
        if pure.is_absolute() or ".." in pure.parts or "\\" in path_value:
            issues.append("filepath must not be absolute, traverse parents, or use backslashes")

    for field in ("source_dataset", "source_video_id", "label", "label_source", "annotation_version"):
        if not isinstance(row.get(field), str) or not row[field]:
            issues.append(f"{field} must be a non-empty string")

    frame_index = row.get("source_frame_index")
    if frame_index is not None and (
        isinstance(frame_index, bool) or not isinstance(frame_index, int) or frame_index < 0
    ):
        issues.append("source_frame_index must be null or a non-negative integer")
    if row.get("label_scope") not in LABEL_SCOPES:
        issues.append("label_scope is not registered")
    if row.get("label_scope") == "teacher_roi" and row.get("label_source") != "teacher":
        issues.append("teacher_roi rows must use label_source=teacher")
    interval = row.get("inside_official_interval")
    if interval is not None and not isinstance(interval, bool):
        issues.append("inside_official_interval must be boolean or null")
    if row.get("split") not in SPLITS:
        issues.append("split is not registered")
    digest = row.get("file_digest")
    if not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
        issues.append("file_digest must be a lowercase SHA-256")
    return issues


def validate_task_contract(contract: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    expected_labels = {
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
    primary = contract.get("primary_task", {})
    if set(primary.get("canonical_labels", [])) != expected_labels:
        issues.append("canonical UCF label set is not the frozen fourteen-label ontology")
    if primary.get("folder_label_map", {}).get("NormalVideos") != "Normal":
        issues.append("NormalVideos must map to canonical label Normal")
    manifest = contract.get("manifest_contract", {})
    if manifest.get("columns_in_order") != MANIFEST_FIELDS:
        issues.append("task contract manifest columns do not match the frozen order")
    if contract.get("split_contract", {}).get("allowed_manifest_values") != ["train", "validation", "test"]:
        issues.append("split vocabulary is not frozen")
    teacher = contract.get("teacher_boundary", {})
    if teacher.get("label_scope") != "teacher_roi" or teacher.get("label_source") != "teacher":
        issues.append("teacher provenance boundary is inconsistent")
    if teacher.get("evaluation_ground_truth") is not False:
        issues.append("teacher outputs must not be evaluation ground truth")
    return issues


def validate_access_registry(registry: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    datasets = registry.get("datasets")
    if not isinstance(datasets, list) or not datasets:
        return ["access registry must contain datasets"]

    required_dataset_ids = {
        "ucf_crime_kaggle_frames",
        "ucf_crime_official",
        "ucf_crime2local",
        "cuhk_avenue",
        "coco_2017",
        "ava_v2_2",
        "cuva",
        "xd_violence",
        "msad",
        "rareanom",
        "valu",
        "fs_ucf_crime",
        "hivau_70k",
        "pistachio",
    }
    seen_dataset_ids: set[str] = set()
    seen_component_ids: set[str] = set()
    component_fields = {
        "component_id",
        "component_type",
        "role",
        "local_root",
        "access_status",
        "source_url",
        "terms_url",
        "license_name",
        "license_version",
        "license_evidence_digest",
        "access_or_acceptance_date",
        "accepted_by",
        "redistribution_status",
        "derived_artifact_restrictions",
        "citation_requirements",
        "gate_status",
        "blocker_id",
        "notes",
    }

    for dataset in datasets:
        if not isinstance(dataset, dict):
            issues.append("each dataset record must be an object")
            continue
        dataset_id = dataset.get("dataset_id")
        if not isinstance(dataset_id, str) or not dataset_id:
            issues.append("dataset_id must be non-empty")
            continue
        if dataset_id in seen_dataset_ids:
            issues.append(f"duplicate dataset_id: {dataset_id}")
        seen_dataset_ids.add(dataset_id)
        components = dataset.get("components", [])
        if not isinstance(components, list):
            issues.append(f"{dataset_id} components must be a list")
            continue
        if any(not isinstance(component, dict) for component in components):
            issues.append(f"{dataset_id} components must contain only objects")
            continue
        types = {component.get("component_type") for component in components}
        if types != COMPONENT_TYPES:
            issues.append(f"{dataset_id} must keep separate media and annotation records")
        for component in components:
            missing = component_fields - set(component)
            component_id = component.get("component_id")
            if missing:
                issues.append(f"{dataset_id}/{component_id} missing fields: {sorted(missing)}")
            if not isinstance(component_id, str) or not component_id:
                issues.append(f"{dataset_id} component_id must be a non-empty string")
            elif component_id in seen_component_ids:
                issues.append(f"duplicate component_id: {component_id}")
            else:
                seen_component_ids.add(component_id)
            if component.get("component_type") not in COMPONENT_TYPES:
                issues.append(f"{dataset_id}/{component_id} has invalid component_type")
            if component.get("role") not in ROLES:
                issues.append(f"{dataset_id}/{component_id} has invalid role")
            if not component.get("gate_status"):
                issues.append(f"{dataset_id}/{component_id} has no gate_status")
            license_name = component.get("license_name")
            gate = component.get("gate_status", "")
            if license_name in {"unknown", "unverified", "unverified academic dataset terms"} and gate in {
                "eligible",
                "release_allowed",
            }:
                issues.append(f"{dataset_id}/{component_id} is usable despite unverified terms")

    missing_datasets = required_dataset_ids - seen_dataset_ids
    if missing_datasets:
        issues.append(f"registry is missing planned/watch datasets: {sorted(missing_datasets)}")

    official = next(
        (
            item
            for item in datasets
            if isinstance(item, dict) and item.get("dataset_id") == "ucf_crime_official"
        ),
        None,
    )
    if official:
        components = official.get("components")
        if not isinstance(components, list) or any(not isinstance(component, dict) for component in components):
            return issues
        roles = {
            component.get("component_type"): component.get("role") for component in components
        }
        if roles != {"media": "conditional", "annotations": "core"}:
            issues.append("official UCF media must be conditional while temporal annotations are core")
    return issues
