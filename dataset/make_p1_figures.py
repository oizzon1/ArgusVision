"""Render P1 Figures 1 and 4. INTERNAL TOOL.

Figure 1 — what the dataset *is*: one scene with paired oriented boxes and the
reconciled instance masks they delimit.

Figure 4 — why reconciliation was needed: the same object as DOTA annotates it
(oriented box), as iSAID annotates it (the raw instance, unclipped), and as
AerialFuseCV releases it (the instance clipped to its box). Harbor and
The two cases shown are chosen to be different in kind, not merely large:
baseball-diamond is a **convention difference** (DOTA annotates the infield,
iSAID the whole field), while the P0262 ship is an **iSAID annotation error** —
a single instance covering a boat, the dock it is moored to, and a second boat.
Harbor was tried first and dropped: its excess is only ~194 px, so the raw and
released masks look identical and the figure would understate the effect.

Figures 2, 5, 6, 7 already exist from the EDA run and are not regenerated here.

    python dataset/make_p1_figures.py
"""

import argparse
import collections
import json
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from argusvision.data.aerialfusecv import AerialFuseCVSplit  # noqa: E402

BOX_COLOUR = (255, 205, 0)      # DOTA oriented box
REL_COLOUR = (60, 220, 90)      # released (reconciled) mask
RAW_COLOUR = (70, 140, 255)     # raw iSAID instance, unclipped


def overlay(base, mask, colour, alpha=0.45):
    out = base.copy()
    sel = mask.astype(bool)
    if sel.any():
        out[sel] = (out[sel] * (1 - alpha) + np.array(colour, np.float32) * alpha).astype(np.uint8)
    return out


def outline(img, mask, colour, thickness=2):
    cnts, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL,
                               cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(img, cnts, -1, colour, thickness, cv2.LINE_AA)
    return img


def caption(panel, text, height=26):
    """Caption bar sized so the text always fits. OpenCV renders ASCII only —
    an em dash silently becomes '???', so text is transliterated first."""
    text = (text.replace("\u2014", "-").replace("\u2013", "-")
                .encode("ascii", "replace").decode("ascii"))
    w = panel.shape[1]
    scale = 0.52
    while scale > 0.28:
        (tw, _), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, scale, 1)
        if tw <= w - 16:
            break
        scale -= 0.02
    bar = np.zeros((height, w, 3), np.uint8)
    cv2.putText(bar, text, (8, height - 8), cv2.FONT_HERSHEY_SIMPLEX, scale,
                (255, 255, 255), 1, cv2.LINE_AA)
    return np.vstack([bar, panel])


def load_pairs(dataset: Path, split: str):
    by_image = collections.defaultdict(list)
    for line in open(dataset / "pairs.jsonl", encoding="utf-8"):
        r = json.loads(line)
        if r["split"] == split:
            by_image[r["image_id"]].append(r)
    return by_image


def raw_isaid_instance(isaid: Path, split: str, img_id: str, rgb):
    """The instance as iSAID drew it — before clipping to the box."""
    p = isaid / split / "instance_masks" / f"{img_id}_instance_id_RGB.png"
    ins = cv2.cvtColor(cv2.imread(str(p)), cv2.COLOR_BGR2RGB)
    return np.all(ins == np.array(rgb, np.uint8), axis=-1)


def figure_1(d, pairs, out: Path, split: str):
    """A scene with several well-separated objects of one category."""
    best = None
    for img_id, recs in pairs.items():
        counts = collections.Counter(r["class_name"] for r in recs)
        for cls, n in counts.items():
            if 6 <= n <= 14 and cls in ("plane", "ship", "storage-tank", "tennis-court"):
                areas = [r["instance_area_px"] for r in recs if r["class_name"] == cls]
                score = float(np.mean(areas))
                if best is None or score > best[0]:
                    best = (score, img_id, cls, n)
    if best is None:
        print("  figure 1: no suitable scene found"); return
    _, img_id, cls, n = best

    image = d.load_image(img_id)
    gts = d.load_ground_truth(img_id)
    masks = d.ground_truth_masks(img_id, gts)
    recs = pairs[img_id]

    sel = [i for i, r in enumerate(recs) if r["class_name"] == cls]
    pts_all = np.concatenate([np.array(recs[i]["obb"]).reshape(4, 2) for i in sel])
    pad = 140
    x1 = max(0, int(pts_all[:, 0].min()) - pad); y1 = max(0, int(pts_all[:, 1].min()) - pad)
    x2 = min(image.shape[1], int(pts_all[:, 0].max()) + pad)
    y2 = min(image.shape[0], int(pts_all[:, 1].max()) + pad)

    view = image[y1:y2, x1:x2].copy()
    for i in sel:
        m = masks[i][y1:y2, x1:x2]
        view = overlay(view, m, REL_COLOUR, 0.40)
        view = outline(view, m, REL_COLOUR, 2)
    for i in sel:
        p = (np.array(recs[i]["obb"]).reshape(4, 2) - [x1, y1]).round().astype(np.int32)
        cv2.polylines(view, [p], True, BOX_COLOUR, 2, cv2.LINE_AA)

    fig = caption(view, f"{img_id} — {n} paired {cls} instances   "
                        f"yellow: DOTA oriented box   green: released mask")
    cv2.imwrite(str(out / "F1_paired_example.png"), cv2.cvtColor(fig, cv2.COLOR_RGB2BGR))
    print(f"  figure 1: {img_id} ({n} x {cls})")


