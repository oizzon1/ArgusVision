# F6 Mask R-CNN Windows Feasibility Report

**Task:** F6 Mask R-CNN path on Windows
**Worker:** Codex-Operator
**Branch:** `task/f6-maskrcnn-windows`
**Status:** in progress

## Objective

Establish a working Mask R-CNN training path on the Windows machine without
modifying `AV_env`. Primary path is MMDetection; fallback is
`torchvision.models.detection.maskrcnn`.

## Current Path

Selected path: **torchvision fallback**.

Reason:

- `P2_env` has torch `2.5.1+cu124`, CUDA, and torchvision `0.20.1+cu124`.
- `mmdet`, `mmcv`, and `mmengine` are not available in `P2_env`.
- The task objective is to establish a working Mask R-CNN path without
  destabilizing `AV_env`; torchvision provides that path immediately.
- No MMDetection install was attempted in `AV_env`. `P2_env` is disposable and
  can still be used for a later MMDetection attempt, but F6 is unblocked by the
  working torchvision path.

## Converter

`dataset/convert_aerialfusecv_to_coco.py` converts AerialFuseCV to COCO
instance JSON using:

- images from `dataset/AerialFuseCV/<split>/images`;
- HBB boxes from `pairs.jsonl`;
- category ids from `dataset_statistics.json`;
- binary masks extracted from RGB `instance_masks` using each pair's
  `instance_rgb`;
- COCO uncompressed RLE segmentation.

Smoke subset command:

```bash
/mnt/c/Windows/System32/cmd.exe /c "cd /d d:\Work\AV && conda run -n P2_env python dataset\convert_aerialfusecv_to_coco.py --dataset-root dataset\AerialFuseCV --split train --selection fewest-annotations --max-images 50 --output experiments\maskrcnn_setup\coco_smoke\train_50_fewest.json"
```

Smoke subset output:

- `experiments/maskrcnn_setup/coco_smoke/train_50_fewest.json`
- 50 train images
- 50 annotations

## Smoke Evidence

Smoke training command:

```bash
/mnt/c/Windows/System32/cmd.exe /c "cd /d d:\Work\AV && conda run -n P2_env python experiments\maskrcnn_setup\smoke_train_torchvision_maskrcnn.py --coco-json experiments\maskrcnn_setup\coco_smoke\train_50_fewest.json --dataset-root dataset\AerialFuseCV --iterations 50 --batch-size 1 --num-workers 0 --lr 0.0001 --grad-clip 1.0 --image-size 512 --min-mask-area 16 --output-log experiments\maskrcnn_setup\smoke_train_50iter.jsonl"
```

Result:

- completed 50 iterations on CUDA;
- no non-finite losses in the accepted run;
- first-10 average loss: 5.082584;
- last-10 average loss: 3.906363;
- min/max total loss: 2.616734 / 6.602014;
- final throughput sample: 2.007 iterations/sec;
- GPU sample at iteration 1: 2467 MiB used / 24564 MiB total / 15% utilization;
- GPU sample at iteration 50: 2606 MiB used / 24564 MiB total / 22% utilization.

Accepted smoke log:

- `experiments/maskrcnn_setup/smoke_train_50iter.jsonl`

One earlier attempt used too large a learning rate for this tiny random-init
smoke setup and produced a non-finite loss at iteration 29. The accepted run
uses lower LR, gradient clipping, and a minimum resized-mask area filter.

## Full-Training Estimate

Indicative only; not a paper claim.

The accepted smoke run uses a small ResNet-18 FPN Mask R-CNN at 512 px input
and reached about 2 iterations/sec with batch size 1. A full train split pass
under this lightweight smoke configuration would therefore be on the order of
minutes per epoch. A publication-quality Mask R-CNN configuration, larger
backbone, larger input scale, validation, checkpointing, and augmentation will
be slower; budget full supervised baseline work in days as roadmap v2.4 already
does.

## Decision

F6 has a working Windows Mask R-CNN path:

- environment: `P2_env`;
- implementation route: `torchvision.models.detection.maskrcnn`;
- data bridge: `dataset/convert_aerialfusecv_to_coco.py`;
- proof: 50-iteration CUDA smoke run with decreasing first-window to
  last-window average loss.

Recommended next F7 action after orchestrator review: build a proper training
script/config around the torchvision path, then run YOLOv11-seg and Mask R-CNN
baselines under the frozen evaluator.

---

**Storage note (2026-08-04, results/ restructure).** This directory moved from
`experiments/maskrcnn_setup/` to `results/experimental/f6_maskrcnn_setup/`; the
scripts that produced it moved to `experiments/baselines/maskrcnn/`. Evidence
that must stay in git — `pip_freeze.txt`, `probe_env.json`,
`smoke_train_50iter.jsonl` — now lives under `evidence/`. `coco_smoke/` is not
tracked: it is a 50-image COCO subset regenerable with
`dataset/convert_aerialfusecv_to_coco.py`.
