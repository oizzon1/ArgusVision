# How To: Setup, Activate, and Run Experiments

This guide shows how to set up the environment, activate it, verify GPU, and run the evaluations.

## 1) Prerequisites
- Install Miniconda/Anaconda (Windows).
- Ensure NVIDIA GPU drivers are installed (RTX 30xx supported).
- Clone this repo (or open it in VS Code).

## 2) Create the Environment
- From the repo root (`d:\Work\AV`), create the conda env using the provided file:

```cmd
conda env create -f ArgusVision_environment.yml
```

This installs CUDA-enabled PyTorch + Ultralytics + SAM + all project dependencies.

## 3) Activate the Environment
- Command Prompt (cmd):
```cmd
conda activate AV_env
set PYTHONNOUSERSITE=1
```
- PowerShell:
```powershell
conda activate AV_env
$env:PYTHONNOUSERSITE = "1"
```

Tip: `PYTHONNOUSERSITE=1` avoids accidentally importing packages from your user site-packages.

## 4) Verify GPU (optional but recommended)
- Quick checks:
```cmd
python -c "import torch; print('CUDA available:', torch.cuda.is_available()); print('Torch:', torch.__version__, 'CUDA build:', getattr(torch.version,'cuda',None))"
python .\test_gpu
```
You should see your GPU name and a successful small matmul on GPU.

## 5) Datasets
- **AerialFuseCV_Refined_Merged**: Primary dataset for SAM and ArgusVision evaluation
  - Location: `dataset/AerialFuseCV_Refined_Merged`
  - 1,783 images, 114,870 bbox-mask pairs, 13 classes
- **DOTA v1** (YOLO baseline):
  - OBB: `dataset/DOTA_v1_YOLO_oriented_bboxes_dataset`
  - VBB: `dataset/DOTA_v1_YOLO_vertical bboxes_dataset`

## 6) Model Checkpoints
- **YOLO weights** (optional; Ultralytics can auto-download if missing):
  - OBB: `model_checkpoints/YOLO/OBB/` (e.g., `yolo11x-obb.pt`)
  - VBB: `model_checkpoints/YOLO/VBB/` (e.g., `yolo11x.pt`)
- **SAM weights** (required for SAM/ArgusVision):
  - Location: `model_checkpoints/SAM/`
  - Download: `sam_vit_h_4b8939.pth`, `sam_vit_l_0b3195.pth`, `sam_vit_b_01ec64.pth`
  - Source: https://github.com/facebookresearch/segment-anything

## 7) Run Experiments

### YOLO Baseline (Phase 1)
- **OBB Evaluation** (DOTA-trained models):
```cmd
python src/experiments/evaluate_yolo_obb.py
```
- **VBB Evaluation** (COCO models):
```cmd
python src/experiments/evaluate_yolo_vbb.py
```

### SAM-Only Benchmark (Phase 2)
```cmd
python src/experiments/evaluate_sam.py
```
Output: `results/experimental/sam_evaluation/{config}/` with metrics + 10 best/worst examples

### ArgusVision Pipeline (Phase 3)
- **Quick Test** (1 image, ~10 seconds):
```cmd
python src/experiments/test_argusvision_quick.py
```

- **Small Evaluation** (10 images, ~20-30 seconds):
```cmd
python src/experiments/evaluate_ArgusVision.py --max-images 10
```

- **Full Evaluation** (1,783 images, ~30-40 minutes):
```cmd
python src/experiments/evaluate_ArgusVision.py
```

Output: `results/experimental/ArgusVision_evaluation/` with metrics + 10 best/worst visualizations

## 8) VS Code Tips
- Select Interpreter: Ctrl+Shift+P → "Python: Select Interpreter" → choose `AV_env`.
- Default Terminal: Terminal → Select Default Profile → choose Command Prompt if you prefer `cmd`.

## 9) Troubleshooting
- Torchvision/ops errors (e.g., missing `nms`): ensure you are in `AV_env` and created it from `ArgusVision_environment.yml`. Note that torch/torchvision must come from the PyTorch cu124 index, not PyPI — a plain `pip install torch` yields a CPU build and this is the usual cause.
- Mixed packages from user site: make sure `PYTHONNOUSERSITE` is set for the session.
- Slow runs on CPU: re-check GPU availability (`test_gpu`), and that the environment shows `cuda:0` when starting `evaluate_yolo_obb`.
