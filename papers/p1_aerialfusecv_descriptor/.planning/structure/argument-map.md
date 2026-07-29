# P1 Argument Map

## Central thesis
AerialFuseCV is the first dataset pairing DOTA v1.0 OBB annotations with
iSAID instance masks at instance level — 125,102 validated pairs, 1,857
images, 15 classes, 97.9% match rate, reproducible from official sources.

## Supporting claims (each traces to thesis / ATHENA_STATE)

1. **Novelty** — DOTA and iSAID share source imagery but their annotations
   were never linked instance-to-instance; existing aerial datasets offer
   boxes OR masks, not validated pairs.
   *Evidence: literature positioning from thesis Ch. 2 (verify citations at
   write time).*
2. **Scale & coverage** — 1,857 images (1,401 train / 456 val), 125,102
   bbox–mask pairs, 15 DOTA classes.
   *Evidence: thesis; ATHENA_STATE § verified results.*
3. **Quality, honestly characterized** — 97.9% overall match (98.1 train /
   97.2 val) under conservative IoU ≥ 0.1 matching; per-class floor
   documented (helicopter 83.6% val, harbor 89.6% train); 12 images
   discarded by rule; class imbalance quantified (top-3 classes = 71% of
   instances).
   *Evidence: thesis validation chapter.*
4. **Reproducibility** — deposit = annotations + pairing metadata +
   construction script + checksums; rebuilds from official DOTA/iSAID
   downloads (images not redistributable — standard DOTA-ecosystem practice).
   *Evidence: P0 Zenodo release contents (Aug 2026).*

## Logical flow
Novelty (why it didn't exist) → Scale (what it is) → Quality (why to trust
it) → Reproducibility (how to get it) — mapped onto the DiB template:
claims 1 lives in Value of the Data + Background; 2–3 in Data Description +
Specifications Table; construction + validation method in Experimental
Design; honesty caveats in Limitations.

## Known gaps / risks
- **P0 DOI must exist before submission** (hard blocker, Aug 2026).
- DiB rejects datasets with "insufficient variables or samples" — we clear
  this by orders of magnitude; state scale prominently in abstract.
- Per-class floors and imbalance must be IN the article (Limitations) — a
  reviewer discovering them post-hoc is the only real rejection risk.
- "Related research article": none at submission — confirm field accepts
  "none"/thesis reference (flagged in venue NOTES).
