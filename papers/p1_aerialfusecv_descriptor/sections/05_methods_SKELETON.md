# P1 Experimental Design, Materials and Methods — SKELETON (2026-07-29)

> The template's biggest section (~900 w budget, no hard limit). NOT drafted
> yet — must be written against the actual construction scripts in `dataset/`
> and the thesis methods chapter in a dedicated session, stage by stage, so
> every operational detail (thresholds, color decoding, discard rules) is
> code-verified rather than remembered. P0 packaging will reorganize the
> scripts into `tools/dataset_construction/` — write this section AFTER P0
> freezes that layout, so script names in prose match the deposit.

Planned stages (verify each against code before writing):

1. **Source acquisition** — official DOTA v1.0 + iSAID downloads; expected
   versions and checksums.
2. **Mask color decoding** — iSAID color-encoding conventions; the corrected
   class-color table (two historically miscopied values fixed:
   storage-tank, bridge — now canonical in `argusvision.data.constants`).
3. **Instance extraction** — per-class binary masks; OBB-polygon clipping to
   isolate instances (avoids connected-component index mismatch).
4. **Pairing** — candidate generation per class; conservative acceptance
   IoU ≥ 0.1; one-to-one constraint handling.
5. **Quality control** — structural checks; the 12 discarded images and the
   discard criteria; per-class match-rate computation (97.9% overall,
   98.1/97.2 train/val).
6. **Packaging & verification** — output formats (labels, metadata JSON),
   checksum generation, rebuild verification (end-to-end reproducibility run
   is a P1 roadmap task, 3–5 days, before submission).

Figure F3 (pipeline diagram) belongs to this section.
