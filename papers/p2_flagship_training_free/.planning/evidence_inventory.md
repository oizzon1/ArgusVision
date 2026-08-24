# P2 Evidence Inventory

This file lists what can already be cited in the P2 paper planning draft. It does **not** mean every item is final paper evidence; final Results prose must use runs produced under the final P2 protocol.

## Dataset and Evaluation Contract

| Evidence | Source | Use in P2 |
|---|---|---|
| Corrected AerialFuseCV build has 125,722 paired objects, 1,862 retained images, 98.34% box-side pairing rate. | `results/experimental/AerialFuseCV_Testing/FINDINGS.md` | Dataset description once P1/Zenodo DOI exists. |
| Build verification reproduced the precursor object-for-object before correction: 1,857 label files and 1,857 masks, 0 mismatches, pair delta +0. | `results/experimental/AerialFuseCV_Testing/FINDINGS.md`; `results/experimental/AerialFuseCV_Testing/build_verification/verification_report.json` | Establishes construction change was controlled. |
| Deposit verification passed 7,448/7,448 files. | `results/experimental/AerialFuseCV_Testing/deposit_verification_v2/deposit_verification.json` | Reproducibility statement after DOI release. |
| Manual alignment audit judged 200/200 sampled pairs, with 0 wrong pairs observed and 2 ambiguous. | `results/experimental/AerialFuseCV_Testing/alignment_audit/alignment_audit_report.json` | Supports paired-object validity. |
| Pairs-only scope and discard accounting rationale are decided. | `documentation/DECISION_unpaired_annotations.md` | Methods and Limitations. |
| Reconciled masks are matched iSAID instance clipped to the DOTA oriented box. | `documentation/DECISION_reconciled_masks.md` | Ground-truth definition for cascade evaluation. |

## Existing Training-Free Cascade Evidence

| Evidence | Source | Use in P2 |
|---|---|---|
| YOLOv11x-OBB -> SAM pipeline on validation split, polygon-mode validation: IoU-0.5 detection micro precision 0.8469, recall 0.6046, micro F1 0.7055, macro F1 0.5947, mean AP 0.4742; TP-only mask IoU 0.6639, GT-anchored mask IoU 0.4149. | `results/experimental/restructure_validation_pipeline_polygon/20260729_181306_106c7af/metrics.json` | Baseline anchor only; rerun under final P2 protocol before final Results. |
| Reconciled-mask evaluation shifted segmentation by about 0.1 pp versus clip-derived GT; effect is correctness, not a performance jump. | `results/experimental/AerialFuseCV_Testing/FINDINGS.md` | Explains why P2 uses released instance GT. |
| SAM GT-prompt benchmark exists for ViT-B/L/H with box and point prompts. | `results/experimental/sam_evaluation/` | Candidate segmenter-ceiling evidence; verify/rerun before final Results. |

## Detector Protocol Evidence

| Evidence | Source | Use in P2 |
|---|---|---|
| Full-image YOLOv11x-OBB at IoU 0.5: micro precision 0.8525, recall 0.6065, micro F1 0.7087, macro F1 0.6022, mean AP 0.4869. | `results/experimental/f6b_tiling_yolo11x_obb/REPORT.md` | Detector ablation, not final until seam/fusion and operating-point handling. |
| Tiled YOLOv11x-OBB at IoU 0.5: micro precision 0.7399, recall 0.8516, micro F1 0.7918, macro F1 0.6801, mean AP 0.6687. | `results/experimental/f6b_tiling_yolo11x_obb/REPORT.md` | Strong evidence that tiling should be the primary detector protocol. |
| Scale-sensitive recall improved under tiling at IoU 0.5 for small-vehicle, ship, plane, with more modest large-vehicle gain. | `results/experimental/f6b_tiling_yolo11x_obb/REPORT.md` | Supports scale-handling discussion. |
| Open defect: tile-border truncation can duplicate seam-crossing objects; quantify before final paper numbers. | `results/experimental/f6b_tiling_yolo11x_obb/REPORT.md` | F8 gap; must not be hidden. |

## Supervised Baseline Readiness

| Evidence | Source | Use in P2 |
|---|---|---|
| Mask R-CNN Windows path selected: torchvision fallback in `P2_env`; no changes to `AV_env`. | `results/experimental/f6_maskrcnn_setup/REPORT.md` | Methods readiness, not performance. |
| A 50-iteration CUDA smoke run completed with finite loss and declining first-window to last-window average loss. | `results/experimental/f6_maskrcnn_setup/REPORT.md`; `results/experimental/f6_maskrcnn_setup/evidence/smoke_train_50iter.jsonl` | Feasibility only. Do not cite as model quality. |
| AerialFuseCV-to-COCO converter exists for Mask R-CNN input. | `dataset/convert_aerialfusecv_to_coco.py`; `results/experimental/f6_maskrcnn_setup/REPORT.md` | Implementation path for F7. |

## Related-Work Positioning

| Evidence | Source | Use in P2 |
|---|---|---|
| Existing iSAID supervised and SAM-related work does not kill ArgusVision but narrows the claim. | `ArgusVision_Strategic_Planning/Context/iSAID_baselines_positioning_NOTES.md` | Related Work and Introduction. |
| Competitive review says ArgusVision competes on paired contract and cascade failure science, not another SAM wrapper. | `ArgusVision_Strategic_Planning/Context/competitive_landscape_2026-08_NOTES.md` | Claim discipline. |
| AerOSeg is open-vocabulary semantic segmentation with SAM as feature guidance, not a detector-prompted instance cascade. | `ArgusVision_Strategic_Planning/Context/2504.09203v1_AerOSeg_REVIEW.md` | Related Work boundary. |
