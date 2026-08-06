#!/usr/bin/env python3
"""Assemble the AerialFuseCV Zenodo deposit. INTERNAL TOOL.

Stages every file the deposit ships into one directory, writes the landing
README and the licence, and emits a file-by-file inventory with sizes and
SHA-256 digests — which the data article's Deposit contents section reports.

Nothing is uploaded. The release is held until the manuscript is submitted, so
the dataset is never sitting in the open with no paper claiming it.

    python dataset/make_zenodo_package.py

Internal files are deliberately excluded: `make_deposit.py` builds the
correspondence and is not something a depositor runs, and `OPTIMISATION_PATCH.md`
is a development note. Shipping either invites questions the deposit should not
have to answer.
"""

import argparse
import hashlib
import json
import shutil
import sys
import time
from pathlib import Path

SHIP = [
    ("correspondence.jsonl", "One record per paired object: image, split, category, "
                             "the index of the box within that image's own DOTA "
                             "annotation file, the matched iSAID instance identity, "
                             "and the achieved overlap."),
    ("discarded.jsonl", "One record per unpaired box or instance, with the reason it "
                        "was dropped and the best overlap it achieved."),
    ("dataset_statistics.json", "Totals, per split, per category, and every discard "
                                "reason with its count."),
    ("checksums.sha256", "Expected SHA-256 of every annotation and mask file the "
                         "rebuild produces (7,448 files)."),
    ("deposit_manifest.json", "Build identity: version, generation date, pair and "
                              "image counts, source dataset references."),
    ("rebuild_aerialfusecv.py", "The rebuild script. Validates your DOTA and iSAID "
                                "copies, resolves the correspondence against them, "
                                "writes the dataset, and verifies it."),
    ("SETUP.md", "Step-by-step: prerequisites, downloads, extraction layout, "
                 "execution, troubleshooting, citation."),
]

EXCLUDE = {"make_deposit.py", "OPTIMISATION_PATCH.md", "__pycache__"}


def sha256(p, chunk=1 << 20):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(chunk), b""):
            h.update(b)
    return h.hexdigest()


def human(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n/1:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} GB"


def size_str(n):
    if n < 1024:
        return f"{n} B"
    if n < 1024 ** 2:
        return f"{n/1024:.1f} KB"
    if n < 1024 ** 3:
        return f"{n/1024**2:.1f} MB"
    return f"{n/1024**3:.2f} GB"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--deposit", type=Path,
                    default=Path("papers/p1_aerialfusecv_descriptor/deposit"))
    ap.add_argument("--out", type=Path,
                    default=Path("zenodo_release/AerialFuseCV_v1.0"))
    ap.add_argument("--version", default="1.0")
    args = ap.parse_args()

    missing = [n for n, _ in SHIP if not (args.deposit / n).exists()]
    if missing:
        sys.exit("missing from the deposit: " + ", ".join(missing))

    if args.out.exists():
        shutil.rmtree(args.out)
    args.out.mkdir(parents=True)

    inventory = []
    for name, desc in SHIP:
        src = args.deposit / name
        shutil.copy2(src, args.out / name)
        st = (args.out / name).stat()
        inventory.append({"file": name, "bytes": st.st_size,
                          "size": size_str(st.st_size),
                          "sha256": sha256(args.out / name), "description": desc})
        print(f"  {name:28} {size_str(st.st_size):>10}")

    stats = json.loads((args.deposit / "dataset_statistics.json").read_text(encoding="utf-8"))
    t = stats["totals"]

    (args.out / "LICENSE.txt").write_text(LICENSE_TEXT, encoding="utf-8")
    readme = README_TEXT.format(
        version=args.version,
        pairs=f"{t['pairs']:,}", images=f"{t['images_kept']:,}",
        boxes=f"{t['boxes']:,}", instances=f"{t['src_instances']:,}",
        box_rate=f"{t['box_pairing_rate']*100:.2f}",
        inst_rate=f"{t['instance_pairing_rate']*100:.2f}",
        table="\n".join(f"| `{i['file']}` | {i['size']} | {i['description']}" + " |"
                        for i in inventory),
    )
    (args.out / "README.md").write_text(readme, encoding="utf-8")

    for extra in ("LICENSE.txt", "README.md"):
        st = (args.out / extra).stat()
        inventory.append({"file": extra, "bytes": st.st_size,
                          "size": size_str(st.st_size),
                          "sha256": sha256(args.out / extra),
                          "description": "Deposit licence." if "LICENSE" in extra
                          else "Deposit landing description and file inventory."})

    total = sum(i["bytes"] for i in inventory)
    manifest = {
        "package": f"AerialFuseCV v{args.version}",
        "assembled_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "files": len(inventory), "total_bytes": total, "total_size": size_str(total),
        "pairs": t["pairs"], "images": t["images_kept"],
        "released": False,
        "release_policy": "Held until the data article is submitted, so the "
                          "dataset is never public with no paper claiming it.",
        "inventory": inventory,
    }
    (args.out.parent / "package_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8")

    print(f"\n  {len(inventory)} files, {size_str(total)} total")
    print(f"  package  -> {args.out}")
    print(f"  manifest -> {args.out.parent/'package_manifest.json'}")
    print("\n  NOT uploaded. Release when the manuscript is submitted.")
    return 0


