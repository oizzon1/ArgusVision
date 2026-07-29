# 🦉 ATHENA_STATE — Program Ledger
**Last updated: 2026-07-29 (by ATHENA, NTUA dev PC — environment audit session)**

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
- Publication Roadmap v2.0 committed; ATHENA protocol suite live (v2.1 as of 2026-07-29)
- WTF-P installed (NTUA dev PC, Claude Code)
- Line-ending policy committed (`.gitattributes`, `* text=auto eol=lf`) — required because Windows editors and WSL agents share one worktree

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
| **Work stays on Windows; WSL hosts agents only** | Running experiments from WSL would pay the `/mnt` I/O penalty on every dataset read (55 GB of imagery). Agents read the same tree through `/mnt/d` and execute via cmd.exe interop | 2026-07-29 |
| **Single primary machine, not two** | The "Local PC / NTUA PC" split in RISE v2.0 never existed. One NTUA dev PC holds GPU + all data; home PC is secondary and has no CUDA. OPERATOR is permitted here | 2026-07-29 |
| **Env canonical name `AV_env`** (was `thesis_env`) | Phase-0 name outlived Phase 0. Renamed by clone→verify→remove, not rebuilt — rebuilding from the spec would have destroyed a working CUDA install | 2026-07-29 |
| **Env spec corrected to match reality; lock file added** | `ArgusVision_environment.yml` specified conda `pytorch-cuda=12.1` while the real env had pip `torch==2.5.1+cu124`, and omitted `scipy` (which the code imports). The file could not have rebuilt the env that produced the thesis results. Config was corrected to the env, not the reverse | 2026-07-29 |

---

## 🔄 IN PROGRESS

- **Codebase restructure — PLANNED, not started.** Full REVIEWER pass done 2026-07-29; findings + target structure + 5-phase migration plan in `TODO_RESTRUCTURE.md`. Deadline: before P2 experiments (Sep 2026). Key findings: evaluation implemented 4× with disagreeing matchers (greedy vs Hungarian); metric named `map` is actually macro-F1 (ISPRS reviewer risk); adapters entangled with evaluation. Independent of P0.
- Next up per roadmap: **P0 Zenodo release** (Aug 2026) — construction scripts in `dataset/` are the raw material; packaging, checksums, LICENSE, README remain

---

## 🖥️ ENVIRONMENT (NTUA dev PC — verified 2026-07-29)

Repo root `D:\Work\AV` (Windows) = `/mnt/d/Work/AV` (WSL2, agents only). Work runs in Windows conda; WSL hosts AI agents and reaches Python via cmd.exe interop. Full model in `ATHENA_RISE.md` § ENVIRONMENTS.

**Conda env: `AV_env`** (Windows, `C:\Users\Panagiotis\.conda\envs\AV_env`). Renamed from `thesis_env` on 2026-07-29 — the Phase-0 name no longer matched the program. Verified: python 3.9.25, torch 2.5.1+cu124, `cuda.is_available() == True`, RTX 3090 Ti (24 GB), GPU matmul executed, all 11 codebase imports resolve.

| Asset | Path (repo-relative) | Size |
|---|---|---|
| DOTA v1.0 | `dataset/DOTA_v1/` | 20 GB |
| iSAID | `dataset/iSAID/` | 7.2 GB |
| AerialFuseCV | `dataset/AerialFuseCV/` | 14 GB |
| AerialFuseCV_Refined | `dataset/AerialFuseCV_Refined/` | 14 GB |
| DOTA→YOLO OBB / VBB conversions | `dataset/DOTA_v1_YOLO_{oriented,vertical}_bboxes_dataset/` | — |
| SAM checkpoints (ViT-B/L/H) | `model_checkpoints/SAM/` | 5.6 GB total |
| YOLO weights (10 OBB, 24 VBB) | `model_checkpoints/YOLO/{OBB,VBB}/` | (in the above) |

All assets are local to this machine — none are on a separate server.

---

## ❓ OPEN (inherited by every future session until formally closed)

1. **P2 exact scope** — aim clean at ISPRS Journal; decision deferred. Options on the table: (a) roadmap scope as written; (b) trim (drop Mask2Former, tighten to core ablation + 2 baselines); (c) pull one cheap DIOR generalization eval forward from P4. STRATEGIST's recorded concern: P2 as written risks a forced split at ISPRS review; no cross-dataset test may draw reviewer fire. Close via Revision Protocol when triggered (likely supervisor input or P2 experiment findings).
2. **P3 venue** — EarthVision @ CVPR 2027 vs IGARSS 2027; decide when calls open (~Nov 2026 / Jan 2027).
3. **DIOR / NWPU VHR-10 setup** — needed for P4 (and for P2 option c); not yet downloaded/prepared.
4. ~~**NTUA PC asset paths**~~ — **CLOSED 2026-07-29.** All assets were already on this machine; recorded in § ENVIRONMENT above. The item was written on the false premise of a two-machine split.
5. **Mask R-CNN baseline on Windows** — P2 requires it, but **Detectron2 has no official Windows support** and the work environment is Windows by decision. MMDetection is the more Windows-tolerant path; a `torchvision.models.detection.maskrcnn` implementation is the fallback. Must be resolved **before P2 experiments begin (Sep 2026)**, together with the Phase-1 env upgrade (SAM2 for P4). Not urgent today, but it is a dated dependency, not a vague gap.

---

## 📜 STATE LOG

| Date | Session | Change |
|---|---|---|
| 2026-07-28 | Local PC, ATHENA v2.0 restructure | Ledger created. Phase 0 results recorded from thesis full read. Roadmap v2.0 adopted as canonical. Environment architecture decided. |
| 2026-07-29 | NTUA dev PC, codebase review | Deep REVIEWER pass over `src/` (~10.5k lines). Restructure approved in principle; plan recorded in `TODO_RESTRUCTURE.md` (installable package, single evaluation stack, model adapters via protocol, run manifests, runtime/ for operational mode). Found: 4× evaluation duplication with matcher disagreement, `map`-is-F1 naming, confidence-ordering bug in greedy matcher. Execution deferred. |
| 2026-07-29 | NTUA dev PC, environment audit | User-led audit found the repo unready. Resolved: CRLF phantom diff (69 files / 15,962 lines) killed via `.gitattributes`; `thesis_env` → `AV_env` rename; env spec corrected (wrong PyTorch install path, missing scipy) + lock file added; doc rot fixed (stale `d:\Work\DSML` root, wrong yml filename, three-way env-name disagreement). RISE → v2.1: machine table corrected, Windows-conda-via-interop execution model documented. Ledger stale entries fixed; OPEN 4 closed, OPEN 5 (Detectron2-on-Windows) opened. |
