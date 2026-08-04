"""Render P1 Figure 3 — the construction pipeline. INTERNAL TOOL.

A schematic, not a data render, but every number on it is read from
`dataset_statistics.json` rather than typed in, so the diagram cannot drift
from the build it describes.

The figure shows the funnel as it actually is: two sources entering, a
one-to-one match on the oriented polygon, and two discard streams leaving —
2,121 boxes with no acceptable instance and 349,716 instances with no box. The
second stream is the large one, and showing it is the point: AerialFuseCV is
the *intersection* of two annotation sets, not a superset of either.

    python dataset/make_pipeline_figure.py
"""

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import textwrap

from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

SRC = "#4C72B0"      # source datasets
PROC = "#55A868"     # processing stages
OUT = "#2F4B7C"      # released artefact
DROP = "#C44E52"     # discard streams


def box(ax, x, y, w, h, text, colour, fontsize=9, text_colour="white"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.012",
                                linewidth=0, facecolor=colour))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
            fontsize=fontsize, color=text_colour, linespacing=1.45)


def arrow(ax, x1, y1, x2, y2, colour="#444444", style="-|>", lw=1.6, ls="-"):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle=style,
                                 mutation_scale=13, linewidth=lw,
                                 color=colour, linestyle=ls,
                                 shrinkA=2, shrinkB=2))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stats", type=Path,
                    default=Path("dataset/AerialFuseCV/dataset_statistics.json"))
    ap.add_argument("--out", type=Path,
                    default=Path("results/experimental/AerialFuseCV_Testing/eda/figures"))
    args = ap.parse_args()

    s = json.loads(args.stats.read_text(encoding="utf-8"))
    t, dis = s["totals"], s["discarded"]
    thr = s["iou_threshold"]

    fig, ax = plt.subplots(figsize=(11.5, 6.4))
    ax.set_xlim(0, 100); ax.set_ylim(0, 60); ax.axis("off")

    # --- sources -----------------------------------------------------------
    box(ax, 2, 44, 25, 11,
        f"DOTA v1.0\noriented boxes\n{t['boxes']:,} boxes / {t['images_seen']:,} images", SRC)
    box(ax, 2, 24, 25, 11,
        f"iSAID\nper-instance masks\n{t['src_instances']:,} instances", SRC)

    # --- stages ------------------------------------------------------------
    box(ax, 34, 34, 24, 11,
        f"Decode instances\nclass from semantic mask\nat the instance's own pixels", PROC)
    box(ax, 64, 34, 24, 11,
        f"Match one-to-one\nIoU of oriented polygon\nvs instance, >= {thr}", PROC)
    # The definition is read from the build, so its length is not ours to
    # control — wrap it rather than let it overflow the box.
    definition = textwrap.fill(s["mask_definition"], width=30)
    box(ax, 64, 13, 24, 13, f"Clip to the box\n{definition}", PROC, fontsize=7.6)

    # --- output ------------------------------------------------------------
    box(ax, 34, 4, 24, 12,
        f"AerialFuseCV\n{t['pairs']:,} paired instances\n{t['images_kept']:,} images", OUT,
        fontsize=10)

    # --- flows -------------------------------------------------------------
    arrow(ax, 27, 49.5, 34, 43)      # DOTA -> decode
    arrow(ax, 27, 29.5, 34, 37)      # iSAID -> decode
    arrow(ax, 58, 39.5, 64, 39.5)    # decode -> match
    arrow(ax, 76, 34, 76, 26)        # match -> clip
    arrow(ax, 64, 19.5, 58, 12)      # clip -> output  (unchanged)

    # --- discards ----------------------------------------------------------
    box(ax, 91, 39, 8, 8,
        f"{dis['boxes']:,}\nboxes", DROP, fontsize=8)
    box(ax, 91, 17, 8, 10,
        f"{dis['instances']:,}\ninstances", DROP, fontsize=8)
    arrow(ax, 88, 41, 91, 43, DROP, ls=(0, (3, 2)))
    arrow(ax, 88, 24, 91, 22, DROP, ls=(0, (3, 2)))
    ax.text(95, 36.5, "no acceptable\ninstance", ha="center", va="top",
            fontsize=7.5, color=DROP)
    ax.text(95, 14.5, "no corresponding\nbox", ha="center", va="top",
            fontsize=7.5, color=DROP)

    excluded = t["images_excluded"]
    ax.text(46, 1.2,
            f"{excluded} images retained no pair and were excluded. "
            f"Discarded streams are reported per class and per reason in discarded.jsonl.",
            ha="center", va="bottom", fontsize=7.8, color="#555555")

    ax.text(50, 58, "AerialFuseCV construction", ha="center", va="top",
            fontsize=13)

    args.out.mkdir(parents=True, exist_ok=True)
    dst = args.out / "F3_construction_pipeline.png"
    fig.savefig(dst, dpi=200, bbox_inches="tight", facecolor="white")
    print(f"figure 3 -> {dst}")
    print(f"  sources {t['boxes']:,} boxes / {t['src_instances']:,} instances")
    print(f"  output  {t['pairs']:,} pairs over {t['images_kept']:,} images")
    print(f"  dropped {dis['boxes']:,} boxes, {dis['instances']:,} instances")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
