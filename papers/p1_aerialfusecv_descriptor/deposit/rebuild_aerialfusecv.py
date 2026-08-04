#!/usr/bin/env python3
"""Rebuild AerialFuseCV from the official DOTA v1.0 and iSAID distributions.

AerialFuseCV is a *correspondence*: for each object, a link between one DOTA
oriented bounding box and one iSAID instance mask, together with a reconciled
mask definition. The imagery and the source annotations belong to DOTA and
iSAID and are not redistributed here — this script reconstructs the full
dataset on your machine from your own copies of those datasets.

WHAT YOU NEED
    DOTA v1.0   train/val images and labelTxt   https://captain-whu.github.io/DOTA/
    iSAID       train/val semantic + instance masks   https://captain-whu.github.io/iSAID/
    (iSAID's masks are downloaded directly; its images come from DOTA.)

EXPECTED SOURCE LAYOUT
    <dota>/{train,val}/images/<id>.png
    <dota>/{train,val}/labels/<id>.txt        (DOTA labelTxt format)
    <isaid>/{train,val}/semantic_masks/<id>_instance_color_RGB.png
    <isaid>/{train,val}/instance_masks/<id>_instance_id_RGB.png

USAGE
    python rebuild_aerialfusecv.py --dota /path/to/DOTA_v1 \
                                   --isaid /path/to/iSAID \
                                   --out /path/to/AerialFuseCV

    Add --verify to check the result against the published checksums.

OUTPUT (per split)
    images/                 the DOTA image, unchanged
    labels_obb/             paired boxes only, DOTA format, oriented corners
    labels_hbb/             the same boxes as axis-aligned hulls
    semantic_masks/         paired instances, coloured by category
    instance_masks/         paired instances, coloured by instance identity

Requires: python >= 3.8, numpy, opencv-python.
Licence: see LICENSE.txt. DOTA and iSAID remain under their own terms.
"""

import argparse
import hashlib
import json
import shutil
import sys
from collections import defaultdict
from pathlib import Path

try:
    import cv2
    import numpy as np
except ImportError:  # pragma: no cover
    sys.exit("This script needs numpy and opencv-python:\n"
             "    pip install numpy opencv-python")

SPLITS = ("train", "val")

# iSAID category colours (RGB) -> DOTA class name.
CLASS_COLOURS = {
    "plane": (0, 127, 255), "ship": (0, 0, 63), "storage-tank": (0, 63, 63),
    "baseball-diamond": (0, 63, 0), "tennis-court": (0, 63, 127),
    "basketball-court": (0, 63, 191), "ground-track-field": (0, 63, 255),
    "harbor": (0, 100, 155), "bridge": (0, 127, 63), "large-vehicle": (0, 127, 127),
    "small-vehicle": (0, 0, 127), "helicopter": (0, 0, 191), "roundabout": (0, 191, 127),
    "soccer-ball-field": (0, 127, 191), "swimming-pool": (0, 0, 255),
}


def read_rgb(path):
    bgr = cv2.imread(str(path), cv2.IMREAD_COLOR)
    return None if bgr is None else cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)


def parse_dota_labels(path):
    """Return (objects, gsd, imagesource).

    `objects` is a list of (corners, class_name, difficulty) in file order —
    the order the correspondence indexes into. Header lines and unparsable or
    unknown-category lines are skipped, exactly as during construction.
    """
    objects, gsd, imagesource = [], None, None
    if not path.exists():
        return objects, gsd, imagesource
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        parts = line.split()
        if not parts:
            continue
        if parts[0].startswith("imagesource:"):
            imagesource = line.split(":", 1)[1].strip() if ":" in line else None
            continue
        if parts[0].startswith("gsd:"):
            tail = line.split(":", 1)[1].strip() if ":" in line else ""
            try:
                gsd = float(tail)
            except ValueError:
                gsd = None
            continue
        if len(parts) < 10:
            continue
        try:
            corners = [float(v) for v in parts[:8]]
        except ValueError:
            continue
        if parts[8] not in CLASS_COLOURS:
            continue
        objects.append((corners, parts[8], parts[9]))
    return objects, gsd, imagesource


def hull_corners(corners):
    xs, ys = corners[0::2], corners[1::2]
    x1, y1, x2, y2 = min(xs), min(ys), max(xs), max(ys)
    return [x1, y1, x2, y1, x2, y2, x1, y2]


