# F6 Mask R-CNN Environment

**Task:** F6 Mask R-CNN Windows feasibility
**Worker:** Codex-Operator
**Started:** 2026-08-04

## Rules

- `AV_env` is read-only for this task.
- All feasibility work runs in a separate conda environment: `P2_env`.
- Windows conda is invoked from WSL through `cmd.exe` from the repository root.
- Inline `python -c` is avoided; diagnostic code lives in scripts in this
  directory.

## Commands

Environment creation:

```bash
/mnt/c/Windows/System32/cmd.exe /c "conda create -y -n P2_env --clone AV_env"
```

Environment probe:

```bash
/mnt/c/Windows/System32/cmd.exe /c "cd /d d:\Work\AV && conda run -n P2_env python experiments\maskrcnn_setup\probe_env.py"
```

Package freeze:

```bash
/mnt/c/Windows/System32/cmd.exe /c "cd /d d:\Work\AV && conda run -n P2_env python -m pip freeze"
```

Editable repo install inside `P2_env`:

```bash
/mnt/c/Windows/System32/cmd.exe /c "cd /d d:\Work\AV && conda run -n P2_env python -m pip install -e ."
```

## Install Notes

No packages have been installed into `AV_env`.

`P2_env` was cloned from `AV_env` first so the fallback torchvision path can be
tested without destabilizing the program environment.

The editable `argusvision` install was refreshed inside `P2_env` after cloning.
`AV_env` was not modified.

Observed pip warning during freeze/install:

```text
WARNING: Ignoring invalid distribution -illow (c:\users\panagiotis\appdata\roaming\python\python39\site-packages)
```

The warning comes from the user-site package directory, not from the conda env
site-packages path. It did not block the smoke run.

## Probe Result

`experiments/maskrcnn_setup/probe_env.json` records:

- torch `2.5.1+cu124`;
- CUDA available on NVIDIA GeForce RTX 3090 Ti;
- torchvision `0.20.1+cu124`;
- `mmdet`, `mmcv`, and `mmengine` unavailable.

Decision: use the torchvision fallback for the smoke proof. MMDetection is not
installed in the separate environment, and the existing CUDA-compatible
torchvision stack is sufficient to establish the P2 Mask R-CNN path without
risking the main `AV_env`.
