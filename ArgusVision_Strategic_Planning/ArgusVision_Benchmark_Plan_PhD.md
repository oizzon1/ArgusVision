# 🛰️ ArgusVision Benchmark Plan — PhD  
### Full Exhaustive Evaluation (Detectors × SAM Variants × Prompts × Devices)  
**Version 2.2 — PhD Edition (Updated)**

---

## 🎯 Purpose
This document defines the **complete full-scale ArgusVision benchmark**  
to be executed during the PhD program.

It expands all dimensions to produce a **180+ configuration** scientific map of aerial segmentation refinement.

---

# 🧵 Dataset
AerialFuseCV — 458 validation images  
Used consistently across Master and PhD phases.

---

# 🧩 PhD Benchmark Matrix

## 1. YOLO OBB Detectors — 10 models
**YOLOv8:** n, s, m, l, x  
**YOLOv11:** n, s, m, l, x  

---

## 2. SAM Variants — 6 models
**Official:**  
- ViT-H  
- ViT-L  
- ViT-B  

**Unofficial:**  
- Mobile-SAM  
- FastSAM  
- +1 optional lightweight SAM variant  

---

## 3. Prompt Strategies — 3
- Box  
- Point  
- Hybrid  

---

# 🟩 Total Configurations: **180**  
(10 YOLO × 6 SAM × 3 prompts)

---

# 🎛 Metrics (Full Suite)
- All Master Thesis metrics +  
- mAP@50-mask  
- Robustness curves  
- Occlusion performance  
- Device-level runtime (Cloud / Edge / Mobile / UAV)  
- Energy consumption (optional)  

---

# 🚀 Protocol
1. Precompute YOLO detections  
2. Generate prompts  
3. Run SAM variants  
4. Evaluate metrics  
5. Aggregate  
6. Build publications  

---

# 🛰️ PhD Integration
### Year 1  
Full 180-config benchmark → **Publication #1**

### Year 2–3  
Optimization + embedded inference → Publication #2  

### Year 4  
Dual-UAV ArgusVision system  

### Year 5  
Final prototype + dissertation  

---

# 🔐 Strategic Note
Master Thesis remains minimal.  
Full benchmark = **PhD-only** to preserve novelty.

---
