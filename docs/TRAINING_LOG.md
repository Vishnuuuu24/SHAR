# Training history — SHAR

> v1.1 · 2026-07-20 · Concise append-preserving human index; immutable append-only attempt artifacts are authoritative.

## Current training state

**No research training runs have started. No model result or “best model” exists. Material calibration/code-smoke attempts are recorded below and are not research results.**

| Task | Best valid full experiment | Primary result | Gate assessment | Artifact |
|---|---|---|---|---|
| UCF classification | — | — | `PENDING` | — |
| Denoising VAE/restoration | — | — | `PENDING` | — |
| Temporal baseline | — | — | `PENDING` | — |
| Full-frame versus ROI | — | — | `PENDING` | — |
| Optional external evaluation | — | — | `PENDING` | — |

## Ledger

One row represents one logical experiment/configuration and its registered seed set. Its lifecycle fields may be updated until closure, but rows are never deleted and completed rows are immutable. Every launch/retry is appended to `attempts.jsonl` and a unique attempt directory. Create a new experiment row when data, code behavior, model, or frozen configuration changes materially.

| Experiment ID | Date | Sprint / kind | Status | Control → one change | Seeds/attempts / hardware | Primary outcome | Verdict / claim state / reason | Improvement / next action | Immutable artifact |
|---|---|---|---|---|---|---|---|---|---|
| — | — | — | — | — | — | No runs yet | `PENDING` / `NOT_APPLICABLE` | Start only after the applicable readiness and compute gates pass. | — |
| P0C-MPS-CAL-001 | 2026-07-20 | P0C / calibration | `COMPLETED` | Environment import → synthetic ResNet50 MPS training path | s0:1✓ / M5 Pro MPS | 928.90 images/s median at B64, 64×64 FP32 | `GOOD_ENOUGH` / `NOT_APPLICABLE` / compute-readiness path passed | Use only to prove the ETA method; recalibrate each real experiment. | `results/p0c/calibration-8f89fbbe07fad434/` |
| P1A-FRAMEWORK-SMOKE-001 | 2026-07-20 | P1A / fixture smoke | `COMPLETED` | Initial framework → strict outer-Train grouping and governed lifecycle | 1×→2×→3✓ / fixture-only | Split/leakage, metrics, provenance and closure checks pass | `GOOD_ENOUGH` / `NOT_APPLICABLE` / two audited artifacts retained invalid | Use the valid third artifact for P1A code evidence. | `results/p1a/p1a-framework-smoke-e9969c66-a40be623/` |
| P1B-VIEW-SMOKE-001 | 2026-07-20 | P1B / fixture smoke | `COMPLETED` | Frozen membership rules → provenance-separated deterministic UCF-only views | 1×→2×→3×→4✓ / fixture-only | Event-only/noisy-proxy fixture membership and gates pass | `GOOD_ENOUGH` / `NOT_APPLICABLE` / no real UCF view exists | Complete P0B after B-001, then generate real manifests/views. | `results/p1b/p1b-view-smoke-dd0f2476-81037629/` |
| P1C-CODE-SMOKE-001 | 2026-07-20 | P1C / code smoke | `COMPLETED` | Three control shapes → MPS gradients/determinism compatibility | s0:1×→2✓ / M5 Pro MPS | 14-logit shapes and finite gradients; strict temporal determinism unsupported | `GOOD_ENOUGH` / `NOT_APPLICABLE` / code passes, full temporal policy owner-gated | Resolve B-006 before temporal full run; no CPU fallback occurred. | `results/p1c/p1c-code-smoke-4b15b908-bfa53af0/` |
| P2A-SCAFFOLD-SMOKE-001 | 2026-07-20 | P2A / synthetic code smoke | `INVALID` | Initial explicit interfaces → first 10×5 matrix | s0:1× / CPU fixture-only | Matrix ran, but later audit found config/API and closure-integrity gaps | `INVALID` / `NOT_APPLICABLE` / superseded without research use | Retained under the P2A supersession record; use P2A-SCAFFOLD-SMOKE-003. | `results/p2a/p2a-scaffold-smoke-15d6f7f3-8414da9c/` |
| P2A-SCAFFOLD-SMOKE-002 | 2026-07-20 | P2A / synthetic code smoke | `INVALID` | First audited contracts → authenticated 10×5 matrix | s0:1× / CPU fixture-only | Matrix passed, but later audit found remaining clipping/attempt-binding evidence gaps | `INVALID` / `NOT_APPLICABLE` / superseded without research use | Retained under the second P2A supersession record; use P2A-SCAFFOLD-SMOKE-003. | `results/p2a/p2a-scaffold-smoke-28a73d01-8f502497/` |
| P2A-SCAFFOLD-SMOKE-003 | 2026-07-20 | P2A / synthetic code smoke | `COMPLETED` | Fully audited contracts → authenticated 10 degradation × 5 method matrix | s0:1✓ / CPU fixture-only | 50/50 combinations pass; config/API, all-family worker determinism, filters/metrics, attempt binding, replay, and closure authentication pass | `GOOD_ENOUGH` / `NOT_APPLICABLE` / no data, training, or benefit claim | Resolve B-007, encode the owner-frozen matrix, then retest before real execution. | `results/p2a/p2a-scaffold-smoke-7a155e42-ce6758b2/` |