LICENSE_TEXT = """AerialFuseCV — licence

WHAT THIS DEPOSIT CONTAINS

This deposit contains no imagery, no source annotations and no source masks. It
contains the object-level correspondence between DOTA v1.0 and iSAID computed by
this work, the discard records, summary statistics, verification checksums, and
a script that rebuilds the dataset from your own copies of the two sources.


TERMS OF THE PARENT DATASETS

AerialFuseCV is derived from, and cannot be used without, two datasets that
carry their own terms.

  DOTA v1.0   https://captain-whu.github.io/DOTA/dataset.html
  iSAID       https://captain-whu.github.io/iSAID/dataset.html

Both state, verbatim:

  "All images and their associated annotations ... can be used for academic
   purposes only, but any commercial use is prohibited."

Both additionally require that use of the Google Earth imagery respect Google's
geospatial terms of use:

  https://www.google.com/permissions/geoguidelines.html

Neither dataset declares a redistribution policy or a formal licence.


TERMS OF THIS DEPOSIT

Because the dataset this deposit reconstructs is inseparable from sources that
prohibit commercial use, this deposit is released under

  Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0)
  https://creativecommons.org/licenses/by-nc/4.0/

You may share and adapt the correspondence for non-commercial purposes with
attribution. A permissive licence allowing commercial use was considered and
rejected: it would purport to grant a freedom over derived records that the
underlying data does not permit in practice, which would mislead rather than
help.

This licence covers the contents of this deposit only. It grants no rights over
DOTA v1.0 or iSAID, and it does not relax their terms. Obtain both from their
official pages and use them under their own conditions.


ATTRIBUTION

Cite the data article and this deposit, and cite both parent datasets. See
"How to cite" in SETUP.md.
"""


README_TEXT = """# AerialFuseCV v{version}

Object-level correspondence between **DOTA v1.0** oriented bounding boxes and
**iSAID** instance segmentation masks, over the aerial imagery both annotate.

{pairs} paired objects across {images} images and 15 categories. For every pair,
the deposit records which DOTA box and which iSAID instance describe the same
physical object — a linkage neither source publishes.

## Read this first

**This deposit contains no imagery and no source annotations.** Both parent
datasets restrict use to academic purposes and neither declares a
redistribution policy, so what is published here is the correspondence this
work computed, together with a script that rebuilds the full dataset on your
machine from your own copies of DOTA v1.0 and iSAID.

**`SETUP.md` is the instruction manual.** It covers prerequisites, where to
download each source, how to arrange the extracted folders, the commands to
run, and the two mistakes that account for most failed rebuilds.

Rebuilding takes about ten minutes and roughly 30 GB of disk. The included
checksums then verify the result file by file — 7,448 files — so you can
confirm your rebuild is identical to the one described in the data article.

## Contents

| File | Size | Description |
|---|---|---|
{table}

## How it was built

Each DOTA box was matched to an iSAID instance of the same category by an
optimal one-to-one assignment maximising total intersection-over-union between
the rasterised oriented quadrilateral and the instance, accepting matches from
an IoU of 0.1. The released mask for a pair is the matched instance **clipped to
its oriented box**.

Of {boxes} source boxes and {instances} source instances over the shared
imagery, {pairs} pairs were formed: {box_rate}% of boxes received a mask, and
{inst_rate}% of instances received a box. The two rates differ because pairing
is anchored on the boxes and iSAID annotates many objects DOTA does not. Every
unpaired box and instance is recorded in `discarded.jsonl` with its reason;
pairs plus discards equal each source population exactly.

## Licence

**Non-commercial research and academic use only**, inherited from both parent
datasets. See `LICENSE.txt`.

## Citation

See "How to cite" in `SETUP.md`. Please cite the data article, this deposit,
and both parent datasets.
"""


if __name__ == "__main__":
    sys.exit(main())
