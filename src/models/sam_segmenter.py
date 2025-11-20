import torch
from segment_anything import SamPredictor, sam_model_registry
import numpy as np

class SAMSegmenter:
    def __init__(self, sam_type="vit_h", checkpoint_path="model_checkpoints/SAM/sam_vit_h.pth", device=None):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.sam = sam_model_registry[sam_type](checkpoint=checkpoint_path)
        self.sam.to(self.device)
        self.predictor = SamPredictor(self.sam)

    def segment(self, image: np.ndarray, prompts: list, prompt_type: str = "box"):
        """
        Segment objects in image using SAM with either box or point prompts.

        Args:
            image (np.ndarray): Input image (H, W, 3)
            prompts (list): List of prompts (boxes or points)
            prompt_type (str): "box" or "point"

        Returns:
            masks (list): List of segmentation masks
        """
        self.predictor.set_image(image)
        masks = []

        if prompt_type == "box":
            # Each prompt is [x1, y1, x2, y2]
            for box in prompts:
                mask, _, _ = self.predictor.predict(box=box, multimask_output=False)
                masks.append(mask)
        elif prompt_type == "point":
            # Each prompt is [x, y]
            for point in prompts:
                mask, _, _ = self.predictor.predict(point_coords=np.array([point]), point_labels=np.array([1]), multimask_output=False)
                masks.append(mask)
        else:
            raise ValueError("prompt_type must be 'box' or 'point'")

        return masks
