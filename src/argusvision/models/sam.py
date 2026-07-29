"""SAM adapter — the legacy `SAMSegmenter` was already predict-only; ported
near-unchanged. The one performance-critical property is preserved: the image
is encoded ONCE per call (`set_image`), then every prompt reuses the embedding
(SAM encoding is ~92% of the pipeline budget on the 3090 Ti).
"""

import warnings
from pathlib import Path
from typing import List, Optional, Sequence

import numpy as np

SAM_CHECKPOINTS_ROOT = Path("model_checkpoints/SAM")

# Official checkpoint filenames as present on the NTUA dev PC.
SAM_CHECKPOINT_FILES = {
    "vit_b": "sam_vit_b_01ec64.pth",
    "vit_l": "sam_vit_l_0b3195.pth",
    "vit_h": "sam_vit_h_4b8939.pth",
}


def resolve_checkpoint(sam_type: str) -> Path:
    if sam_type not in SAM_CHECKPOINT_FILES:
        raise ValueError(
            f"unknown SAM type {sam_type!r}; expected one of {sorted(SAM_CHECKPOINT_FILES)}"
        )
    return SAM_CHECKPOINTS_ROOT / SAM_CHECKPOINT_FILES[sam_type]


class SamSegmenter:
    """segment-anything wrapped to emit one binary (H, W) mask per prompt."""

    def __init__(self, sam_type: str = "vit_b", checkpoint: Optional[str] = None, device: Optional[str] = None):
        import torch
        from segment_anything import SamPredictor, sam_model_registry

        warnings.filterwarnings("ignore", category=FutureWarning, module="segment_anything")

        checkpoint_path = Path(checkpoint) if checkpoint else resolve_checkpoint(sam_type)
        if not checkpoint_path.exists():
            raise FileNotFoundError(
                f"SAM checkpoint not found: {checkpoint_path} (run from repo root; "
                "checkpoints are machine-local, see ATHENA_STATE.md)"
            )
        self.sam_type = sam_type
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.sam = sam_model_registry[sam_type](checkpoint=str(checkpoint_path))
        self.sam.to(self.device)
        self.predictor = SamPredictor(self.sam)

    # ------------------------- protocol method -------------------------
    def predict_masks(
        self, image_rgb: np.ndarray, box_prompts_xyxy: Sequence[np.ndarray]
    ) -> List[np.ndarray]:
        """One mask per box prompt, in prompt order."""
        return self.segment(image_rgb, list(box_prompts_xyxy), prompt_type="box")

    # ------------------------- general prompting -----------------------
    def segment(
        self, image_rgb: np.ndarray, prompts: List, prompt_type: str = "box"
    ) -> List[np.ndarray]:
        """Encode the image once, then run every prompt against the embedding.

        prompts: for "box", each entry is [x1, y1, x2, y2];
                 for "point", each entry is [x, y].
        """
        if prompt_type not in ("box", "point"):
            raise ValueError("prompt_type must be 'box' or 'point'")

        self.predictor.set_image(image_rgb)
        masks: List[np.ndarray] = []

        if prompt_type == "box":
            for box in prompts:
                mask, _, _ = self.predictor.predict(
                    box=np.asarray(box, dtype=np.float32), multimask_output=False
                )
                masks.append(np.asarray(mask).squeeze().astype(bool))
        else:
            for point in prompts:
                point = np.asarray(point, dtype=np.float32).reshape(-1)[:2]
                mask, _, _ = self.predictor.predict(
                    point_coords=point[None, :],
                    point_labels=np.array([1]),
                    multimask_output=False,
                )
                masks.append(np.asarray(mask).squeeze().astype(bool))
        return masks
