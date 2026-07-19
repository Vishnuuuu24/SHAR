# Evidence register — SHAR

> v2.0 · 2026-07-19 · Status: `verified`, `qualified`, `rejected`, or `watch`.

## Evidence policy

Technical validity requires a primary paper, official dataset/model page, official annotations/code, or a direct local measurement. Reddit is recorded only to surface practical failure modes. A few comments cannot establish a majority, and silence on a niche equation is not evidence against it.

| Claim or change | Status | Primary evidence | Reddit sanity check / limit |
|---|---|---|---|
| Kaggle mirror is 64×64 with 1,266,345 train and 111,308 test images | verified | Direct local inspection; [mirror description](https://huggingface.co/datasets/hibana2077/UCF-Crime-Dataset/blob/main/README.md) | Not needed; direct data beats opinion. |
| UCF training labels are video-level and test has temporal annotations | verified | [Official UCF-Crime project](https://www.crcv.ucf.edu/research/real-world-anomaly-detection-in-surveillance-videos/) | [A UCF user independently reports missing train/val frame labels](https://www.reddit.com/r/learnmachinelearning/comments/11m27pt/has_anyone_worked_with_the_ucfcrime_dataset_before/); anecdotal only. |
| Official UCF intervals are not semantically exhaustive | verified/qualified | [VALU, ACL 2026](https://aclanthology.org/2026.acl-long.56/) documents omitted related segments and repeated footage | No representative Reddit evidence; none claimed. |
| Pseudo-labels cannot serve as independent evaluation ground truth | verified | mAP requires predictions to be compared with independent reference annotations; use UCF-Crime2Local/COCO/AVA | [Practitioner discussion](https://www.reddit.com/r/computervision/comments/1uqy6hu/labeling_images_automatically/) largely warns against treating noisy automatic masks as ground truth; [a separate discussion](https://www.reddit.com/r/computervision/comments/1l39aiu/zeroshot_labels_rival_human_label_performance_at/) shows auto-labeling can aid training but also exposes missed/occluded objects. This supports the training-only distinction, not proof. |
| UCF-Crime2Local provides real surveillance localization labels | verified | [UCF-Crime2Local paper](https://arxiv.org/pdf/1901.10364); [ST-UCF-Crime paper](https://www.ijcai.org/proceedings/2021/162) is an alternative spatiotemporal benchmark | No meaningful dataset-specific majority found. |
| AVA v2.2 is a strong movie-based localization source | verified/qualified | [Official AVA overview](https://research.google.com/ava/) and [v2.2 download/spec](https://sites.research.google/gr/ava/download/) | [Practitioner report](https://www.reddit.com/r/computervision/comments/1isgpb6/prepare_ava_dataset_to_fine_tuning_model/) warns close-range movie people may transfer poorly to long-range CCTV; therefore separate-domain evaluation is required. |
| XD-Violence is useful movie/multisource generalization data | verified/qualified | [Official XD-Violence project](https://roc-ng.github.io/XD-Violence/) | No statistically meaningful Reddit consensus found. Different labels/task prevent direct UCF comparison. |
| MSAD is a modern multisource generalization candidate | verified/qualified | [Official MSAD project](https://msad-dataset.github.io/) | No statistically meaningful Reddit consensus found; access approval is a practical gate. |
| Prior 14-category UCF-Crime work exists | verified | [Vosta et al., Applied Sciences 2022](https://www.mdpi.com/2076-3417/12/3/1021), [joint anomaly detection/classification](https://arxiv.org/abs/2108.08996), and later 14-class studies | Reddit cannot establish literature novelty. Absolute novelty claim rejected. |
| AVAD’s 94.94 is directly comparable to SHAR accuracy | rejected | [AVAD](https://ietresearch.onlinelibrary.wiley.com/doi/10.1049/ipr2.12720) is normal-only reconstruction VAD and reports mean frame-level ROC AUC across five datasets | No Reddit vote can make metrics comparable. |
| Dwivedi is exactly a 3-class task | qualified | [Primary article page](https://link.springer.com/article/10.1007/s11042-023-14445-7) confirms model/rate but accessible evidence reviewed here does not establish three classes | Remove the unsupported class-count assertion until the full paper is available. |
| Zaidi uses six activity categories | verified/qualified | [DOAJ record](https://doaj.org/article/ca9ab96ae7be482597d2354074a2d21d) and [proceedings copy](https://ieomsociety.org/proceedings/india2025/400.pdf); not local | Still not comparable to the UCF protocol. |
| DilateFormer uses 3×3 SWDA, dilations [1,2,3], early stages | verified | Local `DilateFormer_Multi-Scale_Dilated_Transformer_for_Visual_Recognition.pdf`, method and Table X | P3/P4 transfer remains a SHAR hypothesis, not a fact proved by Reddit or DilateFormer. |
| YOLO11 contains stock C2PSA at P3/P4 | rejected | [Official YOLO11 YAML](https://github.com/ultralytics/ultralytics/blob/main/ultralytics/cfg/models/11/yolo11.yaml) places one C2PSA after SPPF at P5/32 | Exact source inspection is decisive. |
| ASFF 8-channel→3-channel→softmax weight computation | verified | Local AF-YOLO PDF, pp. 6–7, citing original [ASFF](https://arxiv.org/abs/1911.09516) | No Reddit evidence needed for a printed architecture definition. AF-YOLO reuses rather than invents ASFF. |
| Gaussian ASFFH is necessarily beneficial | rejected pending ablation | No source establishes the proposed SHAR formula or benefit; original equation was underspecified | No relevant Reddit consensus. Retain only as a falsifiable prototype. |
| Slide Loss has one unambiguous exact formula and fixes rare-class imbalance | rejected | [YOLO-FaceV2 paper](https://arxiv.org/abs/2208.02019) and [upstream code](https://raw.githubusercontent.com/Krasjet-Yu/YOLO-FaceV2/master/utils/loss.py) disagree on the middle weight (`exp(1-μ)` versus `exp(μ)`); code uses batch/layer mean IoU clamped ≥0.2, no EMA. Local `2509.21696v1.pdf`, pp. 5–6 has no class-frequency term and worse Slide-only mAP. | Reddit is not evidence for the loss mechanism. Core Slide work is removed. |
| SEMSCNN is a copyable 2-D image classifier | rejected | [University of Essex accepted manuscript](https://repository.essex.ac.uk/39499/) confirms 1-D EEG/SSVEP temporal design | 2-D SHAR version must be called an adaptation and ablated. |
| Python `hash(filepath)` is stable across runs | rejected | [Python data model documentation](https://docs.python.org/3/reference/datamodel.html#object.__hash__) describes hash randomization | Use a cryptographic digest; no community vote required. |
| YOLO26 is the current official comparison candidate | verified | [Ultralytics model index](https://docs.ultralytics.com/models/) and [YOLO26 docs](https://docs.ultralytics.com/models/yolo26/) | Current-state claim must be rechecked at implementation freeze. |

## Local paper coverage

Every PDF in `papers/` was fully text-extracted and reviewed; formula/table pages central to ASFF, DilateFormer, and Slide Loss were also rendered for visual confirmation.

| Local file | Relevance to SHAR | Decision |
|---|---|---|
| `1-s2.0-S0031320323002674-main.pdf` | RareAnom | Keep as external/related work; verify media license before use. |
| `1-s2.0-S0167865523001897-main.pdf` | Multiscale attention/dilation for small defects | Related architectural context, not direct surveillance validation. |
| `1-s2.0-S0923596525001547-main.pdf` | Tiny-YOLO loss/features for shadow detection | Related detection/loss context; no direct task equivalence. |
| `2509.21696v1.pdf` | MS-YOLO with Slide Loss | Its printed paper-formula reproduction was visually verified; it does not resolve the upstream paper/code discrepancy. Old training-recipe claim rejected; negative Slide-only mAP noted. |
| `AF-YOLO_Asymptotic_Feature_Extraction_and_Fusion_for_Aerial_Object_Detection.pdf` | ASFF/PAFFN | ASFF computation verified; aerial topology not imported without object-scale evidence. |
| `A_Comprehensive_Review_for_Video_Anomaly_Detection_on_Videos.pdf` | Survey | Terminology/context only; primary papers govern numeric claims. |
| `Deep_Learning_for_Smart_Surveillance_Multi-Class_Detection_of_People_Weapons_and_Masks_using_YOLOv11.pdf` | YOLO11 surveillance application | Related work only; task/classes differ. |
| `DilateFormer_Multi-Scale_Dilated_Transformer_for_Visual_Recognition.pdf` | MSDA | Kernel/dilations/stage ablation verified; YOLO placement remains hypothesis. |
| `EBSCO-Metadata-07_13_2026.pdf` | Bibliographic metadata | Not implementation evidence. |
| `s10115-024-02122-6.pdf` | Human-activity-recognition review | Literature orientation only; follow cited primary sources for claims. |

## Missing primary files and watchlist

The local folder does not contain Dwivedi, Zaidi, AVAD, Ginseng-YOLO, SEMSCNN, original ASFF, or YOLO-FaceV2, and contains no JSON extractions. Do not write “full local read verified” for those sources.

- [VALU, ACL 2026](https://aclanthology.org/2026.acl-long.56/): paper is public; annotation release must be verified before dependency.
- [FS-UCF-Crime v0.1.0](https://zenodo.org/records/21336651): July 2026 record promises corrected train/test intervals, but says the complete package follows paper acceptance; watch, do not depend on it yet.
- [HIVAU-70K / HolmesVAU](https://github.com/pipixin321/HolmesVAU): candidate annotation overlay; verify ontology, files, and license before use.
- [Pistachio](https://pistachio-video.github.io/): synthetic robustness candidate only, never a replacement for real surveillance evaluation.
