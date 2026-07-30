# TODO — AerialFuseCV Single-Step Recreation Script + Verified EDA

**Status: PLANNED, not started.** Investigation done 2026-07-30 (ATHENA, OPERATOR).
**Blocks: P0 Zenodo release (Aug 2026), and therefore P1 submission.**
Closes `ATHENA_STATE.md` OPEN 6.

**Goal.** One script that builds AerialFuseCV from the official DOTA v1.0 and
iSAID downloads in a single pass, plus one EDA report whose every number is
recomputed and verified. Replaces the historical two-step process (combine →
refine), of which the combine step was never version-controlled.

---

## What we have to work with

| Asset | State | Role |
|---|---|---|
| `dataset/DOTA_v1/{train,val}/{images,labels}` | 1,411 / 458 | source |
| `dataset/iSAID/{train,val}/{semantic_masks,instance_masks}` | 1,411 / 458 each | source |
| `dataset/AerialFuseCV/` | 1,411 + 458 = **1,869** | **ground truth for the combine step** |
| `dataset/AerialFuseCV_Refined/` | 1,401 + 456 = **1,857** | **ground truth for the whole pipeline** |
| `dataset/refine_aerialfusecv.py` | works | reference implementation of matching |
| `dataset/convert_dota_to_yolo_obb.py` | works | separate YOLO-OBB conversion (not on this path) |

**The decisive advantage: both historical outputs are still on disk.** The new
script does not have to be trusted — it can be proven, file by file, against
the dataset that produced the thesis results. Any divergence is a bug in the
new script or an undocumented step in the old one, and either way we want to
know. Do the verification before deleting anything.

---

## Findings from the investigation

| # | Finding | Consequence |
|---|---|---|
| **R1** | **Stage 1 is trivial, not lost work.** iSAID covers *exactly* DOTA's train+val: 1,411/1,411 and 458/458, and the image-ID sets match exactly (verified by set comparison). There is no non-trivial "intersection" to recompute — only the exclusion of DOTA's 937 test images, which iSAID does not annotate. | The missing combine script is ~30 lines, not a reconstruction project. OPEN 6 is far less severe than it looked. |
| **R2** | **iSAID ships true per-instance masks, and the construction did not use them.** `instance_masks/<id>_instance_id_RGB.png` encodes one colour per instance (444 distinct colours in P0000); `semantic_masks/<id>_instance_color_RGB.png` encodes one colour per *class* (4 colours in the same image). AerialFuseCV was built from the class-coloured masks, recovering instances approximately via connected components. | Root cause of: the connected-components step, same-class touching instances merging, the released masks' loss of instance identity, and part of the unmatched 2.1%. **Forces a v1.0/v2.0 decision — see below.** |
| **R3** | **`images_gsd_mapping.json` in the refined dataset is stale**: 1,867 entries for 1,857 images. It was not regenerated after refinement. `dataset/DOTA_v1/dota_gsd_mapping.json` also holds 1,867 for 1,869 images, so 2 images appear to lack GSD. | Regenerate both in the new script; verify the 2 missing-GSD images are real (DOTA `gsd:` header absent or `null`) and handle explicitly. |
| **R4** | **`isaid_instance_colors.json` is an empty file** (0 entries) in the released dataset. | Dead artifact: either populate it meaningfully (the class-colour table) or drop it from the deposit. Do not ship an empty JSON. |
| **R5** | **The statistics file is not named what the thesis says.** Thesis Stage 5 documents `Dataset_Statistics.md`; the actual file is `AerialFuseCV_Refined_DATASET_ANALYSIS.md`. P1's Data Description currently repeats the thesis name. | Fix the P1 draft to the real name, or standardise the name in the new script and keep the paper aligned. Prefer the latter: `DATASET_ANALYSIS.md`. |

Also worth recording: the thesis says the 1,869 images represent "66.6% of the
combined DOTA train and validation splits". They are **100%** of train+val;
66.6% is their share of all 2,806 DOTA images including test. A wording
erratum — add to the errata list in `ATHENA_STATE.md`.

---

## The decision this plan needs first: v1.0 faithful, or v2.0 corrected?

R2 puts a genuine fork in front of us.

