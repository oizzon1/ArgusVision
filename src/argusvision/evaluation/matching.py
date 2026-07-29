"""Prediction-to-ground-truth matching — the single implementation.

Two matchers exist because they answer different questions, and each is the
standard tool for its question:

- `hungarian_match`: optimal one-to-one assignment of a *fixed* detection set.
  Used for set-level TP/FP/FN (and for pairing pipeline masks to GT masks).
- `match_by_confidence`: detections judged in descending-confidence order, each
  taking the best still-unmatched GT — the VOC/COCO ranking protocol that PR
  curves and AP require. The thesis-era greedy matcher iterated in *arbitrary*
  order (finding F2), letting a low-confidence detection steal a GT from a
  high-confidence one; ordering is enforced here.

Both operate on a plain IoU matrix; class filtering is the caller's job
(the evaluator matches within each class separately).

Box IoU: true polygon IoU via shapely for OBBs, rectangle IoU for AABBs.
`mode="aabb"` collapses OBBs to their axis-aligned hulls first — that is what
the thesis-era V2 evaluator silently did; it is kept only so the Phase 4
validation diff can reproduce legacy numbers, and is not the default.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple

import numpy as np
from scipy.optimize import linear_sum_assignment
from shapely.geometry import Polygon
from shapely.geometry import box as shapely_box

from argusvision.models.base import Detection, GroundTruthInstance, obb_to_aabb


def _to_polygon(box_xyxy: np.ndarray, obb_xyxyxyxy: Optional[np.ndarray], mode: str) -> Polygon:
    if obb_xyxyxyxy is not None and mode == "auto":
        pts = np.asarray(obb_xyxyxyxy, dtype=np.float64).reshape(4, 2)
        return Polygon(pts)
    if obb_xyxyxyxy is not None and mode == "aabb":
        box_xyxy = obb_to_aabb(obb_xyxyxyxy)
    x1, y1, x2, y2 = np.asarray(box_xyxy, dtype=np.float64)
    return shapely_box(x1, y1, x2, y2)


def box_iou(
    a_box: np.ndarray,
    b_box: np.ndarray,
    a_obb: Optional[np.ndarray] = None,
    b_obb: Optional[np.ndarray] = None,
    mode: str = "auto",
) -> float:
    """IoU between two boxes. Polygon IoU when both sides carry an OBB and
    mode="auto"; rectangle IoU otherwise. A mixed pair (one OBB, one AABB)
    compares polygon against rectangle, which is still exact."""
    if mode not in ("auto", "aabb"):
        raise ValueError(f"unknown IoU mode: {mode!r}")
    p1 = _to_polygon(a_box, a_obb, mode)
    p2 = _to_polygon(b_box, b_obb, mode)
    if not p1.is_valid or not p2.is_valid:
        return 0.0
    union = p1.union(p2).area
    if union <= 0.0:
        return 0.0
    return float(p1.intersection(p2).area / union)


def iou_matrix(
    predictions: Sequence[Detection],
    ground_truth: Sequence[GroundTruthInstance],
    mode: str = "auto",
) -> np.ndarray:
    """(n_pred, n_gt) IoU matrix."""
    m = np.zeros((len(predictions), len(ground_truth)), dtype=np.float64)
    for i, p in enumerate(predictions):
        for j, g in enumerate(ground_truth):
            m[i, j] = box_iou(p.box_xyxy, g.box_xyxy, p.obb_xyxyxyxy, g.obb_xyxyxyxy, mode)
    return m


@dataclass
class MatchResult:
    """Outcome of matching one prediction set against one GT set."""

    matches: List[Tuple[int, int, float]] = field(default_factory=list)  # (pred_i, gt_j, iou)
    unmatched_pred: List[int] = field(default_factory=list)
    unmatched_gt: List[int] = field(default_factory=list)

    @property
    def tp(self) -> int:
        return len(self.matches)

    @property
    def fp(self) -> int:
        return len(self.unmatched_pred)

    @property
    def fn(self) -> int:
        return len(self.unmatched_gt)


def hungarian_match(ious: np.ndarray, iou_threshold: float) -> MatchResult:
    """Optimal one-to-one assignment maximizing total IoU; pairs below the
    threshold are discarded (their members count as FP / FN)."""
    n_pred, n_gt = ious.shape
    result = MatchResult()
    if n_pred == 0 or n_gt == 0:
        result.unmatched_pred = list(range(n_pred))
        result.unmatched_gt = list(range(n_gt))
        return result

    pred_idx, gt_idx = linear_sum_assignment(-ious)
    matched_pred, matched_gt = set(), set()
    for p, g in zip(pred_idx, gt_idx):
        if ious[p, g] >= iou_threshold:
            result.matches.append((int(p), int(g), float(ious[p, g])))
            matched_pred.add(int(p))
            matched_gt.add(int(g))
    result.unmatched_pred = [i for i in range(n_pred) if i not in matched_pred]
    result.unmatched_gt = [j for j in range(n_gt) if j not in matched_gt]
    return result


def match_by_confidence(
    ious: np.ndarray, scores: Sequence[float], iou_threshold: float
) -> np.ndarray:
    """VOC/COCO ranking protocol: visit predictions in descending confidence;
    each takes the highest-IoU still-unmatched GT if that IoU >= threshold.

    Returns a bool array `tp_flags` aligned to the ORIGINAL prediction order
    (not the sorted order); pair it with `scores` for PR-curve accumulation.
    """
    n_pred, n_gt = ious.shape
    scores = np.asarray(scores, dtype=np.float64)
    if scores.shape[0] != n_pred:
        raise ValueError("scores length must equal number of predictions")

    tp_flags = np.zeros(n_pred, dtype=bool)
    if n_pred == 0 or n_gt == 0:
        return tp_flags

    gt_taken = np.zeros(n_gt, dtype=bool)
    # stable sort => ties keep original order, making results deterministic
    for p in np.argsort(-scores, kind="stable"):
        candidate_ious = np.where(gt_taken, -1.0, ious[p])
        g = int(np.argmax(candidate_ious))
        if candidate_ious[g] >= iou_threshold:
            tp_flags[p] = True
            gt_taken[g] = True
    return tp_flags
