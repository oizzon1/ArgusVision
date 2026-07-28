"""
AerialFuseCV Excluded Images Visualization Script

Finds images that exist in AerialFuseCV but NOT in AerialFuseCV_Refined (10 images).
For each excluded image, creates an overlay showing:
- RED bboxes (DOTA OBB annotations)
- Segmentation masks in their original iSAID color codes

Output: 10 overlay images in results/AerialFuseCV_excluded_images/
"""

import os
import cv2
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
import matplotlib.patches as mpatches


class ExcludedImagesVisualizer:
    """Visualizes excluded images from AerialFuseCV refinement process."""
    
    def __init__(self, 
                 original_dir="dataset/AerialFuseCV",
                 refined_dir="dataset/AerialFuseCV_Refined", 
                 output_dir="results/AerialFuseCV_excluded_images"):
        self.original_dir = Path(original_dir)
        self.refined_dir = Path(refined_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # DOTA class names
        self.class_names = [
            "plane", "ship", "storage-tank", "baseball-diamond", "tennis-court",
            "basketball-court", "ground-track-field", "harbor", "bridge", "large-vehicle",
            "small-vehicle", "helicopter", "roundabout", "soccer-ball-field", "swimming-pool"
        ]
        
        self.class_name_to_id = {name: i for i, name in enumerate(self.class_names)}
        
        # iSAID color codes for segmentation masks
        # FIXED 2026-01-14: Corrected storage-tank and bridge colors
        self.class_colors = {
            0: (0, 127, 255),    # plane
            1: (0, 0, 63),       # ship
            2: (0, 63, 63),      # storage-tank (FIXED: was 0,63,6)
            3: (0, 63, 0),       # baseball-diamond
            4: (0, 63, 127),     # tennis-court
            5: (0, 63, 191),     # basketball-court
            6: (0, 63, 255),     # ground-track-field
            7: (0, 100, 155),    # harbor
            8: (0, 127, 63),     # bridge (FIXED: was 0,127,163)
            9: (0, 127, 127),    # large-vehicle
            10: (0, 0, 127),     # small-vehicle
            11: (0, 0, 191),     # helicopter
            12: (0, 191, 127),   # roundabout
            13: (0, 127, 191),   # soccer-ball-field
            14: (0, 0, 255)      # swimming-pool
        }
    
    def find_excluded_images(self, split='train'):
        """Find images in original AerialFuseCV that are NOT in AerialFuseCV_Refined."""
        print(f"\n[FINDING] Excluded images in {split} split...")
        
        orig_images = self.original_dir / split / 'images'
        ref_images = self.refined_dir / split / 'images'
        
        # Get image names (without extension)
        orig_set = {p.stem for p in orig_images.glob('*.png')}
        ref_set = {p.stem for p in ref_images.glob('*.png')}
        
        # Find excluded (in original but NOT in refined)
        excluded = sorted(orig_set - ref_set)
        
        print(f"  Original AerialFuseCV: {len(orig_set)} images")
        print(f"  Refined AerialFuseCV:  {len(ref_set)} images")
        print(f"  Excluded images:       {len(excluded)} images")
        
        return excluded
    
    def load_bboxes_dota(self, label_path):
        """Load bboxes from DOTA format."""
        bboxes = []
        if not os.path.exists(label_path):
            return bboxes
        
        with open(label_path, 'r') as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) < 10 or parts[0] in ['imagesource:', 'gsd:']:
                    continue
                try:
                    # OBB: x1 y1 x2 y2 x3 y3 x4 y4 class difficult
                    x_coords = [float(parts[i]) for i in range(0, 8, 2)]
                    y_coords = [float(parts[i]) for i in range(1, 8, 2)]
                    class_name = parts[8]
                    
                    if class_name not in self.class_name_to_id:
                        continue
                    
                    class_id = self.class_name_to_id[class_name]
                    bboxes.append({
                        'class_id': class_id,
                        'class_name': class_name,
                        'obb_coords': list(zip(x_coords, y_coords))
                    })
                except (ValueError, IndexError):
                    continue
        return bboxes
    
    def create_overlay(self, img_name, split='train'):
        """Create overlay visualization for a single excluded image."""
        # Paths
        img_path = self.original_dir / split / 'images' / f"{img_name}.png"
        label_path = self.original_dir / split / 'labels' / f"{img_name}.txt"
        mask_path = self.original_dir / split / 'semantic_masks' / f"{img_name}_instance_color_RGB.png"
        
        # Load image
        image = cv2.imread(str(img_path))
        if image is None:
            print(f"    [ERROR] Could not load image: {img_path}")
            return False
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # Load segmentation mask
        mask_rgb = None
        if mask_path.exists():
            mask_bgr = cv2.imread(str(mask_path))
            if mask_bgr is not None:
                mask_rgb = cv2.cvtColor(mask_bgr, cv2.COLOR_BGR2RGB)
        
        # Load bboxes
        bboxes = self.load_bboxes_dota(label_path)
        
        # Create figure
        fig, ax = plt.subplots(figsize=(12, 12))
        
        # Start with original image
        display_img = image.copy().astype(float)
        
        # Count mask instances (connected components per class)
        mask_count = 0
        if mask_rgb is not None:
            # Find all unique non-black colors (classes)
            unique_colors = np.unique(mask_rgb.reshape(-1, 3), axis=0)
            unique_colors = [c for c in unique_colors if not np.all(c == 0)]
            
            # For each class color, count separate instances
            for color in unique_colors:
                # Extract pixels of this class
                class_mask = np.all(mask_rgb == color, axis=-1).astype(np.uint8)
                # Count connected components (separate instances)
                num_instances, _ = cv2.connectedComponents(class_mask)
                mask_count += (num_instances - 1)  # Subtract background label
        
        # Overlay segmentation mask (semi-transparent, BRIGHT GREEN)
        if mask_rgb is not None:
            # Create mask where there are annotations (non-black pixels)
            has_annotation = np.any(mask_rgb > 0, axis=-1)
            
            # Create bright green overlay (RGB: 0, 255, 0)
            green_mask = np.zeros_like(mask_rgb)
            green_mask[has_annotation] = [0, 255, 0]  # Bright green
            
            # Blend mask with image (40% opacity for green mask)
            display_img[has_annotation] = (
                display_img[has_annotation] * 0.6 + 
                green_mask[has_annotation].astype(float) * 0.4
            )
        
        display_img = np.clip(display_img, 0, 255).astype(np.uint8)
        ax.imshow(display_img)
        
        # Draw RED bboxes
        for bbox in bboxes:
            obb_coords = bbox['obb_coords']
            polygon = Polygon(obb_coords, fill=False, edgecolor='red', linewidth=2)
            ax.add_patch(polygon)
        
        # Title with counts
        num_bboxes = len(bboxes)
        
        title = f"Excluded Image: {img_name}\n"
        title += f"BBoxes: {num_bboxes} | Masks: {mask_count if mask_count > 0 else 'No'}"
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.axis('off')
        
        # Legend
        legend_elements = [
            mpatches.Patch(facecolor='none', edgecolor='red', linewidth=2, label='DOTA Detection BBox (OBB)')
        ]
        if mask_count > 0:
            legend_elements.append(mpatches.Patch(facecolor='lime', alpha=0.4, label='iSAID Segmentation Mask'))
        ax.legend(handles=legend_elements, loc='upper right', fontsize=10)
        
        # Save
        output_path = self.output_dir / f"{img_name}_excluded.png"
        plt.savefig(output_path, dpi=100, bbox_inches='tight', pad_inches=0.1)
        plt.close()
        
        return True
    
    def run(self, split='train'):
        """Run visualization for all excluded images."""
        print("\n" + "="*70)
        print("  AERIALFUSECV EXCLUDED IMAGES VISUALIZATION")
        print("="*70)
        print(f"Original: {self.original_dir}")
        print(f"Refined:  {self.refined_dir}")
        print(f"Output:   {self.output_dir}")
        print("="*70)
        
        # Find excluded images
        excluded = self.find_excluded_images(split)
        
        if len(excluded) == 0:
            print("\n[WARNING] No excluded images found!")
            return
        
        # Process each excluded image
        print(f"\n[PROCESSING] Creating overlays for {len(excluded)} excluded images...")
        
        success_count = 0
        for i, img_name in enumerate(excluded):
            print(f"  [{i+1}/{len(excluded)}] {img_name}...", end=" ")
            if self.create_overlay(img_name, split):
                print("OK")
                success_count += 1
            else:
                print("FAILED")
        
        print("\n" + "="*70)
        print("  VISUALIZATION COMPLETE!")
        print("="*70)
        print(f"\nSuccessfully created: {success_count}/{len(excluded)} overlay images")
        print(f"Output directory: {self.output_dir}")


if __name__ == "__main__":
    visualizer = ExcludedImagesVisualizer()
    
    # Process both train and val splits
    print("\n" + "="*70)
    print("  PROCESSING TRAIN SPLIT")
    print("="*70)
    visualizer.run(split='train')
    
    print("\n\n" + "="*70)
    print("  PROCESSING VAL SPLIT")
    print("="*70)
    visualizer.run(split='val')
    
    print("\n\n" + "="*70)
    print("  ALL SPLITS COMPLETE!")
    print("="*70)
