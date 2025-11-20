# THESIS NOTES - YOLO→SAM Pipeline for Aerial Object Detection

**Project:** Integration of YOLO Detection with SAM Segmentation for Enhanced Aerial Imagery Analysis  
**Dataset:** DOTA v1 (Dataset for Object detection in Aerial images)  
**Timeline:** 10 weeks (Start: Nov 17, 2025 → Target: End of January 2026)  
**Last Updated:** 2025-11-17 21:05

---

## 1. EXECUTIVE SUMMARY

### Research Objective
Develop and evaluate a two-stage pipeline combining YOLO object detection with Segment Anything Model (SAM) for improved object segmentation in aerial imagery, focusing on the DOTA v1 dataset with 15 object categories.

### Key Innovation
Using YOLO detections as prompts for SAM to achieve precise object segmentation, addressing the challenge that **detection bounding boxes alone are insufficient** for applications requiring precise object boundaries (e.g., area calculation, change detection, GIS integration).

### Current Status (Week 1)
- ✅ Dataset converted to standard YOLO formats (OBB + VBB)
- ✅ Baseline YOLO evaluation in progress (7/10 OBB models complete)
- 🎯 Next: Complete baseline, then design YOLO→SAM integration

---

## 2. DATASET & PREPARATION

### 2.1 DOTA v1 Dataset Overview

**Source:** Original DOTA v1 dataset  
**Total Images:** 2,806 aerial images (2,848 × 2,848 pixels average)  
**Total Instances:** 188,282 objects across 15 categories  

**Split Distribution:**
- Training: 1,411 images (137,923 instances)
- Validation: 458 images (28,853 instances)
- Test: 937 images (21,506 instances)

### 2.2 AerialFuseCV Dataset Overview

**Source:** Fusion of DOTA v1 (detection) + iSAID (segmentation)  
**Purpose:** Multi-task dataset with detection boxes + semantic masks  
**Total Images:** 1,869 aerial images  
**Total Classes:** 15 (aligned with DOTA v1)

**Split Distribution:**
- Training: 1,411 images (1,411 masks)
- Validation: 458 images (458 masks)

**Class Coverage (Masks with Class Present):**
| Class Name | Train | Val | Total | Coverage % |
|------------|-------|-----|-------|------------|
| small-vehicle | 1,099 | 339 | 1,438 | 76.94% |
| large-vehicle | 770 | 227 | 997 | 53.34% |
| harbor | 339 | 111 | 450 | 24.08% |
| ship | 434 | 150 | 584 | 31.25% |
| plane | 199 | 72 | 271 | 14.50% |
| tennis-court | 310 | 94 | 404 | 21.62% |
| swimming-pool | 261 | 77 | 338 | 18.08% |
| storage-tank | 245 | 71 | 316 | 16.91% |
| ground-track-field | 201 | 76 | 277 | 14.82% |
| soccer-ball-field | 185 | 72 | 257 | 13.75% |
| roundabout | 182 | 64 | 246 | 13.16% |
| baseball-diamond | 146 | 57 | 203 | 10.86% |
| basketball-court | 120 | 46 | 166 | 8.88% |
| helicopter | 39 | 15 | 54 | 2.89% |
| bridge | 226 | 80 | 306 | 16.37% |

**Semantic Mask Format:**
- RGB color-coded masks (one color per class)
- Background: (0, 0, 0) black
- 15 unique class colors (see ANALYTICAL_LOG.md for full mapping)

**Dataset Structure:**
```
dataset/AerialFuseCV/
├── train/
│   ├── images/ (1,411 files)
│   ├── labels/ (1,411 YOLO OBB files)
│   └── semantic_masks/ (1,411 RGB masks)
├── val/
│   ├── images/ (458 files)
│   ├── labels/ (458 YOLO OBB files)
│   └── semantic_masks/ (458 RGB masks)
└── ANALYTICAL_LOG.md (dataset report)
```

**Key Observations:**
- **High vehicle coverage:** 77% train images contain small-vehicles
- **Rare classes:** Helicopter (2.89%), basketball-court (8.88%)
- **Balanced representation:** Most classes in 10-30% coverage range
- **Semantic masks enable:** Pixel-level evaluation, area calculation, precise boundary analysis

### 2.3 Dataset Conversion (DOTA v1 → YOLO Formats)

**Class Distribution:**
| Class ID | Class Name | Train | Val | Total | % of Dataset |
|----------|------------|-------|-----|-------|--------------|
| 0 | plane | 8,055 | 2,531 | 10,586 | 8.28% |
| 1 | ship | 28,068 | 8,960 | 37,028 | 28.96% |
| 2 | storage-tank | 5,029 | 2,888 | 7,917 | 6.19% |
| 3 | baseball-diamond | 415 | 214 | 629 | 0.49% |
| 4 | tennis-court | 2,367 | 760 | 3,127 | 2.45% |
| 5 | basketball-court | 515 | 132 | 647 | 0.51% |
| 6 | ground-track-field | 325 | 144 | 469 | 0.37% |
| 7 | harbor | 5,983 | 2,090 | 8,073 | 6.31% |
| 8 | bridge | 2,047 | 464 | 2,511 | 1.96% |
| 9 | large-vehicle | 16,969 | 4,387 | 21,356 | 16.70% |
| 10 | small-vehicle | 26,126 | 5,438 | 31,564 | 24.69% |
| 11 | helicopter | 630 | 73 | 703 | 0.55% |
| 12 | roundabout | 399 | 179 | 578 | 0.45% |
| 13 | soccer-ball-field | 326 | 153 | 479 | 0.37% |
| 14 | swimming-pool | 1,736 | 440 | 2,176 | 1.70% |

