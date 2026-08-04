# P1 — Assembled Draft

**Status: DRAFT v1.0, 2026-08-04. Re-sourced from `results/`. Not submission-ready.**
Target venue: **Data in Brief** (Elsevier), data-article type. The section order
below follows the mandatory template v19 (Dec 2024); at submission the content
must be transferred into the official `.docx`, which is partially locked.

**Conventions in this file**

- `[[PLACEHOLDER: … ]]` — content not yet available; the reason is given.
- Every number traces to a build artefact. No value is quoted from the MSc
  thesis, which is not a source for this program.

**Provenance of the numbers.** Build counts, per-category tables, matched-IoU
statistics and the discard breakdown come from
`results/experimental/AerialFuseCV_Testing/aerialfusecv_build/20260804_095041_d4c191a/dataset_statistics.json`
(git sha `d4c191a`). Protocol-divergence figures come from
`results/experimental/AerialFuseCV_Testing/annotation_discrepancy/discrepancy_summary.json`
(all 125,722 pairs, no sampling). Threshold sensitivity, object-size and GSD
ranges come from `results/experimental/AerialFuseCV_Testing/eda/DATASET_ANALYSIS.md`. Source
instance totals and colour-table completeness come from
`results/experimental/AerialFuseCV_Testing/isaid_colour_audit/`. Orientation statistics come
from `results/experimental/AerialFuseCV_Testing/FINDINGS.md` §2.

---

## Article title

AerialFuseCV: a **dataset** of reconciled oriented-box and instance-mask
annotation pairs for aerial imagery, with measured protocol divergence

> Template rule satisfied: the title contains "dataset".

## Authors

[[PLACEHOLDER: authorship not yet decided. Fragkos is author; whether the
supervisor (Prof. Charalampos Ioannidis) is co-author on the data article — and
in what order — is a supervisor question, not an ATHENA decision. Resolve
before submission; the CRediT statement below depends on it.]]

## Affiliations

[[PLACEHOLDER: full postal address required by the template — School of Rural,
Surveying and Geoinformatics Engineering (or SECE, per the authorship outcome),
National Technical University of Athens, Greece. Exact department and address
to confirm.]]

## Corresponding author's email and Twitter handle

[[PLACEHOLDER: the template requires an *institutional* address; the NTUA
address is not recorded in the repo. Twitter handle optional.]]

## Keywords

remote sensing; earth observation; object detection; segmentation; label
quality; ground truth

> Template rules satisfied: 6 keywords (4–8), semicolon-separated, none repeats
> a title word.

## Abstract

DOTA v1.0 annotates aerial imagery with oriented bounding boxes and iSAID
annotates the same imagery with pixel-level instance masks, but the two
annotation efforts were independent and publish no correspondence between an
individual box and the mask of the same physical object. AerialFuseCV supplies
that correspondence. Each DOTA box was matched to an iSAID instance of the same
category by an optimal one-to-one assignment maximising total
intersection-over-union between the rasterised oriented quadrilateral and the
instance, with matches accepted from an intersection-over-union of 0.1. Across
the 1,869 images the two sources annotate in common, 127,843 boxes and 475,438
mask instances yielded 125,722 pairs over 1,862 retained images: a box pairing
rate of 98.34% and an instance pairing rate of 26.44%. The two rates differ
because pairing is anchored on the boxes and iSAID annotates many objects that
DOTA does not. Every unpaired box and every unpaired instance is recorded with
the reason it was dropped, and the accounting is exact — pairs plus discards
equal each source population.

Before the released mask definition was fixed, two candidate ground truths were
compared over all 125,722 pairs: the category-coloured mask clipped by the box,
and the exact iSAID instance. They coincide for 21.7% of objects (mean
agreement 0.918). Of the disagreeing pixels, 90.0% arise because iSAID
annotates a larger extent than the box delimits and 10.0% because a
neighbouring instance's pixels fall inside the box; 16.3% of pairs contain at
least one such foreign pixel. The released mask is therefore the matched
instance clipped to its own oriented box.

The deposit provides oriented and axis-aligned box annotations in DOTA format,
instance-identity and category-coloured masks, the pairing and discard records,
per-category statistics, checksums, and a script that rebuilds the dataset from
the official DOTA v1.0 and iSAID downloads, whose imagery is not
redistributable. The data supports training and evaluation of aerial methods
that require box and mask supervision linked on the same object.

