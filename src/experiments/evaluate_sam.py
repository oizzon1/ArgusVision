"""
SAM Benchmark Evaluation Script
Evaluates SAM variants (ViT-H, ViT-L, ViT-B) using perfect ground truth prompts.

This script isolates SAM's intrinsic performance on aerial imagery by using
ground truth bounding boxes from AerialFuseCV dataset.

Configurations:
- 3 SAM models: ViT-H, ViT-L, ViT-B
- 2 prompt types: Box, Point
- Total: 6 configurations

"""

import os
import sys
import json
import time
import numpy as np
import cv2
from pathlib import Path
from tqdm import tqdm
from PIL import Image
import warnings

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.models.sam_segmenter import SAMSegmenter
from src.utils.metrics import calculate_mask_iou, calculate_mask_dice
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

warnings.filterwarnings(
    "ignore",
    category=FutureWarning,
    module="segment_anything.build_sam"
)


class SAMBenchmarkEvaluator:
    """
    Evaluates SAM models using ground truth prompts from AerialFuseCV_Refined dataset.
    """
    
    def __init__(self, dataset_root, sam_checkpoint_dir="model_checkpoints/SAM", excluded_classes=None):
        """
        Initialize the SAM benchmark evaluator.
        
        Args:
            dataset_root: Path to AerialFuseCV_Refined_Merged dataset
            sam_checkpoint_dir: Directory containing SAM checkpoints
            excluded_classes: List of class IDs to exclude (e.g., [2, 8] for storage-tank & bridge)
        """
        self.dataset_root = Path(dataset_root)
        self.sam_checkpoint_dir = Path(sam_checkpoint_dir)
        
        # Classes to exclude (have 0% match rate in refined dataset)
        self.excluded_classes = excluded_classes if excluded_classes is not None else [2, 8]  # storage-tank, bridge
        
        # SAM model configurations
        self.sam_configs = {
            'vit_h': {
                'checkpoint': self.sam_checkpoint_dir / 'sam_vit_h_4b8939.pth',
                'type': 'vit_h',
                'name': 'SAM-ViT-H'
            },
            'vit_l': {
                'checkpoint': self.sam_checkpoint_dir / 'sam_vit_l_0b3195.pth',
                'type': 'vit_l',
                'name': 'SAM-ViT-L'
            },
            'vit_b': {
                'checkpoint': self.sam_checkpoint_dir / 'sam_vit_b_01ec64.pth',
                'type': 'vit_b',
                'name': 'SAM-ViT-B'
            }
        }
        
        # Prompt types
        self.prompt_types = ['box', 'point']
        
        # DOTA class names
        self.class_names = [
            "plane", "ship", "storage-tank", "baseball-diamond", "tennis-court",
            "basketball-court", "ground-track-field", "harbor", "bridge", "large-vehicle",
            "small-vehicle", "helicopter", "roundabout", "soccer-ball-field", "swimming-pool"
        ]
        
        # Class color mapping for AerialFuseCV RGB masks (from notebook)
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
    
    def load_ground_truth_labels(self, label_path, image_width, image_height):
        """
        Load ground truth OBB labels from DOTA format file.
        
        Args:
            label_path: Path to label file
            image_width: Image width in pixels
            image_height: Image height in pixels
            
        Returns:
            List of dicts with 'class_id', 'bbox' (8 points), 'box_prompt', 'point_prompt'
        """
        labels = []
        
        if not os.path.exists(label_path):
            return labels
        
        # DOTA class name to ID mapping
        class_name_to_id = {
            "plane": 0, "ship": 1, "storage-tank": 2, "baseball-diamond": 3,
            "tennis-court": 4, "basketball-court": 5, "ground-track-field": 6,
            "harbor": 7, "bridge": 8, "large-vehicle": 9, "small-vehicle": 10,
            "helicopter": 11, "roundabout": 12, "soccer-ball-field": 13,
            "swimming-pool": 14
        }
        
        with open(label_path, 'r') as f:
            for line in f:
                parts = line.strip().split()
                
                # Skip header lines
                if parts[0] in ['imagesource:', 'gsd:']:
                    continue
                
                # DOTA format: x1 y1 x2 y2 x3 y3 x4 y4 class_name difficulty
                if len(parts) < 10:
                    continue
                
                # Parse coordinates (already in pixel format)
                try:
                    x_coords = [float(parts[i]) for i in range(0, 8, 2)]
                    y_coords = [float(parts[i]) for i in range(1, 8, 2)]
                    class_name = parts[8]
                    
                    # Get class ID
                    if class_name not in class_name_to_id:
                        continue
                    class_id = class_name_to_id[class_name]
                    
                    # Skip excluded classes (no masks available in refined dataset)
                    if class_id in self.excluded_classes:
                        continue
                    
                    # Create axis-aligned bounding box for box prompt
                    x_min, x_max = min(x_coords), max(x_coords)
                    y_min, y_max = min(y_coords), max(y_coords)
                    box_prompt = np.array([x_min, y_min, x_max, y_max])
                    
                    # Create point prompt (center of bbox)
                    point_prompt = np.array([(x_min + x_max) / 2, (y_min + y_max) / 2])
                    
                    labels.append({
                        'class_id': class_id,
                        'bbox': [int(x) for x in x_coords + y_coords],  # Original OBB
                        'box_prompt': box_prompt,
                        'point_prompt': point_prompt
                    })
                except (ValueError, IndexError) as e:
                    continue
        
        return labels
    
    def extract_class_mask(self, rgb_mask, class_id):
        """
        Extract binary mask for a specific class from RGB semantic mask.
        
        Args:
            rgb_mask: RGB semantic mask (H, W, 3)
            class_id: Class ID to extract (0-14)
            
        Returns:
            Binary mask (numpy array) for the specified class
        """
        if class_id not in self.class_color_mapping:
            return None
        
        # Get the RGB color for this class
        class_color = np.array(self.class_color_mapping[class_id])
        
        # Extract binary mask where all RGB channels match the class color
        binary_mask = np.all(rgb_mask == class_color, axis=-1).astype(np.uint8)
        
        return binary_mask
    
    def load_ground_truth_mask(self, mask_path):
        """
        Load ground truth RGB semantic mask.
        
        Args:
            mask_path: Path to semantic mask image
            
        Returns:
            RGB mask (numpy array) or None if not found
        """
        if not os.path.exists(mask_path):
            return None
        
        # Load RGB mask
        mask_rgb = cv2.imread(str(mask_path))
        if mask_rgb is None:
            return None
        
        # Convert BGR to RGB
        mask_rgb = cv2.cvtColor(mask_rgb, cv2.COLOR_BGR2RGB)
        
        return mask_rgb
    
    def match_prompt_to_gt_mask(self, box_prompt, gt_mask, iou_threshold=0.3):
        """
        Check if a bounding box prompt has a corresponding GT mask by spatial overlap.
        
        Args:
            box_prompt: Bounding box [x1, y1, x2, y2]
            gt_mask: Binary GT mask (H, W)
            iou_threshold: Minimum IoU to consider a match
            
        Returns:
            bool: True if prompt matches GT mask (IoU > threshold)
        """
        if gt_mask is None or gt_mask.sum() == 0:
            return False
        
        # Create mask from bounding box
        x1, y1, x2, y2 = box_prompt
        h, w = gt_mask.shape
        box_mask = np.zeros((h, w), dtype=bool)
        
        # Clip coordinates to image bounds
        x1, y1 = max(0, int(x1)), max(0, int(y1))
        x2, y2 = min(w, int(x2)), min(h, int(y2))
        
        if x2 <= x1 or y2 <= y1:
            return False
        
        box_mask[y1:y2, x1:x2] = True
        
        # Calculate IoU between box and GT mask
        intersection = np.logical_and(box_mask, gt_mask).sum()
        union = np.logical_or(box_mask, gt_mask).sum()
        
        if union == 0:
            return False
        
        iou = intersection / union
        return iou >= iou_threshold
    
    def save_visualization(self, image_rgb, gt_mask, pred_mask, class_name, 
                          iou, dice, img_name, config_name, output_dir, prompts=None, prompt_type='box'):
        """
        Save side-by-side visualization of GT mask and predicted mask.
        
        Args:
            image_rgb: Original image (RGB)
            gt_mask: Ground truth binary mask
            pred_mask: Predicted binary mask
            class_name: Name of the class
            iou: IoU score
            dice: DICE score
            img_name: Image filename
            config_name: Configuration name (e.g., SAM-ViT-H-BOX)
            output_dir: Output directory for visualizations
            prompts: List of prompts (boxes or points) used for segmentation
            prompt_type: Type of prompt ('box' or 'point')
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Create figure with 3 subplots: Original, GT Mask, Predicted Mask
        fig, axes = plt.subplots(1, 3, figsize=(18, 6))
        
        # Original image with prompts
        axes[0].imshow(image_rgb)
        
        # Draw prompts on the original image
        if prompts is not None:
            if prompt_type == 'box':
                # Draw bounding boxes
                for box in prompts:
                    x1, y1, x2, y2 = box
                    rect = Rectangle((x1, y1), x2-x1, y2-y1, 
                                   linewidth=2, edgecolor='cyan', facecolor='none')
                    axes[0].add_patch(rect)
            else:  # point
                # Draw points
                for point in prompts:
                    if len(point) == 2:  # Single point
                        x, y = point
                        axes[0].plot(x, y, 'r*', markersize=15, markeredgewidth=2, markeredgecolor='yellow')
                    else:  # List of points
                        for p in point:
                            x, y = p
                            axes[0].plot(x, y, 'r*', markersize=15, markeredgewidth=2, markeredgecolor='yellow')
        
        axes[0].set_title('Original Image with Prompts', fontsize=12, fontweight='bold')
        axes[0].axis('off')
        
        # GT mask overlay
        axes[1].imshow(image_rgb)
        gt_overlay = np.zeros((*gt_mask.shape, 4))
        gt_overlay[gt_mask > 0] = [0, 1, 0, 0.5]  # Green with 50% transparency
        axes[1].imshow(gt_overlay)
        axes[1].set_title('Ground Truth Mask', fontsize=12, fontweight='bold')
        axes[1].axis('off')
        
        # Predicted mask overlay
        axes[2].imshow(image_rgb)
        pred_overlay = np.zeros((*pred_mask.shape, 4))
        pred_overlay[pred_mask > 0] = [1, 0, 0, 0.5]  # Red with 50% transparency
        axes[2].imshow(pred_overlay)
        axes[2].set_title('Predicted Mask', fontsize=12, fontweight='bold')
        axes[2].axis('off')
        
        # Add metrics as suptitle
        fig.suptitle(f'{config_name} | {class_name} | IoU: {iou:.4f} | DICE: {dice:.4f}',
                    fontsize=14, fontweight='bold')
        
        # Adjust spacing to bring images closer
        plt.subplots_adjust(wspace=0.05, hspace=0)
        plt.tight_layout(rect=[0, 0, 1, 0.96])
        
        # Save with metrics in filename
        filename = f"{img_name}_{config_name}_{class_name}_iou_{iou:.3f}_dice_{dice:.3f}.png"
        save_path = output_path / filename
        plt.savefig(save_path, dpi=100, bbox_inches='tight')
        plt.close()
    
    def evaluate_configuration(self, sam_model_key, prompt_type, output_dir, split='val', test_mode=False, test_limit=10, save_examples=True, num_examples=20):
        """
        Evaluate a single SAM configuration.
        
        Args:
            sam_model_key: Key for SAM model ('vit_h', 'vit_l', 'vit_b')
            prompt_type: 'box' or 'point'
            output_dir: Directory to save results
            split: Dataset split ('val' or 'train')
            test_mode: If True, only process test_limit images
            test_limit: Number of images to process in test mode
            save_examples: If True, save visualization examples
            num_examples: Number of examples to save (best and worst)
            
        Returns:
            Dictionary of evaluation metrics
        """
        config = self.sam_configs[sam_model_key]
        config_name = f"{config['name']}-{prompt_type.upper()}"
        
        print(f"\n{'='*60}")
        print(f"Evaluating: {config_name}")
        if test_mode:
            print(f"TEST MODE: Processing only {test_limit} images")
        print(f"{'='*60}")
        
        # Initialize SAM model
        print(f"Loading {config['name']}...")
        sam_segmenter = SAMSegmenter(
            sam_type=config['type'],
            checkpoint_path=str(config['checkpoint'])
        )
        
        print(f"Using 🚀 \033[33mGPU\033[0m" if sam_segmenter.device == "cuda" else "💻 \033[33mCPU\033[0m")
        
        # Prepare dataset paths (merged dataset has no splits)
        if (self.dataset_root / 'images').exists():
            # Merged dataset structure (no split subdirectories)
            images_dir = self.dataset_root / 'images'
            labels_dir = self.dataset_root / 'labels'
            masks_dir = self.dataset_root / 'semantic_masks'
        else:
            # Original split structure
            images_dir = self.dataset_root / split / 'images'
            labels_dir = self.dataset_root / split / 'labels'
            masks_dir = self.dataset_root / split / 'semantic_masks'
        
        image_files = sorted(images_dir.glob('*.png'))
        
        # Limit images in test mode
        if test_mode:
            image_files = image_files[:test_limit]
        
        # Metrics storage
        all_ious = []
        all_dices = []
        per_class_ious = {i: [] for i in range(15)}
        per_class_dices = {i: [] for i in range(15)}
        inference_times = []
        
        # Diagnostic counters
        total_prompts = 0
        total_matched_prompts = 0
        total_unmatched_prompts = 0
        
        # Storage for visualization examples
        examples_data = []  # Store (iou, dice, image_rgb, gt_mask, pred_mask, class_name, img_name)
        
        # Evaluate each image
        for img_path in tqdm(image_files, desc=f"Processing {config_name}"):
            img_name = img_path.stem
            label_path = labels_dir / f"{img_name}.txt"
            mask_path = masks_dir / f"{img_name}_instance_color_RGB.png"
            
            # Load image
            image = cv2.imread(str(img_path))
            if image is None:
                continue
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            h, w = image_rgb.shape[:2]
            
            # Load GT labels
            gt_labels = self.load_ground_truth_labels(label_path, w, h)
            if not gt_labels:
                continue
            
            # Generate prompts based on type
            if prompt_type == 'box':
                prompts = [label['box_prompt'] for label in gt_labels]
            else:  # point
                prompts = [[label['point_prompt']] for label in gt_labels]
            
            # Run SAM inference
            start_time = time.time()
            try:
                if prompt_type == 'box':
                    masks = sam_segmenter.segment(image_rgb, prompts, prompt_type='box')
                else:  # point
                    masks = []
                    for point in prompts:
                        mask = sam_segmenter.segment(image_rgb, point, prompt_type='point')
                        masks.extend(mask)
            except Exception as e:
                print(f"Error processing {img_name}: {e}")
                continue
            
            inference_time = (time.time() - start_time) * 1000  # ms
            inference_times.append(inference_time)
            
            # Debug: Check if masks were generated
            if not masks:
                print(f"Warning: No masks generated for {img_name}")
                continue
            
            # Load GT RGB mask
            gt_rgb_mask = self.load_ground_truth_mask(mask_path)
            if gt_rgb_mask is None:
                print(f"Warning: No GT mask found for {img_name}")
                continue
            
            # Group masks by class for union-based evaluation (NO FILTERING)
            # The issue: DOTA and iSAID are already aligned - they're from the same images
            # We should evaluate ALL prompts, not filter them
            class_pred_masks = {}  # class_id -> list of predicted masks
            class_labels = {}      # class_id -> list of labels
            
            for i, pred_mask in enumerate(masks):
                if i >= len(gt_labels):
                    break
                
                total_prompts += 1
                label = gt_labels[i]
                class_id = label['class_id']
                
                # Ensure pred_mask is 2D
                if pred_mask is not None and len(pred_mask.shape) == 3:
                    pred_mask = pred_mask[0]
                
                # Skip empty masks
                if pred_mask is None or pred_mask.sum() == 0:
                    continue
                
                # Group by class
                if class_id not in class_pred_masks:
                    class_pred_masks[class_id] = []
                    class_labels[class_id] = []
                class_pred_masks[class_id].append(pred_mask)
                class_labels[class_id].append(label)
                total_matched_prompts += 1
            
            # Calculate metrics per class (union of instances)
            for class_id in class_pred_masks.keys():
                # Extract GT mask for this class (union of all instances)
                gt_class_mask = self.extract_class_mask(gt_rgb_mask, class_id)
                
                if gt_class_mask is None or gt_class_mask.sum() == 0:
                    continue
                
                # Create union of all predicted masks for this class
                pred_union = np.zeros_like(gt_class_mask, dtype=bool)
                for pred_mask in class_pred_masks[class_id]:
                    # Resize if needed
                    if pred_mask.shape != gt_class_mask.shape:
                        pred_mask = cv2.resize(pred_mask.astype(np.uint8), 
                                             (gt_class_mask.shape[1], gt_class_mask.shape[0]),
                                             interpolation=cv2.INTER_NEAREST).astype(bool)
                    pred_union = np.logical_or(pred_union, pred_mask.astype(bool))
                
                # Convert GT to boolean
                gt_class_mask_bool = gt_class_mask.astype(bool)
                
                try:
                    iou = calculate_mask_iou(pred_union, gt_class_mask_bool)
                    dice = calculate_mask_dice(pred_union, gt_class_mask_bool)
                    
                    all_ious.append(iou)
                    all_dices.append(dice)
                    per_class_ious[class_id].append(iou)
                    per_class_dices[class_id].append(dice)
                    
                    # Store for visualization (union masks) with prompts
                    if save_examples:
                        # Get prompts for this class
                        class_prompts = []
                        for i, label in enumerate(gt_labels):
                            if label['class_id'] == class_id:
                                if prompt_type == 'box':
                                    class_prompts.append(label['box_prompt'])
                                else:
                                    class_prompts.append(label['point_prompt'])
                        
                        examples_data.append({
                            'iou': iou,
                            'dice': dice,
                            'image_rgb': image_rgb.copy(),
                            'gt_mask': gt_class_mask_bool.copy(),
                            'pred_mask': pred_union.copy(),
                            'class_name': self.class_names[class_id],
                            'img_name': img_name,
                            'prompts': class_prompts,
                            'prompt_type': prompt_type
                        })
                except Exception as e:
                    print(f"Metric calculation error for {img_name}, class {self.class_names[class_id]}: {e}")
                    continue
        
        # Save visualization examples
        if save_examples and examples_data:
            examples_dir = Path(output_dir) / config_name / 'examples'
            
            # Sort by IoU to get best and worst examples
            examples_data.sort(key=lambda x: x['iou'], reverse=True)
            
            # Save top examples (best)
            num_best = min(num_examples // 2, len(examples_data))
            print(f"\nSaving {num_best} best examples...")
            for example in examples_data[:num_best]:
                self.save_visualization(
                    example['image_rgb'],
                    example['gt_mask'],
                    example['pred_mask'],
                    example['class_name'],
                    example['iou'],
                    example['dice'],
                    example['img_name'],
                    config_name,
                    examples_dir / 'best',
                    prompts=example.get('prompts'),
                    prompt_type=example.get('prompt_type', prompt_type)
                )
            
            # Save worst examples
            num_worst = min(num_examples // 2, len(examples_data))
            print(f"Saving {num_worst} worst examples...")
            for example in examples_data[-num_worst:]:
                self.save_visualization(
                    example['image_rgb'],
                    example['gt_mask'],
                    example['pred_mask'],
                    example['class_name'],
                    example['iou'],
                    example['dice'],
                    example['img_name'],
                    config_name,
                    examples_dir / 'worst',
                    prompts=example.get('prompts'),
                    prompt_type=example.get('prompt_type', prompt_type)
                )
        
        # Print diagnostic statistics
        match_rate = (total_matched_prompts / total_prompts * 100) if total_prompts > 0 else 0
        print(f"\n📊 Dataset Alignment Statistics:")
        print(f"   Total prompts: {total_prompts}")
        print(f"   Matched prompts: {total_matched_prompts} ({match_rate:.1f}%)")
        print(f"   Unmatched prompts: {total_unmatched_prompts} ({100-match_rate:.1f}%)")
        
        # Aggregate results
        results = {
            'config_name': config_name,
            'sam_model': config['name'],
            'prompt_type': prompt_type,
            'mean_iou': float(np.mean(all_ious)) if all_ious else 0.0,
            'mean_dice': float(np.mean(all_dices)) if all_dices else 0.0,
            'std_iou': float(np.std(all_ious)) if all_ious else 0.0,
            'std_dice': float(np.std(all_dices)) if all_dices else 0.0,
            'avg_inference_time_ms': float(np.mean(inference_times)) if inference_times else 0.0,
            'num_samples': len(all_ious),
            'total_prompts': total_prompts,
            'matched_prompts': total_matched_prompts,
            'unmatched_prompts': total_unmatched_prompts,
            'match_rate_percent': float(match_rate),
            'per_class_iou': {
                self.class_names[i]: float(np.mean(ious)) if ious else 0.0
                for i, ious in per_class_ious.items()
            },
            'per_class_dice': {
                self.class_names[i]: float(np.mean(dices)) if dices else 0.0
                for i, dices in per_class_dices.items()
            }
        }
        
        return results
    
    def run_full_benchmark(self, output_dir='results/sam_benchmark', test_mode=False, save_examples=True):
        """
        Run the complete SAM-only benchmark (6 configurations).
        
        Args:
            output_dir: Directory to save results
            test_mode: If True, run in test mode (10 images only)
            save_examples: If True, save visualization examples
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        all_results = []
        
        # Run all 6 configurations
        for sam_key in ['vit_h', 'vit_l', 'vit_b']:
            for prompt_type in ['box', 'point']:
                results = self.evaluate_configuration(sam_key, prompt_type, str(output_path), test_mode=test_mode, save_examples=save_examples)
                all_results.append(results)
                
                # Save individual result in config subfolder
                config_dir = output_path / results['config_name']
                config_dir.mkdir(parents=True, exist_ok=True)
                
                result_file = config_dir / 'metrics.json'
                with open(result_file, 'w') as f:
                    json.dump(results, f, indent=4)
                
                print(f"\n✅ {results['config_name']} complete:")
                print(f"   Mean IoU: {results['mean_iou']:.4f}")
                print(f"   Mean DICE: {results['mean_dice']:.4f}")
                print(f"   Avg Time: {results['avg_inference_time_ms']:.2f} ms")
        
        # Save summary
        summary_file = output_path / 'sam_benchmark_summary.json'
        with open(summary_file, 'w') as f:
            json.dump(all_results, f, indent=4)
        
        print(f"\n{'='*60}")
        print("SAM Benchmark Complete!")
        print(f"Results saved to: {output_dir}")
        print(f"{'='*60}")
        
        return all_results


