# SHAR documentation map

> v3.0 · 2026-07-20 · Canonical map for research authority, execution control, and live state.

## Authority order

1. `PRD.md` — problem, scope, success, and claim boundaries.
2. `REQUIREMENTS.md` — testable functional, data, and non-functional requirements.
3. `DATA_SPEC.md` — label semantics, datasets, splits, provenance, and metrics.
4. `ARCHITECTURE.md` — design hypotheses and required ablations.
5. `PHASE_PLAN.md` — canonical phase/sprint roadmap, dependencies, artifacts, and exit gates.
6. `PROJECT_CONTROL.md` — readiness, WIP, change control, blockers, layered DoDs, and transition rules.
7. `VALIDATION_PLAN.md` — checks that can support or reject each claim.
8. `RISKS.md` — reviewer objections, failure modes, and scope cuts.
9. `DECISIONS.md` — dated research and governance decision audit trail.
10. `EVIDENCE_REGISTER.md` — claim-by-claim evidence and source status.
11. `COMPUTE_POLICY.md` — M5 Pro/48 GB quality-first run and pre/post-run estimate rules.
12. `PROJECT_STATUS.md` — sole live current-phase/sprint/blocker/resume pointer; it cannot change research scope.
13. `TRAINING_LOG.md` — concise operational training index; immutable artifacts remain the result evidence.
14. `TECH_STACK.md` and `AGENTS.md` — implementation environment and builder enforcement rules.

If documents conflict, use the higher item and synchronize every affected lower document before continuing. `DECISIONS.md` records why a resolution occurred but becomes effective only after the governing documents are updated. The preserved `SHAR_Research_Plan.docx` is historical input rather than current authority.

## Execution entry

After this map, read `AGENTS.md` and `PROJECT_STATUS.md`. Execute only the active sprint in `PHASE_PLAN.md` under `PROJECT_CONTROL.md`. Validation/data/provenance scaffolding is allowed in Phase 0; research training and headline experiments remain blocked until the core Phase 0 exit gate is green.

## Current research position

- The local Kaggle mirror is verified at 64×64. It contains 1,266,345 train and 111,308 test images, but anomalous frames inherit a source-video class and are not frame-level event ground truth.
- The primary 14-label result will use weak/noisy training labels and an official-interval-derived, event-only test protocol. The original UCF intervals are useful but imperfect, so the wording must remain exact.
- No manual annotation is required. Independent published annotations may be used conditionally in their native tasks: UCF-Crime2Local for surveillance boxes, COCO for masks, and AVA v2.2 for movie action localization.
- Pseudo-labels are optional ROI proposals or training auxiliaries only. They cannot be used as evaluation ground truth.
- YOLO11 remains the pinned stock ROI teacher. Custom detector modules are deferred; YOLO26 is an optional current official comparison only if independently labeled detector work is revived.
- The SEMSCNN-inspired 2-D visual head is a core, outcome-gated hypothesis. Gaussian fusion, detector Slide Loss, and shallow MSDAM placement are deferred research notes until independent localization labels and a new owner decision justify the added work.

## Immediate attention gates

The official UCF temporal-annotation package is eligible for internal non-commercial SHAR manifest work: the verified Kaggle mirror is `minmints/ufc-crime-full-dataset`, Version 1, and P0B validates checksums, filename/frame alignment, and exact interval boundaries. Raw annotations, media, and crops may not be redistributed; upstream footage rights remain qualified. Original-resolution UCF videos are locally visible but remain conditional on owner activation of original-resolution ROI work and verified terms. UCF-Crime2Local annotations are locally visible but remain conditional on native localization/custom-detector work, terms, split, and evaluator validation. Record media and annotation terms separately before use. VALU and FS-UCF-Crime remain watchlist items until their complete annotation packages are obtainable and verified.
