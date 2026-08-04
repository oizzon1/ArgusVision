# results/

Every number this program publishes lives here, next to the manifest that
produced it. The thesis is not a source; `results/` is.

## The two trees

| Directory | Holds | Written by |
|---|---|---|
| `experimental/` | Runs that produced measurements — metrics, manifests, run heartbeats, audits, and the reports that interpret them | `argusvision run <config>` |
| `visualization/` | Rendered figures that are not the output of a measured run: examples, overlays, comparison plates, paper figures | the visualization scripts in `dataset/` and `src/argusvision/viz/` |

**Scripts never live here.** `results/` is evidence. Code that produces it
lives in the package, in `dataset/`, or in `experiments/baselines/` — see
`documentation/PLATFORM_BOUNDARY.md`.

## Where visualizations go

The split is by *origin*, not by file type:

- A figure produced **by an experiment** stays inside that experiment's
  directory — best/worst example plates, per-run overlays, qualitative
  evidence. They are part of the run's findings and separating them from the
  metrics they illustrate is how a figure ends up captioned with the wrong
  numbers.
- A figure produced by a **standalone rendering script** goes in
  `visualization/`.

So `experimental/ArgusVision_evaluation/examples/best|worst` and
`experimental/AerialFuseCV_Testing/gt_mask_comparison/best|worst` stay where
they are, while `visualization/dota_example/` and
`visualization/thesis_figures/` are their own thing.

## Run layout

```
experimental/<experiment>/<UTC-timestamp>_<git-sha>/
    manifest.json     git SHA, resolved config, environment — written BEFORE inference
    status.json       live heartbeat: progress, ETA, phase, final state
    metrics.json      the numbers
```

No manifest, no number. The timestamp and SHA in the directory name mean two
runs of the same config never collide and are always attributable.

## What git keeps

`results/**` is ignored except metrics, provenance and prose:
`*_metrics.json`, `metrics.json`, `metrics_summary.json`, `*manifest.json`,
`*_audit.json`, `dataset_statistics.json`, and every `.md`.

Anything else a run needs kept — environment freezes, probe output, training
loss logs — goes in an **`evidence/`** folder inside the run and is tracked
whatever its extension:

```
experimental/f6_maskrcnn_setup/
    REPORT.md                    tracked (prose)
    evidence/pip_freeze.txt      tracked (evidence/)
    evidence/probe_env.json      tracked
    coco_smoke/                  NOT tracked — regenerable payload
```

One convention rather than a growing list of per-filename exceptions. Keep
`evidence/` small: if it is regenerable in bulk, it belongs outside.

Imagery and checkpoints stay local — every published figure must be
regenerable from the script and the manifest beside it.
