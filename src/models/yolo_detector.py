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

        examples_dir = Path(results_dir) / "examples" / self.model_name
        examples_dir.mkdir(parents=True, exist_ok=True)

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
                    
                    m = self.evaluate_image(
                        img, gts, num_classes,
                        save_dir=str(examples_dir),
                        image_id=image_id,
                        class_names=names,
                    )
                    all_metrics.append(m)
                    per_image_counts.append(m["per_class_counts"])
                    
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

                m = self.evaluate_image(
                    img,
                    gts,
                    num_classes,
                    save_dir=str(examples_dir),
                    image_id=Path(img_path).stem,
                    class_names=names,
                )
                all_metrics.append(m)
                per_image_counts.append(m["per_class_counts"])

        # -------- aggregate (dataset-level) --------
        mean_iou_values = [m["mean_iou"] for m in all_metrics]
        mean_dice_values = [m["mean_dice"] for m in all_metrics]
        times = [m.get("inference_time_ms", 0.0) for m in all_metrics]

        overall_mean_iou = float(np.mean(mean_iou_values)) if mean_iou_values else 0.0
        overall_mean_dice = float(np.mean(mean_dice_values)) if mean_dice_values else 0.0
        overall_avg_time = float(np.mean(times)) if times else 0.0

        # sum tp/fp/fn across images
        counts = np.array([[(c["tp"], c["fp"], c["fn"]) for c in per_img] for per_img in per_image_counts],
                          dtype=np.int64)  # (N, C, 3)
        summed = counts.sum(axis=0) if len(counts) else np.zeros((num_classes, 3), dtype=np.int64)
        tp, fp, fn = summed[:, 0].astype(float), summed[:, 1].astype(float), summed[:, 2].astype(float)

        with np.errstate(divide="ignore", invalid="ignore"):
            precision = np.divide(tp, tp + fp, where=(tp + fp) > 0)
            recall    = np.divide(tp, tp + fn, where=(tp + fn) > 0)
            f1        = np.divide(2 * precision * recall, precision + recall, where=(precision + recall) > 0)

        # keep only allowed classes for MAP
        allowed_ids = self.allowed_class_ids if self.allowed_class_ids is not None else set(range(num_classes))
        existed = ((tp + fp + fn) > 0) & np.isin(np.arange(num_classes), list(allowed_ids))
        dataset_map = float(np.nanmean(f1[existed])) if np.any(existed) else 0.0

        # expose class_aps as dict keyed by class name
        class_aps_named = {
            (names[i] if names is not None and i < len(names) else str(i)):
                float(f1[i]) if not np.isnan(f1[i]) else 0.0
            for i in range(num_classes) if i in allowed_ids
        }

        overall_metrics = {
            "mean_iou": overall_mean_iou,
            "mean_dice": overall_mean_dice,
            "map": dataset_map,
            "class_aps": class_aps_named,                # <- dict with names
            "avg_inference_time_ms": overall_avg_time,
        }

        save_metrics(overall_metrics, self.model_name, results_dir)
        return overall_metrics
