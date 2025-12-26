import json
from collections import defaultdict
from typing import Dict, Iterable, List, Optional, Set, Tuple
import numpy as np
import cv2
import time
import torch
from tqdm import tqdm
from ultralytics import YOLO
from pathlib import Path
from torch.utils.data import DataLoader
from ..utils.metrics import calculate_bbox_metrics, save_metrics
from ..utils.visualization import save_detection_examples


class YOLODetector:
    """Unified YOLO Detector for both VBB (axis-aligned) and OBB (oriented) evaluation."""

    def __init__(
        self,
        model_name: str,
        weights_path: str,
        conf_threshold: float = 0.25,
        mode: str = "vbb",
        class_map: Optional[Dict[int, int]] = None,
        allowed_class_ids: Optional[Iterable[int]] = None,
        class_names: Optional[List[str]] = None,
    ):
        self.model_name = model_name
        self.mode = mode.lower()
        self.conf_threshold = conf_threshold
        self.class_map = class_map if class_map is not None else {}
        self.allowed_class_ids: Optional[Set[int]] = (
            set(allowed_class_ids) if allowed_class_ids is not None else None
        )
        self.class_names = class_names        
        # Load GSD mapping
        gsd_file = Path("dataset/dota_gsd_mapping.json")
        self.gsd_mapping = {}
        if gsd_file.exists():
            with open(gsd_file) as f:
                self.gsd_mapping = json.load(f)


        weights_path = self._resolve_weights(weights_path)
        self.model = YOLO(weights_path)
        # choose device and move model
        self.device = "cuda:0" if torch.cuda.is_available() else "cpu"
        try:
            self.model.to(self.device)
        except Exception:
            pass

    def _resolve_weights(self, weights_path: str) -> str:
        checkpoints_dir = Path("model_checkpoints/YOLO") / self.mode.upper()
        checkpoints_dir.mkdir(parents=True, exist_ok=True)
        local_path = checkpoints_dir / weights_path
        if not local_path.exists():
            # use tqdm.write to avoid interfering with progress bars
            tqdm.write(f"⚠️ Weights not found locally: {local_path}. Please place weights manually or let Ultralytics download.")
        else:
            tqdm.write(f"✅ Using existing weights for {self.model_name}")
        return str(local_path)

    # ----------------------------- Inference -----------------------------
    def predict(self, image: np.ndarray) -> Tuple[List[Dict], float]:
        """Run inference; return predictions list and inference time (ms)."""
        t0 = time.time()
        res = self.model.predict(
            source=image, conf=self.conf_threshold, verbose=False,
            device=self.device
        )[0]
        inf_ms = (time.time() - t0) * 1000.0

        preds: List[Dict] = []

        if self.mode == "vbb":
            if res.boxes is not None and len(res.boxes) > 0:
                for b in res.boxes:
                    x1, y1, x2, y2 = map(int, b.xyxy[0].tolist())
                    mid = int(b.cls.item())
                    cid = self.class_map.get(mid, mid)
                    if self.allowed_class_ids is not None and cid not in self.allowed_class_ids:
                        continue
                    conf = float(b.conf.item())
                    preds.append({
                        "bbox": [x1, y1, x2, y2],
                        "class_id": cid,
                        "confidence": conf
                    })

        else:  # OBB
            if hasattr(res, "obb") and res.obb is not None:
                polys = res.obb.xyxyxyxy  # (N, 8)
                clss = res.obb.cls        # (N,)
                confs = getattr(res.obb, "conf", None)

                n = len(polys)
                for i in range(n):
                    poly = polys[i]
                    # flatten robustly
                    if hasattr(poly, "tolist"):
                        poly = poly.tolist()
                    if isinstance(poly[0], (list, tuple, np.ndarray)):
                        poly = [float(v) for sub in poly for v in sub]
                    x1, y1, x2, y2, x3, y3, x4, y4 = map(float, poly)
                    mid = int(clss[i].item() if hasattr(clss[i], "item") else clss[i])
                    cid = self.class_map.get(mid, mid)
                    if self.allowed_class_ids is not None and cid not in self.allowed_class_ids:
                        continue
                    conf = float(confs[i].item()) if confs is not None else 1.0
                    preds.append({
                        "bbox": [int(x1), int(y1), int(x2), int(y2),
                                 int(x3), int(y3), int(x4), int(y4)],
                        "class_id": cid,
                        "confidence": conf
                    })

        return preds, inf_ms

    # ----------------------------- Evaluate one image -----------------------------
    def evaluate_image(self,
                       image: np.ndarray,
                       ground_truth: List[Dict],
                       num_classes: int,
                       save_dir: Optional[str] = None,
                       image_id: str = "eval",
                       class_names: Optional[List[str]] = None) -> Dict:
        preds, inf_ms = self.predict(image)
        m = calculate_bbox_metrics(preds, ground_truth, num_classes)
        m["inference_time_ms"] = inf_ms

        if save_dir:
            names = class_names or self.class_names
            save_detection_examples(
                image_id=image_id,
                model_name=self.model_name,
                image=image,
                predictions=preds,
                ground_truth=ground_truth,
                class_names={
                    i: (names[i] if names is not None and i < len(names) else str(i))
                    for i in range(num_classes)
                },
                metrics=m,
                output_dir=save_dir,
                is_obb=(self.mode == "obb"),
            )
        return m

    # ----------------------------- Evaluate dataset -----------------------------
    def evaluate_dataset(self,
                         image_paths: Optional[List[str]] = None,
                         label_paths: Optional[List[str]] = None,
                         dataloader: Optional[DataLoader] = None,
                         num_classes: int = 15,
                         results_dir: str = "results",
                         class_names: Optional[List[str]] = None) -> Dict:
        """
        Evaluate model on a dataset.
        
        Args:
            image_paths: List of image paths (legacy API, use dataloader instead)
            label_paths: List of label paths (legacy API, use dataloader instead)
            dataloader: PyTorch DataLoader (preferred method)
            num_classes: Number of classes in dataset
            results_dir: Directory to save results
            
        Returns:
            Dictionary of evaluation metrics
        """
        all_metrics: List[Dict] = []
        per_image_counts: List[List[Dict]] = []
        names = class_names or self.class_names
        
        # Store examples for later filtering (10 best + 10 worst)
        examples_data = []

        # Use DataLoader if provided, otherwise fall back to legacy path lists
        if dataloader is not None:
            total = len(dataloader.dataset)
            iterator = tqdm(dataloader, desc=f"Evaluating {self.model_name} ({self.mode.upper()})")
            
            for batch in iterator:
                # Process each image in the batch
                for i in range(len(batch["images"])):
                    img = batch["images"][i]
                    gts = batch["labels"][i]
                    image_id = batch["image_ids"][i]
                    
                    # Get predictions
                    preds, inf_ms = self.predict(img)
                    m = calculate_bbox_metrics(preds, gts, num_classes)
                    m["inference_time_ms"] = inf_ms
                    
                    all_metrics.append(m)
                    per_image_counts.append(m["per_class_counts"])
                    
                    # Store for visualization
                    examples_data.append({
                        'image_id': image_id,
                        'image': img.copy(),
                        'predictions': preds,
                        'ground_truth': gts,
                        'metrics': m
                    })
                    
        else:
            # Legacy API: use image_paths and label_paths
            if image_paths is None or label_paths is None:
                raise ValueError("Must provide either dataloader or (image_paths, label_paths)")
            
            for img_path, lbl_path in tqdm(zip(image_paths, label_paths),
                                           total=len(image_paths),
                                           desc=f"Evaluating {self.model_name} ({self.mode.upper()})"):
                img = cv2.imread(img_path)
                if img is None:
                    continue
                img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                ih, iw = img.shape[:2]

                # --- read GT and filter to allowed_class_ids ---
                gts: List[Dict] = []
                with open(lbl_path, "r") as f:
                    for line in f:
                        p = line.strip().split()
                        if self.mode == "vbb" and len(p) == 5:
                            cid, cx, cy, w, h = map(float, p)
                            cid = int(cid)
                            if self.allowed_class_ids is not None and cid not in self.allowed_class_ids:
                                continue
                            x1 = int((cx - w / 2) * iw); y1 = int((cy - h / 2) * ih)
                            x2 = int((cx + w / 2) * iw); y2 = int((cy + h / 2) * ih)
                            gts.append({"bbox": [x1, y1, x2, y2], "class_id": cid})
                        elif self.mode == "obb" and len(p) == 9:
                            # New format: class_id x1 y1 x2 y2 x3 y3 x4 y4
                            cid, x1, y1, x2, y2, x3, y3, x4, y4 = map(float, p)
                            cid = int(cid)
                            if self.allowed_class_ids is not None and cid not in self.allowed_class_ids:
                                continue
                            gts.append({
                                "bbox": [int(x1 * iw), int(y1 * ih),
                                         int(x2 * iw), int(y2 * ih),
                                         int(x3 * iw), int(y3 * ih),
                                         int(x4 * iw), int(y4 * ih)],
                                "class_id": cid
                            })

                # Get predictions
                preds, inf_ms = self.predict(img)
                m = calculate_bbox_metrics(preds, gts, num_classes)
                m["inference_time_ms"] = inf_ms
                
                all_metrics.append(m)
                per_image_counts.append(m["per_class_counts"])
                
                # Store for visualization
                examples_data.append({
                    'image_id': Path(img_path).stem,
                    'image': img.copy(),
                    'predictions': preds,
                    'ground_truth': gts,
                    'metrics': m
                })

        # -------- aggregate (dataset-level) --------
        mean_iou_values = [m["mean_iou"] for m in all_metrics]
        mean_dice_values = [m["mean_dice"] for m in all_metrics]
        times = [m.get("inference_time_ms", 0.0) for m in all_metrics]

        # Collect per-class IoU/DICE values across all images
        per_class_ious_aggregated = [[] for _ in range(num_classes)]
        per_class_dices_aggregated = [[] for _ in range(num_classes)]
        
        for img_metrics in all_metrics:
            # Aggregate per-class IoU/DICE from each image
            for class_id in range(num_classes):
                if "per_class_ious" in img_metrics and "per_class_dices" in img_metrics:
                    per_class_ious_aggregated[class_id].extend(img_metrics["per_class_ious"][class_id])
                    per_class_dices_aggregated[class_id].extend(img_metrics["per_class_dices"][class_id])
        
        overall_mean_iou = float(np.mean(mean_iou_values)) if mean_iou_values else 0.0
        overall_mean_dice = float(np.mean(mean_dice_values)) if mean_dice_values else 0.0
        overall_std_iou = float(np.std(mean_iou_values)) if len(mean_iou_values) > 1 else 0.0
        overall_std_dice = float(np.std(mean_dice_values)) if len(mean_dice_values) > 1 else 0.0
        overall_avg_time = float(np.mean(times)) if times else 0.0

        # sum tp/fp/fn across images
        counts = np.array([[(c["tp"], c["fp"], c["fn"]) for c in per_img] for per_img in per_image_counts],
                          dtype=np.int64)  # (N, C, 3)
        summed = counts.sum(axis=0) if len(counts) else np.zeros((num_classes, 3), dtype=np.int64)
        tp, fp, fn = summed[:, 0].astype(float), summed[:, 1].astype(float), summed[:, 2].astype(float)

        # Calculate total counts
        total_gt = int((tp + fn).sum())
        total_detections = int((tp + fp).sum())
        matched_pairs = int(tp.sum())

        with np.errstate(divide="ignore", invalid="ignore"):
            precision = np.divide(tp, tp + fp, where=(tp + fp) > 0)
            recall    = np.divide(tp, tp + fn, where=(tp + fn) > 0)
            f1        = np.divide(2 * precision * recall, precision + recall, where=(precision + recall) > 0)

        # keep only allowed classes for MAP
        allowed_ids = self.allowed_class_ids if self.allowed_class_ids is not None else set(range(num_classes))
        existed = ((tp + fp + fn) > 0) & np.isin(np.arange(num_classes), list(allowed_ids))
        dataset_map = float(np.nanmean(f1[existed])) if np.any(existed) else 0.0
        
        # Calculate mean detection metrics across all classes
        mean_recall = float(np.nanmean(recall[existed])) if np.any(existed) else 0.0
        mean_precision = float(np.nanmean(precision[existed])) if np.any(existed) else 0.0
        mean_f1 = dataset_map  # Same as mAP

        # Per-class metrics in new format (matching ArgusVision)
        per_class_metrics = {}
        for i in range(num_classes):
            if i in allowed_ids and existed[i]:
                class_name = names[i] if names is not None and i < len(names) else str(i)
                # Calculate per-class bbox quality averages
                class_bbox_iou = float(np.mean(per_class_ious_aggregated[i])) if per_class_ious_aggregated[i] else 0.0
                class_bbox_dice = float(np.mean(per_class_dices_aggregated[i])) if per_class_dices_aggregated[i] else 0.0
                
                per_class_metrics[class_name] = {
                    'recall': float(recall[i]) if not np.isnan(recall[i]) else 0.0,
                    'precision': float(precision[i]) if not np.isnan(precision[i]) else 0.0,
                    'f1': float(f1[i]) if not np.isnan(f1[i]) else 0.0,
                    'bbox_iou': class_bbox_iou,  # Per-class average
                    'bbox_dice': class_bbox_dice,  # Per-class average
                    'tp': int(tp[i]),
                    'fp': int(fp[i]),
                    'fn': int(fn[i]),
                }

        # New format matching ArgusVision structure
        overall_metrics = {
            'config': {
                'dataset': results_dir,
                'num_images': len(all_metrics),
                'total_gt': total_gt,
                'total_detections': total_detections,
                'matched_pairs': matched_pairs,
            },
            'overall': {
                'bbox_iou': overall_mean_iou,
                'bbox_dice': overall_mean_dice,
                'std_bbox_iou': overall_std_iou,
                'std_bbox_dice': overall_std_dice,
                'mean_recall': mean_recall,
                'mean_precision': mean_precision,
                'mean_f1': mean_f1,
            },
            'per_class': per_class_metrics,
            'timing': {
                'avg_inference_ms': overall_avg_time,
            },
            # Legacy format for backward compatibility
            'mean_iou': overall_mean_iou,
            'mean_dice': overall_mean_dice,
            'map': dataset_map,
            'avg_inference_time_ms': overall_avg_time,
        }

        # Save best and worst examples PER CLASS
        if examples_data:
            # Load GSD mapping
            gsd_file = Path("dataset/dota_gsd_mapping.json")
            gsd_mapping = {}
            if gsd_file.exists():
                with open(gsd_file) as f:
                    gsd_mapping = json.load(f)
            
            # Group examples by classes present
            per_class_examples = defaultdict(list)
            for example in examples_data:
                # Get unique classes in this image
                classes_in_image = set()
                for gt in example['ground_truth']:
                    classes_in_image.add(gt['class_id'])
                for pred in example['predictions']:
                    classes_in_image.add(pred['class_id'])
                
                # Calculate per-class F1 for each class in this image
                for class_id in classes_in_image:
                    if 'per_class_counts' in example['metrics']:
                        counts = example['metrics']['per_class_counts'][class_id]
                        tp, fp, fn = counts['tp'], counts['fp'], counts['fn']
                        
                        # Calculate F1 for this class in this image
                        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
                        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
                        class_f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
                        
                        per_class_examples[class_id].append({
                            'example': example,
                            'class_f1': class_f1,
                            'class_id': class_id
                        })
            
            # Create directories for per-class examples
            base_examples_dir = Path(results_dir) / "examples" / self.model_name
            best_per_class_dir = base_examples_dir / "best_per_class"
            worst_per_class_dir = base_examples_dir / "worst_per_class"
            best_per_class_dir.mkdir(parents=True, exist_ok=True)
            worst_per_class_dir.mkdir(parents=True, exist_ok=True)
            
            class_name_dict = {
                i: (names[i] if names is not None and i < len(names) else str(i))
                for i in range(num_classes)
            }
            
            # For each class, save best and worst
            for class_id, examples_list in per_class_examples.items():
                if not examples_list:
                    continue
                
                # Sort by class F1
                examples_list.sort(key=lambda x: x['class_f1'])
                
                best_example = examples_list[-1]['example']  # Highest F1
                worst_example = examples_list[0]['example']  # Lowest F1
                
                class_name = class_name_dict.get(class_id, str(class_id))
                
                # Get GSD for the images
                best_gsd = gsd_mapping.get(best_example['image_id'], None)
                worst_gsd = gsd_mapping.get(worst_example['image_id'], None)
                
                # Save best example for this class
                best_filename = f"{class_name}_{best_example['image_id']}"
                save_detection_examples(
                    image_id=best_filename,
                    model_name=self.model_name,
                    image=best_example['image'],
                    predictions=best_example['predictions'],
                    ground_truth=best_example['ground_truth'],
                    class_names=class_name_dict,
                    metrics=best_example['metrics'],
                    output_dir=str(best_per_class_dir),
                    is_obb=(self.mode == "obb"),
                    gsd=best_gsd,
                )
                
                # Save worst example for this class
                worst_filename = f"{class_name}_{worst_example['image_id']}"
                save_detection_examples(
                    image_id=worst_filename,
                    model_name=self.model_name,
                    image=worst_example['image'],
                    predictions=worst_example['predictions'],
                    ground_truth=worst_example['ground_truth'],
                    class_names=class_name_dict,
                    metrics=worst_example['metrics'],
                    output_dir=str(worst_per_class_dir),
                    is_obb=(self.mode == "obb"),
                    gsd=worst_gsd,
                )

        save_metrics(overall_metrics, self.model_name, results_dir)
        return overall_metrics
