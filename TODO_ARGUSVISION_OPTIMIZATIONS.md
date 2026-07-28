# 🦉 ArgusVision TODO: Optimizations & Improvements
**Created:** Dec 27, 2025 | **Author:** ATHENA_STRATEGIST  
**Status:** For future evaluation and consideration

---

## 🏗️ **ARCHITECTURE REFACTOR** (HIGH PRIORITY)

### **📊 Centralize Metrics Calculation**
> **ISSUE**: Metrics are currently calculated in multiple places:
> - `ArgusVisionEvaluation.py` calculates some metrics inline (detection TP/FP/FN, IoU matching)
> - `src/utils/metrics.py` has metric functions (calculate_mask_iou, calculate_mask_dice)
> 
> **SOLUTION**: Move ALL metric calculations to `src/utils/metrics.py` and use evaluation scripts only for accumulation.

**Action Items:**
- [ ] Move detection metric calculation (TP/FP/FN/Recall/Precision/F1) to `metrics.py`
- [ ] Move IoU matching logic (Hungarian algorithm) to `metrics.py`
- [ ] Create unified `compute_detection_metrics()` function in `metrics.py`
- [ ] Create unified `match_predictions_to_gt()` function in `metrics.py`
- [ ] Update `ArgusVisionEvaluation.py` to only accumulate results from `metrics.py`
- [ ] Update `evaluate_yolo_obb.py` and `evaluate_yolo_vbb.py` for consistency
- [ ] Ensure all scripts use identical metric implementations

---

## 🚀 **TIER 1: IMMEDIATE OPTIMIZATIONS** (Master's Thesis Scope)

### **1.1 SAM Batched Image Encoding** ⚡
**Impact:** ~5-10% speedup on dense images

**Current State:**
- `set_image()` called once per image ✅
- But prompts processed one-by-one in loop

**Proposed Enhancement:**
```python
# In sam_segmenter.py
def segment_batch(self, image, prompts_list, prompt_types):
    """Process all prompts for one image in single forward pass"""
    self.predictor.set_image(image)  # Encode once
    # Batch decode all prompts
```

- [ ] Implement batched prompt processing in SAMSegmenter
- [ ] Test performance impact on dense images
- [ ] Validate output consistency with sequential approach

---

### **1.2 Progress Reporting Enhancement** 📈
**Current:** Basic percentage display  
**Proposed:** Add ETA calculation and throughput metrics

```python
elapsed = time.time() - start_time
eta = (elapsed / (idx+1)) * (total - idx - 1)
throughput = (idx+1) / elapsed  # images/sec
print(f"\r{idx+1}/{total} | {throughput:.2f} img/s | ETA: {eta:.0f}s", end='')
```

- [ ] Add ETA calculation to ArgusVisionEvaluation.py
- [ ] Add throughput display (images/second)
- [ ] Add timing breakdown in final summary

---

### **1.3 IoU Threshold Standardization** 🎯
**Current:** 
- ArgusVisionEvaluation.py uses 0.1
- YOLO evaluators use 0.3

**Proposed:** Standardize to 0.3 for consistency with thesis claims

- [ ] Change IoU threshold in ArgusVisionEvaluation.py from 0.1 to 0.3
- [ ] Document threshold in thesis methodology section
- [ ] Validate impact on TP/FP/FN counts

---

## 📊 **TIER 2: THESIS POLISH OPTIMIZATIONS**

### **2.1 Per-Class Prompt Strategy** 🎯
**Context:** Some classes might benefit from point prompts over box prompts

**After results analysis:**
```python
CLASS_PROMPT_CONFIG = {
    4: 'point',  # tennis-court (already high, test point)
    11: 'point', # helicopter (low IoU, might improve with centroid)
    # ... rest use 'box' (default)
}
```

- [ ] Analyze per-class SAM performance (box vs point from SAM-only benchmark)
- [ ] Identify classes with low box IoU but structured shapes
- [ ] Create optimized CLASS_PROMPT_CONFIG
- [ ] Re-run ArgusVision benchmark with optimized prompts
- [ ] Document performance delta in thesis

---

### **2.2 Confidence Threshold Tuning** 📉
**Current:** Fixed 0.25 for all classes  
**Opportunity:** Per-class thresholds based on precision/recall trade-off

```python
CONFIDENCE_THRESHOLDS = {
    0: 0.3,   # plane - balanced
    10: 0.2,  # small-vehicle - higher recall needed
    14: 0.4,  # swimming-pool - reduce FPs
}
```

- [ ] Analyze precision/recall curves per class
- [ ] Identify optimal thresholds per class
- [ ] Implement per-class confidence in YOLODetector
- [ ] Document trade-offs in thesis

---

### **2.3 Boundary F1 Metric Implementation** 📏
**Context:** Current evaluation uses IoU and DICE for segmentation quality, which measure overall pixel overlap. Boundary F1 specifically evaluates edge alignment precision.

**What is Boundary F1:**
- Measures precision and recall of predicted mask EDGES compared to GT mask EDGES
- More sensitive to boundary quality than IoU/DICE
- Common in medical imaging and instance segmentation benchmarks
- Useful for highlighting SAM's edge refinement capabilities

