"""
Flexible Annotation Visualization Script

Given a path to either:
- A bbox annotation file (.txt)
- OR a segmentation mask file (.png)

Automatically finds the corresponding image and creates an overlay showing:
- RED bboxes (DOTA OBB format)
- Segmentation mask in original iSAID colors (semi-transparent)

Usage:
    python dataset/visualize_annotation.py <path_to_annotation_or_mask>
    
Examples:
    python dataset/visualize_annotation.py dataset/iSAID/val/semantic_masks/P2695_instance_color_RGB.png
    python dataset/visualize_annotation.py dataset/AerialFuseCV/train/labels_obb/P0050.txt
"""

import os
import sys
import cv2
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
import matplotlib.patches as mpatches


class AnnotationVisualizer:
    """Flexible annotation visualizer for aerial imagery datasets."""
    
    def __init__(self):
        # DOTA class names
        self.class_names = [
            "plane", "ship", "storage-tank", "baseball-diamond", "tennis-court",
            "basketball-court", "ground-track-field", "harbor", "bridge", "large-vehicle",
            "small-vehicle", "helicopter", "roundabout", "soccer-ball-field", "swimming-pool"
        ]
        self.class_name_to_id = {name: i for i, name in enumerate(self.class_names)}
    
    def parse_input_path(self, input_path):
        """Parse input path to determine type and extract image name."""
        path = Path(input_path)
        
        # Determine input type
        if path.suffix == '.txt':
            input_type = 'bbox'
            img_name = path.stem
        elif path.suffix == '.png':
            input_type = 'mask'
            # Handle naming convention: P0001_instance_color_RGB.png -> P0001
            img_name = path.stem
            if '_instance_color_RGB' in img_name:
                img_name = img_name.replace('_instance_color_RGB', '')
            elif '_instance_id_RGB' in img_name:
                img_name = img_name.replace('_instance_id_RGB', '')
        else:
            raise ValueError(f"Unsupported file type: {path.suffix}")
        
        # Determine base directory (parent of labels/semantic_masks)
        parent = path.parent
        if parent.name in ['labels', 'labels_obb', 'labels_hbb', 'semantic_masks', 'instance_masks']:
            base_dir = parent.parent
        else:
            base_dir = parent
        
        return {
            'input_type': input_type,
            'img_name': img_name,
            'base_dir': base_dir,
            'original_path': path
        }
    
    def find_related_files(self, parsed):
        """Find all related files (image, bbox, mask) based on parsed info."""
        base_dir = parsed['base_dir']
        img_name = parsed['img_name']
        
        # Determine split from path (train/val/test)
        split = base_dir.name if base_dir.name in ['train', 'val', 'test'] else 'train'
        
        # Dataset root (parent of dataset folders)
        dataset_root = Path('dataset')
        
        # Possible image paths - including DOTA and DOTA_v1 for iSAID masks
        image_candidates = [
            base_dir / 'images' / f"{img_name}.png",
            base_dir / 'images' / f"{img_name}.jpg",
            base_dir / f"{img_name}.png",
            base_dir / f"{img_name}.jpg",
            # DOTA paths
            dataset_root / 'DOTA' / split / 'images' / f"{img_name}.png",
            dataset_root / 'DOTA' / 'val' / 'images' / f"{img_name}.png",
            dataset_root / 'DOTA' / 'train' / 'images' / f"{img_name}.png",
            # DOTA_v1 paths
            dataset_root / 'DOTA_v1' / split / 'images' / f"{img_name}.png",
            dataset_root / 'DOTA_v1' / 'val' / 'images' / f"{img_name}.png",
            dataset_root / 'DOTA_v1' / 'train' / 'images' / f"{img_name}.png",
            dataset_root / 'DOTAv1' / split / 'images' / f"{img_name}.png",
        ]
        
        # Possible bbox paths - including DOTA and DOTA_v1
        bbox_candidates = [
            base_dir / 'labels' / f"{img_name}.txt",
            base_dir / 'labelTxt' / f"{img_name}.txt",
            base_dir / f"{img_name}.txt",
            # DOTA label paths
            dataset_root / 'DOTA' / split / 'labels' / f"{img_name}.txt",
            dataset_root / 'DOTA' / split / 'labelTxt' / f"{img_name}.txt",
            dataset_root / 'DOTA' / 'val' / 'labels' / f"{img_name}.txt",
            dataset_root / 'DOTA' / 'val' / 'labelTxt' / f"{img_name}.txt",
            dataset_root / 'DOTA' / 'train' / 'labels' / f"{img_name}.txt",
            dataset_root / 'DOTA' / 'train' / 'labelTxt' / f"{img_name}.txt",
            # DOTA_v1 label paths
            dataset_root / 'DOTA_v1' / split / 'labels' / f"{img_name}.txt",
            dataset_root / 'DOTA_v1' / split / 'labelTxt' / f"{img_name}.txt",
            dataset_root / 'DOTA_v1' / 'val' / 'labels' / f"{img_name}.txt",
            dataset_root / 'DOTA_v1' / 'val' / 'labelTxt' / f"{img_name}.txt",
            dataset_root / 'DOTA_v1' / 'train' / 'labels' / f"{img_name}.txt",
            dataset_root / 'DOTA_v1' / 'train' / 'labelTxt' / f"{img_name}.txt",
        ]
        
        # Possible mask paths - including iSAID
        mask_candidates = [
            base_dir / 'semantic_masks' / f"{img_name}_instance_color_RGB.png",
            base_dir / 'Semantic_masks' / f"{img_name}_instance_color_RGB.png",
            base_dir / 'semantic_masks' / f"{img_name}.png",
            base_dir / f"{img_name}_instance_color_RGB.png",
            # iSAID mask paths
            dataset_root / 'iSAID' / split / 'semantic_masks' / f"{img_name}_instance_color_RGB.png",
            dataset_root / 'iSAID' / 'val' / 'semantic_masks' / f"{img_name}_instance_color_RGB.png",
            dataset_root / 'iSAID' / 'train' / 'semantic_masks' / f"{img_name}_instance_color_RGB.png",
        ]
        
        # Find existing files
        image_path = None
        for p in image_candidates:
            if p.exists():
                image_path = p
                break
        
        bbox_path = None
        for p in bbox_candidates:
            if p.exists():
                bbox_path = p
                break
        
        mask_path = None
        for p in mask_candidates:
            if p.exists():
                mask_path = p
                break
        
        return {
            'image': image_path,
            'bbox': bbox_path,
            'mask': mask_path,
            'img_name': img_name
        }
    
    def load_bboxes_dota(self, label_path):
        """Load bboxes from DOTA format."""
        bboxes = []
        if label_path is None or not os.path.exists(label_path):
            return bboxes
        
        with open(label_path, 'r') as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) < 9 or parts[0] in ['imagesource:', 'gsd:']:
                    continue
                try:
                    # OBB: x1 y1 x2 y2 x3 y3 x4 y4 class [difficult]
                    x_coords = [float(parts[i]) for i in range(0, 8, 2)]
                    y_coords = [float(parts[i]) for i in range(1, 8, 2)]
                    class_name = parts[8]
                    
                    class_id = self.class_name_to_id.get(class_name, -1)
                    bboxes.append({
                        'class_id': class_id,
                        'class_name': class_name,
                        'obb_coords': list(zip(x_coords, y_coords))
                    })
                except (ValueError, IndexError):
                    continue
        return bboxes
    
    def visualize(self, input_path, show=True):
        """Create visualization overlay for the given annotation path."""
        print(f"\n{'='*70}")
        print("  ANNOTATION VISUALIZER")
        print(f"{'='*70}")
        print(f"Input: {input_path}")
        
        # Output directory
        output_dir = Path('results/Visualize_Annotation')
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Parse input
        parsed = self.parse_input_path(input_path)
        print(f"Type: {parsed['input_type']}")
        print(f"Image name: {parsed['img_name']}")
        print(f"Base dir: {parsed['base_dir']}")
        
        # Find related files
        files = self.find_related_files(parsed)
        print(f"\nFound files:")
        print(f"  Image: {files['image']}")
        print(f"  BBox:  {files['bbox']}")
        print(f"  Mask:  {files['mask']}")
        
        # Load image
        if files['image'] is None:
            print("\n[ERROR] Could not find corresponding image!")
            return None
        
        image = cv2.imread(str(files['image']))
        if image is None:
            print(f"\n[ERROR] Could not load image: {files['image']}")
            return None
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        print(f"\nImage size: {image.shape[1]}x{image.shape[0]}")
        
        # Load segmentation mask
        mask_rgb = None
        if files['mask'] is not None:
            mask_bgr = cv2.imread(str(files['mask']))
            if mask_bgr is not None:
                mask_rgb = cv2.cvtColor(mask_bgr, cv2.COLOR_BGR2RGB)
                print(f"Mask loaded: {files['mask'].name}")
        
        # Load bboxes
        bboxes = self.load_bboxes_dota(files['bbox'])
        print(f"BBoxes loaded: {len(bboxes)}")
        
        # Create figure
        fig, ax = plt.subplots(figsize=(14, 14))
        
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
        
        title = f"Image: {files['img_name']}\n"
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
        
        # Always save to output directory
        save_path = output_dir / f"{files['img_name']}_overlay.png"
        plt.savefig(save_path, dpi=150, bbox_inches='tight', pad_inches=0.1)
        print(f"\nSaved to: {save_path}")
        
        if show:
            plt.show()
        else:
            plt.close()
        
        print(f"\n{'='*70}")
        return fig


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print("\nError: Please provide a path to an annotation file or mask.")
        print("Example: python dataset/visualize_annotation.py dataset/iSAID/val/semantic_masks/P2695_instance_color_RGB.png")
        sys.exit(1)
    
    input_path = sys.argv[1]
    
    visualizer = AnnotationVisualizer()
    visualizer.visualize(input_path, show=True)


if __name__ == "__main__":
    main()
