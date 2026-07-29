# P1 Value of the Data — DRAFT v0.1 (2026-07-29)

> Template rules: 3–6 bullets; why valuable + how reusable; NO background,
> interpretation, or conclusions.

- AerialFuseCV is, to the authors' knowledge, the first publicly available
  dataset linking oriented bounding boxes and pixel-level instance masks for
  the same object instances in aerial imagery: 125,102 validated box–mask
  pairs over 1,857 images and the 15 DOTA v1.0 categories.
- Researchers in aerial and satellite computer vision can train and evaluate
  methods that require joint box and mask supervision — instance
  segmentation, detection-to-segmentation pipelines, and prompt-based
  segmentation with box prompts — without performing any re-annotation.
- Every pairing decision is transparent: the deposit includes per-class match
  rates, the conservative acceptance threshold (IoU ≥ 0.1), and the list of
  excluded images, allowing users to assess fitness for their task
  class-by-class.
- The construction pipeline and verification checksums make the dataset fully
  reproducible from the official DOTA v1.0 and iSAID distributions, and the
  reconciliation methodology is directly transferable to other
  box-annotated / mask-annotated dataset pairs that share source imagery.
