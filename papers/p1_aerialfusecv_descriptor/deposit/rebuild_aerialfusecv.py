#!/usr/bin/env python3
"""Rebuild AerialFuseCV from the official DOTA v1.0 and iSAID distributions.

AerialFuseCV is a *correspondence*: for each object, a link between one DOTA
oriented bounding box and one iSAID instance mask, together with a reconciled
mask definition. The imagery and the source annotations belong to DOTA and
iSAID and are not redistributed here — this script reconstructs the full
dataset on your machine from your own copies of those datasets.

WHAT YOU NEED
    DOTA v1.0   train/val images and labelTxt   https://captain-whu.github.io/DOTA/
    iSAID       train/val instance + semantic masks   https://captain-whu.github.io/iSAID/
    (iSAID's masks are downloaded directly; its images come from DOTA.)

    See SETUP.md for step-by-step download and extraction instructions.

EXPECTED SOURCE LAYOUT
    <dota>/train/images/P####.png          <dota>/val/images/P####.png
    <dota>/train/labels/P####.txt          <dota>/val/labels/P####.txt
    <isaid>/train/instance_masks/P####_instance_id_RGB.png
    <isaid>/train/semantic_masks/P####_instance_color_RGB.png
    <isaid>/val/...  (same two subdirectories)

    A `test` directory in either source is ignored — iSAID publishes no
    test-split masks, so AerialFuseCV covers train and val only.

USAGE
    Interactive (prompts for each location):
        python rebuild_aerialfusecv.py

    Non-interactive:
        python rebuild_aerialfusecv.py --dota D:\\AI_Datasets\\DOTA_v1 \\
                                       --isaid D:\\AI_Datasets\\iSAID \\
                                       --out D:\\AI_Datasets\\AerialFuseCV

    Add --verify to check the result against the published checksums.

OUTPUT (per split)
    images/                 the DOTA image, unchanged
    labels_obb/             paired boxes only, DOTA format, oriented corners
    labels_hbb/             the same boxes as axis-aligned hulls
    semantic_masks/         paired instances, coloured by category
    instance_masks/         paired instances, coloured by instance identity

OUTPUT (dataset root)
    pairs.jsonl             one record per paired object, with resolved geometry
    discarded.jsonl         one record per unpaired box or instance
    dataset_statistics.json totals, per split, per category, discards
    images_gsd_mapping.json per-image ground sample distance
    build_manifest.json     run identity, arguments, environment, timings
    checksums.sha256        expected hash of every regenerated annotation file
    summary.md              short summary of this build

Requires: python >= 3.8, numpy, opencv-python.
Licence: see LICENSE.txt. DOTA and iSAID remain under their own terms.
"""

import argparse
import hashlib
import json
import platform
import shutil
import sys
import time
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

REQUIRED = {
    "dota": ["{split}/images", "{split}/labels"],
    "isaid": ["{split}/instance_masks", "{split}/semantic_masks"],
}


# ----------------------------------------------------------------- interface

class Progress:
    """Single-line progress bar driven by PAIRS, not images.

    Cost is dominated by pair count, and pair density varies by two orders of
    magnitude across DOTA images — an image-count bar would sit at "80% done"
    while most of the remaining work was still ahead. Falls back to periodic
    lines when stdout is redirected to a file.
    """

    def __init__(self, total_images, total_pairs, stream=sys.stdout):
        self.total_images = total_images
        self.total_pairs = total_pairs
        self.stream = stream
        self.tty = hasattr(stream, "isatty") and stream.isatty()
        self.images = 0
        self.pairs = 0
        self.t0 = time.time()
        self.last = 0.0

    @staticmethod
    def _clock(seconds):
        seconds = int(max(0, seconds))
        h, rem = divmod(seconds, 3600)
        m, s = divmod(rem, 60)
        return f"{h:d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"

    def update(self, img_id, n_pairs, force=False):
        self.images += 1
        self.pairs += n_pairs
        now = time.time()
        # A dense image can take minutes; refresh often enough that the user
        # can tell the difference between working and wedged.
        if not force and now - self.last < (0.5 if self.tty else 15.0):
            return
        self.last = now

        elapsed = now - self.t0
        frac = self.pairs / self.total_pairs if self.total_pairs else 1.0
        eta = (elapsed / frac - elapsed) if frac > 0.001 else 0
        rate = self.pairs / elapsed if elapsed > 0 else 0

        if self.tty:
            width = 28
            filled = int(width * frac)
            bar = "#" * filled + "-" * (width - filled)
            line = (f"\r  [{bar}] {frac*100:5.1f}%  "
                    f"{self.images:,}/{self.total_images:,} img  "
                    f"{self.pairs:,}/{self.total_pairs:,} pairs  "
                    f"{rate:,.0f} pair/s  elapsed {self._clock(elapsed)}  "
                    f"ETA {self._clock(eta)}   ")
            self.stream.write(line[:158].ljust(158))
        else:
            self.stream.write(
                f"  {frac*100:5.1f}%  {self.images:,}/{self.total_images:,} img  "
                f"{self.pairs:,}/{self.total_pairs:,} pairs  "
                f"elapsed {self._clock(elapsed)}  ETA {self._clock(eta)}  "
                f"[{img_id}, {n_pairs:,} pairs]\n")
        self.stream.flush()

    def close(self):
        if self.tty:
            self.stream.write("\n")
        self.stream.flush()