**Key Observations:**
- **Highly imbalanced:** Ships (29%) and small-vehicles (25%) dominate
- **Rare classes:** baseball-diamond, ground-track-field, roundabout, soccer-ball-field (<0.5% each)
- **Small objects:** swimming-pools, helicopters, small-vehicles (challenging for detection)

### 2.4 Dataset Conversion (DOTA v1 → YOLO Formats)

**Formats Created:**
1. **OBB (Oriented Bounding Boxes):** `dataset/DOTA_v1_YOLO_oriented_bboxes_dataset/`
   - Format: `class_id x1 y1 x2 y2 x3 y3 x4 y4` (normalized 0-1)
   - Preserves rotation information
   - Use: YOLOv8/v11-OBB models

2. **VBB (Vertical/Axis-Aligned Boxes):** `dataset/DOTA_v1_YOLO_vertical_bboxes_dataset/`
   - Format: `class_id cx cy w h` (normalized 0-1)
   - Standard YOLO format
   - Use: YOLOv8/v9/v10/v11/v12 models

**Conversion Statistics:**
- Files converted: 1,869 per format (1,411 train + 458 val)
- Total instances: 127,843 per format
- Quality: ✅ All validations passed

---

## 3. BASELINE EXPERIMENTS (YOLO-only)

### 3.1 OBB Models Evaluated (YOLOv8 Series - COMPLETE)

| Model | mAP | Mean IoU | Mean DICE | Inference (ms) | Status |
|-------|-----|----------|-----------|----------------|--------|
| YOLOv8n-obb | 51.8% | 57.3% | 64.7% | 53.7 | ✅ Complete |
| YOLOv8s-obb | ? | ? | ? | ? | 🔄 Running |
| YOLOv8m-obb | ? | ? | ? | ? | 🔄 Running |
| YOLOv8l-obb | **59.4%** | 61.5% | 68.5% | 70.5 | ✅ Complete |
| YOLOv8x-obb | **59.7%** | 61.9% | 69.1% | 81.2 | ✅ Complete |

### 3.2 Per-Class Performance (YOLOv8-OBB)

**Strong Performance (>70% AP):**
- ✅ tennis-court: **93-94% AP** (excellent - simple rectangular shape)
- ✅ large-vehicle: **80-83% AP** (good - common, distinctive)
- ✅ plane: **66-78% AP** (good - large, distinctive shape)
- ✅ harbor: **70-79% AP** (good - context helps)
- ✅ ship: **65-70% AP** (good - common class)

**Moderate Performance (50-70% AP):**
- ⚠️ baseball-diamond: 56-73% AP
- ⚠️ storage-tank: 46-55% AP
- ⚠️ basketball-court: 54-62% AP
- ⚠️ ground-track-field: 50-61% AP
- ⚠️ small-vehicle: 55-62% AP
- ⚠️ helicopter: 37-55% AP

**Poor Performance (<50% AP):**
- ❌ **swimming-pool: 0-0.4% AP** (catastrophic failure!)
- ❌ bridge: 25-35% AP (very poor)
- ❌ roundabout: 32-43% AP (poor)
- ❌ soccer-ball-field: 48-50% AP (mediocre)

### 3.3 Key Findings

**Overall Assessment:**
- ✅ **mAP 52-60%:** Acceptable baseline for pretrained models
- ✅ **IoU 57-62%:** Reasonable localization quality
- ⚠️ **High variance:** 0-94% AP across classes (huge spread!)

**Problem Analysis:**

1. **Swimming Pool Failure (0% AP):**
   - Smallest objects in dataset (avg 2% of image area)
   - Complex backgrounds (gardens, buildings)
   - Limited training examples (2,176 total)
   - Irregular shapes (rectangular, kidney-shaped, etc.)
   - **Hypothesis:** Below detection threshold for pretrained models

2. **Bridge Challenges (25-35% AP):**
   - Long, thin structures (high aspect ratio)
   - Partial occlusion by clouds/shadows
   - Variable appearances (suspension, arch, beam)
   - **Hypothesis:** Aspect ratio mismatch with anchor boxes

3. **Small Object Issues:**
   - Small-vehicles: 55-62% AP (better than expected due to quantity)
   - Helicopters: 37-55% AP (rare + small)
   - **Pattern:** Size matters more than we'd like

**Success Factors:**
- Simple geometric shapes (tennis courts, baseball diamonds)
- Large objects (planes, large-vehicles)
- High frequency (ships, vehicles)
- Distinctive context (harbors near water)

---

## 4. FINETUNING DECISION: NOT RECOMMENDED ❌

### 4.1 Rationale

**Decision:** Use pretrained models as-is, do NOT finetune

**Reasons:**

