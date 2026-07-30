# P1 — Assembled Draft

**Status: DRAFT v0.1, 2026-07-30. Not submission-ready.**
Target venue: **Data in Brief** (Elsevier), data-article type. Section order
below follows the mandatory template v19 (Dec 2024); at submission the content
must be transferred into the official `.docx`, which is partially locked.

**Conventions in this file**
- `[[PLACEHOLDER: … ]]` — content not yet available; reason given.
- ⚠ — value derived by ATHENA from thesis Table 7 rather than stated in the
  thesis. Must be regenerated from the deposit's `Dataset_Statistics.md` at P0
  and cited from there. **No ⚠ value may survive into submission.**
- Every other number traces to thesis §3.1 (pp. 55–60) or its Tables 6–7.

---

## Article title

AerialFuseCV: an instance-level paired oriented-box and instance-mask **dataset**
for aerial imagery derived from DOTA v1.0 and iSAID

> Template rule satisfied: title contains "dataset".

## Authors

[[PLACEHOLDER: authorship not yet decided. Fragkos is author; whether the
supervisor (Prof. Charalampos Ioannidis) is co-author on the data article — and
in what order — is a supervisor question, not an ATHENA decision. Resolve
before submission; CRediT statement below depends on it.]]

## Affiliations

[[PLACEHOLDER: full postal address required by template — School of Rural,
Surveying and Geoinformatics Engineering (or SECE, per the authorship
outcome), National Technical University of Athens, Greece. Exact department
and address to confirm.]]

## Corresponding author's email and Twitter handle

[[PLACEHOLDER: template requires an *institutional* address; the NTUA address
is not recorded in the repo. Twitter handle optional.]]

## Keywords

object detection; segmentation; remote sensing; deep learning; annotation
reconciliation; earth observation

> Template rules satisfied: 6 keywords (4–8), semicolon-separated, none
> repeats a title word.

## Abstract

AerialFuseCV pairs the oriented bounding-box annotations of DOTA v1.0 with the
pixel-level instance masks of iSAID at the level of individual object
instances. Although both benchmarks annotate the same aerial imagery, their
annotations were produced independently and share no instance correspondence.
The dataset was constructed by decoding iSAID's colour-encoded masks into
per-category binary masks, isolating candidate instances as connected
components within the neighbourhood of each DOTA box, and pairing every box
with its highest-overlap candidate under a permissive intersection-over-union
rule (IoU ≥ 0.1); images retaining no pair were excluded (12 in total). The
result contains 1,857 images (1,401 training, 456 validation) with 125,102
validated box–mask pairs across the 15 DOTA v1.0 object categories, meaning
that 97.9% of DOTA boxes acquired a mask (98.1% training, 97.2% validation).
Pairing is anchored on the boxes, so a smaller fraction of the more numerous
iSAID mask instances is retained; both rates and per-category figures are
reported. The deposit provides all pairing annotations and metadata,
per-category statistics, and a construction pipeline with verification
checksums that rebuilds the dataset from the official DOTA v1.0 and iSAID
distributions, whose imagery cannot be redistributed directly. AerialFuseCV
supports training and evaluation of aerial instance-segmentation methods that
require linked box and mask supervision, including detection-to-segmentation
pipelines built on promptable segmentation models, without any re-annotation
effort.

> 236 words (template window 100–500).

---

## Specifications Table

