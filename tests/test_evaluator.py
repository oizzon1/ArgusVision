"""End-to-end evaluator semantics on a tiny synthetic dataset."""

import numpy as np
import pytest

from argusvision.evaluation.evaluator import DetectionEvaluator, SegmentationEvaluator
from argusvision.models.base import Detection, GroundTruthInstance


def _det(cid, score, box):
    return Detection(class_id=cid, score=score, box_xyxy=np.array(box, dtype=float))


def _gt(cid, box):
    return GroundTruthInstance(class_id=cid, box_xyxy=np.array(box, dtype=float))


def test_detection_evaluator_counts_and_summary():
    ev = DetectionEvaluator(num_classes=2, iou_thresholds=(0.5,))

    # image 1: class 0 — perfect hit + one FP far away; class 1 — one missed GT
    preds = [
        _det(0, 0.9, [0, 0, 10, 10]),
        _det(0, 0.8, [100, 100, 110, 110]),
    ]
    gts = [
        _gt(0, [0, 0, 10, 10]),
        _gt(1, [50, 50, 60, 60]),
    ]
    merged = ev.add_image(preds, gts)

    # merged MatchResult uses ORIGINAL (global) indices
    assert merged[0.5].matches[0][0] == 0  # pred 0 matched
    assert merged[0.5].matches[0][1] == 0  # ...to gt 0
    assert 1 in merged[0.5].unmatched_pred
    assert 1 in merged[0.5].unmatched_gt

    s = ev.summarize()
    t = s["per_threshold"][0.5]
    c0 = t["per_class"]["plane"]  # class 0 name from canonical table
    c1 = t["per_class"]["ship"]
    assert (c0["tp"], c0["fp"], c0["fn"]) == (1, 1, 0)
    assert (c1["tp"], c1["fp"], c1["fn"]) == (0, 0, 1)
    assert t["micro_counts"] == {"tp": 1, "fp": 1, "fn": 1}
    # micro: P = 1/2, R = 1/2, F1 = 1/2
    assert t["micro_f1"] == pytest.approx(0.5)
    # class 0: P=0.5 R=1 F1=2/3 ; class 1: F1=0 ; macro over both present = 1/3
    assert t["macro_f1"] == pytest.approx((2 / 3) / 2)
    # AP: class 0 -> TP at rank 1, FP at rank 2, 1 GT -> AP=1; class 1 -> 0
    assert c0["average_precision"] == pytest.approx(1.0)
    assert c1["average_precision"] == 0.0
    assert t["mean_ap"] == pytest.approx(0.5)


def test_cross_class_predictions_never_match():
    ev = DetectionEvaluator(num_classes=2, iou_thresholds=(0.5,))
    # perfect overlap but wrong class
    ev.add_image([_det(1, 0.9, [0, 0, 10, 10])], [_gt(0, [0, 0, 10, 10])])
    t = ev.summarize()["per_threshold"][0.5]
    assert t["micro_counts"] == {"tp": 0, "fp": 1, "fn": 1}


def test_multi_threshold_monotonicity():
    ev = DetectionEvaluator(num_classes=1, iou_thresholds=(0.1, 0.3, 0.5))
    # IoU with GT is 0.4: [0,0,10,10] vs [0,0,10,25] -> 100 / (100+250-100)
    ev.add_image([_det(0, 0.9, [0, 0, 10, 10])], [_gt(0, [0, 0, 10, 25])])
    s = ev.summarize()
    tps = [s["per_threshold"][t]["micro_counts"]["tp"] for t in (0.1, 0.3, 0.5)]
    assert tps == [1, 1, 0]  # match survives 0.1 and 0.3, dies at 0.5


def test_accumulates_across_images():
    ev = DetectionEvaluator(num_classes=1, iou_thresholds=(0.5,))
    for _ in range(3):
        ev.add_image([_det(0, 0.9, [0, 0, 10, 10])], [_gt(0, [0, 0, 10, 10])])
    s = ev.summarize()
    assert s["num_images"] == 3
    assert s["per_threshold"][0.5]["micro_counts"]["tp"] == 3


def test_segmentation_evaluator_tp_only_vs_gt_anchored():
    ev = SegmentationEvaluator(num_classes=1)
    m_pred = np.zeros((4, 4), dtype=bool)
    m_gt = np.zeros((4, 4), dtype=bool)
    m_pred[0:2, :] = True
    m_gt[0:2, :] = True  # perfect: IoU 1.0

    ev.add_pair(0, m_pred, m_gt)
    ev.add_missed_gt(0)  # detector never found this one

    s = ev.summarize()
    ov = s["overall"]
    assert ov["n_matched"] == 1
    assert ov["n_gt_anchored"] == 2
    assert ov["tp_only_iou"] == pytest.approx(1.0)
    assert ov["gt_anchored_iou"] == pytest.approx(0.5)  # (1.0 + 0.0) / 2


def test_segmentation_evaluator_empty_summary():
    s = SegmentationEvaluator(num_classes=1).summarize()
    assert s["overall"]["n_matched"] == 0
    assert s["overall"]["tp_only_iou"] == 0.0
