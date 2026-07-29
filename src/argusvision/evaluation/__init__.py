"""THE evaluation stack — frozen interface; every paper number flows through here."""

from argusvision.evaluation.evaluator import (
    DEFAULT_IOU_THRESHOLDS,
    DetectionEvaluator,
    SegmentationEvaluator,
)
from argusvision.evaluation.matching import (
    MatchResult,
    box_iou,
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
from argusvision.evaluation.reporting import (
    create_run_dir,
    write_metrics,
    write_run_manifest,
)
