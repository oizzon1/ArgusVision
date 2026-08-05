#!/usr/bin/env python3
"""Single-file EDA report for a built AerialFuseCV. INTERNAL TOOL.

Working aid for reading the whole build in one place while writing the data
article — every table and figure on one scrollable page instead of a markdown
file plus loose PNGs. Not shipped with the dataset and not produced by the
rebuild script: a user gets the build receipt (`summary.md`) from the rebuild,
and the full dataset description from the published article.

Every number is computed here from the build's own artefacts. Nothing is
quoted from prose, and nothing is carried over from a previous build — so a
figure that silently stops matching the build shows up as a changed number
rather than surviving into the paper.

    python dataset/make_eda_report.py --dataset D:/AI_Datasets/AerialFuseCV

Optional: --discrepancy <dir> adds the box/mask agreement section, using the
per-pair records written by dataset/measure_discrepancy.py.
"""

import argparse
import base64
import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

CSS = """
:root { color-scheme: light dark; }
* { box-sizing: border-box; }
body { margin: 0 auto; padding: 2.5rem 1.5rem 5rem; max-width: 62rem;
  font: 16px/1.65 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  color: #1a1d21; background: #fff; }
h1 { font-size: 2rem; margin: 0 0 .3rem; letter-spacing: -.02em; }
h2 { font-size: 1.3rem; margin: 3rem 0 .8rem; padding-bottom: .4rem;
  border-bottom: 2px solid #e3e6ea; letter-spacing: -.01em; }
h3 { font-size: 1.02rem; margin: 2rem 0 .5rem; color: #3d4450; }
.sub { color: #6b7280; margin: 0 0 2rem; font-size: .93rem; }
table { border-collapse: collapse; width: 100%; margin: .8rem 0 1.4rem;
  font-size: .9rem; display: block; overflow-x: auto; }
th, td { padding: .45rem .7rem; text-align: right; border-bottom: 1px solid #e8ebef;
  white-space: nowrap; }
th:first-child, td:first-child { text-align: left; }
thead th { background: #f6f8fa; font-weight: 600; border-bottom: 2px solid #d8dde3; }
tbody tr:hover { background: #fafbfc; }
td.em, th.em { font-weight: 700; }
figure { margin: 1.5rem 0 2rem; }
figure img { width: 100%; height: auto; border: 1px solid #e3e6ea; border-radius: 6px; }
figcaption { font-size: .85rem; color: #6b7280; margin-top: .5rem; }
.note { background: #f6f8fa; border-left: 3px solid #9aa4b2; padding: .8rem 1rem;
  margin: 1.2rem 0; font-size: .92rem; border-radius: 0 5px 5px 0; }
.kv { display: grid; grid-template-columns: max-content 1fr; gap: .3rem 1.2rem;
  font-size: .92rem; margin: 1rem 0 2rem; }
.kv dt { color: #6b7280; }
.kv dd { margin: 0; font-variant-numeric: tabular-nums; }
code { background: #f0f2f5; padding: .1rem .35rem; border-radius: 3px;
  font-size: .87em; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }
pre { background: #f6f8fa; padding: .9rem 1rem; border-radius: 6px; overflow-x: auto;
  font-size: .85rem; line-height: 1.5; }
footer { margin-top: 4rem; padding-top: 1.2rem; border-top: 1px solid #e3e6ea;
  font-size: .85rem; color: #6b7280; }
@media (prefers-color-scheme: dark) {
  body { color: #d6dae0; background: #14171a; }
  h2 { border-color: #2a2f36; } h3 { color: #aab3bf; }
  th, td { border-color: #23282e; } thead th { background: #1c2025; border-color: #333a42; }
  tbody tr:hover { background: #1a1e23; }
  .note, pre { background: #1a1e23; } code { background: #23282e; }
  figure img { border-color: #2a2f36; } footer { border-color: #2a2f36; }
}
"""


def load_jsonl(path, limit=None):
    rows = []
    with open(path, encoding="utf-8") as f:
        for n, line in enumerate(f):
            if limit and n >= limit:
                break
            if line.strip():
                rows.append(json.loads(line))
    return rows


def embed(path):
    """PNG -> data URI, so the report is one file with no external assets."""
    return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode()


