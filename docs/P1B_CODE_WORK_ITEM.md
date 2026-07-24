# P1B work item — real manifests and frozen evaluation views

> Started: 2026-07-20 · State: `DONE` — Test views and owner-reaffirmed grouped Train/validation manifests are materialized; no model run occurred.

## Control packet

- **Sprint/work item:** `P1B` / `P1B-CODE-W1`
- **Governs:** FR-3, P1B in `PHASE_PLAN.md`, D-03, and V-D4.
- **Objective:** fixture-test then materialize the frozen UCF Test views and grouped outer-Train manifests without model execution or evaluation.
- **In scope:** exact view names; event-only membership; Normal retention; separate full-directory noisy proxy; deterministic source-video-grouped 10% validation allocation; traceability, class-count, overlap, and digest reports; hard refusal of unresolved anomalous membership.
- **Non-goals:** model training, model selection, metrics, Test-guided tuning, raw redistribution, or claims.
- **Dependencies/blockers:** P1A and P0B are complete. B-001 permits internal non-commercial temporal-annotation manifest work only; it does not authorize raw redistribution, training, or a headline evaluation claim. D-26 records the owner-reaffirmed grouped Train/validation policy used here.
- **Artifacts:** `data/views.py`, `data/train_validation.py`, `configs/p1b_views.yaml`, both P1B materializers, tests, fixture evidence, and local-only evidence under `results/p1b/p1b-*/`.
- **Verification:** out-of-interval anomalous rows never enter event-only; Normal test-video rows remain; every test row enters the separate noisy proxy; unresolved/contradictory rows stop; missing labels explicitly block a headline claim.
- **DoD:** Real source/event-only/noisy-proxy Test manifests are complete with zero unresolved intervals and all 14 headline labels. D-26 then closed the outer-Train allocation: all 1,266,345 source Train rows are assigned deterministically with zero source-video overlap. P1B is complete; no training/evaluation result exists.
- **Next action:** register the P1C architecture/run policy and resolve the MPS determinism choice before any full model run.

## Verification

- View builder: `../data/views.py`
- Frozen config: `../configs/p1b_views.yaml`
- Valid fixture smoke: `../results/p1b/p1b-view-smoke-dd0f2476-81037629`
- Final code closure: `../results/p1b/p1b-code-closure-final-20260720.json`
- Real Test-view closure: local-only `results/p1b/p1b-real-views-57f3a29b-3b954241/` contains 111,308 source Test rows, 73,500 event-only rows, and 111,308 noisy-proxy rows; 37,808 anomalous frames are excluded outside official intervals. All 14 headline labels are present and zero intervals are unresolved. This is not model evaluation.
- Grouped Train/validation closure: local-only `results/p1b/p1b-grouped-train-validation-57f3a29b-10pct-s0/` contains 1,136,536 Train and 129,809 validation rows, representing 1,576/34 source videos with zero overlap. It uses D-26's 10% / seed-0 / `source_video_id` policy, reads no Test rows, and makes no model claim.
