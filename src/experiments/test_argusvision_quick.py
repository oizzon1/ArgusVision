"""
Quick Integration Test for ArgusVision Pipeline

This script tests the full YOLO→SAM pipeline on a single image to verify:
1. Models load correctly
2. Pipeline executes without errors
3. Output format is correct
4. Timing metrics are recorded
5. Basic performance sanity checks

Usage:
    python src/experiments/test_argusvision_quick.py
"""

import sys
from pathlib import Path

# Add project root to path (go up 2 levels: experiments -> src -> root)
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.ArgusVision import ArgusVisionEvaluation
from src.ArgusVision.branding import display_logo
from src.ArgusVision.config.class_prompt_config import CLASS_PROMPT_CONFIG
from src.models.yolo_detector import YOLODetector
from src.models.sam_segmenter import SAMSegmenter


def test_single_image():
    """Run ArgusVision pipeline on single image and validate output"""
    
    # Display ArgusVision logo
    display_logo()
    
    print("="*60)
    print("QUICK INTEGRATION TEST")
    print("="*60)
    
    # Display prompt configuration
    print(f"✅ CLASS_PROMPT_CONFIG loaded: {len(CLASS_PROMPT_CONFIG)} classes configured")
    print(f"   - Box prompts: {sum(1 for v in CLASS_PROMPT_CONFIG.values() if v == 'box')}")
    print(f"   - Point prompts: {sum(1 for v in CLASS_PROMPT_CONFIG.values() if v == 'point')}")
    
    # Configuration
    yolo_model_name = 'yolo11x-obb'
    yolo_weights = 'yolo11x-obb.pt'
    sam_path = 'model_checkpoints/SAM/sam_vit_l_0b3195.pth'
    dataset_path = 'dataset/AerialFuseCV_Refined_Merged'
    
    try:
        # 1. Load YOLO model
        print("\n[1/5] Loading Detection Model (YOLO)...")
        print(f"      Model: {yolo_model_name}")
        print(f"      Weights: {yolo_weights}")
        yolo = YOLODetector(
            model_name=yolo_model_name,
            weights_path=yolo_weights,
            conf_threshold=0.25,
            mode='obb'
        )
        print("      ✅ Detector loaded successfully")
        
    except Exception as e:
        print(f"      ❌ Failed to load detector: {e}")
        print("\n💡 Troubleshooting:")
        print(f"   - Verify weights exist: model_checkpoints/YOLO/OBB/{yolo_weights}")
        print("   - Model checkpoints should be in model_checkpoints/YOLO/OBB/")
        return False
    
    try:
        # 2. Load SAM model
        print("\n[2/5] Loading Segmentation Model (SAM)...")
        print(f"      Model: SAM-ViT-L")
        print(f"      Checkpoint: {sam_path}")
        sam = SAMSegmenter(
            sam_type='vit_l',
            checkpoint_path=sam_path,
            device='cuda'  # Change to 'cpu' if no GPU
        )
        print("      ✅ Segmenter loaded successfully")
        
    except Exception as e:
        print(f"      ❌ Failed to load segmenter: {e}")
        print("\n💡 Troubleshooting:")
        print(f"   - Verify checkpoint exists: {sam_path}")
        print("   - SAM checkpoints: sam_vit_h_*.pth, sam_vit_l_*.pth, sam_vit_b_*.pth")
        print("   - If no GPU, change device='cuda' to device='cpu' in this script")
        return False
    
    try:
        # 3. Initialize evaluation pipeline
        print("\n[3/5] Initializing ArgusVision pipeline...")
        print(f"      Dataset: {dataset_path}")
        evaluator = ArgusVisionEvaluation(
            yolo_model=yolo,
            sam_model=sam,
            dataset_path=dataset_path,
            output_dir='results/test_quick'
        )
        print("      ✅ Pipeline initialized")
        
    except Exception as e:
        print(f"      ❌ Failed to initialize pipeline: {e}")
        print("\n💡 Troubleshooting:")
        print(f"   - Verify dataset exists: {dataset_path}")
        print("   - Check dataset structure: images/, labels/, semantic_masks/")
        return False
    
    try:
        # 4. Run evaluation on 1 image
        print("\n[4/5] Running evaluation on 1 image...")
        results = evaluator.evaluate(max_images=1, save_visualizations=False)
        print("      ✅ Evaluation complete")
        
    except Exception as e:
        print(f"      ❌ Evaluation failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 5. Validate results
    print("\n[5/5] Validating results...")
    
    checks_passed = []
    checks_failed = []
    
    # Check 1: IoU in valid range
    iou = results['overall']['mean_iou']
    if 0 <= iou <= 1:
        checks_passed.append(f"IoU in valid range: {iou:.4f}")
    else:
        checks_failed.append(f"IoU out of range [0, 1]: {iou:.4f}")
    
    # Check 2: DICE in valid range
    dice = results['overall']['mean_dice']
    if 0 <= dice <= 1:
        checks_passed.append(f"DICE in valid range: {dice:.4f}")
    else:
        checks_failed.append(f"DICE out of range [0, 1]: {dice:.4f}")
    
    # Check 3: Timing recorded
    total_time = results['timing']['avg_total_ms']
    if total_time > 0:
        checks_passed.append(f"Timing recorded: {total_time:.2f} ms")
    else:
        checks_failed.append(f"Invalid timing: {total_time}")
    
    # Check 4: Detection time reasonable
    det_time = results['timing']['avg_detection_ms']
    if 10 < det_time < 5000:  # Between 10ms and 5 seconds
        checks_passed.append(f"Detection time reasonable: {det_time:.2f} ms")
    else:
        checks_failed.append(f"Detection time suspicious: {det_time:.2f} ms")
    
    # Check 5: Segmentation time reasonable
    seg_time = results['timing']['avg_segmentation_ms']
    if 100 < seg_time < 60000:  # Between 100ms and 60 seconds
        checks_passed.append(f"Segmentation time reasonable: {seg_time:.2f} ms")
    else:
        checks_failed.append(f"Segmentation time suspicious: {seg_time:.2f} ms")
    
    # Check 6: Has per-class results
    if results['per_class']:
        num_classes = len(results['per_class'])
        checks_passed.append(f"Per-class results found: {num_classes} classes")
    else:
        checks_failed.append("No per-class results")
    
    # Print validation results
    print("\n      Validation checks:")
    for check in checks_passed:
        print(f"      ✅ {check}")
    for check in checks_failed:
        print(f"      ❌ {check}")
    
    # Summary
    print("\n" + "="*60)
    print("TEST RESULTS")
    print("="*60)
    
    print(f"\n📊 Performance Metrics:")
    print(f"   Overall IoU:      {iou:.4f}")
    print(f"   Overall DICE:     {dice:.4f}")
    
    print(f"\n⏱️  Timing Breakdown:")
    print(f"   Detection:        {det_time:.2f} ms")
    print(f"   Segmentation:     {seg_time:.2f} ms")
    print(f"   Total:            {total_time:.2f} ms")
    
    print(f"\n📁 Output saved to: results/test_quick/")
    
    if checks_failed:
        print(f"\n⚠️  {len(checks_failed)} validation check(s) failed")
        print("   Review issues above before full evaluation")
        success = False
    else:
        print(f"\n✅ ALL {len(checks_passed)} VALIDATION CHECKS PASSED")
        print("\n🎉 Pipeline is working correctly!")
        print("\n📍 Next steps:")
        print("   1. Test on 10 images:")
        print("      python src/experiments/evaluate_ArgusVision.py --max-images 10")
        print("   2. Run full evaluation:")
        print("      python src/experiments/evaluate_ArgusVision.py")
        success = True
    
    print("="*60 + "\n")
    
    return success


if __name__ == '__main__':
    try:
        success = test_single_image()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