1. **Time Constraint (Critical)**
   - Finetuning requires: 1-2 weeks minimum
   - Available time: 10 weeks total for entire thesis
   - Better use: Invest in YOLO→SAM integration (main contribution)

2. **Acceptable Baseline**
   - 52-60% mAP is respectable for zero-shot transfer
   - Good enough to demonstrate detection → segmentation improvement
   - SAM will refine boundaries regardless of YOLO precision

3. **Diminishing Returns**
   - Going from 60% → 70% mAP requires significant effort
   - Improvements may not translate to better segmentation
   - Focus should be on **integration**, not optimization

4. **Thesis Narrative Advantage**
   - Pretrained models show realistic challenges
   - Demonstrates SAM's ability to compensate for imperfect detections
   - More impressive to show improvement from modest baseline

5. **Class-Specific Issues Unlikely to Fix**
   - Swimming pool failure likely fundamental (too small)
   - Bridge issues related to shape, not training data
   - Finetuning might help marginally but not resolve

### 4.2 Alternative Strategy

**Use performance variation as research dimension:**
- Test how SAM performs with different quality YOLO prompts
- Compare: high-confidence (tennis-courts) vs low-confidence (bridges) detections
- Show SAM's robustness to noisy/imperfect prompts

**Thesis angle:**
> "While pretrained OBB models show variable performance (52-60% mAP), particularly struggling with small/complex objects, our YOLO→SAM pipeline demonstrates that **foundation models can compensate for imperfect detections** through refined segmentation, achieving [X%] improvement in mask IoU..."

---

## 5. YOLO→SAM INTEGRATION (To be implemented)

### 5.1 Architecture Design

**Pipeline Overview:**
```
Input Image
    ↓
YOLO Detection (OBB/VBB)
    ↓
Bounding Box Prompts
    ↓
SAM Segmentation
    ↓
Refined Object Masks
    ↓
Evaluation & Metrics
```

**Key Design Decisions (To be finalized):**

1. **Prompt Strategy:**
   - [ ] Option A: Box prompts (entire detection box)
   - [ ] Option B: Point prompts (box center)
   - [ ] Option C: Hybrid (box + center point)
   - [ ] Option D: Multi-point (corners + center)

2. **SAM Variant:**
   - [ ] Original SAM (highest quality, slow)
   - [ ] Mobile-SAM (faster, slightly lower quality)
   - [ ] Fast-SAM (fastest, good for real-time)

3. **Confidence Threshold:**
   - [ ] Use YOLO defaults (0.25)
   - [ ] Optimize per-class thresholds
   - [ ] Study impact on SAM quality

4. **Batch Processing:**
   - [ ] Image-level batching
   - [ ] Detection-level batching
   - [ ] Async processing for speed

### 5.2 Implementation Plan

**Week 2-3: Core Integration (40-50 hours)**

**Phase 1: Basic Pipeline (Week 2, Days 1-3)**
- [ ] Create `src/pipeline/yolo_sam_pipeline.py`
- [ ] Implement YOLO → SAM prompt conversion
- [ ] Basic box prompt strategy
- [ ] Single-image processing
- [ ] Initial testing on 10 validation images

**Phase 2: Optimization (Week 2, Days 4-5)**
- [ ] Add batch processing
- [ ] Implement multiple prompt strategies
- [ ] GPU optimization
- [ ] Memory management for large images

**Phase 3: Evaluation Framework (Week 3, Days 1-3)**
- [ ] Mask-based IoU/DICE metrics
- [ ] Per-class performance tracking
- [ ] Comparison: YOLO boxes vs YOLO+SAM masks
- [ ] Visualization tools

**Phase 4: Experimentation (Week 3, Days 4-5)**
- [ ] Test different SAM variants
- [ ] Prompt strategy comparison
- [ ] Confidence threshold optimization
- [ ] Speed vs quality analysis

### 5.3 Metrics to Implement

**Segmentation Metrics:**
1. **Mask IoU:** Intersection-over-Union for masks
2. **Mask DICE:** DICE coefficient for masks
3. **Boundary F1:** Precision on mask boundaries
4. **AP_mask:** Average Precision for segmentation

**Comparative Metrics:**
1. **ΔIoU:** Improvement from boxes to masks
2. **Quality Score:** Mask coherence/smoothness
3. **Processing Time:** End-to-end latency

### 5.4 Expected Challenges

1. **Small Objects:**
   - Swimming pools may remain challenging
   - SAM struggles with objects <32×32 pixels
   - **Strategy:** Test multiple prompt points

2. **Memory:**
   - SAM is memory-intensive
   - Large aerial images (2848×2848)
   - **Strategy:** Tile-based processing or downsampling

3. **Speed:**
   - SAM inference: ~100-300ms per prompt
   - 458 validation images × avg 280 objects = ~128,000 prompts
   - **Strategy:** Batch processing, Fast-SAM variant

4. **Prompt Quality:**
   - Bad YOLO boxes → bad SAM masks
   - Low confidence detections problematic
   - **Strategy:** Confidence threshold tuning

---

## 6. EXPERIMENTAL PLAN (Weeks 4-5)

### 6.1 Experiment Matrix

**Experiment 1: Baseline Comparison**
- YOLO-only (boxes) vs YOLO+SAM (masks)
- All 15 classes
- Validation set (458 images)
- **Hypothesis:** SAM improves IoU by 10-20%

