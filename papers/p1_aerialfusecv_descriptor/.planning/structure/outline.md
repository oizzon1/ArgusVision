# P1 Outline — Data in Brief mandatory template

Section order is fixed by the venue (see
`.claude/write-the-f-paper/venues/data-in-brief.yaml` and the official guide
in `papers/shared/venues/data-in-brief/`). Budgets total ≈2,600 words of
prose — DiB articles are short by design.

| # | Section | Budget | Content anchor |
|---|---|---|---|
| 0 | Title + keywords (4–8, semicolons, no title-word repeats) | — | "AerialFuseCV: an instance-level paired oriented-box and mask **dataset** for aerial imagery (DOTA v1.0 + iSAID)" — title MUST contain "data"/"dataset" (template v19 rule) |
| 1 | Abstract | 100–500 w (template v19; target ~250) | Collection process + dataset + reuse potential. No interpretation. |
| 2 | Specifications Table | fields | Subject: Computer Vision; Specific subject area ≤150 chars; Type: annotations + metadata + scripts (JSON/TXT/PNG-refs/Python); Collection: derived + reconciled from DOTA v1.0 + iSAID; Accessibility: Zenodo DOI + URL; Related article: TBD (none/thesis) |
| 3 | Value of the Data | 4 bullets, ~150 w | (a) first instance-level box–mask pairing for aerial imagery; (b) enables detect-then-segment and instance-seg research without re-annotation; (c) validated match quality with per-class transparency; (d) fully reproducible from official sources |
| 4 | Background (CONFIRMED in template v19) | ~200 w | DOTA/iSAID share imagery, annotations unlinked; why pairing is nontrivial (instance correspondence, color-encoded masks) |
| 5 | Data Description (v0.1 drafted 2026-07-30; now also carries the **box-anchored two-retention-rate** subsection — box side 97.9%, mask side ~37.8% — the honest framing a reviewer would otherwise demand) | ~700 w + 2 figs + 2 tables | Deposit tree file-by-file; splits table (1,401/456); per-class instance counts + match rates table; example-pair figure; class-distribution figure |
| 6 | Experimental Design, Materials and Methods | ~900 w + 1 fig | Construction pipeline: source acquisition → mask color decoding (iSAID conventions, corrected color table) → OBB-polygon ∩ class-mask instance extraction → conservative IoU ≥ 0.1 matching → discard rules (12 images) → verification checksums. Pipeline flow diagram. |
| 7 | Limitations | ≤200 w | Conservative matching leaves 2.1% unpaired (worst classes named); severe class imbalance (71%/top-3); inherits DOTA v1.0 annotation quality; images not redistributed (rebuild required) |
| 8 | Ethics / CRediT / Declarations / Acknowledgments | ~100 w | No human/animal data; CRediT: Fragkos (all roles), supervisor per contribution; funding TBD |

## Reference budget
Template v19: **max 20 references**, numbered `[n]`; must include the Zenodo
deposit itself, DOTA, iSAID, and only load-bearing related-dataset citations
— no citation padding, self-citations only where essential.

## Figure/table plan (4 + 2)
- F1 example image with paired OBB + instance mask overlay
- F2 class distribution (log scale)
- F3 construction pipeline diagram
- T1 split statistics; T2 per-class counts + match rates

## Order of writing
6 → 5 → 7 → 3 → 4 → 2 → 1 (methods first — everything else summarizes it).
