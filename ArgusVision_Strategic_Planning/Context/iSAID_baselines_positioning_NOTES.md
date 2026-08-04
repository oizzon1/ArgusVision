# iSAID Baselines and ArgusVision Positioning Notes

**Created by ATHENA:** 2026-08-04  
**Trigger:** user asked whether existing iSAID-tested segmentation baselines
kill the ArgusVision work and how to justify the need.

## Short Answer

Existing iSAID segmentation work does **not** kill ArgusVision. It prevents
weak framing.

ArgusVision must not claim:

- "first to segment iSAID";
- "first SAM use in remote sensing";
- "iSAID lacks segmentation baselines";
- "YOLO-seg / Mask R-CNN / Mask2Former have not been tried";
- "our method is the first aerial instance segmentation system."

The defensible claim is narrower and stronger:

> Existing work trains, adapts, or evaluates segmentation models for
> remote-sensing masks. ArgusVision studies whether aerial object detectors
> and their geometry can serve as a practical interface to promptable
> foundation segmentation, under a paired detection-segmentation benchmark
> that makes this question measurable.

## What Existing iSAID Work Already Answers

### Supervised Instance Segmentation

Mask R-CNN, PANet, Mask2Former, and YOLO-seg style models answer the classic
supervised question:

> If mask annotations are available, can an end-to-end instance segmenter learn
> the iSAID mask task?

These are necessary baselines for ArgusVision, not threats. They define the
expected reviewer comparison: "Why not just train a segmentation model?"

Primary anchors:

- iSAID original benchmark: Mask R-CNN and PANet on aerial instance
  segmentation. Source: https://paperswithcode.com/paper/isaid-a-large-scale-dataset-for-instance
- DiffuPrompter-style iSAID comparisons include Mask R-CNN, Cascade R-CNN, and
  Mask2Former. Source: https://www.mdpi.com/2072-4292/16/11/2004
- Recent YOLOv11-seg/iSAID evidence exists, but is newer and less canonical
  than the Mask R-CNN/PANet lineage. Sources:
  https://www.kaggle.com/datasets/redzapdos123/isaid-dataset-yolo11-seg-format
  and https://www.mdpi.com/2227-7390/13/19/3079

### SAM and SAM-Adaptation in Remote Sensing

SAM-RSIS, Causal-SAM, ROS-SAM/HQ-SAM-style work, AerOSeg, and related methods
show that SAM or SAM-derived features are active in remote sensing. This means
ArgusVision must not frame the area as empty.

The distinction is task contract:

- many papers adapt SAM, fine-tune SAM components, use SAM features, or produce
  semantic/open-vocabulary masks;
- ArgusVision evaluates a training-free detector-to-prompted-segmenter
  instance pipeline, where the detector supplies the object prompt and the
  evaluator tracks object-level detection and mask quality together.

Primary anchors:

- SAM-RSIS: https://doi.org/10.1109/TGRS.2024.3460085
- Causal-SAM: https://www.sciencedirect.com/science/article/pii/S0950705126006416
- AerOSeg local review:
  `ArgusVision_Strategic_Planning/Context/2504.09203v1_AerOSeg_REVIEW.md`

### Open-Vocabulary Semantic Segmentation

AerOSeg, OVRS/OVRSISBench, SegEarth-OV, and related work answer a different
semantic/open-vocabulary question:

> Can a model assign remote-sensing semantic classes from text or open
> vocabulary supervision?

This can be cited as related work, especially in P4, but it is not a direct P2
baseline unless the benchmark is deliberately broadened beyond instance-level
detector-to-segmenter systems.

Primary anchors:

- SegEarth-OV/iSAID: https://paperswithcode.com/paper/segearth-ov-towards-traning-free-open
- OVRSISBench-style work: https://ojs.aaai.org/index.php/AAAI/article/view/37521

## ArgusVision Need Statement

The practical gap is not "remote-sensing segmentation exists?" It does.

The gap is:

> Many aerial datasets, operational archives, and detector pipelines provide
> boxes, often oriented boxes, but not instance masks. A training-free
> detector-to-prompted-segmenter pipeline could convert detector outputs into
> masks without training a segmentation model, but this needs object-level
> paired detection-segmentation data and a rigorous evaluator.

This is why AerialFuseCV is needed:

- DOTA supplies oriented detection geometry.
- iSAID supplies instance masks on overlapping imagery.
- AerialFuseCV defines the one-to-one object contract between those sources.
- The release records pairing metadata, discard accounting, class identity,
  and reproducible reconstruction.
- The evaluation can measure both detector failure and mask quality instead of
  collapsing the problem into semantic mIoU.

This is why P2 is needed:

- It compares the training-free detector-to-SAM path against supervised
  instance-segmentation baselines.
- It asks what is gained or lost when masks are scarce but boxes/detectors
  exist.
- It exposes the detector bottleneck, prompt quality, confidence filtering, and
  geometry mismatch instead of hiding them.
- If supervised baselines win, the paper is still valid: the contribution is
  the quantified tradeoff and failure analysis, not a guaranteed win claim.

## Preferred Framing

Use this phrasing in papers and supervisor discussions:

> We do not propose AerialFuseCV because iSAID lacks segmentation baselines.
> We propose it because detector-to-segmenter systems require paired
> object-level detection and mask annotations, explicit pairing metadata, and
> evaluation that separates detector error from segmentation error. This is the
> contract needed to test whether promptable segmentation can extend existing
> aerial detection pipelines when dense mask training is unavailable or
> undesirable.

## Roadmap Impact

- No roadmap revision required.
- P2 baselines remain Mask R-CNN and YOLOv11-seg, as decided with the
  supervisor.
- PANet and Mask2Former are useful related-work anchors and possible P4
  expansion baselines.
- SAM-RSIS/Causal-SAM/ROS-SAM/HQ-SAM-type work strengthens the need for
  careful positioning around promptable segmentation and remote-sensing domain
  adaptation.
- AerOSeg/OVRS/SegEarth-OV remain context baselines, not direct P2 baselines,
  unless P4 explicitly expands into semantic/open-vocabulary segmentation.
