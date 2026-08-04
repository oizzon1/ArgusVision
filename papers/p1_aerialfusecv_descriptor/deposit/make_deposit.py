"""Turn an internal AerialFuseCV build into the publishable deposit. INTERNAL TOOL.

Not shipped. This converts what we computed into what we are allowed to
distribute: the correspondence, expressed by *reference* rather than by value.

WHY REFERENCE, NOT VALUE
    DOTA and iSAID both state that images *and their annotations* are for
    academic use only. Our `pairs.jsonl` reproduces DOTA corner coordinates and
    iSAID instance identifiers, so it cannot go into a CC-BY deposit. Instead we
    publish, per pair: which image, which split, which category, the *ordinal
    index* of the box within its DOTA label file, the iSAID instance colour that
    identifies the mask, and our computed matching IoU. Nothing in that record is
    usable without the user's own copies of DOTA and iSAID; everything in it is
    ours.

    The instance colour is the one borderline field — it is an identifier drawn
    from iSAID's mask, not annotation content (no geometry, no boundary). We
    keep it because there is no other stable way to name an instance, and note
    it explicitly in the deposit README.

    python papers/p1_aerialfusecv_descriptor/deposit/make_deposit.py \
        --build dataset/AerialFuseCV --dota dataset/DOTA_v1
"""

import argparse
import hashlib
import json
import shutil
import sys
import time
from collections import defaultdict
from pathlib import Path

SPLITS = ("train", "val")
KNOWN = {"plane", "ship", "storage-tank", "baseball-diamond", "tennis-court",
         "basketball-court", "ground-track-field", "harbor", "bridge",
         "large-vehicle", "small-vehicle", "helicopter", "roundabout",
         "soccer-ball-field", "swimming-pool"}


def parse_source_objects(path):
    """Objects in file order — the same order rebuild_aerialfusecv.py indexes."""
    out = []
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        parts = line.split()
        if not parts or parts[0].startswith(("imagesource:", "gsd:")) or len(parts) < 10:
            continue
        try:
            corners = [float(v) for v in parts[:8]]
        except ValueError:
            continue
        if parts[8] not in KNOWN:
            continue
        out.append((corners, parts[8]))
    return out


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    here = Path(__file__).resolve().parent
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", type=Path, default=Path("dataset/AerialFuseCV"))
    ap.add_argument("--dota", type=Path, default=Path("dataset/DOTA_v1"))
    ap.add_argument("--out", type=Path, default=None, help="default: this deposit folder")
    args = ap.parse_args()
    out = args.out or here

    pairs_path = args.build / "pairs.jsonl"
    if not pairs_path.exists():
        sys.exit(f"no pairs.jsonl in {args.build}")

    by_image = defaultdict(list)
    for line in open(pairs_path, encoding="utf-8"):
        r = json.loads(line)
        by_image[(r["split"], r["image_id"])].append(r)

    records, unresolved = [], []
    for (split, img_id), recs in sorted(by_image.items()):
        objects = parse_source_objects(args.dota / split / "labels" / f"{img_id}.txt")
        # map each pair back to the ordinal index of its box in the source file
        used = set()
        for rec in recs:
            want = [round(v, 1) for v in rec["obb"]]
            hit = None
            for i, (corners, cls) in enumerate(objects):
                if i in used or cls != rec["class_name"]:
                    continue
                if all(abs(a - b) <= 0.05 for a, b in zip(want, [round(c, 1) for c in corners])):
                    hit = i
                    break
            if hit is None:
                unresolved.append(f"{split}/{img_id} {rec['class_name']}")
                continue
            used.add(hit)
            records.append({
                "image_id": img_id,
                "split": split,
                "class_name": rec["class_name"],
                "box_index": hit,
                "instance_rgb": rec["instance_rgb"],
                "iou": rec["iou"],
            })

    if unresolved:
        print(f"WARNING: {len(unresolved)} pair(s) could not be indexed back to source:",
              file=sys.stderr)
        for u in unresolved[:10]:
            print("   " + u, file=sys.stderr)

    corr = out / "correspondence.jsonl"
    with open(corr, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")

    # carry over the statistics and discard accounting — both are ours
    for name in ("dataset_statistics.json", "discarded.jsonl"):
        src = args.build / name
        if src.exists():
            shutil.copy2(src, out / name)

    manifest = {
        "dataset": "AerialFuseCV",
        "version": "1.0",
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "pairs": len(records),
        "images": len({(r["split"], r["image_id"]) for r in records}),
        "unresolved": len(unresolved),
        "source_datasets": {
            "DOTA": "v1.0, train+val, https://captain-whu.github.io/DOTA/",
            "iSAID": "train+val masks, https://captain-whu.github.io/iSAID/",
        },
        "contents": "correspondence by reference (no source coordinates or masks)",
    }
    (out / "deposit_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    with open(out / "checksums.sha256", "w", encoding="utf-8") as f:
        for split in SPLITS:
            for sub in ("labels_obb", "labels_hbb", "semantic_masks", "instance_masks"):
                d = args.build / split / sub
                if not d.exists():
                    continue
                for p in sorted(d.iterdir()):
                    if p.is_file():
                        f.write(f"{sha256(p)}  {split}/{sub}/{p.name}\n")

    print(f"correspondence : {len(records):,} pairs -> {corr}")
    print(f"unresolved     : {len(unresolved)}")
    print(f"checksums      : {out/'checksums.sha256'}")
    print(f"manifest       : {out/'deposit_manifest.json'}")
    return 1 if unresolved else 0


if __name__ == "__main__":
    sys.exit(main())
