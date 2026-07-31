# TODO — AerialFuseCV Single-Step Recreation Script + Verified EDA

**Status: PLANNED, not started.** Investigation done 2026-07-30 (ATHENA, OPERATOR).
**Blocks: P0 Zenodo release (Aug 2026), and therefore P1 submission.**
Closes `ATHENA_STATE.md` OPEN 6.

**Goal.** One script that builds AerialFuseCV from the official DOTA v1.0 and
iSAID downloads in a single pass, plus one EDA report whose every number is
recomputed and verified. Replaces the historical two-step process (combine →
refine), of which the combine step was never version-controlled.

> **Policy (user directive, 2026-07-30): the MSc thesis is not a source.**
> It was a prerequisite and is closed. Nothing cites it. Every number this
> program publishes is measured by this program, lands in `results/` with a run
> manifest, and is re-run for consistency. Where this plan previously said
> "reproduce thesis Table 6/7", read instead: **the precursor build's outputs on
> disk are a regression baseline, not an authority.** If our measurement and the
> precursor disagree, our measurement is right and the delta gets explained.

---

## What we have to work with

| Asset | State | Role |
|---|---|---|
| `dataset/DOTA_v1/{train,val}/{images,labels}` | 1,411 / 458 | source |
| `dataset/iSAID/{train,val}/{semantic_masks,instance_masks}` | 1,411 / 458 each | source |
| `dataset/AerialFuseCV/` | 1,411 + 458 = **1,869** | regression baseline, combine step |
| `dataset/AerialFuseCV_Refined/` | 1,401 + 456 = **1,857** | regression baseline, full pipeline (**not an authority**) |
| `dataset/refine_aerialfusecv.py` | works | reference implementation of matching |
| `dataset/convert_dota_to_yolo_obb.py` | works | separate YOLO-OBB conversion (not on this path) |

**The decisive advantage: both precursor outputs are still on disk.** The new
script's *port fidelity* can therefore be proven file by file rather than
assumed — any divergence is a bug in the new script or an undocumented step in
the precursor, and either way we want to know. This is a regression check, not
a claim that the precursor was right: the corrected build is expected to
differ, and its differences are the point. Verify before deleting anything.

---

## Findings from the investigation

| # | Finding | Consequence |
|---|---|---|
| **R1** | **Stage 1 is trivial, not lost work.** iSAID covers *exactly* DOTA's train+val: 1,411/1,411 and 458/458, and the image-ID sets match exactly (verified by set comparison). There is no non-trivial "intersection" to recompute — only the exclusion of DOTA's 937 test images, which iSAID does not annotate. | The missing combine script is ~30 lines, not a reconstruction project. OPEN 6 is far less severe than it looked. |
| **R2** | **iSAID ships true per-instance masks, and the construction did not use them.** `instance_masks/<id>_instance_id_RGB.png` encodes one colour per instance (444 distinct colours in P0000); `semantic_masks/<id>_instance_color_RGB.png` encodes one colour per *class* (4 colours in the same image). AerialFuseCV was built from the class-coloured masks, recovering instances approximately via connected components. | Root cause of: the connected-components step, same-class touching instances merging, the released masks' loss of instance identity, and part of the unmatched 2.1%. **Forces a v1.0/v2.0 decision — see below.** |
| **R3** | **`images_gsd_mapping.json` in the refined dataset is stale**: 1,867 entries for 1,857 images. It was not regenerated after refinement. `dataset/DOTA_v1/dota_gsd_mapping.json` also holds 1,867 for 1,869 images, so 2 images appear to lack GSD. | Regenerate both in the new script; verify the 2 missing-GSD images are real (DOTA `gsd:` header absent or `null`) and handle explicitly. |
| **R4** | **`isaid_instance_colors.json` is an empty file** (0 entries) in the released dataset. | Dead artifact: either populate it meaningfully (the class-colour table) or drop it from the deposit. Do not ship an empty JSON. |
| **R5** | **The statistics file is not named what the thesis says.** Thesis Stage 5 documents `Dataset_Statistics.md`; the actual file is `AerialFuseCV_Refined_DATASET_ANALYSIS.md`. P1's Data Description currently repeats the thesis name. | Fix the P1 draft to the real name, or standardise the name in the new script and keep the paper aligned. Prefer the latter: `DATASET_ANALYSIS.md`. |

Measured directly: the 1,869 images are **100%** of DOTA's train+val, and 66.6%
of all 2,806 DOTA images once the 937 test images are counted. Stating it the
second way without saying "including test" is the kind of ambiguity to avoid in
P1.

---

## ✅ DECIDED 2026-07-30 (user): build the CORRECTED dataset

**Option B. Fix it.** Plus two requirements and one verification mandate:

