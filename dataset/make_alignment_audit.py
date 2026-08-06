#!/usr/bin/env python3
"""Build a clickable alignment-verification audit for AerialFuseCV. INTERNAL TOOL.

Data in Brief's editorial office asked for "alignment verification" alongside
the pairing logic and discard criteria. Nothing in the build supplies it: the
matcher accepts a pair at IoU >= 0.1 under a globally optimal one-to-one
assignment, but an acceptance rule is not evidence of identity. Optimal under a
rule and correct are different claims, and 125,722 pairs have never been
checked by eye.

This produces a single self-contained HTML page: one pair per screen, three
buttons, keyboard shortcuts, progress saved as you go. A human answers one
question per pair — does the box and the mask describe the same physical
object? — and the result is exported as JSON for scoring.

    python dataset/make_alignment_audit.py --dataset dataset/AerialFuseCV
    python dataset/make_alignment_audit.py --per-band 40      # bigger sample

Then open the HTML, review, click "Download results", and score with
`score_alignment_audit.py`.


WHY STRATIFIED, AND WHY THESE BANDS
-----------------------------------
The achieved IoU of a pair is the one observable that plausibly predicts whether
the match is right, so it is the stratifying variable.

A simple random sample would be a poor design here. Roughly 84% of pairs sit
above IoU 0.5, so 200 pairs drawn at random would contain only a handful below
0.2 — precisely the region where a wrong match is most likely and where an
estimate is most needed. The sample would be precise about the easy majority and
say almost nothing about the tail that carries the risk.

Equal allocation across IoU bands fixes that: every band gets the same number of
pairs, so each band's error rate is estimated with comparable precision
regardless of how rare that band is in the population. The cost is that the
sample is no longer self-weighting — the raw count of errors in the sample is
NOT an estimate of the population error rate, because low-IoU pairs are
deliberately over-represented. `score_alignment_audit.py` therefore reports two
different things: the per-band rate (unweighted, describes that band) and a
population estimate that re-weights each band by its true share of the 125,722
pairs. Reporting only the first would overstate the error rate; reporting only
the second would hide where the errors are.

Band edges are placed where they carry meaning rather than at round numbers:

    0.10-0.20   at and just above the acceptance threshold — the pairs a
                stricter rule would have rejected, and the ones the data
                article's Table 3 quantifies
    0.20-0.30   still weak overlap
    0.30-0.50   the region where the released clip starts to dominate
    0.50-0.70   comfortable agreement
    0.70-1.00   near-coincident box and mask

BLINDING
--------
The reviewer is not shown the IoU, the band, or any statistic, and pairs are
presented in shuffled order rather than grouped. Someone told a pair scored 0.12
will look for a reason it is wrong, and that expectation would be indistinguish-
able in the results from a real error. The band is recorded in the manifest and
re-joined at scoring time by pair id.

THE THREE OUTCOMES
------------------
`same` · `wrong` · `ambiguous`. A binary forces a judgement on cases that
genuinely do not have one — an object occluded to near-invisibility, two
identical adjacent vehicles where either assignment is defensible, a source
annotation that is itself unclear. Recording those separately and reporting
their rate is more honest than distributing them into whichever bin makes the
number look better, and their rate is itself a finding about the sources.
"""

import argparse
import base64
import io
import json
import random
import sys
import time
from pathlib import Path

try:
    import cv2
    import numpy as np
except ImportError:  # pragma: no cover
    sys.exit("needs numpy and opencv-python:  pip install numpy opencv-python")

BANDS = [(0.10, 0.20), (0.20, 0.30), (0.30, 0.50), (0.50, 0.70), (0.70, 1.01)]
BOX_COLOUR = (255, 205, 0)
MASK_COLOUR = (60, 220, 90)


def band_of(iou):
    for i, (lo, hi) in enumerate(BANDS):
        if lo <= iou < hi:
            return i
    return None


def overlay(base, mask, colour, alpha=0.45):
    out = base.copy()
    out[mask] = (out[mask] * (1 - alpha) + np.array(colour) * alpha).astype(np.uint8)
    return out


