"""Build AerialFuseCV from the official DOTA v1.0 and iSAID distributions.

INTERNAL BUILD-AND-VERIFY TOOL. The script that ships with the dataset is
written separately, to the descriptor's scope alone. See
`TODO_RECREATION_SCRIPT.md` and `documentation/DECISION_unpaired_annotations.md`.

Run from the repo root, in AV_env:

    python dataset/build_aerialfusecv.py --dota dataset/DOTA_v1 \
        --isaid dataset/iSAID --out dataset/AerialFuseCV

Matching modes:

  instance (default) — iSAID's per-instance masks give exact instance identity;
        class comes from the semantic mask at the same pixels. A box is scored
        against an instance by IoU between the **rasterised oriented
        quadrilateral** and the instance mask, and assignment is one-to-one
        within a class.

  semantic — regression only, replicating the earlier construction
        (class-coloured mask, padded crop, connected components, greedy
        best-per-box against the axis-aligned hull). Retained so a build can be
        compared object-for-object with the existing dataset.

Output annotations stay in DOTA's own format — headers, absolute pixel
coordinates, class names, difficulty flag — because framework conversions are
lossy and no single framework format serves every consumer.
"""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from argusvision.data.constants import (  # noqa: E402
    CLASS_ID_TO_ISAID_COLOR,
    CLASS_ID_TO_NAME,
    CLASS_NAME_TO_ID,
    ISAID_COLOR_TO_CLASS_ID,
    NUM_DOTA_CLASSES,
)
from argusvision.evaluation.matching import hungarian_match  # noqa: E402

SPLITS = ("train", "val")
cv2.setNumThreads(1)          # we parallelise across images, not within them


# --------------------------------------------------------------------------- #
# data types
# --------------------------------------------------------------------------- #

@dataclass
class Box:
    class_id: int
    corners: np.ndarray               # (8,) x1 y1 ... x4 y4, DOTA order
    difficulty: str
    hull: Tuple[int, int, int, int] = field(init=False)

    def __post_init__(self):
        c = self.corners.reshape(4, 2)
        self.hull = (int(np.floor(c[:, 0].min())), int(np.floor(c[:, 1].min())),
                     int(np.ceil(c[:, 0].max())), int(np.ceil(c[:, 1].max())))


@dataclass
class Instance:
    label: int
    class_id: int
    colour: Tuple[int, int, int]
    area: int
    bbox: Tuple[int, int, int, int]


# --------------------------------------------------------------------------- #
# io
# --------------------------------------------------------------------------- #

def pack(rgb: np.ndarray) -> np.ndarray:
    a = rgb.astype(np.int32)
    return (a[:, :, 0] << 16) | (a[:, :, 1] << 8) | a[:, :, 2]


def unpack(key: int) -> Tuple[int, int, int]:
    return ((key >> 16) & 0xFF, (key >> 8) & 0xFF, key & 0xFF)


def read_rgb(path: Path) -> Optional[np.ndarray]:
    bgr = cv2.imread(str(path), cv2.IMREAD_COLOR)
    return None if bgr is None else cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)


def load_dota_label(path: Path):
    """Parse a DOTA annotation file -> (boxes, gsd, imagesource)."""
    boxes: List[Box] = []
    gsd: Optional[float] = None
    imagesource: Optional[str] = None
    if not path.exists():
        return boxes, gsd, imagesource
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
            corners = np.array([float(v) for v in parts[:8]], dtype=np.float64)
        except ValueError:
            continue
        class_id = CLASS_NAME_TO_ID.get(parts[8])
        if class_id is None:
            continue
        boxes.append(Box(class_id=class_id, corners=corners, difficulty=parts[9]))
    return boxes, gsd, imagesource


