# P1A work item — data and experiment framework

> Started: 2026-07-20 · Closed: 2026-07-20 · State: `DONE`

## Control packet

- **Sprint/work item:** `P1A` / `P1A-W1`
- **Governs:** FR-1, FR-2, FR-11, FR-13, FR-15, FR-16; V-G1–V-G4; future manifest/metrics/provenance checks.
- **Objective:** build the fixture-verified manifest, grouped-sampling, metric, configuration, artifact, and immutable run-lifecycle framework required before real manifests or models.
- **In scope:** strict manifest CSV loading; config-only data roots; deterministic source-video-grouped validation planning; grouped sample indices; classification metrics and video-cluster bootstrap fixtures; run/attempt lifecycle; provenance refusal; framework smoke artifact.
- **Non-goals:** real interval mapping/manifests (P0B/P1B), model architectures/training (P1C), test-guided tuning, and headline/research claims.
- **Dependencies/blockers:** P0A/P0C code-complete; B-001 does not block fixture/local-path framework code.
- **Artifacts:** `data/`, `eval/`, `core/`, `configs/`, tests, and `results/p1a/` smoke/verification evidence.
- **Verification:** positive/negative manifest fixtures, zero source-group leakage, hand metric parity, video-level bootstrap, immutable lifecycle/provenance failures, and config-root checks.
- **DoD:** framework passes all fixture/hand checks and refuses incomplete provenance or mutable completed artifacts.
- **Next action:** follow the live blocker/action state in `PROJECT_STATUS.md`; P1A is closed.

## Definition of done

- [x] Manifest loader enforces exact fields/order, registered values, configured roots, and optional content digest checks.
- [x] Deterministic grouped split has zero source-video leakage and approximately class-stratified validation groups.
- [x] Grouped sampler indices never mix source-video membership semantics.
- [x] Accuracy, macro precision/recall/F1, per-class F1, confusion matrix, and video-clustered CI pass hand fixtures.
- [x] Run lifecycle appends attempts, refuses incomplete provenance, and prevents completed artifact mutation.
- [x] Fixture smoke closes immutable machine artifacts without touching real headline data.
- [x] All framework tests and verification pass.
- [x] No P1B real completion, model training, headline evaluation, or benefit claim occurred.
- [x] `PROJECT_STATUS.md` states P1A completion and B-001/P1B boundary honestly.

## Verification

- Valid smoke: `../results/p1a/p1a-framework-smoke-e9969c66-a40be623`
- Superseding closure: `../results/p1a/p1a-closure-superseding-20260720.json`
- Two earlier smokes are retained as `INVALID`: one omitted dirty source identity; the next accepted Test rows into grouped splitting and used an incomplete attempt lifecycle.
- Result: the current 44-test full suite passes; P1A is code-complete. P1B real completion still requires B-001.
