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
                            is_obb: bool = False,
                            gsd: float = None):
    """
    Filename: <image>_<model>_iou_<xx>_dice_<yy>_map_<zz>.png
    (mAP is the per-image mAP over *present* classes only)
    
    Args:
        gsd: Ground Sample Distance in meters (optional)
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    metrics_str = f"iou_{metrics['mean_iou']:.3f}_dice_{metrics['mean_dice']:.3f}_map_{metrics['map']:.3f}"
    filename = f"{image_id}_{model_name}_{metrics_str}.png"
    save_path = output_dir / filename

    image_bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR) if image.shape[-1] == 3 else image
    vis = visualize_detections(image_bgr, predictions, ground_truth, class_names, is_obb=is_obb)
    
    # Calculate per-class stats for this image
    class_stats = {}
    for gt in ground_truth:
        cid = gt["class_id"]
        if cid not in class_stats:
            class_stats[cid] = {'gt': 0, 'pred': 0, 'tp': 0}
        class_stats[cid]['gt'] += 1
    
    for pred in predictions:
        cid = pred["class_id"]
        if cid not in class_stats:
            class_stats[cid] = {'gt': 0, 'pred': 0, 'tp': 0}
        class_stats[cid]['pred'] += 1
    
    # Use per_class_counts from metrics for accurate TP
    if 'per_class_counts' in metrics:
        for idx, counts in enumerate(metrics['per_class_counts']):
            if counts['tp'] > 0 or counts['fp'] > 0 or counts['fn'] > 0:
                if idx in class_stats:
                    class_stats[idx]['tp'] = counts['tp']
    
    # Build title with per-class results
    h, w = vis.shape[:2]
    
    # Calculate scale factor based on image width (reference: 800px)
    scale_factor = max(0.5, min(3.0, w / 800.0))  # Clamp between 0.5x and 3.0x
    
    # Row 1: Model, Image name, and GSD (centered, bold)
    if gsd is not None:
        row1 = f"{model_name}  |  {image_id}  |  GSD: {gsd:.2f}m"
    else:
        row1 = f"{model_name}  |  {image_id}"
    
    # Build per-class lines in new multi-line format
    class_lines = []
    for cid in sorted(class_stats.keys()):
        cname = class_names.get(cid, f"Class{cid}")
        stats = class_stats[cid]
        gt_count = stats['gt']
        det_count = stats['pred']
        tp = stats['tp']
        
        # Calculate per-class metrics
        precision = (tp / det_count * 100) if det_count > 0 else 0.0
        recall = (tp / gt_count * 100) if gt_count > 0 else 0.0
        
        # Get per-class IoU/DICE if available
        per_class_iou = 0.0
        per_class_dice = 0.0
        if 'per_class_ious' in metrics and cid < len(metrics['per_class_ious']):
            ious = metrics['per_class_ious'][cid]
            per_class_iou = (np.mean(ious) * 100) if ious else 0.0
        if 'per_class_dices' in metrics and cid < len(metrics['per_class_dices']):
            dices = metrics['per_class_dices'][cid]
            per_class_dice = (np.mean(dices) * 100) if dices else 0.0
        
        # Multi-line format (3 lines per class):
        # Line 1: Class name (bold)
        class_lines.append(('bold', f"{cname}:"))
        # Line 2: Detection counts and Precision
        class_lines.append(('normal', f"Det: {tp}/{gt_count} | Prec: {precision:.2f}%"))
        # Line 3: Recall, IoU, DICE
        class_lines.append(('normal', f"Rec: {recall:.2f}% | IoU: {per_class_iou:.2f}% | DICE: {per_class_dice:.2f}%"))
    
    # Scale font sizes and spacing based on image width
    line_height = int(30 * scale_factor)
    title_height = line_height * (1 + len(class_lines)) + int(25 * scale_factor)
    
    # Create white background for title
    titled_vis = np.ones((h + title_height, w, 3), dtype=np.uint8) * 255
    titled_vis[title_height:, :] = vis
    
    # Font settings - clean, readable fonts without excessive bold
    font_scale_classes = 0.5 * scale_factor
    font_scale_row1 = font_scale_classes * 1.5  # Model|image is 1.5× bigger than class font
    
    # Clean thickness - no bold multipliers that make text ugly
    thickness_row1 = max(1, int(1.5 * scale_factor))  # Title - slightly thicker but not bold
    thickness_bold = max(1, int(1.2 * scale_factor))   # Class names - slightly thicker
    thickness_normal = 1  # Metrics - always 1px for cleanest look
    
    left_margin = int(10 * scale_factor)
    
    # Draw Row 1 (centered)
    (text_w, text_h), _ = cv2.getTextSize(row1, cv2.FONT_HERSHEY_SIMPLEX, font_scale_row1, thickness_row1)
    text_x = (w - text_w) // 2
    y_offset = int(30 * scale_factor)
    cv2.putText(titled_vis, row1, (text_x, y_offset),
                cv2.FONT_HERSHEY_SIMPLEX, font_scale_row1, (0, 0, 0), thickness_row1, cv2.LINE_AA)
    
    # Draw per-class results (left-justified, class names bold)
    for style, class_line in class_lines:
        y_offset += line_height
        thickness = thickness_bold if style == 'bold' else thickness_normal
        cv2.putText(titled_vis, class_line, (left_margin, y_offset),
                    cv2.FONT_HERSHEY_SIMPLEX, font_scale_classes, (0, 0, 0), thickness, cv2.LINE_AA)
    
    cv2.imwrite(str(save_path), titled_vis)
