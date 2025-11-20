<p align="center">`n  <img src="assets/ArgusVision_logo_4_Magenta.png" alt="ArgusVision Logo" width="320">`n</p>`n`n# 🛰️ **ArgusVision – Aerial Detection & Segmentation Research Platform**
### *Master’s Thesis (Phase 0) → PhD System (Phase 1–5)*  
**Author:** Panagiotis Fragkos (LtCol, Hellenic Army)  
**Project Timeline:** Nov 2025 → 2030  
**Current Phase:** Master’s Thesis (Phase 0)  

---

# 📘 Overview

**ArgusVision** is a multi-stage research and development program for aerial computer vision, focused on:

- **Aerial object detection** using YOLO (OBB + VBB)
- **Segmentation refinement** using Meta’s **Segment Anything Model (SAM)**
- **Dataset fusion and curation** (AerialFuseCV)
- **Benchmarking**, **analysis**, and **modular pipeline design**
- Future **dual-UAV cooperative perception** and **near real-time mapping**

This repository supports **two parallel tracks**:

---

# 🎓 **1. Master’s Thesis (Phase 0)**  
*A minimal, clean, controlled evaluation to build foundational knowledge without revealing PhD-level system concepts.*

### **Master Thesis Goals**
- Benchmark **SAM variants (ViT-H/L/B)** with **ground-truth prompts**  
- Benchmark **YOLOv11x → SAM** with minimal configurations  
- Produce a rigorous but **non-exhaustive** evaluation  
- Build all components needed for the future full benchmark  
- Write a clean thesis and graduate  
- Preserve novelty for PhD work  

---

# 🧪 **Master Thesis Benchmarks**

## **A. SAM-Only Benchmark (6 configurations)**
Using **ground-truth OBBs** to isolate SAM’s true segmentation capability:

| SAM Variant | Box Prompt | Point Prompt |
|-------------|------------|--------------|
| ViT-H       | ✓          | ✓            |
| ViT-L       | ✓          | ✓            |
| ViT-B       | ✓          | ✓            |

**Purpose:** Identify the best SAM model before integrating with YOLO.

---

## **B. Minimal ArgusVision Benchmark (6 configurations)**

Using **YOLOv11x-OBB** (best detector identified in Phase 0):

| YOLO → SAM | Box Prompt | Point Prompt |
|------------|------------|--------------|
| v11x → ViT-H | ✓        | ✓            |
| v11x → ViT-L | ✓        | ✓            |
| v11x → ViT-B | ✓        | ✓            |

Total Master Thesis runs: **12**

---

# 🧬 **2. PhD Research Program (Phase 1–5)**  
The full ArgusVision system will expand into:

### **Full 180+ Configuration Benchmark**
- All YOLOv8 + YOLOv11 OBB models  
- SAM ViT-H/L/B + MobileSAM + FastSAM  
- Box, Point, Hybrid prompts  
- Cloud / Edge / Embedded device profiling  

### **ArgusVision System Roadmap**
- **Year 1:** Full benchmark + first publication  
- **Year 2:** Embedded inference (Jetson Orin)  
- **Year 3:** Dual-UAV cooperative perception  
- **Year 4:** Real-time mapping + flight trials  
- **Year 5:** ArgusVision v3.0 Demonstrator + PhD defense  

---

# 🗂️ **Repository Structure**

```
ArgusVision/
│
├── src/
│   ├── detection/           # YOLO inference, OBB/VBB converters
│   ├── segmentation/        # SAM integration modules
│   ├── benchmarks/          # Benchmark runners (SAM-only, Master, PhD)
│   ├── datasets/            # AerialFuseCV dataloaders + utils
│   ├── utils/               # Metrics, prompt generation, helpers
│   ├── visualization/       # Overlay generation, plots, samples
│   └── argus_vision/        # Core pipeline (YOLO → SAM)
│
├── data/
│   ├── AerialFuseCV/        # Dataset (DOTA + iSAID fusion)
│   └── ground_truth/        # GT OBBs + segmentation masks
│
├── results/
│   ├── sam_only/
│   ├── master_benchmark/
│   └── phd_benchmark/
│
├── docs/
│   ├── ArgusVision_Benchmark_Plan_MasterThesis.md
│   ├── ArgusVision_Benchmark_Plan_PhD.md
│   ├── ArgusVision_5Year_Roadmap.md
│   ├── ArgusVision_SAM_Benchmark_Plan.md
│   └── ArgusVision_Master_Roadmap.md
│
├── WORK_LOG.md
├── ATHENA_RISE.md
├── ATHENA_RISE_STRATEGIST.md
└── README.md  ← (this file)
```

---

# 🚀 **Setup Instructions**

### **Install environment**
```
conda create -n argus python=3.10
conda activate argus
pip install -r requirements.txt
```

### **Run SAM-Only Benchmark**
```
python -m src.benchmarks.sam_benchmark --sam vit_l --prompt box
```

### **Run Master Thesis Minimal Benchmark**
```
python -m src.benchmarks.master_benchmark --sam vit_l --prompt point
```

---

# 🧠 **ATHENA Integration**

The project includes two AI control layers:

- **ATHENA_STRATEGIST** → planning, roadmaps, Operator prompt generation  
- **ATHENA Operator (VS Code AI)** → executes code, logs results, runs benchmarks  

Documentation:  
- `ATHENA_RISE_STRATEGIST.md`  
- `ATHENA_RISE.md`  

---

# 🔐 **Strategic Boundaries (Master vs PhD)**

### **Master Thesis (Phase 0) includes:**
- YOLOv11x-only  
- SAM H/L/B  
- Box & Point prompts  
- 12 total runs  
- No hybrid prompts  
- No multi-UAV  
- No real-time edge inference  
- No full benchmark  

### **PhD (Phase 1–5) includes:**
- All YOLO models  
- All SAM models  
- Hybrid prompts  
- Full 180+ configurations  
- Dual-UAV systems  
- Real-time onboard mapping  
- SLAM + segmentation fusion  

---

# 🏁 **Outcome**

This repository forms the backbone of:

- A rigorous Master’s Thesis  
- The future ArgusVision PhD system  
- A dual-UAV real-time geospatial intelligence platform  

You are currently in **Master Thesis Phase — MSFP Phase 2**:  
**Implementing the SAM-only benchmark.**

---

*Updated: Nov 21, 2025 — Maintained by ATHENA_STRATEGIST*  

