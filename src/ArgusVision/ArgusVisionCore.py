"""
ArgusVisionCore: Main pipeline integrating YOLO detection with SAM segmentation.

This is the core pipeline that handles both inference and evaluation modes.
Supports per-class prompt configuration (box or point prompts).
"""

import time
import numpy as np
import torch
from typing import Dict, List, Tuple, Optional, Union
from PIL import Image

from src.ArgusVision.config.class_prompt_config import CLASS_PROMPT_CONFIG, get_prompt_type


class ArgusVisionCore:
    """
    Core pipeline for ArgusVision combining YOLO detection → SAM segmentation.
    
    Features:
    - Dual-mode: Inference (operational) and Evaluation (benchmarking)
    - Per-class prompt configuration (box or point)
    - Comprehensive timing tracking
    - OBB → VBB conversion for SAM compatibility
    """
    
    def __init__(self, yolo_detector, sam_segmenter, class_prompt_config=None):
        """
        Initialize ArgusVision pipeline.
        
        Args:
            yolo_detector: Initialized YOLO detector instance
            sam_segmenter: Initialized SAM segmenter instance
            class_prompt_config: Dict mapping class_id → 'box'/'point'
                               If None, uses default from CLASS_PROMPT_CONFIG
        """
        self.yolo = yolo_detector
        self.sam = sam_segmenter
        self.prompt_config = class_prompt_config or CLASS_PROMPT_CONFIG
        
        # Timing accumulators
        self.reset_timing()
        
    def reset_timing(self):
        """Reset timing statistics"""
        self.total_detection_time = 0.0
        self.total_segmentation_time = 0.0
        self.total_inference_time = 0.0
        self.num_images_processed = 0
        
    def run_inference(self, image: Union[np.ndarray, Image.Image]) -> Dict:
        """
        Run pipeline in INFERENCE mode (operational).
        
        Args:
            image: Input image as numpy array (H,W,3) RGB or PIL Image
            
        Returns:
            dict: {
                'detections': List of detection dicts,
                'masks': List of binary masks (np.ndarray),
                'classes': List of class IDs,
                'confidences': List of detection confidences,
                'timing': {'detection_ms': X, 'segmentation_ms': Y, 'total_ms': Z}
            }
        """
        start_time = time.time()
        
        # Convert PIL to numpy if needed
        if isinstance(image, Image.Image):
            image_np = np.array(image)
        else:
            image_np = image
            
        # 1. YOLO Detection
        detections, det_time = self.yolo.predict(image_np)
        # det_time is already in milliseconds from YOLODetector
        
        # 2. Generate SAM prompts based on class configuration
        sam_prompts = self._generate_sam_prompts(detections)
        
        # 3. SAM Segmentation
        seg_start = time.time()
        if sam_prompts:
            masks = self._run_sam_segmentation(image_np, sam_prompts)
        else:
            masks = []
        seg_time = (time.time() - seg_start) * 1000  # milliseconds
        
        total_time = (time.time() - start_time) * 1000
        
        # Update timing stats
        self.total_detection_time += det_time
        self.total_segmentation_time += seg_time
        self.total_inference_time += total_time
        self.num_images_processed += 1
        
        # Extract metadata from detections
        classes = [d['class_id'] for d in detections]
        confidences = [d['confidence'] for d in detections]
        
        return {
            'detections': detections,
            'masks': masks,
            'classes': classes,
            'confidences': confidences,
            'timing': {
                'detection_ms': det_time,
                'segmentation_ms': seg_time,
                'total_ms': total_time
            }
        }
    
    def run_evaluation(self, image: Union[np.ndarray, Image.Image], 
                      gt_mask: np.ndarray, gt_labels: List) -> Dict:
        """
        Run pipeline in EVALUATION mode (benchmarking).
        
        Args:
            image: Input image
            gt_mask: Ground truth semantic mask (H, W, 3) RGB
            gt_labels: List of ground truth labels (OBB format)
            
        Returns:
            dict: {
                'detections': List of detections,
                'predicted_masks': List of predicted masks,
                'ground_truth_masks': List of GT masks per class,
                'timing': Timing information,
                'metrics': Per-detection metrics (computed externally)
            }
        """
        # Run inference
        inference_result = self.run_inference(image)
        
        # Extract GT masks per class for comparison
        # (This will be done by the evaluation wrapper)
        
        return {
            **inference_result,
            'ground_truth_mask': gt_mask,
            'ground_truth_labels': gt_labels
        }
    
    def _generate_sam_prompts(self, detections: List[Dict]) -> List[Dict]:
        """
        Generate SAM prompts based on YOLO detections and per-class config.
        
        Args:
            detections: List of detection dicts from YOLO
                       Each has: 'bbox' (OBB), 'class_id', 'confidence'
                       
        Returns:
            List of prompt dicts: {'type': 'box'/'point', 'coords': [...], 'class_id': int}
        """
        prompts = []
        
        for det in detections:
            class_id = det['class_id']
            bbox = det['bbox']  # OBB format: [x1,y1,x2,y2,x3,y3,x4,y4]
            
            # Get prompt type for this class
            prompt_type = get_prompt_type(class_id)
            
            if prompt_type == 'box':
                # Convert OBB → VBB (axis-aligned bounding box)
                vbb = self._obb_to_vbb(bbox)
                prompts.append({
                    'type': 'box',
                    'coords': vbb,
                    'class_id': class_id,
                    'confidence': det['confidence']
                })
                
            elif prompt_type == 'point':
                # Extract center point from OBB
                center = self._obb_to_center_point(bbox)
                prompts.append({
                    'type': 'point',
                    'coords': center,
                    'class_id': class_id,
                    'confidence': det['confidence']
                })
        
        return prompts
    
    def _run_sam_segmentation(self, image: np.ndarray, prompts: List[Dict]) -> List[np.ndarray]:
        """
        Run SAM segmentation with mixed prompt types.
        
        Args:
            image: Input image
            prompts: List of prompt dicts
            
        Returns:
            List of binary masks (np.ndarray)
        """
        masks = []
        
        # Group prompts by type for efficient batching
        box_prompts = [p for p in prompts if p['type'] == 'box']
        point_prompts = [p for p in prompts if p['type'] == 'point']
        
        # Process box prompts
        if box_prompts:
            box_coords = [p['coords'] for p in box_prompts]
            box_masks = self.sam.segment(image, box_coords, prompt_type='box')
            masks.extend(box_masks)
        
        # Process point prompts
        if point_prompts:
            point_coords = [p['coords'] for p in point_prompts]
            point_masks = self.sam.segment(image, point_coords, prompt_type='point')
            masks.extend(point_masks)
        
        return masks
    
    def _obb_to_vbb(self, obb: List[float]) -> List[float]:
        """
        Convert Oriented Bounding Box (8 coords) to Vertical Bounding Box (4 coords).
        
        Args:
            obb: [x1, y1, x2, y2, x3, y3, x4, y4]
            
        Returns:
            [x_min, y_min, x_max, y_max]
        """
        if len(obb) == 8:
            x_coords = [obb[i] for i in range(0, 8, 2)]
            y_coords = [obb[i] for i in range(1, 8, 2)]
            return [min(x_coords), min(y_coords), max(x_coords), max(y_coords)]
        elif len(obb) == 4:
            # Already VBB format
            return obb
        else:
            raise ValueError(f"Invalid bbox format: expected 4 or 8 coords, got {len(obb)}")
    
    def _obb_to_center_point(self, obb: List[float]) -> List[float]:
        """
        Extract center point from Oriented Bounding Box.
        
        Args:
            obb: [x1, y1, x2, y2, x3, y3, x4, y4]
            
        Returns:
            [center_x, center_y]
        """
        if len(obb) == 8:
            x_coords = [obb[i] for i in range(0, 8, 2)]
            y_coords = [obb[i] for i in range(1, 8, 2)]
            center_x = sum(x_coords) / 4
            center_y = sum(y_coords) / 4
            return [center_x, center_y]
        elif len(obb) == 4:
            # VBB format: center is midpoint
            x1, y1, x2, y2 = obb
            return [(x1 + x2) / 2, (y1 + y2) / 2]
        else:
            raise ValueError(f"Invalid bbox format: expected 4 or 8 coords, got {len(obb)}")
    
    def get_timing_stats(self) -> Dict:
        """
        Get accumulated timing statistics.
        
        Returns:
            dict: {
                'total_images': int,
                'total_detection_ms': float,
                'total_segmentation_ms': float,
                'total_inference_ms': float,
                'avg_detection_ms': float,
                'avg_segmentation_ms': float,
                'avg_total_ms': float
            }
        """
        n = max(self.num_images_processed, 1)  # Avoid division by zero
        
        return {
            'total_images': self.num_images_processed,
            'total_detection_ms': self.total_detection_time,
            'total_segmentation_ms': self.total_segmentation_time,
            'total_inference_ms': self.total_inference_time,
            'avg_detection_ms': self.total_detection_time / n,
            'avg_segmentation_ms': self.total_segmentation_time / n,
            'avg_total_ms': self.total_inference_time / n
        }


# TODO: Mask vectorization for GIS integration
# Future enhancement: Convert binary masks → vector polygons
# - Use cv2.findContours() or skimage.measure.find_contours()
# - Simplify polygons with Douglas-Peucker algorithm (cv2.approxPolyDP)
# - Export as GeoJSON or Shapefile format
# - Add coordinate system transformation (pixel → geographic)
# Example implementation:
#
# def vectorize_mask(mask: np.ndarray, simplify_tolerance=2.0) -> List[np.ndarray]:
#     """Convert binary mask to vector polygon(s)"""
#     import cv2
#     contours, _ = cv2.findContours(mask.astype(np.uint8), 
#                                    cv2.RETR_EXTERNAL, 
#                                    cv2.CHAIN_APPROX_SIMPLE)
#     simplified = [cv2.approxPolyDP(c, simplify_tolerance, True) for c in contours]
#     return simplified