1. **Matching uses the per-instance masks** (`instance_masks/*_instance_id_RGB.png`)
   for exact instance separation — no connected-components approximation.
   Class comes from the semantic mask at the same pixels; instance identity
   from the instance mask. The audit precondition for this
   (every instance region maps to exactly one class) is being verified
   exhaustively — see § Colour audit.
2. **The released dataset ships BOTH mask directories per split:**
   `semantic_masks/` (class-coloured, as before, for backward compatibility and
   semantic-segmentation users) and `instance_masks/` (per-instance identity).
   This removes the v1.0 limitation that adjacent same-class instances are
   inseparable — the paired box is no longer the only way to isolate an
   instance.
3. **No colour table is trusted, including the thesis's.** Table 5 must be
   verified against an exhaustive scan of every mask; "P0000 contains four
   colours" proves nothing about the other 1,868 images.

**Consequence, recorded not relitigated.** Pair counts will change, so the
released dataset is no longer numerically identical to the one the thesis
experiments ran on. This is acceptable and manageable because:
- P2 re-runs every experiment under the new evaluation stack anyway (already
  decided at the restructure), so P2's numbers will describe the released
  dataset natively.
- The thesis stands as Phase 0 with its own numbers, computed on the
  pre-release construction — stated plainly in P1 and in `ATHENA_STATE.md`.
- **P1 must be re-based on the corrected numbers.** Every count in
  `DRAFT_P1.md` (125,102 pairs, 97.9%, all of Table 2, the four ⚠ values) is
  provisional until the new build reports its own. Phase 4 becomes a rewrite
  of the numeric content, not a patch. The narrative and structure survive.
- Thesis-vs-release divergence becomes a documented Data Description
  subsection, not an inconsistency a reviewer discovers.

The superseded analysis is kept below for the record.

## Superseded (kept only as decision record — do not act on)

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

~~⛔ Do not start implementation until this is decided.~~ **Decided — see above.**

---

## Colour audit (prerequisite, running)

`dataset/scan_isaid_colours.py` — exhaustive, no sampling.
Over all 1,869 image pairs it establishes:

1. **Every RGB value that actually occurs** in the semantic masks, with pixel
   and image counts → verifies thesis Table 5 / `argusvision.data.constants`
   and surfaces any colour present in the data but absent from the table
   (`unknown_semantic_colours`) or in the table but never observed
   (`table_colours_never_observed`).
2. **The authoritative instance count** per image from the instance-id masks —
   independent of connected components, and the number that replaces my ⚠
   derivation of 330,693. **Result: 475,438 — see below.**
3. **Whether any instance region spans more than one semantic class**
   (`instances_spanning_multiple_classes`). This is the correctness
   precondition for deriving (class, instance) by intersecting the two mask
   types. **A non-zero count here changes the build design**, so it gates
   Phase 1.

Implementation note: both masks are packed to `0xRRGGBB` int32 and the
(instance, semantic) co-occurrence set is obtained in a single `np.unique`
over a combined int64 key — one pass per image rather than per-instance
masking, which would be ~444 × 21 M operations on a large image.

Smoke run (6 images): 8 distinct semantic colours, 0 unknown, 1,159 instances,
**0 instances spanning multiple classes**. Output:
`results/isaid_colour_audit/colour_audit.json`.

---

## Target script

```
dataset/build_aerialfusecv.py     # the single entry point
dataset/analyze_aerialfusecv.py   # the EDA (importable + CLI)
```

Run from repo root, as everything else in this repo:

```bash
python dataset/build_aerialfusecv.py \
    --dota   dataset/DOTA_v1 \
    --isaid  dataset/iSAID \
    --out    dataset/AerialFuseCV_v1 \
    --iou-threshold 0.1 \
    --mask-source instance   # DECIDED default; 'semantic' reproduces the
                             # historical build for the verification harness
    --manifest               # checksums + provenance
```

**Instance-mask matching (the corrected path).** Per image: pack both masks;
obtain the (instance, semantic) co-occurrence set in one pass; that yields, for
every instance, its pixel set and its class — exactly, with no connected-
components approximation and no merging of touching same-class objects. Then
match DOTA boxes to instances of the same class by IoU against the box hull,
threshold 0.1 as before. Because instances are now exact, **a one-to-one
assignment becomes meaningful and should be enforced** (Hungarian, reusing
`argusvision.evaluation.matching` — the same single matcher the restructure
froze), removing the v1.0 caveat that two boxes could claim one component.

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
- `{train,val}/{images,labels,semantic_masks,instance_masks}/` — **both mask
  types**, filtered to paired instances only, per the decision above
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

**Levels 1–2 apply to `--mask-source semantic`,** which must reproduce the
historical dataset. That is what proves the port is faithful and isolates the
effect of the instance-mask change: any difference in the corrected build is
then attributable to the fix, not to a porting bug. Run both modes.

