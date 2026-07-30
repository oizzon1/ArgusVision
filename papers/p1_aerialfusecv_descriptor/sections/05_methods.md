# P1 Experimental Design, Materials and Methods — DRAFT v0.2 (2026-07-30)

> **Sources.** Structure and rationale follow thesis §3.1 (pp. 55–60), the
> published methodology (five stages, thesis Figure 15). Implementation detail
> is verified against `dataset/refine_aerialfusecv.py` at commit `cc9f305`.
> Where thesis prose and code differ in precision, the code is described,
> since it is what produced the released data — noted inline.
>
> ⛔ Stages 1 and 3 have no committed script — see PENDING.

## Source material

AerialFuseCV derives from two public benchmarks annotating the same aerial
imagery. DOTA v1.0 provides oriented bounding boxes over 15 categories; iSAID
provides pixel-level instance masks encoded as RGB colours. Although the
imagery corresponds one-to-one, the two were annotated by different teams at
different times under separate protocols — DOTA emphasising object-level
detection, iSAID emphasising precise instance boundaries for GIS use — and no
correspondence between an individual box and the mask of the same physical
object is published by either source. The datasets also differ in file
structure and naming convention, so pairing requires filename matching and
verification rather than a direct join.

## Stage 1 — Image identification and matching (⛔ no committed script)

The intersection of the two image sets was identified by filename pattern
matching with dimension verification. Of the 2,806 images in the DOTA v1.0
train and validation splits, **1,869** (1,411 training, 458 validation) have
corresponding iSAID masks — 66.6% of those splits. The 937 test-split images
were excluded because iSAID publishes no masks for that subset. The original
DOTA split assignment was preserved throughout.

## Stage 2 — Annotation format conversion

Detection annotations were converted from DOTA text format
(`x₁ y₁ … x₄ y₄ class-name difficulty`) to YOLO OBB format with coordinates
normalised to [0, 1], preserving rotation — essential for aerial objects —
while making the labels consumable by OBB-capable detectors. **127,843**
bounding-box instances (98,990 training, 28,853 validation) across 15
categories were converted and verified for spatial correspondence with their
source images. Implementation: `dataset/convert_dota_to_yolo_obb.py`.

## Stage 3 — Segmentation mask integration (⛔ no committed script)

iSAID masks were retained in their original PNG form and reorganised into the
per-split directory layout. Each mask was verified to share the exact
dimensions of its image, guaranteeing pixel-level alignment. The iSAID RGB
class-colour encoding was preserved unmodified, keeping compatibility with
iSAID evaluation protocols.

## Stage 4 — Instance-level refinement

The refinement algorithm takes the **DOTA boxes as the baseline** — not the
iSAID masks — and attempts to attach a mask instance to each box.

For each image, the mask is read and a binary mask per category is obtained by
exact colour equality against the class-colour table
(`extract_class_mask`, L124–132). Two entries of that table had been
transcribed incorrectly in earlier work and were corrected before
construction: storage-tank (0, 63, 63) and bridge (0, 127, 63) (L42–58). An
incorrect colour produces an empty class mask, so such an error suppresses
every pair of the affected category rather than degrading them — which is why
it is recorded here.

Labels are parsed in DOTA format, skipping the `imagesource:` and `gsd:`
header lines and retaining only the 15 known category names; for each object
both the four oriented corners and their axis-aligned hull are kept
(`load_bboxes`, L66–109). Each box is then processed independently
(`match_bbox_to_mask_instance`, L155–220):

1. The category mask is cropped to the box's **axis-aligned hull expanded by
   20% of the box's longer side**, so instances extending slightly beyond the
   annotated box remain whole (L180–188). *(Thesis prose describes this as the
   region defined by the OBB coordinates; the implementation uses that
   polygon's axis-aligned hull with padding.)*
2. Connected components within the crop become candidate instances
   (`cv2.connectedComponents`, L195).
3. Each candidate is scored by intersection-over-union against the box's hull
   rendered as a filled rectangle (`bbox_mask_iou`, L134–153).
4. The best-scoring candidate is accepted if its IoU reaches **0.1**;
   otherwise the box remains unpaired (L217–220).

**Threshold rationale (thesis §3.1).** 0.1 is a conservative criterion
requiring only minimal spatial overlap: it establishes that box and mask refer
to the same object while tolerating the inconsistencies inherent in
independent annotation. A higher threshold such as 0.3 would reject valid
pairs where a DOTA box extends beyond its iSAID mask or vice versa; a lower
one such as 0.05 would risk accepting false matches. The value was settled by
trial and error as the balance between avoiding false matches and retaining
valid pairs with imperfect alignment.

Matching treats each box independently and does not enforce a one-to-one
assignment between boxes and mask components
(`match_bboxes_to_mask_instances`, L222–242). Reported in Limitations.

## Stage 5 — Output construction, organisation and documentation

For every image retaining at least one pair (L351), three artefacts are
written: the image, unchanged; a label file containing only paired boxes, in
standard DOTA corner order (`save_refined_labels`, L244–256); and a mask
containing only paired instances, each painted in its **category** colour
(`save_refined_mask`, L258–277). Images yielding no pair are excluded
entirely — 12 images, 10 training and 2 validation.

Because output masks carry category rather than per-instance colours,
adjacent instances of one category merge in the mask file; the paired box is
the means of isolating a single instance. Consumers should intersect mask with
box rather than re-run connected components.

The result is organised as three parallel directories per split
(`images/`, `labels/`, `semantic_masks/`) so that detectors can read images and
labels by standard YOLO conventions while segmentation models read the mask
directory, and an integrated pipeline reads all three.

Per category and split, the script counts source boxes, source mask instances,
paired boxes, and both classes of discard (L312–348); these counts are
reported in Data Description.

---

## PENDING before submission

- **Stages 1 and 3 have no script in version control.**
  `refine_aerialfusecv.py` consumes `dataset/AerialFuseCV/` as pre-existing
  input; no committed code performs the image-intersection or
  mask-integration steps, and the repository contains no notebooks. Only
  Stage 2 (`convert_dota_to_yolo_obb.py`) and Stage 4 survive as code. P0 must
  author and verify Stages 1 and 3 — thesis §3.1 specifies them precisely
  enough to reimplement (filename matching + dimension verification;
  reorganisation with dimension checks) — or the deposit's reproducibility
  claim fails. Recorded as a P0 blocker in `ATHENA_STATE.md`.
- Script paths above must be updated once P0 moves construction code to
  `tools/dataset_construction/`.
- Figure F3: reuse or redraw thesis Figure 15 (creation methodology).
- End-to-end reproducibility run (roadmap: 3–5 days) precedes submission.
