# P1 Background — DRAFT v0.1 (2026-07-29) — ~190 words

> Template: motivation and context for compiling the dataset.

DOTA v1.0 [xia2018dota] is a widely used benchmark for object detection in
aerial imagery, annotating objects with oriented bounding boxes across 15
categories. iSAID [zamir2019isaid] later re-annotated the same source
imagery with pixel-level, color-encoded instance masks for the same
categories. Although the two benchmarks describe the same scenes, their
annotations were produced independently: there is no published
correspondence between a DOTA box and the iSAID mask of the same physical
object, and their instance counts differ.

Research on aerial instance segmentation increasingly needs both annotation
forms simultaneously — for training mask heads on detector outputs, for
evaluating detection-to-segmentation pipelines, and for prompting
segmentation foundation models [kirillov2023sam] with detected boxes while
scoring against ground-truth masks. Producing such paired supervision by
manual re-annotation is prohibitively expensive at the scale of these
benchmarks.

AerialFuseCV was compiled to close this gap by reconciling the two existing
annotation sets at instance level under a conservative, fully documented
matching rule, so that the correspondence itself — not only the source
annotations — is a validated, reusable artifact.
