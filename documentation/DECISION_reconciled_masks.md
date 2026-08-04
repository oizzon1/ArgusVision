# Decision Record — Reconciled Masks

**Status: ACCEPTED, 2026-07-31.** Evidence:
`results/experimental/AerialFuseCV_Testing/annotation_discrepancy/` (125,722 pairs, all
measured — no sampling).
**Companion:** `documentation/DECISION_unpaired_annotations.md` (scope),
`TODO_AERIALFUSECV_REBUILD.md` (steps).

---

## 1. Decision

**AerialFuseCV's released mask for a paired object is the matched iSAID
instance clipped to that object's oriented bounding box.**

```
reconciled_mask = iSAID_instance(matched)  ∩  polygon(DOTA oriented box)
```

Not the class-coloured semantic mask clipped by the box (the precursor's
derivation), and not the iSAID instance as drawn.

## 2. Why: the measurement

Two candidate ground truths were compared for every pair — the polygon-clipped
semantic mask and the exact iSAID instance. They agree on only **21.7%** of
objects (mean IoU 0.918, median 0.946). Decomposing the disagreement by pixel:

| Cause | Share | Pixels |
|---|---|---|
| **Extent** — iSAID annotates a larger region than the box delimits | **90.0%** | 15,270,258 |
| **Foreign** — clip contains pixels of a *different* iSAID instance | **10.0%** | 1,689,081 |
| Unlabelled — class-coloured pixels belonging to no instance | 0.0% | 0 |

**16.3% of pairs (20,489) contain at least some foreign pixels.**

Both failure modes are real, and the reconciled definition addresses each by a
different mechanism:

- **Extent** is handled by the clip. The released mask cannot exceed the box,
  so it is consistent with the annotation that delimits it.
- **Foreign contamination is eliminated by construction**, not subtracted:
  starting from the matched instance rather than the class mask means another
  object's pixels can never enter. This is only possible because the build
  holds per-instance identities.

The two derivations coincide where `unlabelled = 0`, which the measurement
confirms exactly — so nothing is lost relative to the class-mask route.

## 3. Why extent disagreement is not an error to fix

Inspection of the worst cases (`results/experimental/AerialFuseCV_Testing/gt_mask_comparison/`)
showed `extra = 0px` throughout: the sources **annotate different extents of
the same object**, by convention rather than by mistake.

- **baseball-diamond** — DOTA boxes the infield; iSAID annotates the whole
  field. Agreement 0.937 but **100%** of its disagreement is extent.
- **harbor** — DOTA boxes the pier; iSAID includes the adjoining platforms.
  99.5% extent.
- **ground-track-field, tennis-court, roundabout** — 100% extent.

Neither source is wrong. But a box-prompted method must not be scored against
an extent its prompt never covered, which is precisely what clipping prevents.

Separately, genuine **iSAID annotation errors** exist: in P0262 a single
instance covers a boat, its dock, and a second boat — verified as one colour in
one connected component, so not an artefact of our extraction. Clipping bounds
the damage from these too.

## 4. Where contamination actually lives

Foreign pixels concentrate in dense classes, exactly as expected:

| Class | pairs with foreign px |
|---|---|
| storage-tank | 27.6% |
| plane | 25.2% |
| helicopter | 21.6% |
| ship | 19.4% |
| small-vehicle | 16.9% |
| large-vehicle | 14.1% |

against **≤2.3%** for bridge, harbor, tennis-court, roundabout and the sports
fields. Note `plane` is the one class where extent is *not* dominant (21.8%) —
its disagreement is mostly contamination, because aircraft are parked in tight
rows and wings overlap neighbouring boxes.

## 5. The claim to make, and the one to avoid

**Avoid:** "box and mask agree 100%." That is circular — masks defined by
clipping to the box agree with it by construction, and a reviewer will say so.

**Make:** *the released masks are consistent with the annotation that delimits
them, so a box-prompted method is evaluated against ground truth its prompt
could in principle produce, and no mask contains a neighbouring object's
pixels.* That is a statement about **evaluation validity**, and it is
defensible because both halves are measured.

## 6. Traceability

The iSAID instance identifier stays in `pairs.jsonl`, so the original
unclipped instance is always recoverable from the user's own iSAID download.
The derivation is auditable and reversible; nothing is hidden.

## 7. Known residual — ours to fix

**2.61% of pairs (3,283)** reference an instance whose colour spans multiple
disconnected components. Some are legitimate occlusion splits; some are iSAID
colour reuse, which our colour-keyed extraction would merge. Clipping to the
box bounds the consequence — a distant fragment sharing a colour falls outside
the box and is removed — but the underlying extraction should still be
component-aware. Tracked as step 2 of `TODO_AERIALFUSECV_REBUILD.md`.
