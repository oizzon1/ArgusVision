# 🛰️ ArgusVision — SAM Benchmark Plan (Intermediate Step)
### Evaluating SAM Variants with Perfect Ground Truth Prompts  
**Version 1.0 — Prepared by ATHENA_STRATEGIST**

---

## 🎯 Purpose
This intermediate benchmark isolates **SAM’s intrinsic performance** by evaluating all official SAM variants using *perfect ground truth bounding boxes* (no YOLO noise).  
This step provides a clean scientific understanding of how SAM behaves on AerialFuseCV before integrating it into the ArgusVision pipeline.

This benchmark:
- Determines which SAM variant is best suited for ArgusVision  
- Establishes reference-quality segmentation metrics  
- Provides insights independent of detection quality  
- Lays the foundation for the Master Thesis and the PhD benchmark  

---

# 🧵 Dataset
**AerialFuseCV**  
- 458 validation images  
- 15 classes  
- Ground truth OBBs  
- Ground truth segmentation masks  

---

# 🧩 Benchmark Matrix (SAM-Only Evaluation)

### 1. SAM Variants (3)
| Code | Model    | Notes |
|------|----------|-------|
| **S1** | SAM ViT-H | Highest quality |
| **S2** | SAM ViT-L | Balanced model |
| **S3** | SAM ViT-B | Lightweight baseline |

---

### 2. Prompt Strategies (2)
| Code | Prompt | Description |
|------|--------|-------------|
| **P1** | Box Prompt | Perfect GT bounding box |
| **P2** | Point Prompt | GT box centroid |

---

# 🟩 Total Configurations: **6 runs**

| SAM Model | Box Prompt | Point Prompt |
|-----------|------------|--------------|
| ViT-H     | S1-P1      | S1-P2        |
| ViT-L     | S2-P1      | S2-P2        |
| ViT-B     | S3-P1      | S3-P2        |

---

# 🎛 Metrics
- Mask IoU (global + per-class)
- DICE coefficient
- Boundary F1
- ΔIoU vs GT bounding boxes
- Runtime (per-image)
- GPU memory usage
- Good/Bad qualitative examples

---

# 🚀 Protocol
1. Load GT OBBs  
2. Generate prompts  
3. Run SAM variant  
4. Evaluate against masks  
5. Save per-image results  
6. Aggregate into tables  

---

# 📘 Output
- SAM-only benchmark tables  
- Per-class SAM performance  
- Qualitative examples  
- Recommendation for best SAM model for ArgusVision  

---

# 🟩 Outcome
This benchmark determines the **SAM model** to use for:
- The Master Thesis minimal ArgusVision benchmark  
- The PhD full-scale benchmark  

This is the cleanest possible way to evaluate SAM for aerial segmentation.

---
