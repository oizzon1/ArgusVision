# `dataset/` — data and the scripts that build, verify and inspect it

Everything here runs **from the repo root**, in `AV_env`:

```bash
python dataset/<script>.py --help
```

Data directories (`DOTA_v1/`, `iSAID/`, `AerialFuseCV_*/`) are git-ignored;
only `*.py`, `*.md` and small `*.json` are tracked.

---

## Construction and verification

| Script | Purpose |
|---|---|
| `build_aerialfusecv.py` | **The builder.** One pass from DOTA v1.0 + iSAID to AerialFuseCV. Oriented-polygon matching, one-to-one assignment, reconciled masks, DOTA-native annotations, both box geometries. Internal tool — the script shipped with the deposit is written separately, to the descriptor's scope. |
| `verify_build.py` | Compares a build against a reference directory across three levels (structural, content, statistical). Used to prove port fidelity. |
| `measure_discrepancy.py` | Decomposes DOTA/iSAID annotation disagreement per pair into extent, foreign-instance and unlabelled pixels. Evidence behind `documentation/DECISION_reconciled_masks.md`. |
| `scan_isaid_colours.py` | Exhaustive audit of iSAID mask encodings — verifies the colour table, counts true instances, checks no instance spans two classes. |
| `analyze_aerialfusecv.py` | EDA → `DATASET_ANALYSIS.md` + figures, computed only from build artefacts. |
| `extract_gsd_mapping.py` | Regenerates `DOTA_v1/dota_gsd_mapping.json` from DOTA headers. Keep — `argusvision.data.constants` and the test suite depend on that file. |
| `convert_dota_to_yolo_obb.py` · `convert_dota_to_yolo_vbb.py` | Produce the YOLO-format DOTA conversions used by detector benchmarking. Note the conversion is **lossy** — it drops the `difficult` flag, `gsd:` and `imagesource:` — which is why AerialFuseCV itself stays DOTA-native. |

## Inspection and visualization

All verified against `AerialFuseCV_reconciled` on 2026-08-03.

| Script | Purpose |
|---|---|
| `visualize_aerialfusecv_4tile.py` | **The general-purpose assessment view.** Four panels for one image: GT boxes as HBB, GT boxes as OBB, semantic masks, instance masks. Shows at a glance whether boxes, classes and instance identity all agree. |
| `visualize_annotation.py` | Flexible single-file viewer — point it at any label or mask file and it resolves the matching image and renders the overlay. |
| `inspect_gt_masks.py` | Side-by-side comparison of two ground-truth derivations (box-clipped semantic vs exact instance), with a difference panel. Selects the best- and worst-agreeing instances. |
| `create_dataset_overlays.py` | Batch overlays across a whole split — boxes plus mask, one image per sample. |
| `visualize_dota_boxes.py` | Source-level view of DOTA annotations: image, OBB overlay, HBB overlay. Operates on `DOTA_v1/` directly. |
| `visualize_obb_vs_vbb_thesis.py` | Publication-quality two-panel OBB-vs-HBB comparison figure. Paper material for the parked oriented-vs-horizontal study. |

---

## Removed 2026-08-03

Superseded by the rebuild, and recoverable from the `legacy_thesis` branch if
ever needed:

`refine_aerialfusecv.py` (→ `build_aerialfusecv.py`) ·
`merge_aerialfusecv_refined.py` (merged a directory that no longer exists) ·
`analyze_isaid_instance_colors.py` (→ `scan_isaid_colours.py`) ·
`inspect_instance_mask.py` (ad-hoc probe, → `scan_isaid_colours.py`) ·
`visualize_excluded_images.py` (diffed two deleted directories; the excluded
list now lives in `dataset_statistics.json`) ·
`visualize_aerialfusecv_refined.py` (pointed at a deleted directory; covered by
the 4-tile view).

The whole thesis-era `src/` tree was removed in the same pass — `models/`,
`utils/`, `experiments/`, `datasets/` and `_legacy_ArgusVision/` — all
superseded by the `argusvision` package and all preserved on `legacy_thesis`.
`evaluate_sam.py` went with them: the GT-prompt SAM benchmark it implements is
still wanted for P4, and will be ported from the branch as a driver kind rather
than carried here as code that no longer runs.