def write_dota_label(path: Path, rows, gsd, imagesource) -> None:
    """DOTA-native: original headers, absolute coordinates, class name, difficulty."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        if imagesource:
            f.write(f"imagesource:{imagesource}\n")
        if gsd is not None:
            f.write(f"gsd:{gsd}\n")
        for coords, class_id, difficulty in rows:
            c = " ".join(f"{v:.1f}" for v in coords)
            f.write(f"{c} {CLASS_ID_TO_NAME[class_id]} {difficulty}\n")


def hull_corners(box: Box) -> List[float]:
    """Axis-aligned hull expressed as a clockwise quadrilateral, so HBB files
    parse with exactly the same reader as OBB files."""
    x1, y1, x2, y2 = box.hull
    return [x1, y1, x2, y1, x2, y2, x1, y2]


# --------------------------------------------------------------------------- #
# instance indexing and matching
# --------------------------------------------------------------------------- #

def build_instance_index(sem_rgb: np.ndarray, ins_rgb: np.ndarray):
    ik, sk = pack(ins_rgb), pack(sem_rgb)
    uniq, inverse = np.unique(ik.reshape(-1), return_inverse=True)
    labels = inverse.reshape(ik.shape).astype(np.int32)
    objects = ndimage.find_objects(labels)
    areas = np.bincount(inverse, minlength=uniq.size)

    instances: List[Instance] = []
    ambiguous = 0
    for idx, key in enumerate(uniq.tolist()):
        if key == 0:
            continue
        sl = objects[idx - 1] if idx - 1 < len(objects) else None
        if sl is None:
            continue
        ys, xs = sl
        sub = labels[ys, xs] == idx
        sem_vals = np.unique(sk[ys, xs][sub])
        sem_vals = sem_vals[sem_vals != 0]
        if sem_vals.size != 1:
            ambiguous += 1
            continue
        class_id = ISAID_COLOR_TO_CLASS_ID.get(unpack(int(sem_vals[0])))
        if class_id is None:
            ambiguous += 1
            continue
        instances.append(Instance(label=idx, class_id=class_id, colour=unpack(key),
                                  area=int(areas[idx]),
                                  bbox=(xs.start, ys.start, xs.stop, ys.stop)))
    return labels, instances, ambiguous


def polygon_instance_iou(labels: np.ndarray, inst: Instance, box: Box, shape) -> float:
    """IoU between the rasterised ORIENTED quadrilateral and an instance mask.

    The axis-aligned hull is a median 1.83x the true box area on this data, so
    scoring against it both depresses IoU and blurs the distinction between
    neighbouring objects. The polygon is the annotation; score against it.
    """
    h, w = shape
    bx1, by1, bx2, by2 = box.hull
    ix1, iy1, ix2, iy2 = inst.bbox
    x1, y1 = max(0, min(bx1, ix1)), max(0, min(by1, iy1))
    x2, y2 = min(w, max(bx2, ix2)), min(h, max(by2, iy2))
    if x2 <= x1 or y2 <= y1:
        return 0.0

    pts = box.corners.reshape(4, 2) - np.array([x1, y1], dtype=np.float64)
    poly = np.zeros((y2 - y1, x2 - x1), dtype=np.uint8)
    cv2.fillPoly(poly, [np.round(pts).astype(np.int32)], 1)
    poly_area = int(np.count_nonzero(poly))
    if poly_area == 0:
        return 0.0

    inst_sel = labels[y1:y2, x1:x2] == inst.label
    inter = int(np.count_nonzero(poly.astype(bool) & inst_sel))
    if inter == 0:
        return 0.0
    union = poly_area + inst.area - inter
    return inter / union if union > 0 else 0.0


def match_instance_mode(boxes, labels, instances, shape, iou_threshold):
    """One-to-one box<->instance assignment per class, scored on the polygon.

    Returns (pairs, discarded). Only pairs enter the dataset; every discard is
    reported with the reason it failed.
    """
    pairs, discarded = [], []
    by_class: Dict[int, List[int]] = {}
    for i, inst in enumerate(instances):
        by_class.setdefault(inst.class_id, []).append(i)

    for cid in sorted({b.class_id for b in boxes} | set(by_class)):
        b_idx = [i for i, b in enumerate(boxes) if b.class_id == cid]
        i_idx = by_class.get(cid, [])
        if b_idx and not i_idx:
            discarded += [{"kind": "box", "class_id": cid, "index": bi,
                           "reason": "no_mask_instance_of_class", "best_iou": 0.0}
                          for bi in b_idx]
            continue
        if i_idx and not b_idx:
            discarded += [{"kind": "instance", "class_id": cid, "index": ii,
                           "reason": "no_box_of_class"} for ii in i_idx]
            continue

        ious = np.zeros((len(b_idx), len(i_idx)), dtype=np.float64)
        for r, bi in enumerate(b_idx):
            bx1, by1, bx2, by2 = boxes[bi].hull
            for c, ii in enumerate(i_idx):
                ix1, iy1, ix2, iy2 = instances[ii].bbox
                if bx2 <= ix1 or ix2 <= bx1 or by2 <= iy1 or iy2 <= by1:
                    continue
                ious[r, c] = polygon_instance_iou(labels, instances[ii], boxes[bi], shape)

        res = hungarian_match(ious, iou_threshold)
        m_rows = {r for r, _, _ in res.matches}
        m_cols = {c for _, c, _ in res.matches}
        pairs += [(b_idx[r], i_idx[c], float(v)) for r, c, v in res.matches]

        for r, bi in enumerate(b_idx):
            if r in m_rows:
                continue
            best = float(ious[r].max()) if ious.shape[1] else 0.0
            reason = ("no_overlapping_instance" if best == 0.0 else
                      "below_iou_threshold" if best < iou_threshold else
                      "lost_to_one_to_one_assignment")
            discarded.append({"kind": "box", "class_id": cid, "index": bi,
                              "reason": reason, "best_iou": round(best, 6)})
        for c, ii in enumerate(i_idx):
            if c in m_cols:
                continue
            best = float(ious[:, c].max()) if ious.shape[0] else 0.0
            discarded.append({"kind": "instance", "class_id": cid, "index": ii,
                              "reason": ("no_overlapping_box" if best == 0.0
                                         else "unassigned"),
                              "best_iou": round(best, 6)})
    return pairs, discarded


def match_semantic_mode(boxes, sem_rgb, iou_threshold):
    """Replicates the earlier construction. Regression comparisons only."""
    h, w = sem_rgb.shape[:2]
    class_masks, pairs, comp_masks = {}, [], []
    for bi, box in enumerate(boxes):
        cid = box.class_id
        if cid not in class_masks:
            colour = CLASS_ID_TO_ISAID_COLOR.get(cid)
            class_masks[cid] = (
                np.all(sem_rgb == np.array(colour, dtype=np.uint8), axis=-1).astype(np.uint8)
                if colour else np.zeros((h, w), np.uint8))
        cmask = class_masks[cid]
        if not cmask.any():
            continue
        x1, y1, x2, y2 = box.hull
        pad = int(max(x2 - x1, y2 - y1) * 0.2)
        cx1, cy1 = max(0, x1 - pad), max(0, y1 - pad)
        cx2, cy2 = min(w, x2 + pad), min(h, y2 + pad)
        crop = cmask[cy1:cy2, cx1:cx2]
        if crop.size == 0 or not crop.any():
            continue
        n_comp, comp = cv2.connectedComponents(crop)
        best_iou, best = 0.0, None
        bx1, by1, bx2, by2 = max(0, x1), max(0, y1), min(w, x2), min(h, y2)
        if bx2 <= bx1 or by2 <= by1:
            continue
        for k in range(1, n_comp):
            full = np.zeros((h, w), dtype=bool)
            full[cy1:cy2, cx1:cx2] = comp == k
            rect = np.zeros((h, w), dtype=bool)
            rect[by1:by2, bx1:bx2] = True
            inter = int(np.count_nonzero(full & rect))
            union = int(np.count_nonzero(full | rect))
            iou = inter / union if union else 0.0
            if iou > best_iou:
                best_iou, best = iou, full
        if best is not None and best_iou >= iou_threshold:
            pairs.append((bi, len(comp_masks), float(best_iou)))
            comp_masks.append(best)
    return pairs, comp_masks


# --------------------------------------------------------------------------- #
# per-image worker
# --------------------------------------------------------------------------- #

def process_image(task: dict) -> dict:
    img_id, split = task["img_id"], task["split"]
    dota, isaid, out = Path(task["dota"]), Path(task["isaid"]), Path(task["out"])
    mode, thr, image_mode = task["mask_source"], task["iou_threshold"], task["image_mode"]
    mask_mode = task.get("mask_mode", "reconciled")

    boxes, gsd, imagesource = load_dota_label(dota / split / "labels" / f"{img_id}.txt")
    sem = read_rgb(isaid / split / "semantic_masks" / f"{img_id}_instance_color_RGB.png")
    ins = read_rgb(isaid / split / "instance_masks" / f"{img_id}_instance_id_RGB.png")
    if sem is None or ins is None or sem.shape != ins.shape:
        return {"img_id": img_id, "split": split, "status": "unreadable",
                "boxes": len(boxes), "instances": 0, "pairs": [], "discarded": [],
                "per_class": {}, "gsd": None, "ambiguous": 0}

    shape = sem.shape[:2]
    labels, instances, ambiguous = build_instance_index(sem, ins)

    if mode == "instance":
        matched, discarded = match_instance_mode(boxes, labels, instances, shape, thr)
    else:
        matched, comp_masks = match_semantic_mode(boxes, sem, thr)
        paired = {bi for bi, _, _ in matched}
        discarded = [{"kind": "box", "class_id": boxes[bi].class_id, "index": bi,
                      "reason": "unpaired_semantic_mode", "best_iou": 0.0}
                     for bi in range(len(boxes)) if bi not in paired]

    per_class = defaultdict(lambda: {"boxes": 0, "pairs": 0, "src_instances": 0})
    for b in boxes:
        per_class[b.class_id]["boxes"] += 1
    for inst in instances:
        per_class[inst.class_id]["src_instances"] += 1
    for bi, _, _ in matched:
        per_class[boxes[bi].class_id]["pairs"] += 1

    pair_records, discard_records = [], []
    for d in discarded:
        rec = {"image_id": img_id, "split": split, "kind": d["kind"],
               "class_name": CLASS_ID_TO_NAME[d["class_id"]], "reason": d["reason"],
               "best_iou": d.get("best_iou", 0.0)}
        if d["kind"] == "box":
            rec["corners"] = [round(v, 1) for v in boxes[d["index"]].corners.tolist()]
        elif mode == "instance":
            rec["instance_rgb"] = list(instances[d["index"]].colour)
            rec["instance_area_px"] = instances[d["index"]].area
        discard_records.append(rec)

    if not matched:
        return {"img_id": img_id, "split": split, "status": "no_pairs",
                "boxes": len(boxes), "instances": len(instances), "pairs": [],
                "discarded": discard_records, "per_class": dict(per_class),
                "gsd": gsd, "ambiguous": ambiguous}

    # ---- write artefacts ----
    obb_rows, hbb_rows = [], []
    sem_out = np.zeros((*shape, 3), dtype=np.uint8)
    ins_out = np.zeros((*shape, 3), dtype=np.uint8) if mode == "instance" else None

    for bi, ref, iou in matched:
        b = boxes[bi]
        obb_rows.append((b.corners.tolist(), b.class_id, b.difficulty))
        hbb_rows.append((hull_corners(b), b.class_id, b.difficulty))
        sel = (labels == instances[ref].label) if mode == "instance" else comp_masks[ref]
        if mask_mode == "reconciled":
            # Clip to the oriented box: the released mask is consistent with the
            # annotation that delimits it, and cannot contain a neighbouring
            # object's pixels. See documentation/DECISION_reconciled_masks.md
            poly = np.zeros(shape, dtype=np.uint8)
            cv2.fillPoly(poly, [np.round(b.corners.reshape(4, 2)).astype(np.int32)], 1)
            clipped = sel & (poly > 0)
            if clipped.any():
                sel = clipped
        sem_out[sel] = CLASS_ID_TO_ISAID_COLOR[b.class_id]
        if ins_out is not None:
            ins_out[sel] = instances[ref].colour
        rec = {"image_id": img_id, "split": split, "class_name": CLASS_ID_TO_NAME[b.class_id],
               "obb": [round(v, 1) for v in b.corners.tolist()],
               "hbb": [round(v, 1) for v in hull_corners(b)],
               "difficulty": b.difficulty, "iou": round(iou, 6)}
        if mode == "instance":
            rec["instance_rgb"] = list(instances[ref].colour)
            rec["instance_area_px"] = instances[ref].area
        pair_records.append(rec)

    write_dota_label(out / split / "labels_obb" / f"{img_id}.txt", obb_rows, gsd, imagesource)
    write_dota_label(out / split / "labels_hbb" / f"{img_id}.txt", hbb_rows, gsd, imagesource)

    outputs = [("semantic_masks", "instance_color", sem_out)]
    if ins_out is not None:
        outputs.append(("instance_masks", "instance_id", ins_out))
    for sub, tag, arr in outputs:
        p = out / split / sub / f"{img_id}_{tag}_RGB.png"
        p.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(p), cv2.cvtColor(arr, cv2.COLOR_RGB2BGR))

    if image_mode != "none":
        src = dota / split / "images" / f"{img_id}.png"
        dst = out / split / "images" / f"{img_id}.png"
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists():
            dst.unlink()
        try:
            if image_mode == "hardlink":
                os.link(src, dst)
            else:
                shutil.copy2(src, dst)
        except OSError:
            shutil.copy2(src, dst)

    return {"img_id": img_id, "split": split, "status": "kept", "boxes": len(boxes),
            "instances": len(instances), "pairs": pair_records,
            "discarded": discard_records, "per_class": dict(per_class),
            "gsd": gsd, "ambiguous": ambiguous}


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git_sha() -> str:
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                             text=True, timeout=10)
        return out.stdout.strip() or "unknown"
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dota", type=Path, default=Path("dataset/DOTA_v1"))
    ap.add_argument("--isaid", type=Path, default=Path("dataset/iSAID"))
    ap.add_argument("--out", type=Path, default=Path("dataset/AerialFuseCV"))
    ap.add_argument("--mask-source", choices=("instance", "semantic"), default="instance")
    ap.add_argument("--mask-mode", choices=("reconciled", "isaid"), default="reconciled",
                    help="reconciled = matched instance clipped to the oriented box "
                         "(consistent with the annotation that delimits it); "
                         "isaid = the instance as iSAID drew it")
    ap.add_argument("--iou-threshold", type=float, default=0.1)
    ap.add_argument("--image-mode", choices=("copy", "hardlink", "none"), default="copy",
                    help="copy = self-contained dataset (default); hardlink saves space "
                         "but shares inodes with the source; none writes annotations only")
    ap.add_argument("--splits", nargs="+", default=list(SPLITS))
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    ap.add_argument("--results-root", type=Path, default=Path("results/experimental/AerialFuseCV_Testing/aerialfusecv_build"))
    args = ap.parse_args()

    missing = [str(p) for s in args.splits
               for p in (args.dota / s / "images", args.dota / s / "labels",
                         args.isaid / s / "semantic_masks", args.isaid / s / "instance_masks")
               if not p.exists()]
    if missing:
        print("ERROR: missing expected source directories:", file=sys.stderr)
        [print("  " + p, file=sys.stderr) for p in missing]
        return 2

    tasks = []
    for split in args.splits:
        ids = sorted(p.stem for p in (args.dota / split / "images").glob("*.png"))
        if args.limit:
            ids = ids[: args.limit]
        tasks += [{"img_id": i, "split": split, "dota": str(args.dota),
                   "isaid": str(args.isaid), "out": str(args.out),
                   "mask_source": args.mask_source, "iou_threshold": args.iou_threshold,
                   "image_mode": args.image_mode, "mask_mode": args.mask_mode} for i in ids]

    run_id = f"{time.strftime('%Y%m%d_%H%M%S')}_{git_sha()[:7]}"
    results_dir = args.results_root / run_id
    results_dir.mkdir(parents=True, exist_ok=True)
    args.out.mkdir(parents=True, exist_ok=True)

    stats = {c: {s: {"boxes": 0, "pairs": 0, "src_instances": 0} for s in args.splits}
             for c in range(NUM_DOTA_CLASSES)}
    per_split = {s: {"images_seen": 0, "images_kept": 0, "boxes": 0, "pairs": 0,
                     "src_instances": 0} for s in args.splits}
    gsd_map, excluded, iou_values = {}, [], []
    discard_counts = defaultdict(int)
    discard_by_class = defaultdict(lambda: defaultdict(int))
    ambiguous_total = 0
    t0 = time.time()

    print(f"building {len(tasks)} images with {args.workers} workers "
          f"(mode={args.mask_source})", flush=True)

    with open(args.out / "pairs.jsonl", "w", encoding="utf-8") as pf, \
            open(args.out / "discarded.jsonl", "w", encoding="utf-8") as df, \
            ProcessPoolExecutor(max_workers=args.workers) as pool:
        for n, r in enumerate(pool.map(process_image, tasks, chunksize=4), 1):
            s = r["split"]
            per_split[s]["images_seen"] += 1
            per_split[s]["boxes"] += r["boxes"]
            per_split[s]["src_instances"] += r["instances"]
            ambiguous_total += r["ambiguous"]
            for cid, d in r["per_class"].items():
                for k, v in d.items():
                    stats[int(cid)][s][k] += v
            for rec in r["pairs"]:
                pf.write(json.dumps(rec) + "\n")
                iou_values.append(rec["iou"])
            for rec in r["discarded"]:
                df.write(json.dumps(rec) + "\n")
                discard_counts[(rec["kind"], rec["reason"])] += 1
                discard_by_class[rec["class_name"]][rec["kind"]] += 1
            if r["status"] == "kept":
                per_split[s]["images_kept"] += 1
                per_split[s]["pairs"] += len(r["pairs"])
                if r["gsd"] is not None:
                    gsd_map[r["img_id"]] = r["gsd"]
            else:
                excluded.append(r["img_id"])
            if n % 200 == 0:
                el = time.time() - t0
                print(f"  {n}/{len(tasks)}  {el:.0f}s  ({n/el:.1f} img/s)", flush=True)

    totals = {k: sum(v[k] for v in per_split.values())
              for k in ("boxes", "pairs", "src_instances", "images_kept", "images_seen")}
    per_class = {}
    for cid in range(NUM_DOTA_CLASSES):
        row = {"class_id": cid, "class_name": CLASS_ID_TO_NAME[cid]}
        for s in args.splits:
            d = stats[cid][s]
            row[s] = {**d, "box_pairing_rate": (d["pairs"] / d["boxes"]) if d["boxes"] else None}
        row["total_pairs"] = sum(stats[cid][s]["pairs"] for s in args.splits)
        per_class[CLASS_ID_TO_NAME[cid]] = row

    a = np.array(iou_values) if iou_values else np.zeros(0)
    statistics = {
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "mask_source": args.mask_source,
        "matching_geometry": ("oriented polygon" if args.mask_source == "instance"
                              else "axis-aligned hull (regression)"),
        "iou_threshold": args.iou_threshold,
        "annotation_format": "DOTA native (headers, absolute px, class name, difficulty)",
        "mask_mode": args.mask_mode,
        "mask_definition": ("matched iSAID instance clipped to the oriented box"
                            if args.mask_mode == "reconciled"
                            else "matched iSAID instance as drawn"),
        "box_geometries_written": ["labels_obb", "labels_hbb"],
        "totals": {**totals, "images_excluded": len(excluded),
                   "box_pairing_rate": totals["pairs"] / totals["boxes"] if totals["boxes"] else None,
                   "instance_pairing_rate": (totals["pairs"] / totals["src_instances"]
                                             if totals["src_instances"] else None)},
        "per_split": per_split,
        "per_class": per_class,
        "matched_iou": {"mean": float(a.mean()) if a.size else None,
                        "median": float(np.median(a)) if a.size else None,
                        "p05": float(np.percentile(a, 5)) if a.size else None,
                        "p95": float(np.percentile(a, 95)) if a.size else None},
        "excluded_images": sorted(excluded),
        "instances_with_ambiguous_class": ambiguous_total,
        "discarded": {
            "by_reason": {f"{k}:{r}": n for (k, r), n in sorted(discard_counts.items())},
            "boxes": sum(n for (k, _), n in discard_counts.items() if k == "box"),
            "instances": sum(n for (k, _), n in discard_counts.items() if k == "instance"),
            "by_class": {c: dict(v) for c, v in sorted(discard_by_class.items())},
        },
    }
    manifest = {
        "run_id": run_id, "created_utc": statistics["generated_utc"],
        "git_sha": git_sha(), "command": " ".join(sys.argv),
        "args": {k: str(v) for k, v in vars(args).items()},
        "elapsed_s": round(time.time() - t0, 1),
        "environment": {"python": sys.version.split()[0], "numpy": np.__version__,
                        "opencv": cv2.__version__,
                        "conda_env": os.environ.get("CONDA_DEFAULT_ENV", "unknown")},
    }

    for target in (args.out, results_dir):
        (target / "dataset_statistics.json").write_text(json.dumps(statistics, indent=2),
                                                        encoding="utf-8")
        (target / "build_manifest.json").write_text(json.dumps(manifest, indent=2),
                                                     encoding="utf-8")
    (args.out / "images_gsd_mapping.json").write_text(
        json.dumps(dict(sorted(gsd_map.items())), indent=2), encoding="utf-8")

    checks = args.out / "checksums.sha256"
    with open(checks, "w", encoding="utf-8") as f:
        for p in sorted(args.out.rglob("*")):
            if p.is_file() and p.name != checks.name and "images" not in p.parts:
                f.write(f"{sha256(p)}  {p.relative_to(args.out).as_posix()}\n")

    t = statistics["totals"]
    print("\n" + "=" * 72)
    print(f"mode / geometry     : {args.mask_source} / {statistics['matching_geometry']}")
    print(f"mask definition     : {statistics['mask_definition']}")
    print(f"images kept         : {t['images_kept']} / {t['images_seen']}"
          f"   (excluded {t['images_excluded']})")
    print(f"source boxes        : {t['boxes']:,}")
    print(f"source instances    : {t['src_instances']:,}")
    print(f"pairs               : {t['pairs']:,}")
    print(f"box pairing rate    : {t['box_pairing_rate']:.4f}")
    print(f"instance pairing    : {t['instance_pairing_rate']:.4f}")
    print(f"matched IoU median  : {statistics['matched_iou']['median']:.3f}")
    print(f"ambiguous instances : {ambiguous_total}")
    print(f"elapsed             : {manifest['elapsed_s']:.0f}s")
    print(f"dataset -> {args.out}\nresults -> {results_dir}")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main())
