#!/usr/bin/env python3
"""Pin the DOTA source annotations the correspondence indexes into. INTERNAL TOOL.

`correspondence.jsonl` identifies a DOTA box by its ORDINAL POSITION within the
user's own annotation file. That is what keeps source coordinates out of the
deposit — but it also means the deposit is only meaningful against the exact
label files it was built from. A different DOTA copy with the same class at the
same index yields a silently wrong object: the class check passes, the rebuild
completes, the checksums of our own output still match each other, and nothing
reports a problem.

This publishes a SHA-256 per source label file, so that condition becomes
detectable instead of assumed. Hashes carry no annotation content, so nothing
about the sources is redistributed by including them.

    python papers/p1_aerialfusecv_descriptor/deposit/make_source_pin.py \
        --dota D:/AI_Datasets/DOTA_v1

Writes `source_pin.json` beside the correspondence. `rebuild_aerialfusecv.py`
verifies against it when present and reports any file that differs, by name.
"""

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

SPLITS = ("train", "val")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    here = Path(__file__).resolve().parent
    ap = argparse.ArgumentParser()
    ap.add_argument("--dota", type=Path, required=True)
    ap.add_argument("--correspondence", type=Path, default=here / "correspondence.jsonl")
    ap.add_argument("--out", type=Path, default=here / "source_pin.json")
    args = ap.parse_args()

    # only the files the correspondence actually indexes into
    needed = set()
    for line in open(args.correspondence, encoding="utf-8"):
        r = json.loads(line)
        needed.add((r["split"], r["image_id"]))
    print(f"correspondence references {len(needed):,} images")

    labels, missing = {}, []
    for split, img_id in sorted(needed):
        p = args.dota / split / "labels" / f"{img_id}.txt"
        if not p.exists():
            missing.append(f"{split}/{img_id}.txt")
            continue
        labels[f"{split}/{img_id}.txt"] = sha256(p)
    if missing:
        sys.exit(f"{len(missing)} label file(s) missing, e.g. {missing[:3]}")

    # a single digest over the whole set, so a user can check one value by hand
    joined = "\n".join(f"{k} {v}" for k, v in sorted(labels.items()))
    collective = hashlib.sha256(joined.encode()).hexdigest()

    out = {
        "purpose": "Pins the DOTA v1.0 label files that correspondence.jsonl "
                   "indexes into by ordinal box position. A different copy of "
                   "DOTA can resolve an index to a different object without "
                   "any error being raised; comparing these digests detects "
                   "that before a rebuild starts.",
        "note": "These are digests only. No annotation content is reproduced, "
                "so nothing of DOTA is redistributed here.",
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source": "DOTA v1.0 labelTxt-v1.0, train+val",
        "source_page": "https://captain-whu.github.io/DOTA/dataset.html",
        "files": len(labels),
        "collective_sha256": collective,
        "label_sha256": labels,
    }
    args.out.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"  pinned {len(labels):,} label files")
    print(f"  collective digest: {collective}")
    print(f"  -> {args.out}  ({args.out.stat().st_size/1024:.0f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
