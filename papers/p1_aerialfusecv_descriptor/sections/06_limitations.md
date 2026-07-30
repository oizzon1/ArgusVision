# P1 Limitations — DRAFT v0.2 (2026-07-30) — hard cap 200 words

> v0.2: added the one-to-one and mask-encoding caveats discovered while
> reading `dataset/refine_aerialfusecv.py` for the Methods section.

Matching leaves 2.1% of candidate boxes unpaired; per-category rates are
provided, the lowest being helicopter (83.6%, validation) and harbor (89.6%,
training).

Each box is paired independently with its highest-overlap mask component,
without enforcing a one-to-one assignment. In crowded scenes two boxes of the
same category may therefore reference the same component, and users requiring
strictly disjoint instances should filter on this.

Masks store category colours rather than per-instance identifiers, so adjacent
instances of one category are inseparable from the mask alone; the paired box
is required to isolate an instance.

The category distribution is severely imbalanced: ship, small-vehicle and
large-vehicle supply 71% of instances, while six categories each contribute
under 0.6%.

Annotation quality is bounded by the sources — geometry by DOTA v1.0, masks by
iSAID — and their errors propagate into the pairs. Only training and
validation splits are covered, as public instance annotations do not exist for
the test split.

Because the source imagery cannot be redistributed, the deposit provides
annotations, metadata and a construction script rather than images.
