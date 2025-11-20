# How To: Setup, Activate, and Run Experiments

This guide shows how to set up the environment, activate it, verify GPU, and run the OBB/VBB evaluations.

## 1) Prerequisites
- Install Miniconda/Anaconda (Windows).
- Ensure NVIDIA GPU drivers are installed (RTX 30xx supported).
- Clone this repo (or open it in VS Code).

## 2) Create the Environment
- From the repo root (`d:\Work\DSML`), create the conda env using the provided file:

```cmd
conda env create -f thesis_environment.yml
```

This installs CUDA-enabled PyTorch + all project dependencies.

## 3) Activate the Environment
- Command Prompt (cmd):
```cmd
conda activate thesis_env
set PYTHONNOUSERSITE=1
```
- PowerShell:
```powershell
conda activate thesis_env
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

## 5) Dataset and Weights
- Default dataset paths used by the scripts:
  - OBB: `dataset/DOTA_v1_YOLO_oriented_bboxes_dataset`
  - VBB: `dataset/DOTA_v1_YOLO_vertical bboxes_dataset`
- Place YOLO weights here (optional; Ultralytics can auto-download if missing):
  - OBB weights: `model_checkpoints/YOLO/OBB/` (e.g., `yolov8n-obb.pt`, `yolo11s-obb.pt`)
  - VBB weights: `model_checkpoints/YOLO/VBB/` (e.g., `yolo11n.pt`, `yolov8s.pt`)

## 6) Run Experiments
- Oriented Bounding Boxes (OBB, DOTA-trained models):
```cmd
python -m src.experiments.evaluate_yolo_obb
```
- Vertical/Axis-Aligned Bounding Boxes (VBB, COCO models):
```cmd
python -m src.experiments.evaluate_yolo_vbb
```
Outputs are saved under `results/yolo_evaluation/OBB` and `results/yolo_evaluation/VBB`.

## 7) VS Code Tips
- Select Interpreter: Ctrl+Shift+P → "Python: Select Interpreter" → choose `thesis_env`.
- Default Terminal: Terminal → Select Default Profile → choose Command Prompt if you prefer `cmd`.

## 8) Troubleshooting
- Torchvision/ops errors (e.g., missing `nms`): ensure you are in `thesis_env` and created it from `thesis_environment.yml`.
- Mixed packages from user site: make sure `PYTHONNOUSERSITE` is set for the session.
- Slow runs on CPU: re-check GPU availability (`test_gpu`), and that the environment shows `cuda:0` when starting `evaluate_yolo_obb`.
