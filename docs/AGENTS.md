# AI agent guide — SHAR

> v3.0 · 2026-07-20 · Read root `CLAUDE.md`, `docs/00_README.md`, and `docs/PROJECT_STATUS.md` first.

## Ground rules

1. **Authority and control:** follow the complete order in `00_README.md`; work only on the active sprint in `PROJECT_STATUS.md` under `PROJECT_CONTROL.md`. Record resolutions in `DECISIONS.md` and changed evidence in `EVIDENCE_REGISTER.md`.
2. **Source quality:** primary paper/official code/official annotations/direct measurement > official metadata > reputable review > Reddit anecdote. Reddit never proves equations, novelty, labels, or majority consensus.
3. **Local-paper honesty:** `papers/` currently contains ten PDFs and zero JSON extraction files. Never cite a nonexistent JSON or say a missing paper was locally full-read.
4. **Label honesty:** video-label-inherited UCF frames and teacher ROIs are not frame-level ground truth. Official intervals are useful but not clean/exhaustive.
5. **Task separation:** 14-label accuracy/F1, VAD AUC/AP, COCO mAP, AVA Frame-mAP, and UCF-Crime2Local localization metrics are not interchangeable.
6. **No manual-label dependency:** core phases use existing annotations. Do not add a human annotation gate without a new owner decision.
7. **Phase 0 boundary:** data/provenance/mapping/environment scaffolding, tests, and calibration are allowed. Research training, headline experiments, and benefit claims wait for the core Phase 0 exit gate.
8. **Ablation discipline:** one material change per row; three seeds for headline results; report mean, variability, and video-clustered confidence intervals.
9. **No forced wins:** negative or neutral results remain visible. If gain ≤ instability, the claim fails.
10. **Terminology:** C2PSA, official-interval-derived event-only, weak/noisy video-label-inherited frames, and SEMSCNN-inspired 2-D multiscale-SE head.
11. **Continuity:** update `PROJECT_STATUS.md` before pause/handoff. When platform project memory is available and authorized, add one concise index pointer to the authoritative document; memory never replaces repository state.
12. **Mac quality-first:** primary hardware is Apple M5 Pro with 48 GB unified memory. Follow `COMPUTE_POLICY.md`; use representative MPS calibration to report ETA before long runs and never silently shrink research runs for speed.
13. **Training ledger:** open/close one concise row per pilot/full logical experiment and material calibration in `TRAINING_LOG.md`; append every individual attempt immutably and preserve failures/negative results without dumping epoch logs into Markdown.
14. **Completion honesty:** report code-complete, run-complete, and research-complete separately. `DONE` requires linked verification, not an implementation assertion.

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

## Definition of done enforcement

The canonical work-item, sprint, experiment, phase, and project DoDs are in `PROJECT_CONTROL.md`; sprint-specific artifacts/checks are in `PHASE_PLAN.md`. Three seeds apply to registered headline/full comparisons, not routine smoke tests. No training milestone is done until its immutable artifacts, estimate-versus-actual reconciliation, verdict, claim impact, next action, and concise ledger entry are closed.
