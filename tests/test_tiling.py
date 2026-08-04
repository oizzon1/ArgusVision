"""Tiling is a protocol, so its geometry and coordinate handling are pinned.

The failure these tests exist to prevent is silent: detections that land in the
wrong place still produce a number, just a wrong one.
"""

import numpy as np
import pytest

from argusvision.models.base import Detection
from argusvision.runtime.tiling import (
    TiledDetector,
    rotated_nms,
    shift_detections,
    tile_origins,
)


# -- geometry --------------------------------------------------------------


def test_small_image_yields_one_tile():
    assert tile_origins(800, 600, 1024, 200) == [(0, 0)]


def test_exact_fit_yields_one_tile():
    assert tile_origins(1024, 1024, 1024, 200) == [(0, 0)]


def test_tiles_cover_the_whole_image():
    w, h, size, overlap = 3000, 2000, 1024, 200
    origins = tile_origins(w, h, size, overlap)
    covered = np.zeros((h, w), dtype=bool)
    for x, y in origins:
        covered[y : y + size, x : x + size] = True
    assert covered.all(), "tiling left a gap — objects there are invisible"


def test_last_tile_is_flush_with_the_edge():
    origins = tile_origins(3000, 1200, 1024, 200)
    assert max(x for x, _ in origins) + 1024 == 3000
    assert max(y for _, y in origins) + 1024 == 1200


def test_stride_respects_overlap():
    xs = sorted({x for x, _ in tile_origins(4000, 1024, 1024, 200)})
    assert xs[1] - xs[0] == 1024 - 200


def test_overlap_must_be_smaller_than_tile():
    with pytest.raises(ValueError):
        tile_origins(2000, 2000, 512, 512)


def test_negative_overlap_rejected():
    with pytest.raises(ValueError):
        tile_origins(2000, 2000, 512, -1)


# -- coordinate mapping ----------------------------------------------------


def _det(box, obb=None, cls=0, score=0.9):
    return Detection(
        class_id=cls,
        score=score,
        box_xyxy=np.array(box, dtype=np.float64),
        obb_xyxyxyxy=None if obb is None else np.array(obb, dtype=np.float64),
    )


def test_shift_moves_boxes_into_full_image_space():
    out = shift_detections([_det([10, 20, 30, 40])], 1000, 500, 4000, 4000)
    assert out[0].box_xyxy.tolist() == [1010, 520, 1030, 540]


def test_shift_moves_oriented_boxes_too():
    obb = [0, 0, 10, 0, 10, 10, 0, 10]
    out = shift_detections([_det([0, 0, 10, 10], obb)], 100, 200, 4000, 4000)
    assert out[0].obb_xyxyxyxy.tolist() == [100, 200, 110, 200, 110, 210, 100, 210]


def test_shift_clips_to_image_bounds():
    out = shift_detections([_det([0, 0, 100, 100])], 950, 950, 1000, 1000)
    assert out[0].box_xyxy[2] <= 999
    assert out[0].box_xyxy[3] <= 999


def test_shift_drops_degenerate_slivers():
    # An edge sliver under 1 px after clipping is not an object.
    assert shift_detections([_det([0, 0, 100, 100])], 999, 999, 1000, 1000) == []


def test_shift_preserves_class_and_score():
    out = shift_detections([_det([1, 1, 9, 9], cls=7, score=0.42)], 10, 10, 100, 100)
    assert out[0].class_id == 7
    assert out[0].score == pytest.approx(0.42)


# -- NMS -------------------------------------------------------------------


def test_nms_merges_duplicates_of_the_same_object():
    a = _det([100, 100, 200, 200], score=0.9)
    b = _det([102, 101, 202, 201], score=0.8)
    assert len(rotated_nms([a, b], 0.5)) == 1


def test_nms_keeps_distinct_neighbours():
    a = _det([100, 100, 150, 150], score=0.9)
    b = _det([400, 400, 450, 450], score=0.8)
    assert len(rotated_nms([a, b], 0.5)) == 2


def test_nms_is_class_wise():
    # Two classes on the same footprint is a disagreement to score, not a
    # duplicate to suppress.
    a = _det([100, 100, 200, 200], cls=0, score=0.9)
    b = _det([100, 100, 200, 200], cls=1, score=0.8)
    assert len(rotated_nms([a, b], 0.5)) == 2


def test_nms_returns_confidence_ranked():
    dets = [_det([0, 0, 10, 10], score=0.3), _det([500, 500, 510, 510], score=0.9)]
    scores = [d.score for d in rotated_nms(dets, 0.5)]
    assert scores == sorted(scores, reverse=True)


# -- the wrapper -----------------------------------------------------------


class _StubDetector:
    """Reports one detection at a fixed spot inside every tile it is given."""

    def __init__(self):
        self.calls = 0
        self.last_inference_ms = 0.0

    def predict(self, image_rgb):
        self.calls += 1
        return [_det([5, 5, 25, 25])]


class _BatchStub(_StubDetector):
    def __init__(self):
        super().__init__()
        self.batches = 0

    def predict_batch(self, images):
        self.batches += 1
        self.calls += len(images)
        return [[_det([5, 5, 25, 25])] for _ in images]


def test_wrapper_satisfies_the_detector_protocol():
    from argusvision.models.base import Detector

    assert isinstance(TiledDetector(_StubDetector()), Detector)


def test_wrapper_calls_the_detector_once_per_tile():
    stub = _StubDetector()
    tiled = TiledDetector(stub, tile_size=1024, overlap=200)
    tiled.predict(np.zeros((2000, 3000, 3), dtype=np.uint8))
    assert stub.calls == len(tile_origins(3000, 2000, 1024, 200))


def test_wrapper_uses_batching_when_available():
    stub = _BatchStub()
    tiled = TiledDetector(stub, tile_size=1024, overlap=200, batch_size=4)
    tiled.predict(np.zeros((2000, 3000, 3), dtype=np.uint8))
    assert stub.batches > 0
    assert stub.calls == len(tile_origins(3000, 2000, 1024, 200))


def test_detections_land_in_full_image_coordinates():
    # The stub reports at (5,5) of each tile; with stride 824 the second column
    # of tiles must appear at x = 824 + 5, not at 5.
    tiled = TiledDetector(_StubDetector(), tile_size=1024, overlap=200, nms_iou=0.9)
    dets = tiled.predict(np.zeros((1024, 3000, 3), dtype=np.uint8))
    xs = sorted(round(d.box_xyxy[0]) for d in dets)
    assert xs[0] == 5
    assert any(x > 800 for x in xs), "tile detections were never offset"


def test_single_tile_path_matches_the_plain_detector():
    image = np.zeros((800, 800, 3), dtype=np.uint8)
    plain = _StubDetector().predict(image)
    tiled = TiledDetector(_StubDetector(), tile_size=1024, overlap=200).predict(image)
    assert len(tiled) == len(plain)
    assert tiled[0].box_xyxy.tolist() == plain[0].box_xyxy.tolist()


def test_wrapper_reports_per_image_statistics():
    tiled = TiledDetector(_StubDetector(), tile_size=1024, overlap=200)
    tiled.predict(np.zeros((2000, 3000, 3), dtype=np.uint8))
    stats = tiled.last_stats
    assert stats["num_tiles"] > 1
    assert stats["num_raw"] >= stats["num_final"]


def test_bad_geometry_fails_at_construction_not_mid_run():
    with pytest.raises(ValueError):
        TiledDetector(_StubDetector(), tile_size=512, overlap=512)
