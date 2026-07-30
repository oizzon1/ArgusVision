# Decision Record — Dataset Scope and the Treatment of Unpaired Annotations

**Status: ACCEPTED, 2026-07-30.** Decided by the candidate; recorded by ATHENA.
**Scope:** AerialFuseCV construction, the evaluation stack, and the reporting
rules for P2/P4.

---

## 1. Decision

**AerialFuseCV contains exact box–mask pairs and nothing else.** Every
discarded object is logged with the reason it was discarded, but the released
dataset is clean and paired.

The scope statement is the whole argument:

> Evaluating a **detector**? Use DOTA v1.0.
> Evaluating a **segmentation** model? Use iSAID.
> Evaluating a **unified detection→segmentation system**? Use AerialFuseCV.

Each dataset does one job. AerialFuseCV's job is the verified correspondence
between an oriented box and the mask of the same physical object — which no
other public dataset provides, and which is precisely what a unified pipeline
needs in order to be scored on both stages against the same object.

## 2. The situation being resolved

DOTA v1.0 and iSAID annotate the same imagery independently, so their object
sets do not coincide. Measured over all 1,869 images
(`results/isaid_colour_audit/colour_audit.json`):

- iSAID contains **475,438** instances; DOTA contains **127,843** boxes.
- iSAID annotators included many objects DOTA omitted — small and partially
  occluded vehicles above all.
- A minority of DOTA boxes have no corresponding iSAID mask.

Fusion therefore yields three populations: paired, box-without-mask, and
mask-without-box. Only the first is in scope.

## 3. Why not keep the unpaired objects

An earlier draft of this record argued for retaining everything with pairing
flags and filtering at evaluation time. **That position was wrong, and the
reasoning that killed it is worth preserving:**

The retention argument rested on "deleting unpaired objects discards ~205,000
mask instances permanently." It does not. Those instances remain in iSAID,
publicly, in full. We are not the custodian of iSAID's masks or DOTA's boxes,
and excluding them destroys nothing — it **defines a scope**. Once that is
clear, the retention case reduces to "someone might want a filtered variant",
which is a poor reason to complicate a published artefact.

Retention also carried real costs: a dataset serving three purposes is harder
to describe, cite and use correctly; side tables and a `paired_only` reader
flag invite misuse by anyone who forgets to set them; and the deposit grows
without adding anything a user could not obtain from the sources directly.

## 4. The metric hazard, and why scope resolves it

Raised by the candidate: during pipeline evaluation a detected box prompts SAM,
SAM returns a mask, and if no ground-truth mask exists for that object the
comparison has nothing to score against. Scoring it as IoU 0 would penalise the
system for the **annotation's** absence rather than for any failure of its own.

With a pairs-only dataset the hazard cannot arise: every ground-truth object
has both a box and a mask by construction. The problem is eliminated at the
source instead of mitigated downstream.

## 5. The known cost, and the answer to it

Removing unpaired boxes means a detector that correctly finds one of those
objects is charged a **false positive**, because our labels no longer record
it. Roughly 2.1% of DOTA's boxes are affected.

**The answer is the scope statement.** AerialFuseCV is not a detection
benchmark; a detector's absolute precision should be measured on DOTA, which
annotates every object it knows about. What AerialFuseCV measures is a unified
system's behaviour on objects that possess both annotation types.

For P2 specifically: every method compared is evaluated against the identical
label set, so the artefact is constant across the comparison and cannot favour
one approach over another. It must still be stated in P1's Limitations and
quantified from the discard log rather than hand-waved.

## 6. Accounting: the discard log

Exclusion must be explainable, arguable and reproducible, so the build records
every discarded object:

- **`discarded.jsonl`** — one record per dropped object: kind (box or
  instance), class, image, split, the reason, the best IoU achieved, and the
  geometry (box corners) or instance identity (RGB, pixel area).
- **`dataset_statistics.json` → `discarded`** — counts by reason, by kind and
  by class.

Reasons recorded:

| Reason | Meaning |
|---|---|
| `box:no_mask_instance_of_class` | no instance of that class anywhere in the image |
| `box:no_overlapping_instance` | instances exist, none overlaps the box |
| `box:below_iou_threshold` | best overlap fell under the acceptance threshold |
| `box:lost_to_one_to_one_assignment` | overlapped adequately, but the instance went to a better-fitting box |
| `instance:no_box_of_class` | no box of that class in the image |
| `instance:no_overlapping_box` | boxes exist, none overlaps the instance |
| `instance:unassigned` | overlapped, but not selected by the assignment |

The accounting is exact and checked: `source boxes = pairs + discarded boxes`
and `source instances = pairs + discarded instances`, verified on every build.

This is what makes the exclusion defensible. The dataset is clean; the record
of what was excluded, and why, is complete.

## 7. Evaluation-stack consequence

`SegmentationEvaluator.add_gt_without_mask()` — an object excluded from mask
averaging rather than scored zero — was added while the retention approach was
under consideration. **It is retained deliberately**, although it is
unreachable when evaluating on AerialFuseCV, where every object has a mask by
construction. It becomes necessary for P4's cross-dataset work on DIOR and
NWPU VHR-10, whose annotation coverage differs, and the tests pinning the
distinction between an *excluded* object and a *missed* one guard a semantic
that is easy to collapse by accident.

## 8. Anticipated challenges

**"Your pairing rate is measured on the subset you kept."**
No: the rates are computed against the *source* populations — 127,843 boxes and
475,438 instances — and both the box-side and instance-side rates are reported,
along with the full discard breakdown.

**"You excluded the hard cases."**
Exclusion depends only on whether both source datasets annotated the object. It
is fixed before any model runs, identical for every model compared, and
independent of any prediction.

**"Why not just use iSAID, which annotates more?"**
iSAID provides no oriented boxes. The paired correspondence is the
contribution.

---

*Companion records: `ATHENA_STATE.md` § DECIDED · `TODO_RECREATION_SCRIPT.md` ·
`Athena_Protocols/WORK_LOG.md` 2026-07-30.*
