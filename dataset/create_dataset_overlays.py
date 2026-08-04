"""
Create visual overlays for every image in an AerialFuseCV-style dataset.

For each image, the script:
  - loads the image, its DOTA-format label file, and the RGB semantic mask;
  - overlays the mask colors and draws the bounding boxes;
  - writes the composite into a clone folder, preserving the split structure.

Usage example:
    python dataset/create_dataset_overlays.py \
        --source dataset/AerialFuseCV \
        --output results/experimental/AerialFuseCV_Testing/visualizations/overlays \
        --alpha 0.35
"""

from pathlib import Path
import argparse
import shutil

import cv2
import numpy as np
from tqdm import tqdm


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


def load_labels(label_path: Path):
    """Return list of (class_name, (x1,y1,x2,y2)) from a DOTA-format label file."""
    if not label_path.exists():
        return []
    boxes = []
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
            boxes.append((cls, (int(x1), int(y1), int(x2), int(y2))))
    return boxes


def overlay_mask(image_bgr: np.ndarray, mask_path: Path, alpha: float):
    """Blend the RGB mask onto the image. Returns blended image; if mask missing, return original."""
    if not mask_path.exists():
        return image_bgr
    mask_bgr = cv2.imread(str(mask_path))
    if mask_bgr is None:
        return image_bgr
    mask_nonzero = np.any(mask_bgr != 0, axis=-1)
    if not mask_nonzero.any():
        return image_bgr
    blended = image_bgr.copy().astype(np.float32)
    blended[mask_nonzero] = (
        blended[mask_nonzero] * (1.0 - alpha) + mask_bgr[mask_nonzero].astype(np.float32) * alpha
    )
    return blended.astype(np.uint8)


def draw_bboxes(image_bgr: np.ndarray, labels):
    """Draw axis-aligned bboxes on the image."""
    out = image_bgr.copy()
    for cls, (x1, y1, x2, y2) in labels:
        color_rgb = CLASS_COLORS.get(cls)
        color_bgr = (color_rgb[2], color_rgb[1], color_rgb[0]) if color_rgb else (255, 255, 255)
        cv2.rectangle(out, (x1, y1), (x2, y2), color_bgr, 2)
        cv2.putText(out, cls, (x1, max(15, y1 - 4)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color_bgr, 1, cv2.LINE_AA)
    return out


def process_split(images_dir: Path, labels_dir: Path, masks_dir: Path, overlays_dir: Path, alpha: float, desc: str):
    """Process a dataset split given explicit directories."""
    if not images_dir.exists():
        return 0
    overlays_dir.mkdir(parents=True, exist_ok=True)

    count = 0
    for img_path in tqdm(sorted(images_dir.glob("*.png")), desc=f"{desc} overlays"):
        image = cv2.imread(str(img_path))
        if image is None:
            continue
        labels = load_labels(labels_dir / f"{img_path.stem}.txt")
        overlay = overlay_mask(image, masks_dir / f"{img_path.stem}_instance_color_RGB.png", alpha)
        overlay = draw_bboxes(overlay, labels)
        cv2.imwrite(str(overlays_dir / img_path.name), overlay)
        count += 1
    return count


def clone_structure(source_root: Path, output_root: Path):
    """Optional: copy labels + masks into clone directory for reference."""
    candidates = []
    # hierarchical (train/val)
    for split in ("train", "val"):
        for sub in ("labels_obb", "semantic_masks"):
            candidates.append((source_root / split / sub, output_root / split / sub))
    # flat
    for sub in ("labels_obb", "semantic_masks"):
        candidates.append((source_root / sub, output_root / sub))

    for src_dir, dst_dir in candidates:
            if src_dir.exists():
                if dst_dir.exists():
                    continue
                shutil.copytree(src_dir, dst_dir)


def main():
    parser = argparse.ArgumentParser(description="Create overlay visualizations for AerialFuseCV-style dataset.")
    parser.add_argument("--source", default="dataset/AerialFuseCV", help="Source dataset root.")
    parser.add_argument("--output", default="results/experimental/AerialFuseCV_Testing/visualizations/overlays", help="Destination clone folder.")
    parser.add_argument("--alpha", type=float, default=0.35, help="Mask overlay alpha.")
    parser.add_argument("--copy-metadata", action="store_true", help="Copy labels/masks into the clone for reference.")
    args = parser.parse_args()

    src = Path(args.source)
    dst = Path(args.output)
    if not src.exists():
        raise SystemExit(f"Source directory {src} does not exist.")
    dst.mkdir(parents=True, exist_ok=True)

    total = 0
    has_split = (src / "train" / "images").exists() or (src / "val" / "images").exists()
    if has_split:
        for split in ("train", "val"):
            total += process_split(
                src / split / "images",
                src / split / "labels_obb",
                src / split / "semantic_masks",
                dst / split / "images",
                args.alpha,
                split,
            )
    else:
        total += process_split(
            src / "images",
            src / "labels_obb",
            src / "semantic_masks",
            dst / "images",
            args.alpha,
            "all",
        )

    if args.copy_metadata:
        clone_structure(src, dst)

    print(f"Overlay generation finished: {total} images written to {dst}")


if __name__ == "__main__":
    main()