def banner(text):
    print("\n" + text)
    print("-" * max(12, len(text)))


def prompt_path(question, must_exist=True, default=None):
    """Ask for a directory. Accepts quoted paths pasted from a file manager."""
    while True:
        suffix = f" [{default}]" if default else ""
        try:
            raw = input(f"{question}{suffix}\n  > ").strip()
        except EOFError:
            sys.exit("\nno input available — pass --dota, --isaid and --out instead")
        if not raw and default:
            raw = str(default)
        if not raw:
            print("  ! please enter a path")
            continue
        raw = raw.strip().strip('"').strip("'")
        p = Path(raw).expanduser()
        if must_exist and not p.is_dir():
            print(f"  ! not a directory: {p}")
            continue
        return p


def describe_sources(dota, isaid):
    """Check the source layout. Returns (ok, lines) — lines are always shown.

    Fails loudly and specifically before any work starts, rather than part way
    through a multi-hour run.
    """
    lines, ok = [], True
    for label, root, patterns in (("DOTA", dota, REQUIRED["dota"]),
                                  ("iSAID", isaid, REQUIRED["isaid"])):
        lines.append(f"{label}: {root}")
        for split in SPLITS:
            for pat in patterns:
                sub = root / pat.format(split=split)
                if not sub.is_dir():
                    lines.append(f"   MISSING  {pat.format(split=split)}")
                    ok = False
                    continue
                n = sum(1 for _ in sub.iterdir())
                lines.append(f"   ok       {pat.format(split=split):<26} {n:>7,} files")
    return ok, lines


def cross_check(by_image, dota, isaid):
    """Confirm every image the correspondence needs is actually present."""
    missing = defaultdict(list)
    for split, img_id in sorted(by_image):
        for path, kind in (
                (dota / split / "labels" / f"{img_id}.txt", "DOTA label"),
                (dota / split / "images" / f"{img_id}.png", "DOTA image"),
                (isaid / split / "instance_masks" / f"{img_id}_instance_id_RGB.png",
                 "iSAID instance mask")):
            if not path.exists():
                missing[kind].append(f"{split}/{img_id}")
    return missing


# ------------------------------------------------------------------- helpers

def read_rgb(path):
    bgr = cv2.imread(str(path), cv2.IMREAD_COLOR)
    return None if bgr is None else cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)


def pack_rgb(arr):
    """(H, W, 3) uint8 -> (H, W) int32 colour key.

    Selecting an instance then costs one scalar comparison instead of a
    three-channel equality test across the whole ~20 MP mask, which is what
    made dense images take minutes each.
    """
    return ((arr[:, :, 0].astype(np.int32) << 16)
            | (arr[:, :, 1].astype(np.int32) << 8)
            | arr[:, :, 2].astype(np.int32))


def pack_colour(rgb):
    return (int(rgb[0]) << 16) | (int(rgb[1]) << 8) | int(rgb[2])


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


# --------------------------------------------------------------------- build