def write_labels(path, rows, gsd, imagesource):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        if imagesource:
            f.write(f"imagesource:{imagesource}\n")
        if gsd is not None:
            f.write(f"gsd:{gsd}\n")
        for corners, cls, diff in rows:
            f.write(" ".join(f"{v:.1f}" for v in corners) + f" {cls} {diff}\n")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def rebuild_image(img_id, split, records, dota, isaid, out, image_mode):
    """Reconstruct one image's annotations. Returns (n_pairs, problem or None)."""
    label_src = dota / split / "labels" / f"{img_id}.txt"
    objects, gsd, imagesource = parse_dota_labels(label_src)
    if not objects:
        return 0, f"{img_id}: no DOTA labels at {label_src}"

    ins = read_rgb(isaid / split / "instance_masks" / f"{img_id}_instance_id_RGB.png")
    if ins is None:
        return 0, f"{img_id}: missing iSAID instance mask"

    shape = ins.shape[:2]
    sem_out = np.zeros((*shape, 3), np.uint8)
    ins_out = np.zeros((*shape, 3), np.uint8)
    obb_rows, hbb_rows = [], []

    for rec in records:
        idx = rec["box_index"]
        if idx >= len(objects):
            return 0, (f"{img_id}: box_index {idx} out of range ({len(objects)} objects). "
                       "Source labels differ from the ones used to build the correspondence.")
        corners, cls, diff = objects[idx]
        if cls != rec["class_name"]:
            return 0, (f"{img_id}: class mismatch at box {idx} "
                       f"(source '{cls}', correspondence '{rec['class_name']}')")

        colour = np.array(rec["instance_rgb"], np.uint8)
        instance = np.all(ins == colour, axis=-1)
        if not instance.any():
            return 0, f"{img_id}: iSAID instance {tuple(colour)} not found in mask"

        # Reconciled mask: the matched instance, clipped to its oriented box.
        poly = np.zeros(shape, np.uint8)
        cv2.fillPoly(poly, [np.round(np.array(corners).reshape(4, 2)).astype(np.int32)], 1)
        clipped = instance & (poly > 0)
        sel = clipped if clipped.any() else instance

        sem_out[sel] = CLASS_COLOURS[cls]
        ins_out[sel] = colour
        obb_rows.append((corners, cls, diff))
        hbb_rows.append((hull_corners(corners), cls, diff))

    write_labels(out / split / "labels_obb" / f"{img_id}.txt", obb_rows, gsd, imagesource)
    write_labels(out / split / "labels_hbb" / f"{img_id}.txt", hbb_rows, gsd, imagesource)
    for sub, tag, arr in (("semantic_masks", "instance_color", sem_out),
                          ("instance_masks", "instance_id", ins_out)):
        p = out / split / sub / f"{img_id}_{tag}_RGB.png"
        p.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(p), cv2.cvtColor(arr, cv2.COLOR_RGB2BGR))

    if image_mode != "none":
        src = dota / split / "images" / f"{img_id}.png"
        dst = out / split / "images" / f"{img_id}.png"
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.exists() and not dst.exists():
            shutil.copy2(src, dst)
    return len(records), None


def main():
    here = Path(__file__).resolve().parent
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dota", type=Path, required=True, help="DOTA v1.0 root")
    ap.add_argument("--isaid", type=Path, required=True, help="iSAID root")
    ap.add_argument("--out", type=Path, required=True, help="where to build AerialFuseCV")
    ap.add_argument("--correspondence", type=Path, default=here / "correspondence.jsonl")
    ap.add_argument("--image-mode", choices=("copy", "none"), default="copy",
                    help="copy = self-contained dataset (default); none = annotations only")
    ap.add_argument("--verify", action="store_true",
                    help="check the rebuilt annotations against published checksums")
    args = ap.parse_args()

    if not args.correspondence.exists():
        sys.exit(f"correspondence file not found: {args.correspondence}")

    missing = [str(p) for s in SPLITS
               for p in (args.dota / s / "images", args.dota / s / "labels",
                         args.isaid / s / "semantic_masks", args.isaid / s / "instance_masks")
               if not p.exists()]
    if missing:
        print("ERROR: expected source directories are missing:", file=sys.stderr)
        for p in missing:
            print("   " + p, file=sys.stderr)
        sys.exit("\nSee the layout described at the top of this script.")

    by_image = defaultdict(list)
    for line in open(args.correspondence, encoding="utf-8"):
        r = json.loads(line)
        by_image[(r["split"], r["image_id"])].append(r)
    total_records = sum(len(v) for v in by_image.values())
    print(f"correspondence: {total_records:,} pairs over {len(by_image):,} images")

    args.out.mkdir(parents=True, exist_ok=True)
    built = pairs = 0
    problems = []
    for n, ((split, img_id), records) in enumerate(sorted(by_image.items()), 1):
        got, problem = rebuild_image(img_id, split, records, args.dota, args.isaid,
                                     args.out, args.image_mode)
        if problem:
            problems.append(problem)
        else:
            built += 1
            pairs += got
        if n % 200 == 0:
            print(f"  {n:,}/{len(by_image):,} images", flush=True)

    print(f"\nrebuilt {built:,} images, {pairs:,} pairs -> {args.out}")
    if problems:
        print(f"\n{len(problems)} image(s) could not be rebuilt:", file=sys.stderr)
        for p in problems[:20]:
            print("   " + p, file=sys.stderr)
        if len(problems) > 20:
            print(f"   ... and {len(problems) - 20} more", file=sys.stderr)

    ok = not problems and pairs == total_records
    if args.verify:
        checks = here / "checksums.sha256"
        if not checks.exists():
            print("no checksums.sha256 in the deposit; skipping verification")
        else:
            bad = 0
            for line in open(checks, encoding="utf-8"):
                want, rel = line.strip().split("  ", 1)
                got = args.out / rel
                if not got.exists() or sha256(got) != want:
                    bad += 1
                    if bad <= 10:
                        print(f"   MISMATCH {rel}", file=sys.stderr)
            print(f"\nchecksum verification: {'PASS' if bad == 0 else f'{bad} file(s) differ'}")
            ok = ok and bad == 0

    print("\n" + ("Rebuild complete." if ok else "Rebuild finished WITH PROBLEMS — see above."))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
