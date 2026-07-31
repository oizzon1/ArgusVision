"""Measure the DOTA/iSAID annotation discrepancy. INTERNAL TOOL.

For every paired object it compares two candidate ground-truth masks:

  clipped  = class-coloured semantic mask  ∩  oriented box polygon
  exact    = the iSAID instance mask of the matched instance

and decomposes their disagreement into causes that need different responses:

  missing        exact-only pixels — iSAID annotates a LARGER extent than the
                 box delimits (convention difference, or an iSAID error)
  extra_foreign  clip-only pixels belonging to a DIFFERENT iSAID instance —
                 genuine contamination of the clip by a neighbour
  extra_unlabelled clip-only pixels with no instance identity — class-mask
                 pixels iSAID left outside every instance

Also counts instances whose colour spans multiple disconnected components,
which is the one failure mode belonging to our own extraction.

    python dataset/measure_discrepancy.py --dataset dataset/AerialFuseCV_v1
"""

import argparse
import collections
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import cv2
import numpy as np
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from argusvision.data.aerialfusecv import (  # noqa: E402
    AerialFuseCVSplit,
    extract_gt_instance_mask,
)

cv2.setNumThreads(1)


def pack(rgb):
    a = rgb.astype(np.int32)
    return (a[:, :, 0] << 16) | (a[:, :, 1] << 8) | a[:, :, 2]


