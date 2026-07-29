"""Model adapters: standard types + one predict-only adapter per model family."""

from argusvision.models.base import (
    Detection,
    Detector,
    GroundTruthInstance,
    InstanceMask,
    Segmenter,
    obb_to_aabb,
)
