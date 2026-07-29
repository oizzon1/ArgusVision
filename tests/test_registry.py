"""Registry name resolution — no weights loading involved."""

from pathlib import Path

import pytest

from argusvision.models.registry import detector_spec, segmenter_spec
from argusvision.models.sam import resolve_checkpoint
from argusvision.models.yolo import resolve_weights


def test_detector_spec_obb():
    assert detector_spec("yolo11x-obb") == ("yolo11x-obb.pt", "obb")
    assert detector_spec("YOLOv8n-OBB") == ("yolov8n-obb.pt", "obb")


def test_detector_spec_vbb_default():
    assert detector_spec("yolo11x") == ("yolo11x.pt", "vbb")


def test_detector_spec_rejects_unknown_family():
    with pytest.raises(ValueError):
        detector_spec("rtdetr-x")


def test_segmenter_spec_names():
    sam_type, ckpt = segmenter_spec("sam-vit-b")
    assert sam_type == "vit_b"
    assert ckpt == Path("model_checkpoints/SAM/sam_vit_b_01ec64.pth")
    assert segmenter_spec("sam-vit-h")[0] == "vit_h"


def test_segmenter_spec_rejects_unknown():
    with pytest.raises(ValueError):
        segmenter_spec("mobilesam")  # P4 material, not registered yet
    with pytest.raises(ValueError):
        resolve_checkpoint("vit_g")


def test_yolo_weights_paths():
    assert resolve_weights("yolo11x-obb.pt", "obb") == Path(
        "model_checkpoints/YOLO/OBB/yolo11x-obb.pt"
    )
    with pytest.raises(ValueError):
        resolve_weights("x.pt", "hbb")
