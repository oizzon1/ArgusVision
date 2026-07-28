# Quick Reference Commands

## 🦉 Restore ATHENA Context
```
ATHENA, read THESIS_NOTES.md and WORK_LOG.md to restore full project context
```

## 📦 Environment Setup
```cmd
# Create environment
conda env create -f ArgusVision_environment.yml

# Activate environment
conda activate AV_env
set PYTHONNOUSERSITE=1

# Verify GPU
python -c "import torch; print('CUDA:', torch.cuda.is_available())"
python test_gpu
```

## 🎯 Phase 1: YOLO Baseline Evaluation
```cmd
# Oriented Bounding Boxes (OBB)
python src/experiments/evaluate_yolo_obb.py

# Vertical Bounding Boxes (VBB)
python src/experiments/evaluate_yolo_vbb.py
```

## 📘 Phase 2: SAM-Only Benchmark
```cmd
# Full evaluation (all 6 configurations)
python src/experiments/evaluate_sam.py

# Test mode (10 images)
python src/experiments/evaluate_sam.py --test
```
**Results:** `results/sam_evaluation/{config}/` with metrics + 10 best/worst examples

## 🛰️ Phase 3: ArgusVision Pipeline
```cmd
# Quick integration test (1 image, ~10 sec)
python src/experiments/test_argusvision_quick.py

# Small evaluation (10 images, ~20-30 sec)
python src/experiments/evaluate_ArgusVision.py --max-images 10

# Full evaluation (1,783 images, ~30-40 min)
python src/experiments/evaluate_ArgusVision.py
```
**Results:** `results/ArgusVision_evaluation/` with metrics + 10 best/worst visualizations

## 🔧 Optional Arguments
```cmd
# ArgusVision with custom settings
python src/experiments/evaluate_ArgusVision.py \
    --dataset dataset/AerialFuseCV_Refined_Merged \
    --yolo-model model_checkpoints/YOLO/OBB/yolo11x-obb.pt \
    --sam-model model_checkpoints/SAM/sam_vit_l_0b3195.pth \
    --max-images 100 \
    --device cuda \
    --output-dir results/custom_run
```

## 📊 Results Locations
- **YOLO:** `results/yolo_evaluation/OBB/` and `results/yolo_evaluation/VBB/`
- **SAM:** `results/sam_evaluation/{config}/`
- **ArgusVision:** `results/ArgusVision_evaluation/`
