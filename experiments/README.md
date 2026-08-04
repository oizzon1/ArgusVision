# experiments/

Every experiment is a YAML config. This file is the index: what each one
measures, what it is for, and whether it can run today.

```
argusvision run experiments/configs/<group>/<config>.yaml
argusvision status --watch                    # from a second terminal
```

Results land in `results/experimental/<experiment>/<timestamp>_<sha>/`.

## The three groups

| Group | Question it answers |
|---|---|
| `configs/baselines/` | **What does one model do alone?** A detector by itself, or a supervised instance segmenter by itself. One model, one number. |
| `configs/argusvision/` | **What does the cascade do?** Detector → segmenter, the system this program is about. One config per model *combination*. |
| `configs/validation/` | **Does the code still agree with itself?** Port checks and protocol equivalence. Not science — no result here goes in a paper. |

## Naming

`<detector>__<segmenter>__<protocol>.yaml` — double underscore separates
stages, so a filename states the whole pipeline. A baseline has no segmenter
stage, so its second field is the dataset instead.

`_full` and `_tiled` name the **inference protocol**: whether the detector sees
whole images or overlapping 1024 px windows. It is in the filename because it
changes the numbers more than the model choice does (F6b: detector recall
0.607 → 0.852 at IoU 0.5).

## Index

### Baselines — one model alone

| Config | Model | Data | Protocol | Status |
|---|---|---|---|---|
| `baselines/yolo11x_obb__afcv_full.yaml` | YOLOv11x-OBB | AerialFuseCV val | full image | ✅ runs — the ablation |
| `baselines/yolo11x_obb__afcv_tiled.yaml` | YOLOv11x-OBB | AerialFuseCV val | tiled 1024/200 | ✅ runs — **the P2 detector protocol** |
| YOLO VBB baseline | YOLOv11x (axis-aligned) | DOTA VBB | either | ⛔ needs a VBB dataset loader — `DotaYoloObbSplit` reads oriented labels only |
| Mask R-CNN baseline | torchvision Mask R-CNN | AerialFuseCV val | tiled | ⛔ F7 — needs training, plus `InstanceSegmenter` protocol and `models/baselines/` |
| YOLOv11-seg baseline | YOLOv11x-seg | AerialFuseCV val | tiled | ⛔ F7 — same |

### ArgusVision — the cascade

| Config | Detector | Segmenter | Protocol | Status |
|---|---|---|---|---|
| `argusvision/yolo11x_obb__sam_vit_b__full.yaml` | YOLOv11x-OBB | SAM ViT-B | full image | ✅ runs |
| `argusvision/yolo11x_obb__sam_vit_b__tiled.yaml` | YOLOv11x-OBB | SAM ViT-B | tiled | ✅ runs — **P2 primary** |
| further combinations | any registered detector | any registered segmenter | either | P4 — the grid. Add a config per cell; no code changes needed |

### Validation — not science

| Config | Checks | Status |
|---|---|---|
| `validation/yolo11x_obb__dota_port_check.yaml` | New evaluator reproduces the legacy YOLO-OBB numbers on DOTA val | ✅ runs |

Three validation configs were removed on 2026-08-04 because the datasets they
pointed at (`AerialFuseCV_v1`, `AerialFuseCV_Refined`) were deleted as
superseded. Their runs are preserved in
`results/experimental/restructure_validation_*`, and the configs themselves are
in git history at commit `1eca0ec`. A config that cannot run is worse than no
config: it looks like an available experiment.

## Adding an experiment

Copy the nearest config, change what differs, run it. You should not need to
write code — if you do, the capability belongs in the package rather than in
the experiment (`documentation/PLATFORM_BOUNDARY.md`).

Config keys:

| Key | Meaning |
|---|---|
| `experiment` | Names the results directory. Keep it stable once results exist under it |
| `kind` | `detection` (detector only) or `pipeline` (detector → segmenter) |
| `dataset` | `type` + `path` (+ `split` for DOTA) |
| `detector` / `segmenter` | Registry names — `yolo11x-obb`, `sam-vit-b` |
| `tiling` | `enabled`, `tile_size`, `overlap`, `nms_iou`, `batch_size` |
| `iou_thresholds` / `iou_mode` | Frozen evaluator settings — change only with a reason |
| `max_images` | Cap for smoke runs. Also available as `--max-images` |

## Training scripts

`baselines/<model>/` holds the scripts that *train* a comparison model. They
are run by hand and are not imported by the platform — inference adapters for
those models belong in `argusvision/models/baselines/`, so that a baseline and
the cascade are scored through the same evaluator.

| Directory | Holds |
|---|---|
| `baselines/maskrcnn/` | torchvision Mask R-CNN environment probe and smoke-training script (F6). Evidence: `results/experimental/f6_maskrcnn_setup/` |
