# P0A work item — data inventory and contract freeze

> Started: 2026-07-20 · Closed: 2026-07-20 · State: `DONE`

## Control packet

- **Sprint/work item:** `P0A` / `P0A-W1`
- **Governs:** FR-1, FR-13, FR-14; DR-1 and the access/role portions of DR-2–DR-7; V-D1, V-D5, V-D6; V-G1–V-G3; D-01–D-07, D-13, D-17–D-19, D-21.
- **Objective:** create a reproducible content inventory of the local data and freeze the access, provenance, task, label, split, metric, and manifest contracts.
- **In scope:** local content checksums and aggregate distributions; separate media/annotation access records; dataset roles and gates; task contract; manifest schema; fixture and real-data verification.
- **Non-goals:** interval parsing or source-video reconstruction (P0B), environment/model foundation (P0C/P1A), training, headline evaluation, and benefit claims.
- **Dependencies/blockers:** local data is present; B-001 blocks later real interval mapping. Unknown local acquisition/license evidence must remain explicit and may block affected use or release.
- **Artifacts:** `data/registry/`, `data/schemas/`, `results/p0a/`, and this work-item record.
- **Verification:** standard-library unit tests plus the full content-addressed acceptance inventory; machine verdicts map to V-D1/V-D5/V-D6.
- **DoD:** every checkbox below is binary and evidence-linked.
- **Next action:** follow the live blocker/action state in `PROJECT_STATUS.md`; P0A is closed.

## Definition of done

- [x] Deterministic sorted inventory hashes every included local file and reproduces its aggregate digest.
- [x] UCF counts are 1,266,345 Train and 111,308 Test; every inventoried PNG is readable and 64×64.
- [x] UCF per-split/class counts and content digests are persisted.
- [x] Avenue has 16 training and 21 testing clips; its mask/volume components are inventoried separately.
- [x] Media and annotation access records are separate, with unknown facts left unknown.
- [x] Every planned component is core, conditional, optional, or watch-only and has an explicit gate.
- [x] Task, ontology, split, evaluation-view, metric, and pseudo-label boundaries are frozen.
- [x] The eleven-field manifest schema and positive/negative fixtures pass.
- [x] V-D1, V-D5, and V-D6 have machine-readable verdicts.
- [x] No licensed raw media is committed or redistributed.
- [x] No P0B mapping, training, headline evaluation, or benefit claim occurred.
- [x] `PROJECT_STATUS.md` reports code-, run-, and research-completion separately.

## Verification and remaining gate

- Inventory: `../results/p0a/inventory-57f3a29b43a7d2e6/inventory_summary.json`
- Reproduction: `../results/p0a/reproduction-57f3a29b43a7d2e6.json`
- Historical scan-time machine verdicts: `../results/p0a/inventory-57f3a29b43a7d2e6/verification.json` (retained with V-D6 blocked before owner confirmation)
- Post-confirmation access verification: `../results/p0a/access-verification-20260720.json`
- Closure: `../results/p0a/p0a-closure-20260720.json`
- `V-D1`: `PASS`; `V-D5`: `PASS`; `V-D6`: `PASS` only in the linked post-confirmation artifact after the owner confirmed direct acquisition sources and accepted conservative non-commercial/no-redistribution restrictions.
- P0A is `DONE`. Official UCF temporal annotations remain B-001 and block P0B real-data completion, not P0C.
