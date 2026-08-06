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
from scipy import ndimage

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


divergence_kinds = ("extent", "split", "foreign")

KIND_TITLE = {
    "extent": "Extent — the sources annotate different amounts of the same object",
    "split": "Source error — one iSAID instance spans several physical objects",
    "foreign": "Contamination — a neighbour's pixels fall inside the box",
    "gallery": "Box and mask disagree",
}


def pick_divergence_cases(d, pairs, isaid: Path, split: str, scan: int, top: int,
                          gallery: int = 5):
    """Choose cases by measured property rather than by hand, one set per kind.

    Hand-picking drifted once already: a case chosen from an earlier build
    matched a different instance after rematching, leaving the figure caption
    describing something the panel no longer showed. Selection here is driven
    entirely by quantities measured during the scan, so a changed build changes
    the chosen cases rather than silently invalidating the caption.

    The three kinds are the same decomposition the data article's disagreement
    table uses, so a figure illustrates a row of that table rather than merely
    being a striking picture:

      extent   raw instance reaches well beyond the box, in ONE connected
               piece — a protocol difference about how much of an object to
               annotate, not an error by either source
      split    the instance colour spans several disconnected components — one
               iSAID instance covering more than one physical object
      foreign  pixels inside the box carry a DIFFERENT instance identity — a
               neighbour bleeding into the clip, concentrated in dense scenes
    """
    found = {k: [] for k in divergence_kinds + ("gallery",)}
    for n, img_id in enumerate(list(pairs)[:scan], 1):
        recs = pairs[img_id]
        ins = cv2.cvtColor(cv2.imread(str(isaid / split / "instance_masks" /
                                          f"{img_id}_instance_id_RGB.png")), cv2.COLOR_BGR2RGB)
        ik = (ins[:, :, 0].astype(np.int32) << 16) | \
             (ins[:, :, 1].astype(np.int32) << 8) | ins[:, :, 2].astype(np.int32)
        h, w = ik.shape

        # Locate every instance ONCE per image. Comparing the whole mask per
        # pair, and labelling it per pair, is cost = pairs x image pixels —
        # the defect this project already paid for once (LESSONS D6). Here it
        # made the scan slow enough to halve its own throughput on dense val
        # images.
        uniq, inv = np.unique(ik, return_inverse=True)
        boxes_of = ndimage.find_objects(inv.reshape(h, w) + 1)
        where = {int(k): i for i, k in enumerate(uniq.tolist())}

        for rec_idx, rec in enumerate(recs):
            c = rec["instance_rgb"]
            key = (int(c[0]) << 16) | (int(c[1]) << 8) | int(c[2])
            slot = where.get(key)
            if slot is None or boxes_of[slot] is None:
                continue
            sy, sx = boxes_of[slot]

            # window = instance extent U box extent, so everything below is
            # local to the object rather than to the image
            pts = np.round(np.array(rec["obb"]).reshape(4, 2)).astype(np.int32)
            y1 = max(0, min(sy.start, int(pts[:, 1].min())))
            y2 = min(h, max(sy.stop, int(pts[:, 1].max()) + 1))
            x1 = max(0, min(sx.start, int(pts[:, 0].min())))
            x2 = min(w, max(sx.stop, int(pts[:, 0].max()) + 1))
            sub = ik[y1:y2, x1:x2]

            raw = sub == key
            poly = np.zeros((y2 - y1, x2 - x1), np.uint8)
            cv2.fillPoly(poly, [pts - [x1, y1]], 1)
            inside = poly > 0
            # released mask = instance clipped to its box, with the build's
            # documented fallback to the whole instance when the clip is empty
            rel = raw & inside
            if not rel.any():
                rel = raw
            excess = int((raw & ~rel).sum())
            _, pieces = ndimage.label(raw)
            foreign = int((inside & (sub != 0) & (sub != key)).sum())

            # Every kind requires visible divergence. A 59-piece instance lying
            # entirely inside its box is a true multi-piece case and a useless
            # picture; ranking by piece count alone selected exactly that.
            # The record INDEX travels with the case. Identifying a case only
            # by (class, image) let the figure render the first object of that
            # class instead of the measured one — in an image with 43 harbours,
            # never the right one — so the caption described a different object
            # than the panel showed.
            if pieces > 1 and excess > 0:
                found["split"].append((excess, rec["class_name"], img_id,
                                       {"idx": rec_idx, "pieces": int(pieces)}))
            if pieces == 1 and excess > 0:
                found["extent"].append((excess, rec["class_name"], img_id,
                                        {"idx": rec_idx, "pieces": 1}))
            if foreign > 0:
                found["foreign"].append((foreign, rec["class_name"], img_id,
                                         {"idx": rec_idx, "foreign_px": foreign}))

            # Gallery: candidates for hand-composing a divergence figure.
            # Ranked by absolute excess so the disagreement is large enough to
            # read at figure size, but gated on the ratio so a huge object with
            # a proportionally trivial overhang does not crowd out a small one
            # that is plainly wrong.
            inside = int(rel.sum())
            if inside > 0 and excess > 0:
                ratio = excess / inside
                if ratio >= 0.20:
                    found["gallery"].append(
                        (excess, rec["class_name"], img_id,
                         {"idx": rec_idx, "pieces": int(pieces),
                          "outside_over_inside": round(ratio, 4)}))
        if n % 20 == 0:
            print(f"  scanning {n}/{scan}", flush=True)

    # Rarest kind picks first, and a class used anywhere is not reused. Six
    # panels drawn from three categories illustrate those categories, not the
    # three phenomena the figures exist to separate.
    chosen, used = {}, set()
    for kind in ("split", "foreign", "extent"):
        found[kind].sort(key=lambda t: -t[0])
        picked = []
        for _, cls, img_id, extra in found[kind]:
            if cls in used:
                continue
            picked.append((cls, img_id, extra)); used.add(cls)
            if len(picked) == top:
                break
        chosen[kind] = picked
        print(f"  {kind:8} cases: {[(c, i) for c, i, _ in picked]}", flush=True)

    # Gallery picks independently of the three figures and may reuse their
    # classes — it exists to give the widest choice for hand-composition, not
    # to illustrate a taxonomy. One case per class still, for variety.
    found["gallery"].sort(key=lambda t: -t[0])
    gal, seen = [], set()
    for _, cls, img_id, extra in found["gallery"]:
        if cls in seen:
            continue
        gal.append((cls, img_id, extra)); seen.add(cls)
        if len(gal) == gallery:
            break
    chosen["gallery"] = gal
    print(f"  gallery  cases: {[(c, i) for c, i, _ in gal]}", flush=True)
    return chosen


