# Execution roadmap — SHAR

> v3.0 · 2026-07-20 · Canonical phase/sprint order and gates. Live state is in `PROJECT_STATUS.md`; operating rules are in `PROJECT_CONTROL.md`.

## 1. Roadmap contract

- Follow the core path in order. Optional Phase 4 sprints may be skipped with a recorded reason.
- Phase-0 data/provenance tooling, repository scaffolding, tests, and compute calibration are allowed before the Phase 0 exit gate. **Research model training, headline runs, and benefit claims are not.**
- Report `code-complete`, `run-complete`, and `research-complete` separately under `PROJECT_CONTROL.md`.
- A sprint advances only when its DoD has linked verification. A positive result is never required for completion.
- Universal readiness, experiment, change-control, blocker, and transition rules live in `PROJECT_CONTROL.md` and apply to every row below.
- Before every run expected to exceed 30 minutes, follow `COMPUTE_POLICY.md`; close every training attempt in `TRAINING_LOG.md`.

## 2. Core dependency path

```text
P0A -> P0B -------------------┐
  └-> P0C -> P1A ------------┴-> P1B -> P1C ┬-> P2A -> P2B -> P2C ┐
                                             └-> P3A -> P3B -> P3C ┴-> P5A
P2C + P3C -> optional P4A/P4B/P4C/P4D (or SKIPPED_OPTIONAL) -> P5A -> P5B -> P5C
```

P0B requires official UCF temporal annotations for real-data completion. P0C and P1A code-only infrastructure may continue while access is pending. Under D-23, P2A may also proceed only as parameter-explicit synthetic-fixture scaffolding after P0C/P1A code completion; P1C run completion and a frozen classifier remain mandatory for every real-data/full P2A execution and all later Phase-2 work. P5A requires both P2C and P3C; optional Phase 4 sprints do not block it once explicitly marked `SKIPPED_OPTIONAL`.

## 3. Phase 0 — data authority and feasibility

| Sprint | Prerequisites | Do | Don’t / block condition | Required artifacts and verification | DoD |
|---|---|---|---|---|---|
| `P0A` Inventory, access, licensing, task freeze | Documentation authority established | Inventory/checksum local data; separate media/annotation terms; classify datasets as core/conditional/optional; freeze task, label, split, metric, and manifest schema. | Do not infer a license or make optional original UCF/UCF-Crime2Local a core blocker. Stop affected data use on unclear terms. | Inventory, license/access register, manifest-schema approval; V-D1, V-D5, V-D6. | Local inventory reproducible; core task boundaries frozen; every planned dataset has role and gate. |
| `P0B` Source-video and interval mapping | P0A; official temporal annotations for real completion | Implement filename/source-frame mapping, quarantine policy, interval parser, exact boundary tests, and event-only/noisy-proxy views. | No frame-random split; no out-of-interval anomalous frame in headline; no “clean GT” wording. | Mapping report, boundary fixtures, unresolved-file report; V-D2–V-D4. | Known official examples and start−1/start/end/end+1 tests pass; unresolved files quarantined; zero split leakage. |
| `P0C` Environment, foundation, reproducibility, compute | P0A | Create pinned environment and repository foundation; device/fallback, deterministic seed, provenance, artifact, and representative MPS calibration checks. | No headline training; smoke/calibration output is not a research result; no silent CPU fallback. | Environment lock, compatibility report, calibration artifact, provenance/determinism tests; V-D7, V-D8 and future provenance-writer check. | Fresh environment imports; representative path stays on recorded device or fallback is explicit; ETA/memory/storage method proven. |

### Phase 0 exit

Core exit requires P0A–P0C DoDs, including real official-interval mapping. Original-resolution UCF videos are required only if original-resolution ROI work is activated. UCF-Crime2Local is required only for localization metrics or revived custom-detector work. Missing ESVDAE entropy equations block that named variant, not the generic denoising-VAE control.

## 4. Phase 1 — reproducible classification foundation

