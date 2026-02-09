import numpy as np
import json
from typing import List, Dict, Union
from pathlib import Path
from shapely.geometry import Polygon, box as shapely_box
import numpy as np
import json
from typing import List, Dict, Union
from pathlib import Path
from shapely.geometry import Polygon, box as shapely_box
import warnings

warnings.filterwarnings("ignore", category=RuntimeWarning)


# ----------------------------- DICE (from IoU) -----------------------------
def calculate_dice(iou: float) -> float:
    """
    Calculate DICE coefficient from IoU.
    DICE = 2*IoU / (1 + IoU)
    """
    if iou <= 0:
        return 0.0
    return (2.0 * iou) / (1.0 + iou)

# ----------------------------- IoU (Bounding Box) -----------------------------
def calculate_iou(b1: List[float], b2: List[float]) -> float:
    """
    Calculates Intersection over Union (IoU) for bounding boxes.
    Supports:
      - VBB: [x_min, y_min, x_max, y_max]
      - OBB: [x1, y1, x2, y2, x3, y3, x4, y4]
    """
    if len(b1) == 4 and len(b2) == 4:
        poly1 = shapely_box(b1[0], b1[1], b1[2], b1[3])
        poly2 = shapely_box(b2[0], b2[1], b2[2], b2[3])
    elif len(b1) == 8 and len(b2) == 8:
        poly1 = Polygon([(b1[i], b1[i + 1]) for i in range(0, 8, 2)])
        poly2 = Polygon([(b2[i], b2[i + 1]) for i in range(0, 8, 2)])
    else:
        return 0.0

    if not poly1.is_valid or not poly2.is_valid:
        return 0.0

    inter = poly1.intersection(poly2).area
    union = poly1.union(poly2).area
    return inter / union if union > 0 else 0.0


# ----------------------------- IoU & DICE (Mask) -----------------------------
def calculate_mask_iou(mask1: np.ndarray, mask2: np.ndarray) -> float:
    """
    Calculates Intersection over Union (IoU) for binary segmentation masks.
    Args:
        mask1 (np.ndarray): First binary mask (boolean or 0/1).
        mask2 (np.ndarray): Second binary mask (boolean or 0/1).
    Returns:
        float: IoU score.
    """
    if mask1.shape != mask2.shape:
        raise ValueError("Masks must have the same shape for IoU calculation.")

    intersection = np.logical_and(mask1, mask2).sum()
    union = np.logical_or(mask1, mask2).sum()

    if union == 0:
        return 0.0  # No union, no intersection, so IoU is 0

    return intersection / union

def calculate_mask_dice(mask1: np.ndarray, mask2: np.ndarray) -> float:
    """
    Calculates the DICE coefficient for binary segmentation masks.
    Args:
        mask1 (np.ndarray): First binary mask (boolean or 0/1).
        mask2 (np.ndarray): Second binary mask (boolean or 0/1).
    Returns:
        float: DICE score.
    """
    if mask1.shape != mask2.shape:
        raise ValueError("Masks must have the same shape for DICE calculation.")

    intersection = np.logical_and(mask1, mask2).sum()
    
    # Sum of areas of both masks
    sum_areas = mask1.sum() + mask2.sum()

    if sum_areas == 0:
        return 0.0 # No masks, so DICE is 0

    return (2.0 * intersection) / sum_areas


