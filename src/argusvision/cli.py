"""ArgusVision command line.

    argusvision run experiments/configs/<config>.yaml
    argusvision status [--experiment NAME] [--watch]
    argusvision version

`run` is the single entry point for every experiment: config in, one run
directory out, containing `manifest.json` (git SHA, config, environment) before
inference starts, `status.json` throughout, and `metrics.json` at the end.
No manifest, no number.

Two kinds of run:
  kind: detection  — detector only, DetectionEvaluator
  kind: pipeline   - detector -> segmenter, DetectionEvaluator + SegmentationEvaluator

Optional `tiling:` block on either kind wraps the detector in
`runtime.tiling.TiledDetector`. Detections are always scored in full-image
coordinates.

`status` is meant for a *second* terminal: it reads the heartbeat of a run in
progress without touching the process producing it.
"""

import argparse
import json
import platform
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

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
from argusvision.runtime.banner import (
    C,
    print_banner,
    print_kv,
    print_result_table,
    print_section,
    print_status,
    glyph,
)
from argusvision.runtime.status import RunStatus, latest_run_dir, read_status
from argusvision.runtime.tiling import maybe_tile

DEFAULT_RESULTS_ROOT = Path("results/experimental")


# --------------------------------------------------------------------------
# config / dataset
# --------------------------------------------------------------------------


def load_config(path: str) -> Dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_dataset(cfg: Dict):
    dtype = cfg["dataset"]["type"]
    if dtype == "aerialfusecv":
        return AerialFuseCVSplit(cfg["dataset"]["path"])
    if dtype == "dota_yolo_obb":
        return DotaYoloObbSplit(
            cfg["dataset"]["path"], cfg["dataset"].get("split", "val")
        )
    raise ValueError(f"unknown dataset type {dtype!r}")


def build_detector(cfg: Dict):
    """Detector from config, wrapped for tiling if the config asks for it."""
    detector = create_detector(
        cfg["detector"]["name"],
        conf_threshold=cfg["detector"].get("conf_threshold", 0.25),
    )
    return maybe_tile(detector, cfg.get("tiling"))


def _environment() -> Dict[str, object]:
    env: Dict[str, object] = {
        "python": platform.python_version(),
        "platform": platform.platform(),
    }
    try:
        import torch

        env["torch"] = torch.__version__
        env["cuda_available"] = bool(torch.cuda.is_available())
        if torch.cuda.is_available():
            env["gpu"] = torch.cuda.get_device_name(0)
    except Exception:
        env["torch"] = "not available"
    return env


def _banner_fields(cfg: Dict, run_dir: Path, dataset, env: Dict) -> Dict[str, object]:
    tiling = cfg.get("tiling") or {}
    fields: Dict[str, object] = {
        "experiment": cfg["experiment"],
        "kind": cfg.get("kind", "detection"),
        "dataset": f"{cfg['dataset']['type']} {glyph('mid')} {cfg['dataset']['path']}",
        "images": len(dataset.image_ids),
        "detector": cfg["detector"]["name"],
    }
    if cfg.get("kind") == "pipeline":
        fields["segmenter"] = cfg["segmenter"]["name"]
    if tiling.get("enabled"):
        fields["tiling"] = (
            f"{C.magenta}on{C.reset} {glyph('mid')} {tiling.get('tile_size', 1024)}px "
            f"/ {tiling.get('overlap', 200)}px overlap "
            f"/ NMS IoU {tiling.get('nms_iou', 0.5)}"
        )
    else:
        fields["tiling"] = f"{C.dim}off (full-image inference){C.reset}"
    fields["iou thresholds"] = cfg.get("iou_thresholds", [0.1, 0.3, 0.5])
    fields["device"] = env.get("gpu", "cpu")
    fields["run dir"] = str(run_dir)
    return fields


# --------------------------------------------------------------------------
# run kinds
# --------------------------------------------------------------------------