| Field | Entry |
|---|---|
| Subject | [[PLACEHOLDER: select from template dropdown — "Computer Vision and Pattern Recognition" expected; confirm available options in the .docx]] |
| Specific subject area | Instance-level paired object detection and segmentation annotations for aerial and satellite imagery *(93 chars excl. spaces; limit 150)* |
| Type of data | Annotation files (text, DOTA format); pairing metadata (JSON); per-category statistics (JSON/CSV); construction scripts (Python); verification checksums (text). Processed and analysed, derived from public source datasets. |
| Data collection | Derived by reconciling two existing annotation sets over the same aerial imagery: oriented bounding boxes from DOTA v1.0 and colour-encoded instance masks from iSAID. Per-category masks were decoded by exact colour match; candidate instances were isolated as connected components within each box's neighbourhood and paired with the box under an IoU ≥ 0.1 criterion. Twelve images retaining no pair were excluded. No new imagery was collected and no imagery was modified. |
| Data source location | Source datasets: DOTA v1.0 and iSAID, official public distributions. Deposit: Zenodo. Institution: National Technical University of Athens, Athens, Greece. |
| Data accessibility | Repository name: Zenodo · Data identification number: [[PLACEHOLDER: DOI — blocked by P0 release]] · Direct URL: [[PLACEHOLDER: blocked by P0]] · Instructions: annotations and metadata download directly; imagery-linked portions are rebuilt from the official DOTA v1.0 and iSAID downloads with the included construction script and verified by checksums, since the source imagery is not redistributable. |
| Related research article | None. This data article is not related to a research article. |

---

## Value of the Data

- AerialFuseCV is, to the authors' knowledge, the first publicly available
  dataset linking oriented bounding boxes and pixel-level instance masks for
  the same object instances in aerial imagery: 125,102 validated box–mask
  pairs over 1,857 images and the 15 DOTA v1.0 categories.
- Researchers in aerial and satellite computer vision can train and evaluate
  methods that require joint box and mask supervision — instance
  segmentation, detection-to-segmentation pipelines, and prompt-based
  segmentation with box prompts — without performing any re-annotation.
- Every pairing decision is transparent: the deposit reports per-category
  pairing rates on both the box and the mask side, the acceptance threshold,
  and the excluded images, so users can assess fitness category by category.
- The construction pipeline and verification checksums make the dataset
  reproducible from the official DOTA v1.0 and iSAID distributions, and the
  reconciliation methodology transfers directly to other box-annotated /
  mask-annotated dataset pairs that share source imagery.

---

## Background

DOTA v1.0 [1] is a widely used benchmark for object detection in aerial
imagery, annotating objects with oriented bounding boxes across 15 categories
over 2,806 images at 0.12–3.0 m ground sample distance. iSAID [2] is its
segmentation companion: it re-annotates the same imagery and the same splits
with pixel-level instance masks for the same categories, encoded as RGB PNGs.

Although the imagery corresponds one-to-one, the two annotation efforts were
independent — different teams, different times, separate protocols. DOTA
emphasised object-level detection suitable for surveillance; iSAID emphasised
precise instance boundaries suitable for GIS integration and area
measurement. Consequently no correspondence between an individual box and the
mask of the same physical object is published by either source, the two use
incompatible file structures and naming conventions, and their instance counts
differ substantially — 188,282 boxes against 655,451 mask instances — because
iSAID annotators included very small and partially occluded objects that DOTA
annotators omitted.

Research on aerial instance segmentation increasingly needs both annotation
forms at once: to train mask heads on detector outputs, to evaluate
detection-to-segmentation pipelines, and to prompt segmentation foundation
models [3] with detected boxes while scoring against ground-truth masks.
Producing such paired supervision by manual re-annotation is prohibitively
expensive at benchmark scale. AerialFuseCV was compiled to close this gap by
reconciling the two existing annotation sets at instance level under a
documented matching rule, so that the correspondence itself — not only the
source annotations — becomes a validated, reusable artefact.

---

## Data Description

### Organisation

Three parallel directories per split, so a detector can consume images and
labels by standard YOLO conventions, a segmentation model can read the mask
directory, and an integrated pipeline can use all three at once:

```
AerialFuseCV/
├── train/
│   ├── images/           1,401 PNG
│   ├── labels/           1,401 TXT   (paired boxes only)
│   └── semantic_masks/   1,401 PNG   (RGB, paired instances only)
├── val/
│   ├── images/             456 PNG
│   ├── labels/             456 TXT
│   └── semantic_masks/      456 PNG
└── Dataset_Statistics.md
```

