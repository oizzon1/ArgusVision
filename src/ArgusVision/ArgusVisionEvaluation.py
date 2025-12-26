"""
ArgusVisionEvaluation: Evaluation mode wrapper for benchmarking.

This module handles dataset loading, pipeline evaluation, and metrics computation.
Designed for easy dataset switching and comprehensive performance analysis.

Features:
- Eval restore points (save progress every 50 images)
- Auto-resume from restore point on restart
- Memory management (gc + CUDA cache clearing)
- Graceful handling of errors and interrupts
"""

import json
import sys
import gc
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from tqdm import tqdm
import cv2
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from scipy.ndimage import label
from scipy.optimize import linear_sum_assignment
from datetime import datetime

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

from src.ArgusVision.ArgusVisionCore import ArgusVisionCore
from src.ArgusVision.config.class_prompt_config import CLASS_NAMES
from src.utils.metrics import calculate_mask_iou, calculate_mask_dice


class ArgusVisionEvaluation:
    """
    Evaluation mode wrapper for ArgusVision pipeline.
    
    Purpose: Research and benchmarking against ground truth
    Features:
    - Easy dataset path configuration
    - Comprehensive metrics (IoU, DICE, timing)
    - Per-class and overall performance
    - Visualization support
    - Eval restore points for crash recovery
    - Memory management
    """
    
    def __init__(self, yolo_model, sam_model, dataset_path, class_prompt_config=None, output_dir='results/ArgusVision_evaluation'):
        """
        Initialize evaluation pipeline.
        
        Args:
            yolo_model: Initialized YOLO detector
            sam_model: Initialized SAM segmenter
            dataset_path: Path to dataset (e.g., 'dataset/AerialFuseCV_Refined_Merged')
            class_prompt_config: Optional custom prompt configuration
            output_dir: Where to save evaluation results
        """
        self.pipeline = ArgusVisionCore(yolo_model, sam_model, class_prompt_config)
        self.dataset_path = Path(dataset_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Restore point configuration
        self.restore_point_dir = self.output_dir / 'restore_points'
        self.restore_point_dir.mkdir(parents=True, exist_ok=True)
        self.restore_point_interval = 50  # Save every 50 images
        self.memory_cleanup_interval = 10  # Clean memory every 10 images
        
        # Verify dataset structure
        self._verify_dataset()
        
        # Load dataset
        self.image_files = sorted((self.dataset_path / 'images').glob('*.png'))
        print(f"✅ Dataset loaded")
        print(f"✅ Found {len(self.image_files)} images")
        
        # Class color mapping for GT mask extraction (RGB to class_id)
        self.class_colors = self._load_class_colors()
        
    def _verify_dataset(self):
        """Verify dataset has required structure"""
        required = ['images', 'labels', 'semantic_masks']
        for folder in required:
            folder_path = self.dataset_path / folder
            if not folder_path.exists():
                raise FileNotFoundError(f"Dataset missing required folder: {folder}")
                
    def _load_class_colors(self) -> Dict:
        """
        Load class color mapping from iSAID color scheme.
        Maps RGB color → class_id for GT mask extraction.
        """
        return {
            (0, 127, 255): 0,      # plane
            (0, 0, 63): 1,         # ship
            (0, 63, 63): 2,        # storage-tank
            (0, 63, 0): 3,         # baseball-diamond
            (0, 63, 127): 4,       # tennis-court
            (0, 63, 191): 5,       # basketball-court
            (0, 63, 255): 6,       # ground-track-field
            (0, 100, 155): 7,      # harbor
            (0, 127, 63): 8,       # bridge
            (0, 127, 127): 9,      # large-vehicle
            (0, 0, 127): 10,       # small-vehicle
            (0, 0, 191): 11,       # helicopter
            (0, 191, 127): 12,     # roundabout
            (0, 127, 191): 13,     # soccer-ball-field
            (0, 0, 255): 14,       # swimming-pool
        }
    
    def _save_restore_point(self, metrics: Dict, last_index: int, examples_data: Optional[Dict], 
                           total_images: int, final: bool = False):
        """
        Save evaluation restore point to disk.
        
        Args:
            metrics: Current metrics accumulation
            last_index: Index of last processed image
            examples_data: Visualization examples data (with tuple keys)
            total_images: Total number of images in dataset
            final: Whether this is the final save
        """
        # Convert tuple keys to strings for JSON serialization
        examples_serializable = None
        if examples_data is not None:
            examples_serializable = {
                f"{k[0]}::{k[1]}": v for k, v in examples_data.items()
            }
        
        restore_point = {
            'last_index': last_index,
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'metrics': metrics,
            'examples_data': examples_serializable,
            'total_images': total_images
        }
        
        # Save as latest (for auto-resume)
        latest_path = self.restore_point_dir / 'eval_restore_point_latest.json'
        with open(latest_path, 'w') as f:
            json.dump(restore_point, f, indent=2, default=self._json_serializer)
        
        # Save numbered backup (unless final)
        if not final:
            backup_path = self.restore_point_dir / f'eval_restore_point_{last_index+1:04d}.json'
            with open(backup_path, 'w') as f:
                json.dump(restore_point, f, indent=2, default=self._json_serializer)
    
    def _load_latest_restore_point(self) -> Optional[Dict]:
        """
        Load the latest evaluation restore point if it exists.
        
        Returns:
            dict or None: Restore point data, or None if not found
        """
        latest_path = self.restore_point_dir / 'eval_restore_point_latest.json'
        if latest_path.exists():
            with open(latest_path, 'r') as f:
                restore_data = json.load(f)
            
            # Convert string keys back to tuples for examples_data
            if restore_data.get('examples_data') is not None:
                examples_with_tuples = {}
                for key_str, value in restore_data['examples_data'].items():
                    # Split "img_name::class_id" back to (img_name, class_id)
                    parts = key_str.split('::', 1)
                    img_name = parts[0]
                    class_id = int(parts[1])
                    examples_with_tuples[(img_name, class_id)] = value
                restore_data['examples_data'] = examples_with_tuples
            
            return restore_data
        return None
    
    def _cleanup_memory(self):
        """Force garbage collection and clear CUDA cache"""
        gc.collect()
        if TORCH_AVAILABLE and torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
    
    def _cleanup_restore_points(self):
        """Remove restore points after successful completion"""
        for rp_file in self.restore_point_dir.glob('eval_restore_point_*.json'):
            rp_file.unlink()
        print(f"🧹 Cleaned up restore points")
    
    def _json_serializer(self, obj):
        """Custom JSON serializer for numpy types"""
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.bool_):
            return bool(obj)
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
    
    def evaluate(self, max_images: Optional[int] = None, save_visualizations: bool = True) -> Dict:
        """
        Run full evaluation on dataset with restore point support and memory management.
        
        Args:
            max_images: Optional limit on number of images to process
            save_visualizations: Whether to save example visualizations (10 best, 10 worst)
            
        Returns:
            dict: Comprehensive evaluation results
        """       
        # Limit images if requested
        images_to_process = self.image_files[:max_images] if max_images else self.image_files
        total_images = len(images_to_process)
        
        # Check for existing restore point
        restore_data = self._load_latest_restore_point()
        
        if restore_data:
            print(f"\n📂 Restore point found! Resuming from image {restore_data['last_index'] + 1}/{total_images}")
            print(f"   Previous session: {restore_data['timestamp']}")
            print(f"   Images already processed: {restore_data['last_index'] + 1}")
            metrics = restore_data['metrics']
            examples_data = restore_data.get('examples_data', {} if save_visualizations else None)
            start_index = restore_data['last_index'] + 1
        else:
            print(f"\n🆕 Starting fresh evaluation")
            # Initialize metrics storage
            metrics = {
                'per_class': {class_id: {
                    'ious': [], 'dices': [],
                    'tp': 0, 'fp': 0, 'fn': 0
                } for class_id in range(15)},
                'overall': {'ious': [], 'dices': []},
                'timing': [],
                'detection_counts': {class_id: 0 for class_id in range(15)},
                'gt_counts': {class_id: 0 for class_id in range(15)},
                'matched_pairs': 0,
                'total_detections': 0,
                'total_gt': 0
            }
            examples_data = {} if save_visualizations else None
            start_index = 0
        
        # Track failed images
        failed_images = []
        
        # Process images with restore points and memory management
        try:
            for idx in range(start_index, total_images):
                img_path = images_to_process[idx]
                
                try:
                    # Update progress bar manually
                    progress_pct = (idx + 1) / total_images * 100
                    print(f"\rEvaluating: {progress_pct:5.1f}% | {idx+1:4}/{total_images} | {img_path.name:<30}", end='', flush=True)
                    
                    result = self._evaluate_single_image(img_path, store_examples=save_visualizations)
                    
                    # Accumulate metrics
                    if result:
                        for class_id, iou, dice in result['class_metrics']:
                            metrics['per_class'][class_id]['ious'].append(iou)
                            metrics['per_class'][class_id]['dices'].append(dice)
                            metrics['overall']['ious'].append(iou)
                            metrics['overall']['dices'].append(dice)
                        
                        metrics['timing'].append(result['timing'])
                        metrics['matched_pairs'] += result['matched_pairs']
                        metrics['total_detections'] += result['total_detections']
                        
                        for class_id in result['detection_counts']:
                            metrics['detection_counts'][class_id] += result['detection_counts'][class_id]
                        
                        for class_id in result['gt_counts']:
                            metrics['gt_counts'][class_id] += result['gt_counts'][class_id]
                            metrics['total_gt'] += result['gt_counts'][class_id]
                        
                        for class_id, (tp, fp, fn) in result['detection_metrics'].items():
                            metrics['per_class'][class_id]['tp'] += tp
                            metrics['per_class'][class_id]['fp'] += fp
                            metrics['per_class'][class_id]['fn'] += fn
                        
                        if save_visualizations and 'examples' in result:
                            examples_data.update(result['examples'])
                
                except Exception as e:
                    print(f"\n⚠️  Warning: Error processing {img_path.name}: {e}")
                    failed_images.append(str(img_path.name))
                    continue
                
                # Memory cleanup
                if (idx + 1) % self.memory_cleanup_interval == 0:
                    self._cleanup_memory()
                
                # Save restore point
                if (idx + 1) % self.restore_point_interval == 0:
                    self._save_restore_point(metrics, idx, examples_data, total_images)
                    print(f"\n💾 Restore point saved: {idx+1}/{total_images} images processed")
            
            print("\n")  # New line after progress
            
            # Save final restore point
            self._save_restore_point(metrics, total_images - 1, examples_data, total_images, final=True)
            
        except KeyboardInterrupt:
            print("\n\n⚠️  Evaluation interrupted by user (Ctrl+C)")
            print(f"💾 Saving restore point at image {idx}/{total_images}...")
            self._save_restore_point(metrics, idx, examples_data, total_images)
            print(f"✅ Progress saved. Run script again to resume from image {idx+1}")
            sys.exit(0)
        
        # Log failed images
        if failed_images:
            failed_log = self.output_dir / 'failed_images.txt'
            with open(failed_log, 'w') as f:
                f.write('\n'.join(failed_images))
            print(f"\n⚠️  {len(failed_images)} images failed (see {failed_log})")
        
        # Compute summary statistics
        summary = self._compute_summary(metrics, total_images)
        
        # Save results
        self._save_results(summary)
        
        # Save visualizations
        if save_visualizations and examples_data:
            self._save_visualizations(examples_data)
        
        # Print summary
        self._print_summary(summary)
        
        # Cleanup restore points on successful completion
        self._cleanup_restore_points()
        
        return summary
    
    def _evaluate_single_image(self, img_path: Path, store_examples: bool = False) -> Optional[Dict]:
        """
        Evaluate pipeline on single image with instance-level matching.
        
        Args:
            img_path: Path to image
            store_examples: Whether to store example data for visualization
            
        Returns:
            dict or None: Per-image metrics, or None if error
        """
        try:
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
            
            # Run pipeline (timing is recorded internally - only detection + segmentation)
            result = self.pipeline.run_inference(image_rgb)
            
            # Group predictions by class
            pred_by_class = {}
            for i, (pred_mask, class_id, det) in enumerate(zip(
                result['masks'], result['classes'], result['detections']
            )):
                if class_id not in pred_by_class:
                    pred_by_class[class_id] = []
                pred_by_class[class_id].append({
                    'mask': pred_mask,
                    'det': det,
                    'idx': i
                })
            
            # Compute metrics per class with instance-level matching
            class_metrics = []
            detection_counts = {i: 0 for i in range(15)}
            gt_counts = {i: 0 for i in range(15)}
            detection_metrics_per_class = {i: (0, 0, 0) for i in range(15)}  # (TP, FP, FN)
            examples = {} if store_examples else None
            
            # First pass: Extract all GT instances per class
            for class_id in range(15):
                gt_instances = self._extract_gt_instances(gt_mask_rgb, class_id)
                gt_counts[class_id] = len(gt_instances)
            
            # Second pass: Match predictions to GT
            for class_id, preds in pred_by_class.items():
                detection_counts[class_id] = len(preds)
                
                # Extract GT instances for this class
                gt_instances = self._extract_gt_instances(gt_mask_rgb, class_id)
                
                # Match predictions to GT instances using Hungarian algorithm
                pred_masks = [p['mask'] for p in preds]
                matches = self._match_predictions_to_gt(pred_masks, gt_instances)
                
                # Compute detection metrics
                n_tp = len(matches)
                n_fp = len(preds) - n_tp  # Unmatched predictions
                n_fn = len(gt_instances) - n_tp  # Unmatched GT
                detection_metrics_per_class[class_id] = (n_tp, n_fp, n_fn)
                
                # Compute segmentation metrics for matched pairs
                for pred_idx, gt_idx, iou in matches:
                    pred = preds[pred_idx]
                    gt_mask = gt_instances[gt_idx]
                    
                    dice = calculate_mask_dice(pred['mask'], gt_mask)
                    class_metrics.append((class_id, iou, dice))
                    
                    if store_examples:
                        # Group examples by (image, class) for class-level visualization
                        key = (img_name, class_id)
                        if key not in examples:
                            examples[key] = {
                                'img_name': img_name,
                                'class_id': class_id,
                                'class_name': CLASS_NAMES.get(class_id, f'class_{class_id}'),
                                'image_rgb': image_rgb.copy(),
                                'detections': [],
                                'gt_masks': [],
                                'pred_masks': [],
                                'ious': [],
                                'n_gt': len(gt_instances)
                            }
                        
                        examples[key]['detections'].append(pred['det']['bbox'])
                        examples[key]['gt_masks'].append(gt_mask.copy())
                        examples[key]['pred_masks'].append(pred['mask'].copy())
                        examples[key]['ious'].append(iou)
            
            output = {
                'class_metrics': class_metrics,
                'timing': result['timing'],
                'matched_pairs': len(class_metrics),
                'total_detections': len(result['detections']),
                'detection_counts': detection_counts,
                'gt_counts': gt_counts,
                'detection_metrics': detection_metrics_per_class
            }
            
            if store_examples and examples:
                output['examples'] = examples
                
            return output
            
        except Exception as e:
            raise  # Re-raise to be caught by caller
    
    def _extract_class_mask(self, gt_mask_rgb: np.ndarray, class_id: int) -> Optional[np.ndarray]:
        """
        Extract binary mask for specific class from RGB semantic mask.
        
        Args:
            gt_mask_rgb: RGB semantic mask (H, W, 3)
            class_id: Class ID to extract
            
        Returns:
            Binary mask (H, W) boolean, or None if class not present
        """
        # Find corresponding color for this class
        class_color = None
        for color, cid in self.class_colors.items():
            if cid == class_id:
                class_color = color
                break
        
        if class_color is None:
            return None
        
        # Extract pixels matching this color
        mask = np.all(gt_mask_rgb == class_color, axis=-1)
        
        return mask if mask.any() else None
    
    def _extract_gt_instances(self, gt_mask_rgb: np.ndarray, class_id: int) -> List[np.ndarray]:
        """
        Extract individual GT instances for a class using connected components.
        
        Args:
            gt_mask_rgb: RGB semantic mask (H, W, 3)
            class_id: Class ID to extract instances for
            
        Returns:
            List of binary masks, one per instance
        """
        # Get class mask (union of all instances)
        class_mask = self._extract_class_mask(gt_mask_rgb, class_id)
        if class_mask is None or not class_mask.any():
            return []
        
        # Find connected components (individual instances)
        labeled, num_instances = label(class_mask)
        
        instances = []
        for i in range(1, num_instances + 1):
            instance_mask = (labeled == i)
            instances.append(instance_mask)
        
        return instances
    
    def _match_predictions_to_gt(self, pred_masks: List[np.ndarray], gt_instances: List[np.ndarray]) -> List[Tuple[int, int, float]]:
        """
        Match predicted masks to GT instances using Hungarian algorithm.
        Maximizes total IoU across all matches.
        
        Args:
            pred_masks: List of predicted binary masks
            gt_instances: List of GT instance binary masks
            
        Returns:
            List of (pred_idx, gt_idx, iou) tuples for matched pairs
        """
        if len(pred_masks) == 0 or len(gt_instances) == 0:
            return []
        
        # Compute IoU matrix (predictions × GT instances)
        iou_matrix = np.zeros((len(pred_masks), len(gt_instances)))
        for i, pred_mask in enumerate(pred_masks):
            for j, gt_mask in enumerate(gt_instances):
                iou_matrix[i, j] = calculate_mask_iou(pred_mask, gt_mask)
        
        # Hungarian matching (maximize total IoU)
        # linear_sum_assignment minimizes, so negate IoU
        pred_indices, gt_indices = linear_sum_assignment(-iou_matrix)
        
        # Filter matches with meaningful IoU (> 0.1 threshold)
        matches = []
        for p_idx, g_idx in zip(pred_indices, gt_indices):
            iou = iou_matrix[p_idx, g_idx]
            if iou > 0.1:  # Only count meaningful overlaps
                matches.append((p_idx, g_idx, iou))
        
        return matches
    
    def _compute_detection_metrics(self, n_tp: int, n_fp: int, n_fn: int) -> Dict:
        """
        Compute detection performance metrics.
        
        Args:
            n_tp: Number of true positives (matched pairs)
            n_fp: Number of false positives (unmatched detections)
            n_fn: Number of false negatives (unmatched GT instances)
            
        Returns:
            dict: Detection metrics (recall, precision, f1)
        """
        recall = n_tp / (n_tp + n_fn) if (n_tp + n_fn) > 0 else 0.0
        precision = n_tp / (n_tp + n_fp) if (n_tp + n_fp) > 0 else 0.0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        
        return {
            'tp': n_tp,
            'fp': n_fp,
            'fn': n_fn,
            'recall': float(recall),
            'precision': float(precision),
            'f1': float(f1)
        }
    
    def _compute_summary(self, metrics: Dict, num_images: int) -> Dict:
        """Compute summary statistics from accumulated metrics"""
        summary = {
            'config': {
                'dataset': str(self.dataset_path),
                'num_images': num_images,
                'num_prompts': metrics['total_detections'],
                'matched_pairs': metrics['matched_pairs'],
                'total_gt': metrics['total_gt']
            },
            'overall': {
                'seg_iou': float(np.mean(metrics['overall']['ious'])) if metrics['overall']['ious'] else 0.0,
                'seg_dice': float(np.mean(metrics['overall']['dices'])) if metrics['overall']['dices'] else 0.0,
                'std_seg_iou': float(np.std(metrics['overall']['ious'])) if metrics['overall']['ious'] else 0.0,
                'std_seg_dice': float(np.std(metrics['overall']['dices'])) if metrics['overall']['dices'] else 0.0
            },
            'per_class': {},
            'timing': self.pipeline.get_timing_stats()
        }
        
        # Per-class statistics
        for class_id in range(15):
            class_ious = metrics['per_class'][class_id]['ious']
            class_dices = metrics['per_class'][class_id]['dices']
            
            if class_ious or metrics['per_class'][class_id]['tp'] > 0:
                # Compute detection metrics
                det_metrics = self._compute_detection_metrics(
                    metrics['per_class'][class_id]['tp'],
                    metrics['per_class'][class_id]['fp'],
                    metrics['per_class'][class_id]['fn']
                )
                
                summary['per_class'][CLASS_NAMES.get(class_id, f'class_{class_id}')] = {
                    'seg_iou': float(np.mean(class_ious)) if class_ious else 0.0,
                    'seg_dice': float(np.mean(class_dices)) if class_dices else 0.0,
                    'recall': det_metrics['recall'],
                    'precision': det_metrics['precision'],
                    'f1': det_metrics['f1'],
                    'tp': det_metrics['tp'],
                    'fp': det_metrics['fp'],
                    'fn': det_metrics['fn'],
                    'n_samples': len(class_ious),
                    'n_detections': metrics['detection_counts'][class_id],
                    'n_gt': metrics['gt_counts'][class_id]
                }
        
        return summary
    
    def _save_results(self, summary: Dict):
        """Save evaluation results to JSON"""
        output_file = self.output_dir / 'evaluation_metrics.json'
        with open(output_file, 'w') as f:
            json.dump(summary, f, indent=2)
        print(f"\n✅ Results saved to: {output_file}")
    
    def _print_summary(self, summary: Dict):
        """Print evaluation summary to console"""
        print(f"\n{'='*80}")
        print("ARGUSVISION EVALUATION SUMMARY")
        print(f"{'='*80}")
        
        print(f"\nDataset: {summary['config']['dataset']}")
        print(f"Images processed: {summary['config']['num_images']}")
        print(f"Total GT instances: {summary['config']['total_gt']}")
        print(f"Total detections: {summary['config']['num_prompts']}")
        print(f"Matched pairs (TP): {summary['config']['matched_pairs']}")
        
        print(f"\nOverall Segmentation Quality (for matched pairs):")
        print(f"  Seg-IoU:  {summary['overall']['seg_iou']*100:.2f}% ± {summary['overall']['std_seg_iou']*100:.2f}%")
        print(f"  Seg-DICE: {summary['overall']['seg_dice']*100:.2f}% ± {summary['overall']['std_seg_dice']*100:.2f}%")
        
        print(f"\nTiming:")
        timing = summary['timing']
        print(f"  Avg detection:     {timing['avg_detection_ms']:.2f} ms")
        print(f"  Avg segmentation:  {timing['avg_segmentation_ms']:.2f} ms")
        print(f"  Avg total:         {timing['avg_total_ms']:.2f} ms")
        
        print(f"\n{'='*80}")
        print("PER-CLASS PERFORMANCE")
        print(f"{'='*80}")
        print(f"{'Class':<20} {'──Detection──':^21} | {'─Segmentation─':^19} | {'──Counts──':^14}")
        print(f"{'Class':<20} {'Det-Recall':>10} {'Det-Prec':>9} {'Det-F1':>6} | {'Seg-IoU':>8} {'Seg-DICE':>9} | {'TP':>4} {'FP':>4} {'FN':>4}")
        print("-" * 80)
        
        for class_name, m in sorted(summary['per_class'].items(), 
                                    key=lambda x: x[1]['f1'], reverse=True):
            print(f"{class_name:<20} "
                  f"{m['recall']*100:>6.2f}% "
                  f"{m['precision']*100:>6.2f}% "
                  f"{m['f1']:>5.3f} | "
                  f"{m['seg_iou']*100:>7.2f}% "
                  f"{m['seg_dice']*100:>8.2f}% | "
                  f"{m['tp']:>4} "
                  f"{m['fp']:>4} "
                  f"{m['fn']:>4}")
        
        print(f"{'='*80}\n")
    
    def _save_class_visualization(self, image_rgb, class_name, all_detections, all_gt_masks,
                                  all_pred_masks, avg_iou, n_detected, n_gt, img_name, output_dir):
        """
        Save visualization showing ALL instances of ONE class in an image.
        
        Args:
            image_rgb: Original image (RGB)
            class_name: Name of the class
            all_detections: List of bounding boxes for all detected instances
            all_gt_masks: List of GT masks for all instances
            all_pred_masks: List of predicted masks for matched instances
            avg_iou: Average IoU across all instances
            n_detected: Number of detections
            n_gt: Number of GT instances
            img_name: Image filename
            output_dir: Output directory
        """
        fig, axes = plt.subplots(1, 3, figsize=(18, 6))
        
        # Calculate metrics
        recall = n_detected / n_gt if n_gt > 0 else 0.0
        precision = len(all_pred_masks) / n_detected if n_detected > 0 else 0.0
    def _save_class_visualization(self, image_rgb, class_name, all_detections, all_gt_masks,
                                  all_pred_masks, avg_iou, n_detected, n_gt, img_name, output_dir):
        """
        Save visualization showing ALL instances of ONE class in an image.
        
        Args:
            image_rgb: Original image (RGB)
            class_name: Name of the class
            all_detections: List of bounding boxes for all detected instances
            all_gt_masks: List of GT masks for all instances
            all_pred_masks: List of predicted masks for matched instances
            avg_iou: Average IoU across all instances
            n_detected: Number of detections
            n_gt: Number of GT instances
            img_name: Image filename
            output_dir: Output directory
        """
        fig, axes = plt.subplots(1, 3, figsize=(18, 6))
        
        # Calculate metrics
        recall = n_detected / n_gt if n_gt > 0 else 0.0
        precision = len(all_pred_masks) / n_detected if n_detected > 0 else 0.0
        
        # Panel 1: Original + all detection bboxes
        axes[0].imshow(image_rgb)
        for bbox in all_detections:
            if len(bbox) == 8:  # OBB
                x_coords = [bbox[i] for i in range(0, 8, 2)]
                y_coords = [bbox[i] for i in range(1, 8, 2)]
                x_coords.append(x_coords[0])
                y_coords.append(y_coords[0])
                axes[0].plot(x_coords, y_coords, 'c-', linewidth=2)
            else:  # VBB
                x1, y1, x2, y2 = bbox
                rect = Rectangle((x1, y1), x2-x1, y2-y1,
                               linewidth=2, edgecolor='cyan', facecolor='none')
                axes[0].add_patch(rect)
        axes[0].set_title(f'Detections ({n_detected})', fontsize=12, fontweight='bold')
        axes[0].axis('off')
        
        # Panel 2: All GT masks (green, stacked)
        axes[1].imshow(image_rgb)
        combined_gt = np.zeros((*image_rgb.shape[:2], 4))
        for gt_mask in all_gt_masks:
            combined_gt[gt_mask] = [0, 1, 0, 0.5]  # Green, 50% transparency
        axes[1].imshow(combined_gt)
        axes[1].set_title('Ground Truth Masks', fontsize=12, fontweight='bold')
        axes[1].axis('off')
        
        # Panel 3: All prediction masks (red, stacked)
        axes[2].imshow(image_rgb)
        combined_pred = np.zeros((*image_rgb.shape[:2], 4))
        for pred_mask in all_pred_masks:
            combined_pred[pred_mask] = [1, 0, 0, 0.5]  # Red, 50% transparency
        axes[2].imshow(combined_pred)
        axes[2].set_title('Segmented Masks', fontsize=12, fontweight='bold')
        axes[2].axis('off')
        
        # Calculate average DICE
        avg_dice = 0.0
        if all_pred_masks and all_gt_masks:
            dices = []
            for pred_mask, gt_mask in zip(all_pred_masks, all_gt_masks):
                dices.append(calculate_mask_dice(pred_mask, gt_mask))
            avg_dice = float(np.mean(dices)) if dices else 0.0
        
        # Title with metrics - separated by detection and segmentation
        fig.suptitle(
            f'{img_name} | {class_name}\n'
            f'Detected: {n_detected}/{n_gt} | Recall: {recall*100:.2f}% | Precision: {precision*100:.2f}%\n'
            f'Segmented: {len(all_pred_masks)} | Avg IoU: {avg_iou*100:.2f}% | Avg DICE: {avg_dice*100:.2f}%',
            fontsize=14, fontweight='bold'
        )
        
        plt.subplots_adjust(wspace=0.05, hspace=0)
        plt.tight_layout(rect=[0, 0, 1, 0.96])
        
        # Save
        filename = f"{img_name}_{class_name}_avgIoU_{avg_iou:.3f}_n{n_detected}.png"
        save_path = Path(output_dir) / filename
        save_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(save_path, dpi=100, bbox_inches='tight')
        plt.close()
    
    def _save_visualization(self, image_rgb, gt_mask, pred_mask, bbox, class_name, 
                           iou, dice, img_name, output_dir):
        """
        Save side-by-side visualization of detection, GT mask, and predicted mask.
        
        Args:
            image_rgb: Original image (RGB)
            gt_mask: Ground truth binary mask
            pred_mask: Predicted binary mask
            bbox: Bounding box used for detection
            class_name: Name of the class
            iou: IoU score
            dice: DICE score
            img_name: Image filename
            output_dir: Output directory for visualization
        """
        fig, axes = plt.subplots(1, 3, figsize=(18, 6))
        
        # Original image with detection bbox
        axes[0].imshow(image_rgb)
        # Draw bounding box (OBB - 8 coords or VBB - 4 coords)
        if len(bbox) == 8:
            # OBB: draw polygon
            x_coords = [bbox[i] for i in range(0, 8, 2)]
            y_coords = [bbox[i] for i in range(1, 8, 2)]
            x_coords.append(x_coords[0])  # Close polygon
            y_coords.append(y_coords[0])
            axes[0].plot(x_coords, y_coords, 'c-', linewidth=2)
        else:
            # VBB: draw rectangle
            x1, y1, x2, y2 = bbox
            rect = Rectangle((x1, y1), x2-x1, y2-y1, 
                           linewidth=2, edgecolor='cyan', facecolor='none')
            axes[0].add_patch(rect)
        axes[0].set_title('Detection (YOLO)', fontsize=12, fontweight='bold')
        axes[0].axis('off')
        
        # GT mask overlay
        axes[1].imshow(image_rgb)
        gt_overlay = np.zeros((*gt_mask.shape, 4))
        gt_overlay[gt_mask > 0] = [0, 1, 0, 0.5]  # Green with 50% transparency
        axes[1].imshow(gt_overlay)
        axes[1].set_title('Ground Truth', fontsize=12, fontweight='bold')
        axes[1].axis('off')
        
        # Predicted mask overlay
        axes[2].imshow(image_rgb)
        pred_overlay = np.zeros((*pred_mask.shape, 4))
        pred_overlay[pred_mask > 0] = [1, 0, 0, 0.5]  # Red with 50% transparency
        axes[2].imshow(pred_overlay)
        axes[2].set_title('Prediction (SAM)', fontsize=12, fontweight='bold')
        axes[2].axis('off')
        
        # Add metrics as suptitle
        fig.suptitle(f'ArgusVision | {class_name} | IoU: {iou:.4f} | DICE: {dice:.4f}',
                    fontsize=14, fontweight='bold')
        
        plt.subplots_adjust(wspace=0.05, hspace=0)
        plt.tight_layout(rect=[0, 0, 1, 0.96])
        
        # Save
        filename = f"{img_name}_{class_name}_iou_{iou:.3f}.png"
        save_path = Path(output_dir) / filename
        save_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(save_path, dpi=100, bbox_inches='tight')
        plt.close()
    
    def _save_visualizations(self, examples_data):
        """
        Save 10 best and 10 worst class-level examples.
        
        Args:
            examples_data: Dict keyed by (img_name, class_id) with class-level data
        """
        if not examples_data:
            return
        
        # Convert dict to list and compute average IoU for each
        examples_list = []
        for key, data in examples_data.items():
            data['avg_iou'] = float(np.mean(data['ious'])) if data['ious'] else 0.0
            data['n_detected'] = len(data['detections'])
            examples_list.append(data)
        
        # Sort by average IoU
        examples_list.sort(key=lambda x: x['avg_iou'], reverse=True)
        
        # Save top 10 (best)
        num_best = min(10, len(examples_list))
        if num_best > 0:
            print(f"\n📸 Saving {num_best} best class-level examples...")
            best_dir = self.output_dir / 'examples' / 'best'
            for example in examples_list[:num_best]:
                self._save_class_visualization(
                    example['image_rgb'],
                    example['class_name'],
                    example['detections'],
                    example['gt_masks'],
                    example['pred_masks'],
                    example['avg_iou'],
                    example['n_detected'],
                    example['n_gt'],
                    example['img_name'],
                    best_dir
                )
        
        # Save bottom 10 (worst)
        num_worst = min(10, len(examples_list))
        if num_worst > 0:
            print(f"📸 Saving {num_worst} worst class-level examples...")
            worst_dir = self.output_dir / 'examples' / 'worst'
            for example in examples_list[-num_worst:]:
                self._save_class_visualization(
                    example['image_rgb'],
                    example['class_name'],
                    example['detections'],
                    example['gt_masks'],
                    example['pred_masks'],
                    example['avg_iou'],
                    example['n_detected'],
                    example['n_gt'],
                    example['img_name'],
                    worst_dir
                )
        
        print(f"✅ Visualizations saved to: {self.output_dir / 'examples'}")
