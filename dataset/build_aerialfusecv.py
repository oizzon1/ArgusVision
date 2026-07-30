"""Build AerialFuseCV from the official DOTA v1.0 and iSAID distributions.

One pass. No intermediate dataset. Run from the repo root, in AV_env:

    python dataset/build_aerialfusecv.py --dota dataset/DOTA_v1 \
        --isaid dataset/iSAID --out dataset/AerialFuseCV_v1

Two matching modes:

  --mask-source instance   (default) Exact. Instance identity comes from
        iSAID's per-instance masks and class from the semantic mask at the same
        pixels; a box is paired to an instance of its own class by IoU under a
        one-to-one assignment. No connected-components approximation.

  --mask-source semantic   Regression only. Replicates the precursor build
        (class-coloured mask, 20%-padded crop, connected components, greedy
        best-per-box, no one-to-one constraint) so that port fidelity can be
        proven against the dataset on disk before trusting the corrected path.

Every published number must come from `results/`, so the statistics and the run
manifest are written there as well as into the dataset directory.
"""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
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


# --------------------------------------------------------------------------- #
# data types
# --------------------------------------------------------------------------- #

@dataclass
class Box:
    class_id: int
    corners: np.ndarray          # (8,) x1 y1 ... x4 y4, source order
    difficulty: str
    hull: Tuple[int, int, int, int] = field(init=False)  # x1 y1 x2 y2, ints

    def __post_init__(self):
        c = self.corners.reshape(4, 2)
        self.hull = (
            int(np.floor(c[:, 0].min())), int(np.floor(c[:, 1].min())),
            int(np.ceil(c[:, 0].max())), int(np.ceil(c[:, 1].max())),
        )


@dataclass
class Instance:
    label: int                   # index into the labelled array
    class_id: int
    colour: Tuple[int, int, int]
    area: int
    bbox: Tuple[int, int, int, int]   # x1 y1 x2 y2


# --------------------------------------------------------------------------- #
# io helpers
# --------------------------------------------------------------------------- #

def pack(rgb: np.ndarray) -> np.ndarray:
    a = rgb.astype(np.int32)
    return (a[:, :, 0] << 16) | (a[:, :, 1] << 8) | a[:, :, 2]


def unpack(key: int) -> Tuple[int, int, int]:
    return ((key >> 16) & 0xFF, (key >> 8) & 0xFF, key & 0xFF)


def read_rgb(path: Path) -> Optional[np.ndarray]:
    bgr = cv2.imread(str(path), cv2.IMREAD_COLOR)
    return None if bgr is None else cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)


def load_dota_label(path: Path) -> Tuple[List[Box], Optional[float]]:
    """Parse a DOTA annotation file. Returns (boxes, gsd)."""
    boxes: List[Box] = []
    gsd: Optional[float] = None
    if not path.exists():
        return boxes, gsd
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        parts = line.split()
        if not parts:
            continue
        if parts[0] == "gsd:":
            try:
                gsd = float(parts[1])
            except (IndexError, ValueError):
                gsd = None
            continue
        if parts[0] == "imagesource:" or len(parts) < 10:
            continue
        try:
            corners = np.array([float(v) for v in parts[:8]], dtype=np.float64)
        except ValueError:
            continue
        class_id = CLASS_NAME_TO_ID.get(parts[8])
        if class_id is None:
            continue
        boxes.append(Box(class_id=class_id, corners=corners, difficulty=parts[9]))
    return boxes, gsd


# --------------------------------------------------------------------------- #
# instance indexing (corrected path)
# --------------------------------------------------------------------------- #

