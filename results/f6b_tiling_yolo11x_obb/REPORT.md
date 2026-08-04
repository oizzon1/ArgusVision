# F6b Tiling Report

## Protocol

- Dataset: `D:\Work\AV\dataset\AerialFuseCV\val`
- Weights: `D:\Work\AV\model_checkpoints\YOLO\OBB\yolo11x-obb.pt`
- Full-image mode: one YOLOv11x-OBB prediction per full validation image.
- Tiled mode: 1024x1024 windows, 200 px overlap.
- Tile detections are mapped back to full-image coordinates before evaluation.
- Cross-tile de-duplication: class-wise OpenCV rotated NMS at IoU 0.5.
- Evaluator: frozen `DetectionEvaluator`, `iou_mode=auto`, thresholds [0.1, 0.3, 0.5].

## Detection Metrics

| Mode | IoU | Micro P | Micro R | Micro F1 | Macro F1 | Mean AP |
|---|---:|---:|---:|---:|---:|---:|
| full_image | 0.1 | 0.8811 | 0.6268 | 0.7325 | 0.6269 | 0.5140 |
| full_image | 0.3 | 0.8755 | 0.6228 | 0.7279 | 0.6209 | 0.5081 |
| full_image | 0.5 | 0.8525 | 0.6065 | 0.7087 | 0.6022 | 0.4869 |
| tiled | 0.1 | 0.7506 | 0.8639 | 0.8033 | 0.7013 | 0.7016 |
| tiled | 0.3 | 0.7488 | 0.8619 | 0.8014 | 0.6973 | 0.6955 |
| tiled | 0.5 | 0.7399 | 0.8516 | 0.7918 | 0.6801 | 0.6687 |

## Scale-Sensitive Recall

| Mode | IoU | small-vehicle | ship | large-vehicle | plane |
|---|---:|---:|---:|---:|---:|
| full_image | 0.1 | 0.5377 | 0.6225 | 0.8215 | 0.6713 |
| full_image | 0.3 | 0.5373 | 0.6173 | 0.8213 | 0.6693 |
| full_image | 0.5 | 0.5302 | 0.5971 | 0.8169 | 0.6642 |
| tiled | 0.1 | 0.7961 | 0.9405 | 0.8571 | 0.9346 |
| tiled | 0.3 | 0.7961 | 0.9395 | 0.8561 | 0.9346 |
| tiled | 0.5 | 0.7904 | 0.9358 | 0.8490 | 0.9290 |

## Operational Statistics

| Mode | Mean tiles/image | Raw detections | Final detections | Runtime/image (s) |
|---|---:|---:|---:|---:|
| full_image | 1.00 | 20013 | 20013 | 0.820 |
| tiled | 11.50 | 59136 | 32379 | 1.880 |

## Read

Tiling explains a large share of the detector gap. At IoU 0.5, micro F1 rises
from 0.7087 to 0.7918, macro F1 rises from 0.6022 to 0.6801, and mean AP rises
from 0.4869 to 0.6687. The recall gain is exactly where the scale hypothesis
predicts: small-vehicle recall rises from 0.5302 to 0.7904, ship from 0.5971 to
0.9358, and plane from 0.6642 to 0.9290 at IoU 0.5. Large-vehicle improves only
modestly, from 0.8169 to 0.8490.

The cost is precision and runtime. Tiling increases final detections from
20,013 to 32,379 after NMS, dropping IoU-0.5 micro precision from 0.8525 to
0.7399 while still improving F1 because recall rises more. Runtime increases
from 0.820 s/image to 1.880 s/image on this run.

Recommendation: tiled inference should become P2's primary YOLOv11x-OBB
detection protocol for DOTA-pretrained detector prompts, because it evaluates
the model at the scale it was trained for and materially improves AP/F1 without
changing the evaluator. Keep full-image inference as an ablation and an
operational-speed reference. Before paper use, F8 should tune confidence/NMS
through PR curves rather than treating conf=0.25 and NMS=0.5 as final.

## Artifacts

- Metrics: `D:\Work\AV\.worktrees\f6b\results\f6b_tiling_yolo11x_obb\20260804_105739_207e1f0\metrics.json`
- Manifest: `D:\Work\AV\.worktrees\f6b\results\f6b_tiling_yolo11x_obb\20260804_105739_207e1f0\manifest.json`

---

## Status after the platform move (2026-08-04)

The standalone runner that produced this report has been removed. Tiling is now
a platform capability — `argusvision.runtime.tiling.TiledDetector` — and the
comparison is reproduced from configs rather than from a script:

```
argusvision run experiments/configs/f6b_detection_yolo11x_obb_full.yaml
argusvision run experiments/configs/f6b_detection_yolo11x_obb_tiled.yaml
```

The original 479-line runner is preserved in git history at commit `95e3aa9`
(`experiments/tiling/yolo11x_obb_full_vs_tiled.py`). It was removed rather than
kept because it carried its own copies of the tile-origin, coordinate-shift and
rotated-NMS logic; leaving a second implementation in the tree is how two parts
of this codebase came to disagree about what "mAP" meant.

**Open defect, carried to F8.** There is no tile-border truncation handling. An
object crossing a seam produces two partial detections whose mutual IoU is near
zero, so NMS keeps both and the object is counted twice. This inflates false
positives and is part of why tiled precision (0.740) sits below full-image
precision (0.853) at IoU 0.5. It must be quantified before any P2 number is
final. It cannot reverse the finding: recall and AP gains of this size are not
an artefact of duplicate boxes, which only ever cost precision.
