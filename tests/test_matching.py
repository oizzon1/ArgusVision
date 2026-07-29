"""Matching semantics — including the two legacy failure modes this stack fixes:
arbitrary-order greedy (F2) and silent OBB→AABB collapse (V2 evaluator)."""

import numpy as np
import pytest

from argusvision.evaluation.matching import (
    box_iou,
    hungarian_match,
    iou_matrix,
    match_by_confidence,
)
from argusvision.models.base import Detection, GroundTruthInstance


# ------------------------------ box_iou ------------------------------

def test_rectangle_iou_known_value():
    # two unit-offset 2x2 squares: intersection 1*2=2, union 4+4-2=6
    a = np.array([0, 0, 2, 2])
    b = np.array([1, 0, 3, 2])
    assert box_iou(a, b) == pytest.approx(2 / 6)


def test_identical_boxes_iou_one():
    a = np.array([10, 10, 50, 30])
    assert box_iou(a, a) == pytest.approx(1.0)


def test_disjoint_boxes_iou_zero():
    assert box_iou(np.array([0, 0, 1, 1]), np.array([5, 5, 6, 6])) == 0.0


def test_obb_polygon_iou_differs_from_aabb_collapse():
    # 45°-rotated square (diamond) inscribed in the axis-aligned square [0,2]^2.
    # Polygon IoU with that square = diamond_area/square_area = 2/4 = 0.5;
    # AABB collapse makes the diamond the full square -> IoU 1.0 (legacy V2).
    diamond = np.array([1, 0, 2, 1, 1, 2, 0, 1], dtype=float)
    square = np.array([0, 0, 2, 2], dtype=float)
    aabb_of_diamond = np.array([0, 0, 2, 2], dtype=float)

    iou_poly = box_iou(aabb_of_diamond, square, a_obb=diamond, b_obb=None, mode="auto")
    iou_aabb = box_iou(aabb_of_diamond, square, a_obb=diamond, b_obb=None, mode="aabb")
    assert iou_poly == pytest.approx(0.5)
    assert iou_aabb == pytest.approx(1.0)


def test_invalid_mode_rejected():
    with pytest.raises(ValueError):
        box_iou(np.zeros(4), np.zeros(4), mode="fancy")


def test_iou_matrix_shape_and_values():
    preds = [Detection(class_id=0, score=0.9, box_xyxy=[0, 0, 2, 2])]
    gts = [
        GroundTruthInstance(class_id=0, box_xyxy=[0, 0, 2, 2]),
        GroundTruthInstance(class_id=0, box_xyxy=[10, 10, 12, 12]),
    ]
    m = iou_matrix(preds, gts)
    assert m.shape == (1, 2)
    assert m[0, 0] == pytest.approx(1.0)
    assert m[0, 1] == 0.0


# -------------------------- hungarian_match --------------------------

def test_hungarian_beats_order_dependent_greedy():
    # A: iou(gt1)=0.6, iou(gt2)=0.0 ; B: iou(gt1)=0.55, iou(gt2)=0.4
    # Greedy visiting B first: B takes gt1, A gets nothing -> 1 TP.
    # Hungarian: A->gt1, B->gt2 -> 2 TP, regardless of order.
    ious = np.array([[0.6, 0.0], [0.55, 0.4]])
    res = hungarian_match(ious, iou_threshold=0.3)
    assert res.tp == 2 and res.fp == 0 and res.fn == 0
    assert sorted((p, g) for p, g, _ in res.matches) == [(0, 0), (1, 1)]


def test_hungarian_threshold_discards_weak_pairs():
    ious = np.array([[0.6, 0.0], [0.55, 0.4]])
    res = hungarian_match(ious, iou_threshold=0.5)
    # optimal assignment still A->gt1 (0.6), B->gt2 (0.4 < 0.5 -> discarded)
    assert res.tp == 1 and res.fp == 1 and res.fn == 1
    assert res.matches[0][:2] == (0, 0)


def test_hungarian_empty_inputs():
    res = hungarian_match(np.zeros((0, 3)), 0.5)
    assert res.tp == 0 and res.fp == 0 and res.fn == 3
    res = hungarian_match(np.zeros((2, 0)), 0.5)
    assert res.tp == 0 and res.fp == 2 and res.fn == 0


# ----------------------- match_by_confidence -----------------------
# The ranking protocol (VOC/COCO). The thesis-era greedy iterated in arbitrary
# order (finding F2): a low-confidence prediction could steal a GT from a
# high-confidence one. These tests pin the corrected behavior.

def test_confidence_order_wins_the_gt():
    # one GT; low-conf pred overlaps it MORE, but high-conf pred is visited
    # first and takes it — the protocol judges detections by rank.
    ious = np.array([[0.6], [0.7]])  # pred0 (high conf), pred1 (low conf)
    scores = [0.9, 0.2]
    flags = match_by_confidence(ious, scores, iou_threshold=0.5)
    assert flags[0] and not flags[1]

    # legacy F2 scenario: had order been positional with pred1 listed first,
    # pred1 would have stolen the GT; assert rank still decides.
    flags_swapped_listing = match_by_confidence(
        ious[::-1], scores[::-1], iou_threshold=0.5
    )
    assert flags_swapped_listing[1] and not flags_swapped_listing[0]


def test_each_gt_matched_once():
    ious = np.array([[0.8], [0.8], [0.8]])
    flags = match_by_confidence(ious, [0.9, 0.8, 0.7], iou_threshold=0.5)
    assert flags.sum() == 1 and flags[0]


def test_below_threshold_never_matches():
    flags = match_by_confidence(np.array([[0.4]]), [0.99], iou_threshold=0.5)
    assert not flags.any()


def test_confidence_tie_is_deterministic():
    ious = np.array([[0.9], [0.9]])
    flags = match_by_confidence(ious, [0.5, 0.5], iou_threshold=0.3)
    assert flags[0] and not flags[1]  # stable sort: first-listed wins ties


def test_empty_inputs_return_empty_flags():
    assert match_by_confidence(np.zeros((0, 2)), [], 0.5).shape == (0,)
    flags = match_by_confidence(np.zeros((2, 0)), [0.9, 0.8], 0.5)
    assert flags.shape == (2,) and not flags.any()
