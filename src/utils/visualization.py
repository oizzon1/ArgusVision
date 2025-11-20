import os
from pathlib import Path
import cv2
import numpy as np
from typing import Dict, List


# ------------------------------- Drawing -------------------------------
def draw_vbb(image, bbox, label, color=(255, 0, 0)):
    x1, y1, x2, y2 = map(int, bbox)
    cv2.rectangle(image, (x1, y1), (x2, y2), color, 2)
    cv2.putText(image, label, (x1, max(0, y1 - 5)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA)
    return image


def draw_obb(image, bbox, label, color=(0, 255, 0)):
    """
    Draw an oriented bbox given 4 polygon points (x1,y1,...,x4,y4).
    Robust to OpenCV hull output shape (k,1,2).
    """
    # 1) make Nx2 points
    pts = np.asarray(bbox, dtype=np.float32).reshape(-1, 2)

    # 2) get convex hull, then reshape to (k, 2)
    hull = cv2.convexHull(pts.astype(np.int32))          # -> (k,1,2)
    hull = np.squeeze(hull, axis=1)                      # -> (k,2)

    # guard (shouldn’t happen for 4-pt polys, but safe)
    if hull.ndim != 2 or hull.shape[0] < 2:
        return image

    # 3) draw
    cv2.polylines(image, [hull], isClosed=True, color=color, thickness=2)

    # 4) put label at first vertex
    x, y = int(hull[0, 0]), int(hull[0, 1])
    cv2.putText(image, label, (x, max(0, y - 5)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA)
    return image



# ----------------------------- Visualization -----------------------------
def visualize_detections(image, predictions: List[Dict], ground_truth: List[Dict],
                         class_names: Dict[int, str], is_obb: bool = False):
    image_vis = image.copy()

    # GT green
    for gt in ground_truth:
        cid = gt["class_id"]
        label = f"GT: {class_names.get(cid, str(cid))}"
        image_vis = (draw_obb if is_obb else draw_vbb)(image_vis, gt["bbox"], label, color=(0, 255, 0))

    # Predictions red
    for pred in predictions:
        cid = pred["class_id"]
        conf = pred.get("confidence", 1.0)
        label = f"Pred: {class_names.get(cid, str(cid))} {conf:.2f}"
        image_vis = (draw_obb if is_obb else draw_vbb)(image_vis, pred["bbox"], label, color=(255, 0, 0))

    return image_vis


# ------------------------------- Saving -------------------------------
def save_detection_examples(image_id: str, model_name: str,
                            image, predictions: List[Dict],
                            ground_truth: List[Dict],
                            class_names: Dict[int, str],
                            metrics: Dict, output_dir: str,
                            is_obb: bool = False):
    """
    Filename: <image>_<model>_iou_<xx>_dice_<yy>_map_<zz>.png
    (mAP is the per-image mAP over *present* classes only)
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    metrics_str = f"iou_{metrics['mean_iou']:.3f}_dice_{metrics['mean_dice']:.3f}_map_{metrics['map']:.3f}"
    filename = f"{image_id}_{model_name}_{metrics_str}.png"
    save_path = output_dir / filename

    image_bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR) if image.shape[-1] == 3 else image
    vis = visualize_detections(image_bgr, predictions, ground_truth, class_names, is_obb=is_obb)
    cv2.imwrite(str(save_path), vis)
