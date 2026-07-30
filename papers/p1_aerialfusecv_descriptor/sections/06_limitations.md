# P1 Limitations — DRAFT v0.3 (2026-07-30) — hard cap 200 words

> v0.3: now leads with the box-anchored asymmetry (derived from thesis
> Table 7 — see Data Description ⚠ note). Per-category floors moved to Data
> Description to buy words. v0.2 added the one-to-one and mask-encoding
> caveats found in `dataset/refine_aerialfusecv.py`.

Pairing is box-anchored. 97.9% of DOTA boxes received a mask, but only about
37.8% of iSAID mask instances received a box, so roughly 205,600 mask
instances — overwhelmingly small vehicles — are absent from the released
masks. Work requiring exhaustive small-object mask coverage should use iSAID
directly.

Each box is paired independently with its highest-overlap mask component,
without a one-to-one constraint, so in crowded scenes two boxes of one
category may reference the same component.

Masks store category rather than per-instance colours; adjacent instances of
one category are inseparable from the mask alone, and the paired box is
required to isolate an instance.

The category distribution is severely imbalanced: three categories supply
71.0% of pairs while six contribute under 0.6% each.

Annotation quality is bounded by the sources — geometry by DOTA v1.0, masks by
iSAID — and their errors propagate into the pairs. Only training and
validation splits are covered, as iSAID publishes no test-split masks.

Source imagery cannot be redistributed, so the deposit provides annotations,
metadata and a construction script rather than images.
