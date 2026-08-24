# P2 Argument Map

## One-Sentence Claim

Aerial object detectors can be used as a training-free interface to promptable segmentation, but the usefulness of that cascade depends less on the segmenter alone than on detector recall, scale handling, prompt geometry, and operating-point choice.

## Main Contribution Stack

1. **Benchmark contract:** AerialFuseCV supplies one-to-one object pairs, so detection and mask quality can be measured on the same physical object.
2. **Evaluator:** the frozen ArgusVision evaluator reports detector TP/FP/FN, ranked AP, TP-only mask quality, and GT-anchored mask quality rather than collapsing missed detections into an opaque mask score.
3. **Training-free cascade:** YOLOv11x-OBB detections prompt SAM without mask training on AerialFuseCV.
4. **Supervised reference points:** Mask R-CNN and YOLOv11-seg show what supervised instance segmentation buys when masks are available.
5. **Reliability analysis:** confidence filtering, PR curves, tiled/full/fused detector protocols, and failure taxonomy explain where the cascade breaks.

## Paper Thesis

The paper should not promise that the training-free cascade beats supervised baselines. The durable thesis is:

> When dense masks are scarce but aerial detector assets exist, a training-free detector-to-segmenter cascade can be operationally useful, provided its detector bottleneck and prompt-induced failure modes are measured explicitly. AerialFuseCV makes that measurement possible.

If supervised baselines win on absolute scores, the paper still stands because it quantifies the cost of avoiding segmentation training.

## Required Comparisons

| Comparison | Purpose | Status |
|---|---|---|
| GT-box prompt SAM vs detector-prompted SAM | Separates segmenter ceiling from detector bottleneck | Existing SAM benchmark is available, but rerun/verification on final AerialFuseCV split is required before final prose. |
| YOLOv11x-OBB full-image vs tiled | Shows scale sensitivity and selects primary detector protocol | F6b exists; seam/fusion defect remains open. |
| Training-free cascade vs Mask R-CNN | Classic supervised instance segmentation baseline | Feasibility done; full training/evaluation pending. |
| Training-free cascade vs YOLOv11-seg | Same-family supervised segmentation baseline | Pending. |
| Confidence filtering / PR curves | Avoids one arbitrary operating point | Pending. |
| Per-class failure analysis | Explains the system, not just the aggregate score | Partly available from detector/SAM results; final analysis pending new runs. |

## Hostile-Reviewer Guardrails

- Do not claim "first SAM in remote sensing."
- Do not claim "first iSAID segmentation."
- Do not claim "YOLO+SAM is novel."
- Do not claim VBB-vs-OBB proves representation superiority; the domain/training confound remains parked.
- Do not cite the MSc thesis for a number.
- Do not use F6 smoke-training losses as performance evidence. They prove feasibility only.
- Do not use F6b tiled results as final paper results until seam/truncation and operating point are handled.

## Section Logic

1. **Introduction:** box-rich, mask-poor aerial workflows; need for detect-to-segment evaluation.
2. **Related Work:** supervised aerial instance segmentation; SAM/adapted SAM in remote sensing; detector-to-segmenter pipelines; benchmark/evaluation gaps.
3. **Dataset and Contract:** AerialFuseCV as the paired benchmark; DOI placeholder until release.
4. **Methods:** detector protocols, prompt generation, SAM configuration, supervised baselines, evaluator.
5. **Experiments:** operating-point design, full/tiled/fused detector protocols, baseline training details.
6. **Results:** detector bottleneck, mask quality, supervised comparison, PR curves, per-class failures.
7. **Discussion:** when training-free is useful, when supervised wins, annotation protocol implications.
8. **Limitations:** pairs-only scope, source-license constraints, tile seams, model family coverage.