def build_instance_index(sem_rgb: np.ndarray, ins_rgb: np.ndarray):
    """Label every iSAID instance once, with its class, area and bounding box.

    Returns (labels array, list[Instance]). Class is taken from the semantic
    mask at the instance's own pixels; `scan_isaid_colours.py` verified over all
    1,869 images that no instance spans more than one class, so the assignment
    is unambiguous. Any instance that nonetheless disagrees is skipped and
    reported by the caller.
    """
    ik = pack(ins_rgb)
    sk = pack(sem_rgb)

    flat = ik.reshape(-1)
    uniq, inverse = np.unique(flat, return_inverse=True)
    labels = inverse.reshape(ik.shape).astype(np.int32)

    objects = ndimage.find_objects(labels)          # index i -> label i+1
    areas = np.bincount(inverse, minlength=uniq.size)

    instances: List[Instance] = []
    ambiguous = 0
    for idx, key in enumerate(uniq.tolist()):
        if key == 0:                                 # background
            continue
        sl = objects[idx - 1] if idx - 1 < len(objects) else None
        if sl is None:
            continue
        ys, xs = sl
        sub_lbl = labels[ys, xs] == idx
        sem_vals = np.unique(sk[ys, xs][sub_lbl])
        sem_vals = sem_vals[sem_vals != 0]
        if sem_vals.size != 1:
            ambiguous += 1
            continue
        class_id = ISAID_COLOR_TO_CLASS_ID.get(unpack(int(sem_vals[0])))
        if class_id is None:
            ambiguous += 1
            continue
        instances.append(Instance(
            label=idx,
            class_id=class_id,
            colour=unpack(key),
            area=int(areas[idx]),
            bbox=(xs.start, ys.start, xs.stop, ys.stop),
        ))
    return labels, instances, ambiguous


def rect_instance_iou(labels: np.ndarray, inst: Instance, hull, shape) -> float:
    """IoU between a box's axis-aligned hull (as a filled rectangle) and an
    instance mask. Same quantity the precursor optimised, so the two modes stay
    comparable."""
    h, w = shape
    x1, y1, x2, y2 = hull
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(w, x2), min(h, y2)
    if x2 <= x1 or y2 <= y1:
        return 0.0
    inter = int(np.count_nonzero(labels[y1:y2, x1:x2] == inst.label))
    if inter == 0:
        return 0.0
    union = (x2 - x1) * (y2 - y1) + inst.area - inter
    return inter / union if union > 0 else 0.0


def match_instance_mode(boxes, labels, instances, shape, iou_threshold):
    """One-to-one box<->instance assignment within each class."""
    pairs = []
    by_class: Dict[int, List[int]] = {}
    for i, inst in enumerate(instances):
        by_class.setdefault(inst.class_id, []).append(i)

    for cid in sorted({b.class_id for b in boxes}):
        b_idx = [i for i, b in enumerate(boxes) if b.class_id == cid]
        i_idx = by_class.get(cid, [])
        if not b_idx or not i_idx:
            continue
        ious = np.zeros((len(b_idx), len(i_idx)), dtype=np.float64)
        for r, bi in enumerate(b_idx):
            bx1, by1, bx2, by2 = boxes[bi].hull
            for c, ii in enumerate(i_idx):
                ix1, iy1, ix2, iy2 = instances[ii].bbox
                if bx2 <= ix1 or ix2 <= bx1 or by2 <= iy1 or iy2 <= by1:
                    continue                      # disjoint bounding boxes
                ious[r, c] = rect_instance_iou(labels, instances[ii], boxes[bi].hull, shape)
        res = hungarian_match(ious, iou_threshold)
        for r, c, iou in res.matches:
            pairs.append((b_idx[r], i_idx[c], float(iou)))
    return pairs


# --------------------------------------------------------------------------- #
# precursor replication (regression path)
# --------------------------------------------------------------------------- #

