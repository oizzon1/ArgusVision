# P1 Methods — superseded 2026-08-04 (task P1-WRITE)

**Not maintained.** Canonical text: `../DRAFT_P1.md` § Experimental Design,
Materials and Methods.

The v0.1 text described `refine_aerialfusecv.py` and a five-stage narrative
inherited from the thesis. The shipped construction is a single script whose
algorithm differs on every substantive point:

- Matching is scored on the rasterised oriented quadrilateral, not on the
  axis-aligned hull rendered as a filled rectangle. Over 21,265 boxes the hull
  inflates the matching region by a median factor of 1.83.
- Candidates are iSAID instances decoded from the instance-identity encoding,
  not connected components of a category mask inside a padded crop.
- Assignment is an optimal one-to-one assignment maximising total
  intersection-over-union per category, not an independent best-per-box choice.
  Two boxes can therefore no longer claim the same mask.
- The released mask is the matched instance clipped to its oriented box.
- Annotations stay in DOTA's native format; the YOLO OBB normalisation
  described in v0.1 Stage 2 is not part of the shipped dataset.

The v0.1 "PENDING" note recorded that Stages 1 and 3 had no committed script.
That blocker is closed: construction is one committed script that records its
own git revision and arguments in `build_manifest.json`. A deposit-scoped
rebuild script remains outstanding as separate work.
