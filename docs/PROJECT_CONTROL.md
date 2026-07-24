# Project control system — SHAR

> v1.0 · 2026-07-20 · Operational rules for keeping implementation and research on track.

This document controls **how work advances**. It does not replace the research scope, data rules, architecture, validation criteria, or evidence in the higher-authority documents listed in `00_README.md`.

## 1. Control loop

Every work session follows the same loop:

1. Read root `../CLAUDE.md`, `00_README.md`, `AGENTS.md`, and `PROJECT_STATUS.md`.
2. Select the single active sprint from `PHASE_PLAN.md`; confirm its prerequisites and blockers.
3. Restate the work item’s governing requirement/decision/validation IDs, in-scope work, explicit exclusions, artifacts, and DoD.
4. Inspect the repository and last-known-good artifacts before changing anything.
5. Implement only the selected work item; verify it with the mapped checks.
6. Update `PROJECT_STATUS.md`, affected decision/evidence records, and—after any training attempt—`TRAINING_LOG.md` in the same session.
7. Advance only when the sprint gate has evidence. Otherwise record the blocker and continue only independent safe work.

The normal WIP limit is **one active sprint and one active work item**. Parallel agents may handle independent subtasks inside that item, but may not silently open another sprint or change scientific scope. If the active sprint becomes externally blocked, record it as `BLOCKED` and explicitly activate one dependency-independent `READY` sprint; never keep two active implicitly.

## 2. Status vocabulary

Use only these states in the roadmap and live status:

- `NOT_STARTED`: prerequisites or authorization are absent.
- `READY`: prerequisites are satisfied and work may start.
- `IN_PROGRESS`: active work exists and its DoD is not yet satisfied.
- `BLOCKED`: a named external, scientific, license, or owner dependency prevents meaningful progress.
- `DONE`: the applicable DoD is verified with linked evidence.
- `SKIPPED_OPTIONAL`: an optional sprint was deliberately omitted with a recorded reason.

Never use `DONE` to mean “code was written,” “one run finished,” or “the result looked promising.”

Blocker records use a separate lifecycle: `OPEN`, `CONDITIONAL`, `RESOLVED`, or `WAIVED_BY_OWNER`. `CONDITIONAL` means it blocks only the named optional/activated scope; a waiver must state why no mandatory scientific or license gate is bypassed.

## 3. Definition of Ready

A work item is `READY` only when all applicable items are known:

- sprint and work-item ID;
- governing requirement, decision, and validation IDs;
- objective, in-scope work, and explicit non-goals;
- required datasets/annotations and their access/license state;
- inputs, dependencies, expected outputs, artifact paths, and verification method;
- for an experiment: run kind, control, one material change, primary metric, success gate, seed policy, selection rule, compute estimate, and stop conditions;
- for a claimed efficiency/benefit tradeoff: a measurable allowed increase in parameters, latency, memory, energy/time, or training cost; “acceptable compute” may not be decided after seeing results;
- owner approval for any material scope, task, label, metric, claim, license, or external-state change.

If a missing answer would change the science, the item is not ready. Do not guess.

## 4. Universal dos and don’ts

### Do

- preserve source-video grouping and label provenance end to end;
- use one-change-at-a-time comparisons and task-native metrics;
- distinguish `code-complete`, `run-complete`, and `research-complete`;
- retain failures, neutral findings, negative results, and invalidated runs;
- link summaries to immutable machine-readable artifacts;
- stop and record a blocker when a license, annotation, leakage, provenance, or scientific gate fails;
- keep dynamic state only in `PROJECT_STATUS.md` and training history only in `TRAINING_LOG.md`.

### Don’t

- bypass a gate by weakening data, seeds, resolution, capacity, provenance, or evaluation;
- use test data for tuning or validation checkpoint selection;
- treat inherited frame labels, teacher ROIs, or pseudo-labels as independent ground truth;
- compare incompatible metrics or merge external ontologies into the UCF headline;
- implement deferred detector hypotheses without a dated promotion decision;
- declare a component beneficial because one seed, one metric, or one qualitative example improved;
- paste console logs, per-epoch telemetry, or large result tables into control documents;
- commit, push, change remotes, or publish data without fresh explicit authorization.

## 5. Layered definitions of done

### Work-item DoD

- requested artifact exists and matches its governing specification;
- mapped unit/static/integration checks pass;
- no known error is hidden by a skip, fallback, or reduced protocol;
- docs/configs/tests changed by the work are synchronized;
- verification evidence and remaining limitations are recorded in `PROJECT_STATUS.md`.

### Sprint DoD

- every mandatory work item satisfies its DoD;
- required artifacts and validation IDs in `PHASE_PLAN.md` are linked;
- blockers are closed or explicitly deferred as optional with owner rationale;
- code, run, and research completion are reported separately;
- the next sprint is marked `READY`, or the project is honestly marked `BLOCKED`.

### Experiment DoD

