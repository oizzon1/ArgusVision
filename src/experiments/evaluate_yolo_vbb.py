"""
YOLO-VBB Evaluation Script with Detection Metrics

Evaluates YOLO-VBB models on DOTA dataset with:
- Detection metrics: Recall, Precision, F1 (IoU threshold 0.5)
- Bbox quality metrics: IoU, DICE (secondary)
- Visualization examples (10 best + 10 worst per class)

Usage:
    python src/experiments/evaluate_yolo_vbb.py
"""

from pathlib import Path
from typing import List, Optional, Dict
import traceback
import json
import sys
import numpy as np
import torch
from tqdm import tqdm

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.models.yolo_detector import YOLODetector
from src.utils.data_loader import create_dataloader, get_dataset_paths

# DOTA class names
DOTA_CLASS_NAMES = [
    "plane", "ship", "storage-tank", "baseball-diamond", "tennis-court",
    "basketball-court", "ground-track-field", "harbor", "bridge",
    "large-vehicle", "small-vehicle", "helicopter", "roundabout",
    "soccer-ball-field", "swimming-pool",
]
NUM_DOTA = len(DOTA_CLASS_NAMES)

# COCO to DOTA class mapping for VBB evaluation
# YOLO-VBB models are trained on COCO (80 classes), not DOTA
# Only these COCO classes have semantic equivalents in DOTA:
COCO_TO_DOTA = {
    8: 1,   # boat (COCO) → ship (DOTA)
    2: 10,  # car (COCO) → small-vehicle (DOTA)
    7: 9,   # truck (COCO) → large-vehicle (DOTA)
    5: 9,   # bus (COCO) → large-vehicle (DOTA)
}

# Only evaluate DOTA classes that have COCO equivalents
VBB_EVAL_CLASS_IDS = {1, 9, 10}  # ship, large-vehicle, small-vehicle

# YOLO VBB pretrained models
YOLO_VBB_MODELS = {
    # YOLOv8
    "YOLOv8n": "yolov8n.pt",
    "YOLOv8s": "yolov8s.pt",
    "YOLOv8m": "yolov8m.pt",
    "YOLOv8l": "yolov8l.pt",
    "YOLOv8x": "yolov8x.pt",
    # YOLOv9
    "YOLOv9t": "yolov9t.pt",
    "YOLOv9s": "yolov9s.pt",
    "YOLOv9m": "yolov9m.pt",
    "YOLOv9c": "yolov9c.pt",
    "YOLOv9e": "yolov9e.pt",
    # YOLOv10
    "YOLOv10n": "yolov10n.pt",
    "YOLOv10s": "yolov10s.pt",
    "YOLOv10m": "yolov10m.pt",
    "YOLOv10l": "yolov10l.pt",
    "YOLOv10x": "yolov10x.pt",
    # YOLOv11
    "YOLOv11n": "yolo11n.pt",
    "YOLOv11s": "yolo11s.pt",
    "YOLOv11m": "yolo11m.pt",
    "YOLOv11l": "yolo11l.pt",
    "YOLOv11x": "yolo11x.pt",
    # YOLOv12
    "YOLOv12n": "yolo12n.pt",
    "YOLOv12s": "yolo12s.pt",
    "YOLOv12m": "yolo12m.pt",
    "YOLOv12l": "yolo12l.pt",
    "YOLOv12x": "yolo12x.pt",
}

def print_summary(summary: Dict, model_name: str):
    """Print evaluation summary in ArgusVision format"""
    print(f"\n{'='*80}")
    print(f"{model_name} EVALUATION SUMMARY")
    print(f"{'='*80}")
    
    print(f"\nDataset: {summary['config']['dataset']}")
    print(f"Images processed: {summary['config']['num_images']}")
    print(f"Total GT instances: {summary['config']['total_gt']}")
    print(f"Total detections: {summary['config']['total_detections']}")
    print(f"Matched pairs (TP): {summary['config']['matched_pairs']}")
    
    print(f"\nOverall Detection Performance:")
    print(f"  Mean Recall:    {summary['overall']['mean_recall']*100:.2f}%")
    print(f"  Mean Precision: {summary['overall']['mean_precision']*100:.2f}%")
    print(f"  Mean F1 (mAP):  {summary['overall']['mean_f1']*100:.2f}%")
    
    print(f"\nOverall Bbox Quality (for matched pairs):")
    print(f"  Bbox-IoU:  {summary['overall']['bbox_iou']*100:.2f}% ± {summary['overall']['std_bbox_iou']*100:.2f}%")
    print(f"  Bbox-DICE: {summary['overall']['bbox_dice']*100:.2f}% ± {summary['overall']['std_bbox_dice']*100:.2f}%")
    
    print(f"\nTiming:")
    print(f"  Avg inference: {summary['timing']['avg_inference_ms']:.2f} ms")
    
    print(f"\n{'='*80}")
    print("PER-CLASS PERFORMANCE")
    print(f"{'='*80}")
    print(f"{'Class':<20} {'──Detection──':^21} | {'──Bbox Quality──':^19} | {'──Counts──':^14}")
    print(f"{'Class':<20} {'Det-Recall':>10} {'Det-Prec':>9} {'Det-F1':>6} | {'Bbox-IoU':>8} {'Bbox-DICE':>9} | {'TP':>4} {'FP':>4} {'FN':>4}")
    print("-" * 80)
    
    for class_name, m in sorted(summary['per_class'].items(), 
                                key=lambda x: x[1]['f1'], reverse=True):
        print(f"{class_name:<20} "
              f"{m['recall']*100:>6.2f}% "
              f"{m['precision']*100:>6.2f}% "
              f"{m['f1']*100:>5.1f}% | "
              f"{m['bbox_iou']*100:>7.2f}% "
              f"{m['bbox_dice']*100:>8.2f}% | "
              f"{m['tp']:>4} "
              f"{m['fp']:>4} "
              f"{m['fn']:>4}")
    
    print(f"{'='*80}\n")

