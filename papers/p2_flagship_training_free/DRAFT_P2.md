# Cascade Reliability for Training-Free Aerial Detection-to-Segmentation

> Working draft scaffold, started 2026-08-24. Every result placeholder must be filled from `results/`; the MSc thesis is not a source.

## Abstract

`[WRITE AFTER FINAL RESULTS]`

Many aerial workflows are rich in object boxes but poor in instance masks. This paper evaluates whether a pretrained aerial detector can act as an object interface to promptable segmentation, and where that training-free cascade fails compared with supervised instance segmentation. We use AerialFuseCV, a paired DOTA-v1.0/iSAID object-level benchmark, to evaluate detection and mask quality on the same physical objects. The final abstract must report the selected detector protocol, the cascade result, supervised baseline results, and the main failure mode only after F7-F8 are complete.

## 1. Introduction

### Motivation

Remote-sensing annotation is often asymmetric. Detection datasets, operational archives, and trained detectors commonly describe objects with boxes, including oriented boxes, while dense instance masks remain more expensive to produce and less widely available. Yet many downstream tasks need object extent rather than only object presence: mapping vehicles, ports, storage tanks, bridges, sports facilities, and damaged infrastructure often requires a shape that can be measured, filtered, or fused with other geospatial layers.

Promptable segmentation suggests a practical bridge. If a detector can localise an object and provide its geometry as a prompt, a foundation segmenter may recover an instance mask without training a segmentation model on the target dataset. This is appealing precisely in the setting where masks are scarce. It also creates a cascade whose failure modes are easy to hide: the detector can miss the object, localise it poorly, assign the wrong class, or produce a prompt at the wrong scale before the segmenter ever receives a chance to succeed.

### Gap

The question is not whether remote-sensing segmentation exists. Supervised aerial instance segmentation and SAM-derived remote-sensing methods already provide strong reference points. The unresolved question is narrower: when a workflow already has detectors or boxes but not mask supervision, how reliable is a training-free detector-to-segmenter cascade, and what is lost relative to supervised instance segmentation?

Answering that question needs more than a segmentation benchmark. A detector-to-segmenter system needs object-level pairs: the box that localises an object and the mask of that same physical object. It also needs an evaluator that distinguishes detection failure from mask failure. A single mask score can make a missed object, a false detection, and a poor segmenter output look like the same error; for cascade reliability, they are different mechanisms.

### Contribution

This paper contributes:

1. A cascade-reliability evaluation on AerialFuseCV, using paired object-level detection and segmentation ground truth.
2. A training-free detector-to-segmenter baseline built from YOLOv11x-OBB prompts and SAM masks.
3. Supervised Mask R-CNN and YOLOv11-seg reference baselines on the same dataset and split.
4. An operating-point and failure analysis covering detector scale handling, confidence filtering, PR curves, and mask quality.

The contribution is therefore evaluative rather than architectural. We do not claim that combining a detector with SAM is itself new. We test when this already-plausible pattern works, where it breaks, and what supervised training still buys on the same paired objects.

## 2. Related Work

### Aerial instance segmentation

Discuss iSAID and supervised instance segmentation baselines. Use `Context/iSAID_baselines_positioning_NOTES.md` to avoid weak claims.

### Promptable segmentation in remote sensing

Discuss SAM adaptation, learned prompts, and open-vocabulary segmentation. Separate detector-prompted instance cascades from semantic/open-vocabulary methods such as AerOSeg.

### Detector-to-segmenter pipelines

Frame YOLO+SAM-style systems as existing engineering patterns. The novelty here is not the recipe; it is the paired contract, evaluator, and failure science.

## 3. Dataset and Evaluation Contract

### AerialFuseCV

AerialFuseCV pairs DOTA-v1.0 oriented boxes with iSAID instance masks over shared imagery. The corrected build contains 125,722 paired objects and 1,862 retained images, with all experimental claims sourced from the released build artefacts.

`[INSERT ZENODO DOI AFTER RELEASE]`

The pairs-only scope is deliberate. DOTA remains the correct source for detector-only evaluation, and iSAID remains the correct source for segmentation-only evaluation. AerialFuseCV serves the unified case: evaluating a system that takes an object detection interface and returns an object mask. Objects without both annotation types are logged rather than silently retained, because keeping unpaired annotations would make it possible to score a correct prediction against missing ground truth.

### Reconciled masks