| Sprint | Prerequisites | Do | Don’t / block condition | Required artifacts and verification | DoD |
|---|---|---|---|---|---|
| `P1A` Data and experiment framework | P0A and P0C code-complete | Implement manifest loaders, grouped samplers, configs, artifact layout, run lifecycle, metrics, and provenance enforcement using fixtures/local data. | No headline runs; no missing manifest field; no mutable completed artifact; no dataset path assumptions outside config. | Unit/integration tests, fixture manifests, run-lifecycle artifacts. | Framework passes hand/fixture checks and refuses incomplete provenance. |
| `P1B` Real manifests and evaluation views | P1A; P0B for real-data completion | Implement view builders with fixtures, then generate UCF manifests/digests, grouped validation, event-only/noisy-proxy views, and class/source-video reports when official annotations are available. A local `faculty_preview` visual pack may show three predeclared event-inside examples with provenance, but is not a manifest/evaluation substitute. | No source video crosses partitions; no test-guided tuning; fixture success or visual examples are not real-data completion. | Frozen manifest digests, leakage report, view counts, quarantine report; V-D2–V-D5. | Zero leakage; all headline membership is traceable; missing headline classes explicitly block the claim. |
| `P1C` Baseline/control architectures | P1A for code-complete; P1B real-data completion for full runs | Implement and run the preregistered rows: ResNet50 C5→GAP→linear, same-C5 MLP control, and source-grouped CNN-LSTM temporal baseline; three seeds for headline rows. | Do not start full runs before P1B; do not call head controls unrelated published baselines; do not compare few-class accuracy or VAD AUC as same-task results. | Closed training-ledger rows, checkpoints, aggregate metrics, CIs, confusion/per-class artifacts. | All mandatory rows are valid and run-complete. Technical failures stay recorded but keep P1C `IN_PROGRESS`/`BLOCKED` until rerun or approved scope change; valid negative results count. |

## 5. Phase 2 — RESULT 1 denoising

The preregistered primary downstream endpoint is the frozen Phase-1 ResNet50 GAP/linear classifier. After Phase 3, the winning denoiser may be repeated once with the final selected classifier as a separately named confirmatory analysis.

| Sprint | Prerequisites | Do | Don’t / block condition | Required artifacts and verification | DoD |
|---|---|---|---|---|---|
| `P2A` Degradations and classical restoration | P0C/P1A code-complete for D-23 synthetic-fixture code; P1C run-complete and frozen classifier for real/full execution | Implement deterministic Gaussian, salt-and-pepper, speckle, and low-light transforms plus identity, median, Gaussian, bilateral, and NLM interfaces; verify PSNR/SSIM. Before owner convention freeze, interfaces must require explicit parameters and may use only clearly marked fixture settings. | No real-data/full run before P1C completion; do not invent experiment defaults, claim synthetic corruptions model native UCF noise, or cache all training corruptions. | Bitwise fixture determinism, hand metric fixtures, method/interface matrix; V-D7 and denoiser/metric checks. | Code-only closure requires frozen color/range, metric, and classical-filter conventions. Full P2A DoD additionally requires P1C completion and registered real execution. |
| `P2B` Learned restoration | P2A | Implement generic convolutional denoising VAE, justified component ablations, and one pinned pretrained restoration comparator. | Do not use the ESVDAE name/claim without registered equations; do not call a model SOTA permanently. | Overfit/finite-loss checks, source/checkpoint licenses and digests, ledger rows and artifacts. | Base VAE and comparator are code/run-complete as registered; unsupported components remain labeled hypotheses. |
| `P2C` Frozen-classifier downstream matrix | P2A, P2B, frozen P1 classifier | Evaluate every registered degradation/method/level/seed with PSNR, SSIM, accuracy and macro-F1 delta; paired by source video. | No classifier retuning per denoiser; no visual-quality-only benefit claim. | `result1_denoise.csv`, paired analysis, compute, closed ledger and claim decisions. | Full intended matrix is closed; failed/negative methods retained; restoration and recognition conclusions are separated. |

## 6. Phase 3 — RESULT 2 heads, imbalance, and ROI

