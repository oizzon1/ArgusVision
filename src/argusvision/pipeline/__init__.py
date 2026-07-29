"""detect -> prompt -> segment composition."""

from argusvision.pipeline.core import DetectionSegmentationPipeline, PipelineResult
from argusvision.pipeline.prompts import (
    DEFAULT_CLASS_PROMPT_CONFIG,
    PromptSet,
    build_prompts,
    detection_box_prompt,
    detection_point_prompt,
    get_prompt_type,
)
