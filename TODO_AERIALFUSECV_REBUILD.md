# TODO — AerialFuseCV Clean Rebuild & Annotation-Discrepancy Study

**Status: STEPS 1–6 COMPLETE.** Opened 2026-07-31; steps 1–6 executed same day.
**Consolidated findings: `results/AerialFuseCV_Testing/FINDINGS.md`.**
**All evidence for this work lives in `results/AerialFuseCV_Testing/`** — a
one-time job whose artefacts become legacy once the dataset is released.
**Companion records:** `TODO_RECREATION_SCRIPT.md` (build design and findings
R1–R5, licensing), `documentation/DECISION_unpaired_annotations.md` (scope),
`Athena_Protocols/{ATHENA_STATE.md,WORK_LOG.md}`.

**Goal.** A clean, verified, single-purpose AerialFuseCV — exact box–mask pairs
for unified detection→segmentation systems — plus the measured evidence behind
every construction decision, kept so it can be cited later.

---

## Where we are

- Corrected build exists: `dataset/AerialFuseCV_v1` — 125,722 pairs, 1,862
  images, oriented-polygon matching, one-to-one assignment, DOTA-native
  annotations, both `labels_obb/` and `labels_hbb/`. Self-consistency audit
  passed in full.
- Port fidelity proven: a semantic-mode build reproduced the precursor dataset
  exactly (0 label mismatches, 0 mask mismatches, pair delta +0).
- Pipeline experiment run on it: detection improved (precision +0.0057, mean AP
  +0.0131); segmentation flat because the evaluation never reads instance masks.
- **Open question that drives everything below:** polygon-clipped GT and exact
  iSAID instance GT agree on only 18.5% of instances. Inspection showed the
  dominant cause is *not* contamination but a genuine difference in annotated
  extent between DOTA and iSAID — plus outright iSAID errors.

---

## Steps

### 1. Measure the discrepancy properly — ✅ DONE 2026-07-31
Decides whether a reconciled-mask claim is true at all.
- [ ] Split disagreement into `extra` (neighbour intrusion) vs `missing`
      (extent convention), per class, across all pairs
- [ ] Count clipped masks containing pixels of a **different** iSAID instance —
      exactly detectable now that instance identities are held
- [ ] Quantify multi-piece colour instances dataset-wide (2.4% in a sample)
- [ ] Classify causes: convention difference · iSAID annotation error · our
      extraction merging
- [ ] Output → `results/AerialFuseCV_Testing/annotation_discrepancy/` with a
      manifest, plus figure material

### 2. Fix what is ours — ⚠ PARTIAL: measured (2.61% of pairs), extraction not yet component-aware
Before publishing numbers about anyone else's annotations.
- [ ] Split colour instances into connected components where they are genuinely
      separate objects; decide the occlusion-vs-reuse rule from evidence
- [ ] Record the rule and its reasoning as a decision document
- [ ] Re-run step 1 so the measured discrepancy excludes our own artefacts

### 3. Define the reconciled masks — ✅ DONE (`documentation/DECISION_reconciled_masks.md`)
- [ ] Specify the derivation exactly (class mask ∩ oriented polygon; fallback
      when the class mask is empty inside the box)
- [ ] Decide whether the derivation must also exclude foreign-instance pixels —
      depends on step 1's contamination figure
- [ ] **Framing caution:** "100% box–mask agreement" is circular as a claim.
      State it as *evaluation validity* — the released masks are consistent
      with the annotation that delimits them, so a box-prompted method is
      scored against ground truth its prompt could produce.
- [ ] Write the decision document before implementing

### 4. Rebuild with reconciled masks — ✅ DONE (`dataset/AerialFuseCV_reconciled`)
- [ ] Masks become ours; the iSAID instance identifier stays in the
      correspondence so the original is always recoverable
- [ ] Decide whether both mask directories ship
- [ ] Full build + self-consistency audit

### 5. Re-run the pipeline experiment — ✅ DONE (+0.0012 seg IoU; required a loader fix first)
- [ ] Same models and config; compare against
      `results/AerialFuseCV_Testing/pipeline_aerialfusecv_v1`
- [ ] This is the "effect on evaluation" evidence the paper needs

### 6. EDA — ✅ DONE (`results/AerialFuseCV_Testing/eda/`)
- [ ] `dataset/analyze_aerialfusecv.py` → `dataset_statistics.json` +
      `DATASET_ANALYSIS.md` + the four P1 figures
- [ ] Funnel, per-class statistics, IoU distributions, discrepancy tables

### 7. Deliverable rebuild script + verification build — ⛔ BLOCKED on licensing answers
- [ ] Written clean, to scope — no modes, no comparisons, no history
- [ ] Rebuild with it and verify identical to the internal build
- [ ] **Gated on licensing answers** (NTUA research-data office · DOTA/iSAID
      authors · venue pre-submission enquiry)

### 8. Clean the work area — ⛔ gated on step 7
- [ ] Delete superseded dataset directories once the final build verifies
      (`AerialFuseCV`, `AerialFuseCV_Refined`, `AerialFuseCV_regression`,
      `AerialFuseCV_v1`) — all are deterministically regenerable
- [ ] Keep `results/AerialFuseCV_Testing/` as the evidence record

### 9. Papers
- [ ] Re-source P1 numerically from `dataset_statistics.json` — every current
      number is provisional
- [ ] Decide venue once the discrepancy analysis has a measured size: Data in
      Brief if modest, otherwise a fuller venue (ISPRS Open Journal was raised)
- [ ] Carry forward: the official-benchmarking Value-of-the-Data point, and the
      training-side subset caveat (1.66% of DOTA boxes absent)

---

## Deferred, tracked elsewhere
- `argusvision` VBB → HBB rename (user-deferred; note in `TODO_RECREATION_SCRIPT.md`)
- Stale comment in `pipeline/prompts.py` calling the hull conversion "legacy OBB->VBB"
- `evaluate_sam.py` port as a driver kind, at P4 prep

---

*Every step lands in `results/AerialFuseCV_Testing/` with a manifest; every
decision becomes a dated record in `documentation/`.*