def pick_divergence_cases(d, pairs, isaid: Path, split: str, scan: int, top: int):
    """Choose the cases by measured excess rather than by hand.

    Hand-picking drifted once already: a case chosen from an earlier build
    matched a different instance after rematching, leaving the figure caption
    describing something the panel no longer showed.
    """
    found = []
    for n, img_id in enumerate(list(pairs)[:scan], 1):
        gts = d.load_ground_truth(img_id)
        recs = pairs[img_id]
        if len(gts) != len(recs):
            continue
        released_all = d.ground_truth_masks(img_id, gts)
        ins = cv2.cvtColor(cv2.imread(str(isaid / split / "instance_masks" /
                                          f"{img_id}_instance_id_RGB.png")), cv2.COLOR_BGR2RGB)
        for rec, rel in zip(recs, released_all):
            raw = np.all(ins == np.array(rec["instance_rgb"], np.uint8), axis=-1)
            excess = int((raw & ~rel).sum())
            if excess > 0:
                found.append((excess, rec["class_name"], img_id))
        if n % 20 == 0:
            print(f"  scanning {n}/{scan}", flush=True)
    found.sort(reverse=True)
    chosen, seen = [], set()
    for excess, cls, img_id in found:
        if cls in seen:
            continue
        chosen.append((cls, img_id)); seen.add(cls)
        if len(chosen) == top:
            break
    print(f"  cases by measured excess: {chosen}")
    return chosen


def figure_4(d, pairs, isaid: Path, out: Path, split: str, cases):
    """Box vs raw iSAID instance vs released mask, for the clearest divergences."""
    panels, measurements = [], []
    for want_cls, want_img in cases:
        recs = pairs.get(want_img, [])
        idx = next((i for i, r in enumerate(recs) if r["class_name"] == want_cls), None)
        if idx is None:
            print(f"  figure 4: {want_cls} not found in {want_img}"); continue
        rec = recs[idx]
        image = d.load_image(want_img)
        gts = d.load_ground_truth(want_img)
        released = d.ground_truth_masks(want_img, gts)[idx]
        raw = raw_isaid_instance(isaid, split, want_img, rec["instance_rgb"])

        ys, xs = np.nonzero(raw | released)
        pad = 70
        x1 = max(0, xs.min() - pad); y1 = max(0, ys.min() - pad)
        x2 = min(image.shape[1], xs.max() + pad); y2 = min(image.shape[0], ys.max() + pad)
        crop = image[y1:y2, x1:x2]
        box = (np.array(rec["obb"]).reshape(4, 2) - [x1, y1]).round().astype(np.int32)

        a = crop.copy(); cv2.polylines(a, [box], True, BOX_COLOUR, 2, cv2.LINE_AA)
        b = overlay(crop, raw[y1:y2, x1:x2], RAW_COLOUR, 0.45)
        cv2.polylines(b, [box], True, BOX_COLOUR, 2, cv2.LINE_AA)
        c = overlay(crop, released[y1:y2, x1:x2], REL_COLOUR, 0.45)
        cv2.polylines(c, [box], True, BOX_COLOUR, 2, cv2.LINE_AA)

        excess = int((raw & ~released).sum())
        # Every number rendered into a caption is also written to results/ —
        # a figure is not a licence to invent a value (LESSONS C5).
        measurements.append({"image_id": want_img, "class_name": want_cls,
                             "excess_px": excess,
                             "released_px": int(released.sum()),
                             "raw_px": int(raw.sum())})
        row = np.hstack([caption(a, "DOTA oriented box"),
                         caption(b, f"iSAID raw instance (+{excess:,} px)"),
                         caption(c, "AerialFuseCV released mask")])
        panels.append(caption(row, f"{want_img} — {want_cls}", 30))

    if measurements:
        (out / "figure_values.json").write_text(
            json.dumps({"released_masks_from": str(d.root), "raw_masks_from": str(isaid),
                        "split": split,
                        "cases": measurements}, indent=2), encoding="utf-8")

    if panels:
        # Rows come from different crops, so scale each to a common width rather
        # than padding — padding leaves the smaller row visually adrift.
        w = max(p.shape[1] for p in panels)
        panels = [p if p.shape[1] == w else
                  cv2.resize(p, (w, int(p.shape[0] * w / p.shape[1])),
                             interpolation=cv2.INTER_AREA)
                  for p in panels]
        panels = [np.pad(p, ((0, 12), (0, 0), (0, 0))) for p in panels]
        cv2.imwrite(str(out / "F4_source_divergence.png"),
                    cv2.cvtColor(np.vstack(panels), cv2.COLOR_RGB2BGR))
        print(f"  figure 4: {len(panels)} case(s)")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", type=Path, default=Path("dataset/AerialFuseCV"))
    ap.add_argument("--isaid", type=Path, default=Path("dataset/iSAID"))
    ap.add_argument("--split", default="val")
    ap.add_argument("--scan", type=int, default=120, help="images to scan for divergence cases")
    ap.add_argument("--top", type=int, default=2)
    ap.add_argument("--out", type=Path,
                    default=Path("results/experimental/AerialFuseCV_Testing/eda/figures"))
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    d = AerialFuseCVSplit(str(args.dataset / args.split))
    pairs = load_pairs(args.dataset, args.split)
    print(f"{len(pairs)} images with pairs in {args.split}")

    figure_1(d, pairs, args.out, args.split)
    cases = pick_divergence_cases(d, pairs, args.isaid, args.split,
                                  args.scan, args.top)
    figure_4(d, pairs, args.isaid, args.out, args.split, cases)
    print(f"figures -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