> 319 words (template window 100–500).

---

## Specifications Table

| Field | Entry |
|---|---|
| Subject | [[PLACEHOLDER: select from the template dropdown — "Computer Vision and Pattern Recognition" expected; confirm the available options in the .docx]] |
| Specific subject area | Instance-level paired object detection and segmentation annotations for aerial and satellite imagery *(100 chars incl. spaces; limit 150)* |
| Type of data | Annotation files (text, DOTA format, oriented and axis-aligned); instance-identity and category-coloured masks (PNG); pairing and discard records (JSONL); per-category statistics (JSON); verification checksums (text); construction script (Python). Processed and analysed, derived from public source datasets. |
| Data collection | Derived by reconciling two existing annotation sets over the same aerial imagery: oriented bounding boxes from DOTA v1.0 and colour-encoded instance masks from iSAID. iSAID instances were decoded by exact colour match against the published class-colour table, then assigned to DOTA boxes of the same category by an optimal one-to-one assignment maximising total intersection-over-union between the rasterised oriented quadrilateral and the instance, accepting matches from 0.1. The released mask for each pair is the matched instance clipped to its oriented box. Seven images retaining no pair were excluded. No new imagery was collected and no imagery was modified. |
| Data source location | Source datasets: DOTA v1.0 and iSAID, official public distributions. Deposit: Zenodo. Institution: National Technical University of Athens, Athens, Greece. |
| Data accessibility | Repository name: Zenodo · Data identification number: [[PLACEHOLDER: DOI — arrives with the deposit]] · Direct URL: [[PLACEHOLDER: arrives with the deposit]] · Instructions: annotations, masks, pairing metadata and statistics download directly; the source imagery is not redistributable, so it is obtained from the official DOTA v1.0 and iSAID downloads and the dataset is regenerated with the included construction script, verified against the deposited checksums. |
| Related research article | None. This data article is not related to a research article. |

---

## Value of the Data

- The dataset resolves, object by object, a correspondence that neither source
  publishes: 125,722 oriented boxes from DOTA v1.0 linked to the individual
  iSAID instances that describe the same physical objects, over 1,862 images
  and 15 categories. No public release known to the authors provides this
  linkage.
- Aerial and satellite imaging work that depends on an object's *extent* rather
  than only its location — port and infrastructure monitoring, urban land-use
  inventory, agricultural and environmental mapping, damage assessment after
  disasters — can use the data to train and evaluate methods requiring linked
  box and mask supervision, including instance segmentation, detector →
  promptable segmenter cascades and weakly supervised mask learning, without
  any re-annotation.
- Each released mask is consistent with the annotation that delimits it and
  contains no pixels of a neighbouring instance, so a method prompted with an
  object's box is scored against ground truth that its prompt could in
  principle produce.
- Exclusion is auditable rather than silent: every unpaired box and every
  unpaired instance is recorded with its reason and its best achieved overlap,
  and pairing rates are reported per category on both the box and the instance
  side, so users can judge fitness category by category.
- The disagreement between the two source protocols is measured over every pair
  and decomposed into extent and contamination components, giving a
  quantitative reference for anyone combining independently produced annotation
  sets over shared imagery.
- The construction script and checksums regenerate the dataset from the
  official distributions, and the reconciliation procedure transfers to other
  box-annotated / mask-annotated dataset pairs that share source imagery.

---

## Background

DOTA v1.0 [1] is a widely used benchmark for object detection in aerial
imagery, annotating objects with oriented bounding boxes across 15 categories.
iSAID [2] is its segmentation companion: it re-annotates the same imagery and
the same splits with pixel-level instance masks for the same categories,
encoded as colour PNGs.

Although the imagery corresponds one to one, the two annotation efforts were
independent — different teams, different times, separate protocols. Neither
source publishes a correspondence between an individual box and the mask of the
same physical object, the two use incompatible file structures and naming
conventions, and their instance counts differ substantially: over the images
they share, 127,843 boxes against 475,438 mask instances, because the iSAID
protocol includes many small and partially occluded objects that the DOTA
protocol omits.

The two protocols also disagree about how much of an object an annotation
should cover. The disagreement is systematic rather than incidental, and it is
category-dependent, so it cannot be dismissed as annotation noise or removed by
a tolerance.

