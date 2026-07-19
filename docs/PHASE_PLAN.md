# Phase plan — SHAR

> v2.0 · 2026-07-19 · This is a future execution plan. No implementation is authorized by this document update.

## Phase 0 — data authority and feasibility

**Do:** acquire/checksum official UCF temporal annotations; reconstruct and test source-video/frame mapping; create the license/access register; verify UCF-Crime2Local/AVA/MSAD availability if they remain in scope; freeze task definitions; choose the exact pretrained denoiser and ROI teacher; run MPS compatibility and representative throughput calibrations on the M5 Pro/48 GB Mac without treating calibration as research output.

**Exit gate:** known interval examples map correctly; manifest schema is approved; all core media/annotation terms are recorded; no teacher label can enter evaluation ground truth; no unresolved ESVDAE equation is presented as implemented; full-run wall-time/storage/memory ranges are reported before each long run under `COMPUTE_POLICY.md`.

**Human attention:** obtaining original UCF/third-party dataset access may require accepting terms or requesting approval. This is the only immediate external action.

## Phase 1 — reproducible classification baselines

**Do:** build source-video-grouped manifests; run ResNet50 GAP/linear, an MLP-head control, and a temporal sequence baseline; establish the event-only and noisy-proxy test views; log three seeds and clustered confidence intervals.

**Exit gate:** zero video leakage; all 14 labels covered in the event-only view or any missing class explicitly blocks the headline; ≥3 baseline families complete; no published few-class/AUC number appears as a same-task comparator.

## Phase 2 — RESULT 1 denoising

**Do:** register deterministic corruptions; evaluate classical filters, denoising-VAE baseline, justified ESVDAE ablations, and one pinned pretrained restoration model; freeze the Phase 1 classifier before downstream comparisons.

**Exit gate:** full PSNR/SSIM/downstream matrix; paired per-video analysis; conclusions distinguish visual restoration from recognition benefit; failed methods remain reported.

## Phase 3 — RESULT 2 visual-head and ROI study

**Do:** compare GAP+linear, MLP, temporal baseline, and the SEMSCNN-inspired 2-D multiscale-SE head on the same spatial backbone features; compare CE, weighted CE, focal, and Balanced Softmax; run full-frame versus deterministic stock-detector ROI inputs.

**Exit gate:** per-class and macro metrics over three seeds with clustered CIs; input/head/loss changes isolated; no reshaped GAP-vector experiment; any claimed gain exceeds run variability and has acceptable compute cost.

## Phase 4 — optional external evaluation

**Priority:** UCF-Crime2Local for localization protocol sanity, AVA for movie action localization/pretraining, then XD-Violence or MSAD for cross-domain VAD/generalization; RareAnom for rare/open-set analysis if access terms permit.

**Exit gate:** each dataset has its own ontology mapping, native metric, license record, and table. No external label is silently mapped into the UCF 14-label headline.

## Phase 5 — writing and release audit

**Do:** answer every reviewer objection; trace every number to an artifact; run a fresh-environment reproduction; state label limitations prominently; release only artifacts permitted by licenses.

**Exit gate:** PRD S1–S6 checked; all claim gates green; terminology/provenance audit passes; negative results included; current-model/source claims refreshed.

## Deferred future detector work

MSDAM, ASFF, Gaussian gating, detector Slide Loss, YOLO26 comparison, and custom segmentation are not part of the core phase sequence. Promotion requires a dated decision specifying independent annotations, task-compatible metrics, exact source/code variants, compute, and one-change-at-a-time ablations.

## Scope-cut order

1. RareAnom and synthetic/open-set datasets.
2. MSAD/XD-Violence external rows.
3. AVA pretraining/localization.
4. Low-light and speckle corruption families, retaining Gaussian and salt-and-pepper.

Never cut video-grouped splits, provenance, event-only evaluation, full intended training data/capacity/resolution, three headline seeds, macro/per-class reporting, or claim-aligned controls merely for speed.