def table(headers, rows, emphasise=()):
    h = "".join(f"<th{' class=em' if i in emphasise else ''}>{c}</th>"
                for i, c in enumerate(headers))
    body = []
    for r in rows:
        cells = "".join(f"<td{' class=em' if i in emphasise else ''}>{c}</td>"
                        for i, c in enumerate(r))
        body.append(f"<tr>{cells}</tr>")
    return (f"<table><thead><tr>{h}</tr></thead>"
            f"<tbody>{''.join(body)}</tbody></table>")


def fmt(n):
    return f"{n:,}" if isinstance(n, int) else f"{n:,.2f}"


def agreement_section(per_pair):
    """Box/mask agreement, reported per object rather than as a pixel total.

    The released mask IS the instance clipped to its box, so pixels outside the
    box are not part of the dataset. Summing them describes a property of the
    two sources, not of what is shipped, and a total of tens of millions reads
    as though iSAID were broken. What a user needs is how many OBJECTS have a
    mask that disagrees with its box enough to matter.

    Reported ratio is outside/inside: instance pixels beyond the box, over
    instance pixels within it.
    """
    ratios, clean = [], 0
    for r in per_pair:
        inside, outside = r.get("clip_px", 0), r.get("missing_px", 0)
        if outside == 0:
            clean += 1
        if inside > 0:
            ratios.append(outside / inside)
    if not ratios:
        return ""
    ratios.sort()
    n = len(ratios)

    def share_above(t):
        lo, hi = 0, n
        while lo < hi:
            mid = (lo + hi) // 2
            if ratios[mid] > t:
                hi = mid
            else:
                lo = mid + 1
        return n - lo

    rows = []
    for t, label in ((0.02, "1 / 50"), (0.05, "1 / 20"), (0.10, "1 / 10"),
                     (0.20, "1 / 5"), (1 / 3, "1 / 3"), (0.50, "1 / 2"),
                     (1.00, "1 / 1")):
        c = share_above(t)
        rows.append([f"more than {label}", fmt(c), f"{c / n * 100:.2f}%"])

    median = ratios[n // 2]
    flagged = share_above(1 / 3)
    return f"""
<h2>Box–mask agreement</h2>
<p>Every released mask is its iSAID instance <em>clipped to the DOTA oriented
box</em>. The box is the anchor: pixels beyond it are not part of the dataset.
The question that matters is therefore not how many pixels the two sources
disagree about in total, but how many <strong>objects</strong> have a mask that
extends past its box far enough to signal a genuine annotation problem.</p>

<p>The ratio below is <strong>outside &divide; inside</strong> — instance pixels
beyond the box, divided by instance pixels within it.</p>

<dl class="kv">
  <dt>Objects measured</dt><dd>{fmt(n)}</dd>
  <dt>Nothing outside the box at all</dt><dd>{fmt(clean)} ({clean / len(per_pair) * 100:.1f}%)</dd>
  <dt>Median ratio</dt><dd>{median:.4f}</dd>
  <dt>Beyond 1/3 (flagged)</dt><dd>{fmt(flagged)} ({flagged / n * 100:.2f}%)</dd>
</dl>

{table(["Mask extends beyond box by", "Objects", "Share"], rows)}

<div class="note"><strong>Why the whole curve is shown.</strong> The
distribution is smooth — there is no natural gap separating a boundary
rounding difference from a wrong annotation, so no single cut point is
derivable from the data. Publishing every threshold lets a reader apply their
own rather than accept one chosen for them. The 1/3 row is the value used in
the data article; it is one row of this table, not a tuned parameter.</div>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", type=Path, required=True,
                    help="a built AerialFuseCV directory")
    ap.add_argument("--figures", type=Path,
                    default=Path("results/experimental/AerialFuseCV_Testing/eda/figures"))
    ap.add_argument("--discrepancy", type=Path,
                    default=Path("results/experimental/AerialFuseCV_Testing/"
                                 "annotation_discrepancy/per_pair.jsonl"))
    ap.add_argument("--out", type=Path,
                    default=Path("results/experimental/AerialFuseCV_Testing/"
                                 "eda/AerialFuseCV_EDA.html"))
    args = ap.parse_args()

    stats_path = args.dataset / "dataset_statistics.json"
    if not stats_path.exists():
        sys.exit(f"no dataset_statistics.json under {args.dataset} — "
                 "point --dataset at a built AerialFuseCV directory")
    stats = json.loads(stats_path.read_text(encoding="utf-8"))
    totals = stats.get("totals", {})

    manifest = {}
    mpath = args.dataset / "build_manifest.json"
    if mpath.exists():
        manifest = json.loads(mpath.read_text(encoding="utf-8"))

    parts = []
    parts.append(f"""<h1>AerialFuseCV — Exploratory Data Analysis</h1>
<p class="sub">Generated {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())} from
<code>{args.dataset}</code>. Every figure and number below is computed from the
build's own artefacts at generation time.</p>