Aerial instance-segmentation research increasingly needs both annotation forms
attached to the same object at once: to train mask heads on detector outputs,
to evaluate detection-to-segmentation cascades, and to prompt a promptable
segmentation model [3] with a detected box while scoring the result against a
ground-truth mask. Producing such paired supervision by manual re-annotation is
prohibitively expensive at benchmark scale. AerialFuseCV was compiled to close
that gap by reconciling the two existing annotation sets at instance level
under a documented matching rule and a documented mask definition, so that the
correspondence itself — not only the source annotations — becomes a released,
verifiable artefact.

---

## Data Description

### Organisation

```
AerialFuseCV/
├── train/                          1,406 images
│   ├── images/                     P####.png
│   ├── labels_obb/                 P####.txt    oriented quadrilaterals
│   ├── labels_hbb/                 P####.txt    axis-aligned hulls
│   ├── instance_masks/             P####_instance_id_RGB.png
│   └── semantic_masks/             P####_instance_color_RGB.png
├── val/                              456 images, same five subdirectories
├── pairs.jsonl                     one record per paired object
├── discarded.jsonl                 one record per unpaired box or instance
├── dataset_statistics.json         totals, per split, per category, discards
├── images_gsd_mapping.json         per-image ground sample distance
├── build_manifest.json             run identity, git sha, arguments, environment
├── checksums.sha256                every non-image file
└── DATASET_ANALYSIS.md             generated summary of the build
```

Annotations stay in DOTA's own format — two header lines (`imagesource`,
`gsd`), then one object per line as `x₁ y₁ x₂ y₂ x₃ y₃ x₄ y₄ class-name
difficulty` in absolute pixel coordinates. Both geometries are written: the
oriented quadrilateral in `labels_obb/`, and its axis-aligned hull, expressed in
the same four-corner form, in `labels_hbb/`. Only paired objects appear.

Two mask encodings accompany each image, both sharing its exact pixel
dimensions. `instance_masks/` assigns a distinct colour per object instance, so
individual objects are separable directly from the mask. `semantic_masks/`
paints each object in its category colour from the iSAID class-colour table,
preserving compatibility with iSAID-style evaluation. Black denotes the absence
of any annotated object in both.

`pairs.jsonl` records, per paired object: image identifier, split, category,
the oriented and axis-aligned geometries, the DOTA difficulty flag, the
achieved intersection-over-union, and the matched iSAID instance's colour
identity and pixel area. That identity is what makes the derivation reversible:
the original unclipped iSAID instance remains recoverable from a user's own
iSAID download. `discarded.jsonl` records, per dropped object: whether it was a
box or an instance, its category, image and split, the reason it was dropped,
the best overlap it achieved, and its geometry or instance identity.

### Image properties

Imagery is inherited unchanged from DOTA v1.0 / iSAID. No resizing, retiling or
radiometric adjustment was applied, so per-image ground sample distance remains
applicable and object scale varies by orders of magnitude across the
collection. Instance areas span 10 to 1,080,673 px, median 631 px. Ground
sample distance is recorded for 1,861 of the 1,862 retained images, spanning
0.000–4.496 m/px with a median of 0.260; the single image without a value
carries `gsd:null` in its DOTA header. The values are inherited verbatim from
those headers, degenerate entries included, and are not corrected here.

### Scale and pairing outcome

The collection covers the 1,869 images that DOTA v1.0 and iSAID annotate in
common. The DOTA test split is outside the collection because iSAID publishes
no masks for it. Seven images retained no pair and were dropped (P1531, P1674,
P2123, P2152, P2330, P2352, P2380), leaving 1,862.

**Table 1.** Pairing outcome by split.

| Split | Images in common | Images retained | Source boxes | Source instances | Pairs | Box pairing rate |
|---|---|---|---|---|---|---|
| Train | 1,411 | 1,406 | 98,990 | 358,166 | 97,590 | 98.59% |
| Validation | 458 | 456 | 28,853 | 117,272 | 28,132 | 97.50% |
| **Total** | **1,869** | **1,862** | **127,843** | **475,438** | **125,722** | **98.34%** |

### Pairing is box-anchored: two retention rates

