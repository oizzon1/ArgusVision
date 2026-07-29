"""
ArgusVision: Integration of YOLO Detection with SAM Segmentation for Aerial Imagery

This package provides a dual-mode pipeline:
- Inference Mode: Operational use, returns segmentation masks
- Evaluation Mode: Research/benchmarking, computes metrics against ground truth

Core Components:
- ArgusVisionCore: Main pipeline logic
- ArgusVisionInference: Inference mode wrapper

"""

from .ArgusVisionCore import ArgusVisionCore
from .ArgusVisionInference import ArgusVisionInference
# V1 evaluator deleted at restructure Phase 3 (superseded by argusvision.evaluation)
from .config.class_prompt_config import CLASS_PROMPT_CONFIG, CLASS_NAMES, get_prompt_type

__version__ = '1.0.0'
__all__ = [
    'ArgusVisionCore',
    'ArgusVisionInference',

    'CLASS_PROMPT_CONFIG',
    'CLASS_NAMES',
    'get_prompt_type'
]
