"""Convert AerialFuseCV instance annotations to COCO instance JSON.

The converter is intentionally read-only with respect to the dataset. It uses
`pairs.jsonl` for object identity and HBB geometry, and extracts binary masks
from the released RGB instance masks by matching each pair's `instance_rgb`.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-root", type=Path, default=Path("dataset/AerialFuseCV"))
    parser.add_argument("--split", choices=("train", "val"), default="train")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-images", type=int, default=None)
    parser.add_argument(
        "--selection",
        choices=("sorted", "fewest-annotations"),
        default="sorted",
        help="Image selection strategy when --image-id is not supplied.",
    )
    parser.add_argument(
        "--image-id",
        action="append",
        default=None,
        help="Optional image id without extension. May be supplied multiple times.",
    )
    return parser.parse_args()


def load_categories(stats_path: Path) -> list[dict[str, Any]]:
    with stats_path.open("r", encoding="utf-8") as f:
        stats = json.load(f)

    categories = []
    for item in stats["per_class"].values():
        categories.append(
            {
                "id": int(item["class_id"]) + 1,
                "name": item["class_name"],
                "supercategory": "aerial-object",
            }
        )
    return sorted(categories, key=lambda row: row["id"])


def load_pairs(pairs_path: Path, split: str) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    with pairs_path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            row = json.loads(line)
            if row["split"] == split:
                grouped[row["image_id"]].append(row)
    return grouped


def rle_encode(mask: np.ndarray) -> dict[str, Any]:
    """Return COCO uncompressed RLE for a boolean mask."""
    pixels = np.asfortranarray(mask.astype(np.uint8)).reshape(-1, order="F")
    change_indices = np.where(pixels[1:] != pixels[:-1])[0] + 1
    run_boundaries = np.concatenate(([0], change_indices, [pixels.size]))
    counts = np.diff(run_boundaries).astype(int).tolist()
    if pixels[0] == 1:
        counts.insert(0, 0)
    return {"size": [int(mask.shape[0]), int(mask.shape[1])], "counts": counts}


def hbb_to_bbox(hbb: list[float]) -> list[float]:
    xs = [float(hbb[i]) for i in range(0, len(hbb), 2)]
    ys = [float(hbb[i]) for i in range(1, len(hbb), 2)]
    x_min = min(xs)
    y_min = min(ys)
    x_max = max(xs)
    y_max = max(ys)
    return [x_min, y_min, x_max - x_min, y_max - y_min]


def main() -> int:
    args = parse_args()
    dataset_root = args.dataset_root
    split_root = dataset_root / args.split

    categories = load_categories(dataset_root / "dataset_statistics.json")
    category_by_name = {row["name"]: row["id"] for row in categories}
    pairs_by_image = load_pairs(dataset_root / "pairs.jsonl", args.split)

    if args.image_id:
        image_ids = list(dict.fromkeys(args.image_id))
    else:
        if args.selection == "fewest-annotations":
            image_ids = [
                image_id
                for image_id, _count in sorted(
                    ((image_id, len(pairs)) for image_id, pairs in pairs_by_image.items()),
                    key=lambda item: (item[1], item[0]),
                )
            ]
        else:
            image_ids = sorted(pairs_by_image)
        if args.max_images is not None:
            image_ids = image_ids[: args.max_images]

    images: list[dict[str, Any]] = []
    annotations: list[dict[str, Any]] = []
    ann_id = 1

    for image_index, image_id in enumerate(image_ids, start=1):
        image_path = split_root / "images" / f"{image_id}.png"
        mask_path = split_root / "instance_masks" / f"{image_id}_instance_id_RGB.png"
        if not image_path.exists():
            raise FileNotFoundError(image_path)
        if not mask_path.exists():
            raise FileNotFoundError(mask_path)

        with Image.open(image_path) as image:
            width, height = image.size
        instance_rgb = np.asarray(Image.open(mask_path).convert("RGB"))

        images.append(
            {
                "id": image_index,
                "file_name": str(Path(args.split) / "images" / f"{image_id}.png"),
                "width": int(width),
                "height": int(height),
                "aerialfusecv_image_id": image_id,
                "split": args.split,
            }
        )

        for pair in pairs_by_image.get(image_id, []):
            rgb = np.asarray(pair["instance_rgb"], dtype=np.uint8)
            mask = np.all(instance_rgb == rgb, axis=2)
            area = int(mask.sum())
            if area == 0:
                continue

            annotations.append(
                {
                    "id": ann_id,
                    "image_id": image_index,
                    "category_id": category_by_name[pair["class_name"]],
                    "bbox": hbb_to_bbox(pair["hbb"]),
                    "area": area,
                    "segmentation": rle_encode(mask),
                    "iscrowd": 0,
                    "aerialfusecv": {
                        "image_id": image_id,
                        "class_name": pair["class_name"],
                        "difficulty": pair["difficulty"],
                        "obb": pair["obb"],
                        "hbb": pair["hbb"],
                        "instance_rgb": pair["instance_rgb"],
                        "match_iou": pair["iou"],
                    },
                }
            )
            ann_id += 1

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as f:
        json.dump(
            {
                "info": {
                    "description": "AerialFuseCV COCO instance conversion",
                    "source_dataset": str(dataset_root),
                    "split": args.split,
                    "mask_source": "instance_masks RGB selected by pairs.jsonl instance_rgb",
                    "bbox_source": "pairs.jsonl hbb",
                },
                "licenses": [],
                "categories": categories,
                "images": images,
                "annotations": annotations,
            },
            f,
            indent=2,
        )
        f.write("\n")

    print(
        f"Wrote {args.output} with {len(images)} images and "
        f"{len(annotations)} annotations"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
