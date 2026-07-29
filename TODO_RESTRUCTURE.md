# TODO — Codebase Restructure (`src/` → installable `argusvision` package)

**Status: PLANNED, not started.** Full review done 2026-07-29 (ATHENA, REVIEWER pass over ~10.5k lines).
**Deadline: complete before P2 experiments begin (Sep 2026).** P0 (Zenodo) is independent — touches `dataset/` scripts only — and may proceed in parallel.

**Goals (user-stated, 2026-07-29):** modular — models will be added, but evaluation methods must always be the same; evaluation and operational modes for AV; clean and compartmentalized (data, results per experiment).

---

## Review findings (the *why* — verified against code, with locations)

| # | Finding | Evidence | Severity |
|---|---|---|---|
| F1 | Evaluation implemented **4×** with disagreeing algorithms: greedy matching in `YOLODetector.evaluate_dataset` (`src/models/yolo_detector.py:152`), Hungarian in `ArgusVisionEvaluation.py` and `ArgusVisionEvaluationV2.py`, own 753-line loop in `evaluate_sam.py`. Greedy vs Hungarian give different TP/FP on crowded scenes → YOLO benchmark and pipeline numbers are not strictly comparable. P2's baseline-vs-pipeline table is only defensible if every row uses one evaluator | 4 files | 🔴 blocks P2 |
| F2 | **Metric named `map` is macro-F1**, not mAP: `src/utils/metrics.py:176` (and `class_aps` aliased to `class_f1` at `:184`). Calling F1@IoU0.1 "mAP" at ISPRS = guaranteed reviewer hit. Thesis prose is fine (uses honest F1); the code/JSON label is the problem. **Bonus bug:** greedy matcher iterates predictions unsorted by confidence (`metrics.py:132`) — low-conf pred can steal a GT from a high-conf pred | `src/utils/metrics.py` | 🔴 reviewer risk |
| F3 | Model adapters entangled with evaluation: `YOLODetector` = 460 lines of predict + eval + aggregation + example-saving + GSD loading. Every new model (Mask R-CNN, YOLOv11-seg, SAM2…) would re-implement evaluation inside the model class. Counter-example done right: `SAMSegmenter` (65 lines, predict-only) | `src/models/yolo_detector.py` | 🟠 |
| F4 | Domain constants copy-pasted: `CLASS_NAMES` ×6 files, iSAID color table ×4 files, GSD-mapping loading ×4 places, `dataset/dota_gsd_mapping.json` hardcoded in library code | grep `"plane"`, `"0, 127, 255"`, `dota_gsd_mapping` | 🟠 |
| F5 | No run provenance: `results/` dirs are ad-hoc names; nothing records config/git SHA/env that produced them. Also: two dataloader homes (`src/utils/data_loader.py` vs `src/datasets/`), `sys.path.insert` hacks in all 8 experiment scripts, V1+V2 evaluators and V1+V2 viz coexisting with shim classes (`_ArrayLike`, `_OBBLike`, `SimpleDetection` in `ArgusVisionEvaluationV2.py:44-82`) | — | 🟠 |
| F6 | Operational/eval dual-mode already conceptually separated (`ArgusVisionInference` wraps core; vectorization/GeoJSON is TODO). Keep the idea, give it a real home (`runtime/`) | `src/ArgusVision/ArgusVisionInference.py` | 🟢 keep |

---

## Target structure

