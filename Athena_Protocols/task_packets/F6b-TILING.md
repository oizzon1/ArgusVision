ATHENA WORKER TASK — F6b-TILING (paste this whole block into the operator terminal)

You are an OPERATOR worker. The orchestrator is the Claude Code session.

WHY THIS EXISTS
Ultralytics reports ~80% mAP50 for YOLOv11-OBB on DOTA. Our detector-only run
measured macro-F1 0.6240 on the same weights. The likely dominant cause is that
DOTA detection is universally benchmarked on ~1024px tiles, while we evaluate on
full images up to ~4000x13000px — so small objects appear at a scale the model
never trained on. A reviewer WILL ask why our detector looks weak. This task
replaces an assertion with a measurement.

SETUP
  cd /mnt/d/Work/AV && git fetch origin && git worktree add .worktrees/f6b origin/dev
  cd .worktrees/f6b && git switch -c task/f6b-tiling
  (The shared checkout may be on another session's branch — do NOT `git switch`
   there. Use the worktree. Remove it when done: git worktree remove .worktrees/f6b)

READ FIRST
  Athena_Protocols/ATHENA_RISE.md · ACTIVE_TASKS.md
  src/argusvision/models/yolo.py · src/argusvision/evaluation/*
  experiments/run_evaluation.py · experiments/configs/validation_yolo11x_obb.yaml
  results/AerialFuseCV_Testing/  (the full-image baseline lives here)

CLAIM
  Add a row to ACTIVE_TASKS.md: ID=F6b, Owner=<model>, Status=active.

LOCKED TO YOU (new files only)
  experiments/tiling/**            (script, configs, report)
DO NOT EDIT
  src/argusvision/**  — the evaluation stack is FROZEN. If you believe it needs
  a change, STOP and report; do not edit it.
  dataset/**, papers/**, results/AerialFuseCV_Testing/**, control files.

OBJECTIVE
  Measure how much of the detection gap is explained by input scale, using ONE
  evaluator so the two runs are comparable.

METHOD (the design constraint that makes this valid)
  1. Tile each val image into 1024x1024 windows with 200px overlap.
  2. Run YOLOv11x-OBB on each tile (weights: model_checkpoints/YOLO/OBB/yolo11x-obb.pt,
     conf 0.25 — same as the baseline).
  3. **Map every detection back to full-image coordinates** (add tile origin to
     the oriented corners).
  4. Merge across tiles: an object spanning a seam appears in 2+ tiles. De-duplicate
     with rotated-box NMS (IoU 0.5) over the merged full-image detection set.
  5. Score the merged detections with the EXISTING evaluator against the SAME
     ground truth as the baseline — `DetectionEvaluator`, iou_mode auto,
     thresholds 0.1/0.3/0.5. Do not write a new metric.
  6. Dataset: dataset/AerialFuseCV/val (456 images).

  Steps 3-5 are the point. Scoring detections in tile coordinates, or against
  per-tile ground truth, measures a different task and answers nothing.

REPORT (experiments/tiling/REPORT.md)
  Table: full-image vs tiled, side by side — micro precision/recall/F1 and
  mean AP at each threshold, plus per-class recall for small-vehicle, ship,
  large-vehicle, plane (the classes scale should affect most).
  State: tiles per image (mean), detections before/after NMS, runtime per image.
  Do NOT compare to Ultralytics' published number — different data, split and
  metric. Report only our two runs.

CONSTRAINTS
  - No number leaves this task except into experiments/tiling/ and results/.
  - GPU is shared; check before running (tasklist | findstr python).
  - Windows: /mnt/c/Windows/System32/cmd.exe /c "cd /d d:\Work\AV\.worktrees\f6b && conda run -n AV_env python <script>"
    (inline python -c does not survive cmd.exe quoting — use script files)

ON FINISH
  Set your row ready-for-review; commit with prefix [F6b]; push
  task/f6b-tiling ONLY; report commit hash, the two-run table, and your read on
  whether tiling should become P2's detection protocol.