def figure_4(d, pairs, isaid: Path, out: Path, split: str, cases,
             kind="extent", filename="F4_source_divergence.png"):
    """Box vs raw iSAID instance vs released mask, for one kind of divergence.

    Returns the measurement records so the caller can write every rendered
    number to results/ in a single file.
    """
    panels, measurements = [], []
    for want_cls, want_img, extra in cases:
        recs = pairs.get(want_img, [])
        idx = extra.get("idx")
        if idx is None or idx >= len(recs) or recs[idx]["class_name"] != want_cls:
            print(f"  figure 4: case {want_cls}/{want_img} no longer resolves"); continue
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
        # released is the instance clipped to its box, so released + excess must
        # equal raw. When it did not, the panel and its caption were describing
        # two different objects — the failure this check exists to surface.
        if int(released.sum()) + excess != int(raw.sum()):
            print(f"  WARNING {want_img}/{want_cls}: released {int(released.sum()):,}"
                  f" + excess {excess:,} != raw {int(raw.sum()):,} — panel and "
                  f"measurement disagree, case skipped")
            continue
        # Every number rendered into a caption is also written to results/ —
        # a figure is not a licence to invent a value (LESSONS C5).
        measurements.append({"kind": kind, "figure": filename,
                             "image_id": want_img, "class_name": want_cls,
                             "excess_px": excess,
                             "released_px": int(released.sum()),
                             "raw_px": int(raw.sum()), **extra})
        if kind == "split":
            note = f"iSAID raw instance ({extra.get('pieces', '?')} pieces, +{excess:,} px)"
        elif kind == "foreign":
            note = f"iSAID raw instance (+{excess:,} px; {extra.get('foreign_px', 0):,} foreign px in box)"
        else:
            note = f"iSAID raw instance (+{excess:,} px)"
        row = np.hstack([caption(a, "DOTA oriented box"),
                         caption(b, note),
                         caption(c, "AerialFuseCV released mask")])
        panels.append(caption(row, f"{want_img} — {want_cls}", 30))

    if panels:
        # Rows come from different crops, so scale each to a common width rather
        # than padding — padding leaves the smaller row visually adrift.
        w = max(p.shape[1] for p in panels)
        panels = [p if p.shape[1] == w else
                  cv2.resize(p, (w, int(p.shape[0] * w / p.shape[1])),
                             interpolation=cv2.INTER_AREA)
                  for p in panels]
        panels = [np.pad(p, ((0, 12), (0, 0), (0, 0))) for p in panels]
        stacked = np.vstack(panels)
        stacked = caption(stacked, KIND_TITLE.get(kind, kind), 34)
        cv2.imwrite(str(out / filename), cv2.cvtColor(stacked, cv2.COLOR_RGB2BGR))
        print(f"  {filename}: {len(panels)} case(s)")
    return measurements


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", type=Path, default=Path("dataset/AerialFuseCV"))
    ap.add_argument("--isaid", type=Path, default=Path("dataset/iSAID"))
    ap.add_argument("--split", default="val")
    ap.add_argument("--scan", type=int, default=300,
                    help="images to scan for divergence cases; three kinds now "
                         "compete for candidates, and split cases are rare "
                         "(~0.5%% of pairs), so this is wider than it was")
    ap.add_argument("--top", type=int, default=2)
    ap.add_argument("--gallery", type=int, default=5,
                    help="extra single-case panels of large box/mask "
                         "disagreement, written one file each for "
                         "hand-composition into a figure")
    ap.add_argument("--out", type=Path,
                    default=Path("results/experimental/AerialFuseCV_Testing/eda/figures"))
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    d = AerialFuseCVSplit(str(args.dataset / args.split))
    pairs = load_pairs(args.dataset, args.split)
    print(f"{len(pairs)} images with pairs in {args.split}")

    figure_1(d, pairs, args.out, args.split)
    cases = pick_divergence_cases(d, pairs, args.isaid, args.split,
                                  args.scan, args.top, args.gallery)

    # Three candidate divergence figures, one per measured kind, so the best
    # can be chosen for the article rather than settled on by whichever was
    # rendered first.
    files = {"extent": "F4a_source_divergence_extent.png",
             "split":  "F4b_source_divergence_split.png",
             "foreign": "F4c_source_divergence_foreign.png"}
    all_measurements = []
    for kind in divergence_kinds:
        if not cases.get(kind):
            print(f"  {kind}: no case found in the scanned images")
            continue
        all_measurements += figure_4(d, pairs, args.isaid, args.out, args.split,
                                     cases[kind], kind, files[kind])

    # One file per gallery case, so they can be arranged by hand rather than
    # accepting whatever layout this script happens to stack.
    gal_dir = args.out / "divergence_gallery"
    for n, case in enumerate(cases.get("gallery", []), 1):
        cls, img, _ = case
        gal_dir.mkdir(parents=True, exist_ok=True)
        all_measurements += figure_4(
            d, pairs, args.isaid, gal_dir, args.split, [case],
            "gallery", f"G{n}_{cls}_{img}.png")

    if all_measurements:
        (args.out / "figure_values.json").write_text(
            json.dumps({"released_masks_from": str(d.root),
                        "raw_masks_from": str(args.isaid),
                        "split": args.split, "scanned_images": args.scan,
                        "cases": all_measurements}, indent=2), encoding="utf-8")
    print(f"figures -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
