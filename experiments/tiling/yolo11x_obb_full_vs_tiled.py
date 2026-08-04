"""Compare full-image and tiled YOLOv11x-OBB detection on AerialFuseCV val.

This is an experiment wrapper only. It deliberately feeds both prediction sets
into the frozen DetectionEvaluator so the protocol comparison changes input
scale, not the metric.
"""

import argparse
import json
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

import cv2
import numpy as np
import torch
import yaml
from tqdm import tqdm
from ultralytics import YOLO

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from argusvision.data.aerialfusecv import AerialFuseCVSplit  # noqa: E402
from argusvision.data.constants import CLASS_ID_TO_NAME, NUM_DOTA_CLASSES  # noqa: E402
from argusvision.evaluation import DetectionEvaluator  # noqa: E402
from argusvision.evaluation.reporting import (  # noqa: E402
    environment_provenance,
    git_provenance,
)
from argusvision.models.base import Detection, obb_to_aabb  # noqa: E402


DEFAULT_CONFIG = REPO_ROOT / "experiments" / "tiling" / "yolo11x_obb_tiling.yaml"
DEFAULT_ASSET_ROOT = Path(r"D:/Work/AV")
SCALE_CLASSES = ("small-vehicle", "ship", "large-vehicle", "plane")


@dataclass
class RunStats:
    total_tiles: int = 0
    raw_detections: int = 0
    final_detections: int = 0
    runtime_s: float = 0.0

    def to_dict(self, num_images: int) -> Dict[str, float]:
        return {
            "total_tiles": self.total_tiles,
            "tiles_per_image_mean": self.total_tiles / num_images if num_images else 0.0,
            "raw_detections": self.raw_detections,
            "final_detections": self.final_detections,
            "runtime_s": self.runtime_s,
            "runtime_per_image_s": self.runtime_s / num_images if num_images else 0.0,
        }


def _load_config(path: Path) -> Dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _read_worktree_git_provenance() -> Dict[str, object]:
    git_pointer = REPO_ROOT / ".git"
    if git_pointer.is_file():
        text = git_pointer.read_text(encoding="utf-8").strip()
        if not text.startswith("gitdir:"):
            return {}
        git_dir = Path(text.split(":", 1)[1].strip())
        if not git_dir.is_absolute():
            git_dir = (REPO_ROOT / git_dir).resolve()
    else:
        git_dir = git_pointer

    head_path = git_dir / "HEAD"
    if not head_path.exists():
        return {}
    head = head_path.read_text(encoding="utf-8").strip()

    common_dir = git_dir
    common_pointer = git_dir / "commondir"
    if common_pointer.exists():
        common_text = common_pointer.read_text(encoding="utf-8").strip()
        common_dir = Path(common_text)
        if not common_dir.is_absolute():
            common_dir = (git_dir / common_dir).resolve()

    if not head.startswith("ref:"):
        return {"git_sha": head, "git_branch": "HEAD", "git_dirty": None}

    ref = head.split(" ", 1)[1]
    ref_path = common_dir / ref
    sha = None
    if ref_path.exists():
        sha = ref_path.read_text(encoding="utf-8").strip()
    else:
        packed_refs = common_dir / "packed-refs"
        if packed_refs.exists():
            for line in packed_refs.read_text(encoding="utf-8").splitlines():
                if line.startswith("#") or not line.strip():
                    continue
                maybe_sha, maybe_ref = line.split(" ", 1)
                if maybe_ref == ref:
                    sha = maybe_sha
                    break
    return {
        "git_sha": sha or "unknown",
        "git_branch": ref.replace("refs/heads/", ""),
        "git_dirty": None,
    }


def _git_info() -> Dict[str, object]:
    info = git_provenance()
    if info.get("git_sha") not in (None, "unknown"):
        return info
    fallback = _read_worktree_git_provenance()
    return fallback or info


