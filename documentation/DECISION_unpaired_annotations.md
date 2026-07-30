# Decision Record — Unpaired Annotations: Retention and Evaluation Semantics

**Status: ACCEPTED, 2026-07-30.** Decided by the candidate; recorded by ATHENA.
**Scope:** AerialFuseCV construction, the evaluation stack, and the experimental
protocol for P2/P4.
**Supersedes:** the precursor build's behaviour, which deleted unpaired
annotations at construction time.

---

## 1. The situation

DOTA v1.0 and iSAID annotate the same imagery independently, so their object
sets do not coincide. Measured over all 1,869 images
(`results/isaid_colour_audit/colour_audit.json`, and the build's own
statistics):

- iSAID contains **475,438** instances; DOTA contains **127,843** boxes.
- iSAID annotated many objects DOTA omitted — small and partially occluded
  vehicles above all.
- A minority of DOTA boxes have no iSAID mask at all.

Fusing them therefore produces three populations, not one:

| Population | Box GT | Mask GT | Count (precursor build) |
|---|---|---|---|
| **Paired** | yes | yes | ~125,102 |
| **Box without mask** | yes | **no** | ~2,741 |
| **Mask without box** | **no** | yes | ~205,000+ |

Both unpaired populations are *real annotated objects*. Neither is an error.

## 2. The hazard that forced the decision

Raised by the candidate, and it is correct: during pipeline evaluation a
detected box prompts SAM, SAM returns a mask, and if no ground-truth mask
exists for that object the comparison has nothing to score against. If the
evaluator treats that as IoU 0, the system is penalised for the *annotation's*
absence rather than for any failure of its own. Enough such cases and the
segmentation metric stops measuring segmentation.

This is precisely why the precursor deleted unpaired annotations: with only
paired objects present, every detection can be scored on both tasks and the
artefact cannot arise.

## 3. Why deletion is nonetheless the wrong fix

Deletion solves a **protocol** problem by mutilating the **data**:

1. **It discards ~205,000 mask instances** — about 62% of what iSAID provides —
   permanently, from a dataset we intend to publish as a reusable resource.
2. **It cripples single-task use.** With unpaired boxes removed the labels no
   longer describe everything DOTA annotated, so the dataset is unusable as a
   detection benchmark; with unpaired masks removed it is unusable as an
   instance-segmentation benchmark.
3. **It makes the choice irreversible and invisible.** A future user — or a
   future us, designing P4 — cannot revisit a decision that has been baked into
   the files, and cannot even see that it was made.
4. **It hides the annotation gap that is scientifically interesting.** The
   DOTA/iSAID divergence is a real, quantifiable property of these benchmarks.

## 4. Decision

**Keep every annotated object. Mark pairing status. Enforce the evaluation rule
explicitly, in code, with the safe option as the default.**

**Construction.** All DOTA boxes are written to the label files and all iSAID
instances are painted into the masks, each carrying a pairing status. The
correspondence lives in `pairs.jsonl`; every unpaired object is recorded in
`unpaired.jsonl` with its failure reason (no class mask present, no overlapping
candidate, sub-threshold IoU). Nothing the sources provided is thrown away.

**Loading.** The dataset accessor exposes `paired_only=True` **by default**, so
the safe behaviour is what a caller gets without thinking about it. Retrieving
the complete population is an explicit opt-in.

**Evaluation.** `SegmentationEvaluator` gains a third outcome beside the two it
has. The three are:

| Outcome | Meaning | Effect on mask metrics |
|---|---|---|
| `add_pair` | detected, GT mask exists | scored normally |
| `add_missed_gt` | GT mask exists, detector missed it | contributes **0.0** to the GT-anchored view — a real failure |
| `add_gt_without_mask` *(new)* | GT box exists, **no GT mask** | **excluded from both averages**, counted and reported |

The rule keys on the **mask ground truth's existence, independently of the
detection outcome**: an object with no GT mask is excluded whether or not the
detector found it, because a mask that was never drawn cannot be missed.

`DetectionEvaluator` is unaffected. The box ground truth exists in every case
under discussion, so detection scoring is unchanged.

## 5. What the experiments must report

Any pipeline result produced under this protocol reports, together:

1. **Detection metrics over all annotated boxes** — a detector should find
   every object DOTA annotated, paired or not.
2. **Mask metrics over the subset possessing ground-truth masks**, with both
   the TP-only and GT-anchored views retained as now.
3. **The size of the excluded population**, stated rather than implied. A mask
   metric computed over 97.8% of detections is a different claim from one
   computed over all of them, and the difference must be visible.

An experiment that reports (2) without (3) is not acceptable under this
protocol — that is exactly the silent distortion the decision exists to
prevent.

## 6. Anticipated challenges, and the answers

**"You excluded the cases your system handled worst."**
No: exclusion is decided by the *annotation's* existence, which is a property
of the source datasets, fixed before any model runs and independent of any
prediction. The excluded set is identical for every model compared.

**"Reporting over a subset inflates your numbers."**
The subset and its size are reported alongside every figure, and the GT-anchored
view still charges the system for every detection miss. What is removed is only
the case where no ground truth exists in either direction.

**"Then your dataset's 'pairs' figure is not the dataset size."**
Correct, and stated as such. The dataset contains all annotated objects; the
paired subset is a property *of* the dataset, reported per class on both the
box side and the mask side.

**"Why not simply use iSAID, which annotates more?"**
Because iSAID provides no oriented boxes. The pairing is the contribution.

## 7. Consequences

- **AerialFuseCV** ships the complete annotation population plus the pairing
  relation — strictly more information than the precursor, and usable for
  detection, segmentation, or paired tasks.
- **P1** loses two Limitations entries that become false (instance
  inseparability; two boxes claiming one component) and gains a Data
  Description subsection on the three populations and the retention rates on
  both sides.
- **P2/P4** must report per §5. The evaluation stack enforces it by making the
  excluded count a first-class output rather than an omission.
- **The evaluation stack is no longer frozen in the form validated on
  2026-07-29.** This change is deliberate, tested, and recorded here; any
  numbers produced before it are unaffected because the new outcome is only
  reachable from data that carries pairing flags.

## 8. Out of scope, flagged not forgotten

**The symmetric gap: a GT mask with no GT box.** In our pipeline such an
instance is never prompted, so it never reaches mask scoring — but a detector
that fires on it is charged a false positive for finding a genuinely annotated
object that DOTA merely omitted. With pairing flags now retained, this becomes
*measurable* for the first time, and a reviewer familiar with the DOTA/iSAID
discrepancy may well raise it. Not addressed now; revisit when P2's detection
numbers are in hand, and consider reporting a "false positives coinciding with
unpaired iSAID instances" diagnostic.

---

*Companion records: `ATHENA_STATE.md` § DECIDED · `TODO_RECREATION_SCRIPT.md`
(construction) · `Athena_Protocols/WORK_LOG.md` 2026-07-30.*
