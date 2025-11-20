# DOTA v1 Original Dataset Analysis Report

**Generated:** 2025-11-17 19:43:12

---

## Executive Summary

- **Total Instances:** 127,843
- **Number of Classes:** 15
- **Train Files:** 1,411 labels, 1,411 images
- **Val Files:** 458 labels, 458 images
- **Test Files:** 0 labels, 0 images

## 1. Dataset Structure

```
dataset/DOTA_v1/
├── train/
│   ├── images/ (1,411 files)
│   └── labels/ (1,411 files)
├── val/
│   ├── images/ (458 files)
│   └── labels/ (458 files)
└── test/
    ├── images/ (0 files)
    └── labels/ (test labels not typically provided)
```

## 2. Label Format

**Format Structure:**
```
imagesource:GoogleEarth
gsd:<ground_sample_distance>
x1 y1 x2 y2 x3 y3 x4 y4 class_name difficulty
```

**Characteristics:**
- Header: 2 lines (image source and ground sample distance)
- Coordinates: Absolute pixel coordinates (NOT normalized)
- Bounding Box: 8 values defining 4 corners (oriented bounding box)
- Class: String name (not numeric index)
- Difficulty: 0 (easy) or 1 (difficult)

## 3. Class Distribution

### 3.1 Overall Statistics

| Class ID | Class Name | Train | Val | Test | Total | % of Total | Difficult % |
|----------|------------|-------|-----|------|-------|------------|-------------|
|  0 | plane                | 8,055 | 2,531 |    0 | 10,586 |  8.28% |  2.15% |
|  1 | ship                 | 28,068 | 8,960 |    0 | 37,028 | 28.96% |  1.84% |
|  2 | storage-tank         | 5,029 | 2,888 |    0 |  7,917 |  6.19% | 25.57% |
|  3 | baseball-diamond     |   415 |  214 |    0 |    629 |  0.49% |  2.07% |
|  4 | tennis-court         | 2,367 |  760 |    0 |  3,127 |  2.45% |  3.45% |
|  5 | basketball-court     |   515 |  132 |    0 |    647 |  0.51% |  9.27% |
|  6 | ground-track-field   |   325 |  144 |    0 |    469 |  0.37% | 10.45% |
|  7 | harbor               | 5,983 | 2,090 |    0 |  8,073 |  6.31% |  1.47% |
|  8 | bridge               | 2,047 |  464 |    0 |  2,511 |  1.96% |  8.20% |
|  9 | large-vehicle        | 16,969 | 4,387 |    0 | 21,356 | 16.70% |  2.84% |
| 10 | small-vehicle        | 26,126 | 5,438 |    0 | 31,564 | 24.69% |  9.49% |
| 11 | helicopter           |   630 |   73 |    0 |    703 |  0.55% |  0.71% |
| 12 | roundabout           |   399 |  179 |    0 |    578 |  0.45% |  3.63% |
| 13 | soccer-ball-field    |   326 |  153 |    0 |    479 |  0.37% | 38.83% |
| 14 | swimming-pool        | 1,736 |  440 |    0 |  2,176 |  1.70% |  4.64% |
| **Total** | | **98,990** | **28,853** | **0** | **127,843** | **100.00%** | |

### 3.2 Difficulty Analysis

| Split | Easy | Difficult | Total | Difficult % |
|-------|------|-----------|-------|-------------|
| train | 93,496 |     5,494 | 98,990 |   5.55% |
| val   | 26,944 |     1,909 | 28,853 |   6.62% |
| test  |     0 |         0 |      0 |   0.00% |
| **Total** | **120,440** | **7,403** | **127,843** | **5.79%** |

## 4. Class Name to ID Mapping (DOTAv1.yaml)

| Class ID | YAML Name | Found in Dataset | Status |
|----------|-----------|------------------|--------|
|  0 | plane                | plane                | ✓ Found  |
|  1 | ship                 | ship                 | ✓ Found  |
|  2 | storage tank         | storage-tank         | ✓ Found  |
|  3 | baseball diamond     | baseball-diamond     | ✓ Found  |
|  4 | tennis court         | tennis-court         | ✓ Found  |
|  5 | basketball court     | basketball-court     | ✓ Found  |
|  6 | ground track field   | ground-track-field   | ✓ Found  |
|  7 | harbor               | harbor               | ✓ Found  |
|  8 | bridge               | bridge               | ✓ Found  |
|  9 | large vehicle        | large-vehicle        | ✓ Found  |
| 10 | small vehicle        | small-vehicle        | ✓ Found  |
| 11 | helicopter           | helicopter           | ✓ Found  |
| 12 | roundabout           | roundabout           | ✓ Found  |
| 13 | soccer ball field    | soccer-ball-field    | ✓ Found  |
| 14 | swimming pool        | swimming-pool        | ✓ Found  |

## 5. Conversion Requirements

To convert to Ultralytics YOLO format:

### 5.1 Label Format Changes

**Current Format:**
```
x1 y1 x2 y2 x3 y3 x4 y4 class_name difficulty
```

**Target Format (OBB):**
```
class_id x1_norm y1_norm x2_norm y2_norm x3_norm y3_norm x4_norm y4_norm
```

**Required Transformations:**
1. **Remove header lines** (imagesource, gsd)
2. **Convert class names to indices** (using mapping above)
3. **Normalize coordinates** to [0, 1] range (divide by image width/height)
4. **Reorder format**: Move class_id to beginning
5. **Optional**: Handle difficulty flag (can be discarded or used for filtering)

## 6. Summary & Observations

- Dataset contains **127,843 instances** across **15 classes**
- Most common class: **ship** (37,028 instances)
- Least common class: **ground-track-field** (469 instances)
- Difficult instances: **5.79%** of total

**Class Imbalance:**
- Imbalance ratio (max/min): **79.0:1**
- This indicates moderate class imbalance

---