"""
Test script for ArgusVision integration with real YOLO and SAM models.
This script tests the pipeline on a single validation image.
"""

import cv2
import numpy as np
from pathlib import Path
from src.models.yolo_detector import YOLODetector
from src.models.sam_segmenter import SAMSegmenter
from src.argus_vision.argus_vision_core import ArgusVision

def main():
    print("=" * 60)
    print("ArgusVision Integration Test")
    print("=" * 60)
    
    # Configuration
    yolo_model_path = "model_checkpoints/YOLO/OBB/yolo11x-obb.pt"
    sam_checkpoint = "model_checkpoints/SAM/sam_vit_b_01ec64.pth"
    sam_type = "vit_b"
    
    # Test image from validation set
    test_image_path = "dataset/DOTA_v1_YOLO_oriented_bboxes_dataset/images/val/P0003.png"
    
    # Verify files exist
    if not Path(yolo_model_path).exists():
        print(f"❌ YOLO model not found: {yolo_model_path}")
        return
    if not Path(sam_checkpoint).exists():
        print(f"❌ SAM checkpoint not found: {sam_checkpoint}")
        return
    if not Path(test_image_path).exists():
        print(f"❌ Test image not found: {test_image_path}")
        return
    
    print(f"✅ All files found")
    print()
    
    # Initialize models
    print("Initializing models...")
    print(f"  YOLO: {yolo_model_path}")
    print(f"  SAM: {sam_checkpoint} ({sam_type})")
    
    # DOTA class names for OBB
    dota_classes = [
        "plane", "ship", "storage-tank", "baseball-diamond", "tennis-court",
        "basketball-court", "ground-track-field", "harbor", "bridge", "large-vehicle",
        "small-vehicle", "helicopter", "roundabout", "soccer-ball-field", "swimming-pool"
    ]
    
    yolo_detector = YOLODetector(
        model_name="YOLOv11x-OBB",
        weights_path="yolo11x-obb.pt",
        conf_threshold=0.25,
        mode="obb",
        class_names=dota_classes
    )
    
    sam_segmenter = SAMSegmenter(
        sam_type=sam_type,
        checkpoint_path=sam_checkpoint
    )
    
    argus_vision = ArgusVision(yolo_detector, sam_segmenter)
    
    print("✅ Models initialized")
    print()
    
    # Load test image
    print(f"Loading test image: {test_image_path}")
    image = cv2.imread(test_image_path)
    if image is None:
        print(f"❌ Failed to load image")
        return
    
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    print(f"✅ Image loaded: {image_rgb.shape}")
    print()
    
    # Run pipeline
    print("Running ArgusVision pipeline...")
    results = argus_vision.run_pipeline(image_rgb)
    
    print("=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"YOLO Detections: {len(results['detections'])} objects")
    print(f"SAM Masks: {len(results['segmentation_masks'])} masks")
    print(f"Inference Time: {results['inference_time_ms']:.2f} ms")
    print()
    
    # Display detection details
    if results['detections']:
        print("Detection Details:")
        for i, det in enumerate(results['detections'][:5]):  # Show first 5
            class_name = dota_classes[det['class_id']] if det['class_id'] < len(dota_classes) else f"class_{det['class_id']}"
            print(f"  {i+1}. {class_name}: conf={det['confidence']:.3f}, bbox={det['bbox'][:4]}...")
        if len(results['detections']) > 5:
            print(f"  ... and {len(results['detections']) - 5} more")
    else:
        print("No detections found")
    
    print()
    
    # Display mask details
    if results['segmentation_masks']:
        print("Mask Details:")
        for i, mask in enumerate(results['segmentation_masks'][:5]):  # Show first 5
            if isinstance(mask, np.ndarray):
                print(f"  {i+1}. Shape: {mask.shape}, Type: {mask.dtype}, Pixels: {mask.sum()}")
        if len(results['segmentation_masks']) > 5:
            print(f"  ... and {len(results['segmentation_masks']) - 5} more")
    else:
        print("No masks generated")
    
    print()
    print("=" * 60)
    print("✅ Integration test complete!")
    print("=" * 60)

if __name__ == "__main__":
    main()