<div class="note"><strong>Internal working document.</strong> AerialFuseCV links
each DOTA v1.0 oriented bounding box to the individual iSAID instance mask
describing the same physical object; the released mask is that instance clipped
to its oriented box. This page exists to read one build in a single place while
drafting the data article. It is not shipped with the dataset — the published
article is the dataset description.</div>

<dl class="kv">
  <dt>Mask definition</dt><dd>matched iSAID instance clipped to the oriented box</dd>
  <dt>Matching geometry</dt><dd>oriented polygon, IoU &ge; 0.1, one-to-one within class</dd>
  <dt>Annotation format</dt><dd>DOTA native — headers, absolute px, class name, difficulty</dd>
  <dt>Box geometries</dt><dd><code>labels_obb</code>, <code>labels_hbb</code></dd>
  <dt>Splits</dt><dd>train, val (iSAID publishes no test-split masks)</dd>
</dl>""")

    if manifest:
        parts.append(f"""<h3>Provenance of this build</h3>
<dl class="kv">
  <dt>Rebuilt</dt><dd>{manifest.get('rebuilt_utc', 'n/a')}</dd>
  <dt>Correspondence SHA-256</dt><dd><code>{str(manifest.get('correspondence_sha256', 'n/a'))[:32]}…</code></dd>
  <dt>Pairs written</dt><dd>{fmt(manifest.get('pairs_written', 0))} of {fmt(manifest.get('pairs_expected', 0))}</dd>
  <dt>Box indices resolved</dt><dd>{manifest.get('resolve_rate', 0) * 100:.2f}%</dd>
  <dt>Environment</dt><dd>Python {manifest.get('python', '?')}, numpy {manifest.get('numpy', '?')}, OpenCV {manifest.get('opencv', '?')}</dd>
</dl>""")

    # ---- construction funnel ---------------------------------------------
    funnel = [
        ["Images with both annotations", fmt(totals.get("images_seen", 0))],
        ["Source boxes (DOTA)", fmt(totals.get("boxes", 0))],
        ["Source instances (iSAID)", fmt(totals.get("src_instances", 0))],
        ["<strong>Paired objects</strong>", f"<strong>{fmt(totals.get('pairs', 0))}</strong>"],
        ["Images retained", f"{fmt(totals.get('images_kept', 0))} "
                            f"(excluded {totals.get('images_excluded', 0)})"],
        ["Box pairing rate", f"{totals.get('box_pairing_rate', 0) * 100:.2f}%"],
        ["Instance pairing rate", f"{totals.get('instance_pairing_rate', 0) * 100:.2f}%"],
    ]
    parts.append("<h2>Construction funnel</h2>"
                 + table(["Stage", "Count"], funnel))
    parts.append("""<div class="note"><strong>The two rates differ because
pairing is anchored on the boxes.</strong> iSAID annotates far more objects than
DOTA — overwhelmingly small vehicles — so most unpaired instances simply have no
box to pair with. If you need exhaustive small-object mask coverage, use iSAID
directly; AerialFuseCV serves unified detection&rarr;segmentation systems that
need both forms attached to the same object.</div>""")

    # ---- per split --------------------------------------------------------
    per_split = stats.get("per_split", {})
    if per_split:
        rows = [[s, fmt(v.get("boxes", 0)), fmt(v.get("src_instances", 0)),
                 fmt(v.get("pairs", 0))] for s, v in per_split.items()]
        parts.append("<h2>Per split</h2>"
                     + table(["Split", "Boxes", "Instances", "Pairs"], rows))

    # ---- per category -----------------------------------------------------
    per_class = stats.get("per_class", {})
    if per_class:
        rows = []
        grand = sum(v.get("total_pairs", 0) for v in per_class.values())
        for cls, v in sorted(per_class.items(),
                             key=lambda kv: -kv[1].get("total_pairs", 0)):
            boxes = sum(v.get(s, {}).get("boxes", 0) for s in ("train", "val"))
            pairs = v.get("total_pairs", 0)
            rows.append([cls, fmt(boxes), fmt(pairs),
                         f"{pairs / boxes * 100:.1f}%" if boxes else "—",
                         f"{pairs / grand * 100:.1f}%" if grand else "—"])
        parts.append("<h2>Per category</h2>"
                     + table(["Category", "Boxes", "Pairs", "Paired", "Share"], rows))
        parts.append("""<div class="note"><strong>Categories are severely
