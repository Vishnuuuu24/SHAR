# Architecture — SHAR research pipeline

> v2.0 · 2026-07-19 · Core design plus a clearly separated deferred detector appendix.

## 0. Core dataflow

```text
clean frame ── optional registered degradation ── denoiser ─┬─ full-frame classifier
                                                            └─ stock detector ROI ─ classifier
```

The headline outputs are denoising metrics and 14-label classification metrics. Stock detector boxes are preprocessing proposals, not ground truth. Full-frame versus ROI is the causal bridge: the same classifier protocol changes only its input view.

## 1. Denoising study

All methods receive the same corrupted tensor and return the same shape/range. Baselines are median, Gaussian blur, bilateral, NLM, and one exact pinned pretrained restoration model.

**ESVDAE status:** the attached research plan describes stacked variational denoising autoencoders with layer-wise pretraining, KL regularization, end-to-end fine-tuning, and entropy-weighted reconstruction, but it does not provide an unambiguous citable loss definition. Therefore:

- the reproducible base is a convolutional denoising VAE trained noisy→clean with registered reconstruction and KL terms;
- stacking and layer-wise versus end-to-end training are ablations;
- “entropy-weighted ESVDAE” is not implementation-ready or claimable until its equations/source and all constants are added to the evidence register;
- no threshold or loss term may be invented to fill the gap.

RESULT 1 compares restoration quality and downstream classifier change; a PSNR win alone is not evidence of recognition benefit.

## 2. Stock ROI branch

- Freeze an exact Ultralytics package, model checkpoint, preprocessing, classes, confidence threshold, NMS settings, and input resolution.
- Use original-resolution media where licenses permit. Upsampled 64×64 images may be a sensitivity check but cannot be described as recovered detail.
- Generate deterministic person/activity-relevant boxes; classify either the selected ROI(s) or the full frame.
- If no box survives, use the registered fallback policy (full frame or explicit no-ROI outcome) unchanged across models.
- Do not train or score the detector against its own proposals.

## 3. Visual classifier baselines

At minimum compare:

1. ResNet50 C5 feature map → GAP → linear 14-way head.
2. The same C5 tensor → projected MLP/GAP control.
3. A temporal sequence baseline operating on grouped consecutive frames or clips.
4. The SEMSCNN-inspired 2-D multiscale-SE head below.

Training frames remain weak/noisy; model selection uses source-video-grouped validation. The sequence baseline is required because several crime categories depend on motion and temporal context.

## 4. SEMSCNN-inspired 2-D multiscale-SE head

The source SEMSCNN uses 2-D operators over EEG channel×time tensors, with temporal `(1,3)/(1,9)/(1,13)` branches, EEG band/electrode processing, SE, and participant-specific fine-tuning. SHAR does not copy those EEG semantics.

Planned visual adaptation:

- input: ResNet50 pre-GAP C5 spatial tensor `[B, 2048, 7, 7]`;
- project channels to a registered compute-bounded width;
- parallel true 2-D depthwise branches `{3×3, 5×5, 7×7}`;
- concatenate, pointwise fuse, normalize/activate, SE recalibrate, GAP, linear 14-way head;
- compare against GAP+linear and MLP controls on the same C5 features.

A 2048-D GAP vector must never be reshaped into a 2-D image because it has no justified spatial adjacency. Raw-RGB direct classification is a separate whole-network model, not a fair same-feature head ablation. The historical name `SEAMCNN-2D` is retired because SEMSCNN is the cited source and SEAM is an unrelated YOLO-FaceV2 module.

## 5. Classification losses

Core controls are cross-entropy, class-weighted cross-entropy, focal loss, and Balanced Softmax. Report macro-F1 and a preregistered tail-class macro-F1; do not pick “hard classes” after seeing test results.

The proposed confidence-based Slide port is removed from core scope: upstream Slide uses IoU/targets around unreduced detector BCE, not softmax confidence, and it has no class-frequency term. It may return only as a separately named exploratory method with a new evidence/validation decision.

## 6. Deferred detector hypotheses — not core implementation

These notes preserve the researched design without claiming it is beneficial or authorizing implementation. Promotion requires independent annotations, a task-compatible baseline, and a new decision.

### 6.1 MSDAM placement

Official YOLO11 has one stock C2PSA after SPPF at P5/32; P3 and P4 use C3k2. Therefore “replace P3/P4 C2PSA” is structurally false. A future experiment would keep stock P5 C2PSA and insert standalone residual MSDAM after P3 and/or P4.

DilateFormer verifies a 3×3 sampled window, dilation groups `[1,2,3]`, receptive fields 3/5/7, equal head groups, concatenation, and output projection. It finds shallow MSDA preferable in its transformer. MADNet independently applies 3×3 dilated residual blocks `[1,2,3]` across YOLOv5 P2/P3/P4. Neither proves P3/P4 is optimal for YOLO11; required rows are P3-only, P4-only, and P3+P4.

Any future block must project its active width to equal dilation groups, preserve shape with padding, and keep attention normalized over sampled keys. Stock C2PSA head counts cannot be assumed divisible by three.

### 6.2 Standard ASFF control

The verified ASFF control aligns three feature levels, maps each to 8 weight channels, concatenates them, maps to three spatial logits, applies softmax across scales, and fuses the aligned original features. Original ASFF is the method source; local AF-YOLO is a 2026 reuse inside PAFFN.

The former Gaussian `exp(-||xi-xj||²/(2σ²))` proposal is removed from core because it lacks a unique reference feature, alignment/normalization definition, and evidence of benefit. Any future consensus-gating prototype must be explicitly specified and beat standard ASFF under independent evaluation before it appears in contribution language.

### 6.3 Slide Loss discrepancy

Do not call one Slide formula “exact.” The YOLO-FaceV2 paper/reusers specify the middle weight as `exp(1-μ)`, while upstream code uses `exp(μ)`; they coincide only at `μ=0.5`. Upstream code uses per-batch/per-detection-layer mean IoU clamped to at least 0.2, has no EMA, wraps unreduced classification/objectness BCE, and leaves box regression separate.

If revived, register two named variants—`slide_paper` and `slide_upstream_code`—and compare them. Local MS-YOLO reports Slide-only mAP50 0.505 versus baseline 0.517 and mAP50–95 0.300 versus 0.318, so benefit must not be assumed.

## 7. Contemporary comparison boundary

YOLO11 remains the reproducible project base/ROI teacher. If future labeled detector work is approved, a frozen YOLO26 like-for-like row is the current official Ultralytics comparison. YOLO12 remains a community-driven detection-only optional row; it is not the preferred segmentation comparison because official pretrained segmentation weights are unavailable and Ultralytics documents stability/resource cautions.
