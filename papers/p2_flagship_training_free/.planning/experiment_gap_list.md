# P2 Experiment Gap List

This is the work that must happen before P2 Results can be written.

## Blocking Result Gaps

| ID | Gap | Required Output | Notes |
|---|---|---|---|
| G1 | Final detector protocol decision: full-image, tiled, or fused. | Decision note plus metrics under `results/experimental/`. | F6b shows tiled is stronger, but seam/truncation handling remains open. Fusion may recover large objects while preserving small-object recall. |
| G2 | Tile-border duplicate/truncation quantification. | Report measuring seam-crossing duplicate contribution and whether seam-drop or fusion is required. | Current tiled precision loss partly comes from duplicate partial detections. |
| G3 | Operating-point sweep for YOLOv11x-OBB detector. | PR curves, confidence/NMS choice, final threshold policy. | Do not freeze paper around default confidence/NMS values. |
| G4 | Final YOLOv11x-OBB -> SAM cascade run on released AerialFuseCV GT. | Metrics + manifest under `results/experimental/p2_*`. | Must use final detector protocol and released reconciled masks. |
| G5 | GT-prompt SAM upper bound on final split. | Metrics for selected SAM model(s), probably box prompt primary. | Existing SAM benchmark is useful history but needs verification/rerun under final P2 protocol. |
| G6 | Mask R-CNN supervised baseline. | Training config, checkpoint manifest, validation metrics, per-class table. | F6 proved feasibility through torchvision in `P2_env`; full baseline is not done. |
| G7 | YOLOv11-seg supervised baseline. | Training config, checkpoint manifest, validation metrics, per-class table. | Needs AerialFuseCV segmentation-format preparation and frozen-evaluator compatibility. |
| G8 | Unified comparison table. | One table covering training-free cascade, Mask R-CNN, YOLOv11-seg, and upper-bound prompts. | Metrics must use identical split and evaluator. |
| G9 | Confidence filtering and PR curves. | Figures/tables for detector and cascade operating points. | Required by supervisor-scoped P2 plan. |
| G10 | Failure taxonomy. | Quantified failure categories with visual examples. | Should separate detector miss, detector FP, wrong class, poor prompt geometry, SAM mask leakage/underfit. |

## Implementation Gaps

| Area | Needed |
|---|---|
| Baseline API | Add or reuse an `InstanceSegmenter` path so supervised segmenters can emit predictions into the frozen evaluator. |
| Mask R-CNN training | Convert AerialFuseCV train/val to COCO, train torchvision Mask R-CNN in `P2_env`, export predictions in ArgusVision prediction format. |
| YOLOv11-seg training | Prepare segmentation labels, train/evaluate YOLOv11-seg, export masks and boxes into the frozen evaluator. |
| Tiled/fused inference | Ensure `argusvision.runtime.tiling.TiledDetector` supports final protocol, provenance, and reproducible configs. |
| PR tooling | Produce ranked precision-recall curves and operating-point tables without relying on a single fixed confidence threshold. |
| Runtime reporting | Capture wall-clock and per-image costs for full-image, tiled, cascade, and supervised baselines. |

## What Can Be Written Now

- Introduction need statement.
- Dataset/evaluation contract.
- Related-work posture and claim boundaries.
- Methods shell for the detector-to-segmenter cascade.
- Experimental design with pending result placeholders.
- Risks and limitations.

## What Must Wait

- Abstract result sentence.
- Final Results tables.
- Comparison against Mask R-CNN and YOLOv11-seg.
- PR curve conclusions.
- Claims about which protocol is best, until G1-G3 finish.
- Final submission-ready discussion, until supervised baselines are known.
