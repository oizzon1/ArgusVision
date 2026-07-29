"""Prompt generation: detection -> SAM prompt, with per-class strategy.

Ports the legacy `class_prompt_config.py` + the OBB->VBB / center-point
conversions from `ArgusVisionCore`. The thesis baseline is box prompts for all
15 classes; per-class point prompting remains available for experiments
(thesis: box beats point by ~20 pp IoU on GT prompts).
"""

from dataclasses import dataclass, field
from typing import Dict, List, Sequence, Tuple

import numpy as np

from argusvision.data.constants import NUM_DOTA_CLASSES
from argusvision.models.base import Detection

# Thesis baseline: every class prompts SAM with the detection's axis-aligned box.
DEFAULT_CLASS_PROMPT_CONFIG: Dict[int, str] = {c: "box" for c in range(NUM_DOTA_CLASSES)}

_VALID_PROMPT_TYPES = ("box", "point")


def get_prompt_type(class_id: int, config: Dict[int, str] = None) -> str:
    cfg = DEFAULT_CLASS_PROMPT_CONFIG if config is None else config
    prompt_type = cfg.get(class_id, "box")
    if prompt_type not in _VALID_PROMPT_TYPES:
        raise ValueError(f"invalid prompt type {prompt_type!r} for class {class_id}")
    return prompt_type


def detection_box_prompt(det: Detection) -> np.ndarray:
    """SAM box prompt: the detection's axis-aligned box (for OBB detections
    this is the hull — the legacy OBB->VBB conversion)."""
    return np.asarray(det.box_xyxy, dtype=np.float32)


def detection_point_prompt(det: Detection) -> np.ndarray:
    """SAM point prompt: OBB corner centroid when oriented (equals the box
    center for a rectangle), else the box center."""
    if det.obb_xyxyxyxy is not None:
        pts = det.obb_xyxyxyxy.reshape(4, 2)
        return pts.mean(axis=0).astype(np.float32)
    x1, y1, x2, y2 = det.box_xyxy
    return np.array([(x1 + x2) / 2.0, (y1 + y2) / 2.0], dtype=np.float32)


@dataclass
class PromptSet:
    """Prompts grouped by type, each remembering which detection produced it,
    so masks can be re-aligned to detection order after segmentation.

    The legacy core grouped box-then-point prompts but returned `classes` in
    detection order — masks silently misaligned under any mixed config (it
    never fired only because the config is all-box). The index bookkeeping
    here makes that misalignment impossible.
    """

    box_indices: List[int] = field(default_factory=list)
    box_prompts: List[np.ndarray] = field(default_factory=list)
    point_indices: List[int] = field(default_factory=list)
    point_prompts: List[np.ndarray] = field(default_factory=list)

    def __len__(self) -> int:
        return len(self.box_indices) + len(self.point_indices)


def build_prompts(
    detections: Sequence[Detection], config: Dict[int, str] = None
) -> PromptSet:
    prompts = PromptSet()
    for i, det in enumerate(detections):
        if get_prompt_type(det.class_id, config) == "box":
            prompts.box_indices.append(i)
            prompts.box_prompts.append(detection_box_prompt(det))
        else:
            prompts.point_indices.append(i)
            prompts.point_prompts.append(detection_point_prompt(det))
    return prompts
