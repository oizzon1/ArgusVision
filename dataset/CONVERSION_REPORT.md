# DOTA v1 Dataset Conversion Report

**Date:** 2025-11-17 19:59  
**Task:** Convert DOTA v1 original format to YOLO-compatible formats

---

## Conversion Summary

### ✅ Conversions Completed

1. **OBB (Oriented Bounding Boxes)** - `dataset/DOTA_v1_YOLO_oriented_bboxes_dataset/`
2. **VBB (Vertical/Axis-Aligned Bounding Boxes)** - `dataset/DOTA_v1_YOLO_vertical_bboxes_dataset/`

### Dataset Statistics

- **Total Files Converted:** 1,869 (1,411 train + 458 val)
- **Total Instances:** 127,843 objects
- **Classes:** 15 DOTA v1 categories

---

## Format Transformations

### Source Format (Original DOTA v1)
```
imagesource:GoogleEarth
gsd:<value>
x1 y1 x2 y2 x3 y3 x4 y4 class_name difficulty
```

**Characteristics:**
- 2-line header (metadata)
- Absolute pixel coordinates
- String class names
- Difficulty flag (0=easy, 1=difficult)
- 8 coordinates (4 corners)

### Target Format: OBB
```
class_id x1_norm y1_norm x2_norm y2_norm x3_norm y3_norm x4_norm y4_norm
```

**Transformations Applied:**
1. ✅ Removed header lines
2. ✅ Converted class names → class IDs (0-14)
3. ✅ Normalized coordinates to [0, 1] range
4. ✅ Moved class_id to beginning
5. ✅ Preserved oriented bounding box structure (8 coords)
6. ✅ Discarded difficulty flag

### Target Format: VBB
```
class_id cx_norm cy_norm w_norm h_norm
```

**Transformations Applied:**
1. ✅ Removed header lines
2. ✅ Converted class names → class IDs (0-14)
3. ✅ Calculated axis-aligned bounding box from 4 corners
4. ✅ Converted to center-x, center-y, width, height format
5. ✅ Normalized coordinates to [0, 1] range
6. ✅ Discarded difficulty flag

---

## Class Mapping (DOTAv1.yaml)

| ID | Class Name          | Train | Val   | Total  | % Total |
|----|---------------------|-------|-------|--------|---------|
| 0  | plane               | 8,055 | 2,531 | 10,586 | 8.28%   |
| 1  | ship                | 28,068| 8,960 | 37,028 | 28.96%  |
| 2  | storage tank        | 5,029 | 2,888 | 7,917  | 6.19%   |
| 3  | baseball diamond    | 415   | 214   | 629    | 0.49%   |
| 4  | tennis court        | 2,367 | 760   | 3,127  | 2.45%   |
| 5  | basketball court    | 515   | 132   | 647    | 0.51%   |
| 6  | ground track field  | 325   | 144   | 469    | 0.37%   |
| 7  | harbor              | 5,983 | 2,090 | 8,073  | 6.31%   |
| 8  | bridge              | 2,047 | 464   | 2,511  | 1.96%   |
| 9  | large vehicle       | 16,969| 4,387 | 21,356 | 16.70%  |
| 10 | small vehicle       | 26,126| 5,438 | 31,564 | 24.69%  |
| 11 | helicopter          | 630   | 73    | 703    | 0.55%   |
| 12 | roundabout          | 399   | 179   | 578    | 0.45%   |
| 13 | soccer ball field   | 326   | 153   | 479    | 0.37%   |
| 14 | swimming pool       | 1,736 | 440   | 2,176  | 1.70%   |

**Total:** 98,990 train + 28,853 val = **127,843 instances**

---

## Dataset Structure

### OBB Dataset
```
dataset/DOTA_v1_YOLO_oriented_bboxes_dataset/
├── images/
│   ├── train/ (1,411 images)
│   └── val/ (458 images)
├── labels/
│   ├── train/ (1,411 .txt files)
│   └── val/ (458 .txt files)
└── dataset/DOTA_v1_YOLO_oriented_bboxes_dataset.yaml
```

### VBB Dataset
```
dataset/DOTA_v1_YOLO_vertical_bboxes_dataset/
├── images/
│   ├── train/ (1,411 images)
│   └── val/ (458 images)
├── labels/
│   ├── train/ (1,411 .txt files)
│   └── val/ (458 .txt files)
└── dataset/DOTA_v1_YOLO_vertical_bboxes_dataset.yaml
```

---

## Configuration Files

### OBB YAML
- **Path:** `dataset/DOTA_v1_YOLO_oriented_bboxes_dataset.yaml`
- **Usage:** YOLOv8/v11 OBB detection models

### VBB YAML
- **Path:** `dataset/DOTA_v1_YOLO_vertical_bboxes_dataset.yaml`
- **Usage:** YOLOv8/v9/v10/v11/v12 standard detection models

---

## Verification

### Sample Verification (P0000.txt)

**OBB Format (first 3 lines):**
```
0 0.710452 0.437659 0.738323 0.433479 0.745290 0.448564 0.723871 0.454744
9 0.889032 0.616321 0.899097 0.619593 0.897548 0.621956 0.886968 0.618321
9 0.821935 0.755725 0.824516 0.756270 0.819355 0.764086 0.816516 0.763177
```
✅ Format: class_id + 8 normalized coordinates  
✅ Class IDs: 0 (plane), 9 (large-vehicle)

**VBB Format (first 3 lines):**
```
0 0.727871 0.444111 0.034839 0.021265
9 0.893032 0.619138 0.012129 0.005634
9 0.820516 0.759905 0.008000 0.008361
```
✅ Format: class_id cx cy w h (all normalized)  
✅ Axis-aligned boxes correctly calculated

---

## Usage Examples

### Training with OBB
```python
from ultralytics import YOLO

# Load OBB model
model = YOLO('yolo11n-obb.pt')

# Train
results = model.train(
    data='dataset/DOTA_v1_YOLO_oriented_bboxes_dataset.yaml',
    epochs=100,
    imgsz=1024,
    batch=8
)
```

### Training with VBB
```python
from ultralytics import YOLO

# Load standard detection model
model = YOLO('yolo11n.pt')

# Train
results = model.train(
    data='dataset/DOTA_v1_YOLO_vertical_bboxes_dataset.yaml',
    epochs=100,
    imgsz=1024,
    batch=8
)
```

---

## Files Generated

1. `convert_dota_to_yolo_obb.py` - OBB conversion script
2. `convert_dota_to_yolo_vbb.py` - VBB conversion script
3. `check_conversion_progress.py` - Progress monitoring script
4. `dataset/DOTA_v1/DATASET_ANALYSIS_REPORT.md` - Original dataset analysis
5. `dataset/CONVERSION_REPORT.md` - This report

---

## Next Steps

1. ✅ Datasets ready for training
2. ✅ YAML configuration files created
3. ⏭️ Update code to use new dataset paths
4. ⏭️ Run test predictions to verify format compatibility
5. ⏭️ Begin model training experiments

---

**Status:** ✅ **CONVERSION COMPLETE**  
**Quality:** ✅ **ALL VALIDATIONS PASSED**  
**Ready for:** YOLOv8/v9/v10/v11/v12 Training
