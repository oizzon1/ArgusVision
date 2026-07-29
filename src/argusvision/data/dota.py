"""DOTA-derived detection datasets (YOLO-converted layout).

The thesis YOLO benchmark ran on dataset/DOTA_v1_YOLO_oriented_bboxes_dataset:
    images/val/<id>.png
    labels/val/<id>.txt      normalized YOLO OBB: class x1 y1 x2 y2 x3 y3 x4 y4
"""

from pathlib import Path
from typing import List

import cv2
import numpy as np

from argusvision.models.base import GroundTruthInstance, obb_to_aabb


class DotaYoloObbSplit:
    """Validation split of the YOLO-OBB-converted DOTA dataset."""

    def __init__(self, root: str, split: str = "val"):
        self.root = Path(root)
        self.images_dir = self.root / "images" / split
        self.labels_dir = self.root / "labels" / split
        if not self.images_dir.exists():
            raise FileNotFoundError(f"missing {self.images_dir}")
        self.image_ids = sorted(p.stem for p in self.images_dir.glob("*.png"))

    def __len__(self) -> int:
        return len(self.image_ids)

    def load_image(self, image_id: str) -> np.ndarray:
        bgr = cv2.imread(str(self.images_dir / f"{image_id}.png"))
        if bgr is None:
            raise IOError(f"cannot read image {image_id}")
        return cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)

    def load_ground_truth(
        self, image_id: str, image_width: int, image_height: int
    ) -> List[GroundTruthInstance]:
        path = self.labels_dir / f"{image_id}.txt"
        if not path.exists():
            return []
        instances = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                parts = line.split()
                if len(parts) != 9:
                    continue
                class_id = int(float(parts[0]))
                coords = np.array([float(v) for v in parts[1:9]], dtype=np.float64)
                coords[0::2] *= image_width
                coords[1::2] *= image_height
                instances.append(
                    GroundTruthInstance(
                        class_id=class_id,
                        box_xyxy=obb_to_aabb(coords),
                        obb_xyxyxyxy=coords,
                    )
                )
        return instances