def rebuild_image(img_id, split, records, dota, isaid, out, image_mode):
    """Reconstruct one image's annotations.

    Returns (pairs_written, resolved_records, problem or None).
    """
    label_src = dota / split / "labels" / f"{img_id}.txt"
    objects, gsd, imagesource = parse_dota_labels(label_src)
    if not objects:
        return 0, [], f"{img_id}: no DOTA labels at {label_src}"

    ins = read_rgb(isaid / split / "instance_masks" / f"{img_id}_instance_id_RGB.png")
    if ins is None:
        return 0, [], f"{img_id}: missing iSAID instance mask"

    h, w = ins.shape[:2]
    keys = pack_rgb(ins)                       # packed once per image, not per pair
    sem_out = np.zeros((h, w, 3), np.uint8)
    ins_out = np.zeros((h, w, 3), np.uint8)
    obb_rows, hbb_rows, resolved = [], [], []

    for rec in records:
        idx = rec["box_index"]
        if idx >= len(objects):
            return 0, [], (
                f"{img_id}: box_index {idx} out of range ({len(objects)} objects). "
                "Your DOTA labels differ from the ones used to build the "
                "correspondence — see SETUP.md.")
        corners, cls, diff = objects[idx]
        if cls != rec["class_name"]:
            return 0, [], (
                f"{img_id}: class mismatch at box {idx} "
                f"(your labels say '{cls}', correspondence says '{rec['class_name']}'). "
                "Your DOTA labels differ from the ones used to build the "
                "correspondence — see SETUP.md.")

        colour = np.array(rec["instance_rgb"], np.uint8)
        key = pack_colour(rec["instance_rgb"])

        # The clip cannot extend beyond the oriented box, so the polygon is
        # rasterised inside the box's bounding rectangle rather than into a
        # full-image buffer.
        pts = np.round(np.array(corners).reshape(4, 2)).astype(np.int32)
        x1, y1 = np.clip(pts.min(0) - 1, 0, [w - 1, h - 1])
        x2, y2 = np.clip(pts.max(0) + 2, 0, [w, h])
        sub_poly = np.zeros((int(y2 - y1), int(x2 - x1)), np.uint8)
        cv2.fillPoly(sub_poly, [pts - [x1, y1]], 1)
        sub_sel = (keys[y1:y2, x1:x2] == key) & (sub_poly > 0)

        if sub_sel.any():
            sem_out[y1:y2, x1:x2][sub_sel] = CLASS_COLOURS[cls]
            ins_out[y1:y2, x1:x2][sub_sel] = colour
            n_px = int(sub_sel.sum())
        else:
            # Empty clip: fall back to the whole instance, as during
            # construction. Rare, so the full-image scan is affordable here.
            instance = keys == key
            if not instance.any():
                return 0, [], f"{img_id}: iSAID instance {tuple(colour)} not found in mask"
            sem_out[instance] = CLASS_COLOURS[cls]
            ins_out[instance] = colour
            n_px = int(instance.sum())

        obb_rows.append((corners, cls, diff))
        hbb_rows.append((hull_corners(corners), cls, diff))
        resolved.append({
            "image_id": img_id, "split": split, "class_name": cls,
            "box_index": idx, "difficulty": diff,
            "obb": [round(v, 1) for v in corners],
            "hbb": [round(v, 1) for v in hull_corners(corners)],
            "instance_rgb": list(rec["instance_rgb"]),
            "iou": rec.get("iou"), "mask_px": n_px,
        })

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

    return len(records), resolved, (gsd, imagesource)


# ---------------------------------------------------------------------- main

