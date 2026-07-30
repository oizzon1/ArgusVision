# P1 Data Description — DRAFT v0.1 (2026-07-30)

> Sources: thesis §3.1 Tables 6–7 and pp. 59–60 (structure, class
> distribution); source-dataset properties from thesis §2 (pp. 37, 41).
> Derived values are marked ⚠ and must be reconciled against the deposit's
> `Dataset_Statistics.md` at P0.
>
> ⛔ The deposit file inventory cannot be finalised until P0 fixes the release
> layout. Everything describing the *data itself* is complete.

## Contents and organisation

AerialFuseCV is organised as three parallel directories per split, so that a
detector can consume images and labels by standard YOLO conventions, a
segmentation model can read the mask directory, and an integrated pipeline can
use all three simultaneously:

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
identity, using the iSAID class-colour table; a black background denotes
absence of any annotated object.

## Image properties

Imagery is inherited unchanged from DOTA v1.0 / iSAID: variable-size
high-resolution scenes captured at 0.12–3.0 m ground sample distance from
Google Earth, the JL-1 satellite and the Gaofen-2 satellite. No resizing,
retiling or radiometric adjustment was applied, so per-image GSD metadata
remains applicable and object scale varies by more than an order of magnitude
across the collection.

## Scale and pairing outcome (Table 1)

| Split | Source boxes | Paired | Box pairing rate | Images retained |
|---|---|---|---|---|
| Train | 98,990 | 97,070 | 98.1% | 1,401 |
| Validation | 28,853 | 28,032 | 97.2% | 456 |
| **Total** | **127,843** | **125,102** | **97.9%** | **1,857** |

The collection begins from the 1,869 images (1,411 train / 458 validation)
that DOTA v1.0 and iSAID annotate in common — 66.6% of DOTA's 2,806
train-and-validation images; the 937 test images are excluded because iSAID
publishes no masks for them. Twelve images (10 train, 2 validation) retained
no pair at all and were dropped, leaving 1,857.

## Pairing is box-anchored: two retention rates

Matching takes the DOTA boxes as its baseline, so the 97.9% headline is a
**box-side** rate: 97.9% of annotated boxes received a mask. The mask side
behaves very differently, because iSAID annotates far more objects than DOTA —
655,451 instances against 188,282 across the full benchmark, its annotators
having included very small and partially occluded objects that DOTA omitted.

Within the 1,869-image subset the source masks contain ⚠ 330,693 instances,
of which the 125,102 pairs represent ⚠ 37.8%; ⚠ 205,591 mask instances have no
corresponding box and are therefore absent from the released masks. The
imbalance is category-dependent and extreme for small objects: in the training
split iSAID marks ⚠ 6.2× more small-vehicle instances than DOTA boxes
(160,844 against 26,126).

Users should read this as a definition rather than a defect. AerialFuseCV
inherits DOTA's annotation policy, and each released mask instance is one that
a box confirms. Work needing exhaustive mask coverage of small objects should
use iSAID directly.

## Per-category statistics (Table 2)

Per split and category the deposit reports source boxes, source mask
instances, paired boxes, and the resulting rate (thesis Table 7 reproduced).
All 15 categories pair between 83.6% and 100%. The lowest rates are helicopter
(83.6% validation — objects typically 10–20 px, giving ambiguous box–mask
boundaries), harbor (89.6% training — irregular dock and pier geometry
annotated differently by the two sources), soccer-ball-field (92.2%
validation), and basketball-court and large-vehicle (both 93.2% validation,
attributable to occlusion and density in urban scenes).

## Category distribution (Figure 2)

The distribution is severely imbalanced, mirroring both source datasets and
real-world aerial imagery. Three transport and maritime categories supply
71.0% of all pairs — ship 36,903 (29.5%), small-vehicle 31,073 (24.8%),
large-vehicle 20,797 (16.6%). Six categories are moderately represented,
together 26.3%: plane 8.1%, storage-tank 6.2%, harbor 5.8%, tennis-court 2.5%,
bridge 2.0%, swimming-pool 1.7%. The remaining six each contribute under 0.6%,
2.7% in total: helicopter 0.5%, basketball-court 0.5%, baseball-diamond 0.5%,
roundabout 0.4%, soccer-ball-field 0.4%, ground-track-field 0.4%.

Aggregate metrics computed over this dataset are therefore dominated by
vehicle and ship performance, and per-category reporting is advisable; every
category nonetheless retains enough absolute instances for meaningful
per-class evaluation. The distribution closely tracks that of the sources,
indicating that pairing introduced no systematic category bias.

## Deposit contents (⛔ P0)

To be completed once the release layout is fixed: annotation and pairing
files, per-category statistics, the construction script and its checksums, and
the licence. Source imagery is not redistributable, so the deposit ships
annotations plus a rebuild path rather than images.

---

## Notes for the write-up

- ⚠ values (330,693 / 37.8% / 205,591 / 6.2×) are derived here by summing
  thesis Table 7 mask columns. Table 7's box and matched columns reproduce
  Table 6 exactly (127,843 and 125,102), which validates the reading, but the
  mask totals are not stated anywhere in the thesis — regenerate them from
  `Dataset_Statistics.md` during P0 and cite that file, not this derivation.
- Category counts follow the thesis **tables**, not its prose: p. 59 miscounts
  the moderate group as "seven" and the rare group as "five" (six each), and
  p. 58's list of lowest performers omits soccer-ball-field. See
  `ATHENA_STATE.md` errata note.
- Table 1 ≈ thesis Table 6; Table 2 ≈ thesis Table 7; Figure 2 ≈ thesis
  Figure 16.
