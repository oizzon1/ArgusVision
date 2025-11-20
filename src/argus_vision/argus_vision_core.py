import torch
from PIL import Image
import numpy as np

class ArgusVision:
    """
    Core pipeline for ArgusVision, integrating YOLO detection with SAM segmentation.

    This class encapsulates the logic for processing a single image through
    YOLO for object detection and then using SAM for precise segmentation
    based on the YOLO detections.
    """
    def __init__(self, yolo_detector, sam_segmenter):
        """
        Initializes the ArgusVision pipeline with pre-trained YOLO and SAM models.

        Args:
            yolo_detector: An initialized YOLODetector instance from src.models.yolo_detector
            sam_segmenter: An initialized SAMSegmenter instance from src.models.sam_segmenter
        """
        self.yolo_detector = yolo_detector
        self.sam_segmenter = sam_segmenter

    def run_pipeline(self, image: np.ndarray):
        """
        Runs the ArgusVision pipeline on a single input image.

        Args:
            image (np.ndarray): The input image to process (H, W, 3) in RGB format.

        Returns:
            dict: A dictionary containing:
                - 'detections': List of YOLO detection dicts with 'bbox', 'class_id', 'confidence'
                - 'segmentation_masks': List of SAM segmentation masks (numpy arrays)
                - 'inference_time_ms': Total inference time in milliseconds
        """
        # 1. Run YOLO detection
        detections, yolo_time_ms = self.yolo_detector.predict(image)

        # 2. Convert YOLO detections to SAM prompts
        sam_prompts = self._convert_yolo_to_sam_prompts(detections)

        # 3. Run SAM segmentation
        if sam_prompts:
            segmentation_masks = self.sam_segmenter.segment(image, sam_prompts, prompt_type="box")
        else:
            segmentation_masks = []

        return {
            'detections': detections,
            'segmentation_masks': segmentation_masks,
            'inference_time_ms': yolo_time_ms  # SAM time will be added later if needed
        }

    def _convert_yolo_to_sam_prompts(self, detections):
        """
        Converts YOLO detection results into SAM box prompts.
        
        For OBB (oriented bounding boxes), we convert the 8-point polygon to an axis-aligned box.
        For VBB (vertical bounding boxes), we use the box directly.
        
        Args:
            detections: List of detection dicts from YOLODetector.predict()
                       Each dict has 'bbox', 'class_id', 'confidence'
        
        Returns:
            List of box prompts in format [x1, y1, x2, y2] for SAM
        """
        prompts = []
        
        for det in detections:
            bbox = det['bbox']
            
            if len(bbox) == 4:
                # VBB format: [x1, y1, x2, y2] - use directly
                prompts.append(np.array(bbox))
            elif len(bbox) == 8:
                # OBB format: [x1, y1, x2, y2, x3, y3, x4, y4] - convert to axis-aligned box
                x_coords = [bbox[i] for i in range(0, 8, 2)]
                y_coords = [bbox[i] for i in range(1, 8, 2)]
                x_min, x_max = min(x_coords), max(x_coords)
                y_min, y_max = min(y_coords), max(y_coords)
                prompts.append(np.array([x_min, y_min, x_max, y_max]))
            else:
                # Unknown format, skip
                continue
        
        return prompts

# Example usage (for testing purposes, not part of the core pipeline)
if __name__ == "__main__":
    # Placeholder for model initialization
    class MockYOLO:
        def predict(self, image):
            print("Mock YOLO: Detecting objects...")
            # Simulate some detections
            return [{'box': [10, 10, 50, 50], 'class': 0, 'conf': 0.9}]

    class MockSAM:
        def predict(self, image, prompts):
            print(f"Mock SAM: Segmenting based on {len(prompts)} prompts...")
            # Simulate some masks
            return [np.zeros((image.height, image.width), dtype=bool)]

    mock_yolo = MockYOLO()
    mock_sam = MockSAM()

    argus_vision_pipeline = ArgusVision(mock_yolo, mock_sam)

    # Create a dummy image
    dummy_image = Image.new('RGB', (640, 480), color = 'red')

    print("Running ArgusVision pipeline with dummy models and image...")
    results = argus_vision_pipeline.run_pipeline(dummy_image)

    print("Pipeline results:")
    print(f"Detections: {results['detections']}")
    print(f"Number of segmentation masks: {len(results['segmentation_masks'])}")
