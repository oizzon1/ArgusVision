# P1 Narrative Arc (within DiB's constraints)

DiB forbids interpretation, so the "narrative" is carried entirely by
selection and ordering of facts — the reader should finish with the problem,
journey, and resolution inferred, never stated as argument.

## Problem (reader's opening state)
A researcher wanting paired box+mask supervision on aerial imagery finds
DOTA (boxes, no masks) and iSAID (masks, no linked boxes) built on the same
images — and no way to join them at instance level.

## Journey (what the Methods quietly demonstrate)
Instance correspondence is not a trivial join: color-encoded instance masks
must be decoded (including two historically miscopied class colors),
per-instance regions extracted via OBB-polygon clipping, and matches accepted
only under a conservative IoU rule that prefers dropping a pair over
fabricating one — with every rejection accounted for (2.1%, per-class,
12 whole images discarded by rule).

## Resolution (reader's closing state)
One `zenodo_record + construction script` later, they hold 125,102 validated
pairs with known per-class quality floors — and a citable DOI.

## Reader experience targets
- Abstract alone suffices to decide relevance (scale + pairing + DOI).
- Specifications Table alone suffices to obtain the data.
- Limitations read as confidence, not confession: every weakness is
  quantified and located, none discovered by the reviewer first.

## Tone
Documentary precision. Zero adjectives of enthusiasm ("novel", "rich",
"comprehensive" — banned). Numbers do the persuading.
