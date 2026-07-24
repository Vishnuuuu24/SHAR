# P0B work item — official UCF interval mapping

> Started/closed: 2026-07-24 · State: `DONE`; implementation, local mapping, and narrow annotation eligibility are complete.

## Control packet

- **Sprint/work item:** `P0B` / `P0B-W1`
- **Governs:** DR-2; FR-2, FR-3, FR-13; V-D2–V-D5; V-G1–V-G3; D-03 and D-13.
- **Objective:** map every local Kaggle-UCF frame to a source video/frame coordinate and apply the exact official temporal intervals to anomalous Test frames.
- **In scope:** strict official TXT parser; inclusive interval semantics; strict frame-name parser; source-video outer-split leakage guard; duplicate/unresolved quarantine; immutable mapping report.
- **Non-goals:** manifest materialization, model execution, test tuning, localization metrics, training, headline evaluation, or a benefit claim.
- **Dependencies/blockers:** the official annotation package is locally inventoried and the mapping report passes. B-001 is resolved for internal non-commercial use of the verified Kaggle mirror; raw annotations/media/crops remain non-redistributable. P1B real-manifest materialization is the next governed action.
- **Artifacts:** `data/ucf_intervals.py`, `configs/p0b_mapping.yaml`, `scripts/verify_p0b_mapping.py`, `tests/test_p0b_mapping.py`, and `results/p0b/p0b-mapping-20260724.json`.
- **Verification:** parser rejection fixtures; `start−1/start/end/end+1` inclusive boundary fixture; full streaming scan of 1,377,653 local frames; zero quarantine and zero outer-split leakage.
- **DoD:** complete. Code and local mapping checks pass, and [`official-ucf-access-verification-20260724.json`](../results/p0a/official-ucf-access-verification-20260724.json) records the limited authorization. This does not complete P1B or authorize training/evaluation.

## Verified local mapping

- The exact parsed text release has SHA-256 `3b9542413f2ed9e94f73bf0488c151b3d7d595a8d2ad30f524e9243a2ae2a17c` and 290 source-video rows (140 anomalous and 150 Normal).
- The streaming scan maps all 1,377,653 Kaggle frames: 1,266,345 Train and 111,308 Test.
- Anomalous Test membership is 8,548 inside official intervals and 37,808 outside; Normal Test frames remain separately retained by the P1B view contract.
- Zero malformed/duplicate/unresolved rows and zero source-video outer-split leakage occurred. The report is mapping evidence only: it writes no manifest, model, metric, or claim.

## Remaining transition gate

Do not materialize the real P1B manifests until the owner records the exact source/version and acceptable terms for the locally present official annotation release. On that closure, the next work item is P1B real-manifest materialization using this frozen mapping configuration and digest.
