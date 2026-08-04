"""Choose the tiled-detection operating point from evidence. INTERNAL.

F6b recommended tiled inference as P2's detector protocol but flagged that the
confidence/NMS operating point must be tuned before any paper number. The
seam measurement then showed that seam truncation explains only ~15% of the
tiled precision drop (1.75 of 11.3 points); the rest is genuine marginal
detections. That makes the confidence threshold the lever that matters.

Detection is run ONCE at a permissive threshold and every detection is cached
with its score. Thresholds are then applied post hoc by filtering the cache, so
a grid of N operating points costs one GPU pass rather than N. Re-running the
detector per threshold would produce identical detections — the score of a
detection does not depend on the threshold that admitted it.

Two independent switches are swept together:
  * confidence   — the operating point proper
  * drop_seam    — whether detections abutting an interior tile boundary are
                   discarded (the seam fix, worth ~1.75 precision points)

    python experiments/tiling/sweep_operating_point.py --images 456
"""

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from argusvision.data.aerialfusecv import AerialFuseCVSplit  # noqa: E402
from argusvision.evaluation.evaluator import DetectionEvaluator  # noqa: E402
from argusvision.models.base import Detection  # noqa: E402
from argusvision.models.registry import create_detector  # noqa: E402
from argusvision.runtime.tiling import TiledDetector  # noqa: E402

from measure_seam_defect import interior_seams, touches_seam  # noqa: E402


def collect(dataset: Path, images: int, tile: int, overlap: int, nms: float,
            floor: float, cache: Path) -> None:
    """One GPU pass at a permissive threshold; cache every detection."""
    d = AerialFuseCVSplit(str(dataset))
    det = TiledDetector(create_detector("yolo11x-obb", conf_threshold=floor),
                        tile_size=tile, overlap=overlap, nms_iou=nms)
    ids = d.image_ids[:images]
    t0 = time.time()
    with open(cache, "w", encoding="utf-8") as f:
        for n, img_id in enumerate(ids, 1):
            image = d.load_image(img_id)
            h, w = image.shape[:2]
            dets = det.predict(image)
            sx, sy = interior_seams(w, h, tile, overlap)
            f.write(json.dumps({
                "image_id": img_id,
                "detections": [{
                    "class_id": x.class_id,
                    "score": round(float(x.score), 6),
                    "box": [round(float(v), 2) for v in x.box_xyxy],
                    "obb": ([round(float(v), 2) for v in x.obb_xyxyxyxy]
                            if x.obb_xyxyxyxy is not None else None),
                    "seam": bool(touches_seam(x.box_xyxy, sx, sy, 3.0)),
                } for x in dets],
            }) + "\n")
            if n % 50 == 0:
                print(f"  collect {n}/{len(ids)}  {time.time()-t0:.0f}s", flush=True)


def evaluate(cache: Path, dataset: Path, conf: float, drop_seam: bool,
             thresholds) -> dict:
    """Post-hoc evaluation of the cached detections at one operating point."""
    d = AerialFuseCVSplit(str(dataset))
    ev = DetectionEvaluator(iou_thresholds=thresholds, iou_mode="auto")
    kept = 0
    for line in open(cache, encoding="utf-8"):
        rec = json.loads(line)
        dets = []
        for x in rec["detections"]:
            if x["score"] < conf:
                continue
            if drop_seam and x["seam"]:
                continue
            dets.append(Detection(
                class_id=x["class_id"], score=x["score"],
                box_xyxy=np.array(x["box"], dtype=np.float64),
                obb_xyxyxyxy=(np.array(x["obb"], dtype=np.float64)
                              if x["obb"] is not None else None)))
        kept += len(dets)
        ev.add_image(dets, d.load_ground_truth(rec["image_id"]))
    s = ev.summarize()
    return {"conf": conf, "drop_seam": drop_seam, "detections": kept,
            "per_threshold": s["per_threshold"]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", type=Path, default=Path("dataset/AerialFuseCV/val"))
    ap.add_argument("--images", type=int, default=456)
    ap.add_argument("--tile-size", type=int, default=1024)
    ap.add_argument("--overlap", type=int, default=200)
    ap.add_argument("--nms-iou", type=float, default=0.5)
    ap.add_argument("--floor", type=float, default=0.05,
                    help="permissive threshold for the single detection pass")
    ap.add_argument("--grid", type=float, nargs="+",
                    default=[0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50])
    ap.add_argument("--out", type=Path,
                    default=Path("results/experimental/AerialFuseCV_Testing/operating_point"))
    ap.add_argument("--reuse-cache", action="store_true")
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    cache = args.out / "detections_cache.jsonl"
    if not (args.reuse_cache and cache.exists()):
        print(f"collecting detections at conf>={args.floor} (one GPU pass)", flush=True)
        collect(args.dataset, args.images, args.tile_size, args.overlap,
                args.nms_iou, args.floor, cache)
    else:
        print(f"reusing cache {cache}", flush=True)

    thresholds = (0.1, 0.3, 0.5)
    rows = []
    for drop_seam in (False, True):
        for conf in args.grid:
            if conf < args.floor:
                continue
            r = evaluate(cache, args.dataset, conf, drop_seam, thresholds)
            rows.append(r)
            m = r["per_threshold"][0.5]
            print(f"  conf {conf:.2f}  seam_drop={int(drop_seam)}  "
                  f"det {r['detections']:6,}  P {m['micro_precision']:.4f}  "
                  f"R {m['micro_recall']:.4f}  F1 {m['micro_f1']:.4f}  "
                  f"mAP {m['mean_ap']:.4f}", flush=True)

    best = max(rows, key=lambda r: r["per_threshold"][0.5]["micro_f1"])
    report = {
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "config": {"tile_size": args.tile_size, "overlap": args.overlap,
                   "nms_iou": args.nms_iou, "detection_floor": args.floor,
                   "images": args.images},
        "rows": rows,
        "best_by_micro_f1_at_0.5": {"conf": best["conf"],
                                    "drop_seam": best["drop_seam"]},
    }
    (args.out / "operating_point_report.json").write_text(
        json.dumps(report, indent=2, default=float), encoding="utf-8")

    b = best["per_threshold"][0.5]
    print("\n" + "=" * 72)
    print(f"best by micro-F1 @ IoU 0.5: conf {best['conf']:.2f}, "
          f"seam_drop={best['drop_seam']}")
    print(f"  P {b['micro_precision']:.4f}  R {b['micro_recall']:.4f}  "
          f"F1 {b['micro_f1']:.4f}  macroF1 {b['macro_f1']:.4f}  mAP {b['mean_ap']:.4f}")
    print(f"report -> {args.out/'operating_point_report.json'}")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main())