**Experiment 2: Prompt Strategy**
- Box vs Point vs Hybrid prompts
- Subset of classes (5 representative)
- **Hypothesis:** Hybrid prompts best balance speed/quality

**Experiment 3: SAM Variant Comparison**
- SAM vs Mobile-SAM vs Fast-SAM
- Quality vs speed tradeoff
- **Hypothesis:** Mobile-SAM optimal for production

**Experiment 4: YOLO Model Impact**
- Best (YOLOv8x) vs Worst (YOLOv8n) as prompt sources
- Does better detection = better segmentation?
- **Hypothesis:** Quality plateaus beyond 55% mAP

**Experiment 5: Per-Class Analysis**
- Focus on problem classes (swimming-pool, bridge)
- Can SAM salvage poor detections?
- **Hypothesis:** SAM helps most on medium-confidence detections

### 6.2 Data Collection

**For each experiment, record:**
- [ ] Per-class mask IoU/DICE
- [ ] Overall mAP (mask-based)
- [ ] Inference time breakdown (YOLO + SAM)
- [ ] Memory usage
- [ ] Visualization samples (10 per class)

---

## 7. THESIS OUTLINE

### Chapter 1: Introduction (8-10 pages)

**1.1 Background & Motivation**
- Growth of aerial imagery (drones, satellites)
- Need for precise object segmentation (not just detection)
- Applications: urban planning, disaster response, agriculture
- Problem: Traditional detection insufficient

**1.2 Research Objectives**
- Primary: Develop YOLO→SAM pipeline for aerial objects
- Secondary: Evaluate different integration strategies
- Tertiary: Benchmark on DOTA v1 dataset

**1.3 Contributions**
1. Novel integration of YOLO and SAM for aerial imagery
2. Comprehensive evaluation on 15 object categories
3. Analysis of prompt strategies and their impact
4. Open-source implementation and reproducible results

**1.4 Thesis Structure**
- Brief overview of remaining chapters

### Chapter 2: Literature Review (15-20 pages)

**2.1 Object Detection in Aerial Imagery**
- Traditional methods (Faster R-CNN, etc.)
- YOLO family evolution (v3 → v12)
- Oriented bounding boxes (OBB) vs standard boxes
- Challenges: scale variation, small objects, rotation

**2.2 Semantic Segmentation**
- FCN, U-Net, Mask R-CNN progression
- Instance vs semantic segmentation
- Challenges in aerial imagery

**2.3 Foundation Models**
- Vision transformers (ViT)
- CLIP and vision-language models
- Segment Anything Model (SAM)
  - Architecture (image encoder + prompt encoder + mask decoder)
  - Training approach (1B masks)
  - Zero-shot capabilities
  - Limitations

**2.4 Two-Stage Approaches**
- Detection-then-segmentation pipelines
- Prompt engineering for foundation models
- Related work in medical imaging, robotics

**2.5 DOTA Dataset**
- Overview and statistics
- Previous benchmarks
- State-of-the-art results

### Chapter 3: Methodology (20-25 pages)

**3.1 Problem Formulation**
- Mathematical notation
- Input/output definitions
- Evaluation metrics

**3.2 Dataset**
- DOTA v1 detailed description
- Preprocessing and conversion
- Train/val/test splits
- Class distribution analysis

**3.3 YOLO Detection Module**
- Architecture overview (YOLOv8/v11-OBB)
- Model selection rationale
- Hyperparameters
- Training details (pretrained models)

**3.4 SAM Segmentation Module**
- SAM architecture details
- Prompt encoding
- Mask decoding
- Post-processing

**3.5 YOLO→SAM Integration**
- Pipeline architecture
- Prompt conversion strategies
- Batch processing approach
- Implementation details

**3.6 Evaluation Protocol**
- Metrics: IoU, DICE, mAP, F1
- Comparison baselines
- Statistical significance testing
- Visualization methods

**3.7 Implementation**
- Software stack (Python, PyTorch, Ultralytics)
- Hardware setup
- Code structure
- Reproducibility measures

### Chapter 4: Experiments & Results (25-30 pages)

**4.1 Baseline Results**
- YOLO-only performance (this section partially complete!)
- Per-class analysis
- Failure cases

**4.2 YOLO+SAM Results**
- Overall improvement metrics
- Per-class improvements
- Speed analysis
- Memory usage

**4.3 Ablation Studies**
- Prompt strategy impact
- SAM variant comparison
- YOLO quality vs segmentation quality
- Confidence threshold effects

**4.4 Qualitative Analysis**
- Visual comparisons
- Success cases
- Failure cases
- Edge cases

**4.5 Comparison with State-of-the-Art**
- vs Mask R-CNN
- vs other segmentation methods
- Discussion of tradeoffs

### Chapter 5: Discussion & Conclusion (8-10 pages)

**5.1 Key Findings**
- Summary of results
- Hypothesis validation
- Unexpected discoveries

**5.2 Advantages**
- Benefits of two-stage approach
- SAM's zero-shot capability
- Scalability

**5.3 Limitations**
- Small object challenges
- Computational cost
- Dataset-specific observations

