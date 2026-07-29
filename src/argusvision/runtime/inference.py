"""OPERATIONAL mode — batch/production inference. No evaluation imports.

Port of the legacy `ArgusVisionInference` wrapper onto the new pipeline.
Future work (unchanged from thesis TODO): mask vectorization to polygons and
GeoJSON export for GIS integration.
"""

from typing import Dict, List, Optional

import numpy as np

from argusvision.pipeline.core import DetectionSegmentationPipeline
from argusvision.pipeline.prompts import get_prompt_type


class ArgusVisionInference:
    """Clean operational interface: image in, masks + metadata out."""

    def __init__(self, detector, segmenter, class_prompt_config: Optional[Dict[int, str]] = None):
        self.pipeline = DetectionSegmentationPipeline(detector, segmenter, class_prompt_config)
        self._timings: List[Dict[str, float]] = []

    def predict(self, image_rgb: np.ndarray) -> Dict:
        result = self.pipeline.run(image_rgb)
        self._timings.append(result.timing_ms)

        classes = [d.class_id for d in result.detections]
        return {
            "masks": [m.mask for m in result.masks],
            "classes": classes,
            "confidences": [d.score for d in result.detections],
            "boxes_xyxy": [d.box_xyxy for d in result.detections],
            "obbs": [d.obb_xyxyxyxy for d in result.detections],
            "timing": result.timing_ms,
            "metadata": {
                "num_detections": len(result.detections),
                "prompt_types": self._summarize_prompt_types(classes),
            },
        }

    def predict_batch(self, images_rgb: List[np.ndarray]) -> List[Dict]:
        return [self.predict(img) for img in images_rgb]

    def get_timing_stats(self) -> Dict[str, float]:
        n = len(self._timings)
        if n == 0:
            return {"total_images": 0}
        total_det = sum(t["detection_ms"] for t in self._timings)
        total_seg = sum(t["segmentation_ms"] for t in self._timings)
        total_all = sum(t["total_ms"] for t in self._timings)
        return {
            "total_images": n,
            "total_detection_ms": total_det,
            "total_segmentation_ms": total_seg,
            "total_inference_ms": total_all,
            "avg_detection_ms": total_det / n,
            "avg_segmentation_ms": total_seg / n,
            "avg_total_ms": total_all / n,
        }

    def reset_timing(self) -> None:
        self._timings = []

    def _summarize_prompt_types(self, classes: List[int]) -> Dict[str, int]:
        cfg = self.pipeline.class_prompt_config
        box = sum(1 for c in classes if get_prompt_type(c, cfg) == "box")
        return {"box": box, "point": len(classes) - box, "total": len(classes)}


# TODO (Phase 2 of the PhD, not this restructure): vectorize_masks() ->
# polygon simplification (Douglas-Peucker) -> GeoJSON export with class,
# confidence, and pixel->geographic transform. See thesis notes.
