# Risks and reviewer objections — SHAR

> v2.0 · 2026-07-19

## 1. Reviewer-objection table

| Objection | Defensible response | Required artifact |
|---|---|---|
| “These are not true frame labels.” | Correct: training is weak/noisy video-label inheritance; headline test is official-interval-derived and event-only, with known limitations. | label-flow diagram, manifest counts, noisy-proxy sensitivity |
| “Prior 14-class UCF work exists.” | Agreed; contribution is the exact provenance-aware protocol, controlled noise study, and validated adaptations, not first 14-class recognition. | structured related-work table and claim wording |
| “Official intervals are incomplete.” | Use them as reproducible interval-derived labels, never clean truth; exclude ambiguous out-of-interval frames from headline and track corrected releases. | VALU citation, limitations, annotation version |
| “Pseudo-label mAP is circular.” | No pseudo-label mAP is reported. Teacher boxes are preprocessing; value is measured through downstream classification. | label-source assertions and ROI ablation |
| “Why no manual annotations?” | Existing published annotations support optional localization; the core study is designed around classification and ROI proposals without inventing ground truth. | no-manual protocol and scope statement |
| “Movie data is not CCTV.” | AVA/XD-Violence are separate-domain experiments with native metrics, never merged into UCF. | domain-separated tables |
| “Denoising synthetic noise is artificial.” | It is explicitly a controlled stress test, not a claim about native UCF corruption. Downstream effect is reported alongside PSNR/SSIM. | degradation registry and clean-reference protocol |
| “SEMSCNN is an EEG model.” | Cited as inspiration; EEG-specific processing is removed, spatial input is preserved, and the visual head is compared against same-feature controls. | architecture table and head ablation |
| “Why abandon custom YOLO modules?” | Without independent task-compatible labels, module mAP claims would be unsound. The designs are deferred, not presented as achieved contributions. | DECISIONS and deferred appendix |

## 2. Principal risks

| Risk | Likelihood/impact | Mitigation |
|---|---|---|
| Weak/noisy anomalous training frames | High / high | source-video grouping, robust controls, event-only test, label-provenance disclosure |
| Official UCF intervals omit related content | Confirmed / high | exact annotation version, event-only wording, VALU/FS-UCF watchlist, no “clean GT” claim |
| Source-video ID reconstruction fails | Medium / high | quarantine unresolved files; never frame-random split |
| 64×64 detail bottleneck | Confirmed / high | classification honesty; original-resolution media or separately annotated datasets for ROI/localization |
| Dataset/media licensing ambiguity | High / high | separate media/annotation license register; no raw redistribution; owner approval where required |
| Movie-to-CCTV domain shift | High / medium | AVA/XD results separate; retain surveillance-domain evaluation |
| ESVDAE objective underspecified | High / high | generic denoising-VAE baseline; block entropy-specific claim until equations/source exist |
| Multiscale visual head adds no value | Medium / medium | same-C5 controls, compute profile, report negative result and choose simpler head |
| Class imbalance dominates accuracy | High / high | macro/per-class metrics, preregistered tail set, Balanced Softmax/focal/weighted controls |
| Frame correlation inflates certainty | High / high | video-clustered CIs and grouped splitting |
| External dataset release/access changes | Medium / medium | no unreleased dataset dependency; checksum and freeze versions |
| MPS operator gaps or silent CPU fallback | Medium / high | compatibility smoke test, device/fallback logging, measured ETA revision; never hide fallback |
| Long full-data runs on the Mac | High / medium | quality-first schedule, resumable best checkpoints, pre-run throughput/storage estimate, re-estimate after first epoch; request external compute rather than silently downscale |
| Unified-memory pressure/swap | Medium / high | calibrate largest stable batch with OS headroom, monitor memory pressure, close apps only with user approval |

## 3. Deferred-detector risks

- YOLO11 has no P3/P4 C2PSA to replace; future MSDAM must be a clearly defined insertion/replacement study.
- DilateFormer and MADNet do not prove optimal placement for YOLO11/UCF.
- Gaussian fusion has no evidence of benefit and was underspecified.
- Slide paper/code differ and local MS-YOLO shows lower mAP with Slide alone.
- Generic COCO gains would not alone prove suspicious-activity benefit; a downstream/surveillance result is still required.

## 4. Scope cuts

Cut optional external datasets and corruption families in the order listed in `PHASE_PLAN.md`. Custom detector work is already deferred. Never cut provenance, grouped splits, interval-derived evaluation, three headline seeds, macro/per-class metrics, or honest negative reporting.
