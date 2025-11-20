# 🎓 Master Thesis Roadmap — ArgusVision Phase 0  
### Minimal Benchmarking Framework & Thesis Completion Plan  
**Version 1.0 — Prepared by Panagiotis Fragkos**

---

## 🟩 Purpose
This roadmap defines a **minimal, focused, high-quality Master Thesis plan** that lays the foundation for the full ArgusVision research program while avoiding premature disclosure of PhD-level contributions.

The Master Thesis must:
- be scientifically rigorous  
- be feasible within the remaining timeframe  
- avoid revealing the full ArgusVision system  
- produce publishable-quality groundwork  
- support a clean transition into Year 1 of the PhD  

---

# 🟦 Phase 1 — Pipeline Construction (Weeks 1–2)

## 🎯 Objectives
- Build a **single YOLO→SAM inference pipeline**.
- Ensure correct handling of OBB → box prompt → mask generation.
- Validate against a small curated test set.

## 🔧 Tasks
- Implement YOLOv11m-OBB inference module.
- Implement SAM ViT-L segmentation with box prompts.
- Build visualization tools (bbox + mask overlays).
- Validate on ~10–20 images.

## 📄 Deliverables
- ArgusVision Prototype Pipeline v0.1  
- Figures: detection-to-mask examples  
- Thesis Methodology Chapter (draft)

---

# 🟩 Phase 2 — Minimal Benchmarking (Weeks 3–4)

## 🎯 Objectives
Evaluate a **small, controlled benchmark** that demonstrates:
- effect of prompt strategies
- effect of SAM model size
- effect of detector quality

Avoid full 90-configuration benchmark.

---

## 🔧 Benchmark Matrix (Minimal)

### YOLO Models (2):
- YOLOv8x-OBB  
- YOLOv11x-OBB  

### SAM Models (2):
- SAM ViT-L  
- SAM ViT-B  

### Prompt Types (2):
- Box Prompt (P1)  
- Point Prompt (P2)  

### Total Configurations:
**2 × 2 × 2 = 8 runs**

---

## 📄 Required Metrics
- Mask IoU  
- DICE  
- Boundary F1  
- Runtime per image (breakdown: YOLO, SAM)  
- Qualitative inspection (10 examples)  

---

## 🧪 Deliverables (Benchmark)
- Clean comparative tables  
- Per-class performance summary  
- 2–3 key insights (differences between models/prompts)  
- Benchmark Section for Thesis Chapter 4

---

# 🟦 Phase 3 — Thesis Writing (Weeks 5–7)

## 🎯 Objectives
Finish writing the main scientific body.

## 🔧 Tasks
- Write Introduction  
- Write Related Work  
- Write Methodology (pipeline description)  
- Write Benchmark Evaluation  
- Produce visualizations and tables  
- Write Discussion & Limitations  

## 📄 Deliverables
- Full thesis draft ready for supervisor review  

---

# 🟩 Phase 4 — Revision & Defense Preparation (Weeks 8–10)

## 🎯 Objectives
Deliver a polished thesis and prepare for defense.

## 🔧 Tasks
- Integrate supervisor revisions  
- Add final figures & captions  
- Polish conclusions  
- Prepare defense slide deck  

## 📄 Deliverables
- Final PDF thesis  
- Presentation slides  
- Defense-ready ArgusVision Phase 0 pipeline demo  

---

# 🟦 Why This Minimal Plan Works

- Scientifically valid  
- Methodologically rigorous  
- Fully reproducible  
- Within Master’s constraints  
- Leaves novelty untouched for PhD  
- Builds the bedrock for Year 1 (full 90-config benchmark)

---

# 🟩 Transition to PhD

After submission and graduation:

- Expand pipeline  
- Implement full ArgusVision_Benchmark (90 configs)  
- Begin embedded/real-time ArgusVision research  
- Prepare Publication #1 (Benchmark Paper)

---

**This roadmap guarantees:  
A strong Master Thesis now → A powerful PhD launch afterward.**

