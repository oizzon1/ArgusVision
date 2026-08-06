#!/usr/bin/env python3
"""Score a completed alignment audit. INTERNAL TOOL.

Takes the JSON exported from `alignment_audit.html`, re-joins it to the sample
manifest by pair id, and produces the numbers the data article reports.

    python dataset/score_alignment_audit.py \
        --results ~/Downloads/alignment_audit_results.json

Two rates are reported, and confusing them would misstate the result.

**Per-band rate** — the error rate *within* an IoU band. Directly observed,
unweighted, and the informative one: it shows where identity breaks down.

**Population estimate** — the error rate across all 125,722 pairs, formed by
weighting each band's rate by that band's true share of the population. The
sample is deliberately NOT self-weighting: equal allocation over-represents the
low-IoU bands roughly forty-fold, so counting errors in the sample directly
would overstate the dataset's error rate badly. Conversely, reporting only the
population figure would bury the fact that the weak-overlap tail behaves
differently from the bulk.

Intervals are Wilson score intervals rather than the normal approximation. At
n=40 per band, and especially where the observed count is 0 or near it, the
normal approximation produces intervals that are too narrow and can extend below
zero — it would claim more precision than the sample supports.
"""

import argparse
import json
import math
import subprocess
import sys
import time
from pathlib import Path

Z = 1.959963985  # 95%


