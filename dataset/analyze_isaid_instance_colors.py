u"""
One-time script to analyze iSAID instance masks and extract unique RGB colors per instance.
This script will generate a JSON dictionary mapping: image_id -> class_name -> [RGB colors]

After running once, this script can be deleted.
"""

import os
import json
import numpy as np
from PIL import Image
from pathlib import Path
from tqdm import tqdm

# iSAID class color mapping (semantic colors)
ISAID_CLASS_COLORS = {
    'ship': (0, 0, 63),
    'storage_tank': (0, 63, 63),
    'baseball_diamond': (0, 63, 0),
    'tennis_court': (0, 63, 127),
    'basketball_court': (0, 63, 191),
    'ground_track_field': (0, 63, 255),
    'bridge': (0, 127, 63),
    'large_vehicle': (0, 127, 127),
    'small_vehicle': (0, 0, 127),
    'helicopter': (0, 0, 191),
    'swimming_pool': (0, 0, 255),
    'roundabout': (0, 191, 127),
    'soccer_ball_field': (0, 127, 191),
    'plane': (0, 127, 255),
    'harbor': (0, 100, 155)
}

def analyze_instance_mask(instance_mask_path, class_colors):
    """
    Analyze a single instance mask and extract unique RGB values per class.
    
    Args:
        instance_mask_path: Path to instance mask PNG
        class_colors: Dictionary of class_name -> base_RGB
    
    Returns:
        Dictionary mapping class_name -> list of unique RGB tuples
    """
    # Load instance mask
    mask_img = Image.open(instance_mask_path)
    mask_rgb = np.array(mask_img)
    
    result = {}
    
    # For each class, find all unique RGB values that are "close" to base color
    for class_name, base_color in class_colors.items():
        # Find pixels where R and G match base color (B may vary for instances)
        # iSAID encodes instances by varying one channel slightly
        matching_pixels = (mask_rgb[:, :, 0] == base_color[0]) & \
                         (mask_rgb[:, :, 1] == base_color[1])
        
        if not matching_pixels.any():
            continue
        
        # Extract all unique RGB values for this class
        class_pixels = mask_rgb[matching_pixels]
        unique_colors = np.unique(class_pixels, axis=0)
        
        # Convert to list of tuples
        color_list = [tuple(color) for color in unique_colors]
        
        # Filter out background (0,0,0) and exact base colors if not actual instances
        color_list = [c for c in color_list if c != (0, 0, 0)]
        
        if color_list:
            result[class_name] = color_list
    
    return result


def main():
    """
    Main function to process all iSAID instance masks and generate JSON dictionary.
    """
    # Paths
    isaid_base = Path("dataset/iSAID")
    output_path = Path("dataset/AerialFuseCV_Refined/isaid_instance_colors.json")
    
    # Check if iSAID instance masks exist
    instance_masks_dirs = []
    for split in ['train', 'val']:
        split_dir = isaid_base / split / "instance_masks"
        if split_dir.exists():
            instance_masks_dirs.append(split_dir)
    
    if not instance_masks_dirs:
        print("❌ No instance mask directories found!")
        print(f"Expected: {isaid_base / 'train' / 'instance_masks'}")
        print(f"      or: {isaid_base / 'val' / 'instance_masks'}")
        return
    
    print(f"🔍 Found {len(instance_masks_dirs)} instance mask directories")
    
    # Collect all instance masks
    mask_files = []
    for mask_dir in instance_masks_dirs:
        mask_files.extend(list(mask_dir.glob("*_instance_*.png")))
    
    print(f"📁 Found {len(mask_files)} instance mask files")
    
    if not mask_files:
        print("⚠️  No instance mask files found!")
        return
    
    # Process all masks
    instance_color_dict = {}
    
    print("\n🎨 Analyzing instance colors...")
    for mask_path in tqdm(mask_files, desc="Processing masks"):
        # Extract image ID from filename
        # Format: P0654_instance_id_RGB.png or P0654_instance_color_RGB.png
        image_id = mask_path.stem.split('_')[0]  # e.g., "P0654"
        
        # Analyze this mask
        try:
            colors = analyze_instance_mask(mask_path, ISAID_CLASS_COLORS)
            
            if colors:
                instance_color_dict[image_id] = colors
        except Exception as e:
            print(f"\n⚠️  Error processing {mask_path.name}: {e}")
            continue
    
    # Save to JSON
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(instance_color_dict, f, indent=2)
    
    print(f"\n✅ Successfully processed {len(instance_color_dict)} images")
    print(f"💾 Saved to: {output_path}")
    
    # Print statistics
    print("\n📊 Statistics:")
    class_counts = {}
    total_instances = 0
    
    for image_id, classes in instance_color_dict.items():
        for class_name, colors in classes.items():
            class_counts[class_name] = class_counts.get(class_name, 0) + len(colors)
            total_instances += len(colors)
    
    print(f"   Total images: {len(instance_color_dict)}")
    print(f"   Total instances: {total_instances}")
    print(f"\n   Instances per class:")
    for class_name in sorted(class_counts.keys()):
        print(f"      {class_name}: {class_counts[class_name]}")
    
    # Show example
    if instance_color_dict:
        example_image = list(instance_color_dict.keys())[0]
        print(f"\n📝 Example (Image {example_image}):")
        for class_name, colors in instance_color_dict[example_image].items():
            print(f"   {class_name}: {len(colors)} instances")
            print(f"      Colors: {colors[:3]}{'...' if len(colors) > 3 else ''}")


if __name__ == "__main__":
    main()
