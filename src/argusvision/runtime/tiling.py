"""Tiled inference: run any `Detector` over overlapping windows of a large image.

Aerial images are far larger than a detector's input resolution. Feeding one
whole DOTA image (up to ~13000 px) to a 640-px network shrinks a car to a few
pixels and the detector never sees it. F6b measured the cost on the 456-image
AerialFuseCV val split: full-image YOLOv11x-OBB recall 0.607 against 0.852
tiled, with small-vehicle recall 0.530 -> 0.790 and ship 0.597 -> 0.936
(`results/experimental/f6b_tiling_yolo11x_obb/`). Large objects barely moved, which is what
identifies the cause as input scale rather than detector quality.

`TiledDetector` wraps a detector rather than replacing it: it satisfies the
same `Detector` protocol, so the pipeline, the evaluator and every config path
treat a tiled detector exactly like a plain one. Detections come back in
FULL-IMAGE coordinates — scoring them in tile coordinates would measure a
different task.

Known limitation (open, tracked for F8): an object crossing a tile seam yields
two partial boxes whose mutual IoU is near zero, so NMS keeps both and the
object is counted twice. This inflates the false-positive count and is part of
why tiled precision sits below full-image precision. Quantify before any P2
number is final.
"""

from typing import Iterable, List, Optional, Sequence, Tuple

import numpy as np

from argusvision.data.constants import NUM_DOTA_CLASSES
from argusvision.models.base import Detection

__all__ = ["TiledDetector", "tile_origins", "rotated_nms", "shift_detections"]


def tile_origins(
    width: int, height: int, tile_size: int, overlap: int
) -> List[Tuple[int, int]]:
    """Top-left corners of the tiles covering a `width` x `height` image.

    Tiles step by `tile_size - overlap`. The final row and column are pulled
    back flush with the image edge, so coverage is complete and no tile is
    padded — a partial tile would change the input statistics of the last
    window relative to every other one.
    """
    if tile_size <= 0:
        raise ValueError(f"tile_size must be positive, got {tile_size}")
    if overlap < 0:
        raise ValueError(f"overlap must be non-negative, got {overlap}")
    if overlap >= tile_size:
        raise ValueError(
            f"overlap ({overlap}) must be smaller than tile_size ({tile_size})"
        )
    stride = tile_size - overlap

    def starts(length: int) -> List[int]:
        if length <= tile_size:
            return [0]
        vals = list(range(0, length - tile_size + 1, stride))
        last = length - tile_size
        if vals[-1] != last:
            vals.append(last)
        return vals

    return [(x, y) for y in starts(height) for x in starts(width)]


def shift_detections(
    detections: Sequence[Detection], x0: float, y0: float, width: int, height: int
) -> List[Detection]:
    """Move tile-local detections into full-image coordinates.

    Boxes are clipped to the image and degenerate results (under 1 px on either
    axis after clipping) are dropped — those are edge slivers, not objects.
    """
    shifted: List[Detection] = []
    obb_offset = np.array([x0, y0] * 4, dtype=np.float64)
    aabb_offset = np.array([x0, y0, x0, y0], dtype=np.float64)

    for det in detections:
        obb = None
        if det.obb_xyxyxyxy is not None:
            obb = np.asarray(det.obb_xyxyxyxy, dtype=np.float64).reshape(8) + obb_offset
            obb[0::2] = np.clip(obb[0::2], 0, max(width - 1, 0))
            obb[1::2] = np.clip(obb[1::2], 0, max(height - 1, 0))
            if (
                np.ptp(obb[0::2]) < 1.0
                or np.ptp(obb[1::2]) < 1.0
            ):
                continue

        box = np.asarray(det.box_xyxy, dtype=np.float64).reshape(4) + aabb_offset
        box[0::2] = np.clip(box[0::2], 0, max(width - 1, 0))
        box[1::2] = np.clip(box[1::2], 0, max(height - 1, 0))
        if box[2] - box[0] < 1.0 or box[3] - box[1] < 1.0:
            continue

        shifted.append(
            Detection(
                class_id=det.class_id,
                score=det.score,
                box_xyxy=box,
                obb_xyxyxyxy=obb,
            )
        )
    return shifted


