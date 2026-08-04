# ArgusVision Comparison: V2 vs Previous Method (V1)

Source files:
- `results/ArgusVision_v2_evaluation/evaluation_metrics_v2.json`
- `results/ArgusVision_evaluation/ArgusVision_metrics_summary.json`

## 1) Overall comparison

| Metric | V1 | V2 | Delta (V2-V1) |
|---|---:|---:|---:|
| Recall | 62.14% | 60.63% | -1.51 pp |
| Precision | 81.53% | 84.92% | +3.40 pp |
| F1 | 70.53% | 70.75% | +0.22 pp |
| Seg IoU (TP-only) | 67.91% | 67.14% | -0.77 pp |
| Seg DICE (TP-only) | 79.47% | 79.09% | -0.38 pp |
| Avg detection time (ms/img) | 171.83 | 103.30 | -39.88% |
| Avg segmentation time (ms/img) | 609.51 | 491.20 | -19.41% |
| Avg total time (ms/img) | 786.73 | 599.94 | -23.74% |

## 2) Per-class comparison (F1 + Seg IoU TP-only)

| Class | F1 V1 | F1 V2 | Delta F1 (pp) | IoU V1 | IoU V2 (TP-only) | Delta IoU (pp) |
|---|---:|---:|---:|---:|---:|---:|
| baseball-diamond | 75.13% | 70.37% | -4.76 | 67.57% | 68.81% | +1.23 |
| basketball-court | 56.25% | 62.00% | +5.75 | 82.21% | 80.68% | -1.53 |
| bridge | 40.26% | 35.89% | -4.37 | 56.17% | 58.12% | +1.95 |
| ground-track-field | 60.26% | 61.06% | +0.80 | 58.47% | 59.63% | +1.16 |
| harbor | 71.34% | 79.11% | +7.78 | 61.09% | 58.23% | -2.86 |
| helicopter | 43.75% | 46.67% | +2.92 | 40.99% | 42.28% | +1.30 |
| large-vehicle | 81.74% | 84.05% | +2.31 | 79.36% | 79.64% | +0.28 |
| plane | 74.49% | 76.51% | +2.02 | 54.09% | 49.96% | -4.13 |
| roundabout | 50.59% | 41.13% | -9.46 | 60.54% | 59.56% | -0.99 |
| ship | 71.91% | 72.57% | +0.66 | 63.22% | 62.02% | -1.20 |
| small-vehicle | 63.40% | 61.70% | -1.70 | 70.56% | 69.95% | -0.61 |
| soccer-ball-field | 50.43% | 49.57% | -0.87 | 87.08% | 87.38% | +0.29 |
| storage-tank | 60.85% | 53.43% | -7.42 | 71.76% | 73.65% | +1.90 |
| swimming-pool | 0.00% | 0.00% | +0.00 | 0.00% | 0.00% | +0.00 |
| tennis-court | 93.91% | 94.04% | +0.13 | 85.56% | 86.61% | +1.06 |

## 3) Key insights

- **V2 is much faster** in runtime:
  - detection: **-39.88%**
  - segmentation: **-19.41%**
  - total pipeline: **-23.74%**
- **Detection shifted toward higher precision**:
  - precision improved (**+3.40 pp**)
  - recall dropped (**-1.51 pp**)
  - net F1 slightly improved (**+0.22 pp**)
- **Segmentation quality on TP matches is very close to V1**:
  - IoU **-0.77 pp**
  - DICE **-0.38 pp**
- Biggest F1 gains in V2: **harbor (+7.78 pp)**, **basketball-court (+5.75 pp)**, **helicopter (+2.92 pp)**, **large-vehicle (+2.31 pp)**, **plane (+2.02 pp)**.
- Biggest F1 drops in V2: **roundabout (-9.46 pp)**, **storage-tank (-7.42 pp)**, **baseball-diamond (-4.76 pp)**, **bridge (-4.37 pp)**, **small-vehicle (-1.70 pp)**.
- **Swimming-pool remains a critical failure class** (F1 = 0 in both methods), suggesting class-specific intervention is needed (data quality/label density, class-wise thresholds, prompt strategy).
