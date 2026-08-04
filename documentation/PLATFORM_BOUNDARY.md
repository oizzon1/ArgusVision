# The platform boundary

**Decision, 2026-08-04.** ArgusVision is a platform, and the repository has to
read like one — including to a reader who arrives years from now, or to a
reviewer who asks what exactly was released. Research one-offs must not
accumulate inside it.

## The rule

> **Would a *different* experiment need this code?**
> Yes → it belongs in the package. No → it is configuration.

That is the whole test. It is deliberately about reuse, not about authorship,
novelty, or which paper paid for the work.

## Where things live

| Location | Holds | In git |
|---|---|---|
| `src/argusvision/` | The platform: datasets, model adapters, pipeline, frozen evaluation stack, tiled inference, CLI | yes |
| `experiments/configs/*.yaml` | One file per experiment: which model, which data, which protocol | yes |
| `experiments/baselines/<model>/` | Training and setup scripts for comparison models — run by hand, not imported | yes |
| `results/<experiment>/<run_id>/` | Every number, with `manifest.json`, `status.json`, `metrics.json`, and any report | metrics/manifests only |
| `dataset/` | Dataset construction and verification tooling for AerialFuseCV | scripts only |
| `papers/` | One WTF-P project per paper; `deposit/` scripts ship to users | yes |

Scripts never live in `results/`; evidence never lives in `experiments/`.

## Why the boundary is drawn at reuse

The codebase has already paid for the alternative. Before the restructure,
evaluation was implemented four times across near-duplicate scripts, each with
its own matcher and its own idea of what `mAP` meant. Two of them disagreed,
and the disagreement was invisible because nothing forced them to be the same
code. Every capability left outside the package is an invitation to write that
second implementation.

The same reasoning retired the F6b tiling runner. Tiling started as a
479-line experiment script; when it became the P2 detector protocol it became
platform capability, and keeping the script would have meant two copies of the
tile-origin, coordinate-shift and rotated-NMS logic. It moved to
`argusvision/runtime/tiling.py`, the experiment became two configs that differ
only in a `tiling:` block, and the original runner stayed in git history at
commit `95e3aa9`.

## What this buys

- **Comparability.** Every model is scored through one evaluator. A baseline
  and the cascade differ in the model, not in the measurement.
- **A releasable artefact.** `pip install argusvision` gives a working
  platform; the experiments are data about how it was used.
- **Provenance.** Configs are small, readable and diffable, so what changed
  between two runs is visible without reading code.

## Baselines are not an exception

Mask R-CNN and YOLO-seg are competitors, not components — but their *inference
adapters* still belong in the package, under `models/baselines/`. The evaluator
has to instantiate them, and a baseline scored through a different code path
than the system it is compared against proves nothing. Their *training* is
one-off and stays in `experiments/baselines/`.

The naming carries the distinction the directory structure otherwise loses:
`models/baselines/maskrcnn.py` is unambiguous about what it is.