**Implementation Overview:**
```python
def calculate_boundary_f1(pred_mask, gt_mask, tolerance=2):
    """
    Calculate Boundary F1 score.
    
    Args:
        pred_mask: Binary predicted mask
        gt_mask: Binary ground truth mask
        tolerance: Distance threshold in pixels (default: 2)
    
    Returns:
        f1, precision, recall
    """
    # Extract boundaries using morphological operations
    pred_boundary = extract_boundary(pred_mask)  # cv2.Canny or morphology
    gt_boundary = extract_boundary(gt_mask)
    
    # Distance transform
    gt_dist = cv2.distanceTransform(~gt_boundary, cv2.DIST_L2, 3)
    pred_dist = cv2.distanceTransform(~pred_boundary, cv2.DIST_L2, 3)
    
    # Precision: % pred boundary pixels within tolerance of GT
    pred_near_gt = (gt_dist[pred_boundary > 0] <= tolerance).sum()
    precision = pred_near_gt / (pred_boundary.sum() + 1e-6)
    
    # Recall: % GT boundary pixels within tolerance of pred
    gt_near_pred = (pred_dist[gt_boundary > 0] <= tolerance).sum()
    recall = gt_near_pred / (gt_boundary.sum() + 1e-6)
    
    # F1
    f1 = 2 * (precision * recall) / (precision + recall + 1e-6)
    return f1, precision, recall
```

**Action Items:**
- [ ] Implement `calculate_boundary_f1()` in `src/utils/metrics.py`
- [ ] Add `extract_boundary()` helper using morphological operations
- [ ] Update SAM evaluation script to compute boundary F1
- [ ] Update ArgusVision evaluation to include boundary metrics
- [ ] Add boundary F1 to per-class metrics reporting
- [ ] Document boundary F1 methodology in thesis (if time permits)

**Effort Estimate:**
- Implementation: 2-3 hours
- Testing: 1 hour
- Re-evaluation: 8-10 hours (SAM + ArgusVision experiments)

**Priority:** LOW (Optional - Master's thesis has sufficient metrics)  
**Recommendation:** Add to future work section in thesis, implement post-defense or for PhD

**Related Literature:**
- Common in Cityscapes, COCO, medical imaging benchmarks
- Hausdorff distance is related metric (measures max boundary deviation)
- Particularly valuable for applications requiring precise object delineation

---

### **2.4 Visualization Quality Improvements** 🖼️
- [ ] Add legend to visualizations (GT color, Pred color)
- [ ] Add class confidence scores to detection boxes
- [ ] Improve font readability on dark backgrounds
- [ ] Add mini-map showing object location in full image

---

## 🔮 **TIER 3: PhD-RESERVED** (Protect Novelty)

> ⚠️ **DO NOT IMPLEMENT THESE FOR MASTER'S THESIS**  
> These are reserved for PhD novelty and publication value.

### **3.1 OBB-Aware SAM Prompting** ❌ RESERVED
- SAM only accepts axis-aligned boxes
- OBB→VBB conversion introduces background noise (~3-10% IoU loss estimated)
- **PhD Novelty:** Rotation-aware prompt generation
- **Publication Potential:** High (no existing SAM OBB work)

### **3.2 Dynamic Model Selection** ❌ RESERVED
- Auto-select SAM variant based on object size
- ViT-H for small objects, ViT-B for large
- **PhD Year 1:** Full 180+ configuration benchmark

### **3.3 Hybrid Prompt Strategy** ❌ RESERVED
- Box + Point combination for complex shapes
- Iterative refinement prompts
- Multi-scale prompting
- **PhD Novelty:** Significant publication potential

### **3.4 MobileSAM/FastSAM Integration** ❌ RESERVED
- Edge deployment optimization
- Real-time inference capability
- **PhD Year 2:** Edge Engine Development

### **3.5 Multi-UAV Cooperative Perception** ❌ RESERVED
- Distributed detection and segmentation
- Cross-view matching
- **PhD Year 3-4:** System integration

---

## 📋 **QUICK REFERENCE: What to Do When**

| Task | Priority | When | Scope |
|------|----------|------|-------|
| Centralize metrics | HIGH | After current eval | Master's |
| IoU threshold standardization | HIGH | Before thesis | Master's |
| Progress reporting | MEDIUM | When time permits | Master's |
| Per-class prompts | MEDIUM | After results analysis | Master's |
| Confidence tuning | LOW | If time permits | Master's |
| OBB prompting | ❌ BLOCKED | PhD Year 1 | PhD |
| Dynamic model selection | ❌ BLOCKED | PhD Year 1 | PhD |

---

## 📝 **Notes**

### Memory Optimization (Already Implemented ✅)
- Metadata-only storage in restore points (saves ~48GB per checkpoint)
- Memory cleanup every 10 images (gc + CUDA cache)
- On-demand image loading for visualizations

### Code Quality
- Type hints added throughout
- Comprehensive docstrings
- Clear separation: Core (inference) → Evaluation (benchmarking) → Inference (deployment)

---

*Updated: Dec 27, 2025 01:40 • ATHENA_STRATEGIST 🦉*
