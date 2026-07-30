"""THE evaluator — model-agnostic, consumes standard types only.

`DetectionEvaluator` accumulates over a dataset and reports, per IoU threshold:
  - per class: TP/FP/FN (Hungarian, set-level), precision/recall/F1, ranked AP
  - micro_* : pooled-count metrics (every instance weighs the same)
  - macro_f1: unweighted mean F1 over classes with any GT or predictions
  - mean_ap : mean AP over classes WITH ground truth (a real mAP, honestly
              computed; classes with no GT have undefined AP and are excluded)

`SegmentationEvaluator` accumulates matched mask pairs and reports the two
thesis conventions side by side:
  - tp_only     : mean IoU/Dice over successfully detected instances
  - gt_anchored : every GT instance counts; missed detections contribute 0.0
                  (the operational, error-propagating view)

Matching is within-class, per image. Default box IoU is exact polygon IoU when
OBBs are present ("auto"); "aabb" reproduces the legacy V2 collapse for the
Phase 4 validation diff only.
"""

from collections import defaultdict
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

from argusvision.data.constants import CLASS_ID_TO_NAME, NUM_DOTA_CLASSES
from argusvision.evaluation.matching import (
    MatchResult,
    hungarian_match,
    iou_matrix,
    match_by_confidence,
)
from argusvision.evaluation.metrics import (
    average_precision,
    dice_from_iou,
    macro_f1,
    mask_dice,
    mask_iou,
    pr_curve,
    precision_recall_f1,
)
from argusvision.models.base import Detection, GroundTruthInstance, InstanceMask

DEFAULT_IOU_THRESHOLDS = (0.1, 0.3, 0.5)