Matching takes the DOTA boxes as its baseline, so 98.34% is a **box-side**
rate: that share of annotated boxes received a mask. The instance side behaves
differently, because iSAID annotates far more objects than DOTA. The 125,722
pairs represent **26.44%** of the 475,438 source instances; 349,716 instances
have no box and are therefore not part of any pair. The asymmetry is
category-dependent and largest for small objects, where iSAID records 339,902
instances against 31,564 DOTA boxes.

This is a property of the design, not a defect. AerialFuseCV inherits DOTA's
annotation policy on which objects exist, and every released mask instance is
one that a box confirms. Work needing exhaustive mask coverage of small objects
should use iSAID directly.

### Per-category statistics

**Table 2.** Source boxes, source instances, pairs and box pairing rate per
category, with each category's share of the dataset. Ordered by pairs.

| Category | Source boxes | Source instances | Pairs | Box pairing rate | Share of pairs |
|---|---|---|---|---|---|
| ship | 37,028 | 48,119 | 36,854 | 99.5% | 29.3% |
| small-vehicle | 31,564 | 339,902 | 30,932 | 98.0% | 24.6% |
| large-vehicle | 21,356 | 45,694 | 20,765 | 97.2% | 16.5% |
| plane | 10,586 | 10,846 | 10,432 | 98.5% | 8.3% |
| harbor | 8,073 | 8,313 | 7,862 | 97.4% | 6.3% |
| storage-tank | 7,917 | 9,591 | 7,757 | 98.0% | 6.2% |
| tennis-court | 3,127 | 3,288 | 3,103 | 99.2% | 2.5% |
| bridge | 2,511 | 2,569 | 2,480 | 98.8% | 2.0% |
| swimming-pool | 2,176 | 3,191 | 2,147 | 98.7% | 1.7% |
| helicopter | 703 | 743 | 684 | 97.3% | 0.5% |
| baseball-diamond | 629 | 685 | 627 | 99.7% | 0.5% |
| basketball-court | 647 | 721 | 616 | 95.2% | 0.5% |
| roundabout | 578 | 617 | 562 | 97.2% | 0.4% |
| soccer-ball-field | 479 | 640 | 451 | 94.2% | 0.4% |
| ground-track-field | 469 | 519 | 450 | 95.9% | 0.4% |
| **Total** | **127,843** | **475,438** | **125,722** | **98.34%** | **100%** |

Box pairing rates run from 94.2% (soccer-ball-field) to 99.7%
(baseball-diamond). The instance column shows the box-anchored asymmetry
concentrated in the dense categories: small-vehicle contributes 339,902 of the
475,438 source instances but 31,564 of the 127,843 boxes.

### Category distribution

The distribution is severely imbalanced, mirroring both source datasets. Three
transport and maritime categories supply 70.4% of pairs; six categories
contribute under 0.6% each, 2.7% in total. Aggregate metrics computed over the
dataset are therefore dominated by vehicle and ship performance, and
per-category reporting is advisable; every category nonetheless retains enough
absolute instances for per-category evaluation.

### Matching quality

Intersection-over-union between the oriented box polygon and its matched
instance has mean 0.671, median 0.715, 5th percentile 0.276 and 95th percentile
0.887 over the 125,722 pairs. The acceptance threshold of 0.1 is permissive by
design; raising it discards pairs at the following cost.

**Table 3.** Pairs lost if the acceptance threshold were raised.

| Threshold | Pairs lost | Share |
|---|---|---|
| ≥ 0.15 | 175 | 0.1% |
| ≥ 0.20 | 1,701 | 1.4% |
| ≥ 0.30 | 7,797 | 6.2% |
| ≥ 0.50 | 20,346 | 16.2% |

### Objects not paired

2,121 boxes and 349,716 instances were not paired. The accounting is exact and
checked on every build: pairs plus discards equal each source population, on
both sides.

**Table 4.** Discards by recorded reason.

| Reason | Count |
|---|---|
| `instance:no_box_of_class` — no box of that category in the image | 303,451 |
| `instance:no_overlapping_box` — boxes exist, none overlaps | 44,021 |
| `instance:unassigned` — overlapped, not selected by the assignment | 2,244 |
| `box:no_overlapping_instance` — instances exist, none overlaps | 1,572 |
| `box:below_iou_threshold` — best overlap under the acceptance threshold | 223 |
| `box:lost_to_one_to_one_assignment` — instance went to a better-fitting box | 215 |
| `box:no_mask_instance_of_class` — no instance of that category in the image | 111 |

