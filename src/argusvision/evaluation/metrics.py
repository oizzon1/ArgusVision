"""Metric computations with honest names.

The thesis-era `src/utils/metrics.py` reported a value named `map` that was in
fact a macro-average of per-class F1 at a fixed IoU threshold (finding F2).
Here every quantity is named what it is: `macro_f1` is macro-F1, and
`average_precision` is real ranked AP from a PR curve. Nothing in this module
is allowed to alias one metric name to another.
"""

from typing import Dict, Sequence, Tuple

import numpy as np


# --------------------------- mask overlap ---------------------------

def mask_iou(mask1: np.ndarray, mask2: np.ndarray) -> float:
    """IoU of two binary masks of identical shape."""
    if mask1.shape != mask2.shape:
        raise ValueError("masks must have the same shape")
    m1 = np.asarray(mask1, dtype=bool)
    m2 = np.asarray(mask2, dtype=bool)
    union = np.logical_or(m1, m2).sum()
    if union == 0:
        return 0.0
    return float(np.logical_and(m1, m2).sum() / union)


def mask_dice(mask1: np.ndarray, mask2: np.ndarray) -> float:
    """Dice coefficient of two binary masks of identical shape."""
    if mask1.shape != mask2.shape:
        raise ValueError("masks must have the same shape")
    m1 = np.asarray(mask1, dtype=bool)
    m2 = np.asarray(mask2, dtype=bool)
    total = m1.sum() + m2.sum()
    if total == 0:
        return 0.0
    return float(2.0 * np.logical_and(m1, m2).sum() / total)


def dice_from_iou(iou: float) -> float:
    """Dice = 2*IoU / (1 + IoU), valid for any pair of sets."""
    if iou <= 0.0:
        return 0.0
    return (2.0 * iou) / (1.0 + iou)


# ----------------------- set-level P / R / F1 -----------------------

def precision_recall_f1(tp: int, fp: int, fn: int) -> Tuple[float, float, float]:
    """Precision, recall, F1 from counts. Undefined ratios are 0.0."""
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (
        2.0 * precision * recall / (precision + recall)
        if (precision + recall) > 0
        else 0.0
    )
    return float(precision), float(recall), float(f1)


def macro_f1(per_class_f1: Dict[int, float], present_class_ids: Sequence[int]) -> float:
    """Unweighted mean F1 over the classes listed as present. Honest name for
    what the thesis-era code called `map`."""
    present = list(present_class_ids)
    if not present:
        return 0.0
    return float(np.mean([per_class_f1[c] for c in present]))


# ------------------------- PR curve and AP --------------------------

def pr_curve(
    scores: np.ndarray, tp_flags: np.ndarray, num_gt: int
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Precision and recall as functions of descending confidence cutoff.

    Args:
        scores: confidence of every prediction of one class over the dataset.
        tp_flags: per-prediction TP flag from the ranking-protocol matcher.
        num_gt: total ground-truth instances of that class.

    Returns:
        (sorted_scores_desc, precision, recall), each of length n_predictions.
    """
    scores = np.asarray(scores, dtype=np.float64)
    tp_flags = np.asarray(tp_flags, dtype=bool)
    if scores.shape != tp_flags.shape:
        raise ValueError("scores and tp_flags must have equal length")

    order = np.argsort(-scores, kind="stable")
    scores_sorted = scores[order]
    tp_sorted = tp_flags[order].astype(np.float64)

    cum_tp = np.cumsum(tp_sorted)
    cum_fp = np.cumsum(1.0 - tp_sorted)
    denom = cum_tp + cum_fp
    precision = np.divide(cum_tp, denom, out=np.zeros_like(cum_tp), where=denom > 0)
    recall = cum_tp / num_gt if num_gt > 0 else np.zeros_like(cum_tp)
    return scores_sorted, precision, recall


def average_precision(precision: np.ndarray, recall: np.ndarray) -> float:
    """All-point interpolated AP: area under the precision envelope over
    recall (the continuous VOC-2010+/COCO formulation, no 11-point sampling)."""
    precision = np.asarray(precision, dtype=np.float64)
    recall = np.asarray(recall, dtype=np.float64)
    if precision.size == 0:
        return 0.0

    # prepend recall 0, append precision 0 sentinel-free via concatenation
    r = np.concatenate(([0.0], recall))
    p = np.concatenate(([0.0], precision))

    # monotone non-increasing precision envelope (right to left)
    p_env = np.maximum.accumulate(p[::-1])[::-1]

    dr = np.diff(r)
    return float(np.sum(dr * p_env[1:]))