def main():
    here = Path(__file__).resolve().parent
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dota", type=Path, help="DOTA v1.0 root")
    ap.add_argument("--isaid", type=Path, help="iSAID root")
    ap.add_argument("--out", type=Path, help="where to build AerialFuseCV")
    ap.add_argument("--correspondence", type=Path, default=here / "correspondence.jsonl")
    ap.add_argument("--image-mode", choices=("copy", "none"), default="copy",
                    help="copy = self-contained dataset (default); none = annotations only")
    ap.add_argument("--verify", action="store_true",
                    help="check the rebuilt annotations against published checksums")
    ap.add_argument("--yes", action="store_true", help="skip the confirmation prompt")
    args = ap.parse_args()

    print("=" * 66)
    print("AerialFuseCV".center(66))
    print("=" * 66)
    print("\nThis constructs the AerialFuseCV dataset from the original DOTA v1.0")
    print("and iSAID datasets, making exact pairing of detection bboxes and")
    print("segmentation masks.")
    print("Imagery and annotations come from your own copies of the two source")
    print("datasets.")

    if not args.correspondence.exists():
        sys.exit(f"\ncorrespondence file not found: {args.correspondence}")

    interactive = not (args.dota and args.isaid and args.out)
    if interactive:
        banner("Step 1 of 4 — where are the source datasets?")
        print("Paste the folder paths. See SETUP.md if you have not extracted")
        print("the downloads yet.\n")
        if not args.dota:
            args.dota = prompt_path("DOTA v1.0 root (contains train/ and val/)")
        if not args.isaid:
            args.isaid = prompt_path("iSAID root (contains train/ and val/)")
        if not args.out:
            args.out = prompt_path(
                "Where should AerialFuseCV be written? "
                "(an AerialFuseCV/ folder is created inside)",
                must_exist=False)
    # Always build into a folder of its own, so pointing this at a directory
    # holding other datasets does not scatter train/, val/ and the record files
    # across it. Giving a path that already ends in AerialFuseCV is honoured
    # as-is rather than nested twice.
    args.out = Path(args.out)
    if args.out.name != "AerialFuseCV":
        args.out = args.out / "AerialFuseCV"

    banner("Step 2 of 4 — checking the source layout")
    ok, lines = describe_sources(args.dota, args.isaid)
    for line in lines:
        print("  " + line)
    if not ok:
        print("\nThe layout above does not match what this script expects.")
        print("See SETUP.md for the required folder structure.")
        return 2

    print("\n  reading correspondence ...", end=" ", flush=True)
    by_image = defaultdict(list)
    for line in open(args.correspondence, encoding="utf-8"):
        r = json.loads(line)
        by_image[(r["split"], r["image_id"])].append(r)
    total_records = sum(len(v) for v in by_image.values())
    print(f"{total_records:,} pairs over {len(by_image):,} images")

    missing = cross_check(by_image, args.dota, args.isaid)
    if missing:
        print("\n  Some files the correspondence refers to are not present:")
        for kind, items in missing.items():
            print(f"    {kind}: {len(items):,} missing, e.g. {', '.join(items[:3])}")
        print("\n  Rebuild would be incomplete. Check SETUP.md, then re-run.")
        return 2
    print("  every referenced image, label and mask is present.")

    banner("Step 3 of 4 — ready to build")
    est_gb = 13.0 if args.image_mode == "copy" else 1.0
    print(f"  source DOTA   : {args.dota}")
    print(f"  source iSAID  : {args.isaid}")
    print(f"  output        : {args.out}")
    print(f"  image mode    : {args.image_mode} "
          f"({'images copied — self-contained' if args.image_mode == 'copy' else 'annotations only'})")
    print(f"  to write      : {len(by_image):,} images, {total_records:,} pairs, ~{est_gb:.0f} GB")
    if interactive and not args.yes:
        try:
            if input("\n  Proceed? [Y/n] > ").strip().lower() in ("n", "no"):
                return 1
        except EOFError:
            pass

    banner("Step 4 of 4 — building")
    args.out.mkdir(parents=True, exist_ok=True)
    bar = Progress(len(by_image), total_records)
    built = pairs = 0
    problems, all_pairs, gsd_map = [], [], {}
    t0 = time.time()

    img_id = None
    for (split, img_id), records in sorted(by_image.items()):
        got, resolved, result = rebuild_image(
            img_id, split, records, args.dota, args.isaid, args.out, args.image_mode)
        if isinstance(result, str):
            problems.append(result)
        else:
            built += 1
            pairs += got
            all_pairs.extend(resolved)
            gsd, _ = result
            gsd_map[img_id] = gsd
        bar.update(img_id, got)
    if img_id is not None:
        bar.update(img_id, 0, force=True)
    bar.close()
    elapsed = time.time() - t0

    print(f"\n  rebuilt {built:,} images, {pairs:,} pairs in {bar._clock(elapsed)}")
    resolve_rate = pairs / total_records if total_records else 0
    print(f"  box indices resolved to a class-matching box: "
          f"{pairs:,}/{total_records:,} ({resolve_rate*100:.2f}%)")

    if problems:
        print(f"\n  {len(problems)} image(s) could not be rebuilt:", file=sys.stderr)
        for p in problems[:20]:
            print("     " + p, file=sys.stderr)
        if len(problems) > 20:
            print(f"     ... and {len(problems) - 20} more", file=sys.stderr)

    # ---- auxiliary artefacts (documented in the data article) --------------
    banner("Writing dataset records")
    with open(args.out / "pairs.jsonl", "w", encoding="utf-8") as f:
        for r in all_pairs:
            f.write(json.dumps(r) + "\n")
    print(f"  pairs.jsonl              {len(all_pairs):,} records")

    (args.out / "images_gsd_mapping.json").write_text(
        json.dumps(gsd_map, indent=2), encoding="utf-8")
    print(f"  images_gsd_mapping.json  {len(gsd_map):,} images")

    for name in ("discarded.jsonl", "dataset_statistics.json"):
        src = here / name
        if src.exists():
            shutil.copy2(src, args.out / name)
            print(f"  {name:<24} copied from deposit")

    checks = here / "checksums.sha256"
    if checks.exists():
        shutil.copy2(checks, args.out / "checksums.sha256")
        print("  checksums.sha256         copied from deposit")

    manifest = {
        "dataset": "AerialFuseCV",
        "rebuilt_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "correspondence": str(args.correspondence),
        "correspondence_sha256": sha256(args.correspondence),
        "sources": {"dota": str(args.dota), "isaid": str(args.isaid)},
        "image_mode": args.image_mode,
        "images_rebuilt": built,
        "pairs_written": pairs,
        "pairs_expected": total_records,
        "resolve_rate": round(resolve_rate, 6),
        "problems": len(problems),
        "elapsed_seconds": round(elapsed, 1),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "numpy": np.__version__,
        "opencv": cv2.__version__,
    }
    (args.out / "build_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8")
    print("  build_manifest.json      run identity recorded")

    (args.out / "summary.md").write_text(
        f"""# AerialFuseCV — rebuild summary

Rebuilt {manifest['rebuilt_utc']} from the deposited correspondence.

| Field | Value |
|---|---|
| Images | {built:,} |
| Pairs | {pairs:,} of {total_records:,} expected |
| Box indices resolved | {resolve_rate*100:.2f}% |
| Images with problems | {len(problems):,} |
| Image mode | {args.image_mode} |
| Elapsed | {bar._clock(elapsed)} |
| DOTA source | `{args.dota}` |
| iSAID source | `{args.isaid}` |

Masks are the matched iSAID instance clipped to its DOTA oriented box.
Only paired objects appear. See the data article for the full description.
""", encoding="utf-8")
    print("  summary.md               build summary written")

    ok_build = not problems and pairs == total_records

    if args.verify:
        banner("Verifying against published checksums")
        if not checks.exists():
            print("  no checksums.sha256 in the deposit; skipping verification")
        else:
            expected = [ln.strip().split("  ", 1)
                        for ln in open(checks, encoding="utf-8") if ln.strip()]
            bad = miss = 0
            t1 = time.time()
            for n, (want, rel) in enumerate(expected, 1):
                got = args.out / rel
                if not got.exists():
                    miss += 1
                elif sha256(got) != want:
                    bad += 1
                    if bad <= 10:
                        print(f"    MISMATCH {rel}", file=sys.stderr)
                if n % 500 == 0:
                    print(f"    {n:,}/{len(expected):,} checked "
                          f"({time.time()-t1:.0f}s)", flush=True)
            verdict = "PASS" if (bad == 0 and miss == 0) else "FAIL"
            print(f"\n  {len(expected):,} files checked, {miss:,} missing, "
                  f"{bad:,} mismatched")
            print(f"  checksum verification: {verdict}")
            ok_build = ok_build and verdict == "PASS"

    print("\n" + "=" * 66)
    if ok_build:
        print(f"  Rebuild complete.  ->  {args.out}")
    else:
        print("  Rebuild finished WITH PROBLEMS — see the messages above.")
    print("=" * 66)
    return 0 if ok_build else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit("\n\ninterrupted — partial output left in place; re-run to resume")