**Level 3 — statistical, two parts.**

*Historical mode* must reproduce the precursor build's own outputs, recomputed
from `dataset/AerialFuseCV_Refined/` on disk — not quoted from any document.
Its purpose is purely diagnostic: it proves the port is faithful, so that every
difference in the corrected build is attributable to the fix rather than to a
porting bug. Failure here means the precursor had an undocumented step, which
is worth knowing before anything is deleted.

*Corrected mode* produces the numbers that will be published. Report the delta
against historical mode explicitly, per class: pairs gained by no longer
merging touching instances, pairs lost to one-to-one enforcement, and the new
box-side and mask-side retention rates. **The authoritative source-instance
count is **475,438** (358,166 train / 117,272 val), measured exhaustively by
the colour audit — superseding the 330,693 that connected-components counting
implied, a 30.4% undercount.**

Level 3 is where "recompute and verify everything" is actually satisfied — and
where the corrected build has to justify itself with a measured improvement
rather than an assumed one.

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

- [x] **Phase 0 — Decide (user): CORRECTED build, both mask dirs, exhaustive colour verification.** Done 2026-07-30.
- [~] **Phase 0b — Colour audit (running).** Exhaustive scan of all 1,869 pairs. **Gate: `instances_spanning_multiple_classes` must be 0**, and the colour table must be confirmed, before Phase 1 design is final.
- [ ] **Phase 1 — Build script (~1–1.5 day).** Single-pass builder, `--mask-source {instance,semantic}`, both mask dirs written, Hungarian one-to-one for the corrected path, manifest + checksums. Unit tests on synthetic masks: touching same-class instances (the case v1.0 got wrong), empty class mask, sub-threshold overlap, multi-candidate, instance spanning a class boundary.
- [ ] **Phase 2 — Verification harness (~0.5 day).** Levels 1–3 as `verify_against_reference.py`; historical mode against `AerialFuseCV_Refined`. **Gate: Level 2 clean in historical mode, or the divergence explained in writing, before the corrected build is trusted.**
- [ ] **Phase 3 — EDA (~1 day).** `analyze_aerialfusecv.py` → `dataset_statistics.json` + `DATASET_ANALYSIS.md` + the four P1 figures, plus the historical-vs-corrected delta table.
- [ ] **Phase 4 — Re-base P1 on the corrected numbers (~1 day, was 0.5).** Every count in `DRAFT_P1.md` is provisional: Tables 1–2, the abstract, Value of the Data, Data Description and Limitations all take new values from `dataset_statistics.json`. Add the thesis-vs-release divergence subsection. Remove the instance-inseparability limitation (fixed) and the one-to-one caveat (fixed). Fix R5 filename. Add the 66.6% wording erratum to `ATHENA_STATE.md`.
- [ ] **Phase 5 — P0 packaging (~0.5 day).** LICENSE (CC-BY 4.0 on our contribution), deposit README, the rebuild instructions the descriptor promises, Zenodo upload → DOI.
- [ ] **Close-out.** Close OPEN 6; ledger + work log; delete `refine_aerialfusecv.py` only after Level 2 passes.

**Total ~4.5–5 days**, versus the ~1 week P0 was budgeted at — still inside
budget, and it now produces a *corrected and verified* dataset with both mask
types plus the EDA P1 needs, rather than a package around an approximation.

---

## Open questions

1. ~~v1.0 vs v2.0~~ — **CLOSED: corrected build** (Phase 0, 2026-07-30).
1b. **Version label and DOI strategy.** The release is no longer the thesis
   artefact, so: call it AerialFuseCV **v1.0** (first public release, corrected)
   and describe the thesis construction as an unreleased precursor? Or v2.0,
   acknowledging the thesis version as v1.0 even though it was never
   deposited? Recommend **v1.0 = first public release**, with a Data
   Description note that the thesis experiments used a precursor build — one
   DOI, no phantom version history.
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

---

## Rebuild design — settled 2026-07-31

All verified against sources, not assumed. Four changes converge on one rebuild;
the earlier instance-mode run was stopped ~30% in because it reflected none of
them.

### 1. Match on the oriented polygon, not its axis-aligned hull
The precursor scored candidates against the box's hull rendered as a filled
rectangle, because connected components gave it nothing better. Measured over
21,265 boxes, **that hull is a median 1.83× the true oriented box area** (68%
exceed 1.5×, 37% exceed 2×, worst 12.9×). DOTA is genuinely oriented — 95.5% of
boxes are rotated, median 17.1° off-axis. Matching on the hull therefore
depresses IoU, makes the 0.1 threshold mean "10% of a box twice the object's
size", and loses discrimination exactly where scenes are dense (ships at a quay,
vehicle rows). We now hold the true polygon and an exact instance mask, so
rasterise the quadrilateral (`cv2.fillPoly`) and score against the instance
directly.

