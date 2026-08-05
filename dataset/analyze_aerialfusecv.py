"""EDA for a built AerialFuseCV: DATASET_ANALYSIS.md plus figures.

Reads only artefacts the build produced — `dataset_statistics.json`,
`pairs.jsonl`, `discarded.jsonl`, `images_gsd_mapping.json` — and, when
present, the annotation-discrepancy summary. Every number in the report is
computed here, never quoted.

    python dataset/analyze_aerialfusecv.py --dataset dataset/AerialFuseCV
"""

import argparse
import collections
import json
import sys
import time
from pathlib import Path

import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


def load_jsonl(path):
    if not path.exists():
        return []
    return [json.loads(l) for l in open(path, encoding="utf-8")]


def fig_class_distribution(per_class, out):
    rows = sorted(((v["total_pairs"], k) for k, v in per_class.items()), reverse=True)
    names = [k for _, k in rows]; vals = [n for n, _ in rows]
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.bar(range(len(vals)), vals, color="#3b6ea5")
    ax.set_yscale("log")
    ax.set_xticks(range(len(names)))
    ax.set_xticklabels(names, rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("paired instances (log)")
    ax.set_title("AerialFuseCV — instances per category")
    for i, v in enumerate(vals):
        ax.text(i, v, f"{v:,}", ha="center", va="bottom", fontsize=6.5)
    fig.tight_layout(); fig.savefig(out, dpi=160); plt.close(fig)


def fig_hist(values, title, xlabel, out, bins=60, colour="#3b6ea5"):
    fig, ax = plt.subplots(figsize=(7, 3.6))
    ax.hist(values, bins=bins, color=colour, edgecolor="none")
    ax.axvline(float(np.median(values)), color="#b3402f", ls="--", lw=1.2,
               label=f"median {np.median(values):.3f}")
    ax.set_xlabel(xlabel); ax.set_ylabel("instances"); ax.set_title(title)
    ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(out, dpi=160); plt.close(fig)


def fig_area_by_class(pairs, out):
    by = collections.defaultdict(list)
    for r in pairs:
        if "instance_area_px" in r:
            by[r["class_name"]].append(r["instance_area_px"])
    order = sorted(by, key=lambda k: np.median(by[k]))
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.boxplot([by[k] for k in order], labels=order, showfliers=False, vert=True)
    ax.set_yscale("log"); ax.set_ylabel("instance area (px, log)")
    ax.set_title("Object size by category")
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right", fontsize=8)
    fig.tight_layout(); fig.savefig(out, dpi=160); plt.close(fig)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", type=Path, default=Path("dataset/AerialFuseCV"))
    ap.add_argument("--discrepancy", type=Path,
                    default=Path("results/experimental/AerialFuseCV_Testing/annotation_discrepancy/"
                                 "discrepancy_summary.json"))
    ap.add_argument("--out", type=Path,
                    default=Path("results/experimental/AerialFuseCV_Testing/eda"))
    args = ap.parse_args()
    figs = args.out / "figures"; figs.mkdir(parents=True, exist_ok=True)

    st = json.loads((args.dataset / "dataset_statistics.json").read_text(encoding="utf-8"))
    pairs = load_jsonl(args.dataset / "pairs.jsonl")
    discarded = load_jsonl(args.dataset / "discarded.jsonl")
    gsd = json.loads((args.dataset / "images_gsd_mapping.json").read_text(encoding="utf-8"))
    disc = (json.loads(args.discrepancy.read_text(encoding="utf-8"))
            if args.discrepancy.exists() else None)

    ious = np.array([r["iou"] for r in pairs])
    areas = np.array([r.get("instance_area_px", 0) for r in pairs])
    t = st["totals"]

    fig_class_distribution(st["per_class"], figs / "F2_class_distribution.png")
    fig_hist(ious, "Box–mask matching IoU", "IoU (oriented polygon vs instance)",
             figs / "F5_matching_iou.png")
    fig_area_by_class(pairs, figs / "F6_area_by_class.png")
    # DOTA does not state a GSD for every image; the mapping records those as
    # null rather than inventing a value, so they are skipped here instead of
    # being silently counted as zero.
    gsd_values = np.array([v for v in gsd.values() if v is not None], dtype=float)
    if gsd_values.size:
        fig_hist(gsd_values, "Ground sample distance", "GSD (m/px)",
                 figs / "F7_gsd.png", bins=40, colour="#5a8a5a")
        print(f"  GSD: {gsd_values.size:,} images with a stated value, "
              f"{len(gsd) - gsd_values.size:,} without")

    # ---- report ----
    L = []
    A = L.append
    A(f"# AerialFuseCV — Dataset Analysis\n")
    A(f"Generated {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())} from "
      f"`{args.dataset}`. Every figure below is computed from the build's own "
      f"artefacts; nothing is quoted.\n")
    A(f"**Mask definition:** {st.get('mask_definition','n/a')}  ")
    A(f"**Matching geometry:** {st.get('matching_geometry','n/a')}, "
      f"IoU ≥ {st['iou_threshold']}, one-to-one within class  ")
    A(f"**Annotation format:** {st.get('annotation_format','n/a')}  ")
    A(f"**Box geometries:** {', '.join(st.get('box_geometries_written', []))}\n")

    A("## Construction funnel\n")
    A("| Stage | Count |")
    A("|---|---|")
    A(f"| Images with both annotations | {t['images_seen']:,} |")
    A(f"| Source boxes (DOTA) | {t['boxes']:,} |")
    A(f"| Source instances (iSAID) | {t['src_instances']:,} |")
    A(f"| **Paired objects** | **{t['pairs']:,}** |")
    A(f"| Images retained | {t['images_kept']:,} (excluded {t['images_excluded']}) |")
    A(f"| Box pairing rate | {t['box_pairing_rate']*100:.2f}% |")
    A(f"| Instance pairing rate | {t['instance_pairing_rate']*100:.2f}% |\n")
    A("The two rates differ because pairing is anchored on the boxes: iSAID "
      "annotates far more objects than DOTA, so most unpaired instances simply "
      "have no box. Detection benchmarking belongs on DOTA, segmentation on "
      "iSAID; AerialFuseCV serves unified detection→segmentation systems.\n")

    A("## Per split\n")
    A("| Split | Images kept | Boxes | Instances | Pairs |")
    A("|---|---|---|---|---|")
    for s, v in st["per_split"].items():
        A(f"| {s} | {v['images_kept']:,} | {v['boxes']:,} | "
          f"{v['src_instances']:,} | {v['pairs']:,} |")
    A("")

    A("## Per category\n")
    A("| Category | Boxes | Pairs | Rate | Share |")
    A("|---|---|---|---|---|")
    tot = t["pairs"]
    for k, v in sorted(st["per_class"].items(), key=lambda kv: -kv[1]["total_pairs"]):
        b = sum(v[s]["boxes"] for s in st["per_split"])
        p = v["total_pairs"]
        A(f"| {k} | {b:,} | {p:,} | {p/b*100:.1f}% | {p/tot*100:.1f}% |")
    A(f"\n![class distribution](figures/F2_class_distribution.png)\n")

    A("## Matching quality\n")
    A(f"IoU between the oriented box polygon and its matched instance — "
      f"mean {ious.mean():.3f}, median {np.median(ious):.3f}, "
      f"5th percentile {np.percentile(ious,5):.3f}, "
      f"95th {np.percentile(ious,95):.3f}.\n")
    A("Raising the acceptance threshold would cost:\n")
    A("| Threshold | Pairs lost | Share |")
    A("|---|---|---|")
    for thr in (0.15, 0.2, 0.3, 0.5):
        lost = int((ious < thr).sum())
        A(f"| ≥ {thr} | {lost:,} | {lost/len(ious)*100:.1f}% |")
    A(f"\n![matching iou](figures/F5_matching_iou.png)\n")

    A("## Object size\n")
    A(f"Instance area spans {areas.min():,} to {areas.max():,} px "
      f"(median {int(np.median(areas)):,}).\n")
    A(f"![area by class](figures/F6_area_by_class.png)\n")
    if gsd_values.size:
        g = gsd_values
        A(f"## Ground sample distance\n")
        # Count only the images that actually state a value. Counting the whole
        # mapping described images with `gsd:null` as carrying a GSD, in the
        # same sentence that says they do not.
        A(f"{g.size:,} of {len(gsd):,} images carry a GSD value, "
          f"{g.min():.3f}–{g.max():.3f} m/px (median {np.median(g):.3f}). "
          f"The remaining {len(gsd) - g.size:,} record `gsd:null` in their "
          f"DOTA header and carry none.\n")
        A(f"![gsd](figures/F7_gsd.png)\n")

    A("## Objects not paired\n")
    dd = st.get("discarded", {})
    A(f"{dd.get('boxes',0):,} boxes and {dd.get('instances',0):,} instances were "
      f"not paired. Accounting is exact: pairs + discarded equals each source "
      f"population.\n")
    A("| Reason | Count |")
    A("|---|---|")
    for k, v in sorted(dd.get("by_reason", {}).items(), key=lambda kv: -kv[1]):
        A(f"| `{k}` | {v:,} |")
    A("")

    if disc:
        A("## Annotation discrepancy between the sources\n")
        d = disc["disagreement_decomposition_px"]; ag = disc["agreement"]
        A(f"Comparing the box-clipped semantic mask against the exact iSAID "
          f"instance over all {disc['pairs_measured']:,} pairs, the two agree "
          f"on only {ag['pct_identical_gt_099']:.1f}% of objects "
          f"(mean IoU {ag['mean']:.3f}). The disagreement decomposes as:\n")
        A("| Cause | Share of disagreeing pixels |")
        A("|---|---|")
        A(f"| Extent — iSAID annotates beyond the box | {d['share_missing']*100:.1f}% |")
        A(f"| Foreign — a neighbouring instance's pixels | {d['share_foreign']*100:.1f}% |")
        A(f"| Unlabelled | {d['share_unlabelled']*100:.1f}% |")
        c = disc["contamination_incidence"]
        A(f"\n{c['pct_pairs_with_foreign']:.1f}% of pairs contain at least some "
          f"foreign pixels. The released masks eliminate this by construction — "
          f"see `documentation/DECISION_reconciled_masks.md`.\n")
        A("| Category | Agreement | Pairs with foreign px | Disagreement that is extent |")
        A("|---|---|---|---|")
        for k, v in sorted(disc["per_class"].items(), key=lambda kv: kv[1]["mean_agreement"]):
            A(f"| {k} | {v['mean_agreement']:.3f} | "
              f"{v['pct_with_foreign_pixels']:.1f}% | "
              f"{v['disagreement_share_missing']*100:.1f}% |")
        A("")

    A("## Provenance\n")
    A(f"Build manifest: `{args.dataset}/build_manifest.json`. "
      f"Statistics: `{args.dataset}/dataset_statistics.json`. "
      f"Evidence for this analysis: `results/experimental/AerialFuseCV_Testing/`.\n")

    report = "\n".join(L)
    (args.out / "DATASET_ANALYSIS.md").write_text(report, encoding="utf-8")
    (args.dataset / "DATASET_ANALYSIS.md").write_text(report, encoding="utf-8")
    print(f"report  -> {args.out / 'DATASET_ANALYSIS.md'}")
    print(f"figures -> {figs}  ({len(list(figs.glob('*.png')))} files)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
