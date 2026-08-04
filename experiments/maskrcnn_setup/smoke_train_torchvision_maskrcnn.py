"""Smoke-train torchvision Mask R-CNN on a tiny AerialFuseCV COCO subset.

This is a feasibility script, not a paper experiment. It intentionally uses a
small fixed number of images and iterations to prove that the Windows training
path runs, produces finite losses, and can use CUDA in the separate P2 env.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path
from typing import Any

import numpy as np
import torch
from PIL import Image
from torch.utils.data import DataLoader, Dataset
from torchvision.models.detection import MaskRCNN
from torchvision.models.detection.anchor_utils import AnchorGenerator
from torchvision.models.detection.backbone_utils import resnet_fpn_backbone
from torchvision.ops import masks_to_boxes


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--coco-json", type=Path, required=True)
    parser.add_argument("--dataset-root", type=Path, default=Path("dataset/AerialFuseCV"))
    parser.add_argument("--iterations", type=int, default=50)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--num-workers", type=int, default=0)
    parser.add_argument("--lr", type=float, default=0.0001)
    parser.add_argument("--output-log", type=Path, required=True)
    parser.add_argument("--num-classes", type=int, default=16)
    parser.add_argument("--image-size", type=int, default=512)
    parser.add_argument("--min-mask-area", type=int, default=16)
    parser.add_argument("--grad-clip", type=float, default=1.0)
    parser.add_argument("--seed", type=int, default=20260804)
    return parser.parse_args()


def decode_rle(rle: dict[str, Any]) -> np.ndarray:
    height, width = rle["size"]
    values: list[int] = []
    current = 0
    for count in rle["counts"]:
        values.extend([current] * int(count))
        current = 1 - current
    arr = np.asarray(values, dtype=np.uint8)
    return arr.reshape((height, width), order="F").astype(bool)


class CocoMaskDataset(Dataset):
    def __init__(
        self,
        coco_json: Path,
        dataset_root: Path,
        image_size: int,
        min_mask_area: int,
    ) -> None:
        with coco_json.open("r", encoding="utf-8") as f:
            coco = json.load(f)
        self.dataset_root = dataset_root
        self.image_size = image_size
        self.min_mask_area = min_mask_area
        self.images = coco["images"]
        grouped: dict[int, list[dict[str, Any]]] = {}
        for ann in coco["annotations"]:
            grouped.setdefault(int(ann["image_id"]), []).append(ann)
        self.annotations = grouped

    def __len__(self) -> int:
        return len(self.images)

    def __getitem__(self, index: int) -> tuple[torch.Tensor, dict[str, torch.Tensor]]:
        meta = self.images[index]
        image_path = self.dataset_root / meta["file_name"]
        image = Image.open(image_path).convert("RGB")
        orig_w, orig_h = image.size
        image = image.resize((self.image_size, self.image_size), Image.BILINEAR)
        image_np = np.asarray(image, dtype=np.float32) / 255.0
        image_tensor = torch.from_numpy(image_np).permute(2, 0, 1)

        masks = []
        labels = []
        scale_x = self.image_size / float(orig_w)
        scale_y = self.image_size / float(orig_h)
        for ann in self.annotations.get(int(meta["id"]), []):
            mask = Image.fromarray(decode_rle(ann["segmentation"]).astype(np.uint8) * 255)
            mask = mask.resize((self.image_size, self.image_size), Image.NEAREST)
            mask_tensor = torch.from_numpy(np.asarray(mask) > 0)
            if int(mask_tensor.sum()) < self.min_mask_area:
                continue
            masks.append(mask_tensor)
            labels.append(int(ann["category_id"]))

        if masks:
            masks_tensor = torch.stack(masks).to(torch.uint8)
            boxes = masks_to_boxes(masks_tensor)
            keep = (boxes[:, 2] > boxes[:, 0]) & (boxes[:, 3] > boxes[:, 1])
            masks_tensor = masks_tensor[keep]
            boxes = boxes[keep]
            labels_tensor = torch.as_tensor(labels, dtype=torch.int64)[keep]
        else:
            masks_tensor = torch.zeros((0, self.image_size, self.image_size), dtype=torch.uint8)
            boxes = torch.zeros((0, 4), dtype=torch.float32)
            labels_tensor = torch.zeros((0,), dtype=torch.int64)

        target = {
            "boxes": boxes.float(),
            "labels": labels_tensor,
            "masks": masks_tensor,
            "image_id": torch.tensor([int(meta["id"])]),
            "area": (boxes[:, 2] - boxes[:, 0]) * (boxes[:, 3] - boxes[:, 1]),
            "iscrowd": torch.zeros((boxes.shape[0],), dtype=torch.int64),
        }
        return image_tensor, target


def collate_fn(batch: list[tuple[torch.Tensor, dict[str, torch.Tensor]]]) -> tuple[list[torch.Tensor], list[dict[str, torch.Tensor]]]:
    images, targets = zip(*batch)
    return list(images), list(targets)


def make_model(num_classes: int) -> MaskRCNN:
    backbone = resnet_fpn_backbone(
        backbone_name="resnet18",
        weights=None,
        trainable_layers=3,
    )
    anchor_generator = AnchorGenerator(
        sizes=((16,), (32,), (64,), (128,), (256,)),
        aspect_ratios=((0.5, 1.0, 2.0),) * 5,
    )
    return MaskRCNN(backbone, num_classes=num_classes, rpn_anchor_generator=anchor_generator)


def query_gpu() -> str:
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=memory.used,memory.total,utilization.gpu",
                "--format=csv,noheader,nounits",
            ],
            check=False,
            text=True,
            capture_output=True,
        )
    except FileNotFoundError:
        return "nvidia-smi unavailable"
    return result.stdout.strip() or result.stderr.strip()


def main() -> int:
    args = parse_args()
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    dataset = CocoMaskDataset(
        args.coco_json,
        args.dataset_root,
        args.image_size,
        args.min_mask_area,
    )
    loader = DataLoader(
        dataset,
        batch_size=args.batch_size,
        shuffle=True,
        num_workers=args.num_workers,
        collate_fn=collate_fn,
    )
    iterator = iter(loader)

    model = make_model(args.num_classes).to(device)
    model.train()
    optimizer = torch.optim.SGD(model.parameters(), lr=args.lr, momentum=0.9)

    args.output_log.parent.mkdir(parents=True, exist_ok=True)
    start = time.perf_counter()
    with args.output_log.open("w", encoding="utf-8") as f:
        for step in range(1, args.iterations + 1):
            try:
                images, targets = next(iterator)
            except StopIteration:
                iterator = iter(loader)
                images, targets = next(iterator)

            images = [image.to(device) for image in images]
            targets = [{k: v.to(device) for k, v in target.items()} for target in targets]

            optimizer.zero_grad(set_to_none=True)
            losses = model(images, targets)
            loss = sum(value for value in losses.values())
            if not torch.isfinite(loss):
                raise RuntimeError(f"Non-finite loss at iteration {step}: {loss.item()}")
            loss.backward()
            if args.grad_clip > 0:
                torch.nn.utils.clip_grad_norm_(model.parameters(), args.grad_clip)
            optimizer.step()

            elapsed = time.perf_counter() - start
            record = {
                "iteration": step,
                "loss_total": float(loss.detach().cpu()),
                "losses": {
                    name: float(value.detach().cpu()) for name, value in losses.items()
                },
                "elapsed_sec": elapsed,
                "iter_per_sec": step / elapsed if elapsed > 0 else None,
                "gpu": query_gpu() if step in {1, args.iterations} else None,
            }
            f.write(json.dumps(record) + "\n")
            f.flush()
            print(json.dumps(record), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