def rotated_nms(
    detections: Sequence[Detection],
    iou_threshold: float,
    num_classes: int = NUM_DOTA_CLASSES,
) -> List[Detection]:
    """Class-wise non-maximum suppression on rotated boxes.

    Suppression is per class: two different classes overlapping is a
    disagreement to be scored, not a duplicate to be removed. Detections
    without an OBB fall back to their axis-aligned box, so this works for
    oriented and unoriented detectors alike.
    """
    import cv2  # local import: keeps the package importable without OpenCV

    kept: List[Detection] = []
    for class_id in range(num_classes):
        class_dets = [d for d in detections if d.class_id == class_id]
        if not class_dets:
            continue

        rects, scores, valid = [], [], []
        for det in class_dets:
            if det.obb_xyxyxyxy is not None:
                pts = np.asarray(det.obb_xyxyxyxy, dtype=np.float32).reshape(4, 2)
            else:
                x1, y1, x2, y2 = np.asarray(det.box_xyxy, dtype=np.float32)
                pts = np.array(
                    [[x1, y1], [x2, y1], [x2, y2], [x1, y2]], dtype=np.float32
                )
            rect = cv2.minAreaRect(pts)
            if rect[1][0] < 1.0 or rect[1][1] < 1.0:
                continue
            rects.append(rect)
            scores.append(float(det.score))
            valid.append(det)

        if not valid:
            continue

        indices = cv2.dnn.NMSBoxesRotated(
            rects, scores, score_threshold=0.0, nms_threshold=float(iou_threshold)
        )
        if len(indices) == 0:
            continue
        for idx in np.asarray(indices).reshape(-1):
            kept.append(valid[int(idx)])

    kept.sort(key=lambda d: d.score, reverse=True)
    return kept


def _batched(items: Sequence, size: int) -> Iterable[Sequence]:
    for start in range(0, len(items), size):
        yield items[start : start + size]


class TiledDetector:
    """Adapter that runs a `Detector` over overlapping tiles.

    Satisfies the `Detector` protocol, so it is a drop-in for the wrapped
    detector everywhere: pipeline, evaluator, configs.

    A detector exposing `predict_batch(List[np.ndarray]) -> List[List[Detection]]`
    gets its tiles submitted in batches of `batch_size`; otherwise tiles go
    through `predict` one at a time. Either way the detections are identical —
    batching is throughput only.

    Per-image statistics from the most recent `predict` are on `last_stats`
    (`num_tiles`, `num_raw`, `num_final`), which is what makes the
    duplicate-suppression rate observable rather than guessed at.
    """

    def __init__(
        self,
        detector,
        tile_size: int = 1024,
        overlap: int = 200,
        nms_iou: float = 0.5,
        batch_size: int = 8,
        num_classes: int = NUM_DOTA_CLASSES,
    ):
        self.detector = detector
        self.tile_size = tile_size
        self.overlap = overlap
        self.nms_iou = nms_iou
        self.batch_size = batch_size
        self.num_classes = num_classes
        self.last_stats: dict = {}
        # Fail on a bad geometry now, not on the first image of a long run.
        tile_origins(tile_size, tile_size, tile_size, overlap)

    def predict(self, image_rgb: np.ndarray) -> List[Detection]:
        height, width = image_rgb.shape[:2]
        origins = tile_origins(width, height, self.tile_size, self.overlap)
        tiles = [
            image_rgb[y : y + self.tile_size, x : x + self.tile_size]
            for x, y in origins
        ]

        raw: List[Detection] = []
        batch_fn = getattr(self.detector, "predict_batch", None)
        if callable(batch_fn):
            index = 0
            for batch in _batched(tiles, self.batch_size):
                for tile_dets in batch_fn(list(batch)):
                    x0, y0 = origins[index]
                    raw.extend(shift_detections(tile_dets, x0, y0, width, height))
                    index += 1
        else:
            for (x0, y0), tile in zip(origins, tiles):
                raw.extend(
                    shift_detections(
                        self.detector.predict(tile), x0, y0, width, height
                    )
                )

        final = rotated_nms(raw, self.nms_iou, self.num_classes)
        self.last_stats = {
            "num_tiles": len(origins),
            "num_raw": len(raw),
            "num_final": len(final),
        }
        return final

    def __repr__(self) -> str:
        return (
            f"TiledDetector({self.detector!r}, tile_size={self.tile_size}, "
            f"overlap={self.overlap}, nms_iou={self.nms_iou})"
        )


def maybe_tile(detector, config: Optional[dict]):
    """Wrap `detector` if `config` enables tiling, else return it unchanged.

    Lets a config carry a `tiling:` block without every call site branching.
    """
    if not config or not config.get("enabled", False):
        return detector
    return TiledDetector(
        detector,
        tile_size=int(config.get("tile_size", 1024)),
        overlap=int(config.get("overlap", 200)),
        nms_iou=float(config.get("nms_iou", 0.5)),
        batch_size=int(config.get("batch_size", 8)),
    )