def match_semantic_mode(boxes, sem_rgb, iou_threshold):
    """Replicates the precursor: per-class colour mask, crop padded by 20% of
    the box's longer side, connected components, greedy best-per-box, no
    one-to-one constraint. Returns (pairs, component masks)."""
    h, w = sem_rgb.shape[:2]
    class_masks: Dict[int, np.ndarray] = {}
    pairs, comp_masks = [], []

    for bi, box in enumerate(boxes):
        cid = box.class_id
        if cid not in class_masks:
            colour = CLASS_ID_TO_ISAID_COLOR.get(cid)
            class_masks[cid] = (
                np.all(sem_rgb == np.array(colour, dtype=np.uint8), axis=-1).astype(np.uint8)
                if colour else np.zeros((h, w), np.uint8)
            )
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
        for k in range(1, n_comp):
            full = np.zeros((h, w), dtype=bool)
            full[cy1:cy2, cx1:cx2] = comp == k
            bx1, by1 = max(0, x1), max(0, y1)
            bx2, by2 = min(w, x2), min(h, y2)
            if bx2 <= bx1 or by2 <= by1:
                continue
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
# output
# --------------------------------------------------------------------------- #

def place_image(src: Path, dst: Path, mode: str) -> None:
    if mode == "none":
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        dst.unlink()
    if mode == "hardlink":
        try:
            os.link(src, dst)
            return
        except OSError:
            pass                                   # cross-device: fall back
    shutil.copy2(src, dst)


