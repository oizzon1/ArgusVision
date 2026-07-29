# `legacy_thesis` — Frozen Phase-0 Codebase

**This branch is a preservation snapshot. Do not develop on it.**

It holds the ArgusVision codebase in the structure that produced the MSc
thesis results (defended 8 July 2026, grade 10/10) — the flat `src/` layout
with `ArgusVision/`, `models/`, `utils/`, `datasets/`, `experiments/`, before
the July 2026 restructure into the installable `argusvision` package.

## Why this branch exists

Active development moved to a restructured package on `dev` (see
`documentation/RESTRUCTURE_VALIDATION.md` there). The thesis-era code remains
the historical record of how every published Phase-0 number was produced, so
it stays reachable by branch name, not only by tag.

## What it is, exactly

- **Base:** tag `thesis-code-final` (commit `11ba53c`) — the last commit
  before the restructure began.
- **Chosen over `ArgusVision_main`** (which is 6 commits older) because this
  point includes the corrections that make the legacy code *runnable*:
  the `.gitattributes` line-ending policy, the corrected
  `ArgusVision_environment.yml`, and `ArgusVision_environment.lock.txt`.
  `ArgusVision_main` predates those and its environment spec could not
  rebuild the environment that produced the thesis results.
- **Plus one restoration:** `src/datasets/` (the DOTA and AerialFuseCV
  dataloaders) was never committed during the thesis — unanchored
  `.gitignore` patterns (`datasets/`) silently excluded it, so it is absent
  from both the tag and `ArgusVision_main`. It survived only on one disk.
  The original files were recovered and committed here so this snapshot is
  complete and actually importable. This was restructure finding **F8**.

## Known defects preserved deliberately

These are *not* to be fixed here; they are documented in `TODO_RESTRUCTURE.md`
and fixed on `dev`:

- **F1** evaluation implemented four times with disagreeing matchers.
- **F2** the metric named `map` is macro-F1; the greedy matcher iterates
  predictions unsorted by confidence.
- **F7** GSD loading is a silent no-op (hardcoded path does not exist).
- **F9** pipeline masks misalign with detections under mixed prompt configs.

Validation on `dev` confirmed these defects did not change the thesis
headline numbers at dataset scale.

## Environment

`AV_env` (Windows conda). Spec: `ArgusVision_environment.yml`; exact closure:
`ArgusVision_environment.lock.txt`. Run all scripts from the repo root.
Note this snapshot predates `pytest` being added to the environment.
