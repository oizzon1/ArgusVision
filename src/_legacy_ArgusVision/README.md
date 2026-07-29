# ArgusVision Pipeline

**YOLO Detection → SAM Segmentation for Aerial Object Detection**

ArgusVision is a two-stage pipeline combining YOLO object detection with SAM segmentation for precise aerial object segmentation.

## 📁 Architecture

```
src/ArgusVision/
├── __init__.py                      # Package exports
├── ArgusVisionCore.py               # Main pipeline (dual-mode)
├── ArgusVisionInference.py          # Inference mode wrapper
├── ArgusVisionEvaluation.py         # Evaluation mode wrapper
├── config/
│   ├── class_prompt_config.py       # Per-class prompt configuration
│   └── __init__.py
└── README.md                        # This file
```

## 🚀 Quick Start

### Installation

Ensure you have the required dependencies:
```bash
pip install torch torchvision opencv-python pillow numpy tqdm ultralytics segment-anything
```

### Inference Mode (Operational Use)

```python
from src.ArgusVision import ArgusVisionInference
from src.models.yolo_detector import YOLODetector
from src.models.sam_segmenter import SAMSegmenter

# Initialize models
yolo = YOLODetector('model_checkpoints/YOLO/OBB/yolo11x-obb.pt')
sam = SAMSegmenter(model_type='vit_l', checkpoint_path='model_checkpoints/SAM/sam_vit_l_0b3195.pth')

# Create inference pipeline
pipeline = ArgusVisionInference(yolo, sam)

# Run inference on image
import cv2
image = cv2.imread('path/to/image.png')
result = pipeline.predict(image)

# Access results
masks = result['masks']           # List of binary masks
classes = result['classes']       # List of class IDs
confidences = result['confidences']  # Detection confidences
timing = result['timing']         # Inference time breakdown
```

### Evaluation Mode (Research/Benchmarking)

```python
from src.ArgusVision import ArgusVisionEvaluation

# Create evaluation pipeline
evaluator = ArgusVisionEvaluation(
    yolo_model=yolo,
    sam_model=sam,
    dataset_path='dataset/AerialFuseCV_Refined_Merged'
)

# Run evaluation
results = evaluator.evaluate(max_images=10)  # Test on 10 images

# Results saved to: results/ArgusVision_evaluation/evaluation_metrics.json
```

### Using the Evaluation Script

```bash
# Test on 10 images
python src/experiments/evaluate_ArgusVision.py --max-images 10

# Full evaluation
python src/experiments/evaluate_ArgusVision.py

# Custom dataset
python src/experiments/evaluate_ArgusVision.py --dataset path/to/dataset

# Use different models
python src/experiments/evaluate_ArgusVision.py \
    --yolo-model model_checkpoints/YOLO/OBB/yolo11x-obb.pt \
    --sam-model model_checkpoints/SAM/sam_vit_h_4b8939.pth
```

## ⚙️ Per-Class Prompt Configuration

ArgusVision supports configuring prompt types (box or point) per class:

```python
from src.ArgusVision.config.class_prompt_config import CLASS_PROMPT_CONFIG

# View current configuration
print(CLASS_PROMPT_CONFIG)
# {0: 'box', 1: 'box', ..., 12: 'box', ...}

# Modify configuration (example: use point prompts for roundabouts)
custom_config = CLASS_PROMPT_CONFIG.copy()
custom_config[12] = 'point'  # roundabout
custom_config[14] = 'point'  # swimming-pool

# Use custom configuration
pipeline = ArgusVisionInference(yolo, sam, class_prompt_config=custom_config)
```

**Rationale:**
- **Box prompts**: Better for rectangles, large objects, complex shapes
- **Point prompts**: Better for circular objects where box includes excessive background
  - Example: Roundabout with box → includes surrounding roads
  - Example: Roundabout with point → only central island

## 📊 Evaluation Metrics

### Output Structure

```json
{
  "config": {
    "dataset": "dataset/AerialFuseCV_Refined_Merged",
    "num_images": 1783,
    "num_prompts": 85243,
    "matched_pairs": 82156
  },
  "overall": {
    "mean_iou": 0.623,
    "mean_dice": 0.751,
    "std_iou": 0.187,
    "std_dice": 0.152
  },
  "per_class": {
    "plane": {
      "mean_iou": 0.478,
      "mean_dice": 0.621,
      "n_samples": 8055
    },
    ...
  },
  "timing": {
    "avg_detection_ms": 78.3,
    "avg_segmentation_ms": 954.2,
    "avg_total_ms": 1032.5
  }
}
```