def render_pair(img, ins_rgb, rec, pad=60, max_w=460):
    """Two views of one pair: box alone, then box with the released mask.

    Box-first is deliberate. Showing the mask at the same moment invites the eye
    to accept whatever is highlighted; seeing the box first makes the reviewer
    form an expectation of which object is meant, which is the judgement being
    asked for.
    """
    colour = np.array(rec["instance_rgb"], np.uint8)
    mask = np.all(ins_rgb == colour, axis=-1)
    pts = np.round(np.array(rec["obb"]).reshape(4, 2)).astype(np.int32)

    ys, xs = np.nonzero(mask)
    if len(xs) == 0:
        return None
    x1 = max(0, min(int(xs.min()), int(pts[:, 0].min())) - pad)
    y1 = max(0, min(int(ys.min()), int(pts[:, 1].min())) - pad)
    x2 = min(img.shape[1], max(int(xs.max()), int(pts[:, 0].max())) + pad)
    y2 = min(img.shape[0], max(int(ys.max()), int(pts[:, 1].max())) + pad)
    if x2 - x1 < 8 or y2 - y1 < 8:
        return None

    crop = img[y1:y2, x1:x2]
    sub_pts = pts - [x1, y1]
    a = crop.copy()
    cv2.polylines(a, [sub_pts], True, BOX_COLOUR, 2, cv2.LINE_AA)
    b = overlay(crop, mask[y1:y2, x1:x2], MASK_COLOUR, 0.45)
    cv2.polylines(b, [sub_pts], True, BOX_COLOUR, 2, cv2.LINE_AA)

    panel = np.hstack([a, np.full((a.shape[0], 6, 3), 30, np.uint8), b])
    if panel.shape[1] > max_w * 2:
        s = (max_w * 2) / panel.shape[1]
        panel = cv2.resize(panel, (int(panel.shape[1] * s), int(panel.shape[0] * s)),
                           interpolation=cv2.INTER_AREA)
    ok, buf = cv2.imencode(".jpg", cv2.cvtColor(panel, cv2.COLOR_RGB2BGR),
                           [cv2.IMWRITE_JPEG_QUALITY, 86])
    if not ok:
        return None
    return "data:image/jpeg;base64," + base64.b64encode(buf).decode()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", type=Path, default=Path("dataset/AerialFuseCV"))
    ap.add_argument("--per-band", type=int, default=40,
                    help="pairs sampled per IoU band (5 bands; 40 -> 200 total)")
    ap.add_argument("--seed", type=int, default=20260806,
                    help="fixed so the sample is reproducible and cannot be "
                         "redrawn until it gives a better answer")
    ap.add_argument("--out", type=Path,
                    default=Path("results/experimental/AerialFuseCV_Testing/alignment_audit"))
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    print("reading pairs ...", flush=True)
    by_band = {i: [] for i in range(len(BANDS))}
    population = {i: 0 for i in range(len(BANDS))}
    for n, line in enumerate(open(args.dataset / "pairs.jsonl", encoding="utf-8")):
        r = json.loads(line)
        b = band_of(r.get("iou", -1))
        if b is None:
            continue
        population[b] += 1
        by_band[b].append((n, r))
    total = sum(population.values())
    print(f"  {total:,} pairs; population per band: "
          + ", ".join(f"{lo:.2f}-{hi:.2f}={population[i]:,}"
                      for i, (lo, hi) in enumerate(BANDS)))

    rng = random.Random(args.seed)
    sample = []
    for i in range(len(BANDS)):
        pool = by_band[i]
        take = min(args.per_band, len(pool))
        if take < args.per_band:
            print(f"  ! band {i} holds only {len(pool)} pairs; taking all")
        sample += [(i, idx, r) for idx, r in rng.sample(pool, take)]
    rng.shuffle(sample)                      # blinding: no band-grouped runs
    print(f"  sampled {len(sample)} pairs")

    # group by image so each source image and mask is read once
    by_image = {}
    for band, idx, rec in sample:
        by_image.setdefault((rec["split"], rec["image_id"]), []).append((band, idx, rec))

    items, skipped = [], 0
    for k, ((split, img_id), group) in enumerate(sorted(by_image.items()), 1):
        ip = args.dataset / split / "images" / f"{img_id}.png"
        mp = args.dataset / split / "instance_masks" / f"{img_id}_instance_id_RGB.png"
        img = cv2.imread(str(ip))
        ins = cv2.imread(str(mp))
        if img is None or ins is None:
            skipped += len(group)
            continue
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        ins = cv2.cvtColor(ins, cv2.COLOR_BGR2RGB)
        for band, idx, rec in group:
            uri = render_pair(img, ins, rec)
            if uri is None:
                skipped += 1
                continue
            items.append({"id": f"{split}:{img_id}:{idx}", "band": band,
                          "split": split, "image_id": img_id,
                          "class_name": rec["class_name"], "iou": rec["iou"],
                          "uri": uri})
        if k % 20 == 0:
            print(f"  rendered {k}/{len(by_image)} images", flush=True)

    rng.shuffle(items)
    print(f"  {len(items)} panels rendered, {skipped} skipped")

    manifest = {
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "dataset": str(args.dataset), "seed": args.seed,
        "per_band": args.per_band, "bands": BANDS,
        "population_per_band": population, "population_total": total,
        "sampled": len(items), "skipped": skipped,
        "items": [{k: v for k, v in it.items() if k != "uri"} for it in items],
    }
    (args.out / "sample_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8")

    html = build_html(items)
    (args.out / "alignment_audit.html").write_text(html, encoding="utf-8")
    mb = len(html.encode()) / 1e6
    print(f"\nwrote {args.out/'alignment_audit.html'} ({mb:.1f} MB)")
    print(f"      {args.out/'sample_manifest.json'}")
    print("\nOpen the HTML, review, then click Download results.")
    return 0