Each label line carries one paired object in DOTA convention —
`x₁ y₁ x₂ y₂ x₃ y₃ x₄ y₄ class-name difficulty` — preserving the oriented
geometry of the source annotation. Masks are named
`<image-id>_instance_color_RGB.png` and share the exact pixel dimensions of
their image. Mask pixels are coloured by **category**, not by instance
identity, using the iSAID class-colour table; black denotes the absence of any
annotated object.

### Image properties

Imagery is inherited unchanged from DOTA v1.0 / iSAID: variable-size
high-resolution scenes at 0.12–3.0 m ground sample distance from Google Earth,
the JL-1 satellite and the Gaofen-2 satellite. No resizing, retiling or
radiometric adjustment was applied, so per-image GSD metadata remains
applicable and object scale varies by more than an order of magnitude across
the collection.

### Scale and pairing outcome

The collection begins from the 1,869 images (1,411 training, 458 validation)
that DOTA v1.0 and iSAID annotate in common — 66.6% of DOTA's 2,806
train-and-validation images. The 937 test images are excluded because iSAID
publishes no masks for them. Twelve images (10 training, 2 validation)
retained no pair and were dropped, leaving 1,857.

**Table 1.** Pairing outcome by split.

| Split | Source boxes | Paired | Box pairing rate | Images retained |
|---|---|---|---|---|
| Train | 98,990 | 97,070 | 98.1% | 1,401 |
| Validation | 28,853 | 28,032 | 97.2% | 456 |
| **Total** | **127,843** | **125,102** | **97.9%** | **1,857** |

### Pairing is box-anchored: two retention rates

Matching takes the DOTA boxes as its baseline, so the 97.9% figure is a
**box-side** rate: 97.9% of annotated boxes received a mask. The mask side
behaves differently, because iSAID annotates far more objects than DOTA.
Within the 1,869-image subset the source masks contain ⚠ 330,693 instances, of
which the 125,102 pairs represent ⚠ 37.8%; ⚠ 205,591 mask instances have no
corresponding box and are therefore absent from the released masks. The
imbalance is category-dependent and extreme for small objects: in the training
split iSAID marks ⚠ 6.2× more small-vehicle instances than DOTA boxes
(160,844 against 26,126).

This is a definition rather than a defect. AerialFuseCV inherits DOTA's
annotation policy, and every released mask instance is one that a box
confirms. Work needing exhaustive mask coverage of small objects should use
iSAID directly.

### Per-category statistics

All 15 categories pair between 83.6% and 100%. The lowest rates are helicopter
(83.6% validation — objects typically 10–20 px, giving ambiguous box–mask
boundaries), harbor (89.6% training — irregular dock and pier geometry
annotated differently by the two sources), soccer-ball-field (92.2%
validation), and basketball-court and large-vehicle (both 93.2% validation,
attributable to occlusion and density in urban scenes).

**Table 2.** Source boxes, paired boxes and pairing rate per category and
split, with the resulting share of the dataset. Ordered by total pairs.

| Category | Train boxes | Train paired | Train rate | Val boxes | Val paired | Val rate | Total pairs | Share |
|---|---|---|---|---|---|---|---|---|
| ship | 28,068 | 27,969 | 99.6% | 8,960 | 8,934 | 99.7% | 36,903 | 29.5% |
| small-vehicle | 26,126 | 25,798 | 98.7% | 5,438 | 5,275 | 97.0% | 31,073 | 24.8% |
| large-vehicle | 16,969 | 16,709 | 98.5% | 4,387 | 4,088 | 93.2% | 20,797 | 16.6% |
| plane | 8,055 | 7,689 | 95.5% | 2,531 | 2,478 | 97.9% | 10,167 | 8.1% |
| storage-tank | 5,029 | 4,960 | 98.6% | 2,888 | 2,822 | 97.7% | 7,782 | 6.2% |
| harbor | 5,983 | 5,360 | 89.6% | 2,090 | 1,954 | 93.5% | 7,314 | 5.8% |
| tennis-court | 2,367 | 2,355 | 99.5% | 760 | 748 | 98.4% | 3,103 | 2.5% |
| bridge | 2,047 | 2,004 | 97.9% | 464 | 446 | 96.1% | 2,450 | 2.0% |
| swimming-pool | 1,736 | 1,699 | 97.9% | 440 | 434 | 98.6% | 2,133 | 1.7% |
| helicopter | 630 | 609 | 96.7% | 73 | 61 | 83.6% | 670 | 0.5% |
| baseball-diamond | 415 | 413 | 99.5% | 214 | 214 | 100.0% | 627 | 0.5% |
| basketball-court | 515 | 494 | 95.9% | 132 | 123 | 93.2% | 617 | 0.5% |
| roundabout | 399 | 386 | 96.7% | 179 | 176 | 98.3% | 562 | 0.4% |
| soccer-ball-field | 326 | 312 | 95.7% | 153 | 141 | 92.2% | 453 | 0.4% |
| ground-track-field | 325 | 313 | 96.3% | 144 | 138 | 95.8% | 451 | 0.4% |
| **Total** | **98,990** | **97,070** | **98.1%** | **28,853** | **28,032** | **97.2%** | **125,102** | **100%** |

