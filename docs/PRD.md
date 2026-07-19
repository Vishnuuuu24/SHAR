# PRD — SHAR: Suspicious Human Activity Recognition

> Product requirements · v2.0 · 2026-07-19 · Owners: Priyodip, Likith, Vishnu, Abijith

## 1. Problem statement

Manual CCTV monitoring does not scale, but UCF-Crime is not a clean frame-classification dataset: anomalous training videos have video-level labels, many extracted frames do not depict the named event, and the official test intervals are useful but not semantically exhaustive. Prior work already studies 14-category UCF-Crime recognition, so SHAR will not claim to invent that task.

The defensible gap is a reproducible, provenance-aware study of 14-label weak/noisy frame supervision, event-aware evaluation, controlled image degradation/denoising, and independently evaluated localization modules.

## 2. Goal and research outputs

- **RESULT 1 — denoising:** compare classical filters, ESVDAE, and a modern pretrained denoiser using PSNR/SSIM and downstream 14-label macro-F1 delta.
- **RESULT 2 — classification:** report a 14-label classifier trained with video-label-inherited frames and evaluated with the official-interval-derived event-only protocol.
- **ROI study:** use a pinned stock detector to compare full-frame versus person/action-ROI classification. Custom MSDAM/ASFF/Slide detector modules are deferred until an independently annotated detection benchmark is acquired and the added scope is approved.
- **External generalization:** if resources permit, evaluate separately on AVA, XD-Violence, MSAD, or RareAnom without merging ontologies or headline metrics.

## 3. Scope

**In scope:** deterministic source-video-grouped splits; 14-label frame classification; controlled noise injection; denoising; stock-detector ROI preprocessing; full-frame-versus-ROI evaluation; explainability; ablations; optional UCF-Crime2Local/AVA localization and external VAD transfer.

**Out of scope:** creating manual boxes/masks; core custom-detector training; presenting pseudo-label mAP as ground truth; claiming Avenue anomaly masks are instance masks; merging incompatible datasets into one 14-class table; weakly supervised VAD AUC as a direct accuracy baseline; tracking; production deployment.

## 4. Success criteria

| ID | Criterion | Green condition |
|---|---|---|
| S1 | Reproducible 14-label baselines | ≥3 model families, 3 seeds, video-grouped split, provenance-complete manifests, macro/per-class F1 with video-clustered 95% CIs |
| S2 | RESULT 1 matrix | ≥5 denoisers × ≥3 degradation families; PSNR, SSIM, and downstream macro-F1 delta logged |
| S3 | Honest ROI study | Stock-detector ROIs are provenance-recorded; UCF full-frame versus ROI macro-F1 is measured; any optional mAP uses independent published annotations |
| S4 | RESULT 2 label honesty | Headline uses event-only official intervals; full-directory inherited-label score is named noisy-proxy sensitivity only |
| S5 | Ablation completeness | Every shipped or paper-claimed module has one-change-at-a-time rows and compute cost |
| S6 | Reproducibility package | Exact package/model pins, manifests, annotation versions, seeds, configs, and metric artifacts are shareable subject to dataset licenses |

Success never means forcing a module to win. A neutral or negative result is valid when the protocol is sound.

## 5. Claimable contributions

Claim only after the mapped validation gate passes:

1. A documented 14-label UCF extracted-frame protocol that distinguishes weak/noisy training supervision, interval-derived event-only testing, and noisy-proxy sensitivity.
2. A controlled noise→denoise→downstream-effect study on that protocol.
3. An explicit 1-D EEG-to-2-D visual adaptation inspired by SEMSCNN, with spatial-input and kernel ablations.
4. An independently evaluated full-frame-versus-ROI classification study.

## 6. Claims prohibited by the evidence

- “No published 14-class UCF-Crime classification exists.”
- “Kaggle class folders provide frame-level event ground truth.”
- “Pseudo-labels or Avenue anomaly masks validate UCF instance segmentation.”
- “DilateFormer proves P3/P4 is the correct YOLO placement.”
- “AF-YOLO invented ASFF.”
- “Slide Loss is inherently a rare-class loss.”
- “AVAD 94.94 AUC, Dwivedi 98.87, or Zaidi 90.14 is directly comparable to SHAR accuracy.”
- “Gaussian ASFFH, Slide Loss, ESVDAE, or the SEMSCNN-inspired head is beneficial” before a registered, independently evaluated ablation succeeds.

## 7. Decision boundary for movie data

AVA v2.2 is the preferred movie-derived source because it has person boxes, atomic action labels, official evaluation, and a stated license. It is a separate action-localization/pretraining benchmark. XD-Violence is a separate six-anomaly-plus-Normal multisource generalization task. Neither may be relabeled as UCF’s 14 composite crimes without independent annotations.