**5.4 Future Work**
- Fine-tuning strategies
- Other datasets (DOTA v2, FAIR1M)
- Real-time optimization
- Integration with GIS systems

**5.5 Conclusion**
- Restate contributions
- Broader impact
- Final thoughts

**Appendices:**
- A: Additional results tables
- B: Implementation details
- C: Hyperparameters
- D: Code repository information

---

## 8. TECHNICAL DETAILS & CODE NOTES

### 8.1 Code Structure

```
d:/Work/DSML/
├── dataset/
│   ├── DOTA_v1_YOLO_oriented_bboxes_dataset/
│   ├── DOTA_v1_YOLO_vertical_bboxes_dataset/
│   └── DOTA_v1/ (original)
├── model_checkpoints/
│   ├── YOLO/OBB/ (10 models)
│   ├── YOLO/VBB/ (30 models)
│   └── SAM/ (to be added)
├── results/
│   └── yolo_evaluation/
│       ├── OBB/ (7/10 complete)
│       └── VBB/ (complete)
├── src/
│   ├── models/
│   │   ├── yolo_detector.py ✅
│   │   └── sam_segmenter.py (stub exists)
│   ├── utils/
│   │   ├── data_loader.py ✅
│   │   ├── metrics.py ✅
│   │   └── visualization.py ✅
│   ├── experiments/
│   │   ├── evaluate_yolo_obb.py ✅
│   │   └── evaluate_yolo_vbb.py ✅
│   └── pipeline/ (to be created)
│       └── yolo_sam_pipeline.py
└── notebooks/
    └── 01_yolo_evaluation.ipynb
```

### 8.2 Key Implementation Notes

**YOLO Detector (`src/models/yolo_detector.py`):**
- ✅ Supports both OBB and VBB modes
- ✅ DOTAv1.yaml standard class indices (0-14)
- ✅ Identity mapping for OBB (no complex conversions needed!)
- ✅ COCO→DOTA mapping for VBB (verified against official coco.yaml)
- ✅ DataLoader support for batch processing

**Critical Bug Fixes Applied:**
1. ✅ OBB label parsing: class_id moved from END to BEGINNING
2. ✅ VBB class mapping: updated to DOTAv1.yaml standard
3. ✅ COCO indices: verified against official Ultralytics coco.yaml
4. ✅ DataLoader OBB parsing: synchronized with yolo_detector

**Metrics (`src/utils/metrics.py`):**
- ✅ Class-agnostic design (works with any ID scheme)
- ✅ Supports both 4-coord (VBB) and 8-coord (OBB) boxes
- ✅ Per-class TP/FP/FN tracking
- ⚠️ TODO: Add mask-based metrics for SAM evaluation

### 8.3 Lessons Learned

1. **Format Standardization Critical:**
   - Spent significant time on dataset conversion
   - Worth it: now fully compatible with Ultralytics ecosystem
   - Lesson: Invest in proper data preparation upfront

2. **Class Mapping Pitfalls:**
   - Original code had wrong class indices
   - Silent failures are dangerous
   - Lesson: Always verify against official specs

3. **Evaluation Infrastructure:**
   - DataLoader significantly faster than path-based loading
   - Batch processing worth the implementation effort
   - Lesson: Build reusable evaluation framework

4. **Model Selection:**
   - Pretrained models surprisingly capable
   - No need to finetune for research purposes
   - Lesson: Don't over-engineer baselines

---

## 9. FIGURES & TABLES TO CREATE

### For Thesis

**Chapter 3 (Methodology):**
- [ ] Figure 3.1: DOTA v1 sample images (one per class)
- [ ] Figure 3.2: Pipeline architecture diagram
- [ ] Figure 3.3: YOLO→SAM prompt conversion illustration
- [ ] Table 3.1: Dataset statistics (detailed)
- [ ] Table 3.2: YOLO model architectures comparison
- [ ] Table 3.3: Hyperparameters

**Chapter 4 (Results):**
- [ ] Table 4.1: YOLO baseline results (all models)
- [ ] Table 4.2: Per-class performance breakdown
- [ ] Table 4.3: YOLO+SAM results comparison
- [ ] Figure 4.1: mAP comparison bar chart
- [ ] Figure 4.2: Per-class AP comparison (radar chart)
- [ ] Figure 4.3: IoU improvement distribution
- [ ] Figure 4.4: Qualitative comparison grid (6×5 grid: 5 classes × 6 methods)
- [ ] Figure 4.5: Success cases (4 examples)
- [ ] Figure 4.6: Failure cases (4 examples)
- [ ] Figure 4.7: Speed vs quality tradeoff
- [ ] Figure 4.8: Prompt strategy comparison

**Chapter 5 (Discussion):**
- [ ] Figure 5.1: Object size vs performance correlation
- [ ] Table 5.1: Computational requirements

### For Presentations

- [ ] Overview slide: Problem statement + solution
- [ ] Architecture slide: Clear pipeline diagram
- [ ] Results slide: Key metrics comparison
- [ ] Qualitative slide: Best visual examples

---

## 10. REFERENCES & CITATIONS (To be organized)

### Key Papers

**YOLO Family:**
- [ ] YOLOv1 (Redmon et al., 2016)
- [ ] YOLOv3 (Redmon & Farhadi, 2018)
- [ ] YOLOv5 (Ultralytics)
- [ ] YOLOv8 (Ultralytics, 2023)
- [ ] YOLOv11 (Ultralytics, 2024)