*Reproduced from thesis Table 7; the total-pairs and share columns are computed
from it and reconcile with the thesis's independently stated percentages and
with Table 1's totals. Source mask-instance counts per category are in the
deposit's `Dataset_Statistics.md`.*

### Category distribution

The distribution is severely imbalanced, mirroring both source datasets and
real-world aerial imagery. Three transport and maritime categories supply
71.0% of all pairs. Six categories are moderately represented, together 26.3%.
The remaining six each contribute under 0.6%, 2.7% in total. Aggregate metrics
computed over this dataset are therefore dominated by vehicle and ship
performance, and per-category reporting is advisable; every category
nonetheless retains enough absolute instances for meaningful per-class
evaluation. The distribution closely tracks that of the sources, indicating
that pairing introduced no systematic category bias.

### Deposit contents

[[PLACEHOLDER: file-by-file inventory of the Zenodo deposit — blocked by P0.
Will list annotation and pairing files, per-category statistics, the
construction script, checksums and licence. Source imagery is not
redistributable, so the deposit ships annotations plus a rebuild path rather
than images.]]

### Figures

- **Figure 1.** [[PLACEHOLDER: example image with paired oriented box and
  instance mask overlaid.]]
- **Figure 2.** [[PLACEHOLDER: category distribution, log scale — cf. thesis
  Figure 16.]]
- **Figure 3.** [[PLACEHOLDER: construction pipeline, five stages — cf. thesis
  Figure 15.]]
- **Figure 4.** [[PLACEHOLDER: representative annotation discrepancies between
  the sources, illustrating why pairing is non-trivial — cf. thesis
  Figure 14.]]

---

## Experimental Design, Materials and Methods

Construction proceeded in five stages.

**Stage 1 — Image identification and matching.** The intersection of the two
image sets was identified by filename pattern matching with dimension
verification. Of the 2,806 images in the DOTA v1.0 train and validation
splits, 1,869 (1,411 training, 458 validation) have corresponding iSAID masks,
66.6% of those splits. The 937 test-split images were excluded because iSAID
publishes no masks for that subset. The original DOTA split assignment was
preserved throughout.

**Stage 2 — Annotation format conversion.** Detection annotations were
converted from DOTA text format (`x₁ y₁ … x₄ y₄ class-name difficulty`) to
YOLO OBB format with coordinates normalised to [0, 1], preserving rotation —
essential for aerial objects — while making the labels consumable by
OBB-capable detectors. 127,843 bounding-box instances (98,990 training, 28,853
validation) across 15 categories were converted and verified for spatial
correspondence with their source images.

**Stage 3 — Segmentation mask integration.** iSAID masks were retained in
their original PNG form and reorganised into the per-split directory layout.
Each mask was verified to share the exact dimensions of its image,
guaranteeing pixel-level alignment. The iSAID RGB class-colour encoding was
preserved unmodified, keeping compatibility with iSAID evaluation protocols.