def run_detection(cfg: Dict, run_dir: Path, status: RunStatus) -> Dict:
    dataset = build_dataset(cfg)
    detector = build_detector(cfg)
    evaluator = DetectionEvaluator(
        iou_thresholds=tuple(cfg.get("iou_thresholds", (0.1, 0.3, 0.5))),
        iou_mode=cfg.get("iou_mode", "auto"),
    )

    times: List[float] = []
    tile_counts: List[int] = []
    ids = dataset.image_ids[: cfg.get("max_images") or len(dataset.image_ids)]
    status.set_phase("detection")

    for image_id in tqdm(ids, desc=cfg["experiment"], unit="img", ncols=90):
        image = dataset.load_image(image_id)
        h, w = image.shape[:2]
        if isinstance(dataset, DotaYoloObbSplit):
            gts = dataset.load_ground_truth(image_id, w, h)
        else:
            gts = dataset.load_ground_truth(image_id)

        detections = detector.predict(image)
        inner = getattr(detector, "detector", detector)
        times.append(getattr(inner, "last_inference_ms", 0.0))
        if getattr(detector, "last_stats", None):
            tile_counts.append(detector.last_stats["num_tiles"])
        evaluator.add_image(detections, gts)
        status.advance()

    metrics = evaluator.summarize()
    metrics["timing"] = {"avg_inference_ms": float(np.mean(times)) if times else 0.0}
    if tile_counts:
        metrics["tiling"] = {"mean_tiles_per_image": float(np.mean(tile_counts))}
    return metrics


def run_pipeline(cfg: Dict, run_dir: Path, status: RunStatus) -> Dict:
    dataset = build_dataset(cfg)
    if not isinstance(dataset, AerialFuseCVSplit):
        raise ValueError("pipeline evaluation needs an aerialfusecv dataset (GT masks)")

    detector = build_detector(cfg)
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
    status.set_phase("detect " + glyph("arrow") + " segment")

    for image_id in tqdm(ids, desc=cfg["experiment"], unit="img", ncols=90):
        image = dataset.load_image(image_id)
        gts = dataset.load_ground_truth(image_id)
        gt_masks = dataset.ground_truth_masks(image_id, gts)

        result = pipeline.run(image)
        timings.append(result.timing_ms)

        merged = det_eval.add_image(result.detections, gts)
        match = merged[seg_threshold]
        for pred_i, gt_j, _ in match.matches:
            seg_eval.add_pair(
                gts[gt_j].class_id, result.masks[pred_i].mask, gt_masks[gt_j]
            )
        for gt_j in match.unmatched_gt:
            seg_eval.add_missed_gt(gts[gt_j].class_id)
        status.advance()

    return {
        "detection": det_eval.summarize(),
        "segmentation": seg_eval.summarize(),
        "seg_match_threshold": seg_threshold,
        "timing": {
            k: float(np.mean([t[k] for t in timings])) if timings else 0.0
            for k in ("detection_ms", "segmentation_ms", "total_ms")
        },
    }


# --------------------------------------------------------------------------
# commands
# --------------------------------------------------------------------------


def _summary_rows(metrics: Dict) -> List[List[object]]:
    """Pull the headline numbers out of either metrics shape."""
    det = metrics.get("detection", metrics)
    rows: List[List[object]] = []
    per_threshold = det.get("per_threshold") or det.get("thresholds") or {}
    for key, entry in sorted(per_threshold.items(), key=lambda kv: str(kv[0])):
        if not isinstance(entry, dict):
            continue
        rows.append(
            [
                key,
                f"{entry.get('micro_precision', float('nan')):.4f}",
                f"{entry.get('micro_recall', float('nan')):.4f}",
                f"{entry.get('micro_f1', float('nan')):.4f}",
                f"{entry.get('macro_f1', float('nan')):.4f}",
                f"{entry.get('mean_average_precision', entry.get('mean_ap', float('nan'))):.4f}",
            ]
        )
    return rows


def cmd_run(args: argparse.Namespace) -> int:
    cfg = load_config(args.config)
    if args.max_images:
        cfg["max_images"] = args.max_images
    if args.tile:
        cfg.setdefault("tiling", {})["enabled"] = True

    run_dir = Path(create_run_dir(cfg["experiment"]))
    write_run_manifest(run_dir, cfg["experiment"], cfg)

    dataset = build_dataset(cfg)
    env = _environment()
    print_banner(
        title=f"RUN {glyph('mid')} {cfg['experiment']}",
        subtitle=f"config: {args.config}",
        fields=_banner_fields(cfg, run_dir, dataset, env),
    )
    print_status("info", f"poll from another terminal:  argusvision status")
    print()

    total = min(cfg.get("max_images") or len(dataset.image_ids), len(dataset.image_ids))
    t0 = time.time()
    kind = cfg.get("kind", "detection")

    with RunStatus(
        run_dir,
        cfg["experiment"],
        total=total,
        extra={"config_path": str(args.config), "kind": kind},
    ) as status:
        if kind == "detection":
            metrics = run_detection(cfg, run_dir, status)
        elif kind == "pipeline":
            metrics = run_pipeline(cfg, run_dir, status)
        else:
            raise ValueError(f"unknown kind {kind!r}")
        metrics["wall_time_s"] = time.time() - t0
        metrics["environment"] = env
        status.finish(
            {
                k: metrics.get(k)
                for k in ("wall_time_s",)
                if metrics.get(k) is not None
            }
        )

    path = write_metrics(run_dir, metrics)

    print_section("RESULTS")
    rows = _summary_rows(metrics)
    if rows:
        print_result_table(
            ["IoU", "Micro P", "Micro R", "Micro F1", "Macro F1", "Mean AP"], rows
        )
    print_status("done", f"metrics  {path}")
    print_status("done", f"wall time  {metrics['wall_time_s']:.0f}s")
    print()
    return 0


