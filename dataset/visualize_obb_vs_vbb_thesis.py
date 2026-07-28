"""
Thesis-Quality OBB vs VBB Comparison Figure (Option B — 2-panel layout)

Produces a publication-ready side-by-side figure:
  LEFT panel  → Oriented Bounding Boxes (OBB) — tight, rotation-aware  [green]
  RIGHT panel → Vertical/Axis-Aligned Boxes  (VBB) — loose, background noise  [orange-red]

Usage
-----
  # Auto-select best rotated example from DOTA train split:
  python dataset/visualize_obb_vs_vbb_thesis.py --autoselect

  # Auto-select, prioritise specific classes:
  python dataset/visualize_obb_vs_vbb_thesis.py --autoselect --classes plane ship

  # Use a specific image:
  python dataset/visualize_obb_vs_vbb_thesis.py ^
      --image  dataset/DOTA_v1/train/images/P0000.png ^
      --labels dataset/DOTA_v1/train/labels/P0000.txt

  # Output to custom folder:
  python dataset/visualize_obb_vs_vbb_thesis.py --autoselect --outdir results/thesis_figures
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import Polygon as MplPolygon

# ─── colour palette ─────────────────────────────────────────────────────────
OBB_COLOUR  = "#2ecc40"   # bright green
VBB_COLOUR  = "#ff4136"   # vivid red-orange
TEXT_COLOUR_OBB = "#1a7a29"
TEXT_COLOUR_VBB = "#9b1406"

# ─── DOTA class names ────────────────────────────────────────────────────────
DOTA_CLASSES = [
    "plane", "ship", "storage-tank", "baseball-diamond", "tennis-court",
    "basketball-court", "ground-track-field", "harbor", "bridge",
    "large-vehicle", "small-vehicle", "helicopter", "roundabout",
    "soccer-ball-field", "swimming-pool",
]


# ─── label parsing ───────────────────────────────────────────────────────────

def parse_dota_labels(label_path: Path,
                      class_filter: Optional[list[str]] = None
                      ) -> list[dict]:
    """
    Parse a DOTA label file.
    Returns list of dicts with keys: class_name, points (4×2 float32 array).
    """
    items: list[dict] = []
    if not label_path.exists():
        return items

    with label_path.open("r", encoding="utf-8") as fh:
        for line in fh:
            parts = line.strip().split()
            if not parts or parts[0] in ("imagesource:", "gsd:"):
                continue
            if len(parts) < 9:
                continue
            try:
                coords = [float(v) for v in parts[:8]]
            except ValueError:
                continue
            class_name = parts[8]
            if class_filter and class_name not in class_filter:
                continue
            points = np.array(coords, dtype=np.float32).reshape(4, 2)
            items.append({"class_name": class_name, "points": points})

    return items


# ─── geometry helpers ────────────────────────────────────────────────────────

def obb_area(points: np.ndarray) -> float:
    """Shoelace formula area for a polygon."""
    x, y = points[:, 0], points[:, 1]
    return 0.5 * abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))


def vbb_from_obb(points: np.ndarray) -> tuple[float, float, float, float]:
    """Axis-aligned bounding box from OBB points: (x1, y1, x2, y2)."""
    return (float(points[:, 0].min()), float(points[:, 1].min()),
            float(points[:, 0].max()), float(points[:, 1].max()))


def vbb_area(points: np.ndarray) -> float:
    x1, y1, x2, y2 = vbb_from_obb(points)
    return (x2 - x1) * (y2 - y1)


def mean_area_ratio(labels: list[dict]) -> float:
    """Mean VBB_area / OBB_area across all labels (higher = more dramatic)."""
    ratios = []
    for lbl in labels:
        oa = obb_area(lbl["points"])
        if oa > 0:
            ratios.append(vbb_area(lbl["points"]) / oa)
    return float(np.mean(ratios)) if ratios else 1.0


# ─── auto-selection ──────────────────────────────────────────────────────────

def autoselect_image(label_dir: Path,
                     class_filter: Optional[list[str]],
                     top_n: int = 1,
                     min_objects: int = 3) -> list[Path]:
    """
    Scan all label files in label_dir.
    Score each by mean(VBB_area / OBB_area) on the filtered classes.
    Return the top_n label paths with the highest scores.
    """
    print(f"🔍  Scanning {label_dir} for best OBB vs VBB examples …")
    scored: list[tuple[float, Path]] = []

    label_files = sorted(label_dir.glob("*.txt"))
    if not label_files:
        print(f"[ERROR] No label files found in {label_dir}")
        sys.exit(1)

    for lf in label_files:
        labels = parse_dota_labels(lf, class_filter)
        if len(labels) < min_objects:
            continue
        ratio = mean_area_ratio(labels)
        scored.append((ratio, lf))

    if not scored:
        print("[ERROR] No suitable images found with given class filter "
              f"and min_objects={min_objects}.")
        sys.exit(1)

    scored.sort(key=lambda t: t[0], reverse=True)
    selected = [lf for _, lf in scored[:top_n]]

    for ratio, lf in scored[:top_n]:
        print(f"  ✅  {lf.stem}  —  mean VBB/OBB area ratio: {ratio:.2f}×")

    return selected


# ─── figure drawing ──────────────────────────────────────────────────────────

def draw_comparison(image_bgr: np.ndarray,
                    labels: list[dict],
                    image_name: str,
                    class_filter: Optional[list[str]],
                    outdir: Path,
                    dpi: int = 300) -> Path:
    """
    Build and save the 2-panel thesis figure.
    Returns the path of the saved file.
    """
    image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)

    # ── stats ────────────────────────────────────────────────────────────────
    ratios = [vbb_area(l["points"]) / max(obb_area(l["points"]), 1.0)
              for l in labels]
    mean_ratio = float(np.mean(ratios)) if ratios else 1.0
    extra_pct  = (mean_ratio - 1.0) * 100.0

    class_set = sorted({l["class_name"] for l in labels})
    class_str = ", ".join(class_set)

    # ── figure layout ────────────────────────────────────────────────────────
    fig, axes = plt.subplots(
        1, 2,
        figsize=(18, 9),
        dpi=dpi,
        constrained_layout=True,
        gridspec_kw={"wspace": 0.04}
    )

    fig.patch.set_facecolor("#f8f8f8")

    panel_titles = [
        "OBB — Oriented Bounding Boxes\n(tight, rotation-aware)",
        "VBB — Axis-Aligned Bounding Boxes\n(loose, background included)",
    ]
    panel_colours = [OBB_COLOUR, VBB_COLOUR]
    panel_text_colours = [TEXT_COLOUR_OBB, TEXT_COLOUR_VBB]

    for ax, title, colour, text_colour in zip(
            axes, panel_titles, panel_colours, panel_text_colours):

        ax.imshow(image_rgb)
        ax.set_aspect("equal")
        ax.axis("off")

        h, w = image_rgb.shape[:2]
        font_size = max(5, int(w / 120))

        for lbl in labels:
            pts = lbl["points"]
            cname = lbl["class_name"]

            if colour == OBB_COLOUR:
                # ── OBB panel: draw rotated polygon ─────────────────────────
                poly_patch = MplPolygon(
                    pts,
                    closed=True,
                    fill=False,
                    edgecolor=colour,
                    linewidth=1.8,
                    zorder=3,
                )
                ax.add_patch(poly_patch)
                # label at top-left corner of the OBB
                cx = pts[:, 0].min()
                cy = pts[:, 1].min() - 6
                ax.text(cx, cy, cname,
                        color=colour, fontsize=font_size,
                        fontweight="bold",
                        clip_on=True, zorder=4,
                        bbox=dict(facecolor="white", alpha=0.55,
                                  edgecolor="none", pad=1.5))
            else:
                # ── VBB panel: draw axis-aligned rectangle ───────────────────
                x1, y1, x2, y2 = vbb_from_obb(pts)
                rect = mpatches.FancyBboxPatch(
                    (x1, y1), x2 - x1, y2 - y1,
                    linewidth=1.8,
                    edgecolor=colour,
                    facecolor="none",
                    boxstyle="square,pad=0",
                    zorder=3,
                )
                ax.add_patch(rect)
                # label
                ax.text(x1, y1 - 6, cname,
                        color=colour, fontsize=font_size,
                        fontweight="bold",
                        clip_on=True, zorder=4,
                        bbox=dict(facecolor="white", alpha=0.55,
                                  edgecolor="none", pad=1.5))

        # panel title with coloured bar
        ax.set_title(title,
                     fontsize=13, fontweight="bold", color=colour,
                     pad=10,
                     bbox=dict(facecolor="white", edgecolor=colour,
                               linewidth=1.5, boxstyle="round,pad=0.4"))

    # ── figure-level subtitle ────────────────────────────────────────────────
    fig.suptitle(
        f"Image: {image_name}   ·   Objects shown: {len(labels)}"
        f"   ·   Classes: {class_str}\n"
        f"VBB boxes are on average {extra_pct:+.1f}% larger in area than OBB boxes"
        "  (additional background captured)",
        fontsize=10,
        color="#333333",
        y=0.01,
        va="bottom",
    )

    # ── save ─────────────────────────────────────────────────────────────────
    outdir.mkdir(parents=True, exist_ok=True)
    out_path = outdir / f"obb_vs_vbb_{image_name}.png"
    plt.savefig(str(out_path), dpi=dpi, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    plt.close(fig)

    return out_path


# ─── main ────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a thesis-quality OBB vs VBB 2-panel comparison figure.")

    src_group = parser.add_mutually_exclusive_group(required=True)
    src_group.add_argument(
        "--autoselect", action="store_true",
        help="Auto-scan DOTA_v1 train labels and pick the most dramatic example(s).")
    src_group.add_argument(
        "--image", type=str,
        help="Path to a specific DOTA image (.png).")

    parser.add_argument(
        "--labels", type=str, default=None,
        help="Path to the corresponding DOTA label file (required with --image).")
    parser.add_argument(
        "--label-dir", type=str,
        default="dataset/DOTA_v1/train/labels",
        help="Label directory to scan when --autoselect is used.")
    parser.add_argument(
        "--image-dir", type=str,
        default="dataset/DOTA_v1/train/images",
        help="Image directory matching the label directory.")
    parser.add_argument(
        "--classes", nargs="+", default=None,
        help="Filter to specific DOTA class names (e.g. --classes plane ship).")
    parser.add_argument(
        "--top-n", type=int, default=1,
        help="Number of best examples to generate when --autoselect is used (default: 1).")
    parser.add_argument(
        "--min-objects", type=int, default=3,
        help="Minimum number of matching objects for a valid image (default: 3).")
    parser.add_argument(
        "--outdir", type=str, default="results/thesis_figures",
        help="Output directory for the figure(s).")
    parser.add_argument(
        "--dpi", type=int, default=300,
        help="Figure resolution in DPI (default: 300).")

    args = parser.parse_args()
    outdir = Path(args.outdir)

    # ── collect (image_path, labels) pairs ───────────────────────────────────
    pairs: list[tuple[Path, list[dict]]] = []

    if args.autoselect:
        label_dir = Path(args.label_dir)
        image_dir = Path(args.image_dir)

        selected_label_paths = autoselect_image(
            label_dir,
            class_filter=args.classes,
            top_n=args.top_n,
            min_objects=args.min_objects,
        )

        for lf in selected_label_paths:
            img_path = image_dir / (lf.stem + ".png")
            if not img_path.exists():
                img_path = image_dir / (lf.stem + ".jpg")
            if not img_path.exists():
                print(f"[WARN] Image not found for label {lf.name} — skipping.")
                continue
            labels = parse_dota_labels(lf, class_filter=args.classes)
            pairs.append((img_path, labels))

    else:
        # manual image + labels
        img_path = Path(args.image)
        if args.labels is None:
            parser.error("--labels is required when using --image.")
        lbl_path = Path(args.labels)
        labels = parse_dota_labels(lbl_path, class_filter=args.classes)
        pairs.append((img_path, labels))

    if not pairs:
        print("[ERROR] No valid (image, labels) pairs found. Exiting.")
        sys.exit(1)

    # ── generate figure(s) ───────────────────────────────────────────────────
    for img_path, labels in pairs:
        if not labels:
            print(f"[WARN] No matching labels for {img_path.name} — skipping.")
            continue

        image_bgr = cv2.imread(str(img_path))
        if image_bgr is None:
            print(f"[ERROR] Could not read image: {img_path}")
            continue

        print(f"\n🖼️  Generating figure for {img_path.name}  "
              f"({len(labels)} objects) …")

        out = draw_comparison(
            image_bgr=image_bgr,
            labels=labels,
            image_name=img_path.stem,
            class_filter=args.classes,
            outdir=outdir,
            dpi=args.dpi,
        )

        ratios = [vbb_area(l["points"]) / max(obb_area(l["points"]), 1.0)
                  for l in labels]
        print(f"  ✅  Saved → {out}")
        print(f"      Objects: {len(labels)}  |  "
              f"Mean VBB/OBB area ratio: {np.mean(ratios):.2f}×  |  "
              f"Extra background: {(np.mean(ratios)-1)*100:+.1f}%")

    print("\nDone. 🎓")


if __name__ == "__main__":
    main()
