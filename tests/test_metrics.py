"""Metric correctness on hand-computed examples — honest names, real AP."""

import numpy as np
import pytest

from argusvision.evaluation.metrics import (
    average_precision,
    dice_from_iou,
    macro_f1,
    mask_dice,
    mask_iou,
    pr_curve,
    precision_recall_f1,
)


# ----------------------------- masks -----------------------------

def _pair():
    m1 = np.zeros((4, 4), dtype=bool)
    m2 = np.zeros((4, 4), dtype=bool)
    m1[0:2, 0:4] = True  # 8 px
    m2[1:3, 0:4] = True  # 8 px, overlap 4 px
    return m1, m2


def test_mask_iou_hand_value():
    m1, m2 = _pair()
    assert mask_iou(m1, m2) == pytest.approx(4 / 12)


def test_mask_dice_hand_value():
    m1, m2 = _pair()
    assert mask_dice(m1, m2) == pytest.approx(8 / 16)


def test_dice_from_iou_consistent_with_direct_dice():
    m1, m2 = _pair()
    assert dice_from_iou(mask_iou(m1, m2)) == pytest.approx(mask_dice(m1, m2))


def test_empty_masks():
    z = np.zeros((3, 3), dtype=bool)
    assert mask_iou(z, z) == 0.0
    assert mask_dice(z, z) == 0.0


def test_shape_mismatch_raises():
    with pytest.raises(ValueError):
        mask_iou(np.zeros((2, 2), dtype=bool), np.zeros((3, 3), dtype=bool))


# ------------------------- P / R / F1 -------------------------

def test_prf_basic():
    p, r, f1 = precision_recall_f1(tp=8, fp=2, fn=8)
    assert p == pytest.approx(0.8)
    assert r == pytest.approx(0.5)
    assert f1 == pytest.approx(2 * 0.8 * 0.5 / 1.3)


def test_prf_zero_divisions_are_zero():
    assert precision_recall_f1(0, 0, 0) == (0.0, 0.0, 0.0)
    assert precision_recall_f1(0, 5, 0)[0] == 0.0
    assert precision_recall_f1(0, 0, 5)[1] == 0.0


def test_macro_f1_over_present_classes_only():
    f1s = {0: 1.0, 1: 0.5, 2: 0.0}
    assert macro_f1(f1s, present_class_ids=[0, 1]) == pytest.approx(0.75)
    assert macro_f1(f1s, present_class_ids=[]) == 0.0


# ------------------------- PR curve / AP -------------------------

def test_pr_curve_hand_example():
    # 3 predictions of one class, 2 GT instances.
    # rank:   conf .9 TP | conf .8 FP | conf .7 TP
    scores = np.array([0.9, 0.8, 0.7])
    flags = np.array([True, False, True])
    s, precision, recall = pr_curve(scores, flags, num_gt=2)
    assert np.allclose(s, [0.9, 0.8, 0.7])
    assert np.allclose(precision, [1.0, 0.5, 2 / 3])
    assert np.allclose(recall, [0.5, 0.5, 1.0])


def test_pr_curve_unsorted_input_is_sorted_internally():
    scores = np.array([0.7, 0.9, 0.8])
    flags = np.array([True, True, False])  # aligned to the unsorted scores
    _, precision, recall = pr_curve(scores, flags, num_gt=2)
    assert np.allclose(precision, [1.0, 0.5, 2 / 3])
    assert np.allclose(recall, [0.5, 0.5, 1.0])


def test_average_precision_hand_example():
    # From the curve above: envelope precision on (0, .5] is 1.0, on (.5, 1] is 2/3
    # AP = 0.5 * 1.0 + 0.5 * 2/3 = 5/6
    _, precision, recall = pr_curve(
        np.array([0.9, 0.8, 0.7]), np.array([True, False, True]), num_gt=2
    )
    assert average_precision(precision, recall) == pytest.approx(5 / 6)


def test_perfect_detector_ap_one():
    _, precision, recall = pr_curve(
        np.array([0.9, 0.8]), np.array([True, True]), num_gt=2
    )
    assert average_precision(precision, recall) == pytest.approx(1.0)


def test_all_false_positives_ap_zero():
    _, precision, recall = pr_curve(
        np.array([0.9, 0.8]), np.array([False, False]), num_gt=2
    )
    assert average_precision(precision, recall) == 0.0


def test_missed_gt_caps_recall_and_ap():
    # one TP, but 4 GT -> recall never exceeds 0.25, AP <= 0.25
    _, precision, recall = pr_curve(np.array([0.9]), np.array([True]), num_gt=4)
    ap = average_precision(precision, recall)
    assert recall.max() == pytest.approx(0.25)
    assert ap == pytest.approx(0.25)
