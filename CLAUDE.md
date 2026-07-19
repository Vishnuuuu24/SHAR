# CLAUDE.md — SHAR persistent project instructions

> Project: Suspicious Human Activity Recognition (SHAR)
>
> Owners: Priyodip, Likith, Vishnu, Abijith
>
> Updated: 2026-07-19
>
> Status: research specification complete; implementation has not started.

## Start every session here

1. Read `docs/00_README.md`, then `docs/AGENTS.md`.
2. Use the authority order in `docs/00_README.md`; consult `docs/DECISIONS.md` and `docs/EVIDENCE_REGISTER.md` before repeating or changing a research claim.
3. Check the current repository state and relevant files. Do not assume an older chat, the historical Word plan, or this file is newer than the audited documents.
4. Do not implement models until the Phase 0 data, provenance, access/license, and compute-readiness gates in `docs/PHASE_PLAN.md` are green.

The Markdown documents under `docs/` are the current, decision-complete research specification. `SHAR_Research_Plan.docx` and the original proposal terminology are preserved historical inputs, not current implementation authority. If this file conflicts with a higher-authority research document, stop, resolve the conflict, and update both the decision and evidence registers.

## Project purpose

This is a semester-7 student computer-vision research project. Explain unfamiliar methods clearly and prefer reproducible evidence over impressive terminology.

The faculty framing remains:

- **RESULT 1 — denoising:** compare classical filters, a reproducible denoising-VAE/justified ESVDAE variant, and a pinned modern restoration baseline using PSNR, SSIM, and downstream classification change.
- **RESULT 2 — classification:** classify the 13 UCF-Crime anomaly labels plus Normal and report macro/per-class metrics under the registered event-aware protocol.
- **ROI study:** compare full-frame inputs with deterministic stock-detector ROIs. This is preprocessing evidence, not permission to claim detector mAP.

## Non-negotiable research rules

1. **Label honesty:** UCF Kaggle anomaly folders contain frames inheriting a source-video label. They are weak/noisy supervision, not event-level frame ground truth.
2. **Headline evaluation:** use the official-interval-derived event-only UCF test view. Keep the full-directory inherited-label score only as a separately named noisy-proxy sensitivity analysis. Official intervals are useful but not clean or exhaustive.
3. **No circular evaluation:** model-generated boxes/masks may be ROI proposals or separately ablated auxiliary training signals, never evaluation ground truth for that teacher or its descendants.
4. **No manual-annotation dependency:** the core plan relies on existing annotations. Do not introduce a manual box/mask labeling gate without a new owner decision.
5. **Task separation:** never rank UCF 14-label accuracy/F1, temporal VAD AUC/AP, COCO mAP, AVA Frame-mAP, and UCF-Crime2Local localization as if they were the same metric or task.
6. **Source hierarchy:** direct measurement, primary paper, official code/annotations/model page, and explicit license terms outrank metadata, reviews, blogs, and Reddit. Reddit is an anecdotal failure-mode check—not proof, peer review, or a majority vote.
7. **Ablation discipline:** change one material factor per comparison, use the registered controls, run three seeds for headline results, report variability and video-clustered confidence intervals, and keep negative results.
8. **Claim gate:** a proposed component is not “beneficial,” “novel,” or “SOTA” until its mapped validation succeeds and the claim survives variance, compute-cost, task, and source checks.
9. **Reproducibility:** record config, code revision, data/annotation/checkpoint digests, package versions, seed, hardware, metrics, and artifact paths for every research run.
10. **Git boundary:** the previous commit/push authorization was one-time and is exhausted. Do not commit, push, force-push, create a PR, or change remotes; Git publishing belongs to the user.

## Current verified data facts

- Local Kaggle UCF mirror: 1,266,345 Train + 111,308 Test = 1,377,653 images.
- Verified image resolution: 64×64. Upscaling does not recover surveillance detail.
- UCF training supervision is video-level; official test temporal intervals enable the registered event-only evaluation.
- CUHK Avenue remains a binary anomaly dataset. Its anomaly masks are not SHAR instance-segmentation masks.
- UCF-Crime2Local, COCO, and AVA may provide independent localization/segmentation evaluation in their native task scopes.
- AVA, XD-Violence, MSAD, RareAnom, and any movie-derived data remain separate-domain experiments with their own ontology, metric, access, and license record. Never merge their labels into the UCF 14-label headline without genuine compatible annotations.

See `docs/DATA_SPEC.md` for manifest fields, splits, label provenance, external datasets, and metric separation.

## Proposal names and their audited status

