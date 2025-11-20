from pathlib import Path
from typing import List, Optional
import traceback
import torch

from ..models.yolo_detector import YOLODetector
from ..utils.metrics import save_metrics_summary
from ..utils.data_loader import create_dataloader, get_dataset_paths

# DOTA class names (DOTAv1.yaml standard)
DOTA_CLASS_NAMES = [
    "plane", "ship", "storage-tank", "baseball-diamond", "tennis-court",
    "basketball-court", "ground-track-field", "harbor", "bridge",
    "large-vehicle", "small-vehicle", "helicopter", "roundabout",
    "soccer-ball-field", "swimming-pool",
]
NUM_DOTA = len(DOTA_CLASS_NAMES)

# COCO (ground) -> DOTA (aerial) mapping for VBB evaluation (only 4 classes map well)
COCO_TO_DOTA = {
    2: 10,  # car -> small-vehicle
    4: 0,   # airplane -> plane
    5: 9,   # bus -> large-vehicle
    7: 9,   # truck -> large-vehicle
    8: 1,   # boat -> ship
}
VBB_EVAL_CLASS_IDS = sorted(set(COCO_TO_DOTA.values()))

# YOLO model configurations (COCO-trained, VBB)
YOLO_MODELS = {
    "YOLOv8n": "yolov8n.pt",
    "YOLOv8s": "yolov8s.pt",
    "YOLOv8m": "yolov8m.pt",
    "YOLOv8l": "yolov8l.pt",
    "YOLOv8x": "yolov8x.pt",
    "YOLOv9t": "yolov9t.pt",
    "YOLOv9s": "yolov9s.pt",
    "YOLOv9m": "yolov9m.pt",
    "YOLOv9c": "yolov9c.pt",
    "YOLOv9e": "yolov9e.pt",
    "YOLOv10n": "yolov10n.pt",
    "YOLOv10s": "yolov10s.pt",
    "YOLOv10m": "yolov10m.pt",
    "YOLOv10l": "yolov10l.pt",
    "YOLOv10x": "yolov10x.pt",
    "YOLOv11n": "yolo11n.pt",
    "YOLOv11s": "yolo11s.pt",
    "YOLOv11m": "yolo11m.pt",
    "YOLOv11l": "yolo11l.pt",
    "YOLOv11x": "yolo11x.pt",
    "YOLOv12n": "yolo12n.pt",
    "YOLOv12s": "yolo12s.pt",
    "YOLOv12m": "yolo12m.pt",
    "YOLOv12l": "yolo12l.pt",
    "YOLOv12x": "yolo12x.pt",
}


def run_evaluation(
    dataset_dir: str,
    results_dir: str,
    subset_models: Optional[List[str]] = None,
    use_dataloader: bool = True,
    batch_size: int = 32,
    num_workers: Optional[int] = None
):
    """
    Run YOLO VBB model evaluation.
    """
    results_dir = Path(results_dir)
    results_dir.mkdir(parents=True, exist_ok=True)

    print("\n--- YOLO Model Evaluation on Aerial Imagery (VBB) ---")
    print("Using COCO-pretrained models as baseline")
    print(f"Dataset: {dataset_dir}")
    print(f"Results: {results_dir}")
    print(f"DataLoader: {'Enabled' if use_dataloader else 'Disabled'}")
    if use_dataloader:
        print(f"Batch size: {batch_size}, Workers: {num_workers if num_workers is not None else 'auto'}")
    print()
    device_label = "GPU" if torch.cuda.is_available() else "CPU"
    device_name = f" ({torch.cuda.get_device_name(0)})" if torch.cuda.is_available() else ""
    print(f"Using device: {device_label}{device_name}")
    
    # Get dataset paths
    image_paths, label_paths = get_dataset_paths(dataset_dir)
    print(f"Found {len(image_paths)} validation images")

    models_to_evaluate = YOLO_MODELS
    if subset_models:
        models_to_evaluate = {k: v for k, v in YOLO_MODELS.items() if k in subset_models}

    all_metrics = {}

    for model_name, weights_path in models_to_evaluate.items():
        print(f"\n--- Evaluating {model_name}")
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
                # Use DataLoader for efficient data loading
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
                # Use legacy path-based API
                metrics = detector.evaluate_dataset(
                    image_paths=image_paths,
                    label_paths=label_paths,
                    num_classes=NUM_DOTA,
                    results_dir=str(results_dir),
                    class_names=DOTA_CLASS_NAMES,
                )

            all_metrics[model_name] = metrics

            print(f"  Mean IoU : {metrics['mean_iou']*100:.2f}%")
            print(f"  Mean DICE: {metrics['mean_dice']*100:.2f}%")
            print(f"  mAP      : {metrics['map']*100:.2f}%")
            print(f"  Avg Inference Time: {metrics['avg_inference_time_ms']:.2f} ms/image")

        except Exception as e:
            print(f"Error evaluating {model_name}: {str(e)}")
            traceback.print_exc()
            continue

    save_metrics_summary(all_metrics, str(results_dir))
    print("\nEvaluation complete. Results saved to:", results_dir)


if __name__ == "__main__":
    DATASET_DIR = "dataset/DOTA_v1_YOLO_vertical_bboxes_dataset"
    RESULTS_DIR = "results/yolo_evaluation/VBB"
    
    # Run with DataLoader enabled (recommended for better performance)
    run_evaluation(DATASET_DIR, RESULTS_DIR, use_dataloader=True)
    
    # To use legacy mode without DataLoader, set use_dataloader=False:
    # run_evaluation(DATASET_DIR, RESULTS_DIR, use_dataloader=False)
