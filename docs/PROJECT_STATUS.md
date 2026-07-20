# Live project status — SHAR

> Updated: 2026-07-20 · This is the sole live resume pointer. Keep it under roughly one page.

## Current control state

| Field | Current value |
|---|---|
| Project state | `BLOCKED` |
| Current phase | Phase 0 — data authority and feasibility |
| Active sprint | `P0A` — inventory, access, licensing, and task freeze |
| Sprint state | `BLOCKED` by B-005 after code/data verification |
| Code-complete | Yes for P0A inventory/contracts only; V-D6 and sprint closure remain blocked |
| Run-complete | No — no training or research runs exist |
| Research-complete | No |
| Last verified milestone | P0A inventory and schema verification completed: V-D1/V-D5 pass; second full scan reproduced byte-identical detailed inventory; V-D6 is blocked by B-005. |
| Next concrete action | Owners provide exact local UCF Kaggle and CUHK Avenue acquisition/terms evidence for B-005; then rerun V-D6 and close P0A. Do not start interval mapping or training. |

## Active scope and DoD

`P0A` is governed by `PHASE_PLAN.md`, `REQUIREMENTS.md` FR-1/FR-13/FR-14, DR-1, and the access/role-classification portions of DR-2–DR-7, plus `VALIDATION_PLAN.md` V-D1/V-D5/V-D6. DR-2 acquisition and real interval-mapping completion belong to `P0B`.

Implemented evidence: [`inventory_summary.json`](../results/p0a/inventory-57f3a29b43a7d2e6/inventory_summary.json), [`verification.json`](../results/p0a/inventory-57f3a29b43a7d2e6/verification.json), and [`reproduction-57f3a29b43a7d2e6.json`](../results/p0a/reproduction-57f3a29b43a7d2e6.json). Local inventory, schema, task boundaries, and role/gate records are code/data verified; mandatory local license evidence remains unresolved, so P0A is not `DONE`. Model training and claim evaluation remain out of scope.

## Open blockers and conditional gates

| ID | Type | Affects | Evidence/current state | Owner / unblock action | Status |
|---|---|---|---|---|---|
| B-001 | Annotation/access | P0B, headline UCF evaluation, Phase 1 run-complete | Official UCF temporal annotations are not present locally. | Owners acquire/accept terms; implementation then checksums and validates mappings. | `OPEN` |
| B-002 | Media/access, conditional | Original-resolution ROI work only | Original UCF videos are not present locally. The 64×64 mirror cannot support credible detail recovery. | Acquire only if original-resolution ROI is activated. | `CONDITIONAL` |
| B-003 | Annotation/access, conditional | Localization mAP or revived custom detector only | UCF-Crime2Local annotations are not present locally. | Acquire before any localization metric/custom-detector promotion. | `CONDITIONAL` |
| B-004 | Scientific definition, conditional | Entropy-specific ESVDAE claim only | Exact entropy objective/equations remain unregistered. | Supply a citable definition or retain only the generic denoising-VAE control. | `CONDITIONAL` |
| B-005 | Access/license evidence | P0A V-D6 closure and any run using current local mirrors | Local UCF Kaggle and CUHK Avenue files contain no authoritative acquisition/terms record; a mirror marker or demo Readme is insufficient. | Owners provide the exact download source, accepted terms/license evidence, acceptance date, and accepter for each local media/annotation component. | `OPEN` |

## Last verification

- Full content scan verified 1,377,653 readable 64×64 UCF PNGs (11,573,357,152 bytes) and zero content/header errors; Train/Test counts are 1,266,345/111,308.
- Full content scan verified all 97 local CUHK Avenue files (37 AVI, 58 MAT, one M file, one TXT; 830,450,056 bytes) with zero read errors and the expected 16 train/21 test clips.
- Aggregate inventory SHA-256 is `57f3a29b43a7d2e6f88470edad75d810203bfa5c5978f8fc60dbb524a15da52a`; an independent second pass reproduced it and the detailed compressed inventory byte-for-byte.
- P0A source/tests/contracts and a Python 3.12 project-local `.venv` now exist. No model implementation, training artifact, or research result exists.
- `PHASE_PLAN.md`, `PROJECT_CONTROL.md`, and `TRAINING_LOG.md` define the canonical execution path and closure rules.

## Update contract

Update this file whenever the active sprint, state, blocker, last verified milestone, or exact next action changes. Do not copy detailed results here; link to `TRAINING_LOG.md` and immutable artifacts. Do not use this file to change scientific scope.
