## 📊 Experiment-Dataset Mapping Summary

Based on your THESIS_NOTES.md, here's the comprehensive list of all experiments and their datasets:

---

### __PHASE 1: YOLO Baseline Evaluation__

| Experiment | Dataset | Type | Images | Details | |------------|---------|------|--------|---------| | __YOLO-OBB Evaluation__ | DOTA v1 validation | ✅ __ORIGINAL__ | 458 | Standard DOTA val split, 28,853 GT instances, 15 classes | | __YOLO-VBB Evaluation__ | DOTA v1 validation | ✅ __ORIGINAL__ | 458 | Same images, 18,785 GT instances (3 mapped COCO classes) |

---

### __PHASE 2: SAM-Only Benchmark__

| Experiment | Dataset | Type | Images | Details | |------------|---------|------|--------|---------| | __SAM-Only (6 configs)__ | AerialFuseCV_Refined_Merged | 🔧 __MODIFIED__ | 1,783 | Train+val merged, 114,870 bbox-mask pairs, 13 classes |

__Why Modified?__

- Combined DOTA v1 (OBB labels) + iSAID (segmentation masks)
- Refined to ensure 1:1 bbox-mask correspondence
- Excluded storage-tank & bridge (0% bbox-mask match rate)

---

### __PHASE 3: ArgusVision Pipeline__

| Experiment | Dataset | Type | Images | Details | |------------|---------|------|--------|---------| | __ArgusVision (Box prompts)__ | AerialFuseCV_Refined/val | 🔧 __MODIFIED__ | 438 | Val split only, 23,463 GT instances, 13 classes | | __Ablation: Point vs Box__ | AerialFuseCV_Refined/val | 🔧 __MODIFIED__ | 438 | Same as above |

---

### __Dataset Lineage Summary__

```javascript
ORIGINAL DATASETS
├── DOTA v1 (2,806 images, 188K instances, OBB annotations)
└── iSAID (same images, segmentation masks)
        ↓
    FUSION PROCESS
        ↓
🔧 MODIFIED DATASETS
├── AerialFuseCV (1,869 images, DOTA labels + iSAID masks)
│       ↓
│   REFINEMENT (bbox-mask matching, quality control)
│       ↓
├── AerialFuseCV_Refined/train (1,345 images)
├── AerialFuseCV_Refined/val (438 images)
│       ↓
│   MERGE (for SAM evaluation)
│       ↓
└── AerialFuseCV_Refined_Merged (1,783 images, 114,870 pairs)
```

---

### __Quick Reference Table__

| Phase | Experiment | Dataset | Original/Modified | |-------|------------|---------|-------------------| | 1 | YOLO-OBB (10 models) | DOTA v1 val | ✅ Original | | 1 | YOLO-VBB (24 models) | DOTA v1 val | ✅ Original | | 2 | SAM-ViT-H Box | AerialFuseCV_Refined_Merged | 🔧 Modified | | 2 | SAM-ViT-H Point | AerialFuseCV_Refined_Merged | 🔧 Modified | | 2 | SAM-ViT-L Box | AerialFuseCV_Refined_Merged | 🔧 Modified | | 2 | SAM-ViT-L Point | AerialFuseCV_Refined_Merged | 🔧 Modified | | 2 | SAM-ViT-B Box | AerialFuseCV_Refined_Merged | 🔧 Modified | | 2 | SAM-ViT-B Point | AerialFuseCV_Refined_Merged | 🔧 Modified | | 3 | ArgusVision (Box) | AerialFuseCV_Refined/val | 🔧 Modified | | 3 | Ablation (Point) | AerialFuseCV_Refined/val | 🔧 Modified |

---

### __Why Different Datasets?__

1. __YOLO (Phase 1):__ Uses original DOTA because we're evaluating pretrained detection models (standard benchmark protocol)

2. __SAM (Phase 2):__ Uses modified AerialFuseCV because we need GT segmentation masks (not available in original DOTA)

3. __ArgusVision (Phase 3):__ Uses refined AerialFuseCV/val to enable quantitative evaluation with ground-truth masks
