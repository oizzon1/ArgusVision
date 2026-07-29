"""The detect -> prompt -> segment composition.

Takes any Detector and any Segmenter (protocols in models/base.py) and returns
detections with their masks, ALIGNED: `result.masks[i]` belongs to
`result.detections[i]`, whatever mix of prompt types the config chose.
"""

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np

from argusvision.models.base import Detection, InstanceMask
from argusvision.pipeline.prompts import PromptSet, build_prompts


@dataclass
class PipelineResult:
    detections: List[Detection]
    masks: List[InstanceMask]  # aligned: masks[i] <-> detections[i]
    timing_ms: Dict[str, float] = field(default_factory=dict)


class DetectionSegmentationPipeline:
    """Training-free detector -> segmenter pipeline (the thesis architecture)."""

    def __init__(self, detector, segmenter, class_prompt_config: Optional[Dict[int, str]] = None):
        self.detector = detector
        self.segmenter = segmenter
        self.class_prompt_config = class_prompt_config

    def run(self, image_rgb: np.ndarray) -> PipelineResult:
        t_start = time.time()

        t0 = time.time()
        detections = self.detector.predict(image_rgb)
        detection_ms = (time.time() - t0) * 1000.0

        prompts = build_prompts(detections, self.class_prompt_config)

        t0 = time.time()
        raw_masks: List[Optional[np.ndarray]] = [None] * len(detections)
        if prompts.box_prompts:
            box_masks = self.segmenter.predict_masks(image_rgb, prompts.box_prompts)
            for det_idx, mask in zip(prompts.box_indices, box_masks):
                raw_masks[det_idx] = mask
        if prompts.point_prompts:
            point_masks = self.segmenter.segment(
                image_rgb, prompts.point_prompts, prompt_type="point"
            )
            for det_idx, mask in zip(prompts.point_indices, point_masks):
                raw_masks[det_idx] = mask
        segmentation_ms = (time.time() - t0) * 1000.0

        masks = [
            InstanceMask(class_id=det.class_id, score=det.score, mask=m)
            for det, m in zip(detections, raw_masks)
        ]

        return PipelineResult(
            detections=detections,
            masks=masks,
            timing_ms={
                "detection_ms": detection_ms,
                "segmentation_ms": segmentation_ms,
                "total_ms": (time.time() - t_start) * 1000.0,
            },
        )