def build_html(items):
    payload = json.dumps([{"id": i["id"], "uri": i["uri"], "cls": i["class_name"]}
                          for i in items])
    return HTML_TEMPLATE.replace("__ITEMS__", payload)


HTML_TEMPLATE = r"""<!doctype html><html lang=en><head><meta charset=utf-8>
<title>AerialFuseCV — alignment audit</title>
<style>
:root{color-scheme:dark}
*{box-sizing:border-box}
body{margin:0;background:#15181c;color:#dfe4ea;
 font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
 display:flex;flex-direction:column;height:100vh;overflow:hidden}
header{padding:.7rem 1.1rem;border-bottom:1px solid #262b31;display:flex;
 align-items:center;gap:1.2rem;flex-wrap:wrap}
h1{font-size:.98rem;margin:0;font-weight:600;letter-spacing:-.01em}
.bar{flex:1;height:7px;background:#262b31;border-radius:4px;overflow:hidden;min-width:140px}
.bar i{display:block;height:100%;background:#4a9eff;width:0;transition:width .18s}
.count{font-variant-numeric:tabular-nums;color:#8b95a1;font-size:.86rem}
main{flex:1;display:flex;align-items:center;justify-content:center;padding:1rem;overflow:auto}
figure{margin:0;text-align:center;max-width:100%}
img{max-width:100%;max-height:62vh;border-radius:7px;border:1px solid #2b3138}
.legend{margin-top:.55rem;color:#8b95a1;font-size:.83rem}
.k{display:inline-block;width:10px;height:10px;border-radius:2px;vertical-align:-1px;margin:0 .3rem 0 .9rem}
footer{padding:.9rem 1.1rem 1.3rem;border-top:1px solid #262b31}
.q{text-align:center;color:#aab3bf;margin:0 0 .7rem;font-size:.93rem}
.btns{display:flex;gap:.7rem;justify-content:center;flex-wrap:wrap}
button{font:inherit;font-weight:600;padding:.72rem 1.5rem;border-radius:8px;
 border:1px solid #333a42;background:#1e242a;color:#dfe4ea;cursor:pointer;transition:.12s}
button:hover{transform:translateY(-1px)}
button kbd{font:inherit;font-size:.78em;opacity:.5;margin-left:.5rem}
.same{border-color:#2f7d4f;background:#16301f}.same:hover{background:#1d4029}
.wrong{border-color:#8a3b3b;background:#301818}.wrong:hover{background:#40201f}
.amb{border-color:#7a6a2f;background:#2c2716}.amb:hover{background:#3a331d}
.nav{display:flex;gap:.6rem;justify-content:center;margin-top:.8rem}
.nav button{padding:.4rem .9rem;font-size:.84rem;font-weight:500;background:transparent}
.done{text-align:center;padding:2.5rem 1rem}
.done h2{font-size:1.35rem;margin:0 0 .5rem}
.tally{display:flex;gap:1.6rem;justify-content:center;margin:1.4rem 0;flex-wrap:wrap}
.tally div{text-align:center}
.tally b{display:block;font-size:1.7rem;font-variant-numeric:tabular-nums}
.dl{border-color:#2f5f8a;background:#152a3d;padding:.8rem 1.7rem}
</style></head><body>
<header>
  <h1>Alignment audit</h1>
  <div class=bar><i id=prog></i></div>
  <span class=count id=count></span>
</header>
<main id=main></main>
<footer id=foot></footer>
<script>
const ITEMS = __ITEMS__;
const KEY = "afcv_alignment_audit_v1";
let ans = JSON.parse(localStorage.getItem(KEY) || "{}");
let i = 0;
while (i < ITEMS.length && ans[ITEMS[i].id]) i++;

function render(){
  const done = Object.keys(ans).length;
  document.getElementById("prog").style.width = (done/ITEMS.length*100)+"%";
  document.getElementById("count").textContent = done+" / "+ITEMS.length;
  const main = document.getElementById("main"), foot = document.getElementById("foot");
  if (i >= ITEMS.length){
    const t = {same:0,wrong:0,ambiguous:0};
    Object.values(ans).forEach(v => t[v]!==undefined && t[v]++);
    main.innerHTML = `<div class=done><h2>Review complete</h2>
      <p style="color:#8b95a1">${ITEMS.length} pairs judged. Download and hand the file back.</p>
      <div class=tally>
        <div><b style="color:#5cc98a">${t.same}</b>same object</div>
        <div><b style="color:#e07a7a">${t.wrong}</b>wrong object</div>
        <div><b style="color:#d4bd6a">${t.ambiguous}</b>ambiguous</div>
      </div></div>`;
    foot.innerHTML = `<div class=btns>
        <button class=dl onclick=download()>Download results</button>
        <button onclick="i=0;render()">Review again</button>
        <button onclick="if(confirm('Erase all judgements?')){ans={};i=0;render()}">Reset</button>
      </div>`;
    return;
  }
  const it = ITEMS[i];
  main.innerHTML = `<figure><img src="${it.uri}" alt="pair">
    <figcaption class=legend><b>${it.cls}</b>
      <span class=k style="background:#ffcd00"></span>DOTA box
      <span class=k style="background:#3cdc5a"></span>released mask
    </figcaption></figure>`;
  foot.innerHTML = `<p class=q>Do the box and the mask describe the <b>same physical object</b>?</p>
    <div class=btns>
      <button class=same onclick="pick('same')">Same object<kbd>1</kbd></button>
      <button class=wrong onclick="pick('wrong')">Wrong object<kbd>2</kbd></button>
      <button class=amb onclick="pick('ambiguous')">Ambiguous<kbd>3</kbd></button>
    </div>
    <div class=nav>
      <button onclick="back()">&larr; Back</button>
      <button onclick="skip()">Skip &rarr;</button>
    </div>`;
}
function pick(v){ ans[ITEMS[i].id]=v; localStorage.setItem(KEY,JSON.stringify(ans)); i++; render(); }
function back(){ if(i>0){ i--; delete ans[ITEMS[i].id]; localStorage.setItem(KEY,JSON.stringify(ans)); render(); } }
function skip(){ if(i<ITEMS.length){ i++; render(); } }
function download(){
  const out = {reviewed_utc:new Date().toISOString(), n:Object.keys(ans).length, answers:ans};
  const a=document.createElement("a");
  a.href=URL.createObjectURL(new Blob([JSON.stringify(out,null,2)],{type:"application/json"}));
  a.download="alignment_audit_results.json"; a.click();
}
addEventListener("keydown",e=>{
  if(e.key==="1")pick("same"); else if(e.key==="2")pick("wrong");
  else if(e.key==="3")pick("ambiguous");
  else if(e.key==="ArrowLeft")back(); else if(e.key==="ArrowRight")skip();
});
render();
</script></body></html>
"""


if __name__ == "__main__":
    sys.exit(main())
