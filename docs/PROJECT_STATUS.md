# Live project status — SHAR

> Updated: 2026-07-20 · This is the sole live resume pointer. Keep it under roughly one page.

## Current control state

| Field | Current value |
|---|---|
| Project state | `READY` |
| Current phase | Phase 0 — data authority and feasibility |
| Active sprint | `P0A` — inventory, access, licensing, and task freeze |
| Sprint state | `READY` |
| Code-complete | No — implementation has not started |
| Run-complete | No — no training or research runs exist |
| Research-complete | No |
| Last verified milestone | Documentation/evidence audit and execution-control system completed; three independent control reviews are clean |
| Next concrete action | On owner authorization, start `P0A` by implementing the inventory/license/provenance foundation and verifying the existing local datasets; do not start model training. |

## Active scope and DoD

`P0A` is governed by `PHASE_PLAN.md`, `REQUIREMENTS.md` FR-1/FR-13/FR-14, DR-1, and the access/role-classification portions of DR-2–DR-7, plus `VALIDATION_PLAN.md` V-D1/V-D5/V-D6. DR-2 acquisition and real interval-mapping completion belong to `P0B`.

Done means: local inventory is reproducible; media and annotation access/license records exist separately; core versus conditional datasets are explicit; task/label/metric boundaries are frozen; generated artifacts link to their verification. Model training and claim evaluation are out of scope.

## Open blockers and conditional gates

| ID | Type | Affects | Evidence/current state | Owner / unblock action | Status |
|---|---|---|---|---|---|
| B-001 | Annotation/access | P0B, headline UCF evaluation, Phase 1 run-complete | Official UCF temporal annotations are not present locally. | Owners acquire/accept terms; implementation then checksums and validates mappings. | `OPEN` |
| B-002 | Media/access, conditional | Original-resolution ROI work only | Original UCF videos are not present locally. The 64×64 mirror cannot support credible detail recovery. | Acquire only if original-resolution ROI is activated. | `CONDITIONAL` |
| B-003 | Annotation/access, conditional | Localization mAP or revived custom detector only | UCF-Crime2Local annotations are not present locally. | Acquire before any localization metric/custom-detector promotion. | `CONDITIONAL` |
| B-004 | Scientific definition, conditional | Entropy-specific ESVDAE claim only | Exact entropy objective/equations remain unregistered. | Supply a citable definition or retain only the generic denoising-VAE control. | `CONDITIONAL` |

## Last verification

- Existing local data remains documented as 1,377,653 64×64 UCF frames across 14 folders and CUHK Avenue with 16 train/21 test clips.
- No source/model implementation or training artifact currently exists.
- `PHASE_PLAN.md`, `PROJECT_CONTROL.md`, and `TRAINING_LOG.md` define the canonical execution path and closure rules.

## Update contract

Update this file whenever the active sprint, state, blocker, last verified milestone, or exact next action changes. Do not copy detailed results here; link to `TRAINING_LOG.md` and immutable artifacts. Do not use this file to change scientific scope.