**Segment Anything:**
- [ ] SAM (Kirillov et al., 2023) - arXiv:2304.02643

**DOTA Dataset:**
- [ ] DOTA v1.0 (Xia et al., 2018)
- [ ] DOTA v1.5 (Xia et al., 2019)

**Aerial Object Detection:**
- [ ] Review paper on aerial detection
- [ ] OBB detection methods
- [ ] Small object detection techniques

**Foundation Models:**
- [ ] Vision transformers (Dosovitskiy et al., 2020)
- [ ] CLIP (Radford et al., 2021)

---

## 3.A EXPERIMENTAL FINDINGS - DETAILED ANALYSIS

### VBB Experiments: Domain Transfer Failure

**Context:** VBB models are COCO-pretrained (trained on ground-level perspective, 80 classes). Only 4 DOTA classes can be mapped from COCO:

**COCO→DOTA Class Mapping:**
- COCO car (ID:2) → DOTA small-vehicle (ID:10)
- COCO airplane (ID:4) → DOTA plane (ID:0)
- COCO bus (ID:5) & truck (ID:7) → DOTA large-vehicle (ID:9)
- COCO boat (ID:8) → DOTA ship (ID:1)

**Key Findings:**

1. **Low Metrics - Domain Mismatch**
   - Best model (YOLOv11l): 3.9% mAP@50, 4.3% IoU
   - 15-150x worse than OBB models
   - **Root Cause:** Ground perspective training → aerial perspective testing
   - Different viewpoint = different visual features = poor transfer

2. **Class-Specific Performance:**
   - ✅ **plane: 15.2% AP** (YOLOv11l) - Only acceptable performance
     - Large scale objects (100-200px typical)
     - Distinctive shape from above
     - Clear backgrounds (tarmac/runways)
   - ❌ **ship: 0.04% AP** - Near total failure
     - COCO boats look different from aerial ships
     - Scale variation (small boats → large vessels)
   - ❌ **large-vehicle: 0.05% AP** - Catastrophic
     - Bus/truck perspective completely different
     - Aerial view shows roof, not side
   - ❌ **small-vehicle: 0.1% AP** - Catastrophic
     - Cars appear as dots from aerial view
     - COCO cars show front/side features

3. **Bounding Box Size Issues**
   - VBB detections significantly larger than ground truth
   - Example: GT box = 50×30px, VBB pred = 80×60px
   - **Result:** Lower IoU and DICE even when mAP=100%
   - **Implication:** Large bounding boxes may negatively affect SAM performance
     - SAM receives too much context
     - Background noise included in prompt
     - Could lead to over-segmentation

4. **Inference Speed:**
   - Range: 21-58ms per image
   - Fastest: YOLOv10n (21.5ms)
   - Slowest: YOLOv12l (58.4ms)
   - Comparable to OBB despite simpler format

**Conclusions:**
- ❌ **VBB not suitable for aerial imagery** (domain mismatch too severe)
- ✅ **Need aerial-trained models** (finetuning or DOTA-pretrained)
- ⚠️ **Bbox size critical** for downstream SAM prompting
- ✅ **OBB clearly superior** (15-150x better performance)

---

### OBB Experiments: Strong Baseline Performance

**Context:** OBB models trained directly on DOTA dataset (all 15 classes, aerial perspective).

**Overall Performance (10 models tested):**

| Model | mAP@50 | IoU | DICE | Time (ms) | Best For |
|-------|--------|-----|------|-----------|----------|
| YOLOv8n-obb | 51.8% | 57.3% | 64.7% | 53.7 | Speed |
| YOLOv8s-obb | 54.2% | 60.5% | 67.9% | 66.2 | Balance |
| YOLOv8m-obb | 58.1% | 61.5% | 68.9% | 73.8 | Medium |
| YOLOv8l-obb | 59.4% | 61.5% | 68.5% | 70.5 | Large |
| YOLOv8x-obb | 59.7% | 61.9% | 69.1% | 81.2 | Quality |
| YOLOv11n-obb | 51.8% | 59.1% | 66.6% | 50.5 | **Fastest** |
| YOLOv11s-obb | 56.3% | 61.2% | 68.6% | 74.3 | Good balance |
| YOLOv11m-obb | 57.4% | 63.0% | 70.2% | 71.3 | V11 medium |
| YOLOv11l-obb | 59.1% | 64.0% | 71.3% | 71.4 | V11 large |
| YOLOv11x-obb | **59.9%** | **64.7%** | **71.9%** | 83.2 | **Best Overall** |

**Key Observations:**

1. **Performance Plateau at ~60% mAP**
   - Models plateau at 59-60% mAP regardless of size
   - YOLOv8n (smallest): 51.8%
   - YOLOv11x (largest): 59.9%
   - **Only 8% improvement for 10x parameters**
   - Diminishing returns beyond medium models

2. **No Replication of Official Results**
   - Official YOLO docs claim: 78-81% mAP@50 on DOTA
   - Our results: 52-60% mAP@50
   - **Possible reasons:**
     - Different train/val splits
     - Different preprocessing
     - Different evaluation protocols
     - Official results may include test-time augmentation

