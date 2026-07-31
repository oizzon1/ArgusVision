"""Generic evaluation driver: YAML config in -> results/<experiment>/<run_id>/.

Usage (from repo root, in AV_env):
    python experiments/run_evaluation.py experiments/configs/<config>.yaml

Two kinds:
  kind: detection  — detector only, DetectionEvaluator
  kind: pipeline   — detector -> SAM, DetectionEvaluator + SegmentationEvaluator

Every run writes manifest.json (git SHA, config, env) before inference starts
and metrics.json when done. No manifest, no number.
"""

import argparse
import sys
import time
from typing import Dict, List

import numpy as np
import yaml
from tqdm import tqdm

from argusvision.data.aerialfusecv import AerialFuseCVSplit
from argusvision.data.dota import DotaYoloObbSplit
from argusvision.evaluation import (
    DetectionEvaluator,
    SegmentationEvaluator,
    create_run_dir,
    write_metrics,
    write_run_manifest,
)
from argusvision.models.registry import create_detector, create_segmenter
from argusvision.pipeline.core import DetectionSegmentationPipeline


def load_config(path: str) -> Dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_dataset(cfg: Dict):
    dtype = cfg["dataset"]["type"]
    if dtype == "aerialfusecv":
        return AerialFuseCVSplit(cfg["dataset"]["path"])
    if dtype == "dota_yolo_obb":
        return DotaYoloObbSplit(cfg["dataset"]["path"], cfg["dataset"].get("split", "val"))
    raise ValueError(f"unknown dataset type {dtype!r}")


def run_detection(cfg: Dict, run_dir) -> Dict:
    dataset = build_dataset(cfg)
    detector = create_detector(
        cfg["detector"]["name"],
        conf_threshold=cfg["detector"].get("conf_threshold", 0.25),
    )
    evaluator = DetectionEvaluator(
        iou_thresholds=tuple(cfg.get("iou_thresholds", (0.1, 0.3, 0.5))),
        iou_mode=cfg.get("iou_mode", "auto"),
    )
    times: List[float] = []
    ids = dataset.image_ids[: cfg.get("max_images") or len(dataset.image_ids)]
    for image_id in tqdm(ids, desc=cfg["experiment"], unit="img", ncols=90):
        image = dataset.load_image(image_id)
        h, w = image.shape[:2]
        if isinstance(dataset, DotaYoloObbSplit):
            gts = dataset.load_ground_truth(image_id, w, h)
        else:
            gts = dataset.load_ground_truth(image_id)
        detections = detector.predict(image)
        times.append(detector.last_inference_ms)
        evaluator.add_image(detections, gts)

    metrics = evaluator.summarize()
    metrics["timing"] = {"avg_inference_ms": float(np.mean(times)) if times else 0.0}
    return metrics


def run_pipeline(cfg: Dict, run_dir) -> Dict:
    dataset = build_dataset(cfg)
    if not isinstance(dataset, AerialFuseCVSplit):
        raise ValueError("pipeline evaluation needs an aerialfusecv dataset (GT masks)")

    detector = create_detector(
        cfg["detector"]["name"],
        conf_threshold=cfg["detector"].get("conf_threshold", 0.25),
    )
    segmenter = create_segmenter(cfg["segmenter"]["name"])
    pipeline = DetectionSegmentationPipeline(detector, segmenter)

    det_eval = DetectionEvaluator(
        iou_thresholds=tuple(cfg.get("iou_thresholds", (0.1, 0.3, 0.5))),
        iou_mode=cfg.get("iou_mode", "auto"),
    )
    seg_eval = SegmentationEvaluator()
    seg_threshold = float(cfg.get("seg_match_threshold", 0.1))
    timings: List[Dict[str, float]] = []

    ids = dataset.image_ids[: cfg.get("max_images") or len(dataset.image_ids)]
    for image_id in tqdm(ids, desc=cfg["experiment"], unit="img", ncols=90):
        image = dataset.load_image(image_id)
        gts = dataset.load_ground_truth(image_id)
        gt_masks = dataset.ground_truth_masks(image_id, gts)

        result = pipeline.run(image)
        timings.append(result.timing_ms)

        merged = det_eval.add_image(result.detections, gts)
        match = merged[seg_threshold]
        for pred_i, gt_j, _ in match.matches:
            seg_eval.add_pair(gts[gt_j].class_id, result.masks[pred_i].mask,
                              gt_masks[gt_j])
        for gt_j in match.unmatched_gt:
            seg_eval.add_missed_gt(gts[gt_j].class_id)

    metrics = {
        "detection": det_eval.summarize(),
        "segmentation": seg_eval.summarize(),
        "seg_match_threshold": seg_threshold,
        "timing": {
            k: float(np.mean([t[k] for t in timings])) if timings else 0.0
            for k in ("detection_ms", "segmentation_ms", "total_ms")
        },
    }
    return metrics


def main() -> int:
    parser = argparse.ArgumentParser(description="ArgusVision generic evaluation driver")
    parser.add_argument("config", help="path to YAML experiment config")
    args = parser.parse_args()

    cfg = load_config(args.config)
    run_dir = create_run_dir(cfg["experiment"])
    write_run_manifest(run_dir, cfg["experiment"], cfg)
    print(f"[run] {cfg['experiment']} -> {run_dir}")

    t0 = time.time()
    kind = cfg.get("kind", "detection")
    if kind == "detection":
        metrics = run_detection(cfg, run_dir)
    elif kind == "pipeline":
        metrics = run_pipeline(cfg, run_dir)
    else:
        raise ValueError(f"unknown kind {kind!r}")
    metrics["wall_time_s"] = time.time() - t0

    path = write_metrics(run_dir, metrics)
    print(f"[done] metrics: {path} ({metrics['wall_time_s']:.0f}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
