# P0A data-intake addendum — newly local packages

> Opened/closed: 2026-07-24 · State: `DONE` for the core temporal-annotation path · This addendum does not activate conditional, optional, or watch-only packages.

## Control packet

- **Sprint/work item:** `P0A` / `P0A-W2`
- **Governs:** DR-2, DR-3, DR-4, DR-6; V-D1, V-D5, V-D6; V-G1–V-G3.
- **Objective:** establish reproducible, conservative provenance for data packages that are now locally visible but absent from the prior P0A inventory.
- **In scope:** deterministic inventory of added roots; readability/format distributions; content-tree digests; source/version and media-versus-annotation access records; record of package completeness limits; registry and documentation synchronization.
- **Non-goals:** treating local presence as permission; source-video/frame mapping; real manifests; localization metrics; model execution; training; headline evaluation; benefit claims.
- **Dependencies/blockers:** local roots are visible. The core annotation source/version and owner authorization are now recorded and P0B mapping passes, resolving B-001 for internal non-commercial manifest work only. B-002/B-003 and all optional/watch packages remain conditional.
- **Artifacts:** `data/registry/`, `results/p0a/`, this work-item record, and synchronized status/evidence records.
- **Verification:** deterministic inventory reproduction; source-format/readability checks; registry validation; V-D1/V-D5/V-D6 machine verdicts that distinguish `PASS`, `BLOCKED`, and `NOT_APPLICABLE` honestly.
- **DoD:** all boxes below must be linked to immutable evidence before this addendum is closed.

## Definition of done

- [x] Every newly local root is registered with a role, native-task boundary, local path, and media/annotation separation.
- [x] The inventory scanner records deterministic content-tree digests and format/readability distributions for each included root.
- [x] Official UCF temporal annotations and UCF-Crime2Local annotations are retained in the core immutable intake artifact. COCO, AVA, and CUVA are registered but deliberately unactivated; their full content scans remain optional and must not delay the core UCF path.
- [x] Unknown acquisition, source-version, license, and redistribution facts remain unknown rather than inferred; the core temporal-annotation authorization is owner-recorded rather than inferred.
- [x] CUVA is recorded watch-only and excluded from all approved SHAR task paths.
- [x] `V-D1` remains covered by the retained original Kaggle-UCF inventory; `V-D5` passes for the core addendum roots; `V-D6` permits the core annotation while retaining non-core unknown terms as scoped warnings.
- [x] `PROJECT_STATUS.md`, `DATA_SPEC.md`, `dataset_access.json`, and `EVIDENCE_REGISTER.md` agree with the evidence.
- [x] No training, headline evaluation, localization metric, or research claim occurred; P0B mapping is recorded separately as a completed Phase-0 control artifact.

## Transition

Core intake evidence: [`inventory-ed66e4a2034c0585`](../results/p0a/inventory-ed66e4a2034c0585/) has zero content errors across 2,253 official-UCF files and 104 UCF-Crime2Local files. The scoped superseding scan [`inventory-a8f1ed51716e4f69`](../results/p0a/inventory-a8f1ed51716e4f69/) records the revised registry and V-D6 core pass; it deliberately does not re-evaluate V-D1 because the Kaggle-frame root is outside that scan. The separate access record [`official-ucf-access-verification-20260724.json`](../results/p0a/official-ucf-access-verification-20260724.json) records the verified Kaggle mirror, Version 1, and narrow owner authorization.

P0B local mapping is verified in [`p0b-mapping-20260724.json`](../results/p0b/p0b-mapping-20260724.json). B-001 is `RESOLVED` only for internal non-commercial temporal-annotation use with no raw redistribution; P1B real-manifest materialization may proceed. Added optional packages remain governed by their native-task gates.
