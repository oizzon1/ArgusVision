# Publication Roadmap v2.1
### ArgusVision PhD — Panagiotis Fragkos
**Base:** Master Thesis (Phase 0) — Object Detection and Semantic Segmentation of Aerial and Satellite Imagery with Deep Learning
**Program:** PhD in Photogrammetry, NTUA | **Supervisor:** Prof. Charalampos Ioannidis
**Roadmap version:** 2.1, 2026-07-29 (supervisor-finalized paper plan) | **Replaces:** v2.0, July 2026

> **Status: LIVING DOCUMENT.** Revised only through the Roadmap Revision Protocol in `Athena_Protocols/ATHENA_RISE.md` (triggers: supervisor instruction · new finding · milestone outcome · external event). Minor version bump for date/venue/scope changes, major bump for papers added/cancelled/merged. Every revision is recorded with reasoning in the changelog at the bottom of this file and mirrored to `ATHENA_STATE.md`.

---

## Strategy Change from v1

The draft planned four journal papers, opening with a VBB vs OBB letter. That letter compared COCO-pretrained VBB models against DOTA-pretrained OBB models, which confounds representation with training domain. Rather than defend a vulnerable standalone claim, the VBB/OBB material moves inside the flagship paper together with a new ablation (VBB trained on DOTA HBB annotations) that resolves the confound.

The fast first publication is now the dataset descriptor at a fast community venue instead of Scientific Data, whose review times run 4 to 8 months. A conference paper is added as insurance and visibility.

**Regulation context:** NTUA requires at least 3 peer-reviewed publications to defend. Conference papers count. This plan yields 4 countable items, with the third expected accepted by mid Year 2.

---

## Overview

| # | Order | Paper | Type | Target Submit | Expected Acceptance |
|---|---|---|---|---|---|
| P0 | prereq | AerialFuseCV Zenodo release (DOI) | Data release | Aug 2026 | DOI live immediately |
| P1 | 1st | AerialFuseCV: A Paired Detection–Segmentation Dataset for Aerial Imagery | Data descriptor | Sep 2026 | Nov–Dec 2026 |
| P2 | 2nd | Training-Free Detection to Segmentation for Aerial Imagery (flagship) | Full journal paper | Feb 2027 | Late 2027 |
| P3 | 3rd | Conference paper (condensed pipeline findings) | Conference (peer reviewed) | Nov 2026 or Jan 2027 | Spring 2027 |
| P4 | 4th | ArgusVision Benchmark: Detector × Segmenter Combinations for Aerial Instance Segmentation | Benchmark paper | Sep–Oct 2027 | 2028 |

Beyond P0–P4, single-scope ideas are **parked** (see § Parked Single-Scope Papers): VBB vs OBB (with the resolving ablation), SAM batch processing, OBB prompt support. None are scheduled; none block the sequence.

---

## P0 — AerialFuseCV Zenodo Release (prerequisite, not a paper)

DOTA v1.0 and iSAID are released for academic use and cannot be redistributed as images. The release therefore contains annotations, pairing metadata, and a construction script that rebuilds AerialFuseCV from official DOTA and iSAID downloads. This is standard practice in the DOTA ecosystem.

| Task | Effort |
|---|---|
| Package annotations and pairing metadata (CC-BY 4.0 on our contribution) | 2 days |
| Construction script with verification checksums | 2–3 days |
| README with file structure, formats, usage | 1 day |
| Zenodo upload, DOI minted | 1 day |
| **Total** | **~1 week** |

The DOI becomes the citation anchor for P1, P2, P3, and P4 regardless of any review status.

---

## P1 — AerialFuseCV Data Descriptor

> First paired dataset reconciling DOTA v1.0 OBB annotations with iSAID instance masks at instance level. 1857 images, 125102 bbox–mask pairs, 15 classes, 97.9% overall match rate.

| Field | Detail |
|---|---|
| Type | Data descriptor, ~3000 words |
| Target submit | September 2026 |
| Content source | Thesis only, dataset already constructed |

### Venues

| Priority | Journal | IF (2024) | Notes |
|---|---|---|---|
| Primary | ISPRS Open Journal of Photogrammetry and Remote Sensing | no IF yet (Scopus indexed) | Community venue, recognized by committee, fast review |
| Fallback | Data in Brief (Elsevier) | ~1.2 | Fast, near-certain if methodology is sound |

### Extra Work Needed

| Task | Effort |
|---|---|
| P0 complete (blocking) | see above |
| End-to-end reproducibility run of construction pipeline | 3–5 days |
| Write descriptor (Background, Methods, Validation, Usage Notes) | 4–5 days |
| **Total** | **~2 weeks after P0** |

---

## P2 — Flagship: Training-Free Detection to Segmentation for Aerial Imagery

> Single paper carrying the thesis pipeline arc: what an integrated training-free YOLO to SAM pipeline achieves on aerial imagery, how SAM variants respond to prompt design, and where the pipeline stands against supervised end-to-end baselines (Mask R-CNN, YOLOv11-seg).
>
> **Scope finalized with supervisor, 2026-07-29.** The VBB-on-DOTA-HBB ablation is **out of P2** — the VBB-vs-OBB question moves to a parked single-scope paper. Consequence for writing: the thesis VBB result (0.34% F1, COCO-pretrained) may appear only as motivation, with the representation-vs-training-domain confound explicitly acknowledged as a limitation. P2 makes **no claim** that the VBB failure is a representation effect.