# --------------------------- Bounding Box Metrics ---------------------------
def calculate_bbox_metrics(predictions: List[Dict],
                           ground_truth: List[Dict],
                           num_classes: int,
                           iou_threshold: float = 0.1) -> Dict[str, Union[float, List[float], Dict]]: #NOTE IoU threshold is lowered to 0.1 to account for DOTA annotation errors
    """
    Returns (per-image) bounding box metrics:
      mean_iou, mean_dice,
      class_precision, class_recall, class_f1, class_aps (alias of class_f1),
      per_class_counts (tp/fp/fn for each class),
      map  (macro-avg of class_f1 **only over classes present in this image**)
    
    Args:
        predictions: List of predicted bboxes
        ground_truth: List of ground truth bboxes
        num_classes: Number of classes
        iou_threshold: IoU threshold for matching (default 0.1, too lenient, due to DOTA wide annotation errors. Standard would be 0.5 or 0.3)
    """
    if not predictions and not ground_truth:
        return {
            "mean_iou": 0.0,
            "mean_dice": 0.0,
            "class_precision": [0.0] * num_classes,
            "class_recall":    [0.0] * num_classes,
            "class_f1":        [0.0] * num_classes,
            "class_aps":       [0.0] * num_classes,  # alias
            "per_class_counts": [{"tp": 0, "fp": 0, "fn": 0} for _ in range(num_classes)],
            "map": 0.0,
        }

    ious, dices = [], []
    per_class_ious = [[] for _ in range(num_classes)]  # Track IoU per class
    per_class_dices = [[] for _ in range(num_classes)]  # Track DICE per class
    counts = np.zeros((num_classes, 3), dtype=np.int64)  # (tp, fp, fn)
    matched_gt = set()

    # best-match each prediction to a GT of the same class
    for pred in predictions:
        pred_bbox = pred["bbox"]; pred_class = pred["class_id"]
        best_iou, best_idx = 0.0, -1
        for i, gt in enumerate(ground_truth):
            if i in matched_gt or gt["class_id"] != pred_class:
                continue
            iou = calculate_iou(pred_bbox, gt["bbox"])
            if iou > best_iou:
                best_iou, best_idx = iou, i

        if best_iou >= iou_threshold and best_idx >= 0:
            counts[pred_class, 0] += 1  # tp
            matched_gt.add(best_idx)
            # Track per-class IoU/DICE for matched pairs only
            per_class_ious[pred_class].append(best_iou)
            per_class_dices[pred_class].append(calculate_dice(best_iou))
        else:
            counts[pred_class, 1] += 1  # fp

        ious.append(best_iou)
        dices.append(calculate_dice(best_iou))

    # false negatives
    for i, gt in enumerate(ground_truth):
        if i not in matched_gt:
            counts[gt["class_id"], 2] += 1

    tp = counts[:, 0].astype(float)
    fp = counts[:, 1].astype(float)
    fn = counts[:, 2].astype(float)

    precision = np.full(num_classes, np.nan)
    recall    = np.full(num_classes, np.nan)
    f1        = np.full(num_classes, np.nan)

    pos = (tp + fp) > 0
    precision[pos] = tp[pos] / (tp[pos] + fp[pos])
    pos = (tp + fn) > 0
    recall[pos] = tp[pos] / (tp[pos] + fn[pos])
    pos = (~np.isnan(precision)) & (~np.isnan(recall)) & ((precision + recall) > 0)
    f1[pos] = 2 * precision[pos] * recall[pos] / (precision + recall)[pos]

    # classes present in this image (any tp/fp/fn)
    present = (tp + fp + fn) > 0
    map_val = float(np.nanmean(f1[present])) if np.any(present) else 0.0

    return {
        "mean_iou": float(np.nanmean(ious)) if ious else 0.0,
        "mean_dice": float(np.nanmean(dices)) if dices else 0.0,
        "class_precision": [float(x) if not np.isnan(x) else 0.0 for x in precision],
        "class_recall":    [float(x) if not np.isnan(x) else 0.0 for x in recall],
        "class_f1":        [float(x) if not np.isnan(x) else 0.0 for x in f1],
        "class_aps":       [float(x) if not np.isnan(x) else 0.0 for x in f1],  # alias
        "per_class_counts": [{"tp": int(t), "fp": int(p), "fn": int(n)} for t, p, n in counts],
        "per_class_ious": per_class_ious,  # List of lists: IoU values per class
        "per_class_dices": per_class_dices,  # List of lists: DICE values per class
        "map": map_val,
    }


# ---------------------------- Saving ---------------------------
def save_metrics(metrics: Dict[str, float], model_name: str, output_dir: str) -> None:
    out = Path(output_dir) / f"{model_name}_metrics.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w") as f:
        json.dump(metrics, f, indent=4)


def save_metrics_summary(all_metrics: Dict[str, Dict], output_dir: str) -> None:
    out = Path(output_dir) / "metrics_summary.json"
    with open(out, "w") as f:
        json.dump(all_metrics, f, indent=4)
