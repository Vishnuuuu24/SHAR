# Compute and run policy — SHAR

> v2.0 · 2026-07-20 · Primary machine: MacBook Pro, Apple M5 Pro, 48 GB unified memory.

## 1. Quality-first rule

The default research run uses the full intended training data, registered model capacity, registered image/clip resolution, and full epoch/early-stopping policy. Do not reduce data, model size, resolution, seeds, or epochs merely to finish faster.

If a full run is technically infeasible on this Mac, stop before changing the protocol and present the exact constraint and alternatives. A small smoke test may verify correctness or calibrate speed, but it is never reported as a research result and must be labeled `smoke/calibration`.

## 2. Required pre-run estimate

Before every run expected to exceed 30 minutes, report:

- experiment name and whether it is smoke, pilot, or full research run;
- dataset rows/clips and effective samples per epoch;
- model/checkpoint, trainable parameters, input shape, precision, batch size, and epoch/early-stop ceiling;
- measured calibration throughput from a short representative warm run;
- estimated wall-clock range, checkpoint/log storage, peak unified-memory range, and number of sequential seed runs;
- major uncertainty sources, including MPS operator fallback, data decoding, thermal steady state, and first-epoch compilation/caching;
- expected completion range in local time.

Estimate from measured steady-state batches after warm-up:

`estimated_seconds = remaining_batches × measured_median_step_seconds × overhead_factor`

Use an honest range, not a single optimistic number. Re-estimate after the first full epoch if actual pace differs by more than 20%.

## 3. Required post-run reconciliation

Before a run is marked complete, record actual wall time, peak memory, storage growth, throughput, fallback/thermal events, stop reason, best/resumable checkpoint disposition, and deviation from the pre-run estimate. Explain deviations above 20%. Link the immutable run summary and close the concise `TRAINING_LOG.md` entry in the same session; never paste epoch telemetry into the ledger.

## 4. Use the Mac effectively

- Prefer PyTorch’s `mps` backend and verify that tensors/model actually remain on MPS.
- Record every CPU fallback or unsupported operation; a fallback that materially changes ETA must trigger a revised estimate.
- Tune batch size upward with a short calibration sweep, selecting the largest stable batch that does not cause memory pressure or swap. Unified memory is shared with macOS and applications, so 48 GB is not equivalent to 48 GB dedicated VRAM.
- Use mixed precision only after numerical parity/sanity checks. It is an optimization, not permission to change model quality.
- Size data-loader workers and prefetch from measured throughput; more workers are not automatically faster on macOS.
- Keep training corruptions on the fly, cache only deterministic evaluation artifacts, and avoid duplicate decoded datasets.
- Save best validation checkpoints and resumable state so long runs survive interruption.
- Prevent sleep during an approved long run using a standard macOS keep-awake mechanism; do not disable thermal protections.
- Close avoidable memory-heavy applications when the user agrees, but never terminate user work without permission.

## 5. What is and is not downscaling

Allowed before a full run: tiny shape/unit tests, a short representative throughput calibration, one-class/one-batch loader checks, and a brief overfit diagnostic. These establish correctness and ETA.

Not allowed as a headline substitute: fewer training videos/frames, lower resolution, fewer seeds, a smaller model, fewer planned epochs, or incomplete test evaluation chosen only to save time. Any scientifically motivated sampling design requires an explicit new decision and must remain separate from the full-data claim.

## 6. Mac versus external accelerator

The M5 Pro/48 GB Mac is the primary environment for data processing, baseline development, MPS-compatible training, denoising, classification, and evaluation. If an operation is CUDA-only or a full matrix would take impractically long, report that before starting; do not silently change the study. External NVIDIA compute is an optional execution target only after exact environment parity and owner approval.