def wilson(k, n, z=Z):
    """Wilson score interval. Defined at k=0 and k=n, unlike the normal approx."""
    if n == 0:
        return (0.0, 0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (p, max(0.0, centre - half), min(1.0, centre + half))


def pct(x):
    return f"{x*100:.1f}%"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", type=Path, required=True)
    ap.add_argument("--audit", type=Path,
                    default=Path("results/experimental/AerialFuseCV_Testing/alignment_audit"))
    args = ap.parse_args()

    manifest = json.loads((args.audit / "sample_manifest.json").read_text(encoding="utf-8"))
    answers = json.loads(args.results.read_text(encoding="utf-8"))["answers"]
    bands = manifest["bands"]
    pop = {int(k): v for k, v in manifest["population_per_band"].items()}
    pop_total = manifest["population_total"]
    by_id = {it["id"]: it for it in manifest["items"]}

    unknown = [k for k in answers if k not in by_id]
    if unknown:
        print(f"warning: {len(unknown)} judged id(s) not in this manifest "
              f"(results from a different sample?)", file=sys.stderr)

    tally = {i: {"same": 0, "wrong": 0, "ambiguous": 0} for i in range(len(bands))}
    per_class = {}
    for pid, verdict in answers.items():
        it = by_id.get(pid)
        if not it or verdict not in ("same", "wrong", "ambiguous"):
            continue
        tally[it["band"]][verdict] += 1
        c = per_class.setdefault(it["class_name"], {"same": 0, "wrong": 0, "ambiguous": 0})
        c[verdict] += 1

    rows, weighted_wrong, weighted_amb, covered = [], 0.0, 0.0, 0
    w_lo = w_hi = 0.0
    pooled = {"same": 0, "wrong": 0, "ambiguous": 0}
    for i, (lo, hi) in enumerate(bands):
        t = tally[i]
        n = t["same"] + t["wrong"] + t["ambiguous"]
        if n == 0:
            rows.append({"band": f"{lo:.2f}–{hi:.2f}", "n": 0, "population": pop.get(i, 0)})
            continue
        pw, lo_w, hi_w = wilson(t["wrong"], n)
        pa, _, _ = wilson(t["ambiguous"], n)
        share = pop.get(i, 0) / pop_total
        weighted_wrong += pw * share
        weighted_amb += pa * share
        # Conservative interval on the weighted estimate: combine the per-band
        # bounds under the same weights. A variance-based interval collapses to
        # a point when every band observes zero events, which would assert
        # certainty the sample cannot support.
        w_lo += lo_w * share
        w_hi += hi_w * share
        for k in pooled:
            pooled[k] += t[k]
        covered += pop.get(i, 0)
        rows.append({
            "band": f"{lo:.2f}–{hi:.2f}", "n": n,
            "population": pop.get(i, 0), "population_share": round(share, 6),
            "same": t["same"], "wrong": t["wrong"], "ambiguous": t["ambiguous"],
            "wrong_rate": round(pw, 4), "wrong_ci95": [round(lo_w, 4), round(hi_w, 4)],
            "ambiguous_rate": round(pa, 4),
            "agreement_rate": round(t["same"] / n, 4),
        })

    n_total = sum(r.get("n", 0) for r in rows)
    print(f"\nalignment audit — {n_total} pairs judged of {manifest['sampled']} sampled\n")
    print(f"  {'IoU band':<12}{'n':>4}{'same':>6}{'wrong':>7}{'amb':>5}"
          f"{'wrong rate':>13}{'95% CI':>18}{'pop share':>11}")
    for r in rows:
        if not r.get("n"):
            print(f"  {r['band']:<12}{0:>4}   — not judged —")
            continue
        ci = f"[{pct(r['wrong_ci95'][0])}, {pct(r['wrong_ci95'][1])}]"
        print(f"  {r['band']:<12}{r['n']:>4}{r['same']:>6}{r['wrong']:>7}"
              f"{r['ambiguous']:>5}{pct(r['wrong_rate']):>13}{ci:>18}"
              f"{pct(r['population_share']):>11}")

    n_pooled = sum(pooled.values())
    pp, plo, phi = wilson(pooled["wrong"], n_pooled)
    ap_, alo, ahi = wilson(pooled["ambiguous"], n_pooled)

    print(f"\n  population-weighted wrong-match rate : {pct(weighted_wrong)}"
          f"   95% CI [{pct(w_lo)}, {pct(w_hi)}]")
    print(f"  population-weighted ambiguous rate   : {pct(weighted_amb)}")
    print(f"  population-weighted agreement        : {pct(1 - weighted_wrong - weighted_amb)}")
    print(f"\n  pooled over all {n_pooled} judged pairs:")
    print(f"    wrong     {pooled['wrong']:>3}/{n_pooled}  {pct(pp)}"
          f"  95% CI [{pct(plo)}, {pct(phi)}]")
    print(f"    ambiguous {pooled['ambiguous']:>3}/{n_pooled}  {pct(ap_)}"
          f"  95% CI [{pct(alo)}, {pct(ahi)}]")
    if pooled["wrong"] == 0:
        print(f"\n  Zero observed errors is not zero error rate: the sample is "
              f"consistent with a\n  true wrong-match rate up to {pct(phi)} "
              f"(pooled), and up to {pct(w_hi)} once the\n  strata are weighted.")

    classes = sorted(per_class)
    print(f"\n  categories represented: {len(classes)} of 15")
    missing = sorted(set(manifest.get("all_classes", [])) - set(classes))
    if missing:
        print(f"    absent from the sample: {', '.join(missing)}")
    if covered != pop_total:
        print(f"  ! bands judged cover {covered:,} of {pop_total:,} pairs — "
              "weighted figures are over the covered bands only")

    try:
        sha = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        sha = None

    report = {
        "scored_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "results_file": str(args.results),
        "sample_manifest": str(args.audit / "sample_manifest.json"),
        "seed": manifest["seed"], "per_band": manifest["per_band"],
        "pairs_judged": n_total, "pairs_sampled": manifest["sampled"],
        "population_total": pop_total,
        "method": "Stratified by achieved IoU, equal allocation per band, "
                  "presentation order shuffled and IoU withheld from the "
                  "reviewer. Per-band rates are direct observations; the "
                  "population estimate re-weights each band by its share of "
                  "the full pair population. Intervals are Wilson score "
                  "intervals at 95%.",
        "per_band": rows,
        "population_weighted": {
            "wrong_rate": round(weighted_wrong, 4),
            "wrong_ci95": [round(w_lo, 4), round(w_hi, 4)],
            "ambiguous_rate": round(weighted_amb, 4),
            "agreement_rate": round(1 - weighted_wrong - weighted_amb, 4),
        },
        "pooled": {
            "n": n_pooled, "same": pooled["same"], "wrong": pooled["wrong"],
            "ambiguous": pooled["ambiguous"],
            "wrong_rate": round(pp, 4), "wrong_ci95": [round(plo, 4), round(phi, 4)],
            "ambiguous_rate": round(ap_, 4),
            "ambiguous_ci95": [round(alo, 4), round(ahi, 4)],
        },
        "categories_represented": sorted(per_class),
        "per_class": per_class,
        "git_sha": sha,
    }
    out = args.audit / "alignment_audit_report.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