| Field | Detail |
|---|---|
| Type | Full journal paper, ~9000–10000 words |
| Target submit | February 2027 |
| Content source | Thesis plus new experiments below |

### Venues

| Priority | Journal | IF (2024) | Notes |
|---|---|---|---|
| Primary | ISPRS Journal of Photogrammetry and Remote Sensing | ~10.6 | Exact scope fit, high desk-reject bar, expect major revisions |
| Fallback | IEEE TGRS | ~7.5 | Broad RS and aerial perception |

### Already Complete (thesis)

- VBB zero-shot benchmark, 24 COCO-pretrained models (YOLOv8–v12), best F1 0.34%
- OBB benchmark, 10 DOTA-pretrained models (YOLOv8/v11 families), YOLOv11x-OBB F1 62.4%
- SAM GT-driven benchmark, 6 configs (ViT-H/L/B × Box/Point)
- Integrated pipeline (YOLOv11x-OBB → SAM-ViT-B-Box), seg IoU 0.679, timing decomposition, error propagation

### New Experiments Needed

| Experiment | Purpose | Effort |
|---|---|---|
| Mask R-CNN trained on AerialFuseCV | Supervised classic baseline | 3–5 days |
| YOLOv11-seg trained on AerialFuseCV | Supervised baseline, same family as detector | 2–3 days |
| Confidence-based segmentation filtering | Addresses the ~18.5% false-positive overhead | 2–3 days |
| PR curves at IoU 0.1 / 0.3 / 0.5 | Sensitivity analysis, post-hoc on existing predictions | 2–3 days |
| **Total** | | **~2–3 weeks, parallelizable** |

Removed in v2.1 (supervisor decision, 2026-07-29): **VBB-on-DOTA-HBB ablation** → parked VBB-vs-OBB paper; **Mask2Former** → supervisor named exactly two baselines. RT-DETR-seg was already dropped in v2.0 (weakest effort-to-value).

---

## P3 — Conference Paper (insurance and visibility)

> Condensed zero-shot pipeline findings. Conference-to-journal extension is accepted practice in this field, so no conflict with P2.
>
> **Confirmed kept in the finalized plan (2026-07-29).** Nothing new goes into it — same P2 findings at conference length. Value: a fast peer-reviewed acceptance toward the NTUA 3-paper rule, plus visibility before the journal paper lands.

| Field | Detail |
|---|---|
| Type | Short/full conference paper, peer reviewed (counts toward the 3-paper rule) |
| Content source | P2 material condensed, ~1–2 weeks writing |

### Venues (deadlines to be verified when calls open)

| Priority | Venue | Deadline (approx.) | Notes |
|---|---|---|---|
| Primary | EarthVision workshop at CVPR 2027 | ~Nov 2026 | Aerial/satellite CV audience, high visibility |
| Alternative | IGARSS 2027 | ~Jan 2027 | Large RS community venue |

---

## P4 — ArgusVision Benchmark (PhD Year 1–2 expansion)

> Full configuration space, **reframed in v2.1 as a detector × segmenter combination benchmark** (supervisor, 2026-07-29): many detectors crossed with many segmenters, plus training strategies and prompt designs, for aerial instance segmentation. The v2.0 framing (SAM variants only) is subsumed — the segmenter axis keeps all blocks below; a **detector axis is added** and must be designed before P4 planning (Mar 2027): candidate detectors, pretraining regimes, and which detector–segmenter pairs are worth running versus the full grid.

| Field | Detail |
|---|---|
| Type | Benchmark paper, ~12000–15000 words |
| Target submit | September–October 2027 |
| Content source | All new experiments, PhD Year 1 |

### Venues

| Priority | Journal | IF (2024) | Notes |
|---|---|---|---|
| Primary | IEEE TGRS | ~7.5 | Systematic benchmarks, realistic target |
| Stretch | ISPRS Journal | ~10.6 | Only if findings prove landmark-level |

Decision recorded: no CVPR/ICCV gamble for the benchmark. A TGRS paper citing our own dataset DOI and flagship is the stronger Year 1–2 outcome.

### Experiment Blocks

| Block | Content | Effort |
|---|---|---|
| SAM2 family | tiny/small/base+/large × Box/Point (8 configs) | 3–4 weeks (with lightweight variants) |
| Lightweight variants | MobileSAM, FastSAM, EfficientSAM × Box/Point (6 configs) | included above |
| Fine-tuned SAM ViT-B on AerialFuseCV | Domain adaptation, GPU-intensive | 4–6 weeks |
| Prompt strategies | Hybrid (box+point), automatic per-class selection | 2–3 weeks |
| Cross-dataset validation | DIOR, NWPU VHR-10 | 2–3 weeks |
| **Detector axis (new in v2.1)** | Detector variants × segmenter pairings — block design due before Mar 2027 | TBD |
| Writing and review cycles | | 6–8 weeks |
| **Total** | | **~4–5 months active work (before detector-axis sizing)** |

