"""
Experiment runners and evaluation scripts.
"""

from .evaluate_yolo_vbb import (
    run_evaluation as run_vbb_evaluation,
    YOLO_MODELS as YOLO_VBB_MODELS,
    DOTA_CLASS_NAMES,
    COCO_TO_DOTA,
    VBB_EVAL_CLASS_IDS,
    NUM_DOTA,
)
from .evaluate_yolo_obb import (
    run_evaluation as run_obb_evaluation,
    YOLO_OBB_MODELS,
)

__all__ = [
    "run_vbb_evaluation",
    "YOLO_VBB_MODELS",
    "DOTA_CLASS_NAMES",
    "COCO_TO_DOTA",
    "VBB_EVAL_CLASS_IDS",
    "NUM_DOTA",
    "run_obb_evaluation",
    "YOLO_OBB_MODELS",
]