- preregistered objective, control, material change, metric, gate, selection rule, seeds, and run kind are preserved;
- config, code, data, annotation, environment, and checkpoint digests are complete;
- leakage/provenance checks pass; best checkpoint selection uses validation data only;
- required seeds complete for a full headline experiment; smoke/calibration/pilot runs never substitute for them;
- aggregate metrics, variability, clustered CI where required, compute cost, stop reason, and failures are stored;
- actual time, memory, and storage are reconciled with the pre-run estimate;
- best and resumable checkpoints follow the retention policy in `TRAINING_LOG.md`;
- immutable artifacts and the concise `TRAINING_LOG.md` entry are closed in the same session;
- verdict, claim impact, limitation, and next action are explicit.

### Phase DoD

- all mandatory sprint gates have evidence;
- the phase is separately marked code-complete, run-complete, and research-complete or not applicable;
- every evaluated claim is `SUPPORTED`, `NOT_SUPPORTED`, or `INCONCLUSIVE`; completion never requires a positive result;
- requirements, risks, decisions, evidence, status, and training ledger are consistent;
- an owner/reviewer transition record names the next phase and unresolved optional work.

### Project DoD

- PRD success criteria S1–S6 are checked with artifact links;
- fresh-environment reproduction and provenance audits pass;
- every reported number traces to an immutable artifact;
- unsupported claims are removed and negative results remain visible;
- licenses and redistribution restrictions are satisfied;
- release contents, limitations, final status, and handoff are recorded.

## 6. Completion dimensions

Every sprint/phase reports three independent dimensions:

| Dimension | Meaning |
|---|---|
| Code-complete | Required implementation and automated checks exist. No research result is implied. |
| Run-complete | Registered executions finished and artifacts closed. No positive claim is implied. |
| Research-complete | Required analyses and claim decisions are finished with uncertainty, limitations, and evidence. |

This separation allows infrastructure work before training without pretending the research is complete.

## 7. Run classes

- `smoke`: shape, device, interface, or single-path correctness only.
- `calibration`: representative throughput/memory measurement for an ETA; not research evidence.
- `pilot`: protocol debugging or preregistration refinement using non-test data; not a headline substitute.
- `full`: frozen research protocol eligible for the mapped claim checks.
- `faculty_preview`: deterministic local visual communication of predeclared examples and named pipeline stages. It is neither training nor a benchmark/pilot result, may not tune choices after viewing outputs, and must retain source/parameter/provenance metadata.

### Faculty-preview update rule

At every valid work-item closure, the implementer must decide whether its new artifact adds a renderable, provenance-preserving stage for the three D-25 examples. If yes, create a new immutable local version under `results/faculty_progress/`, add the stage and its exact artifact/config/checkpoint identity, visually inspect it, and update `FACULTY_PROGRESS_VISUAL_PACK.md` plus `PROJECT_STATUS.md`. If no, record the reason and next renderable gate in `PROJECT_STATUS.md`. Never overwrite a pack, substitute a trained result before its gate, or use a visual update as evidence of a research claim.

Three seeds are mandatory only for registered headline/full comparisons unless another higher-authority requirement says otherwise.

## 8. Change control

A dated decision and impact review are required before changing a task, ontology, split, primary metric, model family, loss family, dataset role, annotation source, license assumption, claim, phase scope, or frozen version.

Sequence: evidence/direct measurement → affected requirements and risks → owner approval when material → `DECISIONS.md` entry → update every affected higher-authority document → update `PROJECT_STATUS.md`.

Routine refactors and bug fixes that preserve scientific behavior do not require a research decision, but still require tests and a status checkpoint. If a “bug fix” changes data membership, labels, metrics, or reported results, it is scientific change control.

## 9. Blockers and stop conditions

Each blocker records `ID`, type, affected sprint/gate, evidence, owner, unblock action, and status in `PROJECT_STATUS.md`.

Stop the affected work immediately for source-video leakage, missing/ambiguous annotation mapping, ground-truth contamination, absent provenance, metric disagreement, license uncertainty, non-reproducible results, unsafe memory/storage behavior, or a material scope change without approval. Do not mark the whole project blocked while unrelated safe work remains.

## 10. Pause, resume, and memory

Before pausing, compaction, or handoff, update the live status with completed work, exact verification, artifact links, blockers, last-known-good configuration/digests, and the next concrete action. Chat history and platform memory are convenience layers, not authority.

After a significant milestone, write a concise platform project-memory note only when that facility is available and authorized. Its one-line index must point to the authoritative project document instead of duplicating the roadmap, status, or training history.

## 11. Minimal control records

Use this compact work-item packet in `PROJECT_STATUS.md` or a linked issue/artifact; do not create narrative status essays:

```text
work_item: <sprint-id>/<item-id>
governs: <requirement, decision, validation IDs>
objective: <one sentence>
in_scope / non_goals: <short lists>
dependencies / blockers: <IDs or none>
artifacts: <paths>
verification: <checks and evidence paths>
DoD: <binary checklist>
next_action: <one concrete action>
```

A phase-transition record contains: completed mandatory sprints; code/run/research completion; verification links; claim states; open optional work; blockers/risks; owner/reviewer; date; next phase/sprint. Without that record, the transition has not occurred.
