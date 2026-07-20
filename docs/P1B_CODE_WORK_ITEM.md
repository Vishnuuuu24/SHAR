# P1B code-only work item — evaluation-view builders

> Started: 2026-07-20 · Closed: 2026-07-20 · Code work item: `DONE`; P1B real-data completion: `BLOCKED` by B-001/P0B

## Control packet

- **Sprint/work item:** `P1B` / `P1B-CODE-W1`
- **Governs:** FR-3, P1B in `PHASE_PLAN.md`, D-03, and V-D4.
- **Objective:** implement and fixture-test the two frozen UCF evaluation views without generating or evaluating a real UCF manifest.
- **In scope:** exact view names; event-only membership; Normal retention; separate full-directory noisy proxy; traceability, class-count, missing-class, and digest reports; hard refusal of unresolved anomalous membership.
- **Non-goals:** source-frame reconstruction, official interval parsing, real manifest generation, metrics, model execution, or claims.
- **Dependencies/blockers:** P1A is code-complete. B-001/P0B blocks real-data completion, not fixture view-builder code.
- **Artifacts:** `data/views.py`, `configs/p1b_views.yaml`, tests, and immutable fixture-only `results/p1b/` evidence.
- **Verification:** out-of-interval anomalous rows never enter event-only; Normal test-video rows remain; every test row enters the separate noisy proxy; unresolved/contradictory rows stop; missing labels explicitly block a headline claim.
- **DoD:** fixture code/tests and provenance-complete smoke pass; status remains explicit that no real P1B manifest or evaluation exists.
- **Next action:** add and register official UCF temporal annotations, complete P0B mapping, then generate the real P1B manifests and view sidecars.

## Verification

- View builder: `../data/views.py`
- Frozen config: `../configs/p1b_views.yaml`
- Valid fixture smoke: `../results/p1b/p1b-view-smoke-dd0f2476-81037629`
- Final code closure: `../results/p1b/p1b-code-closure-final-20260720.json`
- Result: the 44-test full suite passes. Fixture view code is complete; no real UCF manifest, real view count, metric, or research result exists.
