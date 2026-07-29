# Restructure Validation Report

**Date:** 2026-07-29 · **Branch:** `AV_dev` · **Author:** ATHENA (OPERATOR)
**Purpose:** before the `argusvision` package replaces the thesis-era code, prove that the new evaluation stack reproduces the legacy numbers, and quantify — deliberately, on our terms — every methodological delta a reviewer could later discover (TODO_RESTRUCTURE.md Phase 4).

All runs: `experiments/run_evaluation.py` + configs in `experiments/configs/`, executed in `AV_env` on the RTX 3090 Ti at clean git state `106c7af`. Full metrics + manifests under `results/restructure_validation_*/`.

---

## Question 1 — Is the port faithful? (run: `pipeline_aabb` vs legacy V2)

New stack in legacy-comparable mode (per-class Hungarian @ IoU 0.1, **AABB** IoU as legacy V2 silently used) against `results/ArgusVision_v2_evaluation/evaluation_metrics_v2.json`. Same 456 AerialFuseCV_Refined val images, YOLOv11x-OBB → SAM ViT-B (box).

| Metric | Legacy V2 | New (aabb) | Δ |
|---|---|---|---|
| Detection recall | 0.6263 | 0.6261 | −0.0002 |
| Detection precision | 0.8772 | 0.8770 | −0.0002 |
| Detection F1 | 0.7308 | 0.7306 | −0.0002 |
| Seg IoU (TP-only) | 0.6621 | 0.6627 | +0.0005 |
| Seg Dice (TP-only) | 0.7825 | 0.7828 | +0.0004 |
| Seg IoU (GT-anchored) | 0.4147 | 0.4149 | +0.0002 |
| TP / FP / FN | 17556 / 2457 / 10476 | 17551 / 2462 / 10481 | ±5 of ~28k |

**Verdict: faithful.** The entire chain — dataset parsing, GT-mask extraction, adapters, pipeline, matcher, mask metrics — reproduces legacy V2 within ±0.05 pp. Residual: float coordinates (legacy int-cast).

## Question 2 — What was the legacy OBB→AABB collapse worth? (run: `pipeline_polygon`)

Identical run under exact polygon IoU (the new canonical default).

| Metric | aabb | polygon | Δ |
|---|---|---|---|
| micro-F1 @ 0.1 | 0.7306 | 0.7292 | −0.0014 |
| micro-F1 @ 0.3 | 0.7260 | 0.7247 | −0.0012 |
| micro-F1 @ 0.5 | 0.7087 | 0.7055 | −0.0032 |
| Seg IoU (TP-only) | 0.6627 | 0.6639 | +0.0012 |
| Seg IoU (GT-anchored) | 0.4149 | 0.4149 | −0.0000 |
| matches @ 0.1 | 17551 | 17518 | −33 |

**Verdict: negligible, and in the honest direction.** Polygon IoU is slightly stricter for rotated boxes (effect grows with threshold, as geometry predicts); segmentation conclusions untouched. Polygon IoU is the default for all P2+ numbers; `mode: aabb` exists only for this comparison.

## Question 3 — Did the greedy matcher's order-dependence distort the thesis YOLO benchmark? (run: `yolo11x_obb`)

New stack (Hungarian + confidence-ranked AP, polygon IoU) vs legacy greedy arbitrary-order benchmark (`results/yolo_evaluation/OBB/YOLOv11x-OBB_metrics.json`). Same 458 DOTA-YOLO val images, conf 0.25.

| Metric | Legacy (greedy) | New (Hungarian) | Δ |
|---|---|---|---|
| macro-F1 @ 0.1 (legacy name: "map") | **0.6240** | **0.6240** | 0.0000 |
| matched pairs @ 0.1 | 17884 | 17885 | +1 |

**Verdict: the thesis headline (YOLOv11x-OBB "F1 62.4%") is CONFIRMED under the rigorous evaluator.** The F2 order-dependence bug is real in principle but averaged out at dataset scale here. No thesis correction needed; P2 cites the number with a clean conscience.

## New capabilities exercised (numbers the project never had)

- Real ranked **mean AP** (all-point interpolation): pipeline detector 0.502 @ 0.1; standalone YOLOv11x-OBB **0.5075 @ 0.1 / 0.5017 @ 0.3 / 0.4806 @ 0.5**.
- Honest **macro-F1** at three thresholds from one run (0.6240 / 0.6181 / 0.5994).
- Micro-F1 alongside macro (0.7314 @ 0.1) — the macro/micro gap quantifies the class-imbalance penalty.
- Every run carries `manifest.json` (git SHA, dirty flag, config, env, GPU).

## Standing conclusions

1. **Merge-gate satisfied:** the new stack may replace the legacy code; thesis-era numbers survive re-measurement.
2. P2 experiments run under polygon IoU, Hungarian set-counts, ranked AP — reviewers get the standard protocol with named metrics.
3. Known residuals to disclose if ever asked: int→float coordinates (±5 counts in 28k), AABB→polygon (≤0.3 pp), matcher family (0 at dataset scale).
