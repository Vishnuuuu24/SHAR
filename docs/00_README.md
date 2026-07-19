# SHAR documentation map

> v2.0 · 2026-07-19 · Research specification only; no model implementation has started.

## Authority order

1. `PRD.md` — problem, scope, success, and claim boundaries.
2. `REQUIREMENTS.md` — testable functional, data, and non-functional requirements.
3. `DATA_SPEC.md` — label semantics, datasets, splits, provenance, and metrics.
4. `ARCHITECTURE.md` — design hypotheses and required ablations.
5. `PHASE_PLAN.md` — build order and exit gates.
6. `VALIDATION_PLAN.md` — checks that can support or reject each claim.
7. `RISKS.md` — reviewer objections, failure modes, and scope cuts.
8. `DECISIONS.md` — dated decisions made after the full source audit.
9. `EVIDENCE_REGISTER.md` — claim-by-claim evidence and source status.
10. `COMPUTE_POLICY.md` — M5 Pro/48 GB quality-first run and pre-run estimate rules.
11. `TECH_STACK.md` and `AGENTS.md` — future implementation environment and builder rules.

If documents conflict, use the higher item and update the lower item before implementation. The preserved `SHAR_Research_Plan.docx` is historical input rather than current authority.

## Current research position

- The local Kaggle mirror is verified at 64×64. It contains 1,266,345 train and 111,308 test images, but anomalous frames inherit a source-video class and are not frame-level event ground truth.
- The primary 14-label result will use weak/noisy training labels and an official-interval-derived, event-only test protocol. The original UCF intervals are useful but imperfect, so the wording must remain exact.
- No manual annotation is required. Independent published annotations are used for evaluation: UCF-Crime2Local for surveillance boxes, COCO for masks, and optionally AVA v2.2 for movie action localization.
- Pseudo-labels are optional ROI proposals or training auxiliaries only. They cannot be used as evaluation ground truth.
- The base remains YOLO11 for the custom-module study. YOLO26 is an optional current official comparison, not a silent base swap.
- The SEMSCNN-inspired 2-D visual head is a core, outcome-gated hypothesis. Gaussian fusion, detector Slide Loss, and shallow MSDAM placement are deferred research notes until independent localization labels and a new owner decision justify the added work.

## Immediate attention gates

Before code is written, acquire and checksum: official UCF temporal annotations, original-resolution UCF videos if their access terms permit, and UCF-Crime2Local annotations. Record license/access terms for every external dataset. VALU and FS-UCF-Crime are watchlist items until their promised complete annotations are actually released and usable.
