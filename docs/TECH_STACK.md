# Technical stack — SHAR

> v3.0 · 2026-07-20 · Choices are provisional until Phase 0 freezes exact versions and checkpoints.

## Core future stack

| Layer | Planned choice | Constraint |
|---|---|---|
| Language/runtime | Python 3.10+ | Freeze exact patch version and environment lockfile before the first run. |
| Deep learning | PyTorch with Apple MPS on the primary Mac | Pin PyTorch/macOS versions; verify device placement and record unsupported-operation CPU fallbacks. CUDA is an optional parity environment, not the local default. |
| Backbone/classification | torchvision ResNet50 plus project heads | Record exact weight enum/checksum; use pre-GAP C5 for spatial heads. |
| Temporal baseline | one reproducible CNN-LSTM/temporal model | Must consume source-grouped clips, not randomly mixed frames. |
| ROI proposals | exact Ultralytics YOLO11 checkpoint | Preprocessing only in core scope; record package version, commit, YAML, checkpoint digest, threshold, and NMS. |
| Classical vision | OpenCV + scikit-image | Filters, degradations, PSNR, SSIM; freeze color/range conventions. |
| Restoration comparator | one official pretrained NAFNet or newer justified model | Pin official repository commit, checkpoint, training domain, and license. “SOTA” is not a permanent label. |
| Metrics | scikit-learn, torchmetrics, dataset-native evaluators | Validate against small hand-calculated fixtures; cluster uncertainty by video. |
| Explainability | pinned Grad-CAM implementation | Qualitative artifact only. |
| Configuration | YAML plus immutable manifest/config digests | Every result row must be reconstructable. |
| Tracking | Immutable CSV/JSON/JSONL artifacts plus concise `TRAINING_LOG.md`; optional W&B | Machine artifacts are authoritative; the Markdown ledger is an index; external service is optional. |

## Core project modules after the audit

1. Dataset/provenance manifests and official-interval mapper.
2. Stable noise/degradation generator using SHA-256-derived seeds.
3. Pluggable denoiser interface and denoising-VAE/ESVDAE research variants.
4. Stock-detector ROI generator with teacher provenance.
5. ResNet50 controls, temporal baseline, and SEMSCNN-inspired 2-D multiscale-SE head.
6. CE, weighted CE, focal, and Balanced Softmax controls.
7. Metric/provenance writers and video-clustered confidence intervals.
8. Run lifecycle, immutable artifact closure, live project status, and concise training ledger support.

No implementation file is created by this documentation pass.

## Deferred detector design dependencies

If the future detector appendix is promoted, use an editable, exact Ultralytics source checkout and follow the official custom-module integration path: module definition/exports, task parser import, channel handling, model YAML, and nonzero-FLOPs/model-info smoke test. Promotion also requires independent UCF-Crime2Local/COCO/AVA annotations.

YOLO26 is the preferred current official like-for-like comparison at the July 2026 research snapshot. YOLO12 uses the same high-level API but is community-driven; its segmentation setup lacks official pretrained weights and carries documented stability/resource cautions. Recheck both at implementation freeze.

## Hardware and storage assumptions

Primary hardware is a **MacBook Pro with Apple M5 Pro and 48 GB unified memory**. Use MPS-first execution and `COMPUTE_POLICY.md`. Unified memory is shared with the OS, so batch calibration must avoid swap and leave safe headroom; do not interpret 48 GB as dedicated VRAM. The local UCF mirror has 1,377,653 small images; generate training corruptions on the fly and cache only deterministic evaluation products. Original-resolution/external media storage depends on access terms and must not be assumed available.

## Intended repository layout

```text
SHAR/
  configs/             # frozen experiment specifications
  data/                # loaders, manifests, transforms; never raw licensed media
  models/              # future core heads/denoisers
  pipelines/           # future denoise, ROI, classify orchestration
  eval/                # metrics, confidence intervals, tables
  scripts/             # future entry points
  results/             # immutable run manifests, seed telemetry/summaries, aggregates, verdicts
  docs/                # authoritative specification, roadmap/control/status, concise training index
  papers/              # local PDFs; currently no JSON extractions
```
