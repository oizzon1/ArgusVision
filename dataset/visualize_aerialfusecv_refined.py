"""
Visualization script for AerialFuseCV_Refined (with train/val splits)

Visualizes bbox-mask alignment for the refined dataset with split structure.

Usage:
  python dataset/visualize_aerialfusecv_refined.py --split train --max-images 10
  python dataset/visualize_aerialfusecv_refined.py --split val --max-images 10
"""

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

import cv2
import numpy as np
from PIL import Image


# Class → color mapping (RGB)
CLASS_COLORS = {
    "small-vehicle": (0, 0, 127),
    "large-vehicle": (0, 127, 127),
    "harbor": (0, 100, 155),
    "ship": (0, 0, 63),
    "ground-track-field": (0, 63, 255),
    "soccer-ball-field": (0, 127, 191),
    "baseball-diamond": (0, 63, 0),
    "swimming-pool": (0, 0, 255),
    "roundabout": (0, 191, 127),
    "tennis-court": (0, 63, 127),
    "basketball-court": (0, 63, 191),
    "plane": (0, 127, 255),
    "helicopter": (0, 0, 191),
    "bridge": (0, 127, 63),
    "storage-tank": (0, 63, 63),
}

COLOR_TO_CLASS = {v: k for k, v in CLASS_COLORS.items()}
CLASS_LIST = list(CLASS_COLORS.keys())


def load_labels(label_path: Path):
    """Load DOTA-format labels; return list of (class_name, bbox) with bbox axis-aligned [x1,y1,x2,y2]."""
    labels = []
    if not label_path.exists():
        return labels
    with label_path.open("r") as f:
        for line in f:
            parts = line.strip().split()
            if not parts or parts[0] in ("imagesource:", "gsd:"):
                continue
            if len(parts) < 10:
                continue
            try:
                xs = [float(parts[i]) for i in range(0, 8, 2)]
                ys = [float(parts[i]) for i in range(1, 8, 2)]
                cls = parts[8]
            except ValueError:
                continue
            x1, x2 = min(xs), max(xs)
            y1, y2 = min(ys), max(ys)
            labels.append((cls, (x1, y1, x2, y2)))
    return labels


def classes_from_mask(mask_path: Path):
    """Return set of class names present in the RGB mask."""
    if not mask_path.exists():
        return set(), Counter()
    img = Image.open(mask_path).convert("RGB")
    colors = img.getcolors(maxcolors=256 * 256)
    if not colors:
        return set(), Counter()
    present = set()
    extras = Counter()
    for _, color in colors:
        if color in COLOR_TO_CLASS:
            present.add(COLOR_TO_CLASS[color])
        else:
            extras[color] += 1
    return present, extras


def overlay_mask(image_bgr: np.ndarray, mask_rgb: np.ndarray, alpha=0.35):
    """Overlay semantic mask colors on the image."""
    overlay = image_bgr.copy()
    for color_rgb in set(map(tuple, mask_rgb.reshape(-1, 3))):
        if color_rgb == (0, 0, 0):
            continue
        mask = np.all(mask_rgb == color_rgb, axis=-1)
        if not mask.any():
            continue
        color_bgr = tuple(int(c) for c in color_rgb[::-1])
        overlay[mask] = (
            overlay[mask].astype(np.float32) * (1 - alpha)
            + np.array(color_bgr, dtype=np.float32) * alpha
        ).astype(np.uint8)
    return overlay


