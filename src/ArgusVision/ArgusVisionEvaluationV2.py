"""
ArgusVisionEvaluationV2: Two-level evaluation for ArgusVision pipeline.

Level 1 (Detection Quality):
    - Uses GT bboxes from DOTA labels
    - Hungarian matching with bbox IoU matrix
    - Micro metrics: TP/FP/FN/Recall/Precision/F1

Level 2 (Segmentation Quality):
    - Evaluates SAM masks for TP detections
    - Computes IoU / DICE against GT instance masks

Outputs are stored under:
    results/ArgusVision_v2_evaluation/
"""

from __future__ import annotations

import gc
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np
from scipy.ndimage import label
from scipy.optimize import linear_sum_assignment

try:
    import torch

    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

from src.ArgusVision.ArgusVisionCore import ArgusVisionCore
from src.ArgusVision.config.class_prompt_config import CLASS_NAMES
from src.utils.metrics import calculate_mask_dice, calculate_mask_iou
from src.utils.visualization_v2 import DiagnosticVisualizerV2


class _ArrayLike:
    """Tiny tensor-like wrapper to satisfy DiagnosticVisualizerV2 expectations."""

    def __init__(self, arr: np.ndarray):
        self.arr = np.array(arr, dtype=np.float32)

    def cpu(self):
        return self

    def numpy(self):
        return self.arr


class _OBBLike:
    def __init__(self, points_4x2: np.ndarray):
        self.xyxyxyxy = [_ArrayLike(points_4x2)]


class SimpleDetection:
    """
    Wrapper object with `.bbox`, `.obb`, and `.xyxy` attributes
    compatible with DiagnosticVisualizerV2.
    """

    def __init__(self, bbox: List[float]):
        self.bbox = bbox
        if len(bbox) == 8:
            pts = np.array(
                [[bbox[0], bbox[1]], [bbox[2], bbox[3]], [bbox[4], bbox[5]], [bbox[6], bbox[7]]],
                dtype=np.float32,
            )
            self.obb = _OBBLike(pts)
            x_min, y_min = float(np.min(pts[:, 0])), float(np.min(pts[:, 1]))
            x_max, y_max = float(np.max(pts[:, 0])), float(np.max(pts[:, 1]))
            self.xyxy = [_ArrayLike(np.array([x_min, y_min, x_max, y_max], dtype=np.float32))]
        else:
            x1, y1, x2, y2 = bbox
            self.obb = None
            self.xyxy = [_ArrayLike(np.array([x1, y1, x2, y2], dtype=np.float32))]


@dataclass
class ClassExample:
    image_path: Path
    img_name: str
    class_id: int
    class_name: str
    gsd: float
    n_gt: int
    n_det: int
    tp: int
    fp: int
    fn: int
    recall: float
    precision: float
    f1: float
    seg_iou: float
    seg_dice: float
    seg_iou_e2e: float
    seg_dice_e2e: float
    det_bboxes: List[List[float]]
    det_outcomes: List[str]
    gt_mask_path: Path