3. **Still Good Baseline for YOLO→SAM**
   - 52-60% detection adequate for segmentation research
   - Focus on integration, not optimization
   - SAM can refine imperfect detections
   - Research angle: "Can SAM compensate for modest detections?"

4. **YOLO11 Improvements**
   - Consistently better IoU/DICE than YOLOv8 equivalents
   - YOLOv11x: 64.7% IoU vs YOLOv8x: 61.9% IoU (+2.8%)
   - Similar speed, better localization
   - Recommendation: Use YOLOv11x for YOLO→SAM pipeline

**Per-Class Analysis (YOLOv11x-obb - Best Model):**

| Class | AP@50 | Performance | Notes |
|-------|-------|-------------|-------|
| tennis-court | 93.7% | ⭐⭐⭐ Excellent | Simple rectangular shape |
| large-vehicle | 84.4% | ⭐⭐⭐ Excellent | Common, distinctive |
| small-vehicle | 61.2% | ⭐⭐ Good | High quantity helps |
| harbor | 80.5% | ⭐⭐⭐ Excellent | Context-aided |
| plane | 77.7% | ⭐⭐⭐ Excellent | Large, distinctive |
| ship | 71.2% | ⭐⭐ Good | Common class |
| baseball-diamond | 72.5% | ⭐⭐ Good | Distinctive shape |
| ground-track-field | 60.3% | ⭐⭐ Moderate | Variable shapes |
| basketball-court | 61.2% | ⭐⭐ Moderate | Similar to tennis-court but harder |
| storage-tank | 55.8% | ⭐ Fair | Circular, cluttered backgrounds |
| helicopter | 54.9% | ⭐ Fair | Small, rare (703 instances) |
| soccer-ball-field | 47.9% | ⚠️ Poor | Irregular boundaries |
| roundabout | 43.8% | ⚠️ Poor | Complex geometry |
| bridge | 33.6% | ❌ Very Poor | Long, thin, variable |
| **swimming-pool** | **0.0%** | ❌❌❌ **FAILURE** | Too small, irregular |

**Problem Classes Deep Dive:**

1. **Swimming Pools (0% AP) - Complete Failure:**
   - Smallest objects (2-10px typical, <1% image area)
   - Highly variable shapes (rectangular, kidney, irregular)
   - Complex backgrounds (gardens, buildings, shadows)
   - Only 2,176 instances (1.7% of dataset)
   - **Hypothesis:** Below minimum detection threshold
   - **SAM Impact:** No detections = no SAM prompts = no help

2. **Bridges (33.6% AP) - Structural Challenge:**
   - Extreme aspect ratios (1:20 to 1:50)
   - Thin structures (3-8px wide, 100-300px long)
   - Partial occlusions (clouds, shadows)
   - Variable types (suspension, beam, arch)
   - **Hypothesis:** Anchor box mismatch
   - **SAM Impact:** Imprecise boxes → SAM might help refine

3. **Crowded Object Confusion:**
   - Dense parking lots: 1 bbox for 2-3 small-vehicles
   - Ship clusters in harbors: merged detections
   - **Pattern:** High-density areas cause detection collapse
   - **SAM Impact:** May separate merged objects with proper prompts

**Inference Speed Analysis:**

| Model Size | Time (ms) | FPS | Production Viable? |
|------------|-----------|-----|--------------------|
| Nano (n) | 50-54 | 19-20 | ✅ Yes (real-time) |
| Small (s) | 66-74 | 13-15 | ✅ Yes (near real-time) |
| Medium (m) | 71-74 | 13-14 | ✅ Yes |
| Large (l) | 70-71 | 14 | ✅ Yes |
| XLarge (x) | 81-83 | 12 | ⚠️ Marginal |

**Speed-Quality Tradeoff:**
- Nano→XLarge: +30ms inference (+60%)
- Performance gain: +8% mAP
- **Recommendation:** YOLOv11m or YOLOv11l (best balance)

---

### Key Insights for YOLO→SAM Pipeline

1. **Use OBB Models (Critical)**
   - 15-150x better than VBB
   - Proper aerial perspective training
   - Tighter bounding boxes

2. **Bbox Size Matters for SAM**
   - VBB boxes too large → excess background
   - OBB boxes tighter → better SAM prompts
   - **Design decision:** May need bbox refinement before SAM

3. **Focus on Medium-Confidence Classes**
   - Perfect detections (tennis-court 94%): SAM may not help much
   - Failed detections (swimming-pool 0%): SAM can't help
   - **Sweet spot:** 40-70% AP classes (bridges, roundabouts)
   - SAM's value proposition: refine imperfect detections

4. **Small Object Strategy**
   - Swimming pools, helicopters challenging
   - **Options:**
     - Multi-scale processing
     - Image tiling with overlap
     - Point prompts instead of box prompts
     - Accept that some classes will fail

5. **Performance Expectations**
   - Don't expect SAM to fix 0% AP classes
   - Target: 10-20% IoU improvement on 40-70% AP classes
   - Main value: Precise masks vs boxes for area calculation

---

## 11. WEEKLY PROGRESS LOG

