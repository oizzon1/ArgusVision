"""
Merge AerialFuseCV_Refined train and val splits into a single evaluation dataset.
This creates a unified dataset with perfect 1:1 bbox-mask correspondence for SAM evaluation.
"""

import shutil
from pathlib import Path
from tqdm import tqdm


def merge_refined_splits():
    """Merge train and val splits of AerialFuseCV_Refined."""
    
    source_dir = Path("dataset/AerialFuseCV_Refined")
    output_dir = Path("dataset/AerialFuseCV_Refined_Merged")
    
    # Create output directories
    output_images = output_dir / "images"
    output_labels = output_dir / "labels"
    output_masks = output_dir / "semantic_masks"
    
    for dir_path in [output_images, output_labels, output_masks]:
        dir_path.mkdir(parents=True, exist_ok=True)
    
    print("=" * 80)
    print("MERGING AERIALFUSECV_REFINED SPLITS")
    print("=" * 80)
    print(f"Source: {source_dir}")
    print(f"Output: {output_dir}")
    print("=" * 80)
    
    # Process both splits
    total_images = 0
    for split in ['train', 'val']:
        print(f"\nProcessing {split} split...")
        
        split_images = sorted((source_dir / split / "images").glob("*.png"))
        
        for img_path in tqdm(split_images, desc=f"Copying {split}"):
            img_name = img_path.stem
            
            # Copy image
            shutil.copy(
                img_path,
                output_images / img_path.name
            )
            
            # Copy label
            label_src = source_dir / split / "labels" / f"{img_name}.txt"
            if label_src.exists():
                shutil.copy(
                    label_src,
                    output_labels / f"{img_name}.txt"
                )
            
            # Copy mask
            mask_src = source_dir / split / "semantic_masks" / f"{img_name}_instance_color_RGB.png"
            if mask_src.exists():
                shutil.copy(
                    mask_src,
                    output_masks / f"{img_name}_instance_color_RGB.png"
                )
            
            total_images += 1
    
    print(f"\n{'=' * 80}")
    print(f"✅ MERGE COMPLETE!")
    print(f"{'=' * 80}")
    print(f"Total images: {total_images}")
    print(f"Output directory: {output_dir}")
    print(f"{'=' * 80}")


if __name__ == "__main__":
    merge_refined_splits()