class ArgusVisionEvaluatorV2:
    """ArgusVision evaluation with two-level metrics."""

    def __init__(
        self,
        yolo_model,
        sam_model,
        dataset_path: str,
        class_prompt_config=None,
        output_dir: str = "results/ArgusVision_v2_evaluation",
    ):
        self.pipeline = ArgusVisionCore(yolo_model, sam_model, class_prompt_config)
        self.dataset_path = Path(dataset_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.examples_dir = self.output_dir / "examples"
        self.best_dir = self.examples_dir / "best"
        self.worst_dir = self.examples_dir / "worst"
        self.single_dir = self.examples_dir / "single_runs"
        for d in [self.best_dir, self.worst_dir, self.single_dir]:
            d.mkdir(parents=True, exist_ok=True)

        self._verify_dataset()
        self.image_files = sorted((self.dataset_path / "images").glob("*.png"))
        self.class_colors = self._load_class_colors()
        self.gsd_mapping = self._load_gsd_mapping()
        self.class_name_to_id = {name: cid for cid, name in CLASS_NAMES.items()}

        print("✅ ArgusVisionEvaluatorV2 initialized")
        print(f"✅ Dataset images: {len(self.image_files)}")

    def _verify_dataset(self):
        required = ["images", "labels", "semantic_masks"]
        for folder in required:
            folder_path = self.dataset_path / folder
            if not folder_path.exists():
                raise FileNotFoundError(f"Dataset missing required folder: {folder_path}")

    def _load_class_colors(self) -> Dict[Tuple[int, int, int], int]:
        return {
            (0, 127, 255): 0,
            (0, 0, 63): 1,
            (0, 63, 63): 2,
            (0, 63, 0): 3,
            (0, 63, 127): 4,
            (0, 63, 191): 5,
            (0, 63, 255): 6,
            (0, 100, 155): 7,
            (0, 127, 63): 8,
            (0, 127, 127): 9,
            (0, 0, 127): 10,
            (0, 0, 191): 11,
            (0, 191, 127): 12,
            (0, 127, 191): 13,
            (0, 0, 255): 14,
        }

    def _load_gsd_mapping(self) -> Dict[str, float]:
        gsd_path = Path("dataset/dota_gsd_mapping.json")
        if not gsd_path.exists():
            return {}
        with open(gsd_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _cleanup_memory(self):
        gc.collect()
        if TORCH_AVAILABLE and torch.cuda.is_available():
            torch.cuda.empty_cache()

    # ---------------------------------------------------------------------
    # Required core methods
    # ---------------------------------------------------------------------
    def _load_gt_bboxes(self, img_name: str, class_id: int) -> List[List[float]]:
        """
        Parse DOTA labels format:
        x1 y1 x2 y2 x3 y3 x4 y4 class-name difficulty
        """
        label_path = self.dataset_path / "labels" / f"{img_name}.txt"
        if not label_path.exists():
            return []

        gt_boxes: List[List[float]] = []
        with open(label_path, "r", encoding="utf-8") as f:
            lines = [ln.strip() for ln in f.readlines() if ln.strip()]

        for ln in lines:
            parts = ln.split()
            if len(parts) < 10:
                continue

            try:
                coords = [float(v) for v in parts[:8]]
            except ValueError:
                continue

            cls_token = parts[8]
            parsed_id: Optional[int] = None
            if cls_token.isdigit():
                parsed_id = int(cls_token)
            else:
                parsed_id = self.class_name_to_id.get(cls_token)

            if parsed_id is None:
                continue
            if parsed_id != class_id:
                continue

            gt_boxes.append(coords)

        return gt_boxes

    def _compute_bbox_iou(self, bbox1: List[float], bbox2: List[float]) -> float:
        """Compute IoU after OBB→AABB conversion."""

        def to_aabb(bb: List[float]) -> Tuple[float, float, float, float]:
            if len(bb) == 4:
                return float(bb[0]), float(bb[1]), float(bb[2]), float(bb[3])
            x_coords = [bb[i] for i in range(0, 8, 2)]
            y_coords = [bb[i] for i in range(1, 8, 2)]
            return min(x_coords), min(y_coords), max(x_coords), max(y_coords)

        x1_min, y1_min, x1_max, y1_max = to_aabb(bbox1)
        x2_min, y2_min, x2_max, y2_max = to_aabb(bbox2)

        inter_x1 = max(x1_min, x2_min)
        inter_y1 = max(y1_min, y2_min)
        inter_x2 = min(x1_max, x2_max)
        inter_y2 = min(y1_max, y2_max)

        inter_w = max(0.0, inter_x2 - inter_x1)
        inter_h = max(0.0, inter_y2 - inter_y1)
        inter_area = inter_w * inter_h

        area1 = max(0.0, (x1_max - x1_min)) * max(0.0, (y1_max - y1_min))
        area2 = max(0.0, (x2_max - x2_min)) * max(0.0, (y2_max - y2_min))
        union = area1 + area2 - inter_area
        if union <= 0:
            return 0.0
        return float(inter_area / union)

    def _match_bboxes(
        self,
        det_bboxes: List[List[float]],
        gt_bboxes: List[List[float]],
        threshold: float = 0.5,
    ) -> List[Tuple[int, int]]:
        """Hungarian matching using IoU matrix."""
        if not det_bboxes or not gt_bboxes:
            return []

        iou_matrix = np.zeros((len(det_bboxes), len(gt_bboxes)), dtype=np.float32)
        for i, det_bb in enumerate(det_bboxes):
            for j, gt_bb in enumerate(gt_bboxes):
                iou_matrix[i, j] = self._compute_bbox_iou(det_bb, gt_bb)

        det_idx, gt_idx = linear_sum_assignment(-iou_matrix)
        matches: List[Tuple[int, int]] = []
        for d, g in zip(det_idx, gt_idx):
            if iou_matrix[d, g] >= threshold:
                matches.append((int(d), int(g)))
        return matches

    def _extract_gt_masks_for_class(self, gt_mask_rgb: np.ndarray, class_id: int) -> List[np.ndarray]:
        """Current approach: connected components on semantic class mask."""
        class_mask = self._extract_class_binary_mask(gt_mask_rgb, class_id)
        if not np.any(class_mask):
            return []

        labeled, num_instances = label(class_mask)
        masks: List[np.ndarray] = []
        for idx in range(1, num_instances + 1):
            m = labeled == idx
            if np.any(m):
                masks.append(m)
        return masks

    def _extract_class_binary_mask(self, gt_mask_rgb: np.ndarray, class_id: int) -> np.ndarray:
        class_color = None
        for color, cid in self.class_colors.items():
            if cid == class_id:
                class_color = color
                break
        if class_color is None:
            return np.zeros(gt_mask_rgb.shape[:2], dtype=bool)
        return np.all(gt_mask_rgb == np.array(class_color, dtype=np.uint8), axis=-1)

    def _extract_gt_mask_for_bbox(
        self,
        gt_mask_rgb: np.ndarray,
        class_id: int,
        gt_bbox: List[float],
    ) -> np.ndarray:
        """
        Build GT mask for a specific GT bbox by clipping class semantic mask with bbox polygon.
        This avoids index mismatch between GT bboxes and connected-component instances.
        """
        class_mask = self._extract_class_binary_mask(gt_mask_rgb, class_id)
        h, w = class_mask.shape

        poly_mask = np.zeros((h, w), dtype=np.uint8)
        if len(gt_bbox) == 8:
            pts = np.array(
                [[gt_bbox[0], gt_bbox[1]], [gt_bbox[2], gt_bbox[3]], [gt_bbox[4], gt_bbox[5]], [gt_bbox[6], gt_bbox[7]]],
                dtype=np.float32,
            )
            pts = np.round(pts).astype(np.int32)
            cv2.fillPoly(poly_mask, [pts], 1)
        else:
            x1, y1, x2, y2 = [int(round(v)) for v in gt_bbox]
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w - 1, x2), min(h - 1, y2)
            cv2.rectangle(poly_mask, (x1, y1), (x2, y2), 1, -1)

        instance_mask = class_mask & (poly_mask > 0)
        if not np.any(instance_mask):
            # Fallback: use polygon area if class mask has annotation gaps.
            instance_mask = poly_mask > 0
        return instance_mask

    # ---------------------------------------------------------------------
    # Evaluation
    # ---------------------------------------------------------------------
    def evaluate(
        self,
        max_images: Optional[int] = None,
        save_visualizations: bool = True,
        single_image: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Main evaluation loop."""
        if single_image:
            candidate = [p for p in self.image_files if p.stem == single_image]
            if not candidate:
                raise FileNotFoundError(f"Single image not found: {single_image}")
            images_to_process = candidate
            print(f"✅ Single-image mode active: {single_image}")
        else:
            images_to_process = self.image_files[:max_images] if max_images else self.image_files

        metrics = {
            "per_class": {
                cid: {
                    "tp": 0,
                    "fp": 0,
                    "fn": 0,
                    "seg_iou_tp": [],
                    "seg_dice_tp": [],
                    "seg_iou_gt_anchored": [],
                    "seg_dice_gt_anchored": [],
                }
                for cid in CLASS_NAMES.keys()
            },
            "overall": {
                "tp": 0,
                "fp": 0,
                "fn": 0,
                "seg_iou_tp": [],
                "seg_dice_tp": [],
                "seg_iou_gt_anchored": [],
                "seg_dice_gt_anchored": [],
            },
            "timing": [],
            "num_images": len(images_to_process),
        }

        examples: Dict[int, List[ClassExample]] = {cid: [] for cid in CLASS_NAMES.keys()}

        for idx, img_path in enumerate(images_to_process, start=1):
            print(f"\n[{idx}/{len(images_to_process)}] Processing: {img_path.name}")
            image_bgr = cv2.imread(str(img_path))
            if image_bgr is None:
                print(f"⚠️ Could not read image: {img_path}")
                continue
            image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)

            img_name = img_path.stem
            gt_mask_path = self.dataset_path / "semantic_masks" / f"{img_name}_instance_color_RGB.png"
            gt_mask_bgr = cv2.imread(str(gt_mask_path))
            if gt_mask_bgr is None:
                print(f"⚠️ Missing GT mask for image: {img_name}")
                continue
            gt_mask_rgb = cv2.cvtColor(gt_mask_bgr, cv2.COLOR_BGR2RGB)

            # Timing is inference-only from pipeline
            infer = self.pipeline.run_inference(image_rgb)
            metrics["timing"].append(infer["timing"])

            detections = infer["detections"]
            pred_masks = infer["masks"]
            pred_classes = infer["classes"]

            for class_id, class_name in CLASS_NAMES.items():
                class_det_indices = [i for i, c in enumerate(pred_classes) if c == class_id]
                class_det_bboxes = [detections[i]["bbox"] for i in class_det_indices]
                class_gt_bboxes = self._load_gt_bboxes(img_name, class_id)

                matches = self._match_bboxes(class_det_bboxes, class_gt_bboxes, threshold=0.5)

                tp = len(matches)
                fp = len(class_det_bboxes) - tp
                fn = len(class_gt_bboxes) - tp

                metrics["per_class"][class_id]["tp"] += tp
                metrics["per_class"][class_id]["fp"] += fp
                metrics["per_class"][class_id]["fn"] += fn
                metrics["overall"]["tp"] += tp
                metrics["overall"]["fp"] += fp
                metrics["overall"]["fn"] += fn

                gt_iou_scores = [0.0 for _ in range(len(class_gt_bboxes))]
                gt_dice_scores = [0.0 for _ in range(len(class_gt_bboxes))]

                for det_local_idx, gt_local_idx in matches:
                    abs_det_idx = class_det_indices[det_local_idx]
                    if abs_det_idx >= len(pred_masks):
                        continue
                    if gt_local_idx >= len(class_gt_bboxes):
                        continue

                    pred_m = pred_masks[abs_det_idx]
                    gt_m = self._extract_gt_mask_for_bbox(
                        gt_mask_rgb=gt_mask_rgb,
                        class_id=class_id,
                        gt_bbox=class_gt_bboxes[gt_local_idx],
                    )
                    iou = float(calculate_mask_iou(pred_m, gt_m))
                    dice = float(calculate_mask_dice(pred_m, gt_m))

                    metrics["per_class"][class_id]["seg_iou_tp"].append(iou)
                    metrics["per_class"][class_id]["seg_dice_tp"].append(dice)
                    metrics["overall"]["seg_iou_tp"].append(iou)
                    metrics["overall"]["seg_dice_tp"].append(dice)

                    gt_iou_scores[gt_local_idx] = iou
                    gt_dice_scores[gt_local_idx] = dice

                # GT-anchored operational segmentation metric (missed detections = 0)
                metrics["per_class"][class_id]["seg_iou_gt_anchored"].extend(gt_iou_scores)
                metrics["per_class"][class_id]["seg_dice_gt_anchored"].extend(gt_dice_scores)
                metrics["overall"]["seg_iou_gt_anchored"].extend(gt_iou_scores)
                metrics["overall"]["seg_dice_gt_anchored"].extend(gt_dice_scores)

                if save_visualizations and (len(class_gt_bboxes) > 0 or len(class_det_bboxes) > 0):
                    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
                    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
                    f1 = (
                        (2 * precision * recall / (precision + recall))
                        if (precision + recall) > 0
                        else 0.0
                    )
                    seg_iou = (
                        float(np.mean(metrics["per_class"][class_id]["seg_iou_tp"][-tp:]))
                        if tp > 0
                        else 0.0
                    )
                    seg_dice = (
                        float(np.mean(metrics["per_class"][class_id]["seg_dice_tp"][-tp:]))
                        if tp > 0
                        else 0.0
                    )
                    seg_iou_e2e = float(np.mean(gt_iou_scores)) if gt_iou_scores else 0.0
                    seg_dice_e2e = float(np.mean(gt_dice_scores)) if gt_dice_scores else 0.0

                    outcomes = ["FP"] * len(class_det_bboxes)
                    for d_idx, _ in matches:
                        outcomes[d_idx] = "TP"

                    examples[class_id].append(
                        ClassExample(
                            image_path=img_path,
                            img_name=img_name,
                            class_id=class_id,
                            class_name=class_name,
                            gsd=float(self.gsd_mapping.get(img_name, 1.0) or 1.0),
                            n_gt=len(class_gt_bboxes),
                            n_det=len(class_det_bboxes),
                            tp=tp,
                            fp=fp,
                            fn=fn,
                            recall=recall,
                            precision=precision,
                            f1=f1,
                            seg_iou=seg_iou,
                            seg_dice=seg_dice,
                            seg_iou_e2e=seg_iou_e2e,
                            seg_dice_e2e=seg_dice_e2e,
                            det_bboxes=class_det_bboxes,
                            det_outcomes=outcomes,
                            gt_mask_path=gt_mask_path,
                        )
                    )

            if idx % 10 == 0:
                self._cleanup_memory()

        summary = self._compute_summary(metrics)
        self._save_results(summary, is_single_image_mode=(metrics["num_images"] == 1))
        self._print_summary(summary)

        if save_visualizations:
            self._save_visualizations(examples, is_single_image_mode=single_image is not None)

        return summary

    # ---------------------------------------------------------------------
    # Summary / Output
    # ---------------------------------------------------------------------
    def _compute_summary(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        def prf(tp: int, fp: int, fn: int) -> Tuple[float, float, float]:
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
            return recall, precision, f1

        o_tp, o_fp, o_fn = metrics["overall"]["tp"], metrics["overall"]["fp"], metrics["overall"]["fn"]
        o_recall, o_precision, o_f1 = prf(o_tp, o_fp, o_fn)

        timing = metrics["timing"]
        avg_det_ms = float(np.mean([t["detection_ms"] for t in timing])) if timing else 0.0
        avg_seg_ms = float(np.mean([t["segmentation_ms"] for t in timing])) if timing else 0.0
        avg_total_ms = float(np.mean([t["total_ms"] for t in timing])) if timing else 0.0

        per_class: Dict[str, Any] = {}
        for cid, cname in CLASS_NAMES.items():
            c = metrics["per_class"][cid]
            rec, prec, f1 = prf(c["tp"], c["fp"], c["fn"])
            per_class[cname] = {
                "tp": c["tp"],
                "fp": c["fp"],
                "fn": c["fn"],
                "recall": rec,
                "precision": prec,
                "f1": f1,
                "seg_iou_tp": float(np.mean(c["seg_iou_tp"])) if c["seg_iou_tp"] else 0.0,
                "seg_dice_tp": float(np.mean(c["seg_dice_tp"])) if c["seg_dice_tp"] else 0.0,
                "seg_iou_gt_anchored": (
                    float(np.mean(c["seg_iou_gt_anchored"])) if c["seg_iou_gt_anchored"] else 0.0
                ),
                "seg_dice_gt_anchored": (
                    float(np.mean(c["seg_dice_gt_anchored"])) if c["seg_dice_gt_anchored"] else 0.0
                ),
            }

        summary = {
            "config": {
                "dataset": str(self.dataset_path),
                "num_images": metrics["num_images"],
                "detection_matching": "Hungarian on bbox IoU matrix (threshold=0.5)",
                "gt_bbox_format": "DOTA x1 y1 x2 y2 x3 y3 x4 y4 class-name difficulty",
            },
            "overall": {
                "tp": o_tp,
                "fp": o_fp,
                "fn": o_fn,
                "recall": o_recall,
                "precision": o_precision,
                "f1": o_f1,
                "seg_iou_tp": (
                    float(np.mean(metrics["overall"]["seg_iou_tp"]))
                    if metrics["overall"]["seg_iou_tp"]
                    else 0.0
                ),
                "seg_dice_tp": (
                    float(np.mean(metrics["overall"]["seg_dice_tp"]))
                    if metrics["overall"]["seg_dice_tp"]
                    else 0.0
                ),
                "seg_iou_gt_anchored": (
                    float(np.mean(metrics["overall"]["seg_iou_gt_anchored"]))
                    if metrics["overall"]["seg_iou_gt_anchored"]
                    else 0.0
                ),
                "seg_dice_gt_anchored": (
                    float(np.mean(metrics["overall"]["seg_dice_gt_anchored"]))
                    if metrics["overall"]["seg_dice_gt_anchored"]
                    else 0.0
                ),
            },
            "per_class": per_class,
            "timing": {
                "avg_detection_ms": avg_det_ms,
                "avg_segmentation_ms": avg_seg_ms,
                "avg_total_ms": avg_total_ms,
                "note": "Timing includes inference only (YOLO + SAM)",
            },
        }
        return summary

    def _save_results(self, summary: Dict[str, Any], is_single_image_mode: bool = False):
        out_name = (
            "evaluation_metrics_v2_1-image_test.json"
            if is_single_image_mode
            else "evaluation_metrics_v2.json"
        )
        out_file = self.output_dir / out_name
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)
        print(f"✅ Results saved: {out_file}")

    def _print_summary(self, summary: Dict[str, Any]):
        ov = summary["overall"]
        print("\n" + "=" * 90)
        print("ARGUSVISION V2 EVALUATION SUMMARY".center(90))
        print("=" * 90)
        print(
            f"Detection: TP={ov['tp']} FP={ov['fp']} FN={ov['fn']} | "
            f"Recall={ov['recall']*100:.2f}% Precision={ov['precision']*100:.2f}% F1={ov['f1']*100:.2f}%"
        )
        print(
            f"Seg (TP-only): IoU={ov['seg_iou_tp']*100:.2f}% DICE={ov['seg_dice_tp']*100:.2f}%"
        )
        print(
            f"Seg (GT-anchored): IoU={ov['seg_iou_gt_anchored']*100:.2f}% "
            f"DICE={ov['seg_dice_gt_anchored']*100:.2f}%"
        )
        print(
            f"Timing (ms): detect={summary['timing']['avg_detection_ms']:.2f}, "
            f"segment={summary['timing']['avg_segmentation_ms']:.2f}, "
            f"total={summary['timing']['avg_total_ms']:.2f}"
        )
        print("=" * 90 + "\n")

    # ---------------------------------------------------------------------
    # Visualization
    # ---------------------------------------------------------------------
    def _save_visualizations(self, examples_data: Dict[int, List[ClassExample]], is_single_image_mode: bool):
        if is_single_image_mode:
            for _, exs in examples_data.items():
                for ex in exs:
                    self._generate_visualization(ex, self.single_dir)
            return

        for _, exs in examples_data.items():
            if not exs:
                continue
            exs_sorted = sorted(exs, key=lambda e: e.f1, reverse=True)
            self._generate_visualization(exs_sorted[0], self.best_dir)
            self._generate_visualization(exs_sorted[-1], self.worst_dir)

    def _generate_visualization(self, example: ClassExample, output_dir: Path):
        """Reload image, re-run pipeline, and create 2x2 diagnostic collage."""
        image_bgr = cv2.imread(str(example.image_path))
        if image_bgr is None:
            return
        image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)

        gt_bgr = cv2.imread(str(example.gt_mask_path))
        if gt_bgr is None:
            return
        gt_rgb = cv2.cvtColor(gt_bgr, cv2.COLOR_BGR2RGB)

        infer = self.pipeline.run_inference(image_rgb)
        class_det_indices = [i for i, cid in enumerate(infer["classes"]) if cid == example.class_id]
        class_det_bboxes = [infer["detections"][i]["bbox"] for i in class_det_indices]
        class_masks = [infer["masks"][i] for i in class_det_indices]

        wrapped_obb = [SimpleDetection(bb) for bb in class_det_bboxes]
        wrapped_vbb = [SimpleDetection(bb if len(bb) == 4 else self._obb_to_aabb(bb)) for bb in class_det_bboxes]
        gt_masks = self._extract_gt_masks_for_class(gt_rgb, example.class_id)

        metadata = {
            "image_id": example.img_name,
            "class_name": example.class_name,
            "gsd": f"{example.gsd:.2f}",
            "gt_count": example.n_gt,
            "det_count": example.n_det,
            "tp_count": example.tp,
            "fp_count": example.fp,
            "fn_count": example.fn,
            "n_tp": example.tp,
            "recall": example.recall,
            "precision": example.precision,
            "f1": example.f1,
            "avg_iou": example.seg_iou,
            "avg_dice": example.seg_dice,
            "avg_iou_e2e": example.seg_iou_e2e,
            "avg_dice_e2e": example.seg_dice_e2e,
        }

        viz = DiagnosticVisualizerV2(panel_size=1024, spacing=10)
        collage_rgb = viz.create_diagnostic_collage(
            image_rgb=image_rgb,
            yolo_obb_results=wrapped_obb,
            yolo_vbb_results=wrapped_vbb,
            gt_instances=gt_masks,
            sam_masks=class_masks,
            detection_outcomes=example.det_outcomes,
            metadata=metadata,
        )

        # Required conversion before save
        collage_bgr = cv2.cvtColor(collage_rgb, cv2.COLOR_RGB2BGR)
        f1_tag = f"{example.f1 * 100:.1f}"
        filename = f"{example.img_name}_{example.class_name}_F1_{f1_tag}.png"
        out_path = output_dir / filename
        cv2.imwrite(str(out_path), collage_bgr)
        print(f"[OK] Saved visualization: {filename}")

    def _obb_to_aabb(self, bb: List[float]) -> List[float]:
        if len(bb) == 4:
            return [float(v) for v in bb]
        xs = [bb[i] for i in range(0, 8, 2)]
        ys = [bb[i] for i in range(1, 8, 2)]
        return [float(min(xs)), float(min(ys)), float(max(xs)), float(max(ys))]
