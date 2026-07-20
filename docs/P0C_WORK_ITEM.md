# P0C work item — environment, reproducibility, and compute readiness

> Started: 2026-07-20 · Closed: 2026-07-20 · State: `DONE`

## Control packet

- **Sprint/work item:** `P0C` / `P0C-W1`
- **Governs:** D-13, D-16, D-18; NFR-1, NFR-3, NFR-4, NFR-8; V-D7, V-D8; `COMPUTE_POLICY.md`.
- **Objective:** freeze a reproducible Python/MPS environment and prove deterministic seeds, explicit device/fallback behavior, provenance closure, and representative local compute calibration.
- **In scope:** Python/package locks; import/platform report; MPS operation smoke path; CPU fallback refusal/recording; stable SHA-256 seed derivation; run-provenance validation; immutable calibration artifact.
- **Non-goals:** official-interval mapping (P0B), real manifests/framework (P1A), model training, headline runs, and research claims.
- **Dependencies/blockers:** P0A `DONE`; B-001 does not block P0C.
- **Artifacts:** environment lock/compatibility report, `results/p0c/` calibration and verification, source/tests, and this work-item record.
- **Verification:** fresh `.venv` import check; deterministic fixtures across fresh processes/workers; representative path stays on recorded MPS or reports explicit fallback; provenance refuses missing fields.
- **DoD:** every checkbox below must have linked evidence.
- **Next action:** follow the live blocker/action state in `PROJECT_STATUS.md`; P0C is closed.

## Definition of done

- [x] Exact Python and package versions are locked and importable from the project `.venv`.
- [x] Platform/MPS availability and tested operations are recorded; no silent CPU fallback occurs.
- [x] Stable per-sample seed derivation reproduces across fresh processes and worker counts.
- [x] Global Python/NumPy/PyTorch seeding is centralized and tested.
- [x] Provenance writer refuses closure when required config/code/data/annotation/environment fields are absent.
- [x] Representative steady-state MPS throughput, storage, and memory method are recorded as calibration, not research.
- [x] V-D7 and V-D8 have machine-readable `PASS` verdicts.
- [x] No research training, headline evaluation, or benefit claim occurred.
- [x] `PROJECT_STATUS.md` states P0C code/run/research completion honestly.

## Verification

- Environment: `../results/p0c/environment-20260720.json`
- Dependency-only fresh rebuild: `../results/p0c/fresh-environment-20260720.json`
- Project-wheel fresh rebuild: `../results/p0c/fresh-environment-project-verified-20260720.json`
- Packaging verification: `../results/p0c/packaging-verification-20260720.json`
- Calibration: `../results/p0c/calibration-8f89fbbe07fad434/calibration.json`
- Calibration governance supplement: `../results/p0c/calibration-attempt-supplement-20260720.json`
- Verification: `../results/p0c/verification-20260720.json`
- Superseding closure: `../results/p0c/p0c-closure-superseding-20260720.json`
- Result: V-D7/V-D8 `PASS`; the exact lock and installed project wheel import outside the checkout; MPS is available and CPU fallback remains disabled. This calibration is not a research result.
