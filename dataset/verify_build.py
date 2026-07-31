"""Compare a build against a reference dataset directory. INTERNAL TOOL.

Purpose: measure the delta between a new build and an existing one, so that a
change in construction can be attributed to the change itself rather than to a
porting mistake. Not shipped with the dataset.

    python dataset/verify_build.py --build dataset/AerialFuseCV_regression \
        --reference dataset/AerialFuseCV_Refined

Three levels, all reported (the run does not stop at the first failure):

  1 structural  — same splits, same retained image IDs, same counts
  2 content     — per image: identical box sets (order-insensitive, tolerant of
                  decimal formatting) and pixel-identical masks
  3 statistical — per-class pair counts, side by side with the delta

Level 2 is the one that matters: it either proves the two constructions agree
object-for-object, or it localises exactly where they part company.
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import cv2
import numpy as np

SPLITS = ("train", "val")
COORD_TOL = 0.05          # labels are written to 1 decimal place


def labels_dir(root: Path, split: str) -> Path:
    """Builds may store oriented boxes in labels_obb/; older ones use labels/."""
    for name in ("labels_obb", "labels"):
        d = root / split / name
        if d.exists():
            return d
    return root / split / "labels"


def image_ids(root: Path, split: str) -> Set[str]:
    d = labels_dir(root, split)
    return {p.stem for p in d.glob("*.txt")} if d.exists() else set()


def parse_label(path: Path) -> List[Tuple[str, Tuple[float, ...]]]:
    out = []
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        parts = line.split()
        if len(parts) < 10:
            continue
        try:
            coords = tuple(float(v) for v in parts[:8])
        except ValueError:
            continue
        out.append((parts[8], coords))
    return out


def boxes_match(a, b) -> bool:
    """Order-insensitive comparison with a tolerance on coordinate formatting."""
    if len(a) != len(b):
        return False
    remaining = list(b)
    for cls, coords in a:
        hit = None
        for i, (c2, co2) in enumerate(remaining):
            if c2 == cls and all(abs(x - y) <= COORD_TOL for x, y in zip(coords, co2)):
                hit = i
                break
        if hit is None:
            return False
        remaining.pop(hit)
    return True


def read_mask(path: Path) -> Optional[np.ndarray]:
    return cv2.imread(str(path), cv2.IMREAD_COLOR) if path.exists() else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", type=Path, required=True)
    ap.add_argument("--reference", type=Path, required=True)
    ap.add_argument("--splits", nargs="+", default=list(SPLITS))
    ap.add_argument("--max-report", type=int, default=25)
    ap.add_argument("--out", type=Path,
                    default=Path("results/AerialFuseCV_Testing/build_verification/verification_report.json"))
    args = ap.parse_args()

    report: Dict = {"build": str(args.build), "reference": str(args.reference), "levels": {}}
    ok = True

    # ---------------- level 1: structural ----------------
    l1: Dict = {"per_split": {}, "passed": True}
    common: Dict[str, Set[str]] = {}
    for s in args.splits:
        b, r = image_ids(args.build, s), image_ids(args.reference, s)
        only_b, only_r = sorted(b - r), sorted(r - b)
        common[s] = b & r
        entry = {
            "build_images": len(b), "reference_images": len(r),
            "only_in_build": only_b[: args.max_report],
            "only_in_reference": only_r[: args.max_report],
            "n_only_in_build": len(only_b), "n_only_in_reference": len(only_r),
        }
        if only_b or only_r:
            l1["passed"] = False
        l1["per_split"][s] = entry
    report["levels"]["1_structural"] = l1
    ok &= l1["passed"]

    # ---------------- level 2: content ----------------
    l2: Dict = {"label_mismatches": [], "mask_mismatches": [],
                "missing_masks": [], "passed": True}
    counts = {"labels_compared": 0, "masks_compared": 0}
    for s in args.splits:
        for img_id in sorted(common[s]):
            a = parse_label(labels_dir(args.build, s) / f"{img_id}.txt")
            b = parse_label(labels_dir(args.reference, s) / f"{img_id}.txt")
            counts["labels_compared"] += 1
            if not boxes_match(a, b):
                l2["passed"] = False
                if len(l2["label_mismatches"]) < args.max_report:
                    l2["label_mismatches"].append(
                        {"image": img_id, "split": s, "build_boxes": len(a),
                         "reference_boxes": len(b)})

            name = f"{img_id}_instance_color_RGB.png"
            ma = read_mask(args.build / s / "semantic_masks" / name)
            mb = read_mask(args.reference / s / "semantic_masks" / name)
            if ma is None or mb is None:
                if len(l2["missing_masks"]) < args.max_report:
                    l2["missing_masks"].append({"image": img_id, "split": s,
                                                "in_build": ma is not None,
                                                "in_reference": mb is not None})
                l2["passed"] = False
                continue
            counts["masks_compared"] += 1
            if ma.shape != mb.shape or not np.array_equal(ma, mb):
                l2["passed"] = False
                if len(l2["mask_mismatches"]) < args.max_report:
                    diff = (int(np.count_nonzero(np.any(ma != mb, axis=-1)))
                            if ma.shape == mb.shape else None)
                    l2["mask_mismatches"].append(
                        {"image": img_id, "split": s, "differing_pixels": diff,
                         "shape_build": list(ma.shape), "shape_reference": list(mb.shape)})
    l2.update(counts)
    l2["n_label_mismatches"] = len(l2["label_mismatches"])
    l2["n_mask_mismatches"] = len(l2["mask_mismatches"])
    report["levels"]["2_content"] = l2
    ok &= l2["passed"]

    # ---------------- level 3: statistical ----------------
    l3: Dict = {}
    stats_path = args.build / "dataset_statistics.json"
    if stats_path.exists():
        st = json.loads(stats_path.read_text(encoding="utf-8"))
        l3["build_totals"] = st.get("totals", {})
        per_class = {}
        for name, row in st.get("per_class", {}).items():
            per_class[name] = row.get("total_pairs", 0)
        l3["build_pairs_per_class"] = per_class
    ref_counts: Dict[str, int] = defaultdict(int)
    for s in args.splits:
        for img_id in sorted(image_ids(args.reference, s)):
            for cls, _ in parse_label(labels_dir(args.reference, s) / f"{img_id}.txt"):
                ref_counts[cls] += 1
    l3["reference_pairs_per_class"] = dict(sorted(ref_counts.items()))
    if "build_pairs_per_class" in l3:
        l3["delta_per_class"] = {
            k: l3["build_pairs_per_class"].get(k, 0) - ref_counts.get(k, 0)
            for k in sorted(set(l3["build_pairs_per_class"]) | set(ref_counts))
        }
        l3["total_delta"] = sum(l3["delta_per_class"].values())
    report["levels"]["3_statistical"] = l3

    report["passed"] = bool(ok)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("\n" + "=" * 72)
    for s in args.splits:
        e = l1["per_split"][s]
        print(f"L1 {s:5} build {e['build_images']:>5} | reference {e['reference_images']:>5}"
              f" | only-build {e['n_only_in_build']} only-ref {e['n_only_in_reference']}")
    print(f"L2 labels compared {l2['labels_compared']:>5}  mismatches {l2['n_label_mismatches']}")
    print(f"L2 masks  compared {l2['masks_compared']:>5}  mismatches {l2['n_mask_mismatches']}"
          f"  missing {len(l2['missing_masks'])}")
    if "total_delta" in l3:
        print(f"L3 pair delta vs reference: {l3['total_delta']:+}")
    print(f"RESULT: {'PASS' if ok else 'DIVERGENCE — see report'}")
    print(f"report -> {args.out}")
    print("=" * 72)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
