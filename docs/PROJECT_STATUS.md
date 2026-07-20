# Live project status — SHAR

> Updated: 2026-07-20 · This is the sole live resume pointer. Keep it under roughly one page.

## Current control state

| Field | Current value |
|---|---|
| Project state | `BLOCKED` |
| Current phase | Phase 1 — reproducible classification foundation (`code-only`; real-data execution blocked) |
| Active sprint | `P1B` — real manifests and evaluation views (fixture code complete) |
| Sprint state | `BLOCKED` for real-data completion by P0B/B-001 |
| Code-complete | P0A/P0C/P1A/P1B view builders/P1C controls: Yes |
| Run-complete | No — no training or research runs exist |
| Research-complete | No |
| Last verified milestone | P1B fixture view builders and P1C controls are code-complete; the corrected 44-test suite, fresh installed project wheel, and lifecycle-complete MPS smokes pass. |
| Next concrete action | Owners add official UCF temporal annotations to unblock P0B/P1B and approve B-006 temporal execution policy (`MPS warn_only` with repeatability evidence, or strict CPU execution) before full P1C runs. |

## Active scope and DoD

`P1B` fixture view-builder code is complete. P0B parsing/mapping, real UCF manifests/view sidecars, full runs, checkpoint selection, metrics, and research conclusions remain blocked by B-001. P1C architecture code was independently allowed after P1A and is also complete, but no P1C full run may start before real P1B completion.

## Open blockers and conditional gates

| ID | Type | Affects | Evidence/current state | Owner / unblock action | Status |
|---|---|---|---|---|---|
| B-001 | Annotation/access | P0B, headline UCF evaluation, Phase 1 run-complete | Official UCF temporal annotations are not present locally. | Owners acquire/accept terms; implementation then checksums and validates mappings. | `OPEN` |
| B-002 | Media/access, conditional | Original-resolution ROI work only | Original UCF videos are not present locally. The 64×64 mirror cannot support credible detail recovery. | Acquire only if original-resolution ROI is activated. | `CONDITIONAL` |
| B-003 | Annotation/access, conditional | Localization mAP or revived custom detector only | UCF-Crime2Local annotations are not present locally. | Acquire before any localization metric/custom-detector promotion. | `CONDITIONAL` |
| B-004 | Scientific definition, conditional | Entropy-specific ESVDAE claim only | Exact entropy objective/equations remain unregistered. | Supply a citable definition or retain only the generic denoising-VAE control. | `CONDITIONAL` |
| B-005 | Access/license evidence | P0A V-D6 closure and any run using current local mirrors | Owner confirmed direct Kaggle-account UCF acquisition and public official-page Avenue acquisition; repository records conservative internal non-commercial/no-raw-redistribution restrictions without storing account email. | Closure evidence: `results/p0a/p0a-closure-20260720.json`. | `RESOLVED` |
| B-006 | MPS determinism | P1C temporal baseline full run only | PyTorch 2.13 MPS `scatter_reduce` has no strict deterministic backward; explicit `warn_only` stays on MPS and produces finite gradients, while CPU fallback is disabled. | Owner chooses logged MPS `warn_only` plus repeatability/3-seed evidence, or strict deterministic CPU execution after ETA calibration. | `OPEN` |

## Last verification

- Full content scan verified 1,377,653 readable 64×64 UCF PNGs (11,573,357,152 bytes) and zero content/header errors; Train/Test counts are 1,266,345/111,308.
- Full content scan verified all 97 local CUHK Avenue files (37 AVI, 58 MAT, one M file, one TXT; 830,450,056 bytes) with zero read errors and the expected 16 train/21 test clips.
- Aggregate inventory SHA-256 is `57f3a29b43a7d2e6f88470edad75d810203bfa5c5978f8fc60dbb524a15da52a`; an independent second pass reproduced it and the detailed compressed inventory byte-for-byte.
- P0A post-confirmation verification: [`access-verification-20260720.json`](../results/p0a/access-verification-20260720.json); the earlier scan-time V-D6 `BLOCKED` artifact is retained, and V-D6 passes only after owner confirmation under recorded restrictions.
- P0C superseding closure: [`p0c-closure-superseding-20260720.json`](../results/p0c/p0c-closure-superseding-20260720.json); the exact lock and SHAR wheel rebuild/import outside the checkout; V-D7/V-D8 pass and MPS is available with fallback disabled.
- P1A superseding closure: [`p1a-closure-superseding-20260720.json`](../results/p1a/p1a-closure-superseding-20260720.json); grouped splitting refuses Test rows, handles uneven groups, and the stricter attempt lifecycle closes valid fixture evidence.
- P1B final code closure: [`p1b-code-closure-final-20260720.json`](../results/p1b/p1b-code-closure-final-20260720.json); deterministic fixture-only event/noisy views pass with frozen UCF source and unique source-frame boundaries, while real-data completion remains blocked.
- P1C superseding code closure: [`p1c-code-closure-superseding-20260720.json`](../results/p1c/p1c-code-closure-superseding-20260720.json); three controls and governed MPS attempt/closure records pass; full execution is not complete.
- Full repository suite: 44 tests pass; compile/import/package checks pass.
- Synthetic ResNet50 calibration at batch 64 measured 928.90 images/s median; it is compute-readiness evidence, not a research result.
- No model training artifact, headline evaluation, or research result exists.
- `PHASE_PLAN.md`, `PROJECT_CONTROL.md`, and `TRAINING_LOG.md` define the canonical execution path and closure rules.

## Update contract

Update this file whenever the active sprint, state, blocker, last verified milestone, or exact next action changes. Do not copy detailed results here; link to `TRAINING_LOG.md` and immutable artifacts. Do not use this file to change scientific scope.