## Status lifecycle

- `PLANNED`: preregistered but not launched.
- `RUNNING`: at least one registered seed/attempt is active.
- `COMPLETED`: all required attempts closed and artifacts reconciled.
- `FAILED`: execution failed technically; retain diagnostics and artifacts.
- `ABORTED`: intentionally stopped with the reason recorded.
- `INVALID`: execution finished or partially ran, but scientific use is prohibited.

Permitted status/verdict pairs:

| Status | Permitted verdicts |
|---|---|
| `PLANNED`, `RUNNING` | `PENDING` |
| `COMPLETED` | `GOOD`, `GOOD_ENOUGH`, `BAD`, `INCONCLUSIVE` |
| `FAILED`, `ABORTED` | `PENDING`; or `INCONCLUSIVE` only when explicitly valid partial evidence exists |
| `INVALID` | `INVALID` |

## Verdicts

- `GOOD`: valid completed full experiment passes its preregistered gate; benefit survives required variability/CI and acceptable compute cost.
- `GOOD_ENOUGH`: valid and reproducible result fulfils its baseline, control, or phase purpose but does not establish a claim-worthy improvement.
- `BAD`: valid completed experiment fails its registered objective or is dominated; retain it as a negative result.
- `INCONCLUSIVE`: valid evidence is insufficient or variability prevents a decision; state the exact missing evidence.
- `INVALID`: leakage, provenance, configuration, metric, annotation, or protocol failure prevents scientific use.
- `PENDING`: execution or required evaluation is incomplete.

“Good” is a gate result, not praise. It does not authorize a paper claim until the mapped validation and decision checks pass.

Claim state is separate: `SUPPORTED`, `NOT_SUPPORTED`, `INCONCLUSIVE`, or `NOT_APPLICABLE`. `GOOD` does not automatically mean supported. A valid, adequately completed `BAD` full comparison may yield `NOT_SUPPORTED`; otherwise the claim remains `INCONCLUSIVE`. Baselines commonly use `GOOD_ENOUGH / NOT_APPLICABLE`.

## Logging rules

1. Open/update one family row in the same session as every pilot or full logical experiment. Append every individual launch, resume, retry, failure, or abort to `attempts.jsonl`. Record a smoke/calibration family only when it changes a decision, exposes a material defect, or supplies the official ETA.
2. Never delete negative, failed, aborted, interrupted, OOM, or invalid history.
3. Keep the Markdown concise: verdict reason and next action are each one sentence, preferably no more than 30 words.
4. Never paste stdout, per-batch/per-epoch telemetry, curves, or large metric tables here. Store them under `results/<experiment-id>/`.
5. An unchanged resume keeps the experiment ID. A material change to data, code behavior, model, loss, resolution, seed policy, or frozen config creates a new ID.
6. Every row links to immutable artifacts; never overwrite a completed run directory.
7. Update the “best valid full experiment” table only from eligible full runs selected by the registered validation rule, never by test-set browsing.
8. A training milestone is not done until runtime/memory/storage estimate versus actual, best/resumable checkpoint disposition, verdict, claim effect, and next action are recorded.
9. Summarize attempts compactly in the seeds/attempts column, for example `s0:1✓ s1:1×→2✓ s2:1✓`; never hide the failed attempt.
10. Primary outcome syntax is `<metric> mean±SD [clustered 95% CI]; Δcontrol=<value>`. Use `N/A` only when the registered protocol makes CI or a control inapplicable.

## Required machine-readable artifact set

```text
results/<experiment-id>/
  run_manifest.json       # objective, config/data/code/checkpoint digests, hardware, pre-run estimate
  attempts.jsonl          # append-only attempt_id, seed, time, status/reason, parent checkpoint, hardware, artifact digest
  seed-<n>/
    attempt-<k>/
      metrics.jsonl       # detailed epoch telemetry
      summary.json        # best epoch, metrics, compute, stop reason, checkpoint disposition
  aggregate.json          # mean/std/CI, control comparison, gate result
  verdict.json            # status, verdict, diagnosis, claim state/effect, next action
```

The artifact directory is the evidence. This file is the short searchable history and review queue.

## Checkpoint retention policy

- Always retain manifests, attempt events, metrics, summaries, aggregates, verdicts, and digests.
- While active, retain the latest valid resumable checkpoint per running seed/attempt.
- At valid closure, retain the validation-selected best checkpoint for every required seed and any checkpoint supporting a reported number.
- Record each checkpoint disposition as `retained`, `pruned`, or `not_produced` with digest, size, reason, and date.
- Never prune a checkpoint supporting a reported/released number. Failed/invalid large checkpoints may be pruned only after diagnostics and summaries are immutable and owner authorization is recorded.