The released mask for each object is the matched iSAID instance clipped to the DOTA oriented box. This makes the mask consistent with the object extent supplied to a box-prompted segmenter and prevents pixels from neighbouring instances entering the ground truth.

This definition matters for P2 because the prompt is itself a box-derived object extent. Scoring a box-prompted method against pixels outside that extent would penalise it for regions the prompt did not delimit. Conversely, deriving masks from class-coloured semantic regions can admit neighbouring objects in dense scenes. Starting from the matched iSAID instance and clipping it to the DOTA oriented box makes the evaluation target physically tied to one object and geometrically tied to the prompt.

### Evaluator

The evaluator reports detection counts and ranked AP separately from segmentation quality. Mask quality is reported both for true-positive detections and GT-anchored over all ground-truth objects, so detector misses remain visible.

The two mask summaries answer different questions. TP-only mask quality asks how good the segmenter is after the detector has already succeeded. GT-anchored mask quality asks how much usable mask coverage the whole cascade delivers over the dataset. The gap between them is the detector bottleneck.

## 4. Methods

### Training-free cascade

Primary candidate:

1. YOLOv11x-OBB detects aerial objects.
2. Detector geometry is converted into prompts.
3. SAM predicts object masks.
4. Predictions are evaluated against AerialFuseCV paired objects.

The detector protocol is not final. F6b supports tiled inference as primary, with full-image inference as an ablation, but seam/fusion and operating-point work must finish first.

The detector stage is expected to dominate cascade reliability. A missed object produces no prompt and therefore no mask, regardless of segmenter quality. Poor localisation changes the prompt geometry, which can bound or distort the segmenter's output. The detector protocol is therefore treated as part of the method rather than as a replaceable pre-processing detail.

### Supervised baselines

Mask R-CNN:

- implementation path: torchvision fallback in `P2_env`;
- COCO conversion path exists;
- full training/evaluation pending.

YOLOv11-seg:

- required by supervisor-scoped P2 plan;
- training/evaluation pending.

Both supervised baselines must be evaluated on the same AerialFuseCV split and through the same reporting stack wherever possible. Their role is not to be easy targets. They define the supervised ceiling under mask availability and make the training-free tradeoff measurable.

### Operating-point analysis

The paper will not rely on one arbitrary confidence threshold. F8 must produce PR curves and the selected operating point for detector and cascade comparisons.

Operating point is central because the detector produces prompts, not just labels. Lowering confidence may recover missed objects but also sends more false prompts to the segmenter, increasing runtime and false mask output. Raising confidence can improve precision while starving the segmenter of objects. P2 should report the curve, then justify the chosen point.

## 5. Experiments

### Data splits

Use the AerialFuseCV train/val split from the released build. Report all source and split details from the Zenodo artefacts and `results/`.

### Experiment matrix

| Experiment | Status |
|---|---|
| YOLOv11x-OBB full-image detector ablation | Existing F6b evidence; final paper use pending protocol cleanup. |
| YOLOv11x-OBB tiled detector protocol | Existing F6b evidence; seam/fusion work pending. |
| YOLOv11x-OBB -> SAM cascade | Existing baseline anchor; final rerun pending. |
| GT-prompt SAM upper bound | Existing benchmark candidate; verify/rerun pending. |
| Mask R-CNN supervised baseline | Feasibility done; full run pending. |
| YOLOv11-seg supervised baseline | Pending. |
| Confidence filtering and PR curves | Pending. |

## 6. Results

`[LOCKED UNTIL F7-F8 RESULTS EXIST]`

Required tables:

- detector protocol table: full vs tiled vs fused if used;
- cascade table: detector metrics plus TP-only and GT-anchored mask metrics;
- supervised baseline comparison;
- per-class failure table;
- runtime table;
- PR/operating-point figure.

## 7. Discussion

Discuss the tradeoff: training-free segmentation avoids mask training but inherits detector recall, scale, and prompt geometry limits. If supervised baselines outperform the cascade, the paper still answers the operational question by quantifying the price paid for avoiding mask supervision.

## 8. Limitations

- AerialFuseCV is pairs-only by design; absolute detector precision belongs on DOTA, segmentation-only quality belongs on iSAID.
- Source datasets impose academic/non-commercial terms; the release is a reproducibility package plus derived correspondence.
- Tiled inference needs seam/truncation handling before final claims.
- Baseline coverage is limited to Mask R-CNN and YOLOv11-seg for P2; broader detector x segmenter grids belong to P4.

## 9. Conclusion

`[WRITE AFTER FINAL RESULTS]`