class DetectionEvaluator:
    """Accumulate detection results image by image; summarize once."""

    def __init__(
        self,
        num_classes: int = NUM_DOTA_CLASSES,
        iou_thresholds: Sequence[float] = DEFAULT_IOU_THRESHOLDS,
        iou_mode: str = "auto",
        class_names: Optional[Dict[int, str]] = None,
    ):
        self.num_classes = num_classes
        self.iou_thresholds = tuple(iou_thresholds)
        self.iou_mode = iou_mode
        self.class_names = class_names if class_names is not None else CLASS_ID_TO_NAME
        self.num_images = 0
        # per threshold, per class: running Hungarian counts
        self._counts = {
            t: np.zeros((num_classes, 3), dtype=np.int64) for t in self.iou_thresholds
        }  # columns: tp, fp, fn
        # per threshold, per class: (score, tp_flag) pairs for PR/AP
        self._ranked: Dict[float, Dict[int, List[Tuple[float, bool]]]] = {
            t: defaultdict(list) for t in self.iou_thresholds
        }
        self._gt_per_class = np.zeros(num_classes, dtype=np.int64)
        # matched IoUs (Hungarian) per class at the LOWEST threshold, for mean matched IoU
        self._matched_ious: Dict[int, List[float]] = defaultdict(list)

    def add_image(
        self, predictions: Sequence[Detection], ground_truth: Sequence[GroundTruthInstance]
    ) -> Dict[float, MatchResult]:
        """Accumulate one image. Returns the Hungarian MatchResult per threshold
        for the WHOLE image (class-wise matching merged), so callers building a
        pipeline evaluation can reuse the pairing without re-matching."""
        self.num_images += 1
        for g in ground_truth:
            self._gt_per_class[g.class_id] += 1

        merged: Dict[float, MatchResult] = {t: MatchResult() for t in self.iou_thresholds}

        for c in range(self.num_classes):
            pred_idx = [i for i, p in enumerate(predictions) if p.class_id == c]
            gt_idx = [j for j, g in enumerate(ground_truth) if g.class_id == c]
            if not pred_idx and not gt_idx:
                continue
            preds_c = [predictions[i] for i in pred_idx]
            gts_c = [ground_truth[j] for j in gt_idx]
            ious = iou_matrix(preds_c, gts_c, mode=self.iou_mode)
            scores_c = [p.score for p in preds_c]

            for t in self.iou_thresholds:
                res = hungarian_match(ious, t)
                self._counts[t][c, 0] += res.tp
                self._counts[t][c, 1] += res.fp
                self._counts[t][c, 2] += res.fn
                if t == min(self.iou_thresholds):
                    self._matched_ious[c].extend(iou for _, _, iou in res.matches)

                tp_flags = match_by_confidence(ious, scores_c, t)
                self._ranked[t][c].extend(zip(scores_c, tp_flags.tolist()))

                m = merged[t]
                m.matches.extend(
                    (pred_idx[p], gt_idx[g], iou) for p, g, iou in res.matches
                )
                m.unmatched_pred.extend(pred_idx[p] for p in res.unmatched_pred)
                m.unmatched_gt.extend(gt_idx[g] for g in res.unmatched_gt)

        return merged

    def summarize(self) -> Dict:
        out: Dict = {
            "num_images": self.num_images,
            "iou_mode": self.iou_mode,
            "matching": "hungarian (set counts) + confidence-ranked (AP)",
            "per_threshold": {},
        }
        for t in self.iou_thresholds:
            counts = self._counts[t]
            per_class = {}
            f1_by_class: Dict[int, float] = {}
            ap_by_class: Dict[int, float] = {}
            for c in range(self.num_classes):
                tp, fp, fn = (int(x) for x in counts[c])
                precision, recall, f1 = precision_recall_f1(tp, fp, fn)
                f1_by_class[c] = f1

                ranked = self._ranked[t][c]
                num_gt = int(self._gt_per_class[c])
                entry = {
                    "tp": tp,
                    "fp": fp,
                    "fn": fn,
                    "precision": precision,
                    "recall": recall,
                    "f1": f1,
                    "num_gt": num_gt,
                }
                if num_gt > 0:
                    if ranked:
                        scores = np.array([s for s, _ in ranked])
                        flags = np.array([f for _, f in ranked], dtype=bool)
                        _, p_curve, r_curve = pr_curve(scores, flags, num_gt)
                        ap = average_precision(p_curve, r_curve)
                    else:
                        ap = 0.0
                    entry["average_precision"] = ap
                    ap_by_class[c] = ap
                per_class[self.class_names.get(c, str(c))] = entry

            present = [
                c
                for c in range(self.num_classes)
                if counts[c].sum() > 0 or self._gt_per_class[c] > 0
            ]
            micro_tp = int(counts[:, 0].sum())
            micro_fp = int(counts[:, 1].sum())
            micro_fn = int(counts[:, 2].sum())
            mp, mr, mf1 = precision_recall_f1(micro_tp, micro_fp, micro_fn)

            out["per_threshold"][t] = {
                "per_class": per_class,
                "micro_precision": mp,
                "micro_recall": mr,
                "micro_f1": mf1,
                "macro_f1": macro_f1(f1_by_class, present),
                "mean_ap": (
                    float(np.mean(list(ap_by_class.values()))) if ap_by_class else 0.0
                ),
                "micro_counts": {"tp": micro_tp, "fp": micro_fp, "fn": micro_fn},
            }

        all_matched = [x for c in self._matched_ious for x in self._matched_ious[c]]
        out["matched_box_iou_mean_at_lowest_threshold"] = (
            float(np.mean(all_matched)) if all_matched else 0.0
        )
        return out