### Divergence between the two source protocols

Two candidate definitions of a pair's mask were compared over all 125,722
pairs: the category-coloured mask clipped by the oriented box, and the exact
iSAID instance. Mean agreement is 0.918 and median 0.946; the two definitions
coincide (agreement above 0.99) for 21.7% of objects, and agreement falls below
0.70 for 3.5%.

**Table 5.** Decomposition of the disagreeing pixels.

| Cause | Pixels | Share |
|---|---|---|
| Extent — iSAID annotates beyond the oriented box | 15,270,258 | 90.0% |
| Foreign — a neighbouring instance's pixels fall inside the box | 1,689,081 | 10.0% |
| Unlabelled — category-coloured pixels belonging to no instance | 0 | 0.0% |

20,489 pairs (16.3%) contain at least one foreign pixel; averaged over pairs,
foreign pixels make up 1.1% of an instance.

**Table 6.** Agreement per category, incidence of foreign pixels, and the share
of each category's disagreement attributable to extent.

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

The two components separate by category. Extent accounts for essentially all
disagreement in the sports fields, roundabout, tennis-court, harbor and bridge,
where the protocols delimit a different portion of the same object —
baseball-diamond, for example, is boxed at the infield by DOTA and annotated as
the whole field by iSAID. Foreign pixels concentrate where objects are densely
packed: storage-tank 27.6%, plane 25.2%, helicopter 21.6%, ship 19.4%. plane is
the one category whose disagreement is mostly contamination rather than extent.

The released mask definition addresses each component by a different mechanism,
described under Methods.

### Deposit contents

[[PLACEHOLDER: file-by-file inventory of the Zenodo deposit, with sizes and
per-file checksums — arrives with the deposit. It will list the annotation
files, the two mask encodings, `pairs.jsonl`, `discarded.jsonl`,
`dataset_statistics.json`, `images_gsd_mapping.json`, `build_manifest.json`,
`checksums.sha256`, the construction script and the licence. Source imagery is
not redistributable, so the deposit ships everything except the images, plus
the rebuild path that regenerates them into place.]]

### Figures

- **Figure 1.** [[PLACEHOLDER: one image with a paired oriented box and its
  reconciled instance mask overlaid.]]
- **Figure 2.** [[PLACEHOLDER: category distribution, log scale — regenerate
  from `results/experimental/AerialFuseCV_Testing/eda/`.]]
- **Figure 3.** [[PLACEHOLDER: construction pipeline.]]
- **Figure 4.** [[PLACEHOLDER: representative divergence between the source
  protocols — a harbor and a baseball-diamond case, box against unclipped
  instance.]]

---

## Experimental Design, Materials and Methods

Construction is performed by a single script that reads the official DOTA v1.0
and iSAID distributions and writes the dataset described above, recording its
own git revision, arguments and library versions in `build_manifest.json`.

**Image identification.** The intersection of the two image sets is taken over
the DOTA train and validation splits, giving 1,869 images (1,411 training, 458
validation). The DOTA test split is excluded because iSAID publishes no masks
for it. The original DOTA split assignment is preserved throughout.

**Annotation parsing.** DOTA annotations are read in their native format and
kept in it. For each object the four oriented corners are retained, together
with the axis-aligned hull written to `labels_hbb/`. Coordinates stay in
absolute pixels; no normalisation or framework-specific conversion is applied,
since such conversions are lossy and no single framework format serves every
consumer.

**Instance decoding.** iSAID publishes both an instance-identity encoding and a
category-colour encoding of the same objects. Instances are decoded from the
identity encoding, and each instance's category is read from the
category-coloured mask at the same pixels. An exhaustive audit of the source
masks over all 1,869 images found the published class-colour table complete and
correct — 16 colour values, no unknown colour observed and no table entry
unobserved — and found 475,438 instances, of which none spans more than one
category. The build re-checks this condition and reports it in
`dataset_statistics.json`; the current build records zero instances of
ambiguous category.

