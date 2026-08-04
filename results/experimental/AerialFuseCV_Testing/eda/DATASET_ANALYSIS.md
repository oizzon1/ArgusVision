# AerialFuseCV — Dataset Analysis

Generated 2026-08-04 07:31 UTC from `dataset\AerialFuseCV`. Every figure below is computed from the build's own artefacts; nothing is quoted.

**Mask definition:** matched iSAID instance clipped to the oriented box  
**Matching geometry:** oriented polygon, IoU ≥ 0.1, one-to-one within class  
**Annotation format:** DOTA native (headers, absolute px, class name, difficulty)  
**Box geometries:** labels_obb, labels_hbb

## Construction funnel

| Stage | Count |
|---|---|
| Images with both annotations | 1,869 |
| Source boxes (DOTA) | 127,843 |
| Source instances (iSAID) | 475,438 |
| **Paired objects** | **125,722** |
| Images retained | 1,862 (excluded 7) |
| Box pairing rate | 98.34% |
| Instance pairing rate | 26.44% |

The two rates differ because pairing is anchored on the boxes: iSAID annotates far more objects than DOTA, so most unpaired instances simply have no box. Detection benchmarking belongs on DOTA, segmentation on iSAID; AerialFuseCV serves unified detection→segmentation systems.

## Per split

| Split | Images kept | Boxes | Instances | Pairs |
|---|---|---|---|---|
| train | 1,406 | 98,990 | 358,166 | 97,590 |
| val | 456 | 28,853 | 117,272 | 28,132 |

## Per category

| Category | Boxes | Pairs | Rate | Share |
|---|---|---|---|---|
| ship | 37,028 | 36,854 | 99.5% | 29.3% |
| small-vehicle | 31,564 | 30,932 | 98.0% | 24.6% |
| large-vehicle | 21,356 | 20,765 | 97.2% | 16.5% |
| plane | 10,586 | 10,432 | 98.5% | 8.3% |
| harbor | 8,073 | 7,862 | 97.4% | 6.3% |
| storage-tank | 7,917 | 7,757 | 98.0% | 6.2% |
| tennis-court | 3,127 | 3,103 | 99.2% | 2.5% |
| bridge | 2,511 | 2,480 | 98.8% | 2.0% |
| swimming-pool | 2,176 | 2,147 | 98.7% | 1.7% |
| helicopter | 703 | 684 | 97.3% | 0.5% |
| baseball-diamond | 629 | 627 | 99.7% | 0.5% |
| basketball-court | 647 | 616 | 95.2% | 0.5% |
| roundabout | 578 | 562 | 97.2% | 0.4% |
| soccer-ball-field | 479 | 451 | 94.2% | 0.4% |
| ground-track-field | 469 | 450 | 95.9% | 0.4% |

![class distribution](figures/F2_class_distribution.png)

## Matching quality

IoU between the oriented box polygon and its matched instance — mean 0.671, median 0.715, 5th percentile 0.276, 95th 0.887.

Raising the acceptance threshold would cost:

| Threshold | Pairs lost | Share |
|---|---|---|
| ≥ 0.15 | 175 | 0.1% |
| ≥ 0.2 | 1,701 | 1.4% |
| ≥ 0.3 | 7,797 | 6.2% |
| ≥ 0.5 | 20,346 | 16.2% |

![matching iou](figures/F5_matching_iou.png)

## Object size

Instance area spans 10 to 1,080,673 px (median 631).

![area by class](figures/F6_area_by_class.png)

## Ground sample distance

1,861 images carry a GSD value, 0.000–4.496 m/px (median 0.260). Images whose DOTA header records `gsd:null` carry none.

![gsd](figures/F7_gsd.png)

## Objects not paired

2,121 boxes and 349,716 instances were not paired. Accounting is exact: pairs + discarded equals each source population.

| Reason | Count |
|---|---|
| `instance:no_box_of_class` | 303,451 |
| `instance:no_overlapping_box` | 44,021 |
| `instance:unassigned` | 2,244 |
| `box:no_overlapping_instance` | 1,572 |
| `box:below_iou_threshold` | 223 |
| `box:lost_to_one_to_one_assignment` | 215 |
| `box:no_mask_instance_of_class` | 111 |

## Annotation discrepancy between the sources

Comparing the box-clipped semantic mask against the exact iSAID instance over all 125,722 pairs, the two agree on only 21.7% of objects (mean IoU 0.918). The disagreement decomposes as:

| Cause | Share of disagreeing pixels |
|---|---|
| Extent — iSAID annotates beyond the box | 90.0% |
| Foreign — a neighbouring instance's pixels | 10.0% |
| Unlabelled | 0.0% |

16.3% of pairs contain at least some foreign pixels. The released masks eliminate this by construction — see `documentation/DECISION_reconciled_masks.md`.

| Category | Agreement | Pairs with foreign px | Disagreement that is extent |
|---|---|---|---|
| storage-tank | 0.857 | 27.6% | 85.5% |
| small-vehicle | 0.899 | 16.9% | 93.2% |
| bridge | 0.908 | 2.3% | 97.9% |
| large-vehicle | 0.912 | 14.1% | 93.5% |
| harbor | 0.920 | 1.5% | 99.5% |
| ship | 0.925 | 19.4% | 85.6% |
| baseball-diamond | 0.937 | 0.2% | 100.0% |
| basketball-court | 0.957 | 8.9% | 97.1% |
| soccer-ball-field | 0.960 | 0.9% | 99.9% |
| plane | 0.963 | 25.2% | 21.8% |
| ground-track-field | 0.967 | 0.2% | 100.0% |
| tennis-court | 0.969 | 0.4% | 100.0% |
| swimming-pool | 0.972 | 0.2% | 99.7% |
| roundabout | 0.982 | 0.0% | 100.0% |
| helicopter | 0.985 | 21.6% | 82.7% |

## Provenance

Build manifest: `dataset\AerialFuseCV/build_manifest.json`. Statistics: `dataset\AerialFuseCV/dataset_statistics.json`. Evidence for this analysis: `results/AerialFuseCV_Testing/`.
