# Faculty progress visual pack

> Decision: D-25 · Run class: `faculty_preview` · Scope: local presentation support, not research evidence

## Purpose

Create one deterministic folder containing three predeclared UCF examples at each available pipeline stage. It gives faculty a compact, visual progress update and creates **candidates** for later paper figures. It does not create a training, validation, benchmark, or qualitative-result claim.

## Fixed first pack

The checked configuration is [`../configs/faculty_progress_visual_pack.yaml`](../configs/faculty_progress_visual_pack.yaml). Under the owner-requested D-25 local-only presentation scope, it extracts three event-inside stills from locally present 320×240 official UCF videos. This does **not** activate original-resolution ROI research or resolve B-002:

| Example | Class | Source video | Frame | Official interval |
|---|---|---|---:|---:|
| 01 | Abuse | `Abuse028_x264` | 230 | 165–240 |
| 02 | RoadAccidents | `RoadAccidents016_x264` | 710 | 530–720 |
| 03 | Robbery | `Robbery137_x264` | 1430 | 135–1950 |

They are predeclared to prevent choosing visually favourable outputs after rendering. The renderer verifies every path, source-video ID, class, frame index, and interval membership against the official text annotation before it writes an image.

## Folder contract

The renderer writes one ignored local directory under `results/faculty_progress/`:

```text
<pack>/
  01_original/                 # 320×240 video still, display-enlarged only
  02_gaussian_noise/           # explicit fixture preview corruption
  03_median_restoration/       # classical algorithm on that corruption
  04_bilateral_restoration/    # second classical algorithm on that corruption
  05_temporal_annotation/      # interval provenance overlay, not a mask
  faculty_progress_contact_sheet.png
  manifest.json
  README.md
```

All original, derived, and contact-sheet images remain local and Git-ignored because they are licensed-data derivatives. `manifest.json` records source paths/digests, exact display-only parameters, interval membership, output digests, renderer version, and the no-claim assertions.

## Stage semantics

1. **Original:** 320×240 local official-video still displayed larger for legibility only. It is not super-resolution and does not recover detail.
2. **Noise:** deterministic Gaussian corruption with explicit fixture settings. This is a presentation example, not a model of native camera noise or a selected experiment level.
3. **Classical restoration:** median and bilateral filters applied to the same displayed corruption. These show implemented algorithm plumbing only; no PSNR/SSIM, accuracy, or “improvement” claim is reported.
4. **Temporal annotation:** a provenance overlay confirms the selected frame lies in an official temporal interval. UCF supplies no pixel/instance mask for this pack, so no mask or localization statement is made.
5. **Learned stage (later):** render only after P1C supplies a registered checkpoint and the learned-restoration work item is eligible. Its card must name the checkpoint/config/seed and use a new pack version; it must never be silently substituted into the first pack.

## Faculty and paper use

- For a faculty progress update, present the contact sheet together with its `README.md` and say “display-only preview; no training or evaluation result.”
- For a paper, a candidate must pass the later artifact/claim audit, retain exact provenance, and meet the source terms. Being in this pack does **not** grant publication or raw-media redistribution permission.
- Do not upload these renders to the public Git repository, include them in slides shared beyond the approved research context, crop out provenance, or call the temporal overlay a mask.

## Automatic milestone-update rule

This pack is a standing project control, not a one-off deliverable. At each valid sprint/work-item closure, the closure procedure must evaluate whether a new visual stage can be rendered from a closed, provenance-complete artifact. A renderable stage produces a new immutable pack version and a status/doc update; a non-renderable stage records why and names the next trigger. P1B is renderable because the selected examples can be traced into the real event-only and noisy-proxy manifests. P1C/P2B learned stages remain non-renderable until their respective registered checkpoints exist.

### Version history

| Version | Trigger | Rendered stage | Status |
|---|---|---|---|
| `ucf-temporal-preview-v1` | D-25 initial preview | Original, fixture noise, median/bilateral display filters, and official temporal provenance | Local-only; no model result |
| `ucf-temporal-preview-v2-p1b` | P1B real Test-view materialization | Green membership cards proving all three fixed examples appear in both event-only and noisy-proxy real views | Local-only; membership provenance, not a prediction/evaluation |
| — (no v3) | P1B grouped Train/validation allocation | No new render: the fixed examples are held-out Test frames, and this closure adds no visual/model/annotation stage | The immutable allocation report records this decision; next trigger is a registered P1C checkpoint or another eligible visual stage |

## Re-run and extension rules

Run `./.venv/bin/python scripts/render_faculty_visual_pack.py`. The output directory is immutable: a rerun refuses to overwrite it. The P1B Test-view materializer invokes its membership-preview extension automatically after it closes valid views; the grouped Train/validation materializer automatically records a no-render decision in its immutable report when no new visual stage exists. To add a later stage or change an example, create a new versioned configuration and document the reason in `DECISIONS.md`, then retain the original pack.

## Verification

- unit test uses a synthetic frame/annotation fixture and validates the output tree, provenance, and no-mask/no-claim fields;
- runtime verifies image digests, image mode/shape, official temporal membership, and output digests;
- the repository suite validates imports, syntax, links, and tests.