---

## Parked Single-Scope Papers (not scheduled)

Ideas the supervisor and candidate agreed to hold as potential standalone papers **after** the P0–P4 sequence is on track. Parked means: no venue, no date, no experiments committed; picking one up is a Revision Protocol event (major version bump).

| Idea | Core content | Origin |
|---|---|---|
| VBB vs OBB for aerial detection | The representation question, resolved properly — includes the VBB-on-DOTA-HBB ablation removed from P2 in v2.1 | v1 letter (cancelled) → v2.0 P2 ablation → parked v2.1 |
| SAM batch processing | Throughput/efficiency study of batched SAM inference for large-scale aerial processing | Thesis timing finding (SAM ≈ 92% of pipeline budget, batch-suitable) |
| OBB prompt support | Oriented-box prompting for segmenters (SAM takes axis-aligned boxes only) | Pipeline limitation observed in thesis |

---

## Timeline

```
Aug 2026   P0 Zenodo release, DOI live
Sep 2026   P1 SUBMIT (ISPRS Open Journal) | P2 experiments begin
Oct 2026   P2 experiments complete (trimmed scope: ~2–3 weeks of work)
Nov 2026   P1 expected acceptance | P3 EarthVision submit (if call fits)
Jan 2027   P2 writing | P3 IGARSS submit (alternative)
Feb 2027   P2 SUBMIT (ISPRS Journal)
Spring 27  P3 expected acceptance (= papers #2 accepted)
Mar 2027   P4 experiments begin
Sep 2027   P4 SUBMIT (TGRS)
Late 2027  P2 expected acceptance after revisions (= papers #3, regulation met)
2028       P4 expected acceptance (= papers #4, slack)
```

## Regulation Tracking (3 peer-reviewed papers required to defend)

| Milestone | Expected | Count |
|---|---|---|
| P1 accepted | Nov–Dec 2026 | 1 |
| P3 accepted | Spring 2027 | 2 |
| P2 accepted | Late 2027 | 3 — requirement met |
| P4 accepted | 2028 | 4 — slack |

## Key Dependencies

| Dependency | Blocks |
|---|---|
| P0 Zenodo DOI | P1 submission, citations in P2/P3/P4 |
| Mask R-CNN-on-Windows path (MMDetection primary, torchvision fallback — see `ATHENA_STATE.md` OPEN) | P2 supervised baselines |
| P2 material | P3 condensation |
| DIOR / NWPU VHR-10 setup | P4 cross-dataset block |
| P4 detector-axis block design | P4 experiment start (Mar 2027) |

## Tooling

- Writing: WTF-P (`npx wtf-p`) via Claude Code
- Experiments: Python, PyTorch, Ultralytics, SAM/SAM2 official repos, Detectron2 / MMDetection
- Dataset hosting: Zenodo
- GPU: RTX 3090 Ti

*Last updated: 2026-07-29 (v2.1). Living document, update after each submission and major experimental decision.*

---

## Changelog

| Version | Date | Trigger | Change & reasoning |
|---|---|---|---|
| v1 (draft) | Jul 2026 | — | Four journal papers, opening with VBB-vs-OBB letter at GRSL. |
| v2.0 | Jul 2026 | Strategy review | Letter cancelled — COCO-VBB vs DOTA-OBB confounds representation with training domain; folded into P2 with VBB-on-DOTA-HBB ablation. Scientific Data dropped (4–8 mo reviews); ISPRS Open Journal primary for P1. P3 conference paper added (insurance, counts toward NTUA rule). RT-DETR-seg dropped (effort/value). No CVPR/ICCV gamble for P4. |
| v2.0 (annot.) | 2026-07-28 | Environment restructure | Living-document header + this changelog added; content unchanged. Open item recorded in `ATHENA_STATE.md`: P2 exact scope (trim vs. as-written vs. +DIOR eval) deferred until supervisor input or P2 findings. |
| v2.1 | 2026-07-29 | **Supervisor instruction** — paper plan finalized in supervisor meeting | Closes the P2-scope open item, resolution ≈ option (b) trim. **P2:** tightened to pipeline + Mask R-CNN + YOLOv11-seg supervised baselines (+ confidence filtering, PR curves); VBB-on-DOTA-HBB ablation moved out — P2 therefore may not claim the VBB failure is a representation effect, only cite it as motivation with the confound acknowledged; Mask2Former dropped (supervisor named exactly two baselines); new-experiment effort ~5–6 wk → ~2–3 wk, experiments-complete pulled Dec → Oct 2026. **P3:** kept as written (user confirmed) — insurance + visibility, no new content. **P4:** reframed from SAM-variants benchmark to detector × segmenter combination benchmark; detector-axis block design due before Mar 2027. **Parked papers section added:** VBB vs OBB (inherits the ablation), SAM batch processing, OBB prompt support — explicitly unscheduled; activation requires a Revision Protocol event. Minor bump: no paper added/cancelled/merged — P0–P4 all stand. |
