"""Standard model-output types and adapter protocols.

Models emit `Detection` / `InstanceMask`; the evaluation stack consumes only
these plus `GroundTruthInstance`. Adding a model means writing one adapter that
produces these types — evaluation code never changes (TODO_RESTRUCTURE.md F3).
"""

from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np

try:
    from typing import Protocol, runtime_checkable
except ImportError:  # Python < 3.8 has no Protocol; AV_env is 3.9
    Protocol = object  # type: ignore

    def runtime_checkable(cls):  # type: ignore
        return cls


def obb_to_aabb(obb_xyxyxyxy: np.ndarray) -> np.ndarray:
    """Axis-aligned [x_min, y_min, x_max, y_max] hull of an 8-value OBB."""
    pts = np.asarray(obb_xyxyxyxy, dtype=np.float64).reshape(4, 2)
    return np.array(
        [pts[:, 0].min(), pts[:, 1].min(), pts[:, 0].max(), pts[:, 1].max()],
        dtype=np.float64,
    )


@dataclass
class Detection:
    """One detected object. `box_xyxy` is always present; `obb_xyxyxyxy` only
    when the detector is oriented (then box_xyxy is its axis-aligned hull)."""

    class_id: int
    score: float
    box_xyxy: np.ndarray  # (4,) [x_min, y_min, x_max, y_max]
    obb_xyxyxyxy: Optional[np.ndarray] = None  # (8,) [x1,y1,...,x4,y4]

    def __post_init__(self):
        self.box_xyxy = np.asarray(self.box_xyxy, dtype=np.float64).reshape(4)
        if self.obb_xyxyxyxy is not None:
            self.obb_xyxyxyxy = np.asarray(self.obb_xyxyxyxy, dtype=np.float64).reshape(8)


@dataclass
class InstanceMask:
    """One predicted instance mask (full-image binary array)."""

    class_id: int
    score: float
    mask: np.ndarray  # (H, W) bool

    def __post_init__(self):
        self.mask = np.asarray(self.mask).astype(bool)


@dataclass
class GroundTruthInstance:
    """One ground-truth instance: box always, oriented box and/or mask when the
    dataset provides them."""

    class_id: int
    box_xyxy: np.ndarray
    obb_xyxyxyxy: Optional[np.ndarray] = None
    mask: Optional[np.ndarray] = None  # (H, W) bool
    difficult: bool = False

    def __post_init__(self):
        self.box_xyxy = np.asarray(self.box_xyxy, dtype=np.float64).reshape(4)
        if self.obb_xyxyxyxy is not None:
            self.obb_xyxyxyxy = np.asarray(self.obb_xyxyxyxy, dtype=np.float64).reshape(8)
        if self.mask is not None:
            self.mask = np.asarray(self.mask).astype(bool)


@runtime_checkable
class Detector(Protocol):
    """Adapter protocol: image in, standardized detections out. Nothing else."""

    def predict(self, image_rgb: np.ndarray) -> List[Detection]: ...


@runtime_checkable
class Segmenter(Protocol):
    """Adapter protocol: image + box prompts in, one binary mask per prompt,
    in prompt order. The segmenter knows nothing about classes or scores —
    the pipeline attaches those from the detection that produced each prompt.
    Prompt design beyond boxes lives in pipeline/prompts.py, not here."""

    def predict_masks(
        self, image_rgb: np.ndarray, box_prompts_xyxy: np.ndarray
    ) -> List[np.ndarray]: ...
