"""Exhaustive audit of iSAID mask encodings across every image.

Answers, without sampling or assumption:

1. Which RGB values actually occur in the semantic (class-coloured) masks?
   -> verifies the `argusvision.data.constants` table against the data and
      exposes any colour present in the data but absent from the table.
2. How many distinct instances does each instance-id mask contain?
   -> the authoritative instance count, independent of connected components.
3. Does every instance-id region map to exactly ONE semantic class?
   -> the correctness precondition for building (class, instance) pairs by
      intersecting the two mask types. Any violation is reported per image.

Run from repo root, in AV_env:
    python dataset/scan_isaid_colours.py
    python dataset/scan_isaid_colours.py --limit 20   # smoke
"""

import argparse
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from argusvision.data.constants import ISAID_COLOR_TO_CLASS_ID, CLASS_ID_TO_NAME

ISAID_ROOT = Path("dataset/iSAID")
OUT_PATH = Path("results/experimental/AerialFuseCV_Testing/isaid_colour_audit/colour_audit.json")


def pack(rgb: np.ndarray) -> np.ndarray:
    """(H,W,3) uint8 -> (H,W) int32 key 0xRRGGBB."""
    a = rgb.astype(np.int32)
    return (a[:, :, 0] << 16) | (a[:, :, 1] << 8) | a[:, :, 2]


def unpack(key: int):
    return ((key >> 16) & 0xFF, (key >> 8) & 0xFF, key & 0xFF)


def read_rgb(path: Path):
    bgr = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if bgr is None:
        return None
    return cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None, help="first N images per split")
    ap.add_argument("--out", type=Path, default=None, help="override report path")
    args = ap.parse_args()

    # A limited run is a smoke test and must never overwrite the full audit.
    out_path = args.out or (
        OUT_PATH.with_name(f"colour_audit_limit{args.limit}.json") if args.limit else OUT_PATH
    )

    known = {(r << 16) | (g << 8) | b: cid for (r, g, b), cid in ISAID_COLOR_TO_CLASS_ID.items()}

    sem_pixels = defaultdict(int)      # semantic colour key -> pixel count
    sem_images = defaultdict(int)      # semantic colour key -> image count
    per_image = {}                     # image id -> stats
    violations = []                    # instance spanning >1 class
    dim_mismatch = []
    unreadable = []
    t0 = time.time()

    for split in ("train", "val"):
        sem_dir = ISAID_ROOT / split / "semantic_masks"
        ins_dir = ISAID_ROOT / split / "instance_masks"
        ids = sorted(p.name.replace("_instance_color_RGB.png", "") for p in sem_dir.glob("*.png"))
        if args.limit:
            ids = ids[: args.limit]

        for n, img_id in enumerate(ids, 1):
            sem = read_rgb(sem_dir / f"{img_id}_instance_color_RGB.png")
            ins = read_rgb(ins_dir / f"{img_id}_instance_id_RGB.png")
            if sem is None or ins is None:
                unreadable.append(img_id)
                continue
            if sem.shape != ins.shape:
                dim_mismatch.append({"image": img_id, "sem": list(sem.shape), "ins": list(ins.shape)})
                continue

            sk = pack(sem)
            ik = pack(ins)

            keys, counts = np.unique(sk, return_counts=True)
            for k, c in zip(keys.tolist(), counts.tolist()):
                sem_pixels[k] += c
                sem_images[k] += 1

            # every (instance, semantic) co-occurrence in ONE pass
            fg = ik != 0
            n_inst = 0
            multi = 0
            if fg.any():
                combo = (ik[fg].astype(np.int64) << 32) | sk[fg].astype(np.int64)
                uniq = np.unique(combo)
                inst_of = (uniq >> 32).astype(np.int64)
                sem_of = (uniq & 0xFFFFFFFF).astype(np.int64)
                inst_ids, first_idx, cls_counts = np.unique(
                    inst_of, return_index=True, return_counts=True
                )
                n_inst = int(inst_ids.size)
                for iid, cnt, fi in zip(inst_ids.tolist(), cls_counts.tolist(), first_idx.tolist()):
                    if cnt > 1:
                        multi += 1
                        if len(violations) < 200:
                            sems = sem_of[inst_of == iid].tolist()
                            violations.append({
                                "image": img_id,
                                "instance_rgb": unpack(iid),
                                "semantic_rgbs": [unpack(s) for s in sems],
                            })

            per_image[img_id] = {
                "split": split,
                "height": int(sem.shape[0]),
                "width": int(sem.shape[1]),
                "instances": n_inst,
                "instances_spanning_multiple_classes": multi,
            }

            if n % 100 == 0:
                el = time.time() - t0
                print(f"[{split}] {n}/{len(ids)}  {el:.0f}s elapsed", flush=True)

    # ---- report ----
    unknown = {k: v for k, v in sem_pixels.items() if k not in known and k != 0}
    missing = [k for k in known if k not in sem_pixels]

    total_instances = sum(v["instances"] for v in per_image.values())
    by_split = defaultdict(int)
    for v in per_image.values():
        by_split[v["split"]] += v["instances"]

    report = {
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "images_scanned": len(per_image),
        "elapsed_s": round(time.time() - t0, 1),
        "semantic_colours_found": [
            {
                "rgb": unpack(k),
                "class_id": known.get(k),
                "class_name": CLASS_ID_TO_NAME.get(known.get(k), "UNKNOWN" if k else "background"),
                "pixels": v,
                "images": sem_images[k],
            }
            for k, v in sorted(sem_pixels.items(), key=lambda kv: -kv[1])
        ],
        "unknown_semantic_colours": [
            {"rgb": unpack(k), "pixels": v, "images": sem_images[k]}
            for k, v in sorted(unknown.items(), key=lambda kv: -kv[1])
        ],
        "table_colours_never_observed": [
            {"rgb": unpack(k), "class_name": CLASS_ID_TO_NAME[known[k]]} for k in missing
        ],
        "instance_totals": {"all": total_instances, **dict(by_split)},
        "instances_spanning_multiple_classes": sum(
            v["instances_spanning_multiple_classes"] for v in per_image.values()
        ),
        "violation_examples": violations,
        "dimension_mismatches": dim_mismatch,
        "unreadable": unreadable,
        "per_image": per_image,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print("\n" + "=" * 72)
    print(f"images scanned              : {report['images_scanned']}")
    print(f"distinct semantic colours   : {len(sem_pixels)} (incl. background)")
    print(f"UNKNOWN semantic colours    : {len(unknown)}")
    print(f"table colours never observed: {len(missing)}")
    print(f"total instances (instance-id): {total_instances:,}")
    for s, c in by_split.items():
        print(f"   {s}: {c:,}")
    print(f"instances spanning >1 class : {report['instances_spanning_multiple_classes']}")
    print(f"dimension mismatches        : {len(dim_mismatch)}   unreadable: {len(unreadable)}")
    print(f"report -> {out_path}")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main())
