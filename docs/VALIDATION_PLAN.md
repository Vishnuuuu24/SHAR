# Validation plan — SHAR

> v3.0 · 2026-07-20 · A claim is permitted only when its mapped check is green.

## 1. Phase 0 data validation

| ID | Check | Green condition |
|---|---|---|
| V-D1 | Local inventory | 1,266,345 train + 111,308 test; sampled and distribution-level resolution check confirms 64×64; discrepancies stop work |
| V-D2 | Source-video grouping | reconstructed IDs manually inspectable by filename logic and no ID crosses train/validation |
| V-D3 | Interval mapping | registered known UCF examples map frame indices/timestamps to official intervals with boundary tests at start−1/start/end/end+1 |
| V-D4 | Event-only isolation | no out-of-interval anomalous-video frame enters the headline test view; Normal-video frames remain included |
| V-D5 | Provenance completeness | every manifest row has dataset, video/frame identity, scope, source, annotation version, split, and stable digest |
| V-D6 | License/access register | media and annotation terms recorded separately for every included dataset; release restrictions understood |
| V-D7 | Noise determinism | same file/config/global seed is bitwise identical across fresh interpreter processes and data-loader worker counts |
| V-D8 | Compute readiness | MPS device/operation compatibility recorded; representative steady-state throughput measured; pre-run ETA/storage/memory range issued per `COMPUTE_POLICY.md` |

## 2. Execution-governance checks

| ID | Check | Green condition |
|---|---|---|
| V-G1 | Sprint readiness | active work has sprint/work-item ID, governing IDs, scope/non-goals, dependencies, artifacts, DoD, verification, and blockers |
| V-G2 | WIP and status | one active sprint/work item unless explicit independent parallelism is recorded; `PROJECT_STATUS.md` matches repository/artifacts |
| V-G3 | Completion dimensions | code-, run-, and research-completion are stated separately; no result is inferred from code completion |
| V-G4 | Training closure | every logical experiment has a concise ledger row; every attempt has an append-only event plus immutable metrics/summary/verdict/checkpoint-disposition artifacts, including failures |
| V-G5 | Phase transition | every mandatory sprint gate links evidence; claims are `SUPPORTED`, `NOT_SUPPORTED`, or `INCONCLUSIVE`; owner/reviewer transition is recorded |

## 3. Future unit/integration checks

| Component | Required check |
|---|---|
| Denoiser interface | input/output shape, dtype/range, batch consistency, finite loss; identity/no-corruption fixture |
| Denoising VAE | finite reconstruction/KL terms and small-subset overfit; no promised PSNR threshold on a toy image |
| Interval evaluator | synthetic clips with exact boundaries and excluded frames |
| ResNet heads | same C5 input reaches GAP+linear, MLP, and multiscale-SE controls; output has 14 logits |
| Multiscale-SE head | branch shapes, gradients, SE weights, parameter/FLOP budget; no GAP-vector reshape |
| ROI pipeline | checkpoint/config digest recorded; deterministic boxes; explicit no-box fallback; same classifier preprocessing after crop |
| Metrics | fixture values match hand/scikit-learn/native-evaluator results; bootstrap resamples videos, not frames |
| Provenance writer | run cannot finalize with missing config/code/data/annotation/checkpoint digest |

## 4. Claim-to-check mapping

| Proposed claim | Required validation | Green condition |
|---|---|---|
| Denoising improves recognition | paired per-video noisy versus denoised comparison under a frozen classifier, three seeds | consistent macro-F1 improvement whose CI/seed variability does not erase the effect |
| ESVDAE adds value | base denoising VAE versus each stacking/entropy component one at a time | equations/source registered and component benefit exceeds variability/cost; otherwise use generic VAE name |
| Event-aware protocol is more honest | publish label construction, counts, exclusions, and noisy-proxy sensitivity | no leakage; limitations of official intervals stated; no “clean ground truth” wording |
| SEMSCNN-inspired head helps | same ResNet C5 features/budget versus GAP+linear and MLP controls | macro-F1 gain consistent across seeds and acceptable compute; else report negative and keep simpler head |
| Imbalance loss helps | CE versus weighted CE, focal, Balanced Softmax on preregistered tail-class set | macro and tail macro-F1 gain is consistent; no post-hoc class selection |
| ROI preprocessing helps | same classifier/config on full frame versus stock-teacher ROI | downstream macro-F1 improves consistently; detector mAP is not inferred |
| External generalization | frozen mapping/protocol using dataset-native metric | separate table, no UCF metric comparison, license and domain limitations disclosed |

## 5. Localization metric guard

No mAP may be reported unless predictions are compared with independent published annotations. Teacher-generated boxes/masks cannot validate that teacher or its descendants. If future detector work is promoted:

- UCF-Crime2Local: use its native box/tube protocol and six-class scope.
- COCO: use official box/mask mAP50–95 and evaluator.
- AVA: use official Frame-mAP and action list.

Every custom module requires stock baseline, one-module rows, combined row, three seeds where feasible, params/FLOPs/latency, and task-compatible labels.

## 6. Statistical, run-closure, and reporting rules

- Headline classification rows: seeds `{0,1,2}`, mean±std, and source-video-clustered 95% CI.
- Pre-register primary metric, tail classes, sampling cap, early stopping, and model-selection rule from validation only.
- Never treat millions of correlated frames as millions of independent samples.
- A test-set-only improvement discovered after repeated tuning is exploratory, not confirmatory.
- Trace every paper number to a result artifact; blanks remain blank until a run exists.
- Full research rows may not be replaced by calibration/smoke results or speed-driven reduced-data/model runs.
- Experiment closure follows `PROJECT_CONTROL.md`; objective verdict vocabulary and concise history follow `TRAINING_LOG.md`.
- Every full headline experiment registers its objective, control, one material change, primary metric/gate, validation selection rule, and seeds before execution.
- Reconcile actual runtime, peak memory, storage, stop reason, checkpoint disposition, and failures against the pre-run record before declaring run-complete.
- `GOOD` means a preregistered gate passed; `GOOD_ENOUGH`, `BAD`, and `INCONCLUSIVE` remain valid completed research outcomes. `INVALID` evidence cannot support a claim.

## 7. Mandatory stop checks

Stop the affected work and record a blocker on source-video leakage, official-interval mapping ambiguity, teacher/pseudo-label contamination of ground truth, missing provenance/digests, hand/native metric disagreement, license uncertainty, irreproducible deterministic fixtures, unsafe resource behavior, or unapproved material scope change. Continue only independent safe work.

## 8. Comparison hygiene

- Dwivedi 98.87 is not directly comparable; its exact class count remains unverified from the accessible primary source, so do not repeat “3-class.”
- Zaidi 90.14 is a six-category custom task, not the UCF 14-label protocol.
- AVAD 94.94 is mean frame-level ROC AUC for normal-only reconstruction VAD; the paper uses mixed weak/semi-supervised terminology. Related work only.
- Prior 14-category UCF-Crime classification exists; do not claim first-in-task novelty.
- DilateFormer supports MSDA mechanics/shallow-stage evidence, not a proved YOLO P3/P4 placement.
- Slide Loss has paper/code discrepancies and negative local ablation evidence; no benefit claim is allowed without new independent results.
