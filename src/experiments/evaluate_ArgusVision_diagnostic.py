"""
ArgusVision Diagnostic Evaluation Script
========================================

This script extends the standard ArgusVision evaluation with:
1. SAM failure logging and analysis
2. Enhanced 2x2 visualizations showing the full pipeline:
   - OBB Detections (YOLO outputs)
   - VBB Prompts (converted for SAM)
   - Segmented Masks (SAM outputs)
   - Ground Truth Masks

Usage:
    python src/experiments/evaluate_ArgusVision_diagnostic.py --dataset dataset/AerialFuseCV_Refined/val

"""

import argparse
import sys
from pathlib import Path
import json
import numpy as np
import cv2
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Polygon

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.models.yolo_detector import YOLODetector
from src.models.sam_segmenter import SAMSegmenter
from src.ArgusVision.ArgusVisionCore import ArgusVisionCore
from src.ArgusVision.config.class_prompt_config import CLASS_NAMES
from scipy.ndimage import label as connected_components


class DiagnosticEvaluator:
    """
    Diagnostic evaluator that tracks SAM failures and generates detailed visualizations.
    """
    
    def __init__(self, yolo_model, sam_model, dataset_path, output_dir='results/ArgusVision_diagnostic'):
        self.pipeline = ArgusVisionCore(yolo_model, sam_model)
        self.dataset_path = Path(dataset_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Diagnostic tracking
        self.sam_failure_log = []
        self.sam_failures_by_class = {i: 0 for i in range(15)}
        self.sam_successes_by_class = {i: 0 for i in range(15)}
        
        # Class color mapping (same as ArgusVisionEvaluation)
        self.class_colors = {
            (0, 127, 255): 0, (0, 0, 63): 1, (0, 63, 63): 2, (0, 63, 0): 3,
            (0, 63, 127): 4, (0, 63, 191): 5, (0, 63, 255): 6, (0, 100, 155): 7,
            (0, 127, 63): 8, (0, 127, 127): 9, (0, 0, 127): 10, (0, 0, 191): 11,
            (0, 191, 127): 12, (0, 127, 191): 13, (0, 0, 255): 14
        }
    
    def _extract_gt_instances(self, gt_mask_rgb, class_id):
        """Extract GT instances for a class using connected components."""
        # Find color for this class
        class_color = None
        for color, cid in self.class_colors.items():
            if cid == class_id:
                class_color = color
                break
        
        if class_color is None:
            return []
        
        # Extract class mask
        mask = np.all(gt_mask_rgb == class_color, axis=-1)
        if not mask.any():
            return []
        
        # Find connected components
        labeled, num_instances = connected_components(mask)
        
        instances = []
        for i in range(1, num_instances + 1):
            instance_mask = (labeled == i)
            instances.append(instance_mask)
        
        return instances
    
    def _analyze_sam_failure(self, img_name, det, class_id, image_shape):
        """Analyze a SAM failure and log diagnostic information."""
        bbox = det['bbox']
        
        # Calculate bbox dimensions
        if len(bbox) == 8:  # OBB
            x_coords = [bbox[i] for i in range(0, 8, 2)]
            y_coords = [bbox[i] for i in range(1, 8, 2)]
            width = max(x_coords) - min(x_coords)
            height = max(y_coords) - min(y_coords)
            x_min, x_max = min(x_coords), max(x_coords)
            y_min, y_max = min(y_coords), max(y_coords)
        else:  # VBB
            x_min, y_min, x_max, y_max = bbox
            width = x_max - x_min
            height = y_max - y_min
        
        # Check for issues
        issues = []
        if width <= 0 or height <= 0:
            issues.append("degenerate_bbox")
        if width < 5 or height < 5:
            issues.append("very_small")
        if x_min < 0 or y_min < 0:
            issues.append("negative_coords")
        if x_max > image_shape[1] or y_max > image_shape[0]:
            issues.append("out_of_bounds")
        if width < 10 or height < 10:
            issues.append("small_object")
        
        failure_info = {
            'image': img_name,
            'class_id': class_id,
            'class_name': CLASS_NAMES.get(class_id, f'class_{class_id}'),
            'bbox': bbox,
            'width': float(width),
            'height': float(height),
            'area': float(width * height),
            'issues': issues,
            'confidence': det.get('confidence', 0.0)
        }
        
        self.sam_failure_log.append(failure_info)
        self.sam_failures_by_class[class_id] += 1
        
        return failure_info
    
    def _save_diagnostic_visualization(self, image_rgb, detections, gt_mask_rgb, 
                                      pred_masks, class_id, class_name, img_name, 
                                      n_gt, output_dir):
        """
        Save 2x2 diagnostic visualization:
        Top: OBB Detections | VBB Prompts
        Bottom: Segmented Masks | Ground Truth
        """
        fig, axes = plt.subplots(2, 2, figsize=(16, 16))
        
        # Filter for this class only
        class_detections = [(d, i) for i, d in enumerate(detections) if d['class_id'] == class_id]
        class_pred_masks = [pred_masks[i] for d, i in class_detections if pred_masks[i] is not None and pred_masks[i].sum() > 0]
        
        n_detected = len(class_detections)
        n_segmented = len(class_pred_masks)
        
        # Top-left: OBB Detections
        axes[0, 0].imshow(image_rgb)
        for det, _ in class_detections:
            bbox = det['bbox']
            if len(bbox) == 8:  # OBB
                x_coords = [bbox[i] for i in range(0, 8, 2)]
                y_coords = [bbox[i] for i in range(1, 8, 2)]
                x_coords.append(x_coords[0])
                y_coords.append(y_coords[0])
                axes[0, 0].plot(x_coords, y_coords, 'c-', linewidth=2)
            else:  # VBB
                x1, y1, x2, y2 = bbox
                rect = Rectangle((x1, y1), x2-x1, y2-y1,
                               linewidth=2, edgecolor='cyan', facecolor='none')
                axes[0, 0].add_patch(rect)
        axes[0, 0].set_title(f'OBB Detections ({n_detected})', fontsize=14, fontweight='bold')
        axes[0, 0].axis('off')
        
        # Top-right: VBB Segmentation Prompts
        axes[0, 1].imshow(image_rgb)
        for det, _ in class_detections:
            bbox = det['bbox']
            # Convert OBB to VBB
            if len(bbox) == 8:
                x_coords = [bbox[i] for i in range(0, 8, 2)]
                y_coords = [bbox[i] for i in range(1, 8, 2)]
                x_min, x_max = min(x_coords), max(x_coords)
                y_min, y_max = min(y_coords), max(y_coords)
            else:
                x_min, y_min, x_max, y_max = bbox
            
            rect = Rectangle((x_min, y_min), x_max-x_min, y_max-y_min,
                           linewidth=2, edgecolor='yellow', facecolor='none')
            axes[0, 1].add_patch(rect)
        axes[0, 1].set_title(f'VBB Segmentation Prompts ({n_detected})', fontsize=14, fontweight='bold')
        axes[0, 1].axis('off')
        
        # Bottom-left: Segmented Masks
        axes[1, 0].imshow(image_rgb)
        combined_pred = np.zeros((*image_rgb.shape[:2], 4))
        for pred_mask in class_pred_masks:
            if pred_mask.shape != image_rgb.shape[:2]:
                pred_mask = cv2.resize(pred_mask.astype(np.uint8), 
                                     (image_rgb.shape[1], image_rgb.shape[0]),
                                     interpolation=cv2.INTER_NEAREST).astype(bool)
            combined_pred[pred_mask] = [1, 0, 0, 0.5]  # Red
        axes[1, 0].imshow(combined_pred)
        axes[1, 0].set_title(f'Segmented Masks ({n_segmented})', fontsize=14, fontweight='bold')
        axes[1, 0].axis('off')
        
        # Bottom-right: Ground Truth Masks
        axes[1, 1].imshow(image_rgb)
        gt_instances = self._extract_gt_instances(gt_mask_rgb, class_id)
        combined_gt = np.zeros((*image_rgb.shape[:2], 4))
        for gt_mask in gt_instances:
            combined_gt[gt_mask] = [0, 1, 0, 0.5]  # Green
        axes[1, 1].imshow(combined_gt)
        axes[1, 1].set_title(f'Ground Truth Masks ({n_gt})', fontsize=14, fontweight='bold')
        axes[1, 1].axis('off')
        
        # Super title with comprehensive info
        sam_failures = n_detected - n_segmented
        fig.suptitle(
            f'{img_name} | Class: {class_name} | Detected: {n_detected}/{n_gt} GT\n'
            f'SAM Segmented: {n_segmented}/{n_detected} | SAM Failures: {sam_failures}',
            fontsize=16, fontweight='bold'
        )
        
        plt.tight_layout(rect=[0, 0, 1, 0.96])
        
        # Save
        filename = f"{img_name}_{class_name}_diagnostic.png"
        save_path = Path(output_dir) / filename
        save_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(save_path, dpi=100, bbox_inches='tight')
        plt.close()
    
    def evaluate_single_image(self, img_path, save_viz=True):
        """Evaluate single image with diagnostic tracking."""
        # Load image
        image = cv2.imread(str(img_path))
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # Load GT mask
        img_name = img_path.stem
        mask_path = self.dataset_path / 'semantic_masks' / f'{img_name}_instance_color_RGB.png'
        gt_mask = cv2.imread(str(mask_path))
        if gt_mask is None:
            return None
        gt_mask_rgb = cv2.cvtColor(gt_mask, cv2.COLOR_BGR2RGB)
        
        # Run pipeline
        result = self.pipeline.run_inference(image_rgb)
        
        # Track SAM failures
        for i, (pred_mask, class_id, det) in enumerate(zip(
            result['masks'], result['classes'], result['detections']
        )):
            if pred_mask is None or not isinstance(pred_mask, np.ndarray) or pred_mask.sum() == 0:
                # SAM failure!
                self._analyze_sam_failure(img_name, det, class_id, image_rgb.shape)
            else:
                self.sam_successes_by_class[class_id] += 1
        
        # Generate diagnostic visualizations for classes with failures
        if save_viz:
            # Group by class
            classes_present = set(result['classes'])
            for class_id in classes_present:
                # Get GT count
                gt_instances = self._extract_gt_instances(gt_mask_rgb, class_id)
                n_gt = len(gt_instances)
                
                if n_gt > 0:  # Only save if GT exists
                    self._save_diagnostic_visualization(
                        image_rgb,
                        result['detections'],
                        gt_mask_rgb,
                        result['masks'],
                        class_id,
                        CLASS_NAMES.get(class_id, f'class_{class_id}'),
                        img_name,
                        n_gt,
                        self.output_dir / 'visualizations'
                    )
        
        return result
    
    def save_diagnostic_report(self):
        """Save comprehensive diagnostic report."""
        # Calculate statistics
        total_detections = sum(self.sam_successes_by_class.values()) + sum(self.sam_failures_by_class.values())
        total_failures = sum(self.sam_failures_by_class.values())
        total_successes = sum(self.sam_successes_by_class.values())
        
        success_rate = (total_successes / total_detections * 100) if total_detections > 0 else 0
        
        report = {
            'summary': {
                'total_detections': total_detections,
                'sam_successes': total_successes,
                'sam_failures': total_failures,
                'success_rate_percent': success_rate
            },
            'per_class_success_rate': {},
            'failure_log': self.sam_failure_log,
            'failure_analysis': self._analyze_failures()
        }
        
        # Per-class success rates
        for class_id in range(15):
            successes = self.sam_successes_by_class[class_id]
            failures = self.sam_failures_by_class[class_id]
            total = successes + failures
            
            if total > 0:
                report['per_class_success_rate'][CLASS_NAMES.get(class_id, f'class_{class_id}')] = {
                    'successes': successes,
                    'failures': failures,
                    'total': total,
                    'success_rate_percent': (successes / total * 100)
                }
        
        # Save report
        report_path = self.output_dir / 'sam_diagnostic_report.json'
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n✅ Diagnostic report saved to: {report_path}")
        
        # Print summary
        self._print_summary(report)
        
        return report
    
    def _analyze_failures(self):
        """Analyze common failure patterns."""
        if not self.sam_failure_log:
            return {}
        
        analysis = {
            'by_issue_type': {},
            'size_distribution': {
                'tiny': 0,  # < 10x10
                'small': 0,  # 10-50
                'medium': 0,  # 50-100
                'large': 0   # > 100
            },
            'by_class': {}
        }
        
        # Count issues
        for failure in self.sam_failure_log:
            for issue in failure['issues']:
                analysis['by_issue_type'][issue] = analysis['by_issue_type'].get(issue, 0) + 1
            
            # Size distribution
            area = failure['area']
            if area < 100:
                analysis['size_distribution']['tiny'] += 1
            elif area < 2500:
                analysis['size_distribution']['small'] += 1
            elif area < 10000:
                analysis['size_distribution']['medium'] += 1
            else:
                analysis['size_distribution']['large'] += 1
            
            # By class
            class_name = failure['class_name']
            if class_name not in analysis['by_class']:
                analysis['by_class'][class_name] = []
            analysis['by_class'][class_name].append(failure)
        
        return analysis
    
    def _print_summary(self, report):
        """Print diagnostic summary to console."""
        print(f"\n{'='*80}")
        print(f"{'SAM DIAGNOSTIC REPORT':^80}")
        print(f"{'='*80}")
        
        summary = report['summary']
        print(f"\nOverall SAM Performance:")
        print(f"  Total detections: {summary['total_detections']}")
        print(f"  SAM successes:    {summary['sam_successes']} ({summary['success_rate_percent']:.1f}%)")
        print(f"  SAM failures:     {summary['sam_failures']} ({100-summary['success_rate_percent']:.1f}%)")
        
        print(f"\nPer-Class SAM Success Rate:")
        print(f"{'Class':<20} {'Successes':>10} {'Failures':>10} {'Total':>10} {'Rate':>10}")
        print("-" * 70)
        
        for class_name, stats in sorted(report['per_class_success_rate'].items(),
                                       key=lambda x: x[1]['success_rate_percent']):
            print(f"{class_name:<20} {stats['successes']:>10} {stats['failures']:>10} "
                  f"{stats['total']:>10} {stats['success_rate_percent']:>9.1f}%")
        
        # Failure analysis
        if 'failure_analysis' in report:
            analysis = report['failure_analysis']
            
            if analysis.get('by_issue_type'):
                print(f"\nFailure Reasons:")
                for issue, count in sorted(analysis['by_issue_type'].items(), 
                                          key=lambda x: x[1], reverse=True):
                    pct = (count / summary['sam_failures'] * 100) if summary['sam_failures'] > 0 else 0
                    print(f"  {issue:<25} {count:>5} ({pct:>5.1f}%)")
            
            if analysis.get('size_distribution'):
                print(f"\nFailure Size Distribution:")
                size_dist = analysis['size_distribution']
                for size_cat, count in size_dist.items():
                    pct = (count / summary['sam_failures'] * 100) if summary['sam_failures'] > 0 else 0
                    print(f"  {size_cat:<10} {count:>5} ({pct:>5.1f}%)")
        
        print(f"{'='*80}\n")


def main():
    parser = argparse.ArgumentParser(description='ArgusVision Diagnostic Evaluation')
    parser.add_argument('--dataset', type=str, default='dataset/AerialFuseCV_Refined/val',
                       help='Path to validation dataset')
    parser.add_argument('--output', type=str, default='results/ArgusVision_diagnostic',
                       help='Output directory')
    parser.add_argument('--max-images', type=int, default=None,
                       help='Limit number of images to process')
    parser.add_argument('--image-name', type=str, default=None,
                       help='Process a specific image by name (e.g., P0654)')
    parser.add_argument('--yolo-model', type=str, default='yolo11x-obb.pt',
                       help='YOLO model checkpoint filename (in model_checkpoints/YOLO/OBB/)')
    parser.add_argument('--sam-model', type=str, default='model_checkpoints/SAM/sam_vit_l_0b3195.pth',
                       help='SAM model checkpoint')
    parser.add_argument('--sam-type', type=str, default='vit_l',
                       choices=['vit_h', 'vit_l', 'vit_b'],
                       help='SAM model type')
    
    args = parser.parse_args()
    
    # Initialize models
    print("Loading models...")
    yolo = YOLODetector(
        model_name='yolov11x-obb',
        weights_path=args.yolo_model,
        conf_threshold=0.25,
        mode='obb'
    )
    sam = SAMSegmenter(sam_type=args.sam_type, checkpoint_path=args.sam_model)
    
    # Initialize evaluator
    evaluator = DiagnosticEvaluator(yolo, sam, args.dataset, args.output)
    
    # Get image files
    dataset_path = Path(args.dataset)
    
    if args.image_name:
        # Process specific image
        image_file = dataset_path / 'images' / f'{args.image_name}.png'
        if not image_file.exists():
            print(f"❌ Error: Image {args.image_name}.png not found in {dataset_path / 'images'}")
            sys.exit(1)
        image_files = [image_file]
        print(f"\nProcessing specific image: {args.image_name}")
    else:
        # Process multiple images
        image_files = sorted((dataset_path / 'images').glob('*.png'))
        
        if args.max_images:
            image_files = image_files[:args.max_images]
        
        print(f"\nProcessing {len(image_files)} images...")
    
    # Process images
    for i, img_path in enumerate(image_files, 1):
        print(f"\rProgress: {i}/{len(image_files)} ({i/len(image_files)*100:.1f}%)", end='', flush=True)
        evaluator.evaluate_single_image(img_path, save_viz=True)
    
    print("\n")
    
    # Save report
    evaluator.save_diagnostic_report()
    
    print(f"\n✅ Diagnostic evaluation complete!")
    print(f"   Visualizations: {evaluator.output_dir / 'visualizations'}")
    print(f"   Report: {evaluator.output_dir / 'sam_diagnostic_report.json'}")


if __name__ == "__main__":
    main()
