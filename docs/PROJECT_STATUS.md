# Live project status — SHAR

> Updated: 2026-07-24 · This is the sole live resume pointer. Keep it under roughly one page.

## Current control state

| Field | Current value |
|---|---|
| Project state | `READY` for P1B real-manifest materialization using the approved UCF temporal annotations; no research run exists |
| Current phase | Phase 1 — manifest construction and frozen evaluation views |
| Active sprint | `P1B-W1` — real UCF evaluation-manifest materialization |
| Sprint state | `READY`: B-001 is resolved for the core annotation path. Optional/conditional packages remain unactivated and do not widen this authorization. |
| Code-complete | P0A/P0B/P0C/P1A/P1B view builders/P1C controls: Yes; P1B real-data artifact/P2A: No |
| Run-complete | No — no training or research runs exist |
| Research-complete | No |
| Last verified milestone | P0A-W2 core intake inventoried 2,253 official-UCF files and 104 UCF-Crime2Local files with zero content errors. P0B then streamed all 1,377,653 local Kaggle frames against the exact 290-row official text release: zero quarantine/leakage; 8,548 anomalous Test frames are inside and 37,808 outside intervals. This is mapping evidence, not a manifest, training run, evaluation, or research result. Repository scaffolding verification passes 116 tests. |
| Next concrete action | Materialize real P1B manifests and view sidecars from the frozen P0B mapping report, retaining the source digest and no-raw-redistribution restrictions. |

## Active scope and DoD

`P0A-W2` is closed for the active core path under [`P0A_DATA_INTAKE_ADDENDUM.md`](P0A_DATA_INTAKE_ADDENDUM.md), and [`P0B_WORK_ITEM.md`](P0B_WORK_ITEM.md) is complete. The owner-authorized annotation release permits only internal non-commercial P1B manifest work; raw annotations, media, and crops remain non-redistributable. P1C full runs, every real/full P2A run, P2B/P2C, checkpoint selection, downstream metrics, and research conclusions remain separately gated. `P2A-CODE-W1` is `BLOCKED` by B-007, not an implicit second active work item.

## Open blockers and conditional gates

| ID | Type | Affects | Evidence/current state | Owner / unblock action | Status |
|---|---|---|---|---|---|
| B-001 | Annotation/access | P1B real manifests | Resolved for this narrow scope. The verified Kaggle mirror is `minmints/ufc-crime-full-dataset`, Version 1 (104.89 GB); the local exact TXT digest, parser, full-frame mapping, inclusive boundaries, and zero-quarantine/leakage report pass. Owner authorizes internal non-commercial research only; raw annotations/media/crops remain non-redistributable and upstream footage rights are qualified. | Evidence: [`official-ucf-access-verification-20260724.json`](../results/p0a/official-ucf-access-verification-20260724.json). Materialize P1B manifests without widening scope. | `RESOLVED` |
| B-002 | Media/access, conditional | Original-resolution ROI work only | 1,950 official-UCF MP4 files are locally visible, but source/version/terms and package completeness are not evidenced. The 64×64 mirror cannot support credible detail recovery. | Verify only if original-resolution ROI is activated. | `CONDITIONAL` |
| B-003 | Annotation/access, conditional | Localization mAP or revived custom detector only | UCF-Crime2Local text annotations and split/support files are locally visible, but source/version/terms, native split, media, and evaluator validation are not evidenced. | Complete its native-task intake before any localization metric/custom-detector promotion. | `CONDITIONAL` |
| B-004 | Scientific definition, conditional | Entropy-specific ESVDAE claim only | Exact entropy objective/equations remain unregistered. | Supply a citable definition or retain only the generic denoising-VAE control. | `CONDITIONAL` |
| B-005 | Access/license evidence | P0A V-D6 closure and any run using current local mirrors | Owner confirmed direct Kaggle-account UCF acquisition and public official-page Avenue acquisition; repository records conservative internal non-commercial/no-raw-redistribution restrictions without storing account email. | Closure evidence: `results/p0a/p0a-closure-20260720.json`. | `RESOLVED` |
| B-006 | MPS determinism | P1C temporal baseline full run only | PyTorch 2.13 MPS `scatter_reduce` has no strict deterministic backward; explicit `warn_only` stays on MPS and produces finite gradients, while CPU fallback is disabled. | Owner chooses logged MPS `warn_only` plus repeatability/3-seed evidence, or strict deterministic CPU execution after ETA calibration. | `OPEN` |
| B-007 | Scientific convention freeze | P2A code closure and every P2A run | RGB layout/dtype/range, clipping/quantization, exact Gaussian/salt-pepper/speckle/low-light semantics, PSNR/SSIM options, and classical-filter parameter matrix are not frozen. | Owners approve a registered convention matrix; until then code requires explicit parameters and fixture settings are non-experimental. | `OPEN` |

