"""
Quick script to inspect iSAID instance mask encoding format.
"""

import numpy as np
from PIL import Image
from pathlib import Path
import cv2

# Check one example instance mask
mask_path = Path("dataset/iSAID/val/instance_masks/P0110_instance_id_RGB.png")

if not mask_path.exists():
    print(f"❌ File not found: {mask_path}")
    # Try alternate locations
    alt_paths = [
        Path("dataset/iSAID/val/P0110_instance_id_RGB.png"),
        Path("dataset/iSAID/train/instance_masks/P0654_instance_id_RGB.png"),
    ]
    for p in alt_paths:
        if p.exists():
            mask_path = p
            print(f"✅ Found: {mask_path}")
            break
    else:
        print("❌ No instance masks found!")
        exit(1)

print(f"\n📁 Inspecting: {mask_path.name}")
print("="*60)

# Load mask
mask_img = Image.open(mask_path)
mask_rgb = np.array(mask_img)

print(f"\n📐 Shape: {mask_rgb.shape}")
print(f"📊 Data type: {mask_rgb.dtype}")

# Get unique RGB values
pixels_2d = mask_rgb.reshape(-1, 3)
unique_colors = np.unique(pixels_2d, axis=0)

print(f"\n🎨 Total unique RGB values: {len(unique_colors)}")
print(f"\n📋 First 20 unique colors:")
for i, color in enumerate(unique_colors[:20]):
    count = np.sum(np.all(mask_rgb == color, axis=-1))
    print(f"   {i+1}. RGB{tuple(color)} - {count:,} pixels")

# Check if colors match iSAID semantic palette
print(f"\n🔍 Checking iSAID class colors:")
ISAID_COLORS = {
    'background': (0, 0, 0),
    'ship': (0, 0, 63),
    'storage_tank': (0, 63, 63),
    'large_vehicle': (0, 127, 127),
    'small_vehicle': (0, 0, 127),
    'plane': (0, 127, 255),
}

for class_name, base_color in ISAID_COLORS.items():
    # Check exact match
    exact_match = np.any(np.all(unique_colors == base_color, axis=1))
    
    # Check if any colors are "close" (within tolerance)
    close_matches = []
    for color in unique_colors:
        if abs(color[0] - base_color[0]) <= 5 and abs(color[1] - base_color[1]) <= 5:
            close_matches.append(tuple(color))
    
    if exact_match or close_matches:
        print(f"   ✅ {class_name}: {len(close_matches)} variations found")
        if len(close_matches) > 0 and len(close_matches) <= 5:
            print(f"      Colors: {close_matches}")

# Save a visual representation
print(f"\n💾 Saving visualization...")
vis_path = "dataset/instance_mask_inspection.png"
cv2.imwrite(vis_path, cv2.cvtColor(mask_rgb, cv2.COLOR_RGB2BGR))
print(f"   Saved to: {vis_path}")

print("\n" + "="*60)
print("✅ Inspection complete!")
