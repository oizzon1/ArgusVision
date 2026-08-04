"""Quantify the tile-seam double-counting defect. INTERNAL MEASUREMENT.

`argusvision.runtime.tiling` documents an open limitation: an object crossing a
tile seam is detected twice, once per tile, as two partial boxes whose mutual
IoU is near zero. NMS therefore keeps both and the object is counted twice,
inflating false positives. Tiled IoU-0.5 micro precision sits at 0.7399 against
full-image 0.8525, and the split between "genuine new detections" and "seam
artefacts" has never been measured.

This measures it. For every final tiled detection it asks whether the box abuts
an INTERIOR tile boundary (image edges do not count — nothing is truncated
there), then evaluates against ground truth and reports TP/FP split by that
flag. If seam-adjacent detections are disproportionately false positives, the
excess is the defect's size.

    python experiments/tiling/measure_seam_defect.py --images 80
"""

import argparse
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from argusvision.data.aerialfusecv import AerialFuseCVSplit  # noqa: E402
from argusvision.evaluation.matching import hungarian_match, iou_matrix  # noqa: E402
from argusvision.models.registry import create_detector  # noqa: E402
from argusvision.runtime.tiling import TiledDetector, tile_origins  # noqa: E402


def interior_seams(width: int, height: int, tile_size: int, overlap: int):
    """x-positions and y-positions of interior tile boundaries.

    A tile at origin x0 spans [x0, x0+tile_size). Its two vertical edges are
    seams unless they coincide with the image border, where no truncation can
    occur. Same for horizontal.
    """
    origins = tile_origins(width, height, tile_size, overlap)
    xs, ys = set(), set()
    for x0, y0 in origins:
        for x in (x0, min(x0 + tile_size, width)):
            if 0 < x < width:
                xs.add(x)
        for y in (y0, min(y0 + tile_size, height)):
            if 0 < y < height:
                ys.add(y)
    return sorted(xs), sorted(ys)


def touches_seam(box_xyxy, seam_xs, seam_ys, tol: float) -> bool:
    """True if any edge of the box lies within `tol` px of an interior seam."""
    x1, y1, x2, y2 = box_xyxy
    for sx in seam_xs:
        if abs(x1 - sx) <= tol or abs(x2 - sx) <= tol:
            return True
    for sy in seam_ys:
        if abs(y1 - sy) <= tol or abs(y2 - sy) <= tol:
            return True
    return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", type=Path, default=Path("dataset/AerialFuseCV/val"))
    ap.add_argument("--images", type=int, default=80)
    ap.add_argument("--tile-size", type=int, default=1024)
    ap.add_argument("--overlap", type=int, default=200)
    ap.add_argument("--nms-iou", type=float, default=0.5)
    ap.add_argument("--conf", type=float, default=0.25)
    ap.add_argument("--match-iou", type=float, default=0.5)
    ap.add_argument("--tol", type=float, default=3.0, help="px tolerance for 'abuts a seam'")
    ap.add_argument("--out", type=Path,
                    default=Path("results/experimental/AerialFuseCV_Testing/seam_defect"))
    args = ap.parse_args()

    d = AerialFuseCVSplit(str(args.dataset))
    det = TiledDetector(
        create_detector("yolo11x-obb", conf_threshold=args.conf),
        tile_size=args.tile_size, overlap=args.overlap, nms_iou=args.nms_iou,
    )

    tp_seam = tp_clear = fp_seam = fp_clear = 0
    fn_total = 0
    per_class = defaultdict(lambda: {"fp_seam": 0, "fp_clear": 0, "tp_seam": 0, "tp_clear": 0})
    ids = d.image_ids[: args.images]
    t0 = time.time()

    for n, img_id in enumerate(ids, 1):
        image = d.load_image(img_id)
        h, w = image.shape[:2]
        gts = d.load_ground_truth(img_id)
        dets = det.predict(image)
        sx, sy = interior_seams(w, h, args.tile_size, args.overlap)
        flags = [touches_seam(x.box_xyxy, sx, sy, args.tol) for x in dets]

        for c in sorted({g.class_id for g in gts} | {x.class_id for x in dets}):
            di = [i for i, x in enumerate(dets) if x.class_id == c]
            gi = [i for i, g in enumerate(gts) if g.class_id == c]
            if not di and not gi:
                continue
            if di and gi:
                m = iou_matrix([dets[i] for i in di], [gts[i] for i in gi], mode="auto")
                res = hungarian_match(m, args.match_iou)
                matched = {r for r, _, _ in res.matches}
                fn_total += res.fn
            else:
                matched = set()
                fn_total += len(gi)
            for r, i in enumerate(di):
                seam = flags[i]
                key = ("tp" if r in matched else "fp") + ("_seam" if seam else "_clear")
                per_class[c][key] += 1
                if r in matched:
                    if seam: tp_seam += 1
                    else:    tp_clear += 1
                else:
                    if seam: fp_seam += 1
                    else:    fp_clear += 1

        if n % 20 == 0:
            print(f"  {n}/{len(ids)}  {time.time()-t0:.0f}s", flush=True)

    tp, fp = tp_seam + tp_clear, fp_seam + fp_clear
    seam_dets = tp_seam + fp_seam
    clear_dets = tp_clear + fp_clear
    fp_rate_seam = fp_seam / seam_dets if seam_dets else 0.0
    fp_rate_clear = fp_clear / clear_dets if clear_dets else 0.0
    # Excess false positives among seam-adjacent detections, over the rate seen
    # away from seams. This is the part attributable to seam truncation.
    excess = max(0.0, (fp_rate_seam - fp_rate_clear)) * seam_dets

    report = {
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "images": len(ids),
        "config": {"tile_size": args.tile_size, "overlap": args.overlap,
                   "nms_iou": args.nms_iou, "conf": args.conf,
                   "match_iou": args.match_iou, "seam_tolerance_px": args.tol},
        "counts": {"tp_seam": tp_seam, "tp_clear": tp_clear,
                   "fp_seam": fp_seam, "fp_clear": fp_clear, "fn": fn_total},
        "seam_adjacent_detections": seam_dets,
        "share_of_detections_seam_adjacent": seam_dets / (tp + fp) if (tp + fp) else 0.0,
        "fp_rate_seam_adjacent": fp_rate_seam,
        "fp_rate_away_from_seams": fp_rate_clear,
        "excess_fp_attributable_to_seams": excess,
        "excess_as_share_of_all_fp": excess / fp if fp else 0.0,
        "precision_measured": tp / (tp + fp) if (tp + fp) else 0.0,
        "precision_if_seam_excess_removed": tp / (tp + fp - excess) if (tp + fp - excess) > 0 else 0.0,
        "per_class": {int(k): v for k, v in per_class.items()},
    }
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "seam_defect_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("\n" + "=" * 72)
    print(f"images {len(ids)}   detections {tp+fp:,}   TP {tp:,}  FP {fp:,}  FN {fn_total:,}")
    print(f"seam-adjacent detections : {seam_dets:,} "
          f"({report['share_of_detections_seam_adjacent']*100:.1f}% of all)")
    print(f"FP rate, seam-adjacent   : {fp_rate_seam:.4f}")
    print(f"FP rate, away from seams : {fp_rate_clear:.4f}")
    print(f"excess FP due to seams   : {excess:.0f} "
          f"({report['excess_as_share_of_all_fp']*100:.1f}% of all FP)")
    print(f"precision measured       : {report['precision_measured']:.4f}")
    print(f"precision, excess removed: {report['precision_if_seam_excess_removed']:.4f}")
    print(f"report -> {args.out/'seam_defect_report.json'}")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main())
