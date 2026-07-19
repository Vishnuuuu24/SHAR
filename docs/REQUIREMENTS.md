# Requirements — SHAR

> v2.0 · 2026-07-19 · FR = functional, NFR = non-functional, DR = data.

## Functional requirements

- **FR-1 Data manifests:** build deterministic CSV manifests with `filepath`, `source_dataset`, `source_video_id`, `source_frame_index`, `label`, `label_scope`, `label_source`, `annotation_version`, `inside_official_interval`, `split`, and stable content digest.
- **FR-2 Split integrity:** all train/validation partitions are grouped by source video and approximately stratified by class. No source video may span partitions.
- **FR-3 UCF evaluation views:** produce (a) the headline official-interval-derived event-only test view and (b) a separately named inherited-label full-directory noisy-proxy view. Frames outside official intervals in anomalous test videos are excluded from the headline view.
- **FR-4 Noise injection:** Gaussian, salt-and-pepper, speckle, and low-light transformations are parameterized and reproducible from a cryptographic filepath/content digest plus global seed.
- **FR-5 Denoisers:** expose median, Gaussian blur, bilateral, NLM, ESVDAE, and one pinned pretrained modern restoration baseline through a uniform interface.
- **FR-6 RESULT 1 metrics:** PSNR and SSIM use the uncorrupted frame as reference; downstream accuracy and macro-F1 compare noisy versus denoised inputs under a frozen evaluation protocol.
- **FR-7 ROI evidence:** use a pinned stock detector for deterministic ROI proposals and measure its value only through downstream full-frame-versus-ROI classification. Optional localization metrics require independent UCF-Crime2Local, COCO, or AVA annotations.
- **FR-8 Pseudo-label boundary:** model-generated UCF labels may be used only as deterministic ROI proposals or a separately ablated auxiliary training signal. They must carry `label_source=teacher` and never enter ground-truth evaluation files.
- **FR-9 Deferred detector design:** MSDAM, ASFF, Gaussian fusion, and detector Slide Loss are future-work hypotheses, not core implementation requirements. They may be promoted only through a new decision after independent annotations, task-compatible metrics, compute budget, and source discrepancies are resolved.
- **FR-10 Classification:** compare a ResNet50 transfer baseline, at least one temporal video/sequence baseline, and the SEMSCNN-inspired 2-D multiscale-SE head. The adapted head consumes a spatial backbone feature map; a reshaped GAP vector is prohibited. Raw RGB is a separate model family, not a same-head input ablation.
- **FR-11 Metrics:** persist accuracy, macro precision/recall/F1, per-class F1, confusion matrices, video-clustered 95% confidence intervals, and the appropriate independent box/mask metric for each localization dataset.
- **FR-12 Explainability:** generate a fixed, provenance-recorded gallery of correct and incorrect classifications. Qualitative review is not a quantitative success criterion.
- **FR-13 Experiment provenance:** every run records config digest, code revision, seed, package/model versions, dataset manifest digest, annotation version, hardware, and metric artifact paths.
- **FR-14 License gate:** no external dataset enters a run or release until its media and annotation access/license terms and redistribution constraints are recorded.

## Non-functional requirements

- **NFR-1 Reproducibility:** headline rows use seeds `{0,1,2}` and deterministic loading where feasible; instability larger than the claimed gain rejects the claim.
- **NFR-2 Evidence honesty:** negative results remain in tables; task-incompatible published metrics appear only in related work.
- **NFR-3 Quality-first compute:** primary execution uses the full intended data, capacity, resolution, seed count, and registered epoch/early-stop policy. Do not subsample or shrink a headline run merely for speed. If the Mac cannot complete it feasibly, stop and request a protocol/compute decision.
- **NFR-4 Version freeze:** pin Ultralytics, PyTorch, CUDA, pretrained checkpoints, and dataset annotation versions. Re-check current-model claims at implementation freeze.
- **NFR-5 Data separation:** raw licensed media is not committed or redistributed unless its terms explicitly allow it; manifests and derived artifacts retain provenance.
- **NFR-6 Terminology:** use “C2PSA,” “weak/noisy video-label-inherited frames,” and “official-interval-derived event-only evaluation.” Do not call interval labels clean ground truth.
- **NFR-7 No manual-annotation dependency:** the core success path relies only on existing annotations; manual review may be optional qualitative inspection, never an exit gate.
- **NFR-8 Pre-run honesty:** before a run expected to exceed 30 minutes, provide a measured throughput-based wall-time range, completion window, storage estimate, peak unified-memory range, and fallback uncertainties as specified in `COMPUTE_POLICY.md`; re-estimate if the first full epoch differs by >20%.

## Data requirements

- **DR-1 Resolved:** the local Kaggle UCF mirror contains 64×64 images; verified totals are 1,266,345 train and 111,308 test images.
- **DR-2:** acquire and checksum official UCF temporal annotations before the classification baseline; verify filename/frame-index alignment with known examples.
- **DR-3:** original-resolution UCF videos are required only for compatible Stage 2/ROI experiments and only if access terms are recorded. Never upsample 64×64 images and imply recovered detail.
- **DR-4:** acquire UCF-Crime2Local annotations for the core surveillance localization benchmark; record its six-class scope and split.
- **DR-5:** CUHK Avenue remains binary anomaly evaluation only. Its masks may not be reported as SHAR instance-segmentation ground truth.
- **DR-6:** AVA, XD-Violence, MSAD, RareAnom, COCO, and all future data require a task/ontology mapping and license record in `DATA_SPEC.md` before use.
- **DR-7:** VALU and FS-UCF-Crime remain watchlist sources until their complete annotation packages are publicly obtainable and verified.
