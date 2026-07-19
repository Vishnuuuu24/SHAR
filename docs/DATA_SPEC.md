# Data specification — SHAR

> v2.0 · 2026-07-19 · Dataset inclusion requires label-provenance and license gates.

## 1. Dataset roles

| Dataset | Native task / supervision | SHAR use | Labels usable for evaluation | Access/license gate |
|---|---|---|---|---|
| UCF-Crime Kaggle extracted frames | 14 folders; every 10th frame; anomalous labels inherited from untrimmed video | Primary weak/noisy classification training and protocol comparison | Official-interval-derived anomalous test frames plus Normal test videos; folder labels only for noisy-proxy sensitivity | Local mirror present. Kaggle’s CC0 marker does not prove rights to third-party source footage; do not redistribute raw media. |
| Official UCF-Crime videos + temporal annotations | Video-level train labels; temporal anomaly intervals for test | Frame-index mapping, event-only evaluation, optional original-resolution ROI work | Official intervals, with known incompleteness disclosed | Acquire/checksum and record original access terms before use. |
| UCF-Crime2Local | Six human-centred anomaly classes with spatiotemporal boxes; published split | Optional surveillance localization benchmark; preferred if custom detector work is revived | Published action-tube boxes and class labels | Verify annotation/media package availability and terms. No masks. |
| CUHK Avenue | Normal-only train; binary anomaly test with spatial anomaly masks | Secondary binary anomaly robustness only | Native binary/region protocol | Academic dataset terms; never reinterpret as instance masks or 14 classes. |
| COCO 2017 | Object boxes and instance masks | Optional generic detector/segmenter sanity if future custom modules are revived | Official COCO annotations and evaluator | Annotations are CC BY 4.0; source images retain their individual licenses. |
| AVA v2.2 | 430 movie clips; person boxes every second; 80 multi-label atomic actions | Preferred optional movie action-localization/pretraining study | Official boxes/actions and Frame-mAP protocol | Official AVA terms/license record required; movie domain and ontology kept separate. |
| XD-Violence | 4,754 multisource videos, 217 h, audio, six anomaly types, weak train labels | Separate movie/multisource generalization task | Native test annotations and AP protocol only | Official access/terms required; never convert to UCF 14-label ground truth. |
| MSAD | 720 videos, 14 scenarios, detailed human/non-human anomalies | Preferred modern cross-scenario VAD generalization if access is approved | Native official evaluation | Access approval and non-redistribution constraints recorded before use. |
| RareAnom | 2,200 videos, 17 rare anomaly types, temporal annotations | Optional rare/open-set generalization and related work | Native annotations only | Verify dataset media license and access before download/use. |

Watch only: VALU, FS-UCF-Crime, HIVAU-70K, Pistachio, and other promised 2026 releases. A paper or placeholder record is not an available dataset.

## 2. Verified local facts

- Kaggle UCF path: `Datasets/UCF Crime Dataset Kaggle`.
- Verified totals: **1,266,345 Train + 111,308 Test = 1,377,653 images**.
- Resolution: sampled files across train/test and Normal/anomaly folders are **64×64**; the mirror description also specifies 64×64.
- Classes: Abuse, Arrest, Arson, Assault, Burglary, Explosion, Fighting, RoadAccidents, Robbery, Shooting, Shoplifting, Stealing, Vandalism, Normal.
- CUHK Avenue local layout contains 16 train and 21 test clips. Its task remains binary anomaly detection.

## 3. Label semantics

Each manifest row must carry:

`filepath, source_dataset, source_video_id, source_frame_index, label, label_scope, label_source, annotation_version, inside_official_interval, split, file_digest`

Allowed `label_scope` values include `video_inherited`, `temporal_interval`, `box`, `instance_mask`, `atomic_action`, and `teacher_roi`. Allowed `label_source` values must name the exact official annotation release, folder mirror, or teacher checkpoint.

### Headline UCF event-only test

1. Map each anomalous test frame to its source video and original frame/time index.
2. Include it only when the mapped time is inside an official anomaly interval; assign the anomaly class from the source-video identity.
3. Include frames from official Normal test videos as Normal.
4. Exclude out-of-interval frames from anomalous videos from the headline multiclass score.
5. Name the result **official-interval-derived event-only 14-label evaluation**. Do not call it clean or exhaustive; VALU documents omissions in the original boundaries.

The complete Kaggle Test folders may be scored only as **full-directory inherited-label noisy proxy** in a separate sensitivity table.

## 4. Splits and leakage control

- Preserve the outer official/Kaggle Train/Test organization.
- Build validation from Train by grouping on reconstructed source video ID; target approximately 10% per class without splitting a video.
- If reliable source video IDs cannot be reconstructed for a subset, quarantine that subset until resolved. Frame-level random splitting is prohibited.
- For external datasets, use their official split. Do not optimize UCF choices on external test data.
- Report uncertainty with a source-video cluster bootstrap, not a frame-i.i.d. bootstrap.

## 5. No-manual-annotation protocol

- Stock detector outputs are ROI proposals, stored with checkpoint digest, threshold, and `label_source=teacher_roi`.
- Teacher outputs are never copied into evaluation ground-truth files and never used to compute headline mAP against themselves.
- Optional future localization uses published UCF-Crime2Local, COCO, or AVA annotations.
- Manual visual review may diagnose data mapping, but no success criterion depends on creating or correcting labels.

## 6. Noise injection protocol

Per-image randomness is derived from `SHA-256(relative_path || file_digest || global_seed || transform_id)`, not Python `hash()`.

| Degradation | Registered levels | Purpose |
|---|---|---|
| Gaussian | σ ∈ {10, 25, 50} on 8-bit scale | controlled sensor/transmission perturbation |
| Salt and pepper | density ∈ {0.02, 0.05, 0.10} | impulse/dropout corruption |
| Speckle | variance ∈ {0.02, 0.05} | multiplicative corruption stress test |
| Low light | gamma 2.2 plus Gaussian σ=15 | dark-scene robustness stress test |

The source clean frame is the PSNR/SSIM reference. Training corruption is generated on the fly; only deterministic evaluation manifests and parameters are cached. These are synthetic stress tests, not claims about the native UCF noise distribution.

## 7. Data products and metric separation

- `result1_denoise.csv`: method × degradation × level × seed × PSNR/SSIM/downstream accuracy/macro-F1.
- `result2_classify.csv`: protocol view × model × loss × seed × accuracy/macro-F1/per-class F1/clustered CI.
- `roi_ablation.csv`: detector/checkpoint/threshold × full-frame-or-ROI × downstream metrics.
- Optional `localization_ablation.csv`: dataset/task/annotation version × model × box/mask/Frame-mAP as natively defined.

Never place UCF classification accuracy/F1, UCF/Avenue VAD AUC, AVA Frame-mAP, COCO mAP, and UCF-Crime2Local localization scores in one comparable ranking column.
