# P2 Flagship Paper — Cascade Reliability

**Working title:** Cascade reliability for training-free aerial detection-to-segmentation

**Status:** started 2026-08-24 under `P2-START`.

**Submission intent:** main journal paper after the AerialFuseCV dataset release. The Zenodo DOI is a dependency for submission and final citations, not a reason to delay the P2 paper skeleton, experiment matrix, or methods writing.

## Scope

P2 is the main methods/evaluation paper. It asks whether a pretrained aerial detector can act as the object interface to a promptable segmenter when dense masks are unavailable or expensive.

This paper is **not** a novelty claim for YOLO+SAM, SAM in remote sensing, iSAID segmentation, or OBB prompts. It is a cascade-reliability paper built on:

- AerialFuseCV's paired object-level detect-to-segment contract;
- a frozen evaluator that separates detector failure from mask quality;
- a training-free YOLOv11x-OBB -> SAM baseline;
- supervised Mask R-CNN and YOLOv11-seg baselines on the same paired dataset;
- confidence filtering, PR curves, and failure analysis.

## Current Files

| File | Purpose |
|---|---|
| `DRAFT_P2.md` | Manuscript skeleton; prose sections are placeholders until evidence is final. |
| `.planning/argument_map.md` | Claim structure and hostile-review constraints. |
| `.planning/evidence_inventory.md` | Existing results that can support the paper, with source paths. |
| `.planning/experiment_gap_list.md` | Work needed before P2 results can be written. |

## Non-Negotiables

- Every experimental number in the paper must trace to `results/`.
- The MSc thesis is not a source.
- P1/Dataset DOI is inserted when the release is public, just before P1/P2 submission work needs it.
- Full-image detector results are an ablation; the current evidence points to tiled inference as the primary detector protocol, pending seam/fusion quantification.
