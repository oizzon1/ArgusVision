# 🛰️ ArgusVision Benchmark Plan — Master Thesis  
### Minimal Benchmark + SAM-Only Evaluation  
**Version 1.2 — MasterThesis Edition (Updated)**

---

## 🎯 Purpose
This updated plan includes **two components**:

1. **SAM-only Benchmark (Intermediate Step)** → Evaluate SAM H/L/B on AerialFuseCV using ground truth prompts  
2. **ArgusVision Minimal Benchmark** → Evaluate YOLOv11x + SAM (best variant) with 2 prompts  

This creates a clean, scientifically rigorous Master Thesis without revealing the full ArgusVision PhD benchmark.

---

# 🟦 Part I — SAM-Only Benchmark (6 configs)

### SAM Models
- ViT-H  
- ViT-L  
- ViT-B  

### Prompts
- Box  
- Point  

→ **6 configurations**  

See `ArgusVision_SAM_Benchmark_Plan.md` for full details.

---

# 🟩 Part II — ArgusVision Minimal Benchmark (6 configs)

### YOLO Detector (fixed)
- **YOLOv11x-OBB** (best-performing)

### SAM Variants (3)
- ViT-H  
- ViT-L  
- ViT-B  

### Prompt Strategies (2)
- Box  
- Point  

→ **3 × 2 = 6 configurations**

---

# 🟩 Total Master Thesis Evaluation: **12 runs**

(6 SAM-only + 6 ArgusVision)

---

# 🎛 Metrics
- Mask IoU  
- DICE  
- Boundary F1  
- ΔIoU vs bbox  
- Runtime  
- Per-class performance  
- Qualitative analysis  

---

# 📘 Thesis Integration
**Chapter 3:**  
- Dataset  
- YOLOv11x  
- SAM models  
- Prompts  
- Pipeline  

**Chapter 4:**  
- SAM-only results  
- Minimal ArgusVision results  

**Chapter 5:**  
- Discussion  
- Limitations  
- Future work (leading to PhD research)

---

# 🔐 Strategic Boundaries
- Only YOLOv11x for Master’s  
- Only 3 SAM official models  
- No FastSAM/MobileSAM  
- Hybrid prompts saved for PhD  
- No multi-UAV, real-time, or cooperative mapping  

---