**Stage 4 — Instance-level refinement.** The refinement algorithm takes the
DOTA boxes as the baseline — not the iSAID masks — and attempts to attach a
mask instance to each box. For each image a binary mask per category is
obtained by exact colour equality against the class-colour table. Labels are
parsed in DOTA format, retaining only the 15 known category names; for each
object both the four oriented corners and their axis-aligned hull are kept.
Each box is then processed independently:

1. The category mask is cropped to the box's axis-aligned hull expanded by 20%
   of the box's longer side, so instances extending slightly beyond the
   annotated box remain whole.
2. Connected components within the crop become candidate instances.
3. Each candidate is scored by intersection-over-union against the box's hull
   rendered as a filled rectangle.
4. The best-scoring candidate is accepted if its IoU reaches 0.1; otherwise
   the box remains unpaired.

The threshold of 0.1 is a conservative criterion requiring only minimal
spatial overlap: it establishes that box and mask refer to the same object
while tolerating the inconsistencies inherent in independent annotation. A
higher threshold such as 0.3 would reject valid pairs where a DOTA box extends
beyond its iSAID mask or vice versa; a lower one such as 0.05 would risk
accepting false matches. The value was settled by trial and error as the
balance between avoiding false matches and retaining valid pairs with
imperfect alignment. Matching treats each box independently and does not
enforce a one-to-one assignment between boxes and mask components.

**Stage 5 — Output construction, organisation and documentation.** For every
image retaining at least one pair, three artefacts are written: the image,
unchanged; a label file containing only paired boxes, in standard DOTA corner
order; and a mask containing only paired instances, each painted in its
category colour. Images yielding no pair are excluded entirely — 12 images, 10
training and 2 validation. Because output masks carry category rather than
per-instance colours, adjacent instances of one category merge in the mask
file; the paired box is the means of isolating a single instance, so consumers
should intersect mask with box rather than re-run connected components. Per
category and split, source boxes, source mask instances, paired boxes and both
classes of discard are counted and reported in the deposit.

---

## Limitations

Pairing is box-anchored. 97.9% of DOTA boxes received a mask, but only about
⚠ 37.8% of iSAID mask instances received a box, so roughly ⚠ 205,600 mask
instances — overwhelmingly small vehicles — are absent from the released
masks. Work requiring exhaustive small-object mask coverage should use iSAID
directly.

Each box is paired independently with its highest-overlap mask component,
without a one-to-one constraint, so in crowded scenes two boxes of one
category may reference the same component.

Masks store category rather than per-instance colours; adjacent instances of
one category are inseparable from the mask alone, and the paired box is
required to isolate an instance.

The category distribution is severely imbalanced: three categories supply
71.0% of pairs while six contribute under 0.6% each.

Annotation quality is bounded by the sources — geometry by DOTA v1.0, masks by
iSAID — and their errors propagate into the pairs. Only training and
validation splits are covered, as iSAID publishes no test-split masks.

Source imagery cannot be redistributed, so the deposit provides annotations,
metadata and a construction script rather than images.

> 177 words (cap 200). ⚠ values to be restated from `Dataset_Statistics.md`.

---

## Ethics Statement

The authors have read and follow the ethical requirements for publication in
Data in Brief. The work involved no human subjects, no animal experiments and
no data collected from social media platforms. The dataset is derived entirely
from publicly released aerial imagery benchmarks used under their academic
terms; no imagery is redistributed.

## CRediT Author Statement

[[PLACEHOLDER: depends on the authorship decision above. Expected for a
single-author article — Panagiotis Fragkos: Conceptualization, Methodology,
Software, Validation, Formal analysis, Data curation, Writing – original
draft, Visualization. Add supervisory roles (Supervision, Writing – review &
editing) if the supervisor is a co-author.]]

## Acknowledgements

[[PLACEHOLDER: contributors not meeting authorship criteria, if any.]]

Funding: [[PLACEHOLDER: if none, the template's sentence applies verbatim —
"This research did not receive any specific grant from funding agencies in the
public, commercial, or not-for-profit sectors." Confirm no NTUA/PhD funding
must be declared.]]

