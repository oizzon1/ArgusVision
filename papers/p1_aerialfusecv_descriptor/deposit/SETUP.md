# AerialFuseCV — setup and rebuild guide

This deposit does not contain imagery or source annotations. It contains the
**correspondence** between DOTA v1.0 and iSAID that this work computed, plus a
script that rebuilds the full AerialFuseCV dataset on your machine from your own
copies of the two sources.

Neither DOTA v1.0 nor iSAID declares a redistribution policy, and both state
that their images and annotations *"can be used for academic purposes only, but
any commercial use is prohibited"*. You therefore download the sources yourself,
under their terms, and the script materialises the dataset locally.

Follow the five steps below in order. Expect **about 30 minutes**, most of it
downloading.

---

## 1. Prerequisites

| Requirement | Detail |
|---|---|
| Python | 3.8 or newer |
| Packages | `numpy`, `opencv-python` |
| Disk space | **~30 GB** — see the budget below |
| Time | ~10 min to rebuild, plus download time |
| OS | Any. Verified on Windows 10 (Python 3.9.18, numpy 2.0.2, OpenCV 4.12.0) |

```bash
python -m pip install numpy opencv-python
```

No GPU is required. No deep-learning framework is required.

### Disk budget

| Item | Size |
|---|---|
| DOTA v1.0 train (images + labels) | 11 GB |
| DOTA v1.0 val (images + labels) | 3.3 GB |
| iSAID train (masks) | 455 MB |
| iSAID val (masks) | 154 MB |
| **Rebuilt AerialFuseCV** | **14 GB** |
| Total, keeping the sources | ~29 GB |

The rebuilt dataset copies the DOTA images so it is self-contained. Pass
`--image-mode none` to write annotations and masks only, which reduces the
output to roughly 1 GB; the dataset then references your DOTA images in place.

---

## 2. Download DOTA v1.0

Official page: <https://captain-whu.github.io/DOTA/dataset.html>

The page offers **Baidu Drive** and **Google Drive** links. Take the **DOTA-v1.0**
section only — v1.5 and v2.0 use different annotations and will not resolve
against this correspondence.

The DOTA-v1.0 Google Drive folder contains three items:

```
images/            the imagery, by split
labelTxt-v1.0/     <- TAKE THIS ONE
labelTxt-v1.5/     <- NOT this one
```

Download `images/` and `labelTxt-v1.0/` for the **training** and **validation**
splits.

**Do not download the test set.** iSAID publishes no test-split masks, so
AerialFuseCV covers train and val only. Anything you download for `test/` is
ignored.

The training images are split across several archives. Extract them all into one
folder — the split is a transfer convenience, not a structure.

---

## 3. Download iSAID

Official page: <https://captain-whu.github.io/iSAID/dataset.html>

Download the **Training set** and **Validation set**, from either Baidu Drive or
Google Drive. Each split's folder contains three items:

```
Annotations/       COCO-format JSON — not needed
Instance_masks/    <- TAKE THIS ONE
Semantic_masks/    <- and this one
```

**You do not need to run the iSAID devkit.** The mask folders ship the rendered
PNGs directly — `P0000_instance_id_RGB.png`, `P0000_instance_color_RGB.png` —
so no preprocessing step is required. 

**You do not need iSAID's images.** iSAID re-annotates DOTA's imagery, and the
rebuild takes the images from your DOTA download.

Note the capitalisation: the folders arrive as `Instance_masks` and
`Semantic_masks`. **Rename them to lowercase** — `instance_masks`,
`semantic_masks`. On Windows this makes no difference, but on Linux and macOS
the paths are case-sensitive and the script will report them as missing.

---

## 4. Arrange into the expected layout

Rename and move the extracted folders so they look **exactly** like this. The
script checks this before it does any work and will tell you precisely what is
missing.

```
<your DOTA folder>/
├── train/
│   ├── images/          P0000.png … 1,411 files
│   └── labels/          P0000.txt … 1,411 files   (DOTA labelTxt)
└── val/
    ├── images/          458 files
    └── labels/          458 files

<your iSAID folder>/
├── train/
│   ├── instance_masks/  P0000_instance_id_RGB.png … 1,411 files
│   └── semantic_masks/  P0000_instance_color_RGB.png … 1,411 files
└── val/
    ├── instance_masks/  458 files
    └── semantic_masks/  458 files
```

Renames required, because the archives do not arrive with these names:

| Arrives as | Rename to |
|---|---|
| `labelTxt-v1.0` | `labels` |
| `Instance_masks` | `instance_masks` |
| `Semantic_masks` | `semantic_masks` |

Other notes:

- Extra files alongside these directories are harmless and ignored — a `test/`
  folder, `iSAID_train.json`, documentation PDFs.
- Only `instance_masks/` is read during the rebuild. `semantic_masks/` is
  checked for presence because the two ship together and a missing one signals
  an incomplete extraction.
- The two roots may live anywhere and need not be siblings.

To confirm the counts before running anything:

```bash
ls <dota>/train/images  | wc -l   # 1411
ls <dota>/train/labels  | wc -l   # 1411
ls <dota>/val/images    | wc -l   # 458
ls <isaid>/train/instance_masks | wc -l   # 1411
ls <isaid>/val/instance_masks   | wc -l   # 458
```

---

## 5. Rebuild

Run from the deposit folder, so the script finds `correspondence.jsonl` beside
itself.

**Interactive** — prompts for each location:

```bash
python rebuild_aerialfusecv.py --verify
```

**Non-interactive:**

```bash
python rebuild_aerialfusecv.py \
    --dota  /path/to/DOTA_v1 \
    --isaid /path/to/iSAID \
    --out   /path/to/output \
    --verify
```

