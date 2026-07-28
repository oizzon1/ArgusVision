# Publication Roadmap v2.0
### ArgusVision PhD — Panagiotis Fragkos
**Base:** Master Thesis (Phase 0) — Object Detection and Semantic Segmentation of Aerial and Satellite Imagery with Deep Learning
**Program:** PhD in Photogrammetry, NTUA | **Supervisor:** Prof. Charalampos Ioannidis
**Roadmap version:** 2.0, July 2026 | **Replaces:** draft of July 2026 (four journal papers)

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
| P4 | 4th | ArgusVision Benchmark: Foundation Model Variants for Aerial Instance Segmentation | Benchmark paper | Sep–Oct 2027 | 2028 |

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

> Single paper carrying the full thesis arc. Which detector representations work on aerial imagery, how SAM variants respond to prompt design, what an integrated training-free YOLO to SAM pipeline achieves, and where it stands against supervised end-to-end baselines.

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
| VBB YOLO trained on DOTA HBB annotations (2–3 models) | Resolves representation vs domain confound. Core new contribution | 1–2 weeks |
| Mask R-CNN trained on AerialFuseCV | Supervised classic baseline | 3–5 days |
| YOLOv11-seg trained on AerialFuseCV | Supervised baseline, same family as detector | 2–3 days |
| Confidence-based segmentation filtering | Addresses the ~18.5% false-positive overhead | 2–3 days |
| PR curves at IoU 0.1 / 0.3 / 0.5 | Sensitivity analysis, post-hoc on existing predictions | 2–3 days |
| Mask2Former baseline (optional, only if schedule allows) | Modern supervised reference | 5–7 days |
| **Total** | | **~5–6 weeks, parallelizable** |

RT-DETR-seg dropped. Weakest effort-to-value in the original list.

---

## P3 — Conference Paper (insurance and visibility)

> Condensed zero-shot pipeline findings. Conference-to-journal extension is accepted practice in this field, so no conflict with P2.

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

> Full configuration space. SAM variants, training strategies, prompt designs for aerial instance segmentation.

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
| Writing and review cycles | | 6–8 weeks |
| **Total** | | **~4–5 months active work** |

---

## Timeline

```
Aug 2026   P0 Zenodo release, DOI live
Sep 2026   P1 SUBMIT (ISPRS Open Journal) | P2 experiments begin
Nov 2026   P1 expected acceptance | P3 EarthVision submit (if call fits)
Dec 2026   P2 experiments complete
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
| VBB-on-DOTA ablation | P2 core claim |
| P2 material | P3 condensation |
| DIOR / NWPU VHR-10 setup | P4 cross-dataset block |

## Tooling

- Writing: WTF-P (`npx wtf-p`) via Claude Code
- Experiments: Python, PyTorch, Ultralytics, SAM/SAM2 official repos, Detectron2 / MMDetection
- Dataset hosting: Zenodo
- GPU: RTX 3090 Ti

*Last updated: July 2026. Living document, update after each submission and major experimental decision.*

---

## Changelog

| Version | Date | Trigger | Change & reasoning |
|---|---|---|---|
| v1 (draft) | Jul 2026 | — | Four journal papers, opening with VBB-vs-OBB letter at GRSL. |
| v2.0 | Jul 2026 | Strategy review | Letter cancelled — COCO-VBB vs DOTA-OBB confounds representation with training domain; folded into P2 with VBB-on-DOTA-HBB ablation. Scientific Data dropped (4–8 mo reviews); ISPRS Open Journal primary for P1. P3 conference paper added (insurance, counts toward NTUA rule). RT-DETR-seg dropped (effort/value). No CVPR/ICCV gamble for P4. |
| v2.0 (annot.) | 2026-07-28 | Environment restructure | Living-document header + this changelog added; content unchanged. Open item recorded in `ATHENA_STATE.md`: P2 exact scope (trim vs. as-written vs. +DIOR eval) deferred until supervisor input or P2 findings. |