def write_label(path: Path, boxes: List[Box], keep: List[int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for bi in keep:
            b = boxes[bi]
            coords = " ".join(f"{v:.1f}" for v in b.corners.tolist())
            f.write(f"{coords} {CLASS_ID_TO_NAME[b.class_id]} {b.difficulty}\n")


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


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dota", type=Path, default=Path("dataset/DOTA_v1"))
    ap.add_argument("--isaid", type=Path, default=Path("dataset/iSAID"))
    ap.add_argument("--out", type=Path, default=Path("dataset/AerialFuseCV_v1"))
    ap.add_argument("--mask-source", choices=("instance", "semantic"), default="instance")
    ap.add_argument("--iou-threshold", type=float, default=0.1)
    ap.add_argument("--image-mode", choices=("hardlink", "copy", "none"), default="hardlink")
    ap.add_argument("--splits", nargs="+", default=list(SPLITS))
    ap.add_argument("--limit", type=int, default=None, help="first N images per split (smoke)")
    ap.add_argument("--results-root", type=Path, default=Path("results/aerialfusecv_build"))
    args = ap.parse_args()

    # ---- validate layout up front rather than failing mid-run ----
    problems = []
    for s in args.splits:
        for p in (args.dota / s / "images", args.dota / s / "labels",
                  args.isaid / s / "semantic_masks", args.isaid / s / "instance_masks"):
            if not p.exists():
                problems.append(str(p))
    if problems:
        print("ERROR: missing expected source directories:", file=sys.stderr)
        for p in problems:
            print("  " + p, file=sys.stderr)
        return 2

    run_id = f"{time.strftime('%Y%m%d_%H%M%S')}_{git_sha()[:7]}"
    results_dir = args.results_root / run_id
    results_dir.mkdir(parents=True, exist_ok=True)
    args.out.mkdir(parents=True, exist_ok=True)

    stats = {c: {s: {"boxes": 0, "pairs": 0, "src_instances": 0}
                 for s in args.splits} for c in range(NUM_DOTA_CLASSES)}
    per_split = {s: {"images_seen": 0, "images_kept": 0, "boxes": 0,
                     "pairs": 0, "src_instances": 0} for s in args.splits}
    gsd_map: Dict[str, float] = {}
    excluded: List[str] = []
    ambiguous_total = 0
    iou_values: List[float] = []
    pairs_path = args.out / "pairs.jsonl"
    t0 = time.time()

    with open(pairs_path, "w", encoding="utf-8") as pairs_f:
        for split in args.splits:
            img_dir = args.dota / split / "images"
            ids = sorted(p.stem for p in img_dir.glob("*.png"))
            if args.limit:
                ids = ids[: args.limit]

            for n, img_id in enumerate(ids, 1):
                per_split[split]["images_seen"] += 1
                boxes, gsd = load_dota_label(args.dota / split / "labels" / f"{img_id}.txt")
                sem = read_rgb(args.isaid / split / "semantic_masks" /
                               f"{img_id}_instance_color_RGB.png")
                ins = read_rgb(args.isaid / split / "instance_masks" /
                               f"{img_id}_instance_id_RGB.png")
                if sem is None or ins is None or sem.shape != ins.shape:
                    excluded.append(img_id)
                    continue

                shape = sem.shape[:2]
                for b in boxes:
                    stats[b.class_id][split]["boxes"] += 1
                    per_split[split]["boxes"] += 1

                labels, instances, ambiguous = build_instance_index(sem, ins)
                ambiguous_total += ambiguous
                for inst in instances:
                    stats[inst.class_id][split]["src_instances"] += 1
                per_split[split]["src_instances"] += len(instances)

                if args.mask_source == "instance":
                    matched = match_instance_mode(boxes, labels, instances, shape,
                                                  args.iou_threshold)
                    masks_for = {bi: instances[ii] for bi, ii, _ in matched}
                else:
                    matched, comp_masks = match_semantic_mode(boxes, sem, args.iou_threshold)
                    masks_for = {bi: comp_masks[ci] for bi, ci, _ in matched}

                if not matched:
                    excluded.append(img_id)
                    continue

                keep = [bi for bi, _, _ in matched]
                for bi, _, iou in matched:
                    cid = boxes[bi].class_id
                    stats[cid][split]["pairs"] += 1
                    per_split[split]["pairs"] += 1
                    iou_values.append(iou)

                # ---- write artefacts ----
                place_image(img_dir / f"{img_id}.png",
                            args.out / split / "images" / f"{img_id}.png", args.image_mode)
                write_label(args.out / split / "labels" / f"{img_id}.txt", boxes, keep)

                sem_out = np.zeros((*shape, 3), dtype=np.uint8)
                # Instance masks are written only when instance identity is
                # genuine. In semantic (regression) mode no per-instance source
                # exists, and inventing colours would fabricate data.
                ins_out = (np.zeros((*shape, 3), dtype=np.uint8)
                           if args.mask_source == "instance" else None)
                for bi, ref, _ in matched:
                    cid = boxes[bi].class_id
                    if args.mask_source == "instance":
                        inst = instances[ref]
                        sel = labels == inst.label
                        ins_out[sel] = inst.colour
                    else:
                        sel = masks_for[bi]
                    sem_out[sel] = CLASS_ID_TO_ISAID_COLOR[cid]

                outputs = [("semantic_masks", "instance_color", sem_out)]
                if ins_out is not None:
                    outputs.append(("instance_masks", "instance_id", ins_out))
                for sub, tag, arr in outputs:
                    p = args.out / split / sub / f"{img_id}_{tag}_RGB.png"
                    p.parent.mkdir(parents=True, exist_ok=True)
                    cv2.imwrite(str(p), cv2.cvtColor(arr, cv2.COLOR_RGB2BGR))

                for bi, ref, iou in matched:
                    b = boxes[bi]
                    rec = {
                        "image_id": img_id, "split": split,
                        "class_id": b.class_id, "class_name": CLASS_ID_TO_NAME[b.class_id],
                        "corners": [round(v, 1) for v in b.corners.tolist()],
                        "hull": list(b.hull), "difficulty": b.difficulty, "iou": round(iou, 6),
                    }
                    if args.mask_source == "instance":
                        rec["instance_rgb"] = list(instances[ref].colour)
                        rec["instance_area_px"] = instances[ref].area
                    pairs_f.write(json.dumps(rec) + "\n")

                if gsd is not None:
                    gsd_map[img_id] = gsd
                per_split[split]["images_kept"] += 1

                if n % 100 == 0:
                    print(f"[{split}] {n}/{len(ids)}  {time.time()-t0:.0f}s", flush=True)

    # ---- statistics ----
    totals = {
        "boxes": sum(v["boxes"] for v in per_split.values()),
        "pairs": sum(v["pairs"] for v in per_split.values()),
        "src_instances": sum(v["src_instances"] for v in per_split.values()),
        "images_kept": sum(v["images_kept"] for v in per_split.values()),
        "images_seen": sum(v["images_seen"] for v in per_split.values()),
    }
    per_class = {}
    for cid in range(NUM_DOTA_CLASSES):
        row = {"class_id": cid, "class_name": CLASS_ID_TO_NAME[cid]}
        for s in args.splits:
            d = stats[cid][s]
            row[s] = {**d, "box_pairing_rate": (d["pairs"] / d["boxes"]) if d["boxes"] else None}
        row["total_pairs"] = sum(stats[cid][s]["pairs"] for s in args.splits)
        per_class[CLASS_ID_TO_NAME[cid]] = row

    iou_arr = np.array(iou_values) if iou_values else np.zeros(0)
    statistics = {
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "mask_source": args.mask_source,
        "iou_threshold": args.iou_threshold,
        "totals": {
            **totals,
            "images_excluded": len(excluded),
            "box_pairing_rate": totals["pairs"] / totals["boxes"] if totals["boxes"] else None,
            "instance_pairing_rate": (
                totals["pairs"] / totals["src_instances"] if totals["src_instances"] else None),
        },
        "per_split": per_split,
        "per_class": per_class,
        "matched_iou": {
            "mean": float(iou_arr.mean()) if iou_arr.size else None,
            "median": float(np.median(iou_arr)) if iou_arr.size else None,
            "p05": float(np.percentile(iou_arr, 5)) if iou_arr.size else None,
            "p95": float(np.percentile(iou_arr, 95)) if iou_arr.size else None,
        },
        "excluded_images": sorted(excluded),
        "instances_with_ambiguous_class": ambiguous_total,
        "images_without_gsd": sorted(
            set(i for s in args.splits
                for i in (p.stem for p in (args.dota / s / "images").glob("*.png")))
            - set(gsd_map)
        )[:50],
    }

    manifest = {
        "run_id": run_id,
        "created_utc": statistics["generated_utc"],
        "git_sha": git_sha(),
        "command": " ".join(sys.argv),
        "args": {k: str(v) for k, v in vars(args).items()},
        "elapsed_s": round(time.time() - t0, 1),
        "environment": {
            "python": sys.version.split()[0],
            "numpy": np.__version__,
            "opencv": cv2.__version__,
            "conda_env": os.environ.get("CONDA_DEFAULT_ENV", "unknown"),
        },
    }

    for target in (args.out, results_dir):
        (target / "dataset_statistics.json").write_text(
            json.dumps(statistics, indent=2), encoding="utf-8")
    (results_dir / "build_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8")
    (args.out / "build_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8")
    (args.out / "images_gsd_mapping.json").write_text(
        json.dumps(dict(sorted(gsd_map.items())), indent=2), encoding="utf-8")

    checks = args.out / "checksums.sha256"
    with open(checks, "w", encoding="utf-8") as f:
        for p in sorted(args.out.rglob("*")):
            if p.is_file() and p.name != checks.name and "images" not in p.parts:
                f.write(f"{sha256(p)}  {p.relative_to(args.out).as_posix()}\n")

    t = statistics["totals"]
    print("\n" + "=" * 72)
    print(f"mode                : {args.mask_source}   IoU >= {args.iou_threshold}")
    print(f"images kept         : {t['images_kept']} / {t['images_seen']}"
          f"   (excluded {t['images_excluded']})")
    print(f"source boxes        : {t['boxes']:,}")
    print(f"source instances    : {t['src_instances']:,}")
    print(f"pairs               : {t['pairs']:,}")
    print(f"box pairing rate    : {t['box_pairing_rate']:.4f}")
    print(f"instance pairing    : {t['instance_pairing_rate']:.4f}")
    print(f"ambiguous instances : {statistics['instances_with_ambiguous_class']}")
    print(f"elapsed             : {manifest['elapsed_s']:.0f}s")
    print(f"dataset  -> {args.out}")
    print(f"results  -> {results_dir}")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main())