def run_evaluation(
    dataset_dir: str,
    results_dir: str,
    subset_models: Optional[List[str]] = None,
    use_dataloader: bool = True,
    batch_size: int = 32,
    num_workers: Optional[int] = None
):
    """
    Run YOLO VBB model evaluation with detection metrics.
    """
    results_dir = Path(results_dir)
    results_dir.mkdir(parents=True, exist_ok=True)

    print("\n" + "="*80)
    print("YOLO-VBB EVALUATION MODE".center(80))
    print("="*80)
    print(f"\n⚙️  Configuration:")
    print(f"    Dataset:      {dataset_dir}")
    print(f"    Results:      {results_dir}")
    print(f"    DataLoader:   {'Enabled' if use_dataloader else 'Disabled'}")
    if use_dataloader:
        print(f"    Batch size:   {batch_size}")
        print(f"    Workers:      {num_workers if num_workers is not None else 'auto'}")
    
    device_label = "CUDA 🚀" if torch.cuda.is_available() else "CPU 💻"
    device_name = f" ({torch.cuda.get_device_name(0)})" if torch.cuda.is_available() else ""
    print(f"    Device:       {device_label}{device_name}")

    # Get dataset paths
    image_paths, label_paths = get_dataset_paths(dataset_dir)
    print(f"\n⚙️  Dataset loaded")
    print(f"✅ Found {len(image_paths)} validation images")

    models_to_evaluate = YOLO_VBB_MODELS
    if subset_models:
        models_to_evaluate = {k: v for k, v in YOLO_VBB_MODELS.items() if k in subset_models}

    all_metrics = {}

    for model_name, weights_path in models_to_evaluate.items():
        print(f"\n{'='*80}")
        print(f"Evaluating {model_name}")
        print(f"{'='*80}")
        
        try:
            detector = YOLODetector(
                model_name=model_name,
                weights_path=weights_path,
                conf_threshold=0.25,
                mode="vbb",
                class_map=COCO_TO_DOTA,
                allowed_class_ids=VBB_EVAL_CLASS_IDS,
                class_names=DOTA_CLASS_NAMES,
            )

            if use_dataloader:
                dataloader = create_dataloader(
                    image_paths=image_paths,
                    label_paths=label_paths,
                    mode="vbb",
                    allowed_class_ids=detector.allowed_class_ids,
                    batch_size=batch_size,
                    num_workers=num_workers,
                    shuffle=False,
                    pin_memory=True,
                )
                
                metrics = detector.evaluate_dataset(
                    dataloader=dataloader,
                    num_classes=NUM_DOTA,
                    results_dir=str(results_dir),
                    class_names=DOTA_CLASS_NAMES,
                )
            else:
                metrics = detector.evaluate_dataset(
                    image_paths=image_paths,
                    label_paths=label_paths,
                    num_classes=NUM_DOTA,
                    results_dir=str(results_dir),
                    class_names=DOTA_CLASS_NAMES,
                )

            all_metrics[model_name] = metrics
            
            # Print summary in new format
            print_summary(metrics, model_name)

        except Exception as e:
            print(f"❌ Error evaluating {model_name}: {str(e)}")
            traceback.print_exc()
            continue

    # Save combined summary
    summary_path = results_dir / "metrics_summary.json"
    with open(summary_path, "w") as f:
        json.dump(all_metrics, f, indent=2)
    
    print(f"\n✅ Evaluation complete!")
    print(f"   Results saved to: {results_dir}")

if __name__ == "__main__":
    DATASET_DIR = "dataset/DOTA_v1_YOLO_vertical_bboxes_dataset"
    RESULTS_DIR = "results/yolo_evaluation/VBB"
    
    # Run with DataLoader enabled (recommended)
    run_evaluation(DATASET_DIR, RESULTS_DIR, use_dataloader=True)
