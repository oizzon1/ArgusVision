"""Predict-only YOLO adapter (VBB and OBB).

The thesis-era `YOLODetector` was 460 lines of predict + evaluation +
aggregation + example-saving + GSD loading (finding F3). This adapter predicts.
Evaluation lives in `argusvision.evaluation`; nothing else belongs here.

Coordinate note: the legacy adapter cast box coordinates to int at extraction;
this one keeps floats. Sub-pixel differences may therefore appear against
legacy outputs — expected, and on the new side of the Phase 4 diff.
"""

import time
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

import numpy as np

from argusvision.models.base import Detection, obb_to_aabb

YOLO_CHECKPOINTS_ROOT = Path("model_checkpoints/YOLO")


def resolve_weights(weights: str, mode: str) -> Path:
    """`model_checkpoints/YOLO/{VBB|OBB}/<weights>`, repo-root relative."""
    mode = mode.lower()
    if mode not in ("vbb", "obb"):
        raise ValueError(f"mode must be 'vbb' or 'obb', got {mode!r}")
    return YOLO_CHECKPOINTS_ROOT / mode.upper() / weights


class YoloDetector:
    """Ultralytics YOLO wrapped to emit standard `Detection` objects."""

    def __init__(
        self,
        weights: str,
        mode: str = "obb",
        conf_threshold: float = 0.25,
        class_map: Optional[Dict[int, int]] = None,
        allowed_class_ids: Optional[Iterable[int]] = None,
        device: Optional[str] = None,
    ):
        import torch
        from ultralytics import YOLO

        self.mode = mode.lower()
        self.conf_threshold = conf_threshold
        self.class_map = class_map if class_map is not None else {}
        self.allowed_class_ids: Optional[Set[int]] = (
            set(allowed_class_ids) if allowed_class_ids is not None else None
        )
        weights_path = resolve_weights(weights, self.mode)
        if not weights_path.exists():
            raise FileNotFoundError(
                f"YOLO weights not found: {weights_path} (run from repo root; "
                "weights are machine-local, see ATHENA_STATE.md)"
            )
        self.model = YOLO(str(weights_path))
        self.device = device or ("cuda:0" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)
        self.last_inference_ms: float = 0.0

    def predict(self, image_rgb: np.ndarray) -> List[Detection]:
        t0 = time.time()
        res = self.model.predict(
            source=image_rgb, conf=self.conf_threshold, verbose=False, device=self.device
        )[0]
        self.last_inference_ms = (time.time() - t0) * 1000.0

        detections: List[Detection] = []
        if self.mode == "vbb":
            if res.boxes is not None:
                for b in res.boxes:
                    cid = self._mapped_class(int(b.cls.item()))
                    if cid is None:
                        continue
                    detections.append(
                        Detection(
                            class_id=cid,
                            score=float(b.conf.item()),
                            box_xyxy=np.asarray(b.xyxy[0].tolist(), dtype=np.float64),
                        )
                    )
        else:
            if getattr(res, "obb", None) is not None:
                polys = res.obb.xyxyxyxy  # (N, 4, 2)
                clss = res.obb.cls
                confs = getattr(res.obb, "conf", None)
                for i in range(len(polys)):
                    cid = self._mapped_class(int(clss[i].item()))
                    if cid is None:
                        continue
                    obb = np.asarray(polys[i].tolist(), dtype=np.float64).reshape(8)
                    detections.append(
                        Detection(
                            class_id=cid,
                            score=float(confs[i].item()) if confs is not None else 1.0,
                            box_xyxy=obb_to_aabb(obb),
                            obb_xyxyxyxy=obb,
                        )
                    )
        return detections

    def _mapped_class(self, model_class_id: int) -> Optional[int]:
        cid = self.class_map.get(model_class_id, model_class_id)
        if self.allowed_class_ids is not None and cid not in self.allowed_class_ids:
            return None
        return cid