An `AerialFuseCV/` folder is created **inside** the output path you give, so
pointing this at a directory holding other datasets will not scatter files
across it.

The script prints its source check, then a progress bar driven by object count
rather than image count — image sizes and object density vary by two orders of
magnitude across DOTA, so an image-count bar would badly misreport how much work
remains.

### Always pass `--verify`

It checks all 7,448 regenerated annotation and mask files against the published
SHA-256 checksums. A silent success is not evidence; the expected final lines
are:

```
7,448 files checked, 0 missing, 0 mismatched
checksum verification: PASS
```

If verification fails, your rebuild does **not** match the published dataset and
should not be used. See troubleshooting below.

---

## What you get

```
AerialFuseCV/
├── train/                      1,406 images
│   ├── images/                 P####.png
│   ├── labels_obb/             P####.txt   oriented quadrilaterals
│   ├── labels_hbb/             P####.txt   axis-aligned hulls
│   ├── instance_masks/         P####_instance_id_RGB.png
│   └── semantic_masks/         P####_instance_color_RGB.png
├── val/                          456 images, same five subdirectories
├── pairs.jsonl                 one record per paired object
├── discarded.jsonl             one record per unpaired box or instance
├── dataset_statistics.json     totals, per split, per category, discards
├── images_gsd_mapping.json     per-image ground sample distance
├── build_manifest.json         run identity, arguments, environment, timings
├── checksums.sha256            expected hash of every regenerated file
└── summary.md                  short summary of this build
```

125,722 paired objects over 1,862 images and 15 categories. Each released mask
is the matched iSAID instance clipped to its DOTA oriented box.

---

## Troubleshooting

**"expected source directories are missing"** — the layout in step 4 does not
match. The message names each missing directory; the usual cause is `labelTxt`
not renamed to `labels`, or images extracted one level too deep
(`train/images/images/`).

**"Some files the correspondence refers to are not present"** — the layout is
right but the download is incomplete. The message reports how many of each kind
are missing with examples. The usual cause is DOTA's multi-part training images
where not every archive was extracted.

**"box_index out of range"** or **"class mismatch"** — your DOTA annotations
differ from those the correspondence was built against. **In almost every case
this is `labelTxt-v1.5` extracted instead of `labelTxt-v1.0`**, since the two
sit beside each other in the same Drive folder. Check the folder you extracted
and re-take v1.0.

**"iSAID instance not found in mask"** — the iSAID masks do not match the
expected build. Check you took the v1 iSAID release and that extraction
completed.

**Verification fails but the rebuild reported no problems** — check free disk
space first; a truncated write produces a valid-looking file with a wrong hash.
`build_manifest.json` records your Python, numpy and OpenCV versions, which is
the first thing to compare against the verified environment in the table above.

**It looks frozen on one image** — dense images carry over 1,700 objects and
take noticeably longer. The progress bar is driven by objects, so it will keep
moving even when the image counter does not.

---

## Licensing

AerialFuseCV is intended for **non-commercial research and academic use only**,
in accordance with the licences of both parent datasets. DOTA v1.0 and iSAID
each state that their images and annotations may be used for academic purposes
only and prohibit commercial use, and both require that use of the Google Earth
imagery respect Google's geospatial terms of use. Obtain both sources from their
official pages, under their own terms.

The deposit itself contains no source imagery, annotations or masks — only the
correspondence computed by this work, the discard records, statistics,
checksums and this script.

---

## How to cite

If AerialFuseCV contributes to your work, please cite **both** the data article
and the deposit. The article describes the construction and its limitations;
the deposit DOI pins the exact version you used.

```bibtex
@article{[[PLACEHOLDER: article key]],
  author  = {[[PLACEHOLDER: author list — depends on the authorship decision]]},
  title   = {AerialFuseCV: reconciled oriented-box and instance-mask
             annotation pairs for aerial imagery},
  journal = {Data in Brief},
  year    = {2026},
  doi     = {[[PLACEHOLDER: article DOI — arrives on acceptance]]}
}

@dataset{[[PLACEHOLDER: dataset key]],
  author    = {[[PLACEHOLDER: author list]]},
  title     = {AerialFuseCV v1.0},
  publisher = {Zenodo},
  year      = {2026},
  doi       = {[[PLACEHOLDER: dataset DOI — arrives with the deposit]]}
}
```

**Cite the parent datasets too.** AerialFuseCV is a correspondence between DOTA
v1.0 and iSAID, and neither is substitutable by it — work using AerialFuseCV
depends on both:

- Xia et al., *DOTA: A Large-Scale Dataset for Object Detection in Aerial
  Images*, CVPR 2018.
- Waqas Zamir et al., *iSAID: A Large-scale Dataset for Instance Segmentation
  in Aerial Images*, CVPRW 2019.

---

## Naming and derived versions

`AerialFuseCV` names this specific correspondence, built by the procedure
described in the data article and pinned by the deposit DOI. Two requests,
which cost nothing to honour and keep the record clear for everyone:

- **Report the version and DOI** you used. The correspondence can be rebuilt
  and revised; "AerialFuseCV" alone does not identify which one you had.
- **If you modify it — different matching rule, different mask definition,
  added or removed pairs — please give the result its own name**, or make the
  derivation explicit (for example *"AerialFuseCV v1.0, re-matched at IoU
  0.3"*). Redistributing altered pairings under the plain name makes results
  built on it non-comparable, and the difference is invisible to anyone
  downstream.

These are conventions, not restrictions. Rebuilding, modifying and
redistributing your own variants is expected and welcome — the whole deposit
exists so the construction can be reproduced and changed. What matters is that
readers can tell which version produced which numbers.

Nothing here overrides the parent datasets' terms: **non-commercial research
and academic use only**.

---