def _resolve_path(value: str, asset_root: Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    local = REPO_ROOT / path
    if local.exists():
        return local
    return asset_root / path


def _batched(items: Sequence[np.ndarray], size: int) -> Iterable[Sequence[np.ndarray]]:
    for start in range(0, len(items), size):
        yield items[start:start + size]


def _tile_origins(width: int, height: int, tile_size: int, overlap: int) -> List[Tuple[int, int]]:
    if overlap >= tile_size:
        raise ValueError("overlap must be smaller than tile_size")
    stride = tile_size - overlap

    def starts(length: int) -> List[int]:
        if length <= tile_size:
            return [0]
        vals = list(range(0, length - tile_size + 1, stride))
        last = length - tile_size
        if vals[-1] != last:
            vals.append(last)
        return vals

    return [(x, y) for y in starts(height) for x in starts(width)]


def _detections_from_result(result, x0: float, y0: float, width: int, height: int) -> List[Detection]:
    detections: List[Detection] = []
    if getattr(result, "obb", None) is None:
        return detections
    polys = result.obb.xyxyxyxy
    clss = result.obb.cls
    confs = getattr(result.obb, "conf", None)
    if polys is None or clss is None:
        return detections

    offset = np.array([x0, y0] * 4, dtype=np.float64)
    for i in range(len(polys)):
        class_id = int(clss[i].item())
        if class_id < 0 or class_id >= NUM_DOTA_CLASSES:
            continue
        obb = np.asarray(polys[i].tolist(), dtype=np.float64).reshape(8) + offset
        xs = np.clip(obb[0::2], 0, max(width - 1, 0))
        ys = np.clip(obb[1::2], 0, max(height - 1, 0))
        obb[0::2] = xs
        obb[1::2] = ys
        if (xs.max() - xs.min()) < 1.0 or (ys.max() - ys.min()) < 1.0:
            continue
        score = float(confs[i].item()) if confs is not None else 1.0
        detections.append(
            Detection(
                class_id=class_id,
                score=score,
                box_xyxy=obb_to_aabb(obb),
                obb_xyxyxyxy=obb,
            )
        )
    return detections


def _rotated_nms(detections: Sequence[Detection], iou_threshold: float) -> List[Detection]:
    kept: List[Detection] = []
    for class_id in range(NUM_DOTA_CLASSES):
        class_dets = [d for d in detections if d.class_id == class_id]
        if not class_dets:
            continue
        rects = []
        scores = []
        valid_dets = []
        for det in class_dets:
            if det.obb_xyxyxyxy is None:
                continue
            pts = det.obb_xyxyxyxy.reshape(4, 2).astype(np.float32)
            rect = cv2.minAreaRect(pts)
            if rect[1][0] < 1.0 or rect[1][1] < 1.0:
                continue
            rects.append(rect)
            scores.append(float(det.score))
            valid_dets.append(det)
        if not valid_dets:
            continue
        indices = cv2.dnn.NMSBoxesRotated(
            rects, scores, score_threshold=0.0, nms_threshold=float(iou_threshold)
        )
        if len(indices) == 0:
            continue
        for idx in np.asarray(indices).reshape(-1):
            kept.append(valid_dets[int(idx)])
    kept.sort(key=lambda d: d.score, reverse=True)
    return kept


def _predict_full(model: YOLO, image: np.ndarray, conf: float, device: str) -> Tuple[List[Detection], int]:
    result = model.predict(source=image, conf=conf, verbose=False, device=device)[0]
    detections = _detections_from_result(result, 0.0, 0.0, image.shape[1], image.shape[0])
    return detections, 1


def _predict_tiled(
    model: YOLO,
    image: np.ndarray,
    conf: float,
    device: str,
    tile_size: int,
    overlap: int,
    batch_size: int,
    nms_iou: float,
) -> Tuple[List[Detection], int, int]:
    height, width = image.shape[:2]
    origins = _tile_origins(width, height, tile_size, overlap)
    tiles = [image[y:y + tile_size, x:x + tile_size] for x, y in origins]

    raw: List[Detection] = []
    origin_offset = 0
    for batch in _batched(tiles, batch_size):
        results = model.predict(
            source=list(batch),
            conf=conf,
            verbose=False,
            device=device,
            batch=batch_size,
        )
        for result in results:
            x0, y0 = origins[origin_offset]
            raw.extend(_detections_from_result(result, x0, y0, width, height))
            origin_offset += 1

    return _rotated_nms(raw, nms_iou), len(origins), len(raw)


def _evaluate_mode(
    mode: str,
    model: YOLO,
    dataset: AerialFuseCVSplit,
    image_ids: Sequence[str],
    cfg: Dict,
    device: str,
) -> Tuple[Dict, Dict]:
    evaluator = DetectionEvaluator(
        iou_thresholds=tuple(cfg["iou_thresholds"]),
        iou_mode=cfg["iou_mode"],
    )
    stats = RunStats()
    t0 = time.perf_counter()
    for image_id in tqdm(image_ids, desc=mode, unit="img", ncols=90):
        image = dataset.load_image(image_id)
        gts = dataset.load_ground_truth(image_id)
        if mode == "full_image":
            detections, tiles = _predict_full(model, image, cfg["conf"], device)
            raw_count = len(detections)
        elif mode == "tiled":
            detections, tiles, raw_count = _predict_tiled(
                model,
                image,
                cfg["conf"],
                device,
                cfg["tile_size"],
                cfg["overlap"],
                cfg["batch_size"],
                cfg["nms_iou"],
            )
        else:
            raise ValueError(f"unknown mode: {mode}")
        stats.total_tiles += tiles
        stats.raw_detections += raw_count
        stats.final_detections += len(detections)
        evaluator.add_image(detections, gts)
    stats.runtime_s = time.perf_counter() - t0
    metrics = evaluator.summarize()
    metrics["operational"] = stats.to_dict(len(image_ids))
    return metrics, stats.to_dict(len(image_ids))


def _threshold_entry(metrics: Dict, threshold: float) -> Dict:
    per_threshold = metrics["per_threshold"]
    return per_threshold.get(threshold) or per_threshold[str(threshold)]


def _metric_row(metrics: Dict, threshold: float) -> Dict[str, float]:
    entry = _threshold_entry(metrics, threshold)
    return {
        "micro_precision": entry["micro_precision"],
        "micro_recall": entry["micro_recall"],
        "micro_f1": entry["micro_f1"],
        "macro_f1": entry["macro_f1"],
        "mean_ap": entry["mean_ap"],
    }


def _selected_recalls(metrics: Dict, threshold: float) -> Dict[str, float]:
    per_class = _threshold_entry(metrics, threshold)["per_class"]
    return {name: per_class[name]["recall"] for name in SCALE_CLASSES}


def _make_report(run_dir: Path, cfg: Dict, output: Dict) -> str:
    thresholds = [float(t) for t in cfg["iou_thresholds"]]
    lines = [
        "# F6b Tiling Report",
        "",
        "## Protocol",
        "",
        f"- Dataset: `{cfg['dataset_path']}`",
        f"- Weights: `{cfg['weights_path']}`",
        f"- Full-image mode: one YOLOv11x-OBB prediction per full validation image.",
        f"- Tiled mode: {cfg['tile_size']}x{cfg['tile_size']} windows, {cfg['overlap']} px overlap.",
        f"- Tile detections are mapped back to full-image coordinates before evaluation.",
        f"- Cross-tile de-duplication: class-wise OpenCV rotated NMS at IoU {cfg['nms_iou']}.",
        f"- Evaluator: frozen `DetectionEvaluator`, `iou_mode={cfg['iou_mode']}`, thresholds {cfg['iou_thresholds']}.",
        "",
        "## Detection Metrics",
        "",
        "| Mode | IoU | Micro P | Micro R | Micro F1 | Macro F1 | Mean AP |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for mode in ("full_image", "tiled"):
        for threshold in thresholds:
            row = _metric_row(output[mode], threshold)
            lines.append(
                "| {mode} | {threshold} | {p:.4f} | {r:.4f} | {f1:.4f} | {mf1:.4f} | {ap:.4f} |".format(
                    mode=mode,
                    threshold=threshold,
                    p=row["micro_precision"],
                    r=row["micro_recall"],
                    f1=row["micro_f1"],
                    mf1=row["macro_f1"],
                    ap=row["mean_ap"],
                )
            )
    lines.extend([
        "",
        "## Scale-Sensitive Recall",
        "",
        "| Mode | IoU | small-vehicle | ship | large-vehicle | plane |",
        "|---|---:|---:|---:|---:|---:|",
    ])
    for mode in ("full_image", "tiled"):
        for threshold in thresholds:
            recalls = _selected_recalls(output[mode], threshold)
            lines.append(
                "| {mode} | {threshold} | {small:.4f} | {ship:.4f} | {large:.4f} | {plane:.4f} |".format(
                    mode=mode,
                    threshold=threshold,
                    small=recalls["small-vehicle"],
                    ship=recalls["ship"],
                    large=recalls["large-vehicle"],
                    plane=recalls["plane"],
                )
            )
    lines.extend([
        "",
        "## Operational Statistics",
        "",
        "| Mode | Mean tiles/image | Raw detections | Final detections | Runtime/image (s) |",
        "|---|---:|---:|---:|---:|",
    ])
    for mode in ("full_image", "tiled"):
        stats = output[mode]["operational"]
        lines.append(
            "| {mode} | {tiles:.2f} | {raw} | {final} | {runtime:.3f} |".format(
                mode=mode,
                tiles=stats["tiles_per_image_mean"],
                raw=stats["raw_detections"],
                final=stats["final_detections"],
                runtime=stats["runtime_per_image_s"],
            )
        )
    lines.extend([
        "",
        "## Read",
        "",
        "TBD after reviewing the completed run.",
        "",
        "## Artifacts",
        "",
        f"- Metrics: `{run_dir / 'metrics.json'}`",
        f"- Manifest: `{run_dir / 'manifest.json'}`",
    ])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--max-images", type=int, default=None)
    args = parser.parse_args()

    cfg = _load_config(Path(args.config))
    asset_root = Path(cfg.get("asset_root") or DEFAULT_ASSET_ROOT)
    cfg["dataset_path"] = str(_resolve_path(cfg["dataset_path"], asset_root))
    cfg["weights_path"] = str(_resolve_path(cfg["weights_path"], asset_root))
    cfg["max_images"] = args.max_images

    dataset_path = Path(cfg["dataset_path"])
    weights_path = Path(cfg["weights_path"])
    if not dataset_path.exists():
        raise FileNotFoundError(f"dataset path not found: {dataset_path}")
    if not weights_path.exists():
        raise FileNotFoundError(f"weights path not found: {weights_path}")

    output_root = Path(cfg["output_root"])
    if not output_root.is_absolute():
        output_root = REPO_ROOT / output_root
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    git_info = _git_info()
    short_sha = str(git_info.get("git_sha") or "nosha")[:7]
    run_dir = output_root / f"{stamp}_{short_sha}"
    run_dir.mkdir(parents=True, exist_ok=False)

    dataset = AerialFuseCVSplit(str(dataset_path))
    image_ids = dataset.image_ids[: args.max_images or len(dataset.image_ids)]
    device = cfg.get("device") or ("cuda:0" if torch.cuda.is_available() else "cpu")
    model = YOLO(str(weights_path))
    model.to(device)

    manifest = {
        "experiment": "f6b_yolo11x_obb_full_vs_tiled",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "config": cfg,
        "num_images": len(image_ids),
        "class_names": CLASS_ID_TO_NAME,
        "command": " ".join(sys.argv),
        **git_info,
        "environment": environment_provenance(),
    }
    with open(run_dir / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    output = {
        "full_image": _evaluate_mode("full_image", model, dataset, image_ids, cfg, device)[0],
        "tiled": _evaluate_mode("tiled", model, dataset, image_ids, cfg, device)[0],
    }
    with open(run_dir / "metrics.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    report = _make_report(run_dir, cfg, output)
    with open(REPO_ROOT / "experiments" / "tiling" / "REPORT.md", "w", encoding="utf-8") as f:
        f.write(report)
    print(f"[done] {run_dir / 'metrics.json'}")
    print(f"[done] {REPO_ROOT / 'experiments' / 'tiling' / 'REPORT.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