### Metrics Computed

- **IoU (Intersection over Union)**: Overlap between predicted and ground truth masks
- **DICE Coefficient**: Similarity metric (2 × intersection / sum of areas)
- **Detection Time**: YOLO inference time per image
- **Segmentation Time**: SAM inference time per image
- **Total Time**: End-to-end pipeline time

## 🔧 Advanced Usage

### Custom Prompt Strategy

```python
# Define custom prompt logic
def custom_prompt_selector(class_id, bbox, confidence):
    """Custom logic to select prompt type"""
    if class_id == 12:  # roundabout
        return 'point'
    elif confidence < 0.5:  # Low confidence → try point
        return 'point'
    else:
        return 'box'

# Implement in ArgusVisionCore subclass or modify config
```

### Batch Processing

```python
pipeline = ArgusVisionInference(yolo, sam)

# Process multiple images
images = [cv2.imread(f'image_{i}.png') for i in range(10)]
results = pipeline.predict_batch(images)

# Get timing statistics
stats = pipeline.get_timing_stats()
print(f"Avg time: {stats['avg_total_ms']:.2f} ms/image")
```

## 🎯 Expected Performance

### Phase 2 Results (SAM-only with GT prompts)
- **SAM-ViT-L-BOX**: 68.6% IoU, 954ms/image

### Phase 3 Predictions (YOLO→SAM)
- **Expected**: 60-65% IoU
- **Degradation sources**:
  - YOLO detection errors (~40% missed/poorly localized)
  - OBB→VBB conversion loss (20-40% background added)
  - Cumulative error propagation

### Per-Class Expectations
- Tennis courts: 80-82% (excellent)
- Large vehicles: 68-72% (very good)
- Small vehicles: 55-60% (good)
- Planes: 45-48% (challenging)
- Helicopters: 35-38% (very challenging)

## 🔮 Future Work (TODOs)

### Mask Vectorization (Priority: High)
Convert binary masks → vector polygons for GIS integration
- Use `cv2.findContours()` or `skimage.measure.find_contours()`
- Simplify with Douglas-Peucker algorithm
- Export as GeoJSON/Shapefile

**Example implementation template provided in:**
- `ArgusVisionInference.py` (lines 90-150)
- `ArgusVisionCore.py` (lines 220-235)

### Optimization Ideas
1. **Batch SAM processing**: Process multiple prompts simultaneously
2. **Image tiling**: Handle very large images by tiling
3. **Confidence-based prompts**: Use detection confidence to select prompt type
4. **Multi-scale detection**: Improve small object detection

## 📝 Dataset Structure

ArgusVision expects datasets in the following structure:

```
dataset/AerialFuseCV_Refined_Merged/
├── images/                          # RGB images (.png)
│   ├── P0000.png
│   ├── P0001.png
│   └── ...
├── labels/                          # OBB labels (.txt)
│   ├── P0000.txt                   # Format: x1 y1 x2 y2 x3 y3 x4 y4 class difficulty
│   ├── P0001.txt
│   └── ...
└── semantic_masks/                  # RGB semantic masks (.png)
    ├── P0000_instance_color_RGB.png
    ├── P0001_instance_color_RGB.png
    └── ...
```

## 🐛 Troubleshooting

### Common Issues

**1. Model loading fails**
```
✅ Solution: Verify model checkpoint paths exist
   - YOLO: model_checkpoints/YOLO/OBB/yolo11x-obb.pt
   - SAM:  model_checkpoints/SAM/sam_vit_l_0b3195.pth
```

**2. CUDA out of memory**
```
✅ Solutions:
   - Reduce batch size
   - Use smaller SAM variant (vit_b instead of vit_l)
   - Process images sequentially
   - Use --device cpu (slower but works)
```

**3. Dataset not found**
```
✅ Solution: Verify dataset structure matches expected format
   Check: images/, labels/, semantic_masks/ directories exist
```

**4. Poor performance (low IoU)**
```
✅ Checks:
   - Verify YOLO detections are correct (check confidence threshold)
   - Verify class color mapping matches your dataset
   - Test on subset first (--max-images 10)
```

## 📧 Support

For issues, questions, or contributions:
- Check THESIS_NOTES.md for detailed methodology
- See WORK_LOG.md for development history
- Review evaluate_sam.py for SAM-only baseline comparison

---

**Last Updated**: Dec 23, 2025  
**Version**: 1.0.0  
**Phase**: 3 (Minimal ArgusVision Benchmark)
