"""
DataLoader utilities for DOTA dataset evaluation.
Provides PyTorch-based data loading with batching and multi-worker support.
"""

from typing import Dict, List, Optional, Tuple, Callable
import numpy as np
import cv2
import torch
from torch.utils.data import Dataset, DataLoader
from pathlib import Path
import platform


class DOTADataset(Dataset):
    """
    PyTorch Dataset for DOTA aerial imagery dataset.
    Supports both VBB (vertical bounding boxes) and OBB (oriented bounding boxes) formats.
    """

    def __init__(
        self,
        image_paths: List[str],
        label_paths: List[str],
        mode: str = "vbb",
        allowed_class_ids: Optional[set] = None,
        transform: Optional[Callable] = None,
    ):
        """
        Initialize DOTA Dataset.

        Args:
            image_paths: List of paths to images
            label_paths: List of paths to corresponding label files
            mode: Either "vbb" (vertical bbox) or "obb" (oriented bbox)
            allowed_class_ids: Set of class IDs to include (filters out others)
            transform: Optional transform function to apply to images
        """
        assert len(image_paths) == len(label_paths), "Mismatch between images and labels"
        assert mode.lower() in ["vbb", "obb"], f"Invalid mode: {mode}"

        self.image_paths = image_paths
        self.label_paths = label_paths
        self.mode = mode.lower()
        self.allowed_class_ids = allowed_class_ids
        self.transform = transform

    def __len__(self) -> int:
        return len(self.image_paths)

    def __getitem__(self, idx: int) -> Dict:
        """
        Load and return a single sample.

        Returns:
            Dictionary containing:
                - image: RGB image as numpy array (H, W, 3)
                - labels: List of ground truth boxes with class IDs
                - image_path: Original image path
                - image_id: Image identifier (filename without extension)
        """
        img_path = self.image_paths[idx]
        lbl_path = self.label_paths[idx]

        # Load image
        img = cv2.imread(img_path)
        if img is None:
            raise ValueError(f"Failed to load image: {img_path}")
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        ih, iw = img.shape[:2]

        # Apply transforms if provided
        if self.transform is not None:
            img = self.transform(img)

        # Parse labels
        labels = self._parse_labels(lbl_path, iw, ih)

        return {
            "image": img,
            "labels": labels,
            "image_path": img_path,
            "image_id": Path(img_path).stem,
            "image_size": (ih, iw),
        }

    def _parse_labels(self, label_path: str, img_width: int, img_height: int) -> List[Dict]:
        """
        Parse label file and return list of ground truth annotations.

        Args:
            label_path: Path to label file
            img_width: Image width in pixels
            img_height: Image height in pixels

        Returns:
            List of dictionaries, each containing 'bbox' and 'class_id'
        """
        labels = []

        if not Path(label_path).exists():
            return labels

        with open(label_path, "r") as f:
            for line in f:
                parts = line.strip().split()
                if not parts:
                    continue

                if self.mode == "vbb" and len(parts) == 5:
                    # VBB format: class_id cx cy w h (normalized)
                    cid, cx, cy, w, h = map(float, parts)
                    cid = int(cid)

                    # Filter by allowed classes
                    if self.allowed_class_ids is not None and cid not in self.allowed_class_ids:
                        continue

                    # Convert from normalized YOLO format to pixel coordinates
                    x1 = int((cx - w / 2) * img_width)
                    y1 = int((cy - h / 2) * img_height)
                    x2 = int((cx + w / 2) * img_width)
                    y2 = int((cy + h / 2) * img_height)

                    labels.append({
                        "bbox": [x1, y1, x2, y2],
                        "class_id": cid
                    })

                elif self.mode == "obb" and len(parts) == 9:
                    # OBB format: class_id x1 y1 x2 y2 x3 y3 x4 y4 (normalized)
                    # Updated to match DOTAv1.yaml standard format
                    cid, x1, y1, x2, y2, x3, y3, x4, y4 = map(float, parts)
                    cid = int(cid)

                    # Filter by allowed classes
                    if self.allowed_class_ids is not None and cid not in self.allowed_class_ids:
                        continue

                    # Convert from normalized to pixel coordinates
                    labels.append({
                        "bbox": [
                            int(x1 * img_width), int(y1 * img_height),
                            int(x2 * img_width), int(y2 * img_height),
                            int(x3 * img_width), int(y3 * img_height),
                            int(x4 * img_width), int(y4 * img_height)
                        ],
                        "class_id": cid
                    })

        return labels


def collate_fn(batch: List[Dict]) -> Dict:
    """
    Custom collate function for variable-length labels.

    Args:
        batch: List of samples from DOTADataset

    Returns:
        Dictionary with batched data:
            - images: List of images (not stacked due to variable sizes)
            - labels: List of label lists (variable length per image)
            - image_paths: List of image paths
            - image_ids: List of image identifiers
            - image_sizes: List of (height, width) tuples
    """
    images = [item["image"] for item in batch]
    labels = [item["labels"] for item in batch]
    image_paths = [item["image_path"] for item in batch]
    image_ids = [item["image_id"] for item in batch]
    image_sizes = [item["image_size"] for item in batch]

    return {
        "images": images,
        "labels": labels,
        "image_paths": image_paths,
        "image_ids": image_ids,
        "image_sizes": image_sizes,
    }


def create_dataloader(
    image_paths: List[str],
    label_paths: List[str],
    mode: str = "vbb",
    allowed_class_ids: Optional[set] = None,
    batch_size: int = 1,
    num_workers: Optional[int] = None,
    shuffle: bool = False,
    pin_memory: bool = True,
    transform: Optional[Callable] = None,
) -> DataLoader:
    """
    Create a DataLoader for DOTA dataset.

    Args:
        image_paths: List of paths to images
        label_paths: List of paths to corresponding label files
        mode: Either "vbb" or "obb"
        allowed_class_ids: Set of class IDs to include
        batch_size: Number of samples per batch (default: 1 for evaluation)
        num_workers: Number of worker processes for data loading.
                     If None, auto-detects based on OS (0 for Windows, 4 for others)
        shuffle: Whether to shuffle the dataset
        pin_memory: Whether to use pinned memory for faster GPU transfer
        transform: Optional transform function to apply to images

    Returns:
        PyTorch DataLoader instance
    """
    # Auto-detect num_workers based on OS if not specified
    if num_workers is None:
        if platform.system() == "Windows":
            num_workers = 0  # Windows has issues with multiprocessing
        else:
            num_workers = min(4, torch.get_num_threads())

    # Create dataset
    dataset = DOTADataset(
        image_paths=image_paths,
        label_paths=label_paths,
        mode=mode,
        allowed_class_ids=allowed_class_ids,
        transform=transform,
    )

    # Create dataloader
    dataloader = DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=shuffle,
        num_workers=num_workers,
        collate_fn=collate_fn,
        pin_memory=pin_memory and torch.cuda.is_available(),
        persistent_workers=num_workers > 0,
    )

    return dataloader


def get_dataset_paths(dataset_dir: str) -> Tuple[List[str], List[str]]:
    """
    Get image and label paths from dataset directory.

    Args:
        dataset_dir: Root directory of dataset

    Returns:
        Tuple of (image_paths, label_paths)
    """
    dataset_dir = Path(dataset_dir)
    val_images_dir = dataset_dir / "images" / "val"
    val_labels_dir = dataset_dir / "labels" / "val"

    image_paths = sorted([str(p) for p in val_images_dir.glob("*.png")])
    label_paths = [
        str(Path(val_labels_dir) / f"{Path(img).stem}.txt")
        for img in image_paths
    ]

    return image_paths, label_paths
