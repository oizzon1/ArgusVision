"""
Evaluation script for ArgusVision V2 pipeline (YOLO → SAM).

V2 Improvements:
- Two-level metrics: Detection (bbox-based) + Segmentation (mask-based)
- Shows ALL pipeline outputs (not filtered)
- Micro-averaged detection metrics

Usage:
    python src/experiments/evaluate_ArgusVision_v2.py --max-images 10  # Test on 10 images
    python src/experiments/evaluate_ArgusVision_v2.py --single-image P0003  # Test single image
    python src/experiments/evaluate_ArgusVision_v2.py                   # Full evaluation
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.ArgusVision.ArgusVisionEvaluationV2 import ArgusVisionEvaluatorV2
from src.ArgusVision.branding import display_logo
from src.models.yolo_detector import YOLODetector
from src.models.sam_segmenter import SAMSegmenter


def main():
    parser = argparse.ArgumentParser(description='Evaluate ArgusVision V2 Detection→Segmentation Pipeline')
    parser.add_argument('--dataset', type=str, 
                       default='dataset/AerialFuseCV_Refined/val',
                       help='Path to dataset (default: AerialFuseCV_Refined/val)')
    parser.add_argument('--yolo-model', type=str,
                       default='model_checkpoints/YOLO/OBB/yolo11x-obb.pt',
                       help='Path to YOLO model checkpoint')
    parser.add_argument('--sam-model', type=str,
                       default='model_checkpoints/SAM/sam_vit_b_01ec64.pth',
                       help='Path to SAM model checkpoint (default: ViT-B)')
    parser.add_argument('--sam-type', type=str, default='vit_b',
                       choices=['vit_h', 'vit_l', 'vit_b'],
                       help='SAM model type (default: vit_b for speed/quality tradeoff)')
    parser.add_argument('--max-images', type=int, default=None,
                       help='Limit number of images to process (for testing)')
    parser.add_argument('--single-image', type=str, default=None,
                       help='Test on single image (e.g., P0003)')
    parser.add_argument('--output-dir', type=str,
                       default='results/ArgusVision_v2_evaluation',
                       help='Output directory for results (separate from V1)')
    parser.add_argument('--device', type=str, default='cuda',
                       choices=['cuda', 'cpu'],
                       help='Device to use for inference')
    
    args = parser.parse_args()
    
    # Display ArgusVision logo
    display_logo()
    
    print("="*60)
    print("EVALUATION MODE - V2 (Two-Level Metrics)".center(60))
    print("="*60)
    
    # Configuration
    print(f"\n⚙️⚙️  Configuration:")
    print(f"    Dataset:          {args.dataset}")
    yolo_model_name = Path(args.yolo_model).stem.upper()
    print(f"    Detector Model:   {yolo_model_name} (Weights: {args.yolo_model})")
    sam_type_upper = args.sam_type.upper().replace('_', '-')
    print(f"    Segmenter Model:  SAM-{sam_type_upper} (Weights: {args.sam_model})")
    if args.single_image:
        print(f"    Mode:             Single Image Test ({args.single_image})")
    else:
        print(f"    Max Images:       {args.max_images or 'All'}")
    device_emoji = "🚀" if args.device == "cuda" else "💻"
    print(f"    Device:           {args.device.upper()} {device_emoji}")
    print(f"    Output Dir:       {args.output_dir}")
    print(f"    Metrics:          Detection (bbox) + Segmentation (mask)")
    
    # Initialize models
    print(f"\n⚙️⚙️  Loading models...")
    
    try:
        # Load detector (YOLO)
        yolo_model_stem = Path(args.yolo_model).stem
        yolo_weights = Path(args.yolo_model).name
        yolo = YOLODetector(
            model_name=yolo_model_stem,
            weights_path=yolo_weights,
            conf_threshold=0.25,
            mode='obb'
        )
        print(f"✅ Detector loaded")
        
        # Load segmenter (SAM)
        sam = SAMSegmenter(
            sam_type=args.sam_type,
            checkpoint_path=args.sam_model,
            device=args.device
        )
        print(f"✅ Segmenter loaded")
        
    except Exception as e:
        print(f"❌ Error loading models: {e}")
        print("\nPlease ensure:")
        print("  1. Model checkpoints exist at specified paths")
        print("  2. CUDA is available if using --device cuda")
        sys.exit(1)
    
    # Initialize evaluation pipeline
    print(f"\n⚙️⚙️  Initializing ArgusVision V2 evaluation pipeline...")
    try:
        evaluator = ArgusVisionEvaluatorV2(
            yolo_model=yolo,
            sam_model=sam,
            dataset_path=args.dataset,
            output_dir=args.output_dir
        )
    except Exception as e:
        print(f"❌ Error initializing evaluator: {e}")
        print(f"\nPlease ensure dataset exists at: {args.dataset}")
        print("Expected structure:")
        print("  dataset/AerialFuseCV_Refined/val/")
        print("    ├── images/")
        print("    ├── labels/")
        print("    └── semantic_masks/")
        sys.exit(1)
    
    # Run evaluation
    print(f"\n⚙️⚙️  Starting V2 evaluation...\n")
    try:
        results = evaluator.evaluate(
            max_images=args.max_images,
            save_visualizations=True,
            single_image=args.single_image
        )
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Evaluation interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error during evaluation: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