class SegmentationEvaluator:
    """Accumulate mask quality for instances paired by detection matching."""

    def __init__(
        self,
        num_classes: int = NUM_DOTA_CLASSES,
        class_names: Optional[Dict[int, str]] = None,
    ):
        self.num_classes = num_classes
        self.class_names = class_names if class_names is not None else CLASS_ID_TO_NAME
        self._tp_iou: Dict[int, List[float]] = defaultdict(list)
        self._tp_dice: Dict[int, List[float]] = defaultdict(list)
        self._anchored_iou: Dict[int, List[float]] = defaultdict(list)
        self._anchored_dice: Dict[int, List[float]] = defaultdict(list)
        self._no_mask_gt: Dict[int, int] = defaultdict(int)

    def add_pair(self, class_id: int, pred_mask: np.ndarray, gt_mask: np.ndarray) -> float:
        """One successfully detected instance: pred mask vs its GT mask."""
        iou = mask_iou(pred_mask, gt_mask)
        dice = mask_dice(pred_mask, gt_mask)
        self._tp_iou[class_id].append(iou)
        self._tp_dice[class_id].append(dice)
        self._anchored_iou[class_id].append(iou)
        self._anchored_dice[class_id].append(dice)
        return iou

    def add_missed_gt(self, class_id: int) -> None:
        """One GT instance the detector never found: contributes 0 to the
        GT-anchored view and nothing to the TP-only view. A real failure."""
        self._anchored_iou[class_id].append(0.0)
        self._anchored_dice[class_id].append(0.0)

    def add_gt_without_mask(self, class_id: int) -> None:
        """One ground-truth OBJECT that carries no ground-truth MASK.

        Arises where the box source annotated an object the mask source did
        not (DOTA/iSAID annotate independently). Such an object is excluded
        from BOTH views and counted instead: scoring it 0 would charge the
        system for the annotation's absence, not for any failure of its own.

        The rule keys on the mask ground truth's existence, independently of
        the detection outcome — a mask that was never drawn cannot be missed,
        so this applies whether or not the detector found the object.

        See `documentation/DECISION_unpaired_annotations.md`.
        """
        self._no_mask_gt[class_id] += 1

    def summarize(self) -> Dict:
        per_class = {}
        for c in range(self.num_classes):
            if not self._anchored_iou[c] and not self._tp_iou[c] and not self._no_mask_gt[c]:
                continue
            per_class[self.class_names.get(c, str(c))] = {
                "n_matched": len(self._tp_iou[c]),
                "n_gt_anchored": len(self._anchored_iou[c]),
                "n_excluded_no_mask_gt": self._no_mask_gt[c],
                "tp_only_iou": float(np.mean(self._tp_iou[c])) if self._tp_iou[c] else 0.0,
                "tp_only_dice": float(np.mean(self._tp_dice[c])) if self._tp_dice[c] else 0.0,
                "gt_anchored_iou": float(np.mean(self._anchored_iou[c])),
                "gt_anchored_dice": float(np.mean(self._anchored_dice[c])),
            }
        all_tp_iou = [x for c in self._tp_iou for x in self._tp_iou[c]]
        all_tp_dice = [x for c in self._tp_dice for x in self._tp_dice[c]]
        all_an_iou = [x for c in self._anchored_iou for x in self._anchored_iou[c]]
        all_an_dice = [x for c in self._anchored_dice for x in self._anchored_dice[c]]
        n_excluded = sum(self._no_mask_gt.values())
        n_scoreable = len(all_an_iou) + n_excluded
        return {
            "per_class": per_class,
            # Objects excluded because no ground-truth mask exists for them.
            # Reported, never silently dropped — see
            # documentation/DECISION_unpaired_annotations.md
            "excluded_no_mask_gt": {
                "count": n_excluded,
                "fraction_of_gt_objects": (n_excluded / n_scoreable) if n_scoreable else 0.0,
            },
            "overall": {
                "n_matched": len(all_tp_iou),
                "n_gt_anchored": len(all_an_iou),
                "n_excluded_no_mask_gt": n_excluded,
                "tp_only_iou": float(np.mean(all_tp_iou)) if all_tp_iou else 0.0,
                "tp_only_dice": float(np.mean(all_tp_dice)) if all_tp_dice else 0.0,
                "gt_anchored_iou": float(np.mean(all_an_iou)) if all_an_iou else 0.0,
                "gt_anchored_dice": float(np.mean(all_an_dice)) if all_an_dice else 0.0,
            },
        }