**Matching.** Matching is scored on the oriented quadrilateral rather than its
axis-aligned hull. DOTA is genuinely oriented: in a measurement over 21,265
boxes, 95.5% are rotated, the median rotation is 17.1° off axis, and using the
hull inflates the matching region by a median factor of 1.83 relative to the
true box area, with 37% of boxes exceeding a factor of two. Scoring on the hull
therefore admits overlap that the annotated object does not cover.

For each image and each category independently, an intersection-over-union
matrix is computed between every box's rasterised oriented quadrilateral and
every instance of that category, skipping pairs whose bounding rectangles do
not intersect. An optimal one-to-one assignment maximising the total
intersection-over-union is then solved on that matrix [4,5], and matches
reaching 0.1 are accepted. The one-to-one constraint means that two boxes
cannot claim the same instance, so a box that overlapped adequately but lost
its instance to a better-fitting box is discarded with that reason recorded
rather than silently duplicating a mask.

The acceptance threshold of 0.1 is deliberately permissive. It establishes that
a box and an instance refer to the same object while tolerating the extent
differences that independent annotation produces; a stricter threshold would
reject valid pairs wherever the two protocols delimit an object differently, at
the cost quantified in Table 3.

**Mask reconciliation.** The released mask for a pair is the matched iSAID
instance clipped to that object's oriented box:

```
reconciled_mask = iSAID_instance(matched) ∩ polygon(DOTA oriented box)
```

This addresses the two measured components of protocol divergence by different
mechanisms. Extent is bounded by the clip, so a released mask cannot exceed the
annotation that delimits it. Foreign pixels cannot arise at all, because the
mask is built from a single identified instance rather than from the
category-coloured mask — a neighbouring object's pixels have no path into it.
The two derivations coincide wherever the unlabelled component is zero, which
the divergence measurement confirms exactly, so nothing is lost relative to
starting from the category mask.

The matched instance's colour identity is preserved in `pairs.jsonl`, so the
clip is reversible: the unclipped iSAID instance can always be recovered from
the user's own iSAID download.

**Output and verification.** For every image retaining at least one pair, the
script writes the image unchanged, the two label files containing only paired
objects, and the two mask encodings containing only paired instances. Images
yielding no pair are excluded entirely. Per category and split, source boxes,
source instances, pairs and every discard are counted and written to
`dataset_statistics.json`, and the identity of every paired and every discarded
object is written to `pairs.jsonl` and `discarded.jsonl`. The build asserts that
pairs plus discarded boxes equal the source boxes and that pairs plus discarded
instances equal the source instances. SHA-256 checksums are written for every
non-image file, so a rebuild from the official downloads can be verified
against the deposit.

---

## Limitations

Pairing is anchored on the boxes. 98.34% of DOTA boxes received a mask, but
only 26.44% of iSAID instances received a box, so 349,716 instances —
overwhelmingly small vehicles — are absent. Work needing exhaustive
small-object mask coverage should use iSAID directly.

Released masks are clipped to the oriented box, so wherever the two protocols
disagree about an object's extent the dataset follows DOTA's convention. Users
needing iSAID's extent can recover the unclipped instance through the identity
recorded for every pair.

3,283 pairs (2.61%) reference an iSAID instance whose colour spans several
disconnected components, partly occlusion splits and partly colour reuse.
Extraction is not yet component-aware; clipping bounds the consequence but does
not remove it.

Annotation quality is bounded by the sources, and their errors propagate into
the pairs. Categories are severely imbalanced: three supply 70.4% of pairs,
six under 0.6% each. Only the training and validation splits are covered, as
iSAID publishes no test-split masks. Source imagery cannot be redistributed, so
the deposit provides annotations, metadata and a construction script rather
than images.

> 174 words (cap 200).

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
Software, Validation, Formal analysis, Data curation, Writing – original draft,
Visualization. Add supervisory roles (Supervision, Writing – review & editing)
if the supervisor is a co-author.]]

## Acknowledgements

[[PLACEHOLDER: contributors not meeting authorship criteria, if any.]]

Funding: [[PLACEHOLDER: if none, the template's sentence applies verbatim —
"This research did not receive any specific grant from funding agencies in the
public, commercial, or not-for-profit sectors." Confirm that no NTUA/PhD
funding must be declared.]]

## Declaration of Competing Interests

The authors declare that they have no known competing financial interests or
personal relationships that could have appeared to influence the work reported
in this paper.

---

## References

