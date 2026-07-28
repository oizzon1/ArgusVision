"""
Unified YOLO Evaluation Script - Runs Both OBB and VBB Experiments

This script orchestrates the evaluation of all YOLO models across both
OBB (Oriented Bounding Boxes) and VBB (Vertical Bounding Boxes) formats.

Usage:
    python src/experiments/evaluate_yolo_all.py
    
Features:
- Runs OBB evaluation (10 models on DOTA dataset)
- Runs VBB evaluation (24 models with COCO-DOTA mapping)
- Provides timing estimates and progress tracking
- Generates comprehensive results in separate directories

Output:
- results/yolo_evaluation/OBB/  (OBB results)
- results/yolo_evaluation/VBB/  (VBB results)
"""

import sys
import time
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def print_banner(text: str, char: str = "="):
    """Print a formatted banner"""
    width = 80
    print(f"\n{char * width}")
    print(f"{text:^{width}}")
    print(f"{char * width}\n")


def print_section(text: str):
    """Print a section header"""
    print(f"\n{'─' * 80}")
    print(f"  {text}")
    print(f"{'─' * 80}\n")


def run_obb_evaluation():
    """Run OBB evaluation"""
    print_section("PHASE 1: OBB Evaluation (10 models)")
    
    print("📦 Loading OBB evaluation module...")
    try:
        from src.experiments.evaluate_yolo_obb import run_evaluation
        
        DATASET_DIR = "dataset/DOTA_v1_YOLO_oriented_bboxes_dataset"
        RESULTS_DIR = "results/yolo_evaluation/OBB"
        
        print(f"📁 Dataset: {DATASET_DIR}")
        print(f"📁 Results: {RESULTS_DIR}")
        print(f"🔢 Models: 10 (YOLOv8/v11 × n/s/m/l/x)")
        print(f"⏱️  Estimated time: 6-8 hours\n")
        
        start_time = time.time()
        
        # Run evaluation with DataLoader enabled
        run_evaluation(DATASET_DIR, RESULTS_DIR, use_dataloader=True)
        
        elapsed = time.time() - start_time
        elapsed_str = str(timedelta(seconds=int(elapsed)))
        
        print(f"\n✅ OBB evaluation complete!")
        print(f"⏱️  Time taken: {elapsed_str}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error during OBB evaluation: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_vbb_evaluation():
    """Run VBB evaluation"""
    print_section("PHASE 2: VBB Evaluation (24 models)")
    
    print("📦 Loading VBB evaluation module...")
    try:
        from src.experiments.evaluate_yolo_vbb import run_evaluation
        
        DATASET_DIR = "dataset/DOTA_v1_YOLO_vertical_bboxes_dataset"
        RESULTS_DIR = "results/yolo_evaluation/VBB"
        
        print(f"📁 Dataset: {DATASET_DIR}")
        print(f"📁 Results: {RESULTS_DIR}")
        print(f"🔢 Models: 24 (YOLOv8/9/10/11/12 variants)")
        print(f"⏱️  Estimated time: 6-8 hours")
        print(f"⚠️  Note: VBB shows catastrophic domain transfer failure (expected)\n")
        
        start_time = time.time()
        
        # Run evaluation with DataLoader enabled
        run_evaluation(DATASET_DIR, RESULTS_DIR, use_dataloader=True)
        
        elapsed = time.time() - start_time
        elapsed_str = str(timedelta(seconds=int(elapsed)))
        
        print(f"\n✅ VBB evaluation complete!")
        print(f"⏱️  Time taken: {elapsed_str}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error during VBB evaluation: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main execution function"""
    print_banner("🎯 UNIFIED YOLO EVALUATION")
    
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total models to evaluate: 34 (10 OBB + 24 VBB)")
    print(f"Estimated total time: 12-16 hours")
    print(f"\n💡 Tip: This script can run overnight or in background")
    print(f"💡 Each phase has restore points - safe to interrupt\n")
    
    overall_start = time.time()
    results = {
        'obb': False,
        'vbb': False
    }
    
    # Phase 1: OBB Evaluation
    print_banner("PHASE 1/2: OBB Evaluation", char="═")
    results['obb'] = run_obb_evaluation()
    
    if not results['obb']:
        print("\n⚠️  OBB evaluation failed. Continuing to VBB...")
    
    # Phase 2: VBB Evaluation
    print_banner("PHASE 2/2: VBB Evaluation", char="═")
    results['vbb'] = run_vbb_evaluation()
    
    # Final summary
    overall_elapsed = time.time() - overall_start
    overall_elapsed_str = str(timedelta(seconds=int(overall_elapsed)))
    
    print_banner("🏁 EVALUATION COMPLETE", char="═")
    
    print(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total time: {overall_elapsed_str}\n")
    
    print("Results Summary:")
    print(f"  OBB Evaluation: {'✅ SUCCESS' if results['obb'] else '❌ FAILED'}")
    print(f"  VBB Evaluation: {'✅ SUCCESS' if results['vbb'] else '❌ FAILED'}")
    
    if results['obb']:
        print(f"\n📊 OBB Results: results/yolo_evaluation/OBB/")
    if results['vbb']:
        print(f"📊 VBB Results: results/yolo_evaluation/VBB/")
    
    # Exit code
    if results['obb'] and results['vbb']:
        print("\n✅ All evaluations completed successfully!")
        sys.exit(0)
    elif results['obb'] or results['vbb']:
        print("\n⚠️  Partial success - some evaluations failed")
        sys.exit(1)
    else:
        print("\n❌ All evaluations failed")
        sys.exit(2)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Evaluation interrupted by user (Ctrl+C)")
        print("💡 Individual phases have restore points - safe to resume")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
