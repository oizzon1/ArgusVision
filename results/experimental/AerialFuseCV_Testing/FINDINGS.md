# AerialFuseCV Rebuild — Consolidated Findings

**Date:** 2026-07-31. **Evidence:** everything referenced below lives in this
directory, with run manifests. **Decisions:** `documentation/DECISION_*.md`.

---

## 1. The precursor construction was reproduced exactly, then improved

A build in regression mode reproduced the earlier dataset **object for object**:
1,857 label files and 1,857 masks compared, **0 mismatches, pair delta +0**
(`build_verification/`). Port fidelity is therefore proven, not assumed — so
every subsequent difference is attributable to a deliberate change.

## 2. The axis-aligned hull was costing real pairs

DOTA is genuinely oriented: **95.5%** of boxes are rotated, median **17.1°**
off-axis. Matching against the hull rather than the polygon inflates the
matching region by a median **1.83×** the true box area (68% exceed 1.5×, 37%
exceed 2×), measured over 21,265 boxes.

Switching to polygon matching plus one-to-one assignment gained:

| | precursor | corrected |
|---|---|---|
| Pairs | 125,102 | **125,722** (+620) |
| Images retained | 1,857 | **1,862** (+5) |
| Box pairing rate | 97.86% | **98.34%** |
| Matched-IoU median | 0.468 | **0.715** |

Largest gains where orientation matters most — **harbor +548** (90.6%→97.4%),
**plane +265**. Small negative deltas in ship, small-vehicle and large-vehicle
are the one-to-one constraint removing duplicate claims on one mask: a
correctness gain that presents as a smaller number.

## 3. The two sources disagree about what an object *is*

Comparing box-clipped semantic ground truth against exact iSAID instances over
**all 125,722 pairs** (`annotation_discrepancy/`), they agree on only **21.7%**
of objects (mean IoU 0.918). Decomposed by pixel:

| Cause | Share |
|---|---|
| **Extent** — iSAID annotates beyond the box | **90.0%** |
| **Foreign** — a neighbouring instance's pixels | **10.0%** |
| Unlabelled | 0.0% |

**16.3% of pairs contain at least some foreign pixels.**

Visual inspection (`gt_mask_comparison/`) showed the worst cases have
`extra = 0px` — pure extent difference, not contamination:

- **baseball-diamond** — DOTA boxes the infield, iSAID the whole field (100% extent)
- **harbor** — DOTA the pier, iSAID the pier plus platforms (99.5% extent)
- **P0262 ship** — one iSAID instance covering a boat, its dock, **and a second
  boat**; verified as one colour in one connected component, so a genuine iSAID
  annotation error rather than an artefact of our extraction

Contamination concentrates exactly where density is highest: storage-tank
27.6%, plane 25.2%, helicopter 21.6%, ship 19.4% — against ≤2.3% for bridge,
harbor, tennis-court and the sports fields.

## 4. Reconciled masks, and what they are worth

Released masks are the **matched iSAID instance clipped to its oriented box**.
Extent is handled by the clip; foreign pixels are impossible by construction,
since the mask starts from the matched instance rather than the class mask.

Measured effect on the pipeline, same dataset and models, only the ground-truth
derivation differing:

| | clip-derived GT | released instance GT |
|---|---|---|
| Seg IoU (TP-only) | 0.6627 | **0.6639** (+0.0012) |
| Seg IoU (GT-anchored) | 0.4154 | **0.4161** (+0.0007) |
| Detection | unchanged | unchanged |

**The magnitude is small — about 0.1 pp — and that should be stated plainly.**
The value is correctness by construction, not a performance jump.

**But the per-class pattern independently validates §3.** Gains appear only in
the classes the discrepancy measurement flagged as contaminated — plane +0.004,
storage-tank +0.002, small-vehicle +0.002, large-vehicle +0.002 — and are
**exactly 0.000** for harbor, bridge, tennis-court, roundabout and the sports
fields, whose foreign-pixel incidence is near zero. Two independent
measurements agreeing on which classes are affected.

## 5. Dataset improvements also raise detection metrics

Comparing the corrected build against the precursor with everything else fixed
(`pipeline_aerialfusecv_v1` vs the polygon-mode baseline): recall +0.0019,
**precision +0.0057**, F1 +0.0033, **mean AP +0.0131**, at every IoU threshold.
Precision gains most because recovered pairs mean detections previously charged
as false positives — for finding real objects the pairing had dropped — now
count as true positives.

## 6. Residuals, honestly stated

- **2.61% of pairs (3,283)** reference an instance whose colour spans multiple
  disconnected components — partly occlusion splits, partly iSAID colour reuse
  that our colour-keyed extraction merges. Clipping bounds the damage; the
  extraction should still be made component-aware.
- **Seven images remain excluded**, all because DOTA annotates them with 0–2
  boxes while iSAID annotates them densely. Not a matching failure: four
  contain no DOTA boxes at all.
- **One image (P2686) has no GSD**, because DOTA's own header records
  `gsd:null`.

## 7. Evidence index

| Artefact | What it establishes |
|---|---|
| `isaid_colour_audit/` | Colour table complete and correct; 475,438 instances; zero spanning >1 class |
| `build_verification/` | Regression build reproduces the precursor exactly |
| `aerialfusecv_build/` | Build manifests and statistics for every run |
| `annotation_discrepancy/` | The 125,722-pair discrepancy decomposition |
| `gt_mask_comparison/` | 10 best + 10 worst ground-truth comparisons |
| `pipeline_aerialfusecv_v1/` | Pipeline on the corrected build |
| `pipeline_aerialfusecv_reconciled/` | Pipeline on reconciled masks, both GT derivations |
| `eda/` | `DATASET_ANALYSIS.md` and figures |