> Template rule: **maximum 20**, numbered, cited as `[n]`; the deposited dataset
> must itself be cited. Five used; all bibliographic details require
> verification against the publisher record before submission (see
> `references.bib`).

[1] G.-S. Xia, X. Bai, J. Ding, Z. Zhu, S. Belongie, J. Luo, M. Datcu,
M. Pelillo, L. Zhang, DOTA: A large-scale dataset for object detection in
aerial images, in: Proc. IEEE/CVF Conf. Computer Vision and Pattern Recognition
(CVPR), 2018, pp. 3974–3983. [[VERIFY pages/DOI]]

[2] S. Waqas Zamir, A. Arora, A. Gupta, S. Khan, G. Sun, F. Shahbaz Khan,
F. Zhu, L. Shao, G.-S. Xia, X. Bai, iSAID: A large-scale dataset for instance
segmentation in aerial images, in: Proc. IEEE/CVF Conf. Computer Vision and
Pattern Recognition Workshops (CVPRW), 2019, pp. 28–37. [[VERIFY pages/DOI]]

[3] A. Kirillov, E. Mintun, N. Ravi, H. Mao, C. Rolland, L. Gustafson, T. Xiao,
S. Whitehead, A.C. Berg, W.-Y. Lo, P. Dollár, R. Girshick, Segment Anything,
in: Proc. IEEE/CVF Int. Conf. Computer Vision (ICCV), 2023, pp. 4015–4026.
[[VERIFY pages/DOI]]

[4] H.W. Kuhn, The Hungarian method for the assignment problem, Naval Research
Logistics Quarterly 2 (1–2) (1955) 83–97. [[VERIFY DOI]]

[5] P. Virtanen, R. Gommers, T.E. Oliphant, et al., SciPy 1.0: fundamental
algorithms for scientific computing in Python, Nature Methods 17 (2020)
261–272. [[VERIFY author list truncation policy and DOI]]

[6] P. Fragkos, AerialFuseCV: reconciled oriented-box and instance-mask
annotation pairs for aerial imagery [dataset], Zenodo, 2026.
[[PLACEHOLDER: DOI — arrives with the deposit]]

---

## Pre-submission checklist

- [ ] **Deposit live, DOI minted** → fills the Specifications Table, the deposit
      inventory and reference [6].
- [ ] Deposit inventory written from the actual uploaded package.
- [ ] Authorship, affiliation, institutional email and CRediT resolved.
- [ ] Four figures produced from `results/experimental/AerialFuseCV_Testing/`.
- [ ] Official DiB `.docx` template filled; instructional text deleted.
- [ ] Reference details verified against publisher records; ≤20 references.
- [ ] Confirm the current APC.
- [ ] Re-verify every number against the build that the deposit actually ships,
      if a further build is made after this draft.
- [ ] 🔴 REVIEWER pass (hostile read) before submission.

---

## Rewrite note — 2026-08-04 (task P1-WRITE)

This draft replaces DRAFT v0.1 in full.

**What changed.** Every number is now sourced from build `d4c191a` and the
measurement artefacts under `results/experimental/AerialFuseCV_Testing/`; nothing derives
from the MSc thesis, which is not a source for this program. The argument was
rebuilt around protocol divergence: the article now states that two expert
protocols on the same imagery disagree about what an object is, measures that
disagreement over every pair, defines the reconciled mask as the response, and
releases the pairing with exact discard accounting.

**Superseded claims from v0.1, for the record.** The counts changed with the
corrected build (1,857 → 1,862 images; 125,102 → 125,722 pairs; 97.9% → 98.34%
box pairing). The instance-side figures in v0.1 (330,693 source instances,
37.8% retention) were derived by connected-component counting and are wrong;
the exhaustive colour audit measures 475,438 instances and a 26.44% rate. Two
v0.1 limitations no longer hold: the dataset now enforces one-to-one assignment,
so two boxes can no longer reference the same mask component, and it ships
instance-identity masks, so adjacent objects of one category are separable
without the box. Both were removed rather than softened.

**Deliberately not claimed.** Novelty is stated as the correspondence and its
accounting, not as priority over any method line. The masks are described as
consistent with the annotation that delimits them and free of neighbouring
objects by construction — a statement about evaluation validity, not an
agreement score. Pipeline and benchmark numbers are absent by venue rule and by
scope; they belong to P2.
