"""
Complete Refinement Pipeline - Runs All Steps Automatically

This script:
1. Runs dataset refinement (2-4 hours)
2. Merges refined splits
3. Runs SAM test evaluation (10 images)
4. Generates final report

Run with: python dataset/run_full_refinement_pipeline.py
"""

import subprocess
import sys
import time
from pathlib import Path


def run_command(description, command):
    """Run a command and report status."""
    print("\n" + "="*80)
    print(f"STEP: {description}")
    print("="*80)
    print(f"Command: {command}")
    print()
    
    start_time = time.time()
    result = subprocess.run(command, shell=True, capture_output=False, text=True)
    elapsed = time.time() - start_time
    
    if result.returncode != 0:
        print(f"\n❌ FAILED: {description}")
        print(f"Exit code: {result.returncode}")
        sys.exit(1)
    
    print(f"\n✅ COMPLETE: {description}")
    print(f"Time elapsed: {elapsed/60:.1f} minutes")
    return elapsed


def main():
    """Run the complete refinement pipeline."""
    
    print("\n" + "="*80)
    print("AERIALFUSECV REFINEMENT PIPELINE")
    print("="*80)
    print("This will take approximately 2-4 hours to complete.")
    print("="*80)
    
    total_start = time.time()
    
    # Step 1: Refinement
    step1_time = run_command(
        "Dataset Refinement (Instance-Level Matching)",
        "python dataset/refine_aerialfusecv.py"
    )
    
    # Step 2: Merge
    step2_time = run_command(
        "Merge Refined Splits (Train + Val)",
        "python dataset/merge_aerialfusecv_refined.py"
    )
    
    # Step 3: Visualize refined dataset (sample from val to verify fix)
    step3_time = run_command(
        "Visualize Refined Val Split (Verify Coordinates)",
        "python dataset/visualize_aerialfusecv_refined.py --split val --max-images 5 --output results/aerialfusecv_refined_verification"
    )
    
    # Step 4: SAM Test
    step4_time = run_command(
        "SAM Evaluation",
        "python src/experiments/evaluate_sam.py"
    )
    
    # Summary
    total_time = time.time() - total_start
    
    print("\n" + "="*80)
    print("✅ PIPELINE COMPLETE!")
    print("="*80)
    print(f"Step 1 - Refinement:     {step1_time/60:.1f} minutes")
    print(f"Step 2 - Merge:          {step2_time/60:.1f} minutes")
    print(f"Step 3 - Visualization:  {step3_time/60:.1f} minutes")
    print(f"Step 4 - SAM Test:       {step4_time/60:.1f} minutes")
    print(f"Total Time:              {total_time/60:.1f} minutes ({total_time/3600:.2f} hours)")
    print("="*80)
    print("\n📊 Next Steps:")
    print("1. Review: results/aerialfusecv_refined_verification/")
    print("2. Check SAM test results: results/sam_evaluation_refined/")
    print("3. If coordinates look correct, run full SAM benchmark:")
    print("   python src/experiments/evaluate_sam.py")
    print("="*80)


if __name__ == "__main__":
    main()
