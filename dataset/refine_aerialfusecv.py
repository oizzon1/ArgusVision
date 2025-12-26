"""
AerialFuseCV Dataset Refinement Script

This script creates a refined version of AerialFuseCV by:
1. Matching bounding boxes (DOTA) with segmentation masks (iSAID)
2. Removing unmatched bboxes (no corresponding segmentation)
3. Removing unmatched segmentation instances (no corresponding bbox)
4. Generating detailed dataset analysis

Output: AerialFuseCV_Refined with only matched bbox-mask pairs
"""

import os
import cv2
import numpy as np
import json
from pathlib import Path
from tqdm import tqdm
from collections import defaultdict
import shutil


class AerialFuseCVRefiner:
    """Refines AerialFuseCV dataset by matching bboxes with segmentation masks."""
    
    def __init__(self, source_dir="dataset/AerialFuseCV", output_dir="dataset/AerialFuseCV_Refined"):
        self.source_dir = Path(source_dir)
        self.output_dir = Path(output_dir)
        
        # DOTA class names
        self.class_names = [
            "plane", "ship", "storage-tank", "baseball-diamond", "tennis-court",
            "basketball-court", "ground-track-field", "harbor", "bridge", "large-vehicle",
            "small-vehicle", "helicopter", "roundabout", "soccer-ball-field", "swimming-pool"
        ]
        
        # Class name to ID mapping
        self.class_name_to_id = {name: i for i, name in enumerate(self.class_names)}
        
        # Class color mapping for AerialFuseCV RGB masks
        self.class_color_mapping = {
            0: (0, 127, 255),    # plane
            1: (0, 0, 63),       # ship
            2: (0, 63, 6),       # storage-tank
            3: (0, 63, 0),       # baseball-diamond
            4: (0, 63, 127),     # tennis-court
            5: (0, 63, 191),     # basketball-court
            6: (0, 63, 255),     # ground-track-field
            7: (0, 100, 155),    # harbor
            8: (0, 127, 163),    # bridge
            9: (0, 127, 127),    # large-vehicle
            10: (0, 0, 127),     # small-vehicle
            11: (0, 0, 191),     # helicopter
            12: (0, 191, 127),   # roundabout
            13: (0, 127, 191),   # soccer-ball-field
            14: (0, 0, 255)      # swimming-pool
        }
        
        # Statistics
        self.stats = {
            'train': defaultdict(lambda: {'bboxes': 0, 'masks': 0, 'matched': 0, 'discarded_bboxes': 0, 'discarded_masks': 0}),
            'val': defaultdict(lambda: {'bboxes': 0, 'masks': 0, 'matched': 0, 'discarded_bboxes': 0, 'discarded_masks': 0})
        }
    
    def load_bboxes(self, label_path):
        """Load bounding boxes from DOTA format label file."""
        bboxes = []
        
        if not os.path.exists(label_path):
            return bboxes
        
        with open(label_path, 'r') as f:
            for line in f:
                parts = line.strip().split()
                
                # Skip header lines
                if parts[0] in ['imagesource:', 'gsd:']:
                    continue
                
                # DOTA format: x1 y1 x2 y2 x3 y3 x4 y4 class_name difficulty
                if len(parts) < 10:
                    continue
                
                try:
                    x_coords = [float(parts[i]) for i in range(0, 8, 2)]
                    y_coords = [float(parts[i]) for i in range(1, 8, 2)]
                    class_name = parts[8]
                    
                    if class_name not in self.class_name_to_id:
                        continue
                    
                    class_id = self.class_name_to_id[class_name]
                    
                    # Create axis-aligned bounding box
                    x_min, x_max = min(x_coords), max(x_coords)
                    y_min, y_max = min(y_coords), max(y_coords)
                    
                    bboxes.append({
                        'class_id': class_id,
                        'class_name': class_name,
                        'bbox': [x_min, y_min, x_max, y_max],
                        'obb': x_coords + y_coords,  # Store as [x1,x2,x3,x4,y1,y2,y3,y4]
                        'difficulty': parts[9] if len(parts) > 9 else '0'
                    })
                except (ValueError, IndexError):
                    continue
        
        return bboxes
    
    def load_segmentation_mask(self, mask_path):
        """Load RGB segmentation mask."""
        if not os.path.exists(mask_path):
            return None
        
        mask_rgb = cv2.imread(str(mask_path))
        if mask_rgb is None:
            return None
        
        # Convert BGR to RGB
        mask_rgb = cv2.cvtColor(mask_rgb, cv2.COLOR_BGR2RGB)
        return mask_rgb
    
    def extract_class_mask(self, rgb_mask, class_id):
        """Extract binary mask for a specific class."""
        if class_id not in self.class_color_mapping:
            return None
        
        class_color = np.array(self.class_color_mapping[class_id])
        binary_mask = np.all(rgb_mask == class_color, axis=-1).astype(np.uint8)
        
        return binary_mask
    
    def bbox_mask_iou(self, bbox, mask):
        """Calculate IoU between bbox and mask."""
        x1, y1, x2, y2 = bbox
        h, w = mask.shape
        
        # Create bbox mask
        bbox_mask = np.zeros((h, w), dtype=bool)
        x1, y1 = max(0, int(x1)), max(0, int(y1))
        x2, y2 = min(w, int(x2)), min(h, int(y2))
        
        if x2 <= x1 or y2 <= y1:
            return 0.0
        
        bbox_mask[y1:y2, x1:x2] = True
        
        # Calculate IoU
        intersection = np.logical_and(bbox_mask, mask).sum()
        union = np.logical_or(bbox_mask, mask).sum()
        
        return intersection / union if union > 0 else 0.0
    
    def match_bbox_to_mask_instance(self, bbox, rgb_mask, min_iou=0.1):
        """
        Match a single bbox to its specific mask instance using connected components.
        OPTIMIZED: Crops to bbox region to speed up processing.
        
        Args:
            bbox: Dict containing bbox info (class_id, bbox coordinates)
            rgb_mask: Full RGB segmentation mask
            min_iou: Minimum IoU threshold for matching
            
        Returns:
            instance_mask: Binary mask for the matched instance, or None
            iou: IoU score of the match
        """
        class_id = bbox['class_id']
        
        # Extract class mask
        class_mask = self.extract_class_mask(rgb_mask, class_id)
        if class_mask is None or class_mask.sum() == 0:
            return None, 0.0
        
        # OPTIMIZATION: Crop to bbox region with padding for better matching
        x1, y1, x2, y2 = bbox['bbox']
        h, w = class_mask.shape
        
        # Add 20% padding around bbox
        padding = int(max(x2 - x1, y2 - y1) * 0.2)
        crop_x1 = max(0, int(x1) - padding)
        crop_y1 = max(0, int(y1) - padding)
        crop_x2 = min(w, int(x2) + padding)
        crop_y2 = min(h, int(y2) + padding)
        
        # Crop class mask to region of interest
        cropped_mask = class_mask[crop_y1:crop_y2, crop_x1:crop_x2]
        
        # Skip if no pixels in cropped region
        if cropped_mask.sum() == 0:
            return None, 0.0
        
        # Find connected components in cropped region (much faster!)
        num_instances, instance_labels = cv2.connectedComponents(cropped_mask)
        
        # Match bbox to best instance by IoU
        best_iou = 0.0
        best_instance_mask = None
        
        for instance_id in range(1, num_instances):  # Skip 0 (background)
            # Create instance mask in cropped space
            cropped_instance = (instance_labels == instance_id).astype(np.uint8)
            
            # Create full-size instance mask
            full_instance_mask = np.zeros((h, w), dtype=np.uint8)
            full_instance_mask[crop_y1:crop_y2, crop_x1:crop_x2] = cropped_instance
            
            # Calculate IoU
            iou = self.bbox_mask_iou(bbox['bbox'], full_instance_mask)
            
            if iou > best_iou:
                best_iou = iou
                best_instance_mask = full_instance_mask
        
        # Return match if IoU meets threshold
        if best_iou >= min_iou:
            return best_instance_mask, best_iou
        else:
            return None, best_iou
    
    def match_bboxes_to_mask_instances(self, bboxes, rgb_mask, iou_threshold=0.1):
        """
        Match bboxes to specific mask instances (instance-level matching).
        
        Returns:
            matched_pairs: List of dicts with {bbox, instance_mask, iou}
        """
        matched_pairs = []
        
        for bbox in bboxes:
            # Match this bbox to its specific mask instance
            instance_mask, iou = self.match_bbox_to_mask_instance(bbox, rgb_mask, iou_threshold)
            
            if instance_mask is not None:
                matched_pairs.append({
                    'bbox': bbox,
                    'instance_mask': instance_mask,
                    'iou': iou
                })
        
        return matched_pairs
    
    def save_refined_labels(self, matched_bboxes, output_path):
        """Save matched bboxes to label file in DOTA format."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            for bbox in matched_bboxes:
                # OBB stored as [x1,x2,x3,x4,y1,y2,y3,y4]
                # DOTA format needs: x1 y1 x2 y2 x3 y3 x4 y4
                obb = bbox['obb']
                line = f"{obb[0]:.1f} {obb[4]:.1f} {obb[1]:.1f} {obb[5]:.1f} "
                line += f"{obb[2]:.1f} {obb[6]:.1f} {obb[3]:.1f} {obb[7]:.1f} "
                line += f"{bbox['class_name']} {bbox['difficulty']}\n"
                f.write(line)
    
    def save_refined_mask(self, matched_pairs, output_path, original_shape):
        """Save refined segmentation mask with only matched instances."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create empty RGB mask
        h, w = original_shape[:2]
        refined_mask = np.zeros((h, w, 3), dtype=np.uint8)
        
        # Add each matched instance with its class color
        for pair in matched_pairs:
            class_id = pair['bbox']['class_id']
            instance_mask = pair['instance_mask']
            color = self.class_color_mapping[class_id]
            
            # Paint this specific instance
            refined_mask[instance_mask > 0] = color
        
        # Convert RGB to BGR for saving
        refined_mask_bgr = cv2.cvtColor(refined_mask, cv2.COLOR_RGB2BGR)
        cv2.imwrite(str(output_path), refined_mask_bgr)
    
    def refine_split(self, split='train'):
        """Refine a dataset split (train or val)."""
        print(f"\n{'='*60}")
        print(f"Refining {split} split...")
        print(f"{'='*60}")
        
        # Paths
        images_dir = self.source_dir / split / 'images'
        labels_dir = self.source_dir / split / 'labels'
        masks_dir = self.source_dir / split / 'semantic_masks'
        
        output_images_dir = self.output_dir / split / 'images'
        output_labels_dir = self.output_dir / split / 'labels'
        output_masks_dir = self.output_dir / split / 'semantic_masks'
        
        # Get all images
        image_files = sorted(images_dir.glob('*.png'))
        
        for img_path in tqdm(image_files, desc=f"Processing {split}"):
            img_name = img_path.stem
            label_path = labels_dir / f"{img_name}.txt"
            mask_path = masks_dir / f"{img_name}_instance_color_RGB.png"
            
            # Load data
            bboxes = self.load_bboxes(label_path)
            rgb_mask = self.load_segmentation_mask(mask_path)
            
            if not bboxes or rgb_mask is None:
                continue
            
            # Match bboxes to specific mask instances
            matched_pairs = self.match_bboxes_to_mask_instances(bboxes, rgb_mask)
            
            # Update statistics - count all bboxes first
            for bbox in bboxes:
                class_name = bbox['class_name']
                self.stats[split][class_name]['bboxes'] += 1
            
            # Count matched bboxes
            matched_class_set = set()
            for pair in matched_pairs:
                class_name = pair['bbox']['class_name']
                self.stats[split][class_name]['matched'] += 1
                matched_class_set.add(pair['bbox']['class_id'])
            
            # Count discarded bboxes
            for bbox in bboxes:
                matched = any(pair['bbox'] == bbox for pair in matched_pairs)
                if not matched:
                    class_name = bbox['class_name']
                    self.stats[split][class_name]['discarded_bboxes'] += 1
            
            # Count original masks and discarded masks
            for class_id in range(15):
                original_mask = self.extract_class_mask(rgb_mask, class_id)
                if original_mask is not None and original_mask.sum() > 0:
                    class_name = self.class_names[class_id]
                    
                    # Count instances in original mask
                    num_instances, _ = cv2.connectedComponents(original_mask)
                    instance_count = num_instances - 1  # Subtract background
                    
                    self.stats[split][class_name]['masks'] += instance_count
                    
                    # Count matched instances for this class
                    matched_count = sum(1 for pair in matched_pairs if pair['bbox']['class_id'] == class_id)
                    discarded_count = instance_count - matched_count
                    
                    if discarded_count > 0:
                        self.stats[split][class_name]['discarded_masks'] += discarded_count
            
            # Save refined data only if there are matched pairs
            if matched_pairs:
                # Copy image
                output_img_path = output_images_dir / img_path.name
                output_img_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(img_path, output_img_path)
                
                # Save refined labels (only matched bboxes)
                matched_bboxes = [pair['bbox'] for pair in matched_pairs]
                output_label_path = output_labels_dir / f"{img_name}.txt"
                self.save_refined_labels(matched_bboxes, output_label_path)
                
                # Save refined mask (only matched instances)
                output_mask_path = output_masks_dir / f"{img_name}_instance_color_RGB.png"
                self.save_refined_mask(matched_pairs, output_mask_path, rgb_mask.shape)
    
    def generate_analysis_report(self):
        """Generate detailed dataset analysis report in Markdown format."""
        report = []
        report.append("# AerialFuseCV Refined - Dataset Analysis Report")
        report.append("")
        report.append("**Instance-Level Bbox-Mask Matching | Perfect 1:1 Correspondence**")
        report.append("")
        
        # Overall statistics
        for split in ['train', 'val']:
            report.append(f"\n## {split.upper()} Split Analysis")
            report.append("")
            
            total_bboxes = sum(self.stats[split][cls]['bboxes'] for cls in self.class_names)
            total_masks = sum(self.stats[split][cls]['masks'] for cls in self.class_names)
            total_matched = sum(self.stats[split][cls]['matched'] for cls in self.class_names)
            total_discarded_bboxes = sum(self.stats[split][cls]['discarded_bboxes'] for cls in self.class_names)
            total_discarded_masks = sum(self.stats[split][cls]['discarded_masks'] for cls in self.class_names)
            
            match_rate = (total_matched / total_bboxes * 100) if total_bboxes > 0 else 0
            
            report.append("### Overall Statistics")
            report.append("")
            report.append("| Metric | Count | Percentage |")
            report.append("|--------|------:|----------:|")
            report.append(f"| Total Bounding Boxes | {total_bboxes:,} | 100.0% |")
            report.append(f"| Total Segmentation Masks | {total_masks:,} | - |")
            report.append(f"| **Matched Pairs** | **{total_matched:,}** | **{match_rate:.1f}%** |")
            report.append(f"| Discarded Bboxes | {total_discarded_bboxes:,} | {total_discarded_bboxes/total_bboxes*100:.1f}% |")
            report.append(f"| Discarded Masks | {total_discarded_masks:,} | {total_discarded_masks/total_masks*100:.1f}% |")
            report.append("")
            
            # Per-class statistics
            report.append("### Per-Class Statistics")
            report.append("")
            report.append("| Class | Bboxes | Masks | Matched | Disc. Bbox | Disc. Mask | Match % |")
            report.append("|-------|-------:|------:|--------:|-----------:|-----------:|--------:|")
            
            for class_name in self.class_names:
                stats = self.stats[split][class_name]
                bboxes = stats['bboxes']
                masks = stats['masks']
                matched = stats['matched']
                disc_bbox = stats['discarded_bboxes']
                disc_mask = stats['discarded_masks']
                match_pct = (matched / bboxes * 100) if bboxes > 0 else 0
                
                # Add emoji indicators
                if match_pct >= 50:
                    emoji = "✅"
                elif match_pct >= 10:
                    emoji = "⚠️"
                elif bboxes > 0:
                    emoji = "❌"
                else:
                    emoji = "➖"
                
                report.append(f"| {emoji} {class_name} | {bboxes:,} | {masks:,} | {matched:,} | {disc_bbox:,} | {disc_mask:,} | {match_pct:.1f}% |")
            
            report.append("")
        
        # Save report as Markdown
        report_path = self.output_dir / 'DATASET_ANALYSIS.md'
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report))
        
        # Also print to console
        print('\n'.join(report))
        
        # Save JSON version
        json_path = self.output_dir / 'dataset_statistics.json'
        with open(json_path, 'w') as f:
            json.dump(self.stats, f, indent=4)
        
        print(f"\n✅ Analysis report saved to: {report_path}")
        print(f"✅ Statistics JSON saved to: {json_path}")
    
    def run(self):
        """Run the complete refinement process."""
        print("\n" + "="*80)
        print("AERIALFUSECV DATASET REFINEMENT")
        print("="*80)
        print(f"Source: {self.source_dir}")
        print(f"Output: {self.output_dir}")
        print("="*80)
        
        # Refine both splits
        self.refine_split('train')
        self.refine_split('val')
        
        # Generate analysis report
        self.generate_analysis_report()
        
        print("\n" + "="*80)
        print("✅ REFINEMENT COMPLETE!")
        print("="*80)


if __name__ == "__main__":
    refiner = AerialFuseCVRefiner()
    refiner.run()
