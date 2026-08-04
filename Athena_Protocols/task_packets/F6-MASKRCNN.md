ATHENA WORKER TASK — F6-MASKRCNN (paste this whole block into the operator model's terminal)

You are an OPERATOR worker. The orchestrator is the Claude Code session; you
do not decide scope, you execute this packet.

SETUP
  cd /mnt/d/Work/AV && git switch dev && git pull
  git switch -c task/f6-maskrcnn-windows
READ FIRST
  Athena_Protocols/ATHENA_RISE.md · ATHENA_STATE.md (OPEN 5) · ACTIVE_TASKS.md
  ArgusVision_Strategic_Planning/PUBLICATION_ROADMAP.md (v2.4, F6–F8)
  dataset/README.md · dataset/AerialFuseCV/dataset_statistics.json

CLAIM
  Update ONLY your row in Athena_Protocols/ACTIVE_TASKS.md:
  ID=F6, Owner=<your model name>, Status=active, Started=<date>.

LOCKED TO YOU (new files only — you create these)
  experiments/maskrcnn_setup/**            (env spec, configs, notes, smoke logs)
  dataset/convert_aerialfusecv_to_coco.py  (new converter, if needed)
DO NOT EDIT
  src/argusvision/** (frozen evaluation stack) · dataset/build_aerialfusecv.py
  and other existing dataset scripts · AV_env (create a NEW conda env; never
  install into AV_env) · control files · papers/.

OBJECTIVE  (closes ATHENA_STATE OPEN 5; unblocks P2 experiments due ≤ 09-15)
  Establish a WORKING Mask R-CNN training path on this Windows machine.
  Primary: MMDetection. Fallback: torchvision.models.detection.maskrcnn.
  Proof = a smoke training run (≥50 iterations, loss decreasing) on a small
  AerialFuseCV subset converted to COCO instance format.

STEPS
  1. New conda env (suggest name: P2_env). Record exact create/install
     commands and a pip freeze into experiments/maskrcnn_setup/ENV.md.
  2. If MMDetection fails on Windows after honest effort (~half a day),
     document the failure precisely and switch to torchvision — a working
     fallback beats a broken primary.
  3. Converter: AerialFuseCV → COCO JSON (images, HBB bboxes from labels_hbb,
     masks as RLE or polygons from instance_masks, category ids from
     labels_obb class names). New file only; read the dataset, never modify it.
  4. Smoke train on ~50 train images; save the log; report loss trajectory,
     iterations/sec, and VRAM use.
  5. Write experiments/maskrcnn_setup/REPORT.md: chosen path, env, converter
     usage, smoke evidence, and estimated wall-time for full training.

CONSTRAINTS
  GPU is shared — check no other training is running before your smoke run
  (tasklist | findstr python). Timing numbers are indicative only; no
  experimental claims from this task enter any paper. Windows conda runs via:
  /mnt/c/Windows/System32/cmd.exe /c "cd /d d:\Work\AV && conda run -n <env> python <script>"
  (inline python -c does not survive cmd.exe quoting — always use script files)

ON FINISH
  Set ACTIVE_TASKS row Status=ready-for-review. Commit with prefix [F6],
  push task/f6-maskrcnn-windows ONLY (never dev), report commit hash,
  chosen path (MMDetection vs torchvision), and any blockers to the user.
