#!/usr/bin/env python3
"""Render the alignment-audit review interface as a paper figure. INTERNAL TOOL.

The figure shows the screen a reviewer actually sees: one sampled pair, the DOTA
box alone beside the same view with the released mask overlaid, and the three
outcomes. It is composed from the same rendering path the audit itself uses and
from a pair that was genuinely in the sample, so it depicts the instrument
rather than illustrating it.

    python dataset/make_audit_figure.py --pair-id "val:P0259:104216"
"""

import argparse
import json
import sys
from pathlib import Path

try:
    import cv2
    import numpy as np
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch
except ImportError:  # pragma: no cover
    sys.exit("needs numpy, opencv-python and matplotlib")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_alignment_audit import render_pair, BOX_COLOUR, MASK_COLOUR  # noqa: E402

BG = "#15181c"
FG = "#dfe4ea"
MUTED = "#8b95a1"


def decode(uri):
    import base64
    raw = base64.b64decode(uri.split(",", 1)[1])
    img = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)
    return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", type=Path, default=Path("dataset/AerialFuseCV"))
    ap.add_argument("--audit", type=Path,
                    default=Path("results/experimental/AerialFuseCV_Testing/alignment_audit"))
    ap.add_argument("--pair-id", help="id from sample_manifest.json; default = first plane")
    ap.add_argument("--out", type=Path,
                    default=Path("results/experimental/AerialFuseCV_Testing/eda/figures/"
                                 "F8_alignment_audit_interface.png"))
    args = ap.parse_args()

    man = json.loads((args.audit / "sample_manifest.json").read_text(encoding="utf-8"))
    items = man["items"]
    if args.pair_id:
        chosen = next((i for i in items if i["id"] == args.pair_id), None)
        if chosen is None:
            sys.exit(f"{args.pair_id} not in the sample")
    else:
        # a mid-band case: representative of the judgement, not the easiest one
        mid = [i for i in items if i["band"] in (2, 3)]
        chosen = mid[0] if mid else items[0]

    split, img_id, idx = chosen["id"].split(":")
    idx = int(idx)
    rec = None
    for n, line in enumerate(open(args.dataset / "pairs.jsonl", encoding="utf-8")):
        if n == idx:
            rec = json.loads(line)
            break
    if rec is None:
        sys.exit("pair record not found")

    img = cv2.cvtColor(cv2.imread(str(args.dataset / split / "images" / f"{img_id}.png")),
                       cv2.COLOR_BGR2RGB)
    ins = cv2.cvtColor(cv2.imread(str(args.dataset / split / "instance_masks" /
                                      f"{img_id}_instance_id_RGB.png")), cv2.COLOR_BGR2RGB)
    uri = render_pair(img, ins, rec)
    if uri is None:
        sys.exit("could not render that pair")
    panel = decode(uri)

    h, w = panel.shape[:2]
    fig_w = 9.0
    fig_h = fig_w * (h / w) + 2.5
    fig = plt.figure(figsize=(fig_w, fig_h), facecolor=BG)

    # header
    fig.text(0.035, 1 - 0.30 / fig_h, "Alignment audit", color=FG,
             fontsize=11, fontweight="bold", va="top")
    fig.text(0.965, 1 - 0.30 / fig_h, "83 / 200", color=MUTED,
             fontsize=10, va="top", ha="right")
    bar_y = 1 - 0.62 / fig_h
    fig.patches.append(plt.Rectangle((0.035, bar_y), 0.93, 0.007,
                                     transform=fig.transFigure, color="#262b31", zorder=2))
    fig.patches.append(plt.Rectangle((0.035, bar_y), 0.93 * 83 / 200, 0.007,
                                     transform=fig.transFigure, color="#4a9eff", zorder=3))

    ax = fig.add_axes([0.035, (1.55 / fig_h), 0.93, 1 - (2.45 / fig_h)])
    ax.imshow(panel)
    ax.axis("off")
    for s in ax.spines.values():
        s.set_visible(False)

    # swatch then label, laid out left to right so nothing overlaps
    lb = 1.30 / fig_h
    hexof = lambda c: f"#{c[0]:02x}{c[1]:02x}{c[2]:02x}"
    legend = [(hexof(BOX_COLOUR), "DOTA oriented box"),
              (hexof(MASK_COLOUR), "released mask")]
    x = 0.335
    for colour, label in legend:
        fig.patches.append(plt.Rectangle((x, lb - 0.0035), 0.010, 0.0085,
                                         transform=fig.transFigure,
                                         color=colour, zorder=4))
        fig.text(x + 0.017, lb, label, color=MUTED, fontsize=8.5,
                 ha="left", va="center")
        x += 0.017 + 0.011 * len(label) + 0.035

    fig.text(0.5, 0.95 / fig_h,
             "Do the box and the mask describe the same physical object?",
             color="#aab3bf", fontsize=9.5, ha="center")

    buttons = [("Same object   1", "#16301f", "#2f7d4f"),
               ("Wrong object   2", "#301818", "#8a3b3b"),
               ("Ambiguous   3", "#2c2716", "#7a6a2f")]
    bw, gap = 0.205, 0.022
    x0 = 0.5 - (len(buttons) * bw + (len(buttons) - 1) * gap) / 2
    by, bh = 0.30 / fig_h, 0.42 / fig_h
    for i, (label, fill, edge) in enumerate(buttons):
        x = x0 + i * (bw + gap)
        fig.patches.append(FancyBboxPatch((x, by), bw, bh,
                                          boxstyle="round,pad=0.004,rounding_size=0.012",
                                          transform=fig.transFigure,
                                          facecolor=fill, edgecolor=edge,
                                          linewidth=1.1, zorder=4))
        fig.text(x + bw / 2, by + bh / 2, label, color=FG, fontsize=9.5,
                 fontweight="bold", ha="center", va="center", zorder=5)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.out, dpi=170, facecolor=BG)
    plt.close(fig)
    print(f"figure -> {args.out}")
    print(f"  pair {chosen['id']}  class={chosen['class_name']}  "
          f"IoU={chosen['iou']:.4f}  band={chosen['band']}")

    (args.out.parent / "F8_values.json").write_text(json.dumps({
        "figure": args.out.name,
        "depicts": "the alignment-audit review interface",
        "pair_id": chosen["id"], "class_name": chosen["class_name"],
        "iou": chosen["iou"], "band": chosen["band"],
        "note": "Rendered through the same code path the audit uses, from a pair "
                "that was genuinely in the sample. The progress counter shown "
                "(83/200) is illustrative of a review in progress.",
    }, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