| Sprint | Prerequisites | Do | Don’t / block condition | Required artifacts and verification | DoD |
|---|---|---|---|---|---|
| `P3A` Visual heads | P1C | Compare same-C5 GAP+linear, MLP, and SEMSCNN-inspired 2-D multiscale-SE head under matched inputs/budgets. Reuse frozen P1C control artifacts only when protocol/config/data/code digests match exactly; otherwise rerun every control. | Never reshape a GAP vector into an image; do not claim the EEG architecture was copied; no mixed-protocol controls. | Shape/gradient/FLOP tests; three-seed metrics and closed ledger rows. | Controls isolate the head change; variability/cost and `SUPPORTED`/`NOT_SUPPORTED`/`INCONCLUSIVE` state recorded. |
| `P3B` Imbalance losses | P3A selected architecture/config frozen | Compare CE, weighted CE, focal, and Balanced Softmax on a preregistered tail-class set. | No post-hoc tail selection; one material loss change per row. | Loss fixtures, aggregate/per-class/tail metrics, ledger and claim state. | Full registered comparison closed; macro/tail conclusions survive or fail variability honestly. |
| `P3C` Stock-detector ROI study | P3B; selected classifier/loss frozen; exact teacher selected; original media only if activated/licensed | Freeze teacher/version/threshold/NMS/fallback; compare identical classifier protocol on full frame versus ROI. | Teacher ROIs are not GT; no mAP without independent annotations; no recovered-detail claim from upscaled 64×64. | ROI provenance, deterministic/fallback tests, `roi_ablation.csv`, ledger and paired downstream analysis. | Downstream comparison is closed; localization claims remain absent unless a conditional independent-label sprint is activated. |

## 7. Phase 4 — optional external evaluation

Each sprint requires official access/terms, native split/ontology/metric mapping, a frozen UCF-trained or separately defined model, and its own table. No external data enters the UCF 14-label headline.

| Sprint | Dataset and purpose | Required DoD |
|---|---|---|
| `P4A` | UCF-Crime2Local surveillance localization sanity | Published six-class box/tube scope and evaluator reproduced; predictions use independent annotations; no masks invented. |
| `P4B` | AVA movie action localization/pretraining | Official v2.2 split/actions/Frame-mAP and license recorded; movie-domain result isolated. |
| `P4C` | XD-Violence or MSAD generalization | One owner-selected dataset uses native AP/AUC/protocol; UCF choices are not tuned on its test set. |
| `P4D` | RareAnom rare/open-set study | Access/license/temporal labels verified; rare/open-set question and native metric preregistered. |

Optional sprint outcomes are `DONE` or `SKIPPED_OPTIONAL`, never silently omitted.

## 8. Phase 5 — audit, reproduction, writing, and release

| Sprint | Prerequisites | Do | Don’t / block condition | Required artifacts and verification | DoD |
|---|---|---|---|---|---|
| `P5A` Artifact and claim audit | Core Phases 1–3 research-complete | Trace every number; reconcile requirements, risks, decisions, evidence, ledger, claims and negative results. | Do not require every hypothesis to win; do not leave blanks disguised as zero. | PRD S1–S6 matrix, claim states, provenance/license audit. | Every required check completed; claims are supported, removed/not supported, or explicitly inconclusive. |
| `P5B` Fresh-environment reproduction | P5A | Recreate environment and rerun the preregistered reproduction protocol; compare artifact digests/metrics within tolerance. | No undocumented local cache/manual step; a failed reproduction may produce a diagnosis but cannot satisfy release DoD. | Reproduction report, environment lock, deviations. | Preregistered tolerance passes. Otherwise P5B remains `BLOCKED` until corrected/rerun or an owner-approved scope/DoD change is recorded. |
| `P5C` Writing, release, and handoff | P5B | Produce paper/review package, permitted code/config/manifests/results, limitations, run instructions and final status. | No prohibited raw-media redistribution, unsupported novelty/SOTA claim, or incompatible metric ranking. | Final manuscript/package, release checklist, handoff/status/memory pointer. | Project-level DoD in `PROJECT_CONTROL.md` is satisfied and owner sign-off recorded. |

## 9. Scope-cut order

1. `P4D` RareAnom and synthetic/open-set work.
2. `P4C` MSAD/XD-Violence external rows.
3. `P4B` AVA pretraining/localization.
4. Low-light and speckle corruption families, retaining Gaussian and salt-and-pepper, only through recorded owner/scientific change control.

Never cut provenance, grouped splits, event-only evaluation, full intended headline data/capacity/resolution, three headline seeds, macro/per-class reporting, claim-aligned controls, or honest negative reporting merely for speed.

## 10. Deferred detector boundary

MSDAM, ASFF, Gaussian gating, detector Slide Loss, YOLO26 comparison, and custom segmentation are outside the core roadmap. Promotion requires a dated owner decision naming independent annotations, native metrics, implementation source/version, compute, exact controls, one-change-at-a-time ablations, added sprints, and scope-cut impact.