### Week 0 (Nov 17, 2025)
**Completed:**
- ✅ DOTA v1 dataset analyzed (188,282 instances, 15 classes)
- ✅ Converted to OBB format (1,869 files, class_id at START)
- ✅ Converted to VBB format (1,869 files, standard YOLO)
- ✅ Fixed critical bugs in class mappings
- ✅ Verified COCO indices against official yaml
- ✅ Started OBB baseline evaluation (7/10 models done)

**Results:**
- YOLOv8 OBB series: 52-60% mAP (acceptable baseline)
- Problem classes identified: swimming-pool (0%), bridge (25-35%)
- Strong classes: tennis-court (94%), large-vehicle (83%)

**Decisions:**
- ❌ No finetuning (save 1-2 weeks)
- ✅ Proceed with YOLO→SAM integration
- ✅ Use performance variation as research dimension

**Time Spent:** ~8 hours (dataset prep, bug fixes, initial evaluation)

### Week 1 (Nov 18-24, 2025)
**Planned:**
- [ ] Complete OBB evaluation (3 models remaining)
- [ ] Analyze full results & create baseline report
- [ ] Design YOLO→SAM pipeline architecture
- [ ] Set up SAM infrastructure

**Target:** 20-25 hours

### Week 2-3 (Nov 25 - Dec 8, 2025)
**Planned:**
- [ ] Implement YOLO→SAM integration
- [ ] Test different prompt strategies
- [ ] Evaluate on validation set
- [ ] Optimize for speed

**Target:** 50-60 hours

---

## 12. OPEN QUESTIONS & TODO

### Research Questions
- [ ] Q1: What prompt strategy works best for aerial objects?
- [ ] Q2: How does YOLO quality affect SAM segmentation?
- [ ] Q3: Can SAM salvage poor detections (bridges, pools)?
- [ ] Q4: What's the speed vs quality tradeoff?

### Implementation TODOs
- [ ] Install SAM models (regular + Mobile + Fast)
- [ ] Create `src/pipeline/yolo_sam_pipeline.py`
- [ ] Implement mask-based evaluation metrics
- [ ] Add visualization tools for masks
- [ ] Batch processing optimization

### Writing TODOs
- [ ] Start Introduction draft (can begin now)
- [ ] Literature review notes (ongoing)
- [ ] Create figure templates
- [ ] Set up LaTeX/Word thesis template

### Admin
- [ ] Check thesis formatting requirements
- [ ] Confirm submission deadline
- [ ] Plan thesis defense (February?)

---

## 13. NOTES FOR FUTURE SELF

### What Went Well Today
1. **Dataset conversion** was thorough and bug-free
2. **Code alignment** prevented silent failures
3. **Baseline evaluation** running smoothly
4. **Finetuning decision** saves significant time

### What to Remember
1. **Swimming pools = hard:** Don't expect miracles from SAM either
2. **Speed matters:** 458 images × 280 objects = lots of SAM calls
3. **Prompt quality:** Garbage in, garbage out applies
4. **Small objects:** May need special handling (tiling, multi-scale)

### Key Insights
1. **Pretrained models sufficient:** 52-60% mAP adequate for research
2. **Class imbalance matters:** Ships (29%) vs baseball diamonds (0.5%)
3. **Simple shapes easiest:** Tennis courts (94%) vs irregular bridges (35%)
4. **Size correlates with performance:** Large objects generally easier

---

**END OF NOTES - WILL BE UPDATED CONTINUOUSLY**

*Next update: After OBB evaluation completes and YOLO→SAM design finalized*


---

# 🟩 **MSFP UPDATE — Nov 21, 2025**
### Integration of Revised Master Thesis Strategy

## ✔ Added Section: SAM-Only Benchmark (Intermediate Step)
A new chapter will be added to Methodology & Results covering:

- SAM ViT-H / ViT-L / ViT-B  
- Box vs Point prompts  
- Use of Ground-Truth OBB prompts  
- Purpose: isolate SAM capability on AerialFuseCV  
- 6 controlled configurations  

## ✔ Added Section: Minimal ArgusVision Benchmark
- YOLOv11x-only  
- 3 SAM variants  
- 2 prompt types  
- 6 configurations  
- Evaluates combined Detector→Segmenter performance  

## ✔ Locked Master Thesis Boundaries
- No MobileSAM / FastSAM  
- No Hybrid prompt  
- No multi-UAV or real-time system  
- No full benchmark (PhD-only)

## ✔ Document Structure Updated
Chapters now include:
1. Introduction  
2. Related Work  
3. Dataset (AerialFuseCV)  
4. Methodology  
   - YOLOv11x  
   - SAM variants  
   - GT prompt generation  
   - Pipeline description  
5. SAM-Only Benchmark (new)  
6. Minimal ArgusVision Benchmark  
7. Discussion & PhD Roadmap  
8. Conclusion  

## ✔ Status  
Master Thesis is now in **Phase 2 (SAM-only benchmarking)**.  
Thesis progress ~34%.  
All updates align with MSFP and preserve PhD novelty.

---

# 🟩 Next Steps (For Thesis)
- Implement SAM-only benchmark loop  
- Generate visual examples  
- Begin drafting Chapters 3–5  

---

*Updated by ATHENA_STRATEGIST on Nov 21, 2025*  
