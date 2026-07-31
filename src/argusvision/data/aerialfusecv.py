"""AerialFuseCV split access: images, DOTA-format labels, semantic masks.

Layout (per split root, e.g. dataset/AerialFuseCV_Refined/val):
    images/<id>.png
    labels/<id>.txt                  DOTA: x1 y1 ... x4 y4 class-name difficulty
    semantic_masks/<id>_instance_color_RGB.png

GT instance masks are derived exactly as the thesis-era V2 evaluator did:
class-color binary mask clipped by the GT OBB polygon, falling back to the
polygon itself where the semantic mask has annotation gaps.
"""

from pathlib import Path
from typing import List, Optional

import cv2
import numpy as np

from argusvision.data.constants import (
    CLASS_ID_TO_ISAID_COLOR,
    CLASS_NAME_TO_ID,
)
from argusvision.models.base import GroundTruthInstance, obb_to_aabb


def parse_dota_label_line(line: str) -> Optional[GroundTruthInstance]:
    """One DOTA line -> GroundTruthInstance, or None if unparsable."""
    parts = line.split()
    if len(parts) < 10:
        return None
    try:
        coords = np.array([float(v) for v in parts[:8]], dtype=np.float64)
    except ValueError:
        return None
    token = parts[8]
    if token.isdigit():
        class_id = int(token)
    else:
        class_id = CLASS_NAME_TO_ID.get(token)
    if class_id is None:
        return None
    difficult = parts[9] == "1" if len(parts) > 9 else False
    return GroundTruthInstance(
        class_id=class_id,
        box_xyxy=obb_to_aabb(coords),
        obb_xyxyxyxy=coords,
        difficult=difficult,
    )


class AerialFuseCVSplit:
    """One split (train or val) of AerialFuseCV(_Refined)."""

    def __init__(self, root: str):
        self.root = Path(root)
        # Oriented boxes live in labels_obb/ (a build may also ship labels_hbb/);
        # older layouts used a single labels/ directory.
        self.labels_dir = next(
            (self.root / n for n in ("labels_obb", "labels") if (self.root / n).exists()),
            self.root / "labels",
        )
        for sub in (self.root / "images", self.labels_dir, self.root / "semantic_masks"):
            if not sub.exists():
                raise FileNotFoundError(f"dataset split missing {sub}")
        self.image_ids = sorted(p.stem for p in (self.root / "images").glob("*.png"))

    def __len__(self) -> int:
        return len(self.image_ids)

    def load_image(self, image_id: str) -> np.ndarray:
        bgr = cv2.imread(str(self.root / "images" / f"{image_id}.png"))
        if bgr is None:
            raise IOError(f"cannot read image {image_id}")
        return cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)

    def load_semantic_mask(self, image_id: str) -> np.ndarray:
        path = self.root / "semantic_masks" / f"{image_id}_instance_color_RGB.png"
        bgr = cv2.imread(str(path))
        if bgr is None:
            raise IOError(f"cannot read semantic mask {path}")
        return cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)

    def load_ground_truth(self, image_id: str) -> List[GroundTruthInstance]:
        path = self.labels_dir / f"{image_id}.txt"
        if not path.exists():
            return []
        instances = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    gt = parse_dota_label_line(line)
                    if gt is not None:
                        instances.append(gt)
        return instances


def class_binary_mask(semantic_rgb: np.ndarray, class_id: int) -> np.ndarray:
    color = CLASS_ID_TO_ISAID_COLOR.get(class_id)
    if color is None:
        return np.zeros(semantic_rgb.shape[:2], dtype=bool)
    return np.all(semantic_rgb == np.array(color, dtype=np.uint8), axis=-1)


def extract_gt_instance_mask(
    semantic_rgb: np.ndarray, gt: GroundTruthInstance
) -> np.ndarray:
    """GT mask for one instance: class semantic mask clipped by the GT box
    polygon; polygon area alone where the class mask has gaps (thesis V2
    semantics, unchanged)."""
    cls_mask = class_binary_mask(semantic_rgb, gt.class_id)
    h, w = cls_mask.shape

    poly_mask = np.zeros((h, w), dtype=np.uint8)
    if gt.obb_xyxyxyxy is not None:
        pts = np.round(gt.obb_xyxyxyxy.reshape(4, 2)).astype(np.int32)
        cv2.fillPoly(poly_mask, [pts], 1)
    else:
        x1, y1, x2, y2 = [int(round(v)) for v in gt.box_xyxy]
        cv2.rectangle(
            poly_mask,
            (max(0, x1), max(0, y1)),
            (min(w - 1, x2), min(h - 1, y2)),
            1,
            -1,
        )

    instance = cls_mask & (poly_mask > 0)
    if not instance.any():
        instance = poly_mask > 0
    return instance
