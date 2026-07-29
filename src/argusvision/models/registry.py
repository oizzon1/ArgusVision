"""Model registry: experiments pick models by name, never by import path.

Name conventions (all lowercase):
  detectors : ultralytics weight stem, e.g. "yolo11x-obb", "yolov8n-obb",
              "yolo11x" (VBB when no -obb suffix). Weights file = <name>.pt
              under model_checkpoints/YOLO/{OBB|VBB}/.
  segmenters: "sam-vit-b" / "sam-vit-l" / "sam-vit-h".

`detector_spec` / `segmenter_spec` resolve names without touching model
weights, so name resolution is unit-testable on machines without checkpoints.
"""

from pathlib import Path
from typing import Tuple

from argusvision.models.sam import resolve_checkpoint
from argusvision.models.yolo import resolve_weights


def detector_spec(name: str) -> Tuple[str, str]:
    """Resolve a detector name to (weights_filename, mode)."""
    name = name.lower().strip()
    if not name.startswith("yolo"):
        raise ValueError(f"unknown detector family in name {name!r}")
    mode = "obb" if name.endswith("-obb") else "vbb"
    return f"{name}.pt", mode


def segmenter_spec(name: str) -> Tuple[str, Path]:
    """Resolve a segmenter name to (sam_type, checkpoint_path)."""
    name = name.lower().strip()
    if not name.startswith("sam-"):
        raise ValueError(f"unknown segmenter family in name {name!r}")
    sam_type = name[len("sam-"):].replace("-", "_")  # "vit-b" -> "vit_b"
    return sam_type, resolve_checkpoint(sam_type)


def create_detector(name: str, **overrides):
    """Instantiate a detector by name (loads weights)."""
    from argusvision.models.yolo import YoloDetector

    weights, mode = detector_spec(name)
    overrides.setdefault("mode", mode)
    return YoloDetector(weights=weights, **overrides)


def create_segmenter(name: str, **overrides):
    """Instantiate a segmenter by name (loads checkpoint)."""
    from argusvision.models.sam import SamSegmenter

    sam_type, _ = segmenter_spec(name)
    return SamSegmenter(sam_type=sam_type, **overrides)


def detector_weights_exist(name: str) -> bool:
    weights, mode = detector_spec(name)
    return resolve_weights(weights, mode).exists()
