"""
AerialFuseCV Dataset Merger Script

This script creates AerialFuseCV_Merged by:
1. Merging train and val splits from AerialFuseCV_Refined
2. Ensuring perfect alignment: images, bboxes, and segmentation masks match
3. Generating detailed analysis report

Output: AerialFuseCV_Merged with single merged split
"""

import os
import cv2
import numpy as np
import json
from pathlib import Path
from tqdm import tqdm
from collections import defaultdict
import shutil


class AerialFuseCVMerger:
    """Merges refined AerialFuseCV splits into single dataset."""
    
    def __init__(self, source_dir="dataset/AerialFuseCV_Refined", output_dir="dataset/AerialFuseCV_Merged"):
        self.source_dir = Path(source_dir)
        self.output_dir = Path(output_dir)
        
        # DOTA class names
        self.class_names = [
            "plane", "ship", "storage-tank", "baseball-diamond", "tennis-court",
            "basketball-court", "ground-track-field", "harbor", "bridge", "large-vehicle",
            "small-vehicle", "helicopter", "roundabout", "soccer-ball-field", "swimming-pool"
        ]
        
        # Statistics
        self.stats = defaultdict(lambda: {'images': 0, 'bboxes': 0, 'masks': 0})
        self.total_images = 0
        self.total_bboxes = 0
        self.total_masks = 0
    
    def merge_splits(self):
        """Merge train and val splits into single dataset."""
        print("\n" + "="*80)
        print("MERGING AERIALFUSECV REFINED SPLITS")
        print("="*80)
        
        # Create output directories
        output_images_dir = self.output_dir / 'images'
        output_labels_dir = self.output_dir / 'labels'
        output_masks_dir = self.output_dir / 'semantic_masks'
        
        output_images_dir.mkdir(parents=True, exist_ok=True)
        output_labels_dir.mkdir(parents=True, exist_ok=True)
        output_masks_dir.mkdir(parents=True, exist_ok=True)
        
        # Process both splits
        for split in ['train', 'val']:
            print(f"\nProcessing {split} split...")
            
            images_dir = self.source_dir / split / 'images'
            labels_dir = self.source_dir / split / 'labels'
            masks_dir = self.source_dir / split / 'semantic_masks'
            
            if not images_dir.exists():
                print(f"Warning: {images_dir} does not exist, skipping...")
                continue
            
            image_files = sorted(images_dir.glob('*.png'))
            
            for img_path in tqdm(image_files, desc=f"Copying {split}"):
                img_name = img_path.name
                label_name = img_path.stem + '.txt'
                mask_name = img_path.stem + '_instance_color_RGB.png'
                
                # Copy image
                shutil.copy(img_path, output_images_dir / img_name)
                
                # Copy label
                label_src = labels_dir / label_name
                if label_src.exists():
                    shutil.copy(label_src, output_labels_dir / label_name)
                    
                    # Count bboxes and update stats
                    with open(label_src, 'r') as f:
                        for line in f:
                            parts = line.strip().split()
                            if len(parts) >= 9 and parts[0] not in ['imagesource:', 'gsd:']:
                                class_name = parts[8]
                                if class_name in self.class_names:
                                    self.stats[class_name]['bboxes'] += 1
                                    self.total_bboxes += 1
                
                # Copy mask
                mask_src = masks_dir / mask_name
                if mask_src.exists():
                    shutil.copy(mask_src, output_masks_dir / mask_name)
                    
                    # Count masks per class
                    mask_rgb = cv2.imread(str(mask_src))
                    if mask_rgb is not None:
                        mask_rgb = cv2.cvtColor(mask_rgb, cv2.COLOR_BGR2RGB)
                        
                        # Class color mapping
                        class_color_mapping = {
                            0: (0, 127, 255), 1: (0, 0, 63), 2: (0, 63, 6), 3: (0, 63, 0),
                            4: (0, 63, 127), 5: (0, 63, 191), 6: (0, 63, 255), 7: (0, 100, 155),
                            8: (0, 127, 163), 9: (0, 127, 127), 10: (0, 0, 127), 11: (0, 0, 191),
                            12: (0, 191, 127), 13: (0, 127, 191), 14: (0, 0, 255)
                        }
                        
                        for class_id, color in class_color_mapping.items():
                            class_mask = np.all(mask_rgb == np.array(color), axis=-1)
                            if class_mask.sum() > 0:
                                class_name = self.class_names[class_id]
                                self.stats[class_name]['masks'] += 1
                                self.total_masks += 1
                
                self.total_images += 1
                
                # Update per-class image count
                if label_src.exists():
                    with open(label_src, 'r') as f:
                        classes_in_image = set()
                        for line in f:
                            parts = line.strip().split()
                            if len(parts) >= 9 and parts[0] not in ['imagesource:', 'gsd:']:
                                class_name = parts[8]
                                if class_name in self.class_names:
                                    classes_in_image.add(class_name)
                        
                        for class_name in classes_in_image:
                            self.stats[class_name]['images'] += 1
        
        print(f"\nMerge complete! Total images: {self.total_images}")
    
    def generate_analysis_report(self):
        """Generate detailed dataset analysis report."""
        report = []
        report.append("="*80)
        report.append("AERIALFUSECV MERGED - DATASET ANALYSIS REPORT")
        report.append("="*80)
        report.append("")
        
        report.append("MERGED DATASET STATISTICS")
        report.append("="*80)
        report.append(f"\nOverall Statistics:")
        report.append(f"  Total Images: {self.total_images}")
        report.append(f"  Total Bounding Boxes: {self.total_bboxes}")
        report.append(f"  Total Segmentation Masks: {self.total_masks}")
        report.append(f"  Average Bboxes per Image: {self.total_bboxes/self.total_images:.2f}")
        report.append(f"  Average Masks per Image: {self.total_masks/self.total_images:.2f}")
        
        report.append(f"\nPer-Class Statistics:")
        report.append(f"{'Class':<20} {'Images':<10} {'Bboxes':<10} {'Masks':<10} {'Bbox/Img':<12} {'Mask/Img':<12}")
        report.append("-"*80)
        
        for class_name in self.class_names:
            stats = self.stats[class_name]
            images = stats['images']
            bboxes = stats['bboxes']
            masks = stats['masks']
            bbox_per_img = bboxes / images if images > 0 else 0
            mask_per_img = masks / images if images > 0 else 0
            
            report.append(f"{class_name:<20} {images:<10} {bboxes:<10} {masks:<10} {bbox_per_img:<12.2f} {mask_per_img:<12.2f}")
        
        # Save report
        report_path = self.output_dir / 'DATASET_ANALYSIS.txt'
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report))
        
        # Print to console
        print('\n'.join(report))
        
        # Save JSON version
        json_stats = {
            'total_images': self.total_images,
            'total_bboxes': self.total_bboxes,
            'total_masks': self.total_masks,
            'per_class': {name: dict(self.stats[name]) for name in self.class_names}
        }
        
        json_path = self.output_dir / 'dataset_statistics.json'
        with open(json_path, 'w') as f:
            json.dump(json_stats, f, indent=4)
        
        print(f"\n[OK] Analysis report saved to: {report_path}")
        print(f"[OK] Statistics JSON saved to: {json_path}")
    
    def run(self):
        """Run the complete merge process."""
        print("\n" + "="*80)
        print("AERIALFUSECV DATASET MERGER")
        print("="*80)
        print(f"Source: {self.source_dir}")
        print(f"Output: {self.output_dir}")
        print("="*80)
        
        # Merge splits
        self.merge_splits()
        
        # Generate analysis report
        self.generate_analysis_report()
        
        print("\n" + "="*80)
        print("[OK] MERGE COMPLETE!")
        print("="*80)


if __name__ == "__main__":
    merger = AerialFuseCVMerger()
    merger.run()