def process(task):
    root, split, img_id, recs = Path(task["root"]), task["split"], task["img_id"], task["recs"]
    d = AerialFuseCVSplit(root / split)
    try:
        gts = d.load_ground_truth(img_id)
        sem = d.load_semantic_mask(img_id)
        ins_rgb = cv2.cvtColor(
            cv2.imread(str(root / split / "instance_masks" / f"{img_id}_instance_id_RGB.png")),
            cv2.COLOR_BGR2RGB)
    except Exception as exc:                       # noqa: BLE001
        return {"img_id": img_id, "error": str(exc), "rows": [], "multi": []}
    if len(gts) != len(recs):
        return {"img_id": img_id, "error": "label/pair count mismatch", "rows": [], "multi": []}

    ik = pack(ins_rgb)
    rows, multi = [], []
    seen_colours = set()

    for gt, rec in zip(gts, recs):
        key = (rec["instance_rgb"][0] << 16) | (rec["instance_rgb"][1] << 8) | rec["instance_rgb"][2]
        exact = ik == key
        clip = extract_gt_instance_mask(sem, gt)
        inter = int(np.count_nonzero(exact & clip))
        union = int(np.count_nonzero(exact | clip))
        if union == 0:
            continue

        extra = clip & ~exact
        missing = exact & ~clip
        # of the clip-only pixels, which carry a DIFFERENT instance identity?
        extra_ids = ik[extra]
        foreign = int(np.count_nonzero((extra_ids != 0) & (extra_ids != key)))
        unlabelled = int(np.count_nonzero(extra_ids == 0))

        if key not in seen_colours:
            seen_colours.add(key)
            _, n_comp = ndimage.label(exact)
            if n_comp > 1:
                multi.append({"image_id": img_id, "split": split,
                              "class_name": rec["class_name"], "pieces": int(n_comp),
                              "pixels": int(exact.sum())})

        rows.append({
            "image_id": img_id, "split": split, "class_name": rec["class_name"],
            "agreement_iou": round(inter / union, 6),
            "exact_px": int(exact.sum()), "clip_px": int(clip.sum()),
            "missing_px": int(missing.sum()),
            "extra_foreign_px": foreign, "extra_unlabelled_px": unlabelled,
        })
    return {"img_id": img_id, "error": None, "rows": rows, "multi": multi}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", type=Path, default=Path("dataset/AerialFuseCV_v1"))
    ap.add_argument("--splits", nargs="+", default=["train", "val"])
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    ap.add_argument("--out", type=Path,
                    default=Path("results/AerialFuseCV_Testing/annotation_discrepancy"))
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    by_image = collections.defaultdict(list)
    for line in open(args.dataset / "pairs.jsonl", encoding="utf-8"):
        r = json.loads(line)
        by_image[(r["split"], r["image_id"])].append(r)

    tasks = []
    for split in args.splits:
        ids = sorted({k[1] for k in by_image if k[0] == split})
        if args.limit:
            ids = ids[: args.limit]
        tasks += [{"root": str(args.dataset), "split": split, "img_id": i,
                   "recs": by_image[(split, i)]} for i in ids]

    print(f"measuring {len(tasks)} images with {args.workers} workers", flush=True)
    t0 = time.time()
    rows, multi, errors = [], [], []
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        for n, r in enumerate(pool.map(process, tasks, chunksize=4), 1):
            if r["error"]:
                errors.append({"image_id": r["img_id"], "error": r["error"]})
            rows += r["rows"]; multi += r["multi"]
            if n % 200 == 0:
                print(f"  {n}/{len(tasks)}  {time.time()-t0:.0f}s", flush=True)

    with open(args.out / "per_pair.jsonl", "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")

    a = np.array([r["agreement_iou"] for r in rows])
    miss = np.array([r["missing_px"] for r in rows], dtype=np.int64)
    fore = np.array([r["extra_foreign_px"] for r in rows], dtype=np.int64)
    unlab = np.array([r["extra_unlabelled_px"] for r in rows], dtype=np.int64)
    exact_px = np.array([r["exact_px"] for r in rows], dtype=np.int64)

    per_class = {}
    for cls in sorted({r["class_name"] for r in rows}):
        idx = [i for i, r in enumerate(rows) if r["class_name"] == cls]
        ca, cm, cf, cu = a[idx], miss[idx], fore[idx], unlab[idx]
        per_class[cls] = {
            "n": len(idx),
            "mean_agreement": float(ca.mean()),
            "median_agreement": float(np.median(ca)),
            "pct_identical_gt_099": float((ca > 0.99).mean() * 100),
            "pct_with_foreign_pixels": float((cf > 0).mean() * 100),
            "mean_missing_px": float(cm.mean()),
            "mean_foreign_px": float(cf.mean()),
            "mean_unlabelled_px": float(cu.mean()),
            "disagreement_share_missing": float(cm.sum() / max(1, cm.sum() + cf.sum() + cu.sum())),
            "disagreement_share_foreign": float(cf.sum() / max(1, cm.sum() + cf.sum() + cu.sum())),
        }

    summary = {
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "dataset": str(args.dataset),
        "pairs_measured": len(rows),
        "elapsed_s": round(time.time() - t0, 1),
        "agreement": {
            "mean": float(a.mean()), "median": float(np.median(a)),
            "p05": float(np.percentile(a, 5)),
            "pct_identical_gt_099": float((a > 0.99).mean() * 100),
            "pct_below_090": float((a < 0.90).mean() * 100),
            "pct_below_070": float((a < 0.70).mean() * 100),
        },
        "disagreement_decomposition_px": {
            "missing_extent": int(miss.sum()),
            "extra_foreign_instance": int(fore.sum()),
            "extra_unlabelled": int(unlab.sum()),
            "share_missing": float(miss.sum() / max(1, miss.sum() + fore.sum() + unlab.sum())),
            "share_foreign": float(fore.sum() / max(1, miss.sum() + fore.sum() + unlab.sum())),
            "share_unlabelled": float(unlab.sum() / max(1, miss.sum() + fore.sum() + unlab.sum())),
        },
        "contamination_incidence": {
            "pairs_with_any_foreign_pixel": int((fore > 0).sum()),
            "pct_pairs_with_foreign": float((fore > 0).mean() * 100),
            "mean_foreign_fraction_of_instance": float((fore / np.maximum(1, exact_px)).mean()),
        },
        "multi_piece_instances": {
            "count": len(multi),
            "pct_of_pairs": float(len(multi) / max(1, len(rows)) * 100),
            "worst": sorted(multi, key=lambda m: -m["pieces"])[:20],
        },
        "per_class": per_class,
        "errors": errors,
    }
    (args.out / "discrepancy_summary.json").write_text(json.dumps(summary, indent=2),
                                                       encoding="utf-8")

    s = summary
    print("\n" + "=" * 74)
    print(f"pairs measured            : {s['pairs_measured']:,}")
    print(f"agreement mean/median     : {s['agreement']['mean']:.3f} / {s['agreement']['median']:.3f}")
    print(f"identical (>0.99)         : {s['agreement']['pct_identical_gt_099']:.1f}%")
    d = s["disagreement_decomposition_px"]
    print(f"disagreement is EXTENT    : {d['share_missing']*100:.1f}%  ({d['missing_extent']:,} px)")
    print(f"disagreement is FOREIGN   : {d['share_foreign']*100:.1f}%  ({d['extra_foreign_instance']:,} px)")
    print(f"disagreement is UNLABELLED: {d['share_unlabelled']*100:.1f}%  ({d['extra_unlabelled']:,} px)")
    c = s["contamination_incidence"]
    print(f"pairs with ANY foreign px : {c['pairs_with_any_foreign_pixel']:,} ({c['pct_pairs_with_foreign']:.1f}%)")
    m = s["multi_piece_instances"]
    print(f"multi-piece instances     : {m['count']:,} ({m['pct_of_pairs']:.2f}% of pairs)")
    print(f"elapsed                   : {s['elapsed_s']:.0f}s")
    print(f"report -> {args.out}")
    print("=" * 74)
    return 0


if __name__ == "__main__":
    sys.exit(main())