def draw_bboxes(image_bgr: np.ndarray, labels):
    """Draw axis-aligned bboxes."""
    out = image_bgr.copy()
    for cls, (x1, y1, x2, y2) in labels:
        color = CLASS_COLORS.get(cls, (255, 255, 255))
        color_bgr = (color[2], color[1], color[0])
        cv2.rectangle(out, (int(x1), int(y1)), (int(x2), int(y2)), color_bgr, 2)
        cv2.putText(out, cls, (int(x1), int(y1) - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color_bgr, 1, cv2.LINE_AA)
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=str, default="dataset/AerialFuseCV_Refined", 
                       help="Dataset root with train/val splits")
    parser.add_argument("--split", type=str, default="train", choices=["train", "val"],
                       help="Which split to visualize")
    parser.add_argument("--output", type=str, default="results/aerialfusecv_refined_visualizations", 
                       help="Where to save overlays")
    parser.add_argument("--max-images", type=int, default=10, 
                       help="Limit overlays to this many images (set -1 for all)")
    args = parser.parse_args()

    root = Path(args.root)
    images_dir = root / args.split / "images"
    labels_dir = root / args.split / "labels"
    masks_dir = root / args.split / "semantic_masks"
    out_dir = Path(args.output) / args.split
    out_dir.mkdir(parents=True, exist_ok=True)

    image_files = sorted(images_dir.glob("*.png"))
    if args.max_images > 0:
        image_files = image_files[: args.max_images]

    per_class = defaultdict(lambda: {"labels": 0, "masks": 0, "both": 0, "label_only": 0, "mask_only": 0})
    extra_colors = Counter()
    missing_masks_total = 0
    missing_labels_total = 0

    print(f"\n{'='*60}")
    print(f"Visualizing {args.split} split from {args.root}")
    print(f"Processing {len(image_files)} images...")
    print(f"{'='*60}\n")

    for img_path in image_files:
        img_name = img_path.stem
        label_path = labels_dir / f"{img_name}.txt"
        mask_path = masks_dir / f"{img_name}_instance_color_RGB.png"

        labels = load_labels(label_path)
        label_classes = {cls for cls, _ in labels}

        mask_classes, extras = classes_from_mask(mask_path)
        extra_colors.update(extras)

        # Update per-class tallies
        for cls in label_classes:
            per_class[cls]["labels"] += 1
        for cls in mask_classes:
            per_class[cls]["masks"] += 1
        for cls in label_classes & mask_classes:
            per_class[cls]["both"] += 1
        for cls in label_classes - mask_classes:
            per_class[cls]["label_only"] += 1
            missing_masks_total += 1
        for cls in mask_classes - label_classes:
            per_class[cls]["mask_only"] += 1
            missing_labels_total += 1

        # Build overlay
        image_bgr = cv2.imread(str(img_path))
        if image_bgr is None or not mask_path.exists():
            print(f"⚠️  Skipping {img_name}: Missing image or mask")
            continue
        
        mask_rgb = cv2.cvtColor(cv2.imread(str(mask_path)), cv2.COLOR_BGR2RGB)
        overlay = overlay_mask(image_bgr, mask_rgb, alpha=0.35)
        overlay = draw_bboxes(overlay, labels)
        
        output_path = out_dir / f"{img_name}_overlay.png"
        cv2.imwrite(str(output_path), overlay)
        print(f"✅ Saved: {output_path.name}")

    # Save summary
    summary = {
        "split": args.split,
        "images_processed": len(image_files),
        "missing_masks_total": missing_masks_total,
        "missing_labels_total": missing_labels_total,
        "per_class": per_class,
        "extra_colors": extra_colors,
    }
    summary_path = out_dir / "alignment_summary.json"
    # Convert defaultdict/Counter to plain dict for JSON
    summary["per_class"] = {k: dict(v) for k, v in per_class.items()}
    summary["extra_colors"] = {str(k): v for k, v in extra_colors.items()}
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\n{'='*60}")
    print(f"✅ Saved {len(image_files)} overlays to {out_dir}")
    print(f"✅ Alignment summary: {summary_path}")
    
    # Print quick summary
    print(f"\n📊 Quick Summary ({args.split}):")
    print(f"   Images: {len(image_files)}")
    print(f"   Missing masks: {missing_masks_total}")
    print(f"   Missing labels: {missing_labels_total}")
    print(f"   Classes present: {len([k for k, v in per_class.items() if v['both'] > 0])}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
