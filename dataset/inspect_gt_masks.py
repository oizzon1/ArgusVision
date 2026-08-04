"""Visual comparison of two ground-truth mask derivations. INTERNAL TOOL.

For each ground-truth instance it renders, side by side:
  1. the image crop with the oriented box drawn
  2. the mask obtained by clipping the class-coloured semantic mask with that box
  3. the exact iSAID instance mask
  4. a difference view — red = present only in the clip (contamination from
     neighbouring same-class objects), blue = present only in the exact
     instance (truncated by the box)

Selects the N best- and N worst-agreeing instances so both failure and success
can be inspected.

    python dataset/inspect_gt_masks.py --split val --images 60 --top 10
"""

import argparse
import collections
import json
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from argusvision.data.aerialfusecv import (  # noqa: E402
    AerialFuseCVSplit,
    extract_gt_instance_mask,
)

PANEL = 340
PAD = 0.6           # crop margin as a fraction of the box's longer side


def overlay(base, mask, colour, alpha=0.55):
    out = base.copy()
    sel = mask.astype(bool)
    if sel.any():
        out[sel] = (out[sel] * (1 - alpha) + np.array(colour, np.float32) * alpha).astype(np.uint8)
    return out


def fit(img, size=PANEL):
    h, w = img.shape[:2]
    s = size / max(h, w)
    out = cv2.resize(img, (max(1, int(w * s)), max(1, int(h * s))),
                     interpolation=cv2.INTER_NEAREST)
    canvas = np.zeros((size, size, 3), np.uint8)
    canvas[: out.shape[0], : out.shape[1]] = out
    return canvas


def label(panel, text):
    cv2.rectangle(panel, (0, 0), (panel.shape[1], 22), (0, 0, 0), -1)
    cv2.putText(panel, text, (6, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1,
                cv2.LINE_AA)
    return panel


def render(image, sem_clip, exact, corners, origin, agreement, meta):
    ox, oy = origin
    pts = (corners.reshape(4, 2) - np.array([ox, oy])).round().astype(np.int32)

    p1 = image.copy()
    cv2.polylines(p1, [pts], True, (255, 210, 0), 2, cv2.LINE_AA)

    p2 = overlay(image, sem_clip, (255, 60, 60))
    cv2.polylines(p2, [pts], True, (255, 210, 0), 1, cv2.LINE_AA)

    p3 = overlay(image, exact, (60, 220, 60))
    cv2.polylines(p3, [pts], True, (255, 210, 0), 1, cv2.LINE_AA)

    only_clip = sem_clip & ~exact
    only_exact = exact & ~sem_clip
    p4 = overlay(overlay(image, only_clip, (255, 40, 40), 0.75),
                 only_exact, (60, 120, 255), 0.75)

    panels = [label(fit(p1), "image + OBB"),
              label(fit(p2), "clipped semantic GT"),
              label(fit(p3), "exact instance GT"),
              label(fit(p4), "red=extra  blue=missing")]
    strip = np.hstack(panels)

    header = np.zeros((30, strip.shape[1], 3), np.uint8)
    cv2.putText(header, f"{meta['image_id']}  {meta['class_name']}  "
                        f"agreement IoU={agreement:.3f}  "
                        f"extra={int(only_clip.sum()):,}px  missing={int(only_exact.sum()):,}px",
                (8, 21), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)
    return np.vstack([header, strip])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", type=Path, default=Path("dataset/AerialFuseCV"))
    ap.add_argument("--split", default="val")
    ap.add_argument("--images", type=int, default=60)
    ap.add_argument("--top", type=int, default=10)
    ap.add_argument("--out", type=Path, default=Path("results/AerialFuseCV_Testing/gt_mask_comparison"))
    args = ap.parse_args()

    root = args.dataset / args.split
    d = AerialFuseCVSplit(root)
    pairs = collections.defaultdict(list)
    for line in open(args.dataset / "pairs.jsonl", encoding="utf-8"):
        r = json.loads(line)
        if r["split"] == args.split:
            pairs[r["image_id"]].append(r)

    for name in ("best", "worst"):
        (args.out / name).mkdir(parents=True, exist_ok=True)   # visible immediately

    cases = []
    ids = d.image_ids[: args.images]
    for n, img_id in enumerate(ids, 1):
        gts, recs = d.load_ground_truth(img_id), pairs[img_id]
        if len(gts) != len(recs):
            continue
        sem = d.load_semantic_mask(img_id)
        ins = cv2.cvtColor(
            cv2.imread(str(root / "instance_masks" / f"{img_id}_instance_id_RGB.png")),
            cv2.COLOR_BGR2RGB)
        for gt, rec in zip(gts, recs):
            exact = np.all(ins == np.array(rec["instance_rgb"], np.uint8), axis=-1)
            clip = extract_gt_instance_mask(sem, gt)
            u = np.logical_or(exact, clip).sum()
            if u == 0:
                continue
            cases.append((np.logical_and(exact, clip).sum() / u, img_id, rec, gt))
        if n % 20 == 0:
            print(f"  scanned {n}/{len(ids)} images, {len(cases):,} instances", flush=True)

    cases.sort(key=lambda c: c[0])
    picks = [("worst", cases[: args.top]), ("best", cases[-args.top:][::-1])]

    for name, group in picks:
        outdir = args.out / name
        # group by image so each image and its two masks load once, not per figure
        by_image = collections.defaultdict(list)
        for rank, case in enumerate(group, 1):
            by_image[case[1]].append((rank, case))
        for img_id, entries in by_image.items():
            image = d.load_image(img_id)
            sem = d.load_semantic_mask(img_id)
            ins = cv2.cvtColor(
                cv2.imread(str(root / "instance_masks" / f"{img_id}_instance_id_RGB.png")),
                cv2.COLOR_BGR2RGB)
            for rank, (agree, _, rec, gt) in entries:
                exact = np.all(ins == np.array(rec["instance_rgb"], np.uint8), axis=-1)
                clip = extract_gt_instance_mask(sem, gt)
                c = gt.obb_xyxyxyxy.reshape(4, 2)
                pad = int(max(np.ptp(c[:, 0]), np.ptp(c[:, 1])) * PAD) + 12
                x1 = max(0, int(c[:, 0].min()) - pad); y1 = max(0, int(c[:, 1].min()) - pad)
                x2 = min(image.shape[1], int(c[:, 0].max()) + pad)
                y2 = min(image.shape[0], int(c[:, 1].max()) + pad)
                fig = render(image[y1:y2, x1:x2], clip[y1:y2, x1:x2], exact[y1:y2, x1:x2],
                             gt.obb_xyxyxyxy, (x1, y1), agree,
                             {"image_id": img_id, "class_name": rec["class_name"]})
                fn = f"{rank:02d}_{rec['class_name']}_{img_id}_iou{agree:.3f}.png"
                cv2.imwrite(str(outdir / fn), cv2.cvtColor(fig, cv2.COLOR_RGB2BGR))
                print(f"  [{name}] {fn}", flush=True)

    print(f"\n{len(cases):,} instances compared over {len(ids)} images")
    print(f"figures -> {args.out}/(best|worst)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
