# SHAR project entry point

Read [docs/00_README.md](docs/00_README.md) and [docs/AGENTS.md](docs/AGENTS.md) before planning or implementation.

The Markdown documents in `docs/` are the current, decision-complete specification. `SHAR_Research_Plan.docx` is the preserved July 2026 input plan, not the implementation authority. Local primary papers are PDFs in `papers/`; there are currently no paper-extraction JSON files.

Non-negotiable rules:

1. Do not treat video-label-inherited UCF frames or model-generated boxes/masks as ground truth.
2. Keep tasks and metrics separate: UCF 14-label classification, UCF-Crime2Local box localization, COCO mask/box evaluation, and external VAD/action datasets are not numerically interchangeable.
3. Cite primary papers, official annotations, code, and licenses for technical claims. Reddit is an anecdotal failure-mode check, never proof or a majority vote.
4. No implementation begins until the Phase 0 data, provenance, and license gates in `docs/PHASE_PLAN.md` are satisfied.
5. Record every changed research decision in `docs/DECISIONS.md` and its evidence in `docs/EVIDENCE_REGISTER.md`.
6. **Record big steps in agent memory:** whenever a session completes a significant milestone, write a concise project memory plus a one-line `MEMORY.md` index entry that points to the authoritative project document instead of duplicating it. This keeps cross-session progress continuous across compaction.
7. **Use the Mac quality-first:** the primary machine is a MacBook Pro with Apple M5 Pro and 48 GB unified memory. Follow `docs/COMPUTE_POLICY.md`: estimate duration/storage before long runs, use measured MPS throughput, and never silently downscale data, resolution, model, epochs, or seeds for speed.
