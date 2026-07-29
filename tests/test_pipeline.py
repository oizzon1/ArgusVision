"""Pipeline composition semantics with fake models — no GPU, no weights."""

from typing import List

import numpy as np
import pytest

from argusvision.models.base import Detection
from argusvision.pipeline.core import DetectionSegmentationPipeline
from argusvision.pipeline.prompts import (
    DEFAULT_CLASS_PROMPT_CONFIG,
    build_prompts,
    detection_box_prompt,
    detection_point_prompt,
    get_prompt_type,
)


class FakeDetector:
    def __init__(self, detections: List[Detection]):
        self._detections = detections

    def predict(self, image_rgb: np.ndarray) -> List[Detection]:
        return self._detections


class FakeSegmenter:
    """Returns a mask whose content encodes the prompt, so alignment between
    detections and masks can be asserted exactly."""

    def predict_masks(self, image_rgb, box_prompts_xyxy):
        return [self._mask_from_value(b[0]) for b in box_prompts_xyxy]

    def segment(self, image_rgb, prompts, prompt_type="box"):
        return [self._mask_from_value(p[0]) for p in prompts]

    @staticmethod
    def _mask_from_value(v):
        m = np.zeros((8, 8), dtype=bool)
        m[0, int(v) % 8] = True
        return m


def _det(cid, score, box, obb=None):
    return Detection(class_id=cid, score=score, box_xyxy=np.array(box, float), obb_xyxyxyxy=obb)


# ----------------------------- prompts -----------------------------

def test_default_config_is_all_box_for_all_classes():
    assert len(DEFAULT_CLASS_PROMPT_CONFIG) == 15
    assert all(v == "box" for v in DEFAULT_CLASS_PROMPT_CONFIG.values())
    assert get_prompt_type(3) == "box"


def test_box_prompt_is_axis_aligned_hull():
    obb = np.array([1, 0, 2, 1, 1, 2, 0, 1], dtype=float)  # diamond
    det = _det(0, 0.9, [0, 0, 2, 2], obb=obb)
    assert np.allclose(detection_box_prompt(det), [0, 0, 2, 2])


def test_point_prompt_is_obb_centroid():
    obb = np.array([1, 0, 2, 1, 1, 2, 0, 1], dtype=float)
    det = _det(0, 0.9, [0, 0, 2, 2], obb=obb)
    assert np.allclose(detection_point_prompt(det), [1.0, 1.0])


def test_point_prompt_falls_back_to_box_center():
    det = _det(0, 0.9, [0, 0, 4, 2])
    assert np.allclose(detection_point_prompt(det), [2.0, 1.0])


def test_build_prompts_split_remembers_indices():
    config = dict(DEFAULT_CLASS_PROMPT_CONFIG)
    config[1] = "point"
    dets = [_det(0, 0.9, [0, 0, 2, 2]), _det(1, 0.8, [4, 4, 6, 6]), _det(0, 0.7, [8, 8, 9, 9])]
    ps = build_prompts(dets, config)
    assert ps.box_indices == [0, 2]
    assert ps.point_indices == [1]
    assert len(ps) == 3


def test_invalid_prompt_type_rejected():
    with pytest.raises(ValueError):
        get_prompt_type(0, {0: "scribble"})


# ----------------------------- pipeline -----------------------------

def test_masks_align_with_detections_under_mixed_config():
    # THE legacy latent bug: box-then-point grouping vs detection order.
    # detection 0 -> point prompt, detection 1 -> box prompt; the legacy core
    # would have returned [mask_of_det1, mask_of_det0].
    config = dict(DEFAULT_CLASS_PROMPT_CONFIG)
    config[0] = "point"
    dets = [
        _det(0, 0.9, [3, 0, 5, 2]),   # point prompt at center x=4
        _det(1, 0.8, [6, 0, 7, 2]),   # box prompt with x1=6
    ]
    pipe = DetectionSegmentationPipeline(FakeDetector(dets), FakeSegmenter(), config)
    result = pipe.run(np.zeros((8, 8, 3), dtype=np.uint8))

    assert len(result.masks) == 2
    # mask 0 must encode the POINT prompt of detection 0 (x=4), not the box of det 1
    assert result.masks[0].mask[0, 4]
    assert result.masks[1].mask[0, 6]
    assert result.masks[0].class_id == 0 and result.masks[1].class_id == 1
    assert result.masks[0].score == pytest.approx(0.9)


def test_pipeline_all_box_alignment_and_timing():
    dets = [_det(0, 0.9, [1, 0, 2, 2]), _det(1, 0.8, [5, 0, 6, 2])]
    pipe = DetectionSegmentationPipeline(FakeDetector(dets), FakeSegmenter())
    result = pipe.run(np.zeros((8, 8, 3), dtype=np.uint8))
    assert result.masks[0].mask[0, 1] and result.masks[1].mask[0, 5]
    for key in ("detection_ms", "segmentation_ms", "total_ms"):
        assert key in result.timing_ms


def test_pipeline_no_detections():
    pipe = DetectionSegmentationPipeline(FakeDetector([]), FakeSegmenter())
    result = pipe.run(np.zeros((8, 8, 3), dtype=np.uint8))
    assert result.detections == [] and result.masks == []
