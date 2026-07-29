# P1 Specifications Table — DRAFT v0.1 (2026-07-29)

> Fill into the locked template table verbatim. `⛔ P0` marks fields blocked
> by the Zenodo release.

| Field | Entry |
|---|---|
| Subject | Computer Vision and Pattern Recognition *(select from template dropdown; verify exact wording)* |
| Specific subject area | Instance-level paired object detection and segmentation annotations for aerial and satellite imagery *(93 chars w/o spaces — under 150 ✓)* |
| Type of data | Annotation files (text, DOTA format), pairing metadata (JSON), per-class statistics tables (JSON/CSV), construction scripts (Python), verification checksums (text). Processed and analyzed data derived from publicly available source datasets. |
| Data collection | Derived by reconciling two existing annotation sets over the same aerial imagery: oriented bounding boxes from DOTA v1.0 and color-encoded instance masks from iSAID. Per-instance masks were extracted by polygon clipping of class-level masks with DOTA oriented boxes and paired under a conservative IoU ≥ 0.1 acceptance rule; 12 images failing structural checks were excluded. No new imagery was collected. |
| Data source location | Source datasets: DOTA v1.0 and iSAID (official public distributions). Deposit: Zenodo. Institution: National Technical University of Athens, Greece. |
| Data accessibility | Repository name: Zenodo · Data identification number: ⛔ P0 DOI · Direct URL: ⛔ P0 · Instructions: annotations and metadata are directly downloadable; the imagery-linked portions are rebuilt from the official DOTA v1.0 and iSAID downloads using the included construction script, verified by checksums (source imagery is not redistributable). |
| Related research article | None. *(Template: state explicitly that the manuscript is not related to a research article; revisit if P2 is submitted first — it will not be.)* |
