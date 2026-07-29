"""
ArgusVisionInference: Inference mode wrapper for operational use.

This module provides a clean interface for production deployment.
Returns segmentation masks ready for downstream processing.
"""

import numpy as np
from typing import Dict, List, Union
from PIL import Image

from src.ArgusVision.ArgusVisionCore import ArgusVisionCore


class ArgusVisionInference:
    """
    Inference mode wrapper for ArgusVision pipeline.
    
    Purpose: Operational deployment (real-time or batch processing)
    Output: Segmentation masks + metadata
    
    TODO: Add mask vectorization for GIS integration
          - Convert binary masks → vector polygons
          - Use cv2.findContours() or skimage.measure.find_contours()
          - Export as GeoJSON or Shapefile for GIS systems
          - Simplify polygons (Douglas-Peucker algorithm)
    """
    
    def __init__(self, yolo_model, sam_model, class_prompt_config=None):
        """
        Initialize inference pipeline.
        
        Args:
            yolo_model: Initialized YOLO detector
            sam_model: Initialized SAM segmenter
            class_prompt_config: Optional custom prompt configuration
        """
        self.pipeline = ArgusVisionCore(yolo_model, sam_model, class_prompt_config)
        
    def predict(self, image: Union[np.ndarray, Image.Image]) -> Dict:
        """
        Run inference on a single image.
        
        Args:
            image: Input image (numpy array or PIL Image)
            
        Returns:
            dict: {
                'masks': List[np.ndarray] - Binary segmentation masks
                'classes': List[int] - Class IDs for each mask
                'confidences': List[float] - Detection confidences
                'bboxes': List[List[float]] - Bounding boxes (for reference)
                'timing': Dict - Inference timing breakdown
                'metadata': Dict - Additional information
            }
        """
        result = self.pipeline.run_inference(image)
        
        # Organize output for operational use
        return {
            'masks': result['masks'],
            'classes': result['classes'],
            'confidences': result['confidences'],
            'bboxes': [det['bbox'] for det in result['detections']],
            'timing': result['timing'],
            'metadata': {
                'num_detections': len(result['detections']),
                'prompt_types': self._get_prompt_types_used(result['classes'])
            }
        }
    
    def predict_batch(self, images: List[Union[np.ndarray, Image.Image]]) -> List[Dict]:
        """
        Run inference on batch of images.
        
        Args:
            images: List of input images
            
        Returns:
            List of prediction dicts (one per image)
        """
        results = []
        for image in images:
            result = self.predict(image)
            results.append(result)
        return results
    
    def get_timing_stats(self) -> Dict:
        """
        Get accumulated timing statistics across all processed images.
        
        Returns:
            dict: Timing breakdown and averages
        """
        return self.pipeline.get_timing_stats()
    
    def reset_timing(self):
        """Reset timing statistics"""
        self.pipeline.reset_timing()
    
    def _get_prompt_types_used(self, classes: List[int]) -> Dict:
        """Helper to summarize prompt types used"""
        from src.ArgusVision.config.class_prompt_config import get_prompt_type
        
        box_count = sum(1 for c in classes if get_prompt_type(c) == 'box')
        point_count = sum(1 for c in classes if get_prompt_type(c) == 'point')
        
        return {
            'box': box_count,
            'point': point_count,
            'total': len(classes)
        }


# TODO: Vectorization implementation
# 
# def vectorize_masks(masks: List[np.ndarray], 
#                     simplify_tolerance: float = 2.0) -> List[Dict]:
#     """
#     Convert binary masks to vector polygons for GIS integration.
#     
#     Args:
#         masks: List of binary masks (H, W) boolean arrays
#         simplify_tolerance: Tolerance for polygon simplification (pixels)
#         
#     Returns:
#         List of polygon dicts: {'exterior': [(x,y), ...], 'holes': [[(x,y), ...]]}
#     """
#     import cv2
#     
#     polygons = []
#     for mask in masks:
#         # Find contours
#         contours, hierarchy = cv2.findContours(
#             mask.astype(np.uint8),
#             cv2.RETR_CCOMP,  # Get external + holes
#             cv2.CHAIN_APPROX_SIMPLE
#         )
#         
#         if not contours:
#             continue
#             
#         # Simplify contours
#         simplified = []
#         for contour in contours:
#             approx = cv2.approxPolyDP(contour, simplify_tolerance, True)
#             simplified.append(approx.squeeze().tolist())
#         
#         # Separate exterior and holes using hierarchy
#         exterior = simplified[0] if simplified else []
#         holes = simplified[1:] if len(simplified) > 1 else []
#         
#         polygons.append({
#             'exterior': exterior,
#             'holes': holes,
#             'area': cv2.contourArea(contours[0]) if contours else 0
#         })
#     
#     return polygons
# 
# def export_to_geojson(polygons: List[Dict], 
#                       classes: List[int], 
#                       confidences: List[float],
#                       output_path: str):
#     """
#     Export vectorized masks to GeoJSON format.
#     
#     Args:
#         polygons: Output from vectorize_masks()
#         classes: Class IDs
#         confidences: Detection confidences
#         output_path: Path to save GeoJSON file
#     """
#     import json
#     from src.ArgusVision.config.class_prompt_config import CLASS_NAMES
#     
#     features = []
#     for poly, cls, conf in zip(polygons, classes, confidences):
#         feature = {
#             'type': 'Feature',
#             'geometry': {
#                 'type': 'Polygon',
#                 'coordinates': [poly['exterior']] + poly['holes']
#             },
#             'properties': {
#                 'class_id': int(cls),
#                 'class_name': CLASS_NAMES.get(cls, 'unknown'),
#                 'confidence': float(conf),
#                 'area_pixels': poly['area']
#             }
#         }
#         features.append(feature)
#     
#     geojson = {
#         'type': 'FeatureCollection',
#         'features': features
#     }
#     
#     with open(output_path, 'w') as f:
#         json.dump(geojson, f, indent=2)
