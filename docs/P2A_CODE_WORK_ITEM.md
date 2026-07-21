# P2A code-only work item — degradation and restoration scaffolding

> Started: 2026-07-20 · State: `IN_PROGRESS`; P2A real/full execution: `BLOCKED`

## Control packet

- **Sprint/work item:** `P2A` / `P2A-CODE-W1`
- **Governs:** FR-4, the classical subset of FR-5, FR-6, FR-13, FR-15, D-13, D-16, D-21, D-23, V-D7, V-G1–V-G4, and P2A in `PHASE_PLAN.md`.
- **Objective:** build dataset-independent, parameter-explicit degradation, classical-restoration, and PSNR/SSIM infrastructure without starting a real-data or research run.
- **In scope:** exact registered degradation families/levels; SHA-256 sample seeding; uniform identity/median/Gaussian/bilateral/NLM interfaces; explicit image-quality options; synthetic/hand fixtures; dependency, package, repository, and artifact validation.
- **Non-goals:** real UCF/Avenue execution; P2B learned restoration; P2C downstream matrix; classifier use/tuning; pretrained comparator selection/download; ESVDAE; benefit/native-noise/SOTA claims; invented scientific defaults.
- **Dependencies/blockers:** P0C/P1A code-complete. D-23 authorizes fixture code. B-007 blocks P2A code closure; P1C/B-001 block real/full execution.
- **Artifacts:** `configs/p2a_scaffold.yaml`, `data/degradations.py`, `models/restoration.py`, `eval/image_quality.py`, dataset-free tests, setup/validation scripts, and fixture-only `results/p2a/` evidence when eligible.
- **Verification:** registered-level checks; bitwise process/worker determinism; shape/dtype/range/non-mutation checks; uniform method matrix; hand PSNR and pinned-library SSIM parity; strict config/artifact/package checks.
- **DoD:** all parameter-independent code/tests pass, missing convention fields remain explicit, and status does not claim P2A code/run/research completion.
- **Implemented evidence:** the frozen lock and installed wheel import OpenCV/scikit-image plus all P2A modules, including the fail-closed convention loader, in a fresh temporary environment; 100 dataset-free tests pass; the immutable synthetic smoke exercises all 10 registered degradation levels against all 5 classical restoration methods (50 combinations). Config/API parity, duplicate/schema/capability/approval rejection, all-stochastic-family DataLoader worker-count determinism, direct-constructor refusal, hand/official-library metric/filter checks, terminal artifact binding, and authenticated closure digests are covered. `scripts/check_p2a_readiness.py` reports all 55 currently unresolved B-007 entries (52 convention fields and 3 approval-record fields) without authorizing execution.
- **Evidence links:** [`fresh-environment-p2a-v4-20260721.json`](../results/p2a/fresh-environment-p2a-v4-20260721.json) and [`p2a-scaffold-smoke-7a155e42-ce6758b2`](../results/p2a/p2a-scaffold-smoke-7a155e42-ce6758b2/). Earlier fresh-environment reports and scaffold smokes remain historical evidence; earlier scaffold smokes are retained under explicit authenticated supersession records and cannot support current evidence.
- **Current assessment:** implementation scaffolding is verified, but P2A remains `IN_PROGRESS`; B-007 prevents code closure and the P1C/B-001 gates prevent any real/full execution.
- **Next action:** owners freeze the B-007 convention matrix; then encode it as experiment configuration and rerun the same contract suite before any real data is touched.
