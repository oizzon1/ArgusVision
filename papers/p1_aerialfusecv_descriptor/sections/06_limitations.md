# P1 Limitations — DRAFT v0.1 (2026-07-29) — ~185 words (hard cap 200)

The conservative matching rule leaves 2.1% of candidate instances unpaired;
users requiring exhaustive coverage of every annotated object should account
for this. Match quality varies by class: the lowest rates are helicopter
(83.6%, validation split) and harbor (89.6%, training split), and per-class
rates are provided so users can judge fitness for class-specific tasks.

The class distribution is severely imbalanced, inherited from the source
imagery: ship, small-vehicle, and large-vehicle together account for 71% of
all instances, while six classes each contribute less than 0.6%.

Annotation quality is bounded by the source datasets: geometric accuracy by
DOTA v1.0 oriented boxes and mask accuracy by iSAID's instance masks; errors
present in either source propagate into the pairs. Only the training and
validation splits are covered, as public instance annotations do not exist
for the test split.

Finally, because DOTA and iSAID imagery cannot be redistributed, the deposit
contains annotations, metadata, and a construction script rather than
images; rebuilding requires the official source downloads and depends on
their continued availability (verification checksums are included).
