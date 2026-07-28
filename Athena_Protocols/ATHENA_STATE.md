# 🦉 ATHENA_STATE — Program Ledger
**Last updated: 2026-07-28 (by ATHENA, local PC — environment restructure session)**

> The single cross-environment source of truth. Any AI instance, any machine, any vendor: what is written here is what has happened. Update after every milestone; date every update. Claims about results must trace to `results/` or the thesis.

---

## ✅ ACHIEVED

### Phase 0 — Master Thesis (CLOSED)
- **Defended 8 July 2026, grade 10/10.** NTUA/SECE DSML. Supervisor: Asst. Prof. A. Voulodimos. Committee: Voulodimos, Ioannidis, Stamou.
- Thesis PDF: `ArgusVision_for_Master_Thesis/` (also Google Drive, DSML--Thesis folder).

### Verified thesis results (citable in papers)
**AerialFuseCV dataset**
- 1,857 images (1,401 train / 456 val), **125,102 bbox–mask pairs**, 15 classes, **97.9% match rate** (98.1% train / 97.2% val), IoU ≥ 0.1 conservative matching, 12 images discarded
- Class imbalance: ship 29.5% + small-vehicle 24.8% + large-vehicle 16.6% = 71% of instances; 6 classes < 0.6% each
- Worst per-class match: helicopter 83.6% (val), harbor 89.6% (train)

**YOLO benchmark (34 models)**
- VBB (24 COCO-pretrained, v8–v12): catastrophic — best F1 **0.34%**
- OBB (10 DOTA-pretrained, v8+v11 families): best **YOLOv11x-OBB, F1 62.4%** → selected backbone
- Known confound: VBB(COCO) vs OBB(DOTA) mixes representation with training domain → P2 ablation resolves it

**SAM benchmark (6 configs, GT prompts, val split)**
- Box ≫ point prompts (~20 pp IoU gap)
- **ViT-B 66.9% vs ViT-H 67.7% mean IoU** — 0.8 pp gap despite ~7× params → *prompt quality dominates model size*

**Integrated pipeline (YOLOv11x-OBB → SAM-ViT-B, box)**
- **67.9% mean mask IoU** on matched pairs; **62.1% detection recall = the bottleneck** (~38% of GT instances never prompted)
- ~730 ms/image on RTX 3090 Ti; SAM ≈ 92% of budget → batch-suitable, not real-time
- Best class soccer-ball-field 87.1% IoU; worst swimming-pool 0% (detection cascade failure)

### Infrastructure
- Repo `oizzon1/ArgusVision` (private): `src/` pipeline + experiments, `dataset/` construction scripts, `results/` metrics-only commit discipline in `.gitignore`, branches `dev` + `ArgusVision_main`
- Publication Roadmap v2.0 committed; ATHENA v2.0 protocol suite live (this restructure)
- WTF-P installed (local PC, Claude Code)

---

## 📌 DECIDED (with reasoning — do not relitigate without a trigger)

| Decision | Reasoning | When |
|---|---|---|
| MSc thesis = Phase 0 of PhD | Program combined; continuity narrative | Jul 2026 |
| VBB-vs-OBB standalone letter **cancelled** | Confounds representation with training domain; folded into P2 with VBB-on-DOTA-HBB ablation | Roadmap v2.0 |
| Scientific Data dropped for P1 | 4–8 month reviews defeat fast-first-acceptance; ISPRS Open Journal primary, Data in Brief fallback | Roadmap v2.0 |
| P3 conference paper added | Insurance + visibility; conference→journal extension is accepted practice; counts toward NTUA rule | Roadmap v2.0 |
| RT-DETR-seg dropped as baseline | Weakest effort-to-value | Roadmap v2.0 |
| No CVPR/ICCV gamble for P4 | TGRS citing own DOI + flagship is stronger Year 1–2 outcome | Roadmap v2.0 |
| NTUA 3-publication rule: conferences count | Confirmed by user; venue plan stands | 2026-07-28 |
| Private monorepo, everything text-based in git | Drive = human-facing DOCX mirrors only; git canonical for ATHENA | 2026-07-28 |
| ATHENA v2.0: one identity, four modes; `ATHENA_RISE.md` name retained | Character continuity; multi-agent bootstrap via identical stubs | 2026-07-28 |
| Roadmap = living document with Revision Protocol | Optimize later on triggers, not now | 2026-07-28 |

---

## 🔄 IN PROGRESS

- **Environment restructure** (this session): ATHENA v2.0 files, bootstrap stubs, `papers/` + `zenodo_release/` skeletons — drafted, pending user review, then commit to `dev`
- Next up per roadmap: **P0 Zenodo release** (Aug 2026) — construction scripts in `dataset/` are the raw material; packaging, checksums, LICENSE, README remain

---

## ❓ OPEN (inherited by every future session until formally closed)

1. **P2 exact scope** — aim clean at ISPRS Journal; decision deferred. Options on the table: (a) roadmap scope as written; (b) trim (drop Mask2Former, tighten to core ablation + 2 baselines); (c) pull one cheap DIOR generalization eval forward from P4. STRATEGIST's recorded concern: P2 as written risks a forced split at ISPRS review; no cross-dataset test may draw reviewer fire. Close via Revision Protocol when triggered (likely supervisor input or P2 experiment findings).
2. **P3 venue** — EarthVision @ CVPR 2027 vs IGARSS 2027; decide when calls open (~Nov 2026 / Jan 2027).
3. **DIOR / NWPU VHR-10 setup** — needed for P4 (and for P2 option c); not yet downloaded/prepared on NTUA PC.
4. **NTUA PC asset paths** — datasets, weights, checkpoints locations not yet recorded here. **Next NTUA PC session: fill this section.**
   - DOTA v1.0 root: `<fill>`
   - iSAID root: `<fill>`
   - AerialFuseCV root: `<fill>`
   - SAM checkpoints: `<fill>`
   - YOLO weights: `<fill>`

---

## 📜 STATE LOG

| Date | Session | Change |
|---|---|---|
| 2026-07-28 | Local PC, ATHENA v2.0 restructure | Ledger created. Phase 0 results recorded from thesis full read. Roadmap v2.0 adopted as canonical. Environment architecture decided. |
