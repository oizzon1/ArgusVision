"""
Generate quick DOTA visualizations: original image, OBB overlay, and VBB overlay.

Example:
  python dataset/visualize_dota_boxes.py ^
    --image dataset/DOTA_v1/train/images/P0000.png ^
    --labels dataset/DOTA_v1/train/labels/P0000.txt ^
    --outdir results/dota_example
"""

from __future__ import annotations

from pathlib import Path
import argparse

import cv2
import numpy as np


RED_BGR = (0, 0, 255)


def _to_bgr(color_rgb: tuple[int, int, int]) -> tuple[int, int, int]:
    r, g, b = color_rgb
    return (b, g, r)


def load_dota_obb_labels(label_path: Path) -> list[tuple[str, np.ndarray]]:
    """
    Parse DOTA label file.
    Returns list of (class_name, points) where points is (4,2) float32 array.
    """
    if not label_path.exists():
        raise FileNotFoundError(f"Label file not found: {label_path}")

    items: list[tuple[str, np.ndarray]] = []
    with label_path.open("r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split()
            if not parts or parts[0] in ("imagesource:", "gsd:"):
                continue
            if len(parts) < 10:
                continue
            try:
                coords = [float(x) for x in parts[:8]]
            except ValueError:
                continue
            class_name = parts[8]
            points = np.array(coords, dtype=np.float32).reshape(4, 2)
            items.append((class_name, points))
    return items


def draw_obb(image_bgr: np.ndarray, labels: list[tuple[str, np.ndarray]], thickness: int) -> np.ndarray:
    out = image_bgr.copy()
    for class_name, points in labels:
        color = RED_BGR
        poly = np.round(points).astype(np.int32).reshape((-1, 1, 2))
        cv2.polylines(out, [poly], isClosed=True, color=color, thickness=thickness, lineType=cv2.LINE_AA)
        x, y = poly[0, 0]
        cv2.putText(
            out,
            class_name,
            (int(x), max(15, int(y) - 4)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            color,
            max(1, thickness // 2),
            cv2.LINE_AA,
        )
    return out


def draw_vbb(image_bgr: np.ndarray, labels: list[tuple[str, np.ndarray]], thickness: int) -> np.ndarray:
    out = image_bgr.copy()
    for class_name, points in labels:
        color = RED_BGR
        xs = points[:, 0]
        ys = points[:, 1]
        x1, y1 = int(np.floor(xs.min())), int(np.floor(ys.min()))
        x2, y2 = int(np.ceil(xs.max())), int(np.ceil(ys.max()))
        cv2.rectangle(out, (x1, y1), (x2, y2), color, thickness, lineType=cv2.LINE_AA)
        cv2.putText(
            out,
            class_name,
            (x1, max(15, y1 - 4)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            color,
            max(1, thickness // 2),
            cv2.LINE_AA,
        )
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Visualize DOTA OBB and derived VBB for a single image.")
    parser.add_argument("--image", required=True, help="Path to a DOTA image (.png).")
    parser.add_argument("--labels", required=True, help="Path to a DOTA label file (.txt).")
    parser.add_argument("--outdir", default="results/dota_example", help="Output directory.")
    parser.add_argument("--prefix", default=None, help="Output filename prefix (defaults to image stem).")
    parser.add_argument("--thickness", type=int, default=2, help="Box line thickness.")
    args = parser.parse_args()

    image_path = Path(args.image)
    labels_path = Path(args.labels)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    image_bgr = cv2.imread(str(image_path))
    if image_bgr is None:
        raise SystemExit(f"Failed to read image: {image_path}")

    labels = load_dota_obb_labels(labels_path)
    prefix = args.prefix or image_path.stem

    cv2.imwrite(str(outdir / f"{prefix}_original.png"), image_bgr)
    cv2.imwrite(str(outdir / f"{prefix}_obb.png"), draw_obb(image_bgr, labels, thickness=args.thickness))
    cv2.imwrite(str(outdir / f"{prefix}_vbb.png"), draw_vbb(image_bgr, labels, thickness=args.thickness))

    print(f"Wrote: {outdir / f'{prefix}_original.png'}")
    print(f"Wrote: {outdir / f'{prefix}_obb.png'}")
    print(f"Wrote: {outdir / f'{prefix}_vbb.png'}")


if __name__ == "__main__":
    main()