### 2. Ship both box geometries
`labels_obb/` (oriented quadrilateral, as DOTA annotates) and `labels_hbb/`
(axis-aligned hull, explicitly derived). The pairing is format-independent — the
same object, two geometries — so this is not a scope expansion. Verified at
source (captain-whu.github.io/DOTA/dataset.html): **DOTA distributes OBB
exclusively**, no official HBB, so ours is a derivation with nothing to
contradict. Needed by our own P2 baselines: Mask R-CNN and YOLOv11-seg are
horizontal-box models. Also enables comparing OBB and HBB detectors against
*identical* mask ground truth, which nothing else offers.

### 3. Keep DOTA-native annotation format; convert per consumer
Verified: the YOLO conversion is **lossy** — it drops the `difficult` flag,
`gsd:` and `imagesource:`, and normalises coordinates. DOTA's own evaluation
protocol treats difficult instances specially, so a converted copy cannot follow
it. No single framework format serves everyone: P2 alone needs YOLO (YOLOv11-seg)
and COCO JSON (Mask R-CNN). Store the source format; conversion belongs in the
loader.

### 4. Deposit the correspondence, not the coordinates — LICENSING
DOTA's terms: *"All images and their associated annotations in DOTA can be used
for academic purposes only, but any commercial use is prohibited."* **Annotations,
not only images.** Redistributing DOTA coordinates under CC-BY 4.0 would
relicense restricted third-party data permissively. The deposit therefore ships
the **pairing relation** (image id, split, class, iSAID instance identity,
matching IoU) plus the script; the user brings their own DOTA and iSAID
downloads and the dataset materialises locally. We license only what we created.
**TODO: check iSAID's terms the same way** — expected at least as restrictive,
since it inherits DOTA's imagery.

### Naming
`HBB`, not VBB. DOTA's own benchmark tasks are *OBB detection* and *HBB
detection*; VBB is not established in this literature and "vertical" misleads.
AABB is computational-geometry vocabulary, not remote sensing.

### 5. NOTE — code rename deferred (user decision, 2026-07-31)
`argusvision` still uses VBB internally: `mode="vbb"` in the YOLO adapter, the
registry naming, and `model_checkpoints/YOLO/VBB/`. **Rename to HBB later** so
one vocabulary spans dataset, code and papers. Mechanical but touches a
checkpoint path, so do it deliberately, with the tests, not in passing.


---

## P1 content notes — captured 2026-07-31 (source: our own builds)

### Value of the Data: official benchmarking stays available
Training on AerialFuseCV does not cut a user off from the official DOTA
evaluation server. Because annotations are kept in DOTA's native form —
absolute pixel coordinates, DOTA class names, oriented quadrilaterals, the
`difficult` flag — predictions from a model trained here are directly
submission-shaped: no de-normalisation, no coordinate reconstruction, no class
re-indexing. The imagery is DOTA's own, unmodified and identically identified,
so there is no train/test domain shift either. Had the dataset shipped
framework-normalised labels this would not hold.

The test split itself is deliberately absent: DOTA publishes no test labels and
iSAID no test masks (verified in our tree — `DOTA_v1/test/` has images only,
`iSAID/test/` likewise), so no correspondence exists there for us to contribute.
Users wanting it download it from DOTA.

### Limitations: the training-side subset effect
AerialFuseCV's labels are DOTA's minus the unpaired boxes — **1.66%** of them
after the corrected build (box pairing 98.34%), roughly one object per image.
Those objects remain visible in the imagery but carry no label, so a detector
trained here is mildly taught to suppress them. This is the training-side mirror
of the evaluation artefact in
`documentation/DECISION_unpaired_annotations.md` §5. Quantifiable per class from
`discarded.jsonl`; state it, do not estimate it. A user seeking maximum
detection performance for a server submission should train on full DOTA.

### Corrected build result (for Data Description)
Run `results/aerialfusecv_build/20260731_082446_667bf23/`:
1,862 images kept of 1,869 (7 excluded), 127,843 source boxes -> **125,722
pairs** (98.34%), 475,438 source instances (26.44% paired), matched-IoU median
**0.715**. Versus the hull/connected-components construction: +620 pairs, +5
images, +0.48 pp box pairing, +0.247 median IoU. Largest class gains are harbor
(+548, 90.6% -> 97.4%) and plane (+265, 96.0% -> 98.5%) — both strongly
oriented, so the axis-aligned hull hurt them most. Small negative deltas in
ship, small-vehicle and large-vehicle are the one-to-one constraint removing
duplicate claims on a single mask, i.e. a correctness gain.
