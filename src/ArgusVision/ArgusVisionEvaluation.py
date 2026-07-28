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
import time
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from tqdm import tqdm
import cv2
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from scipy.ndimage import label
from scipy.optimize import linear_sum_assignment
from datetime import datetime, timedelta

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
        
        # Load GSD mapping for visualization titles
        self.gsd_mapping = self._load_gsd_mapping()
        
    def _verify_dataset(self):
        """Verify dataset has required structure"""
        required = ['images', 'labels', 'semantic_masks']
        for folder in required:
            folder_path = self.dataset_path / folder
            if not folder_path.exists():
                raise FileNotFoundError(f"Dataset missing required folder: {folder}")
                
    def _load_gsd_mapping(self) -> Dict:
        """Load GSD (Ground Sampling Distance) mapping from JSON file."""
        gsd_path = Path('dataset/dota_gsd_mapping.json')
        if gsd_path.exists():
            with open(gsd_path, 'r') as f:
                return json.load(f)
        return {}
    
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

        # Avoid mixing restore points with test runs (or mismatched image counts)
        if restore_data and restore_data.get('total_images') != total_images:
            print(
                f"\nRestore point ignored (different image count: "
                f"{restore_data.get('total_images')} vs {total_images})"
            )
            restore_data = None

        if restore_data and max_images is not None:
            print("\nRestore point ignored (test run with --max-images)")
            restore_data = None

        if restore_data:
            print(f"\n📂 Restore point found! Resuming from image {restore_data['last_index'] + 1}/{total_images}")
            print(f"   Previous session: {restore_data['timestamp']}")
            print(f"   Images already processed: {restore_data['last_index'] + 1}")
            metrics = restore_data['metrics']
            examples_data = restore_data.get('examples_data', {} if save_visualizations else None)
            start_index = restore_data['last_index'] + 1
        else:
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
        
        # Track timing for progress display
        eval_start_time = time.time()
        
        # Process images with restore points and memory management
        try:
            for idx in range(start_index, total_images):
                img_path = images_to_process[idx]
                
                try:
                    # Calculate timing info
                    elapsed = time.time() - eval_start_time
                    images_done = idx - start_index + 1
                    images_remaining = total_images - idx - 1
                    
                    if images_done > 1:
                        avg_time_per_image = elapsed / (images_done - 1) if images_done > 1 else 0
                        eta_seconds = avg_time_per_image * images_remaining
                        elapsed_str = str(timedelta(seconds=int(elapsed)))
                        eta_str = str(timedelta(seconds=int(eta_seconds)))
                    else:
                        elapsed_str = "00:00:00"
                        eta_str = "calculating..."
                    
                    # Update progress bar with timing
                    progress_pct = (idx + 1) / total_images * 100
                    print(f"\rEvaluating: {progress_pct:5.1f}% | {idx+1:4}/{total_images} | ⏱️ {elapsed_str} | ETA: {eta_str} | {img_path.name:<20}", end='', flush=True)
                    
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
            
            # Calculate total runtime
            total_runtime = time.time() - eval_start_time
            total_runtime_str = str(timedelta(seconds=int(total_runtime)))
            avg_time_per_img = total_runtime / (total_images - start_index) if (total_images - start_index) > 0 else 0
            
            print(f"\n🏁 Evaluation complete!")
            print(f"   Total images processed: {total_images - start_index}")
            print(f"   Total runtime: {total_runtime_str} ({total_runtime/60:.2f} minutes)")
            print(f"   Avg per image: {avg_time_per_img:.2f} seconds")
            
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

            # Count false negatives for classes with GT but no predictions
            for class_id in range(15):
                if class_id not in pred_by_class and gt_counts[class_id] > 0:
                    detection_metrics_per_class[class_id] = (0, 0, gt_counts[class_id])
            
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
                        # Store METADATA ONLY (not images/masks) - saves ~48GB per restore point!
                        key = (img_name, class_id)
                        if key not in examples:
                            # Calculate F1 score for this class on this image
                            f1 = 0.0
                            if n_tp > 0:
                                img_recall = n_tp / len(gt_instances) if len(gt_instances) > 0 else 0.0
                                img_precision = n_tp / len(preds) if len(preds) > 0 else 0.0
                                f1 = 2 * (img_precision * img_recall) / (img_precision + img_recall) if (img_precision + img_recall) > 0 else 0.0
                            
                            # Get GSD for this image
                            gsd = self.gsd_mapping.get(img_name, 1.0)  # Default to 1.0 if not found
                            if gsd == 0:  # Fix for missing/zero GSD values
                                gsd = 1.0
                            
                            examples[key] = {
                                'img_path': str(img_path),  # Path to reload image later
                                'mask_path': str(mask_path),  # Path to reload GT mask
                                'img_name': img_name,
                                'class_id': class_id,
                                'class_name': CLASS_NAMES.get(class_id, f'class_{class_id}'),
                                'detection_bboxes': [],  # Just bbox coordinates
                                'ious': [],  # Just IoU values
                                'dices': [],  # Also store DICE values!
                                'n_gt': len(gt_instances),
                                'n_detected': 0,
                                'f1': f1,  # F1 score for this image+class
                                'gsd': gsd  # Ground Sampling Distance in meters
                            }
                        
                        # Store lightweight data only
                        examples[key]['detection_bboxes'].append(pred['det']['bbox'])
                        examples[key]['ious'].append(iou)
                        examples[key]['dices'].append(dice)  # Store DICE too!
                        examples[key]['n_detected'] = len(preds)
            
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
            n_tp = metrics['per_class'][class_id]['tp']
            n_fp = metrics['per_class'][class_id]['fp']
            n_fn = metrics['per_class'][class_id]['fn']
            
            if class_ious or (n_tp + n_fp + n_fn) > 0:
                # Compute detection metrics
                det_metrics = self._compute_detection_metrics(
                    n_tp,
                    n_fp,
                    n_fn
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
        print(f"{'ARGUSVISION EVALUATION SUMMARY':^80}")
        print(f"{'='*80}")
        
        # Dataset Information
        dataset_block = (
            f"\nDataset: {summary['config']['dataset']}\n"
            f"Images processed: {summary['config']['num_images']}\n"
            f"Total GT instances: {summary['config']['total_gt']}\n"
            f"Total detections: {summary['config']['num_prompts']}\n"
            f"Matched pairs (TP): {summary['config']['matched_pairs']}"
        )
        print(dataset_block)
        
        # Compute overall detection metrics (robust to per-class filtering)
        total_tp = int(summary['config']['matched_pairs'])
        total_fp = int(summary['config']['num_prompts']) - total_tp
        total_fn = int(summary['config']['total_gt']) - total_tp
        
        overall_recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
        overall_precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
        overall_f1 = 2 * (overall_precision * overall_recall) / (overall_precision + overall_recall) if (overall_precision + overall_recall) > 0 else 0.0
        
        detection_block = (
            f"\nOverall Detection Quality:\n"
            f"Recall:    {overall_recall*100:.2f}%\n"
            f"Precision: {overall_precision*100:.2f}%\n"
            f"F1 Score:  {overall_f1*100:.2f}%"
        )
        print(detection_block)
        
        print(f"\nOverall Segmentation Quality:")
        print(f"IoU:  {summary['overall']['seg_iou']*100:.2f}% ± {summary['overall']['std_seg_iou']*100:.2f}%")
        print(f"DICE: {summary['overall']['seg_dice']*100:.2f}% ± {summary['overall']['std_seg_dice']*100:.2f}%")
        
        print(f"\nTiming:")
        timing = summary['timing']
        print(f"Avg detection:     {timing['avg_detection_ms']:.2f} ms")
        print(f"Avg segmentation:  {timing['avg_segmentation_ms']:.2f} ms")
        print(f"Avg total:         {timing['avg_total_ms']:.2f} ms")
        
        print(f"\n{'='*80}")
        print(f"{'PER-CLASS PERFORMANCE':^80}")
        print(f"{'='*80}")
        print(f"{'Class':<20} {'──Detection──':^21} | {'─Segmentation─':^19} | {'──Counts──':^14}")
        print(f"{'':<20} {'Recall':>10} {'Prec':>9} {'F1':>8} | {'IoU':>8} {'DICE':>9} | {'TP':>4} {'FP':>4} {'FN':>4}")
        print("-" * 80)
        
        for class_name, m in sorted(summary['per_class'].items(), 
                                    key=lambda x: x[1]['f1'], reverse=True):
            print(f"{class_name:<20} "
                  f"{m['recall']*100:>6.2f}% "
                  f"{m['precision']*100:>6.2f}% "
                  f"{m['f1']*100:>6.2f}% | "
                  f"{m['seg_iou']*100:>7.2f}% "
                  f"{m['seg_dice']*100:>8.2f}% | "
                  f"{m['tp']:>4} "
                  f"{m['fp']:>4} "
                  f"{m['fn']:>4}")
        
        print(f"{'='*80}\n")
    
    def _save_class_visualization(self, image_rgb, class_name, all_detections, all_gt_masks,
                                  all_pred_masks, avg_iou, avg_dice, n_detected, n_gt, n_matched, recall, precision, f1, gsd, img_name, output_dir):
        """
        Save visualization showing ALL instances of ONE class in an image.
        
        Args:
            image_rgb: Original image (RGB)
            class_name: Name of the class
            all_detections: List of bounding boxes for all detected instances
            all_gt_masks: List of GT masks for all instances
            all_pred_masks: List of predicted masks for matched instances
            avg_iou: Average IoU across all instances (from evaluation)
            avg_dice: Average DICE across all instances (from evaluation)
            n_detected: Number of detections (from evaluation)
            n_gt: Number of GT instances (from evaluation)
            n_matched: Number of matched pairs / TP (from evaluation)
            recall: Detection recall (from evaluation data)
            precision: Detection precision (from evaluation data)
            f1: F1 score (from evaluation data)
            gsd: Ground Sampling Distance in meters
            img_name: Image filename
            output_dir: Output directory
        """
        fig, axes = plt.subplots(1, 3, figsize=(18, 6))
        
        # Use passed-in metrics (already calculated from evaluation data)
        # recall and precision are now parameters
        
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
        
        # New title format: Image Name | GSD = x.xx m/px | Class: {class name}
        # GSD values are typically fractional for aerial imagery; keep 2 decimals for readability.
        gsd_val = float(gsd) if gsd is not None else 0.0
        if gsd_val <= 0:
            gsd_val = 0.0
        fig.suptitle(
            f'{img_name} | GSD = {gsd_val:.2f} m/px | Class: {class_name}\n'
            f'Detected: {n_detected}/{n_gt} (TP:{n_matched}) | Recall: {recall*100:.2f}% | Precision: {precision*100:.2f}% | F1: {f1*100:.2f}%\n'
            f'Segmented: {n_matched} matched | Avg IoU: {avg_iou*100:.2f}% | Avg DICE: {avg_dice*100:.2f}%',
            fontsize=14, fontweight='bold'
        )
        
        plt.subplots_adjust(wspace=0.05, hspace=0)
        plt.tight_layout(rect=[0, 0, 1, 0.96])
        
        # New filename format: imagename_class_f1score
        filename = f"{img_name}_{class_name}_{f1*100:.2f}.png"
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
        Save 1 best and 1 worst example PER CLASS.
        Loads images from disk on-demand (not stored in restore points).
        
        Args:
            examples_data: Dict keyed by (img_name, class_id) with METADATA only
        """
        if not examples_data:
            return
        
        # Group examples by class_id
        per_class_examples = {}
        for key, data in examples_data.items():
            data['avg_iou'] = float(np.mean(data['ious'])) if data['ious'] else 0.0
            class_id = data['class_id']
            if class_id not in per_class_examples:
                per_class_examples[class_id] = []
            per_class_examples[class_id].append(data)
        
        # Sort each class's examples by IoU
        for class_id in per_class_examples:
            per_class_examples[class_id].sort(key=lambda x: x['avg_iou'], reverse=True)
        
        best_dir = self.output_dir / 'examples' / 'best'
        worst_dir = self.output_dir / 'examples' / 'worst'
        
        num_classes = len(per_class_examples)
        print(f"\n📸 Generating 1 best + 1 worst per class ({num_classes} classes)...")
        
        # Save best and worst for each class
        for class_id, examples in per_class_examples.items():
            if len(examples) > 0:
                # Best example (highest IoU)
                best_example = examples[0]
                self._generate_and_save_visualization(best_example, best_dir)
                
                # Worst example (lowest IoU) - only if different from best
                if len(examples) > 1:
                    worst_example = examples[-1]
                    self._generate_and_save_visualization(worst_example, worst_dir)
                else:
                    # Only one example - save it as worst too
                    self._generate_and_save_visualization(best_example, worst_dir)
        
        print(f"✅ Visualizations saved to: {self.output_dir / 'examples'}")
        print(f"   Best examples: {best_dir}")
        print(f"   Worst examples: {worst_dir}")
    
    def _generate_and_save_visualization(self, example_metadata: Dict, output_dir: Path):
        """
        Generate visualization by loading image from disk and re-running inference.
        
        Args:
            example_metadata: Metadata dict with paths, not actual images
            output_dir: Directory to save visualization
        """
        try:
            # Load image from disk
            img_path = Path(example_metadata['img_path'])
            image = cv2.imread(str(img_path))
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # Load GT mask from disk
            mask_path = Path(example_metadata['mask_path'])
            gt_mask = cv2.imread(str(mask_path))
            gt_mask_rgb = cv2.cvtColor(gt_mask, cv2.COLOR_BGR2RGB)
            
            # Re-run inference to get predictions
            result = self.pipeline.run_inference(image_rgb)
            
            # Extract GT instances for this class
            class_id = example_metadata['class_id']
            gt_instances = self._extract_gt_instances(gt_mask_rgb, class_id)
            
            # Filter predictions for this class only
            pred_masks_for_class = []
            detections_for_class = []
            for i, (pred_mask, pred_class_id, det) in enumerate(zip(
                result['masks'], result['classes'], result['detections']
            )):
                if pred_class_id == class_id:
                    pred_masks_for_class.append(pred_mask)
                    detections_for_class.append(det['bbox'])
            
            # Match predictions to GT (to get actual pred masks for visualization)
            matches = self._match_predictions_to_gt(pred_masks_for_class, gt_instances)
            matched_pred_masks = [pred_masks_for_class[pred_idx] for pred_idx, _, _ in matches]
            
            # Calculate  metrics from stored metadata (not from fresh inference!)
            n_matched = len(example_metadata['ious'])  # TP from evaluation
            recall = n_matched / example_metadata['n_gt'] if example_metadata['n_gt'] > 0 else 0.0
            precision = n_matched / example_metadata['n_detected'] if example_metadata['n_detected'] > 0 else 0.0
            avg_dice = float(np.mean(example_metadata['dices'])) if example_metadata['dices'] else 0.0  # From evaluation
            
            # Generate visualization with metrics
            self._save_class_visualization(
                image_rgb,
                example_metadata['class_name'],
                detections_for_class,
                gt_instances,
                matched_pred_masks,
                example_metadata['avg_iou'],  # From evaluation
                avg_dice,                      # From evaluation
                example_metadata['n_detected'],  # From evaluation
                example_metadata['n_gt'],        # From evaluation
                n_matched,                       # TP from evaluation
                recall,                          # Calculated from evaluation data
                precision,                       # Calculated from evaluation data
                example_metadata['f1'],          # F1 score from evaluation
                example_metadata['gsd'],         # GSD from mapping
                example_metadata['img_name'],
                output_dir
            )
            
        except Exception as e:
            print(f"\n⚠️  Warning: Could not generate visualization for {example_metadata['img_name']}: {e}")