imbalanced</strong> — a handful supply most of the pairs and several sit well
under 1%. Judge fitness category by category, not on the totals.</div>""")

    # ---- discards ---------------------------------------------------------
    disc = stats.get("discards") or stats.get("discard_reasons")
    if isinstance(disc, dict) and disc:
        rows = [[f"<code>{k}</code>", fmt(v)]
                for k, v in sorted(disc.items(), key=lambda kv: -kv[1])]
        parts.append("<h2>What was discarded, and why</h2>"
                     + table(["Reason", "Count"], rows))
        parts.append("""<div class="note">Exclusion is auditable rather than
silent: every unpaired box and instance is recorded with its reason and its best
achieved overlap in <code>discarded.jsonl</code>. Pairs plus discards equal each
source population exactly, on both sides, and this is checked on every build.</div>""")

    # ---- box/mask agreement ----------------------------------------------
    if args.discrepancy.exists():
        parts.append(agreement_section(load_jsonl(args.discrepancy)))
    else:
        parts.append(f"""<h2>Box–mask agreement</h2>
<div class="note">Not included — no per-pair discrepancy records at
<code>{args.discrepancy}</code>. Generate them with
<code>python dataset/measure_discrepancy.py --dataset {args.dataset}</code>,
then re-run this report.</div>""")

    # ---- figures ----------------------------------------------------------
    captions = {
        "F1_paired_example.png": "Paired annotations in a scene: DOTA oriented "
            "boxes with the released instance masks.",
        "F2_class_distribution.png": "Paired instances per category, log scale.",
        "F3_construction_pipeline.png": "Construction pipeline: two sources in, "
            "a one-to-one match on the oriented polygon, two discard streams out. "
            "Every value is read from the build statistics.",
        "F4_source_divergence.png": "Why reconciliation is needed: a convention "
            "difference between the sources, and a source annotation error.",
        "F5_matching_iou.png": "Distribution of achieved overlap across all pairs.",
        "F6_area_by_class.png": "Object area by category — scale varies by orders "
            "of magnitude.",
        "F7_gsd.png": "Ground sample distance across the retained images.",
    }
    figs = sorted(args.figures.glob("F*.png")) if args.figures.is_dir() else []
    if figs:
        parts.append("<h2>Figures</h2>")
        for f in figs:
            parts.append(f'<figure><img alt="{f.stem}" src="{embed(f)}">'
                         f'<figcaption><strong>{f.stem.split("_")[0]}.</strong> '
                         f'{captions.get(f.name, f.stem)}</figcaption></figure>')

    # ---- how to get it ----------------------------------------------------
    parts.append("""<h2>Regenerating this report</h2>
<pre>python dataset/make_eda_report.py --dataset &lt;built AerialFuseCV&gt;</pre>
<p>Add <code>--discrepancy &lt;per_pair.jsonl&gt;</code> for the box&ndash;mask
agreement section. Re-run it after any rebuild: every value here is read from
that build's own artefacts, so a number that changes is a number that really
changed.</p>""")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        f"<!doctype html><html lang=en><head><meta charset=utf-8>"
        f"<meta name=viewport content='width=device-width,initial-scale=1'>"
        f"<title>AerialFuseCV — EDA</title><style>{CSS}</style></head><body>"
        + "".join(parts)
        + f"<footer>AerialFuseCV exploratory data analysis · generated "
          f"{time.strftime('%Y-%m-%d', time.gmtime())} from "
          f"<code>{args.dataset}</code> · every value computed at generation "
          f"time from the build's own artefacts.</footer>"
          "</body></html>", encoding="utf-8")

    size = args.out.stat().st_size / 1e6
    print(f"wrote {args.out}  ({size:.1f} MB, {len(figs)} figures embedded)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
