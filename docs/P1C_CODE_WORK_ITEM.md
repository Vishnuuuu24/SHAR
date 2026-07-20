# P1C code-only work item — baseline/control architectures

> Started: 2026-07-20 · Closed: 2026-07-20 · Code work item: `DONE`; P1C full run: `BLOCKED`

## Control packet

- **Sprint/work item:** `P1C` / `P1C-CODE-W1`
- **Governs:** FR-10, P1C in `PHASE_PLAN.md`, ResNet-head checks in `VALIDATION_PLAN.md`.
- **Objective:** implement and shape/gradient-test the three mandatory control architectures without starting real-data training.
- **In scope:** ResNet50 C5 extractor with GAP+linear; same-C5 MLP control; source-grouped CNN-LSTM temporal baseline; 14-logit and gradient tests; parameter reports; fixture-only MPS smoke.
- **Non-goals:** pretrained checkpoint download/freeze, training recipe invention, real manifest runs, three-seed headline execution, checkpoint selection, or benefit claims.
- **Dependencies/blockers:** P1A code-complete. P1B/B-001 blocks full P1C runs, not architecture code.
- **Artifacts:** `models/`, tests, and fixture-only `results/p1c/` verification.
- **Verification:** identical C5 spatial input reaches both frame heads; outputs are 14 logits; no GAP-vector spatial reshape; temporal batches retain source-group semantics; finite gradients on tested device.
- **DoD:** code/tests pass and status states code-complete separately from run/research completion.
- **Next action:** add and register the official UCF temporal annotations, then resolve B-006 by approving either logged MPS `warn_only` repeatability evidence or ETA-calibrated strict CPU execution.

## Verification

- Architecture source: `../models/classifiers.py`
- Config gate: `../configs/p1c_architecture_freeze.yaml`
- Valid smoke: `../results/p1c/p1c-code-smoke-4b15b908-bfa53af0`
- Failed strict-MPS attempt: `../results/p1c/failed-smoke-20260720-strict-mps.json`
- Superseding closure: `../results/p1c/p1c-code-closure-superseding-20260720.json`
- Result: the current 44-test full suite passes; all three controls produce 14 logits with finite gradients. Strict deterministic CNN-LSTM backward is unavailable on MPS, so B-006 blocks the temporal full-run policy. No CPU fallback occurred.