def _format_eta(seconds: Optional[float]) -> str:
    if not seconds:
        return "—"
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h}h {m:02d}m" if h else f"{m}m {s:02d}s"


def _print_status_block(run_dir: Path, payload: Dict) -> None:
    state = payload.get("state", "unknown")
    marker = {"running": "info", "done": "done", "failed": "fail"}.get(state, "info")
    bar_width = 32
    pct = float(payload.get("percent") or 0.0)
    filled = int(bar_width * pct / 100.0)
    bar = (
        f"{C.magenta}{glyph('bar_full') * filled}"
        f"{C.dark}{glyph('bar_empty') * (bar_width - filled)}{C.reset}"
    )

    print_kv(
        {
            "experiment": payload.get("experiment", "?"),
            "state": state,
            "phase": payload.get("phase") or "—",
            "progress": f"{bar}  {payload.get('done', 0)}/{payload.get('total', 0)}  ({pct:.1f}%)",
            "elapsed": _format_eta(payload.get("elapsed_seconds")),
            "eta": _format_eta(payload.get("eta_seconds")),
            "rate": f"{payload.get('rate_per_second', 0):.2f} img/s",
            "updated": payload.get("updated_utc", "?"),
            "run dir": str(run_dir),
        }
    )
    if payload.get("error"):
        print()
        print_status("fail", payload["error"])
    print()
    print_status(marker, f"run is {state}")


def cmd_status(args: argparse.Namespace) -> int:
    root = Path(args.results_root)
    run_dir = (
        Path(args.run_dir)
        if args.run_dir
        else latest_run_dir(root, args.experiment)
    )
    if run_dir is None:
        print_status("warn", f"no run with a status file under {root}/")
        return 1

    while True:
        payload = read_status(run_dir)
        if payload is None:
            print_status("warn", f"no status.json in {run_dir}")
            return 1
        if args.json:
            print(json.dumps(payload, indent=2))
            return 0
        print_banner(title="RUN STATUS")
        _print_status_block(run_dir, payload)
        if not args.watch or payload.get("state") != "running":
            return 0
        time.sleep(args.interval)


def cmd_version(args: argparse.Namespace) -> int:
    try:
        from argusvision import __version__ as version
    except Exception:
        version = "0.1.0"
    print_banner(fields=_environment(), version=version)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="argusvision",
        description="ArgusVision — aerial detection to segmentation platform",
    )
    sub = parser.add_subparsers(dest="command")

    run_p = sub.add_parser("run", help="run an experiment from a YAML config")
    run_p.add_argument("config", help="path to YAML experiment config")
    run_p.add_argument(
        "--max-images", type=int, default=None, help="cap images (smoke runs)"
    )
    run_p.add_argument(
        "--tile", action="store_true", help="force tiled inference on"
    )
    run_p.set_defaults(func=cmd_run)

    st = sub.add_parser("status", help="read the heartbeat of a run in progress")
    st.add_argument("--experiment", default=None, help="narrow to one experiment")
    st.add_argument("--run-dir", default=None, help="explicit run directory")
    st.add_argument("--results-root", default=str(DEFAULT_RESULTS_ROOT))
    st.add_argument("--watch", action="store_true", help="refresh until the run ends")
    st.add_argument("--interval", type=float, default=10.0)
    st.add_argument("--json", action="store_true", help="raw JSON, no formatting")
    st.set_defaults(func=cmd_status)

    ver = sub.add_parser("version", help="show version and environment")
    ver.set_defaults(func=cmd_version)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        parser.print_help()
        return 1
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