```
src/argusvision/                  # installable package: pyproject.toml + pip install -e .
│                                 #   (kills every sys.path hack)
├── data/                         # SINGLE source of domain truth
│   ├── constants.py              #   CLASS_NAMES, iSAID colors, GSD loading — defined once
│   ├── aerialfusecv.py           #   dataset class (images/labels/semantic_masks)
│   └── dota.py
├── models/                       # adapters ONLY — predict, nothing else
│   ├── base.py                   #   Detector/Segmenter protocols + standard
│   │                             #   Detection / InstanceMask dataclasses
│   ├── yolo.py                   #   VBB+OBB, predict-only (~120 of current 460 lines)
│   ├── sam.py                    #   current SAMSegmenter, near-unchanged
│   └── registry.py               #   "yolo11x-obb" → factory; experiments pick by name
├── pipeline/
│   ├── core.py                   #   detect → prompt → segment composition
│   └── prompts.py                #   OBB→VBB, center-point, per-class prompt config
├── evaluation/                   # THE evaluator — model-agnostic, frozen interface
│   ├── matching.py               #   Hungarian, one implementation, unit-tested
│   ├── metrics.py                #   IoU/Dice/P/R/F1 + real PR-curves/AP, honest names
│   ├── evaluator.py              #   consumes standard Detections/Masks + GT only
│   └── reporting.py              #   metrics.json + run-manifest writer
├── runtime/                      # OPERATIONAL mode — no eval imports
│   └── inference.py              #   ArgusVisionInference + future vectorize/GeoJSON
└── viz/                          #   one module (V2 absorbs V1)

experiments/                      # thin drivers + YAML configs, OUTSIDE the package
├── configs/                      #   e.g. p2_vbb_on_dota_hbb.yaml
└── run_evaluation.py             #   generic: config in → results/<experiment>/<run_id>/

results/<experiment>/<run_id>/    # every run writes manifest.json:
                                  #   {git_sha, config, env=AV_env, date, dataset_hash}
tools/dataset_construction/       # P0-bound scripts, separated from 55 GB data roots
```

**Load-bearing principle:** models emit standardized `Detection`/`InstanceMask`; the evaluator consumes only those. Adding a P2/P4 model = one ~80-line adapter, zero evaluation changes. That is the "evaluation always the same" requirement, expressed as architecture.

---

## Migration phases (do in order)

- [ ] **Phase 0 — Safety (5 min):** `git tag thesis-code-final` on current `dev` HEAD. Thesis-producing code stays reachable forever.
- [ ] **Phase 1 — Foundation (~1 day):** package skeleton, `pyproject.toml`, `pip install -e .` into `AV_env`; `data/constants.py` — collapse the 6×/4× duplication to one definition.
- [ ] **Phase 2 — Evaluation stack (~2–3 days). Do first among the code, freeze before any P2 number:** one Hungarian matcher (+ unit tests, incl. the confidence-ordering case from F2); metrics with honest names (`macro_f1`, not `map`); real PR curves / AP at IoU 0.1/0.3/0.5 (already a P2 deliverable per roadmap); run-manifest writer.
- [ ] **Phase 3 — Adapters & pipeline (~2 days):** slim `yolo.py` to predict-only; port `sam.py`; registry; port `pipeline/` + `runtime/`; absorb viz V1 into V2; delete V1 evaluator.
- [ ] **Phase 4 — Drivers & validation (~1–2 days):** config+driver experiment layer; **validation run:** re-evaluate YOLOv11x-OBB and the integrated pipeline under the new evaluator, diff against existing `results/` — the greedy→Hungarian delta *will* exist; document it deliberately now rather than let a reviewer find it.
- [ ] **Close-out:** ledger update (§ DECIDED + state log), roadmap check (no P2 date impact expected), delete this file's completed sections or the file.

**Total: ~1.5–2 weeks.**

---

## Decisions already taken (do not relitigate)

- Refactor, not rewrite — layering intent is sound, execution drifted during thesis sprint.
- Thesis numbers stay frozen as Phase 0; P2 re-runs everything under the new evaluator, so any matcher delta is P2's clean re-measurement, not a thesis correction.
- Environment stays `AV_env` (Windows conda); package installed with `pip install -e .` there. Agents run from WSL via interop (see `ATHENA_RISE.md` § ENVIRONMENTS).

## Open questions for the next session

1. Naming: package `argusvision` lowercase (PEP 8) vs keeping `ArgusVision` dir name — recommend lowercase, decide at Phase 1.
2. Whether `evaluate_ArgusVision_diagnostic.py` has anything worth porting or is thesis-era scaffolding to drop (leans drop — re-check at Phase 3).
3. Unit-test framework: plain `pytest` recommended; not yet in `AV_env` — add to spec + lock at Phase 1.

---

*Written 2026-07-29 by ATHENA (REVIEWER/STRATEGIST). Companion ledger entry in `ATHENA_STATE.md` § IN PROGRESS.*
