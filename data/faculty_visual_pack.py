"""Deterministic, local-only faculty visual-progress pack rendering.

This module is deliberately separate from experiment code.  It renders a
predeclared set of licensed UCF frame derivatives for a faculty update, with
full provenance and no performance claim.  Its explicit fixture settings must
not be used as a P2A experiment convention or to resolve B-007.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import csv
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

import cv2
import numpy as np
import yaml
from PIL import Image, ImageDraw, ImageFont

from data.degradations import SampleKey, apply_degradation, gaussian_spec
from data.ucf_intervals import (
    OfficialTemporalAnnotation,
    parse_official_temporal_annotations,
)
from models.restoration import restore_image


RENDERER_VERSION = "faculty-progress-v1"
_REQUIRED_SCOPE_ASSERTIONS = {
    "training_performed": False,
    "learned_model_rendered": False,
    "metric_or_benefit_claim_made": False,
    "pixel_or_instance_mask_rendered": False,
    "raw_redistribution_authorized": False,
}
_BORDER_TYPES = {
    "reflect": cv2.BORDER_REFLECT,
    "reflect_101": cv2.BORDER_REFLECT_101,
    "replicate": cv2.BORDER_REPLICATE,
}


@dataclass(frozen=True)
class FacultyExample:
    identifier: str
    video_relative_path: str
    label: str
    source_video_id: str
    frame_index: int
    interval: tuple[int, int]


def render_faculty_visual_pack(
    repo_root: Path,
    config_path: Path,
) -> Path:
    """Render one immutable, local-only visual-progress pack from YAML config."""

    repo_root = repo_root.resolve()
    config_path = config_path.resolve()
    config = _load_config(config_path)
    _validate_scope_assertions(config)
    video_root = _relative_existing_directory(repo_root, config["video_root"], "video_root")
    annotation_path = _relative_existing_file(
        repo_root, config["official_annotation_text"], "official_annotation_text"
    )
    output_root = _safe_output_root(repo_root, config["output_root"])
    if output_root.exists():
        raise FileExistsError(f"faculty visual pack already exists: {output_root}")
    examples = _parse_examples(config["examples"])
    annotations = parse_official_temporal_annotations(annotation_path)
    display_width = _positive_integer(config["display_width"], "display_width")
    global_seed = _positive_integer(config["global_seed"], "global_seed")
    gaussian = _preview_gaussian_spec(config["preview_noise"])
    restoration = _preview_restoration(config["preview_restoration"])

    output_root.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=".faculty-preview-", dir=output_root.parent))
    try:
        stage_directories = {
            "original": temporary / "01_original",
            "gaussian_noise": temporary / "02_gaussian_noise",
            "median_restoration": temporary / "03_median_restoration",
            "bilateral_restoration": temporary / "04_bilateral_restoration",
            "temporal_annotation": temporary / "05_temporal_annotation",
        }
        for directory in stage_directories.values():
            directory.mkdir()

        examples_manifest: list[dict[str, Any]] = []
        contact_rows: list[list[Image.Image]] = []
        for ordinal, example in enumerate(examples, start=1):
            source_path = video_root / example.video_relative_path
            clean, source_resolution = _read_source_video_frame(source_path, example.frame_index)
            annotation = _validate_example(example, annotations)
            source_digest = _sha256(source_path)
            sample = SampleKey(
                f"{example.video_relative_path}#frame={example.frame_index}",
                source_digest,
                global_seed,
            )
            noisy = apply_degradation(clean, spec=gaussian, sample=sample)
            median = restore_image(
                noisy,
                method="median",
                parameters=restoration["median"],
                output_policy=restoration["output_policy"],
            )
            bilateral = restore_image(
                noisy,
                method="bilateral",
                parameters=restoration["bilateral"],
                output_policy=restoration["output_policy"],
            )

            prefix = f"{ordinal:02d}_{example.identifier}"
            cards = {
                "original": _captioned_card(
                    clean,
                    display_width,
                    "Original official-video still",
                    f"{source_resolution[0]}x{source_resolution[1]} source displayed larger; no recovered detail",
                ),
                "gaussian_noise": _captioned_card(
                    noisy,
                    display_width,
                    "Injected Gaussian noise",
                    "Display-only fixture: sigma 25/255; deterministic per source",
                ),
                "median_restoration": _captioned_card(
                    median,
                    display_width,
                    "Median restoration",
                    "Classical display algorithm on the same injected noise",
                ),
                "bilateral_restoration": _captioned_card(
                    bilateral,
                    display_width,
                    "Bilateral restoration",
                    "Classical display algorithm on the same injected noise",
                ),
                "temporal_annotation": _temporal_annotation_card(
                    clean,
                    display_width,
                    label=example.label,
                    source_video_id=example.source_video_id,
                    frame_index=example.frame_index,
                    interval=example.interval,
                ),
            }
            rendered_files: dict[str, str] = {}
            rendered_digests: dict[str, str] = {}
            for stage, card in cards.items():
                relative_output = Path(stage_directories[stage].name) / f"{prefix}.png"
                destination = temporary / relative_output
                card.save(destination, format="PNG", optimize=False)
                rendered_files[stage] = relative_output.as_posix()
                rendered_digests[stage] = _sha256(destination)
            contact_rows.append([cards[key] for key in stage_directories])
            examples_manifest.append(
                {
                    "id": example.identifier,
                    "source_video_relative_path": example.video_relative_path,
                    "source_video_sha256": source_digest,
                    "source_frame_resolution": list(source_resolution),
                    "label": example.label,
                    "source_video_id": example.source_video_id,
                    "frame_index": example.frame_index,
                    "official_interval": list(example.interval),
                    "inside_official_interval": annotation.contains(example.frame_index),
                    "rendered_files": rendered_files,
                    "rendered_sha256": rendered_digests,
                }
            )

        contact_sheet = _contact_sheet(contact_rows)
        contact_path = temporary / "faculty_progress_contact_sheet.png"
        contact_sheet.save(contact_path, format="PNG", optimize=False)
        manifest = {
            "schema_version": "1.0.0",
            "kind": "faculty visual-progress preview; not a training, evaluation, or research result",
            "renderer_version": RENDERER_VERSION,
            "decision": config["decision"],
            "run_class": config["run_class"],
            "config_path": config_path.relative_to(repo_root).as_posix(),
            "config_sha256": _sha256(config_path),
            "annotation_path": annotation_path.relative_to(repo_root).as_posix(),
            "annotation_sha256": _sha256(annotation_path),
            "preview_noise": _canonical_mapping(config["preview_noise"]),
            "preview_restoration": _canonical_mapping(config["preview_restoration"]),
            "scope_assertions": config["scope_assertions"],
            "contact_sheet": {
                "path": contact_path.name,
                "sha256": _sha256(contact_path),
            },
            "examples": examples_manifest,
            "limitations": [
                "The source is a 320x240 local official-video still; display enlargement does not recover detail.",
                "Noise and restoration settings are presentation-only fixtures, not experiment conventions.",
                "No learned model, training output, metric, or benefit claim is rendered.",
                "The UCF annotation is temporal provenance, not a pixel or instance mask.",
                "Rendered source-frame derivatives are local-only and must not be committed or publicly redistributed.",
            ],
        }
        _write_json(temporary / "manifest.json", manifest)
        (temporary / "README.md").write_text(_local_readme(manifest), encoding="utf-8")
        os.replace(temporary, output_root)
        return output_root
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise


def render_p1b_membership_update(
    repo_root: Path,
    base_config_path: Path,
    p1b_run_directory: Path,
) -> Path:
    """Render the automatic D-25 P1B membership-preview update.

    It renders only the new provenance stage.  The initial pack remains
    immutable and is referenced by its own manifest.
    """

    repo_root = repo_root.resolve()
    config = _load_config(base_config_path.resolve())
    _validate_scope_assertions(config)
    run_directory = p1b_run_directory.resolve()
    report_path = run_directory / "view_report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if report.get("kind") != "P1B real UCF manifest and evaluation-view materialization; not model evaluation":
        raise ValueError("P1B membership preview requires the real materialization report")
    if report.get("scope_assertions", {}).get("model_training") is not False:
        raise ValueError("P1B membership preview refuses a model-training artifact")
    source_rows = _manifest_membership_keys(run_directory / "source_test_manifest.csv")
    event_rows = _manifest_membership_keys(run_directory / "event_only_test_manifest.csv")
    noisy_rows = _manifest_membership_keys(run_directory / "noisy_proxy_test_manifest.csv")
    video_root = _relative_existing_directory(repo_root, config["video_root"], "video_root")
    output = repo_root / "results/faculty_progress/ucf-temporal-preview-v2-p1b"
    if output.exists():
        raise FileExistsError(f"P1B faculty visual update already exists: {output}")
    temporary = Path(tempfile.mkdtemp(prefix=".faculty-p1b-", dir=output.parent))
    try:
        stage = temporary / "06_p1b_membership"
        stage.mkdir()
        cards: list[list[Image.Image]] = []
        selections: list[dict[str, Any]] = []
        for ordinal, example in enumerate(_parse_examples(config["examples"]), start=1):
            key = (example.source_video_id, example.frame_index)
            if key not in source_rows or key not in noisy_rows or key not in event_rows:
                raise ValueError(f"P1B manifests do not contain the selected event example: {key}")
            clean, resolution = _read_source_video_frame(
                video_root / example.video_relative_path, example.frame_index
            )
            card = _p1b_membership_card(clean, int(config["display_width"]), example, resolution)
            filename = f"{ordinal:02d}_{example.identifier}.png"
            card.save(stage / filename, format="PNG", optimize=False)
            cards.append([card])
            selections.append(
                {
                    "id": example.identifier,
                    "source_video_id": example.source_video_id,
                    "frame_index": example.frame_index,
                    "event_only_member": True,
                    "noisy_proxy_member": True,
                    "rendered_file": f"06_p1b_membership/{filename}",
                    "rendered_sha256": _sha256(stage / filename),
                }
            )
        sheet = _contact_sheet(cards)
        sheet_path = temporary / "p1b_membership_contact_sheet.png"
        sheet.save(sheet_path, format="PNG", optimize=False)
        manifest = {
            "schema_version": "1.0.0",
            "kind": "faculty P1B membership visual update; not model evaluation or research evidence",
            "renderer_version": RENDERER_VERSION,
            "parent_pack": "results/faculty_progress/ucf-temporal-preview-v1",
            "p1b_run_directory": run_directory.relative_to(repo_root).as_posix(),
            "p1b_view_report_sha256": _sha256(report_path),
            "view_digests": report["output_manifest_sha256"],
            "scope_assertions": report["scope_assertions"],
            "examples": selections,
            "contact_sheet": {"path": sheet_path.name, "sha256": _sha256(sheet_path)},
        }
        _write_json(temporary / "manifest.json", manifest)
        (temporary / "README.md").write_text(
            "# Local P1B faculty membership update\n\n"
            "All three fixed examples are members of both the real event-only and noisy-proxy P1B views. "
            "This is membership provenance only, not a model prediction or evaluation result.\n",
            encoding="utf-8",
        )
        os.replace(temporary, output)
        return output
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise


def _load_config(config_path: Path) -> dict[str, Any]:
    if not config_path.is_file():
        raise FileNotFoundError(f"faculty visual-pack config is missing: {config_path}")
    loaded = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError("faculty visual-pack config must be a mapping")
    required = {
        "schema_version",
        "kind",
        "decision",
        "run_class",
        "status",
        "video_root",
        "official_annotation_text",
        "output_root",
        "display_width",
        "global_seed",
        "scope_assertions",
        "examples",
        "preview_noise",
        "preview_restoration",
    }
    missing = sorted(required - set(loaded))
    if missing:
        raise ValueError(f"faculty visual-pack config missing keys: {missing}")
    if loaded["schema_version"] != "1.0.0" or loaded["kind"] != "faculty_progress_visual_pack":
        raise ValueError("unsupported faculty visual-pack schema or kind")
    if loaded["decision"] != "D-25" or loaded["run_class"] != "faculty_preview":
        raise ValueError("faculty visual pack must be governed by D-25/faculty_preview")
    if loaded["status"] != "PRESENTATION_ONLY_NOT_RESEARCH_EVIDENCE":
        raise ValueError("faculty visual pack must retain its presentation-only status")
    return loaded


def _validate_scope_assertions(config: Mapping[str, Any]) -> None:
    assertions = config["scope_assertions"]
    if assertions != _REQUIRED_SCOPE_ASSERTIONS:
        raise ValueError("faculty visual-pack scope assertions must retain every no-claim boundary")


def _relative_existing_directory(repo_root: Path, raw: Any, name: str) -> Path:
    path = _relative_path(repo_root, raw, name)
    if not path.is_dir():
        raise FileNotFoundError(f"{name} is not a directory: {path}")
    return path


def _relative_existing_file(repo_root: Path, raw: Any, name: str) -> Path:
    path = _relative_path(repo_root, raw, name)
    if not path.is_file():
        raise FileNotFoundError(f"{name} is not a file: {path}")
    return path


def _relative_path(repo_root: Path, raw: Any, name: str) -> Path:
    if not isinstance(raw, str) or not raw:
        raise ValueError(f"{name} must be a non-empty relative path")
    pure = PurePosixPath(raw)
    if pure.is_absolute() or ".." in pure.parts:
        raise ValueError(f"{name} must stay within the repository")
    return repo_root / Path(pure)


def _safe_output_root(repo_root: Path, raw: Any) -> Path:
    output = _relative_path(repo_root, raw, "output_root")
    required_parent = repo_root / "results" / "faculty_progress"
    if output.parent != required_parent:
        raise ValueError("output_root must be an immediate child of results/faculty_progress")
    return output


def _parse_examples(raw_examples: Any) -> tuple[FacultyExample, ...]:
    if not isinstance(raw_examples, list) or len(raw_examples) != 3:
        raise ValueError("faculty visual pack requires exactly three predeclared examples")
    examples: list[FacultyExample] = []
    seen_ids: set[str] = set()
    seen_paths: set[str] = set()
    for raw in raw_examples:
        if not isinstance(raw, Mapping):
            raise ValueError("each faculty example must be a mapping")
        expected = {
            "id",
            "video_relative_path",
            "expected_label",
            "expected_source_video_id",
            "expected_frame_index",
            "expected_interval",
        }
        if set(raw) != expected:
            raise ValueError(f"faculty example keys must be exactly {sorted(expected)}")
        identifier = _identifier(raw["id"])
        video_relative_path = _canonical_video_path(raw["video_relative_path"])
        label = _non_empty_string(raw["expected_label"], "expected_label")
        source_video_id = _non_empty_string(raw["expected_source_video_id"], "expected_source_video_id")
        frame_index = _nonnegative_integer(raw["expected_frame_index"], "expected_frame_index")
        interval_raw = raw["expected_interval"]
        if (
            not isinstance(interval_raw, list)
            or len(interval_raw) != 2
            or any(isinstance(value, bool) or not isinstance(value, int) for value in interval_raw)
            or interval_raw[0] < 0
            or interval_raw[1] < interval_raw[0]
        ):
            raise ValueError("expected_interval must be a two-integer inclusive interval")
        if identifier in seen_ids or video_relative_path in seen_paths:
            raise ValueError("faculty examples must have unique IDs and paths")
        seen_ids.add(identifier)
        seen_paths.add(video_relative_path)
        examples.append(
            FacultyExample(identifier, video_relative_path, label, source_video_id, frame_index, tuple(interval_raw))
        )
    return tuple(examples)


def _validate_example(
    example: FacultyExample, annotations: Mapping[str, OfficialTemporalAnnotation]
) -> OfficialTemporalAnnotation:
    expected_video_path = f"Videos/{example.label}/{example.source_video_id}.mp4"
    if example.video_relative_path != expected_video_path:
        raise ValueError(f"{example.identifier} configuration does not match the canonical source video path")
    annotation = annotations.get(example.source_video_id)
    if annotation is None or annotation.label != example.label:
        raise ValueError(f"{example.identifier} has no matching official temporal annotation")
    if not any(
        (official_interval.start, official_interval.end) == example.interval
        for official_interval in annotation.intervals
    ):
        raise ValueError(f"{example.identifier} expected interval is not in the official annotation")
    if not annotation.contains(example.frame_index):
        raise ValueError(f"{example.identifier} is outside its official temporal interval")
    return annotation


def _preview_gaussian_spec(raw: Any):
    if not isinstance(raw, Mapping) or set(raw) != {
        "family", "sigma_8bit", "mean_8bit", "sampling_unit", "clipping"
    }:
        raise ValueError("preview_noise must contain exactly the explicit Gaussian fixture fields")
    if raw["family"] != "gaussian":
        raise ValueError("faculty preview currently supports only explicit Gaussian noise")
    return gaussian_spec(
        sigma_8bit=float(raw["sigma_8bit"]),
        mean_8bit=float(raw["mean_8bit"]),
        sampling_unit=str(raw["sampling_unit"]),
        clipping=str(raw["clipping"]),
    )


def _preview_restoration(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, Mapping) or set(raw) != {"output_policy", "median", "bilateral"}:
        raise ValueError("preview_restoration must contain output_policy, median, and bilateral")
    median = raw["median"]
    bilateral = raw["bilateral"]
    if not isinstance(median, Mapping) or set(median) != {"kernel_size", "border_policy"}:
        raise ValueError("preview median parameters are incomplete")
    if not isinstance(bilateral, Mapping) or set(bilateral) != {
        "diameter", "sigma_color", "sigma_space", "border_type"
    }:
        raise ValueError("preview bilateral parameters are incomplete")
    border_name = bilateral["border_type"]
    if border_name not in _BORDER_TYPES:
        raise ValueError(f"unsupported preview border_type: {border_name}")
    return {
        "output_policy": str(raw["output_policy"]),
        "median": dict(median),
        "bilateral": {
            "diameter": bilateral["diameter"],
            "sigma_color": bilateral["sigma_color"],
            "sigma_space": bilateral["sigma_space"],
            "border_type": _BORDER_TYPES[str(border_name)],
        },
    }


def _read_source_video_frame(path: Path, frame_index: int) -> tuple[np.ndarray, tuple[int, int]]:
    if not path.is_file():
        raise FileNotFoundError(f"configured faculty source video is missing: {path}")
    capture = cv2.VideoCapture(str(path))
    try:
        if not capture.isOpened():
            raise RuntimeError(f"OpenCV cannot open configured faculty source video: {path}")
        frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        if frame_index >= frame_count:
            raise ValueError(
                f"configured frame index {frame_index} exceeds {path.name} frame count {frame_count}"
            )
        capture.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
        ok, bgr = capture.read()
    finally:
        capture.release()
    if not ok or bgr is None:
        raise RuntimeError(f"OpenCV could not read frame {frame_index} from {path}")
    if bgr.ndim != 3 or bgr.shape[2] != 3:
        raise ValueError(f"configured faculty source is not a three-channel video frame: {path}")
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    pixels = np.ascontiguousarray(rgb.astype(np.float32) / np.float32(255.0))
    return pixels, (int(pixels.shape[1]), int(pixels.shape[0]))


def _captioned_card(image: np.ndarray, display_width: int, title: str, subtitle: str) -> Image.Image:
    rendered = _scaled_image(image, display_width)
    footer_height = 82
    card = Image.new("RGB", (rendered.width, rendered.height + footer_height), "white")
    card.paste(rendered, (0, 0))
    draw = ImageDraw.Draw(card)
    font = ImageFont.load_default()
    draw.text((12, rendered.height + 10), title, fill="black", font=font)
    draw.multiline_text((12, rendered.height + 34), subtitle, fill="#404040", font=font, spacing=3)
    return card


def _temporal_annotation_card(
    image: np.ndarray,
    display_width: int,
    *,
    label: str,
    source_video_id: str,
    frame_index: int,
    interval: tuple[int, int],
) -> Image.Image:
    rendered = _scaled_image(image, display_width)
    draw = ImageDraw.Draw(rendered)
    draw.rectangle((3, 3, rendered.width - 4, rendered.height - 4), outline="#b91c1c", width=6)
    footer_height = 98
    card = Image.new("RGB", (rendered.width, rendered.height + footer_height), "white")
    card.paste(rendered, (0, 0))
    text = ImageDraw.Draw(card)
    font = ImageFont.load_default()
    text.text((12, rendered.height + 10), "Official temporal annotation", fill="#7f1d1d", font=font)
    text.text(
        (12, rendered.height + 34),
        f"{label} · {source_video_id} · frame {frame_index} inside [{interval[0]}, {interval[1]}]",
        fill="black",
        font=font,
    )
    text.text(
        (12, rendered.height + 58),
        "Temporal provenance only — no pixel/instance mask is available or claimed.",
        fill="#404040",
        font=font,
    )
    return card


def _scaled_image(image: np.ndarray, display_width: int) -> Image.Image:
    source = np.rint(np.clip(image, 0.0, 1.0) * np.float32(255.0)).astype(np.uint8)
    rendered = Image.fromarray(source, mode="RGB")
    if rendered.width >= display_width:
        return rendered
    height = round(rendered.height * display_width / rendered.width)
    return rendered.resize((display_width, height), Image.Resampling.LANCZOS)


def _contact_sheet(rows: list[list[Image.Image]]) -> Image.Image:
    if not rows or not rows[0] or any(len(row) != len(rows[0]) for row in rows):
        raise ValueError("contact sheet requires non-empty rows with a consistent stage count")
    thumbnail_width = 360
    thumbnails = [
        [
            card.resize(
                (thumbnail_width, round(card.height * thumbnail_width / card.width)),
                Image.Resampling.LANCZOS,
            )
            for card in row
        ]
        for row in rows
    ]
    width = max(card.width for row in thumbnails for card in row)
    height = max(card.height for row in thumbnails for card in row)
    padding = 16
    sheet = Image.new(
        "RGB",
        (padding + len(thumbnails[0]) * (width + padding), padding + len(thumbnails) * (height + padding)),
        "#e5e7eb",
    )
    for row_index, row in enumerate(thumbnails):
        for column_index, card in enumerate(row):
            x = padding + column_index * (width + padding)
            y = padding + row_index * (height + padding)
            sheet.paste(card, (x, y))
    return sheet


def _manifest_membership_keys(path: Path) -> set[tuple[str, int]]:
    keys: set[tuple[str, int]] = set()
    with path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            keys.add((row["source_video_id"], int(row["source_frame_index"])))
    return keys


def _p1b_membership_card(
    image: np.ndarray,
    display_width: int,
    example: FacultyExample,
    resolution: tuple[int, int],
) -> Image.Image:
    rendered = _scaled_image(image, display_width)
    draw = ImageDraw.Draw(rendered)
    draw.rectangle((3, 3, rendered.width - 4, rendered.height - 4), outline="#15803d", width=6)
    card = Image.new("RGB", (rendered.width, rendered.height + 98), "white")
    card.paste(rendered, (0, 0))
    text = ImageDraw.Draw(card)
    font = ImageFont.load_default()
    text.text((12, rendered.height + 10), "P1B real-view membership verified", fill="#166534", font=font)
    text.text((12, rendered.height + 34), f"{example.source_video_id} · frame {example.frame_index} · {resolution[0]}x{resolution[1]}", fill="black", font=font)
    text.text((12, rendered.height + 58), "Included in both event-only and noisy-proxy views; not a prediction.", fill="#404040", font=font)
    return card


def _local_readme(manifest: Mapping[str, Any]) -> str:
    return "\n".join(
        [
            "# Local faculty visual-progress preview",
            "",
            "This directory contains licensed source-frame derivatives for a faculty update.",
            "It is presentation-only, not a training/evaluation/research result.",
            "Do not commit, publicly redistribute, or call the temporal overlay a mask.",
            "",
            f"Renderer: {manifest['renderer_version']}",
            f"Official annotation SHA-256: {manifest['annotation_sha256']}",
            f"Examples: {len(manifest['examples'])}",
            "",
            "See docs/FACULTY_PROGRESS_VISUAL_PACK.md for faculty and paper-use rules.",
            "",
        ]
    )


def _canonical_mapping(raw: Mapping[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(raw, sort_keys=True))


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _identifier(value: Any) -> str:
    result = _non_empty_string(value, "id")
    if not result.replace("_", "").isalnum() or not result.isascii():
        raise ValueError("faculty example id must be ASCII alphanumeric with underscores")
    return result


def _canonical_video_path(value: Any) -> str:
    result = _non_empty_string(value, "video_relative_path")
    pure = PurePosixPath(result)
    if pure.is_absolute() or ".." in pure.parts or pure.as_posix() != result:
        raise ValueError("faculty source-video path must be a canonical relative POSIX path")
    if pure.suffix != ".mp4":
        raise ValueError("faculty source-video path must end in .mp4")
    return result


def _non_empty_string(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{name} must be a non-empty string")
    return value


def _positive_integer(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _nonnegative_integer(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")
    return value
