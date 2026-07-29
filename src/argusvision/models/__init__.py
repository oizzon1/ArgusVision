"""Model adapters: standard types + one predict-only adapter per model family.

Heavy imports (torch, ultralytics, segment-anything) happen inside adapter
constructors, not at module import — the evaluation stack stays importable on
machines without the ML stack.
"""

from argusvision.models.base import (
    Detection,
    Detector,
    GroundTruthInstance,
    InstanceMask,
    Segmenter,
    obb_to_aabb,
)
from argusvision.models.registry import (
    create_detector,
    create_segmenter,
    detector_spec,
    segmenter_spec,
)
from argusvision.models.sam import SamSegmenter
from argusvision.models.yolo import YoloDetector