## Last verification

- Full content scan verified 1,377,653 readable 64×64 UCF PNGs (11,573,357,152 bytes) and zero content/header errors; Train/Test counts are 1,266,345/111,308.
- P0A-W2 core intake: [`inventory-ed66e4a2034c0585`](../results/p0a/inventory-ed66e4a2034c0585/) content-inventoried 2,253 official-UCF files (1,950 source-video containers, 290 MAT intervals, text/support files) and 104 UCF-Crime2Local annotation/split files with zero content errors. The scoped superseding inventory [`inventory-a8f1ed51716e4f69`](../results/p0a/inventory-a8f1ed51716e4f69/) records the current access registry: V-D6 passes for the core annotation and lists non-core unknown terms without activating them; V-D1 is intentionally not evaluated in this non-frame scan.
- P0B full mapping: [`p0b-mapping-20260724.json`](../results/p0b/p0b-mapping-20260724.json) parsed the exact official TXT release (`3b954…2ae2a17c`) and streamed all 1,377,653 Kaggle-frame references with zero quarantine and zero source-video outer-split leakage. It records inclusive boundaries and 8,548/37,808 inside/outside anomalous Test frames; no manifest or research result was written.
- Full content scan verified all 97 local CUHK Avenue files (37 AVI, 58 MAT, one M file, one TXT; 830,450,056 bytes) with zero read errors and the expected 16 train/21 test clips.
- Aggregate inventory SHA-256 is `57f3a29b43a7d2e6f88470edad75d810203bfa5c5978f8fc60dbb524a15da52a`; an independent second pass reproduced it and the detailed compressed inventory byte-for-byte.
- P0A post-confirmation verification: [`access-verification-20260720.json`](../results/p0a/access-verification-20260720.json); the earlier scan-time V-D6 `BLOCKED` artifact is retained, and V-D6 passes only after owner confirmation under recorded restrictions.
- P0C superseding closure: [`p0c-closure-superseding-20260720.json`](../results/p0c/p0c-closure-superseding-20260720.json); the exact lock and SHAR wheel rebuild/import outside the checkout; V-D7/V-D8 pass and MPS is available with fallback disabled.
- P1A superseding closure: [`p1a-closure-superseding-20260720.json`](../results/p1a/p1a-closure-superseding-20260720.json); grouped splitting refuses Test rows, handles uneven groups, and the stricter attempt lifecycle closes valid fixture evidence.
- P1B final code closure: [`p1b-code-closure-final-20260720.json`](../results/p1b/p1b-code-closure-final-20260720.json); deterministic fixture-only event/noisy views pass with frozen UCF source and unique source-frame boundaries. Real-data materialization is now the next governed action, not a completed result.
- P1C superseding code closure: [`p1c-code-closure-superseding-20260720.json`](../results/p1c/p1c-code-closure-superseding-20260720.json); three controls and governed MPS attempt/closure records pass; full execution is not complete.
- P2A setup reproduction: [`fresh-environment-p2a-v4-20260721.json`](../results/p2a/fresh-environment-p2a-v4-20260721.json) recreates the exact 22-package lock in a temporary Python 3.12 environment, deterministically rebuilds the project wheel twice, verifies the fail-closed convention loader and all other P2A wheel members/imports, runs `pip check`, and passes with no lock drift.
- P2A synthetic interface smoke: [`p2a-scaffold-smoke-7a155e42-ce6758b2`](../results/p2a/p2a-scaffold-smoke-7a155e42-ce6758b2/) exercises 10 registered degradation levels × 5 classical restoration methods with explicit fixture-only settings, bound attempt artifacts, live replay, and an authenticated manifest/attempt/aggregate/verdict closure; no real data, training, convention freeze, or benefit claim occurred.
- Full repository suite: 116 tests pass; compile, dependency, serialized-syntax, local-link, import, immutable-artifact, owner-placeholder, convention-approval, full-streaming P0B boundary/leakage, all-stochastic-family DataLoader-worker determinism, and isolated wheel checks pass.
- Synthetic ResNet50 calibration at batch 64 measured 928.90 images/s median; it is compute-readiness evidence, not a research result.
- No model training artifact, headline evaluation, or research result exists.
- `PHASE_PLAN.md`, `PROJECT_CONTROL.md`, and `TRAINING_LOG.md` define the canonical execution path and closure rules.

## Update contract

Update this file whenever the active sprint, state, blocker, last verified milestone, or exact next action changes. Do not copy detailed results here; link to `TRAINING_LOG.md` and immutable artifacts. Do not use this file to change scientific scope.
