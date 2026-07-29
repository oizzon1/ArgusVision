# P1 Front Matter — DRAFT v0.1 (2026-07-29)

> Template rules: title must contain "data"/"dataset"; keywords 4–8,
> semicolon-separated, no title-word repeats; abstract 100–500 words
> describing collection + dataset + reuse potential, no interpretation.

## Article title

AerialFuseCV: an instance-level paired oriented-box and instance-mask
dataset for aerial imagery derived from DOTA v1.0 and iSAID

## Keywords (6; none repeat a title word)

object detection; segmentation; remote sensing; deep learning; annotation
reconciliation; earth observation

## Abstract — DRAFT (~210 words; window 100–500)

AerialFuseCV pairs the oriented bounding-box annotations of DOTA v1.0 with
the pixel-level instance masks of iSAID at the level of individual object
instances. Although both benchmarks annotate the same aerial imagery, their
annotations were produced independently and share no instance
correspondence. The dataset was constructed by decoding iSAID's
color-encoded instance masks, extracting per-instance regions through
clipping with the corresponding DOTA oriented-box polygons, and accepting
box–mask pairs under a conservative intersection-over-union rule
(IoU ≥ 0.1); images failing structural checks were discarded (12 in total).
The result contains 1,857 images (1,401 training, 456 validation) with
125,102 validated box–mask pairs across the 15 DOTA v1.0 object categories,
corresponding to an overall match rate of 97.9% (98.1% training, 97.2%
validation); per-class match rates are reported for transparency. The
deposit provides all pairing annotations and metadata, per-class statistics,
and a construction pipeline with verification checksums that rebuilds the
dataset from the official DOTA v1.0 and iSAID distributions, whose imagery
cannot be redistributed directly. AerialFuseCV supports training and
evaluation of aerial instance-segmentation methods that require linked box
and mask supervision, including detection-to-segmentation pipelines built on
promptable segmentation models, without any re-annotation effort.

*Every number above traces to `ATHENA_STATE.md` § verified thesis results.*