def main():
    """Main execution function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='SAM Benchmark Evaluation')
    parser.add_argument('--test', action='store_true', help='Run in test mode (process only 10 images)')
    parser.add_argument('--dataset', type=str, default='dataset/AerialFuseCV_Refined_Merged', 
                       help='Path to refined merged dataset')
    parser.add_argument('--output', type=str, default='results/sam_evaluation_refined', 
                       help='Output directory')
    parser.add_argument('--no-examples', action='store_true', help='Disable saving visualization examples')
    args = parser.parse_args()
    
    # Initialize evaluator (excludes storage-tank [id=2] and bridge [id=8] - 0% match in refined dataset)
    evaluator = SAMBenchmarkEvaluator(args.dataset, excluded_classes=[2, 8])
    
    print(f"\n📊 Dataset: {args.dataset}")
    print(f"⚠️  Excluded classes: storage-tank, bridge (0% match rate in refined dataset)")
    print(f"✅ Evaluating 13 viable classes with perfect bbox-mask alignment\n")
    
    if args.test:
        print("\n" + "="*60)
        print("TEST MODE: Processing only 10 images per configuration")
        print("="*60 + "\n")
    
    # Run benchmark
    results = evaluator.run_full_benchmark(args.output, test_mode=args.test, save_examples=not args.no_examples)
    
    print("\n🎯 SAM Benchmark Summary:")
    print("-" * 60)
    for result in results:
        print(f"{result['config_name']:20s} | IoU: {result['mean_iou']:.4f} | DICE: {result['mean_dice']:.4f}")


if __name__ == "__main__":
    main()