**Option A — faithful v1.0 (recommended).** Reproduce the pipeline exactly as
it ran: class-coloured masks, connected components, IoU ≥ 0.1, same outputs.
The script reproduces `AerialFuseCV_Refined` and every number in the thesis,
P1 and (later) P2 stays valid. Deliverable for P0 as scheduled.

**Option B — corrected v2.0.** Rebuild from `instance_masks`, giving exact
instance separation, no connected-components approximation, per-instance
identity preserved in the released masks, and almost certainly a different —
probably higher — pair count.

**Recommendation: A now, B as a scheduled successor.** The dataset being
released is the dataset that produced the thesis results; if the deposit does
not match it, then the thesis numbers, P1's descriptor and P2's baselines all
describe something that no longer exists, and P0 slips while we re-run
experiments. Ship v1.0 faithful, then treat the instance-ID rebuild as
**AerialFuseCV v2.0** — which has a natural publication home already noted in
`papers/shared/venues/data-in-brief/NOTES.md`: Data in Brief publishes
**Update articles** for exactly this case ("a significant update to a dataset
previously published in Data in Brief"). That converts a defect into a second
countable publication and a P4 asset, rather than a schedule risk.

Either way, R2 must be disclosed in P1's Limitations — the current wording
("masks store category rather than per-instance colours") is accurate but
should say that the *source* offers per-instance masks and v1.0 does not use
them. Honest, and it pre-announces v2.0.

**⛔ Do not start implementation until this is decided.**

---

## Target script

```
tools/dataset_construction/build_aerialfusecv.py     # the single entry point
tools/dataset_construction/analyze_aerialfusecv.py   # the EDA (importable + CLI)
```

Run from repo root, as everything else in this repo:

```bash
python tools/dataset_construction/build_aerialfusecv.py \
    --dota   dataset/DOTA_v1 \
    --isaid  dataset/iSAID \
    --out    dataset/AerialFuseCV_v1 \
    --iou-threshold 0.1 \
    --mask-source semantic   # 'instance' selects the v2.0 path (Option B)
    --manifest                # write checksums + provenance
```

**One pass, no intermediate dataset.** For each split, for each image ID: read
the DOTA label and the iSAID mask, decode class masks, match boxes to
instances, and write image + filtered label + filtered mask straight to the
output — the combine and refine steps fuse into a single loop, which is the
whole point of the exercise. Images with zero pairs are skipped, as before.

Reuse rather than rewrite: the matching logic in `refine_aerialfusecv.py` is
correct and validated by the thesis results. Port it into
`argusvision.data`-adjacent helpers where it can be unit-tested (the
restructure already established `tests/` and the constants module — the
colour table lives in `argusvision.data.constants` and must not be duplicated
here, per finding F4).

**Outputs:**
- `{train,val}/{images,labels,semantic_masks}/`
- `DATASET_ANALYSIS.md` — the EDA report
- `dataset_statistics.json` — machine-readable counterpart (this is what P1
  cites for the ⚠ mask-side numbers)
- `images_gsd_mapping.json` — regenerated, exactly the retained images
- `checksums.sha256` + `build_manifest.json` (git SHA, env, args, timestamp —
  same discipline as `argusvision.evaluation.reporting`)

---

## Verification strategy — three levels, all mandatory

**Level 1 — structural.** Output has 1,401 + 456 images; the retained image-ID
sets equal those of `AerialFuseCV_Refined`; the 12 excluded IDs are the same 12
(10 train, 2 val).

**Level 2 — content, file by file.** For every retained image: label files
compare equal as parsed geometry (order-insensitive, tolerance on the 1-decimal
formatting the old script used), and masks compare pixel-identical. Report any
divergence per image rather than aborting on the first.

**Level 3 — statistical.** Recomputed counts must reproduce thesis Tables 6
and 7 exactly: 127,843 source boxes → 125,102 pairs; 98,990/97,070/98.1% train
and 28,853/28,032/97.2% val; all 15 per-class rows. Plus the numbers P1
currently carries as ⚠ derivations — source mask instances (I derived 330,693
by summing Table 7), mask-side retention (37.8%), unpaired mask instances
(205,591), small-vehicle ratio (6.2×). **These become verified or corrected,
and P1 cites `dataset_statistics.json` instead of my arithmetic.**

Level 3 is the point where "recompute and verify everything" is actually
satisfied, and where a silent discrepancy in the old pipeline would surface.

---

## EDA deliverable

Supersedes both historical reports (`AerialFuseCV_dataset_analysis.md`, 75
lines; `AerialFuseCV_Refined_DATASET_ANALYSIS.md`, 119 lines). Contents:

- Funnel: 2,806 DOTA → 1,869 with masks → 127,843 boxes → 125,102 pairs → 12
  images dropped → 1,857 images, each number computed, not quoted.
- Per class × split: source boxes, **source mask instances (authoritative,
  from the masks themselves)**, pairs, both retention rates, matched-IoU
  distribution (mean/median/percentiles — never reported before).
- Both retention rates prominently, box-side and mask-side (the R2/P1 story).
- Image properties: dimension distribution, GSD distribution, the 2 images
  without GSD.
- Instance geometry: area distribution per class in pixels and in m² via GSD —
  quantifies the "helicopter is 10–20 px" claim the thesis makes qualitatively.
- Unpaired analysis: why boxes fail (no class mask present / no component above
  threshold), and what the 205k unpaired mask instances are by class and size.
- Class-colour table reproduced from `argusvision.data.constants`.
- Figures for P1: the four placeholders in `DRAFT_P1.md` (example pair, class
  distribution, pipeline diagram, source discrepancies).

Every figure and table written to `dataset_statistics.json` first, then
rendered — so the paper cites data, not prose.

---

## Phases

- [ ] **Phase 0 — Decide v1.0 vs v2.0 (user).** Blocks everything. Recommendation above.
- [ ] **Phase 1 — Build script (~1 day).** Single-pass builder with `--mask-source`, manifest, checksums. Matching logic ported and unit-tested (synthetic masks: touching instances, empty class mask, sub-threshold overlap, multi-candidate).
- [ ] **Phase 2 — Verification harness (~0.5 day).** Levels 1–3 as a script (`verify_against_reference.py`) producing a pass/fail report; run against `AerialFuseCV_Refined`. **Gate: Level 2 must be clean, or the divergence explained in writing, before proceeding.**
- [ ] **Phase 3 — EDA (~1 day).** `analyze_aerialfusecv.py` → `dataset_statistics.json` + `DATASET_ANALYSIS.md` + the four P1 figures.
- [ ] **Phase 4 — Reconcile the papers (~0.5 day).** Replace every ⚠ in `DRAFT_P1.md` with verified values citing `dataset_statistics.json`; fix R5 filename; extend Limitations with R2's source-masks disclosure; add the 66.6% wording erratum to `ATHENA_STATE.md`.
- [ ] **Phase 5 — P0 packaging (~0.5 day).** LICENSE (CC-BY 4.0 on our contribution), deposit README, the rebuild instructions the descriptor promises, Zenodo upload → DOI.
- [ ] **Close-out.** Close OPEN 6; ledger + work log; delete `refine_aerialfusecv.py` only after Level 2 passes.

**Total ~3.5 days**, versus the ~1 week P0 was budgeted at — and it now
produces a verified dataset plus the EDA P1 needs, not just a package.

---

## Open questions

1. **v1.0 vs v2.0** — Phase 0, above.
2. **Ship the images?** DOTA/iSAID terms forbid redistribution, hence the
   script-plus-annotations deposit. Confirm the interpretation once more before
   upload; it is the deposit's central design constraint.
3. **Keep `AerialFuseCV_Refined` on disk after verification?** 14 GB. Keep
   until P1 is accepted — it is the only copy of the artefact the thesis
   describes.
4. **`convert_dota_to_yolo_obb.py`'s YOLO-OBB dataset** is a separate product
   used by the detector benchmark, not by AerialFuseCV. Out of scope here;
   note it in the deposit README so users are not confused by two conversions.

---

*Written 2026-07-30 by ATHENA (STRATEGIST/OPERATOR). Companion entries:
`ATHENA_STATE.md` OPEN 6, `Athena_Protocols/WORK_LOG.md` 2026-07-30.*