## Declaration of Competing Interests

The authors declare that they have no known competing financial interests or
personal relationships that could have appeared to influence the work reported
in this paper.

---

## References

> Template rule: **maximum 20**, numbered, cited as `[n]`; the deposited
> dataset must itself be cited. Four used; all bibliographic details require
> verification against the publisher record before submission (see
> `references.bib`).

[1] G.-S. Xia, X. Bai, J. Ding, Z. Zhu, S. Belongie, J. Luo, M. Datcu,
M. Pelillo, L. Zhang, DOTA: A large-scale dataset for object detection in
aerial images, in: Proc. IEEE/CVF Conf. Computer Vision and Pattern
Recognition (CVPR), 2018, pp. 3974–3983. [[VERIFY pages/DOI]]

[2] S. Waqas Zamir, A. Arora, A. Gupta, S. Khan, G. Sun, F. Shahbaz Khan,
F. Zhu, L. Shao, G.-S. Xia, X. Bai, iSAID: A large-scale dataset for instance
segmentation in aerial images, in: Proc. IEEE/CVF Conf. Computer Vision and
Pattern Recognition Workshops (CVPRW), 2019, pp. 28–37. [[VERIFY pages/DOI]]

[3] A. Kirillov, E. Mintun, N. Ravi, H. Mao, C. Rolland, L. Gustafson, T. Xiao,
S. Whitehead, A.C. Berg, W.-Y. Lo, P. Dollár, R. Girshick, Segment Anything,
in: Proc. IEEE/CVF Int. Conf. Computer Vision (ICCV), 2023, pp. 4015–4026.
[[VERIFY pages/DOI]]

[4] P. Fragkos, AerialFuseCV: paired oriented-box and instance-mask
annotations for aerial imagery [dataset], Zenodo, 2026.
[[PLACEHOLDER: DOI — blocked by P0]]

---

## Pre-submission checklist

- [ ] **P0 complete**: Zenodo deposit live, DOI minted → fills Specifications
      Table, deposit inventory, reference [4].
- [ ] **P0 blocker (ledger OPEN 6)**: author and verify construction Stages 1
      and 3 — they exist in no committed script, so the reproducibility claim
      is currently unsupported.
- [ ] Regenerate all ⚠ values from `Dataset_Statistics.md`; remove every ⚠.
- [ ] Authorship, affiliation, institutional email, CRediT resolved.
- [ ] Four figures produced.
- [ ] Official DiB `.docx` template filled; instructional text deleted.
- [ ] Reference details verified; ≤20 references.
- [ ] Confirm current APC.
- [ ] 🔴 REVIEWER pass (hostile read) before submission.

---

## ⛔ POLICY NOTICE — 2026-07-30: this draft must be re-sourced

**The MSc thesis is not a citable source.** It was a degree prerequisite and is
closed; every number this program publishes is measured by this program and
lives in `results/` with a run manifest.

This draft was written before that directive and currently derives its
numeric content and its Methods narrative from that document. It is therefore
**provisional in full**:

- Every count — 1,869 / 127,843 / 125,102 / 97.9% / all of Table 2 / the four ⚠
  values — is superseded pending the corrected build's own output
  (`dataset_statistics.json`).
- The Methods section must be rewritten to describe **the script we ship**, not
  a five-stage narrative inherited from elsewhere.
- Already superseded by our own exhaustive measurement
  (`results/isaid_colour_audit/colour_audit.json`, 1,869 images): the iSAID
  source contains **475,438 instances** (358,166 train / 117,272 val), not the
  330,693 that connected-components counting implied — a 30.4% undercount. The
  class-colour table is confirmed complete and correct (16 values, zero
  unknown, zero unobserved), and **zero instances span more than one class**.

**Deliberately not rewritten yet.** The corrected build changes these numbers
again, so re-sourcing now would mean writing the same prose twice. Rewrite once,
from `dataset_statistics.json`, at Phase 4 of `TODO_RECREATION_SCRIPT.md`.
Structure, argument and venue compliance all survive; only sourcing and figures
change.