| Historical proposal name | Current status |
|---|---|
| ESVDAE | The stacked/entropy-weighted concept is retained, but the entropy objective is not implementation-ready until its missing equations, constants, and source are registered. Start from a reproducible denoising-VAE control. |
| GKLYOLO11 | Custom MSDAM/ASFF/Gaussian/Slide detector training is deferred. Core work uses a pinned stock YOLO11 teacher for ROI proposals and evaluates downstream full-frame versus ROI macro-F1. |
| C2PSA-MSDAM at P3/P4 | Structurally incorrect as “replacement”: official YOLO11 has stock C2PSA at P5 after SPPF; P3/P4 use C3k2. Any future MSDAM work must be a separately approved insertion/replacement ablation with independent labels. |
| ASFFH Gaussian weighting | Removed from core. Standard ASFF is the future control; Gaussian gating was underspecified and has no evidence of benefit. |
| Slide Loss | Removed from core. It is not inherently a rare-class loss, local evidence is mixed/negative, and the YOLO-FaceV2 paper and upstream code disagree on the middle weight. |
| SEAMCNN | Retired name. Use **SEMSCNN-inspired 2-D multiscale-SE head**. It consumes a ResNet pre-GAP spatial feature map; never reshape a 2048-D GAP vector into an image. |
| YOLO12 as automatic successor | Rejected. YOLO11 remains the stock ROI teacher; YOLO26 is only an optional current official comparison if independently labeled detector work is revived. |

Full technical boundaries are in `docs/ARCHITECTURE.md`.

## Stale claims that must not re-enter the project

- “No published 14-class UCF-Crime recognition work exists.” Prior 14-category work exists; claim the exact provenance-aware protocol and controlled study instead.
- “Dwivedi 98.87 is confirmed 3-class.” The accessible primary source reviewed here does not establish that class count.
- “AVAD 94.94 AUC is a direct SHAR accuracy baseline.” AVAD is normal-only reconstruction VAD and uses a different metric/task.
- “DilateFormer proves YOLO P3/P4 placement.” It supports MSDA mechanics and shallow-stage evidence in its own architecture, not that mapping.
- “AF-YOLO invented ASFF.” It reuses standard ASFF.
- “The Ginseng/MS-YOLO recipe is the verified SHAR training recipe.” Paper recipes are dataset-specific priors and the previous synthesis conflated sources.
- “The exact Slide formula is settled.” Paper/code discrepancies are recorded in `docs/EVIDENCE_REGISTER.md`.
- “SEMSCNN is a directly copyable image model.” Its source semantics are EEG channel×time; the visual head is an explicit adaptation.
- “All reference papers were locally full-read into JSON.” The repository currently contains ten PDFs and zero paper-extraction JSON files.

## Compute and long-run policy

Primary machine: **MacBook Pro, Apple M5 Pro, 48 GB unified memory**.

- Follow `docs/COMPUTE_POLICY.md`; prefer verified PyTorch MPS placement and report CPU fallbacks.
- Use the full intended research data, capacity, resolution, epochs/early-stopping policy, and seeds. Do not silently downscale for speed.
- Smoke/calibration runs may prove correctness and measure throughput but are never research results.
- Before any run expected to exceed 30 minutes, report the measured throughput-based wall-time range, local completion window, storage, peak unified-memory range, and major uncertainties.
- Re-estimate after the first full epoch when actual pace differs by more than 20%.
- If the full protocol is infeasible locally or requires CUDA-only operations, stop and present the constraint and alternatives instead of changing the science.

## Working method

Before a change:

- identify the governing requirement, decision, evidence, and validation gate;
- inspect related documents/configuration instead of changing a single file in isolation;
- distinguish a direct source fact, project design decision, hypothesis, and future watch item.

During future implementation:

- preserve source-video grouping and label provenance end to end;
- never invent equations, thresholds, licenses, class mappings, or results;
- keep task-native metrics in separate artifacts;
- retain best validation checkpoints and resumable state;
- stop for owner input when access terms, scientific scope, or a claim would materially change.

At completion:

- run the checks mapped in `docs/VALIDATION_PLAN.md`;
- update `docs/DECISIONS.md` for a changed decision and `docs/EVIDENCE_REGISTER.md` for changed evidence;
- trace every reported number to an immutable result artifact;
- record significant milestones in the platform’s agent memory with a concise note and one index entry pointing to the authoritative project document instead of duplicating it.

## Repository map

```text
SHAR/
  CLAUDE.md                 # this persistent entry point
  SHAR_Research_Plan.docx   # preserved historical synthesis
  docs/                     # authoritative research and execution specification
  papers/                   # ten local PDFs; no JSON extractions currently
  Datasets/                 # local-only, ignored by Git
```

Do not assume historical paths such as `likith papers/`, `second_code/`, or topic-mirrored paper JSON folders exist unless they are actually added and inspected.
