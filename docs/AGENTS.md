# AI agent guide — SHAR

> v2.0 · 2026-07-19 · Read root `CLAUDE.md` and `docs/00_README.md` first.

## Ground rules

1. **Authority:** PRD → REQUIREMENTS → DATA_SPEC → ARCHITECTURE → PHASE_PLAN → VALIDATION_PLAN. Record resolutions in `DECISIONS.md` and evidence in `EVIDENCE_REGISTER.md`.
2. **Source quality:** primary paper/official code/official annotations/direct measurement > official metadata > reputable review > Reddit anecdote. Reddit never proves equations, novelty, labels, or majority consensus.
3. **Local-paper honesty:** `papers/` currently contains ten PDFs and zero JSON extraction files. Never cite a nonexistent JSON or say a missing paper was locally full-read.
4. **Label honesty:** video-label-inherited UCF frames and teacher ROIs are not frame-level ground truth. Official intervals are useful but not clean/exhaustive.
5. **Task separation:** 14-label accuracy/F1, VAD AUC/AP, COCO mAP, AVA Frame-mAP, and UCF-Crime2Local localization metrics are not interchangeable.
6. **No manual-label dependency:** core phases use existing annotations. Do not add a human annotation gate without a new owner decision.
7. **No implementation before Phase 0:** data mapping, access/license, provenance, and unresolved-equation gates must be green.
8. **Ablation discipline:** one material change per row; three seeds for headline results; report mean, variability, and video-clustered confidence intervals.
9. **No forced wins:** negative or neutral results remain visible. If gain ≤ instability, the claim fails.
10. **Terminology:** C2PSA, official-interval-derived event-only, weak/noisy video-label-inherited frames, and SEMSCNN-inspired 2-D multiscale-SE head.
11. **Memory continuity:** after a significant milestone, write a concise project memory and one `MEMORY.md` index line pointing to the authoritative project document instead of duplicating it.
12. **Mac quality-first:** primary hardware is Apple M5 Pro with 48 GB unified memory. Follow `COMPUTE_POLICY.md`; use representative MPS calibration to report ETA before long runs and never silently shrink research runs for speed.

## Source pointers

| Topic | Source of truth |
|---|---|
| UCF label scope/intervals | Official UCF-Crime page; VALU qualification; DATA_SPEC |
| MSDA | local DilateFormer PDF, method + Table X; local MADNet PDF for detector precedent |
| YOLO11 placement | official `yolo11.yaml`; stock C2PSA is at P5 after SPPF |
| ASFF | original ASFF paper; local AF-YOLO pp. 6–7 as verified reuse |
| Slide Loss | YOLO-FaceV2 paper **and upstream code discrepancy**; local MS-YOLO pp. 5–6 negative/mixed ablation |
| SEMSCNN | University of Essex accepted manuscript; visual head choices are SHAR adaptations |
| Datasets/licenses | official dataset pages plus recorded media/annotation terms |

## Deferred work boundary

MSDAM, ASFF/Gaussian fusion, detector Slide Loss, custom segmentation, and YOLO26 comparison are research notes only. Do not implement them unless a new dated decision promotes the work with independent annotations and metrics.

## Definition of done for a future experiment

Config and manifest frozen; source/checkpoint/version digests recorded; relevant validation checks green; three headline seeds complete; metrics trace to immutable artifacts; negative results retained; claims updated; license constraints respected; milestone memory points back to the authoritative doc.
