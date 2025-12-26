"""
Evaluation script for ArgusVision pipeline (YOLO → SAM).

This script evaluates the full ArgusVision pipeline on AerialFuseCV_Refined_Merged dataset.
Easily configurable for different datasets, models, and settings.

Usage:
    python src/experiments/evaluate_ArgusVision.py --max-images 10  # Test on 10 images
    python src/experiments/evaluate_ArgusVision.py                   # Full evaluation
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.ArgusVision import ArgusVisionEvaluation
from src.ArgusVision.branding import display_logo
from src.models.yolo_detector import YOLODetector
from src.models.sam_segmenter import SAMSegmenter


def main():
    parser = argparse.ArgumentParser(description='Evaluate ArgusVision Detection→Segmentation Pipeline')
    parser.add_argument('--dataset', type=str, 
                       default='dataset/AerialFuseCV_Refined/val',
                       help='Path to dataset (default: AerialFuseCV_Refined/val)')
    parser.add_argument('--yolo-model', type=str,
                       default='model_checkpoints/YOLO/OBB/yolo11x-obb.pt',
                       help='Path to YOLO model checkpoint')
    parser.add_argument('--sam-model', type=str,
                       default='model_checkpoints/SAM/sam_vit_l_0b3195.pth',
                       help='Path to SAM model checkpoint')
    parser.add_argument('--max-images', type=int, default=None,
                       help='Limit number of images to process (for testing)')
    parser.add_argument('--output-dir', type=str,
                       default='results/ArgusVision_evaluation',
                       help='Output directory for results')
    parser.add_argument('--device', type=str, default='cuda',
                       choices=['cuda', 'cpu'],
                       help='Device to use for inference')
    
    args = parser.parse_args()
    
    # Display ArgusVision logo
    display_logo()
    
    print("="*60)
    print("EVALUATION MODE".center(60))
    print("="*60)
    
    # Configuration
    print(f"\n⚙️⚙️  Configuration:")
    print(f"    Dataset:          {args.dataset}")
    yolo_model_name = Path(args.yolo_model).stem.upper()
    print(f"    Detector Model:   {yolo_model_name} (Weights: {args.yolo_model})")
    print(f"    Segmenter Model:  SAM (Weights: {args.sam_model})")
    print(f"    Max Images:       {args.max_images or 'All'}")
    device_emoji = "🚀" if args.device == "cuda" else "💻"
    print(f"    Device:           {args.device.upper()} {device_emoji}")
    print(f"    Output Dir:       {args.output_dir}")
    
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
            sam_type='vit_l',  # Can be changed to 'vit_h' or 'vit_b'
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
    print(f"\n⚙️⚙️  Initializing ArgusVision evaluation pipeline...")
    try:
        evaluator = ArgusVisionEvaluation(
            yolo_model=yolo,
            sam_model=sam,
            dataset_path=args.dataset,
            output_dir=args.output_dir
        )
    except Exception as e:
        print(f"❌ Error initializing evaluator: {e}")
        print(f"\nPlease ensure dataset exists at: {args.dataset}")
        print("Expected structure:")
        print("  dataset/AerialFuseCV_Refined_Merged/")
        print("    ├── images/")
        print("    ├── labels/")
        print("    └── semantic_masks/")
        sys.exit(1)
    
    # Run evaluation
    print(f"\n⚙️⚙️  Starting evaluation...\n")
    try:
        results = evaluator.evaluate(
            max_images=args.max_images,
            save_visualizations=True
        )
        
        print("\n✅ Evaluation complete!")
        print(f"   Results saved to: {args.output_dir}")
        
        # Quick summary
        print(f"\n📊 Quick Results:")
        print(f"   Overall IoU:  {results['overall']['seg_iou']*100:.2f}%")
        print(f"   Overall DICE: {results['overall']['seg_dice']*100:.2f}%")
        print(f"   Avg Total Time: {results['timing']['avg_total_ms']:.2f} ms/image")
        
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
