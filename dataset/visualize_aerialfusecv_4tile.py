"""
Create 4-tile collages for AerialFuseCV_Refined samples.

Tiles:
1) Original image + GT VBB (axis-aligned bbox from OBB)
2) Original image + GT OBB (polygon)
3) Original image + semantic mask overlay
4) Original image + instance mask overlay

The script searches the requested image id in BOTH train and val splits.

Usage:
    python dataset/visualize_aerialfusecv_4tile.py --image-id P0173
    python dataset/visualize_aerialfusecv_4tile.py --image-id P0173 --root dataset/AerialFuseCV_Refined
    python dataset/visualize_aerialfusecv_4tile.py --image-id P0173 --output results/aerialfusecv_4tile
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, List, Tuple

import cv2
import numpy as np


CLASS_COLORS_RGB: Dict[str, Tuple[int, int, int]] = {
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


def rgb_to_bgr(color_rgb: Tuple[int, int, int]) -> Tuple[int, int, int]:
    return (int(color_rgb[2]), int(color_rgb[1]), int(color_rgb[0]))


def parse_dota_obb(label_path: Path) -> List[Tuple[str, np.ndarray]]:
    """Parse DOTA labels: x1 y1 x2 y2 x3 y3 x4 y4 class difficulty."""
    items: List[Tuple[str, np.ndarray]] = []
    if not label_path.exists():
        return items

    with label_path.open("r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split()
            if not parts or parts[0] in {"imagesource:", "gsd:"}:
                continue
            if len(parts) < 10:
                continue
            try:
                coords = [float(v) for v in parts[:8]]
            except ValueError:
                continue

            class_name = parts[8]
            points = np.array(coords, dtype=np.float32).reshape(4, 2)
            items.append((class_name, points))

    return items


def draw_vbb(image_bgr: np.ndarray, obb_items: List[Tuple[str, np.ndarray]]) -> np.ndarray:
    out = image_bgr.copy()
    for class_name, pts in obb_items:
        xs = pts[:, 0]
        ys = pts[:, 1]
        x1, y1 = int(np.floor(xs.min())), int(np.floor(ys.min()))
        x2, y2 = int(np.ceil(xs.max())), int(np.ceil(ys.max()))

        color = rgb_to_bgr(CLASS_COLORS_RGB.get(class_name, (255, 255, 255)))
        cv2.rectangle(out, (x1, y1), (x2, y2), color, 2, lineType=cv2.LINE_AA)
        cv2.putText(
            out,
            class_name,
            (x1, max(15, y1 - 4)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            color,
            1,
            lineType=cv2.LINE_AA,
        )
    return out


def draw_obb(image_bgr: np.ndarray, obb_items: List[Tuple[str, np.ndarray]]) -> np.ndarray:
    out = image_bgr.copy()
    for class_name, pts in obb_items:
        poly = np.round(pts).astype(np.int32).reshape((-1, 1, 2))
        color = rgb_to_bgr(CLASS_COLORS_RGB.get(class_name, (255, 255, 255)))
        cv2.polylines(out, [poly], isClosed=True, color=color, thickness=2, lineType=cv2.LINE_AA)

        x, y = int(poly[0, 0, 0]), int(poly[0, 0, 1])
        cv2.putText(
            out,
            class_name,
            (x, max(15, y - 4)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            color,
            1,
            lineType=cv2.LINE_AA,
        )
    return out


def overlay_mask(image_bgr: np.ndarray, mask_bgr: np.ndarray, alpha: float = 0.35) -> np.ndarray:
    """Overlay all non-black mask pixels preserving mask colors."""
    out = image_bgr.copy()
    non_black = np.any(mask_bgr > 0, axis=-1)
    out[non_black] = (
        out[non_black].astype(np.float32) * (1.0 - alpha)
        + mask_bgr[non_black].astype(np.float32) * alpha
    ).astype(np.uint8)
    return out


def add_title(image_bgr: np.ndarray, title: str, bar_h: int = 34) -> np.ndarray:
    h, w = image_bgr.shape[:2]
    canvas = np.zeros((h + bar_h, w, 3), dtype=np.uint8)
    canvas[:bar_h, :, :] = (35, 35, 35)
    canvas[bar_h:, :, :] = image_bgr
    cv2.putText(
        canvas,
        title,
        (10, 23),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (255, 255, 255),
        2,
        lineType=cv2.LINE_AA,
    )
    return canvas


def make_collage(tile_tl: np.ndarray, tile_tr: np.ndarray, tile_bl: np.ndarray, tile_br: np.ndarray) -> np.ndarray:
    top = np.hstack([tile_tl, tile_tr])
    bottom = np.hstack([tile_bl, tile_br])
    return np.vstack([top, bottom])


def resolve_sample_paths(root: Path, split: str, image_id: str) -> Dict[str, Path]:
    base = root / split
    return {
        "image": base / "images" / f"{image_id}.png",
        "label": base / "labels" / f"{image_id}.txt",
        "semantic": base / "semantic_masks" / f"{image_id}_instance_color_RGB.png",
        "instance": base / "instance_masks" / f"{image_id}_instance_id_RGB.png",
    }


def process_split(root: Path, split: str, image_id: str, output_dir: Path) -> Path | None:
    paths = resolve_sample_paths(root, split, image_id)
    required = ["image", "label", "semantic", "instance"]
    if not all(paths[k].exists() for k in required):
        return None

    image_bgr = cv2.imread(str(paths["image"]))
    semantic_bgr = cv2.imread(str(paths["semantic"]))
    instance_bgr = cv2.imread(str(paths["instance"]))
    if image_bgr is None or semantic_bgr is None or instance_bgr is None:
        return None

    obb_items = parse_dota_obb(paths["label"])

    vbb_img = draw_vbb(image_bgr, obb_items)
    obb_img = draw_obb(image_bgr, obb_items)
    sem_overlay = overlay_mask(image_bgr, semantic_bgr, alpha=0.35)
    inst_overlay = overlay_mask(image_bgr, instance_bgr, alpha=0.35)

    t1 = add_title(vbb_img, "Original + GT VBB")
    t2 = add_title(obb_img, "Original + GT OBB")
    t3 = add_title(sem_overlay, "Original + Semantic Masks")
    t4 = add_title(inst_overlay, "Original + Instance Masks")

    collage = make_collage(t1, t2, t3, t4)

    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"{image_id}_{split}_4tile_collage.png"
    cv2.imwrite(str(out_path), collage)
    return out_path


def main():
    parser = argparse.ArgumentParser(description="4-tile AerialFuseCV visualization (train/val auto-search)")
    parser.add_argument("--image-id", required=True, type=str, help="Image id, e.g. P0173")
    parser.add_argument("--root", type=str, default="dataset/AerialFuseCV_Refined", help="Dataset root")
    parser.add_argument("--output", type=str, default="results/AerialFuseCV_4tile", help="Output directory")
    args = parser.parse_args()

    image_id = args.image_id.strip()
    root = Path(args.root)
    out_dir = Path(args.output)

    print("=" * 72)
    print(f"Searching image '{image_id}' in train + val splits")
    print("=" * 72)

    found_any = False
    for split in ["train", "val"]:
        out_path = process_split(root=root, split=split, image_id=image_id, output_dir=out_dir)
        if out_path is None:
            print(f"[MISS] {split}: not found (or missing one of image/label/semantic/instance files)")
        else:
            found_any = True
            print(f"[OK] {split}: saved -> {out_path}")

    if not found_any:
        raise FileNotFoundError(
            f"Image '{image_id}' was not found as a complete sample in train or val under: {root}"
        )


if __name__ == "__main__":
    main()
