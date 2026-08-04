# Work Log — ArgusVision PhD

**Purpose:** session-level operational memory: hours worked, work completed, key issues, findings, and notes that are too granular for `ATHENA_STATE.md`.

**Update rule:** update this file at every session close, even if no code or roadmap file changed. `ATHENA_STATE.md` remains the milestone ledger; this file is the day-to-day work record.

---

## Logging Protocol

At session close, append one entry under the current month using this shape:

```markdown
### YYYY-MM-DD — Mode(s): STRATEGIST / ADVISOR / OPERATOR / REVIEWER

| Field | Entry |
|---|---|
| Work hours | 0.0 h |
| Work done | ... |
| Key issues | ... |
| Findings | ... |
| Notes | ... |
| Files changed | ... |
| Verification | ... |
| Next actions | ... |
```

Rules:
- **One entry per day** (merge multiple sessions of the same day into one entry).
- Record actual hours where known; otherwise write `not tracked`, never guess.
- Keep experimental numbers out unless they already exist in `results/` or the thesis.
- Use repo-relative file paths.
- Promote only durable milestones, decisions, and program-state changes to `ATHENA_STATE.md`.
- If the session ends because work is blocked, record the blocker and the exact next unblocking action.

---

## 2026-07

### 2026-07-28 — Mode(s): STRATEGIST / REVIEWER / OPERATOR

| Field | Entry |
|---|---|
| Work hours | **6.75 h** (20:00 → 02:45) |
| Work done | ATHENA v2.0 protocol suite (single identity, four modes; `ATHENA_STATE.md` ledger created and seeded from full thesis read; multi-agent bootstrap stubs `CLAUDE.md`/`GEMINI.md`/`AGENTS.md`); Publication Roadmap v2.0 adopted as canonical (VBB-vs-OBB letter cancelled into P2 ablation; Scientific Data → ISPRS OJ for P1; P3 conference paper added; RT-DETR-seg dropped); `papers/` WTF-P workspaces + `zenodo_release/` skeletons; line-ending policy (`.gitattributes`, killed 69-file/15,962-line CRLF phantom diff); environment audit: `thesis_env` → `AV_env` rename (clone→verify→remove), env spec corrected (pip cu124 torch, missing scipy) + 200-package lock file, doc rot fixed, `ATHENA_RISE.md` → v2.1; deep REVIEWER pass over `src/` (~10.5k lines) → `TODO_RESTRUCTURE.md` (findings F1–F6, target structure, 5-phase migration plan; committed next day 13:46). |
| Key issues | Env spec could not have rebuilt the env that produced thesis results; evaluation implemented 4× with disagreeing matchers (F1); `map` metric is macro-F1 (F2, ISPRS reviewer risk); adapters entangled with evaluation (F3). |
| Findings | Greedy matcher iterates predictions unsorted by confidence — low-conf pred can steal a GT from a high-conf pred (F2 bonus bug). Config corrected to match the working env, never the reverse. |
| Notes | STATE OPEN 4 closed (assets all local); OPEN 5 opened (Mask R-CNN on Windows: Detectron2 unsupported → MMDetection primary path, before Sep 2026). |
| Files changed | `Athena_Protocols/*`; `ArgusVision_Strategic_Planning/PUBLICATION_ROADMAP.md`; `CLAUDE.md`; `GEMINI.md`; `AGENTS.md`; `papers/**`; `zenodo_release/**`; `.gitattributes`; `ArgusVision_environment.{yml,lock.txt}`; `TODO_RESTRUCTURE.md` |
| Verification | torch 2.5.1+cu124 CUDA verified on RTX 3090 Ti; all 11 codebase imports resolve; bootstrap stubs identical; commits f735f0f, 3cd20d8, b6ca74a, 07f1a34 on `dev`. |
| Next actions | Roadmap revision after supervisor meeting; execute restructure; P0 Zenodo prep. |

### 2026-07-29 — Mode(s): STRATEGIST / OPERATOR / ADVISOR

| Field | Entry |
|---|---|
| Work hours | **7.17 h** (16:00 → 23:10 EEST) |
| Work done | **Roadmap → v2.1** (trigger: supervisor meeting finalized paper plan): P2 trimmed to pipeline + Mask R-CNN + YOLOv11-seg baselines (VBB-on-DOTA ablation → parked VBB-vs-OBB paper; Mask2Former out; experiments Dec→Oct 2026); P3 kept as insurance; P4 reframed detector × segmenter benchmark; parked-papers section added; STATE OPEN 1 closed. **Restructure phases 0–4 executed** on new branch `AV_dev` (user-named): tag `thesis-code-final`; installable `argusvision` package (`pyproject.toml`, editable into `AV_env`); domain constants consolidated; frozen evaluation stack (Hungarian + confidence-ranked matchers in one module, honest metric names `macro_f1`/`average_precision`, IoU 0.1/0.3/0.5, run manifests); predict-only YOLO/SAM adapters + registry + pipeline + runtime + viz (V1 evaluator + 3 dependent scripts deleted); `AerialFuseCVSplit`/`DotaYoloObbSplit` data classes; generic YAML driver `experiments/run_evaluation.py`; 62 tests passing; three validation runs launched (pipeline aabb + polygon, YOLO-only). **WTF-P v0.5.0 installed** locally into repo `.claude/` (145 files; STATE's "installed" claim had been false). `papers/shared/venues/` created; all 5 venue guides retrieved (3 Elsevier PDFs via user browser — ScienceDirect 403s bots) and distilled into per-venue `NOTES.md`. P1 new-paper interview started (paused at venue/argument questions). Work-log protocol adopted; this log backfilled. |
| Key issues | Case-insensitive Windows FS: `src/argusvision` ≡ `src/ArgusVision` → legacy renamed `src/_legacy_ArgusVision`. Evaluation slower than legacy per image (exact polygon IoU + 3 thresholds) — vectorization headroom noted, evaluator stays frozen. |
| Findings | **F7** legacy GSD loading was a silent no-op (hardcoded `dataset/dota_gsd_mapping.json`; file lives under `DOTA_v1/`). **F8** unanchored `.gitignore` patterns excluded `src/datasets/` from git entirely (absent even from thesis tag; rescued) and had kept SAM-eval `metrics.json` files untracked. **F9** legacy mask-ordering latent bug under mixed prompt configs (never fired; now structurally impossible, test-pinned). **Venues:** ISPRS OJPRS has NO data-paper article type → P1 frames as application Paper; DiB template mandatory; EarthVision deadlines are ~Mar (not ~Nov as roadmap assumed) → IGARSS 2027 (~Jan) comes first for P3. **Validation run 1 (aabb mode):** legacy V2 pipeline numbers reproduced to ±0.0005 (TP/FP/FN within 5 of 28k) — port faithful; first-ever honest macro-F1 and mean-AP recorded in `results/restructure_validation_pipeline_aabb/`. |
| Notes | **All three validation runs passed:** (1) port faithful ±0.05 pp vs legacy V2; (2) AABB→polygon ≤0.3 pp; (3) greedy→Hungarian delta ZERO at dataset scale — thesis YOLO macro-F1 0.6240 reproduced exactly. Report: `documentation/RESTRUCTURE_VALIDATION.md`. **`AV_dev` merged to `dev` (`59f583d`)**; one STATE-log conflict resolved (kept both rows); 62/62 tests on merged tree. Process slip owned: a `git add -A` swept the dev-bound pile into the Phase-4 commit on `AV_dev` — absorbed harmlessly by the immediate merge. Roadmap → v2.2 (P1 → Data in Brief; P3 deadline correction). P1: `.planning/` + 5 section drafts + `master.bib` seeded; DiB template v19 rules extracted from official .docx. Deletion inventory in `TODO_RESTRUCTURE.md`; `evaluate_sam.py` deliberately NOT superseded — port as driver kind at P4 prep. **Legacy branch preservation:** created and pushed `legacy_thesis` at `258a67c`, preserving thesis-era structure plus rescued `src/datasets/` dataloader scripts only; no dataset payloads added. **Branch hygiene:** deleted merged `AV_dev` locally and from `origin`. |
| Files changed | `ArgusVision_Strategic_Planning/PUBLICATION_ROADMAP.md`; `Athena_Protocols/{ATHENA_STATE.md,WORK_LOG.md}`; `TODO_RESTRUCTURE.md`; `pyproject.toml`; `.gitignore`; `ArgusVision_environment.{yml,lock.txt}` (+pytest); `src/argusvision/**`; `src/datasets/**`; `experiments/**`; `tests/**`; `.claude/**`; `papers/shared/venues/**` |
| Verification | 62/62 pytest in `AV_env`; validation run 1 diffed against `results/ArgusVision_v2_evaluation/evaluation_metrics_v2.json`; manifests carry clean git SHA. `legacy_thesis` tracks `origin/legacy_thesis`; `git check-ignore` confirms `src/datasets/aerial_fuse_cv_dataloader.py` is trackable while `dataset/DOTA_v1/...` remains ignored. `AV_dev` no longer appears locally or under `origin`. |
| Next actions | User-gated: legacy `src/` deletion sweep. P0 Zenodo (Aug) — unblocks P1 Data Description + methods. Verify DiB APC. P2 prep: MMDetection-on-Windows (STATE OPEN 5), driver class_map passthrough for any VBB eval. ~~Resolve `LEGACY_BRANCH.md` worktree state~~ — done 2026-07-30, see below. |

### 2026-07-30 — Mode(s): OPERATOR

| Field | Entry |
|---|---|
| Work hours | ~1.5 h (00:15 → 01:30 EEST) — post-midnight continuation of the 2026-07-29 session |
| Work done | **P1 writing (WTF-P, sections sourced from thesis §3.1 + code):** Methods drafted against the thesis's five published stages with implementation line-referenced to `refine_aerialfusecv.py`; Data Description drafted from Tables 6–7 (organisation, formats, GSD-inherited image properties, construction funnel, per-category stats, category distribution); Limitations → v0.3; abstract corrected twice. P1 now has drafts of every section except ethics/CRediT boilerplate. Earlier: resolved the `LEGACY_BRANCH.md` misplacement flagged at the previous close: the orientation note had been committed to `dev` (`293e89a`) but describes the frozen snapshot, so the active branch carried a file reading "do not develop on it". Removed from `dev`, rewritten and committed on `legacy_thesis` (`1093ff2`) with the frozen-state warning, tag-vs-`ArgusVision_main` rationale, F8 restoration record, and the list of deliberately preserved defects (F1/F2/F7/F9). Recorded the full branch layout in `ATHENA_STATE.md` § Infrastructure, which had no mention of `legacy_thesis` at all. |
| Key issues | **Wrote paper prose from recollection instead of source.** The first Methods draft described instance isolation as "clipping with the DOTA oriented-box polygons" — that is the *evaluation* code's method, not the dataset's. Caught only by reading the thesis and script. Rule reinforced: every P1 section is sourced from thesis §/table or code line before it is written. Ledger gap (earlier): the preservation branch existed on the remote but was invisible to any session reading only `ATHENA_STATE.md`. |
| Findings | **🔴 P0 blocker (STATE OPEN 6): construction Stages 1 and 3 exist in no committed script.** Only Stage 2 (`convert_dota_to_yolo_obb.py`) and Stage 4 (`refine_aerialfusecv.py`) survive as code; the DOTA∩iSAID intersection and mask reorganisation are absent, and there are no notebooks. P0's deliverable is a rebuild script, so both must be authored before release — thesis §3.1 specifies them well enough to reimplement. **"97.9% match rate" is a box-side rate only:** summing Table 7's mask columns gives ~330,693 iSAID mask instances in the 1,869-image subset, only ~37.8% paired; ~205,591 mask instances (mostly small vehicles — iSAID marks 6.2× more than DOTA boxes in train) are absent from released masks. Derived, not stated in the thesis → flagged ⚠ for regeneration from `Dataset_Statistics.md` at P0. Now disclosed in Data Description, Limitations and the abstract. **Three thesis prose errata** recorded in STATE so papers do not inherit them (moderate group miscounted "seven"/six, rare group "five"/six, lowest-performer list omits soccer-ball-field 92.2%); the tables themselves are arithmetically sound. Earlier: `legacy_thesis` verified correct as built: based on tag `thesis-code-final` (`11ba53c`), carries the thesis-era flat `src/` layout plus the rescued `src/datasets/` dataloaders and the anchored `.gitignore`. Confirmed `ArgusVision_main` is NOT a valid legacy anchor — it is 6 commits older and its environment spec predates the corrections, so it could not rebuild the env that produced the thesis results. |
| Notes | No code touched; documentation, papers and ledger only. Thesis PDF extracted to scratchpad with pypdf (no poppler in WSL, so the Read tool cannot render PDFs — pypdf text extraction is the working method for this machine). |
| Files changed | `LEGACY_BRANCH.md` (removed from `dev`, added on `legacy_thesis`); `Athena_Protocols/{ATHENA_STATE.md,WORK_LOG.md}`; `papers/p1_aerialfusecv_descriptor/sections/{00_front_matter,04_data_description,05_methods,06_limitations}.md` (+ skeleton deleted); `papers/p1_aerialfusecv_descriptor/.planning/structure/outline.md` |
| Verification | All three branches in sync with `origin`, no ahead/behind. `LEGACY_BRANCH.md` present on `legacy_thesis` only (absent from `dev` and `ArgusVision_main`). 62/62 pytest on `dev` in `AV_env`. Worktree clean. |
| Next actions | **P0 now has a hard prerequisite: author + verify construction Stages 1 and 3 (STATE OPEN 6)** before the Zenodo release; regenerate the ⚠ mask-side statistics from `Dataset_Statistics.md` and replace the derivations in P1. Then: P1 ethics/CRediT boilerplate, 4 figures, 🔴 REVIEWER pass. Unchanged: user-gated legacy `src/` deletion sweep; verify DiB APC; MMDetection-on-Windows (OPEN 5). |

### 2026-07-31 — Mode(s): OPERATOR / REVIEWER / ADVISOR

| Field | Entry |
|---|---|
| Work hours | **~16.4 h** (07:46 → 00:07 +1d EEST; timed from first to last commit — earlier uncommitted work not counted) |
| Work done | **AerialFuseCV rebuilt correctly and verified.** Regression build (semantic mode) reproduced the precursor dataset **exactly** — 1,857 labels and 1,857 masks compared, 0 mismatches, pair delta +0 — proving port fidelity before anything else was trusted. Then four settled changes implemented in one rebuild: (1) matching scores the **rasterised oriented polygon** against the instance mask instead of the axis-aligned hull; (2) both `labels_obb/` and `labels_hbb/` written, HBB as a clockwise hull quadrilateral; (3) annotations kept **DOTA-native** (headers, absolute px, class names, `difficult`); (4) parallelised across images. Corrected build: **125,722 pairs** (98.34% box pairing), 1,862 images, matched-IoU median **0.715**, in 24 min (4.1× speedup). Self-consistency audit passed: file counts, label-line counts, `pairs.jsonl` count and reported pairs all agree; **every one of 125,722 HBBs verified to be the hull of its OBB**; stale-GSD defect (R3) fixed. Pipeline experiment run on the corrected dataset and compared against the polygon-mode baseline. Built `dataset/verify_build.py` and `dataset/inspect_gt_masks.py`. |
| Key issues | `pkill` from WSL does not kill the Windows-side Python launched via interop — file locks persisted until the real PIDs were terminated (identified by command line first). Git operations time out during large builds because git walks the tree even for ignored paths. `conda run` buffers stdout, so a background log stays empty until exit — "no output" is indistinguishable from "crashed" unless the script creates visible artefacts early. |
| Findings | **Hull vs polygon:** the axis-aligned hull is a median **1.83×** the true oriented box area (68% >1.5×, 37% >2×) over 21,265 boxes; DOTA is genuinely oriented (95.5% rotated, median 17.1° off-axis). Fixing this gained **+620 pairs** and **+0.247 median IoU**; biggest class gains harbor (+548, 90.6%→97.4%) and plane (+265) — both strongly oriented. Negative deltas in ship/small-vehicle/large-vehicle are the one-to-one constraint removing duplicate claims, i.e. a correctness gain. **Experiment on the corrected dataset:** detection improved at every threshold (precision +0.0057, mean AP +0.0131) — the false-positive artefact shrinking as GT becomes more complete; segmentation flat, **because the evaluation never reads the new instance masks**. **Licensing:** iSAID carries DOTA's exact restriction (annotations academic-only, commercial prohibited) plus Google Earth terms; `pairs.jsonl` as built still reproduces source annotation content, so the deposit must **reference** rather than reproduce. **The big one — annotation discrepancy:** polygon-clipped GT and exact iSAID instance GT agree on only **18.5%** of instances (mean IoU 0.868). Visual inspection overturned the "contamination" explanation: the worst cases show **`extra=0px`** — DOTA and iSAID annotate **different object extents** (baseball diamond = infield vs whole field; harbor = pier vs pier+platforms), plus outright iSAID errors (P0262: one instance covering a boat, its dock, and a second boat — verified 1 colour, 1 connected component, so not an artefact of our extraction). Separately, **2.4% of colour-instances span multiple disconnected pieces** — the only part that is ours to fix. |
| Notes | The visual-inspection request prevented a bad change: I had recommended switching GT to iSAID instance masks; the figures showed that would score box-prompted predictions against extents the prompt never covered. Recommendation withdrawn. New direction agreed: quantify the discrepancies, argue them in the paper, and release **reconciled masks** derived from box-clipping — with the caveat that "100% agreement" is circular unless framed as evaluation validity, and that clipping does not remove neighbour contamination (unmeasured). Venue deferred; may outgrow Data in Brief. |
| Files changed | `dataset/{build_aerialfusecv,verify_build,inspect_gt_masks,scan_isaid_colours}.py`; `src/argusvision/data/aerialfusecv.py`; `src/argusvision/evaluation/evaluator.py`; `experiments/configs/p2_pipeline_aerialfusecv_v1.yaml`; `TODO_RECREATION_SCRIPT.md`; `documentation/DECISION_unpaired_annotations.md`; `Athena_Protocols/ATHENA_STATE.md`; `.gitignore` |
| Verification | Regression build vs reference: 3-level comparison, PASS with zero mismatches. Corrected build: self-consistency audit passed on all checks. 62/62 pytest. Colour audit re-run reproduced its own earlier numbers exactly (1,869 images, 16 colours, 0 unknown, 0 multi-class instances, 475,438 instances). |
| Session close | **Steps 1–6 of `TODO_AERIALFUSECV_REBUILD.md` executed autonomously.** Discrepancy measured over all 125,722 pairs: 90.0% extent / 10.0% foreign, 16.3% of pairs contaminated, 2.61% multi-piece instances. Reconciled masks defined (matched instance ∩ oriented box) and recorded in `documentation/DECISION_reconciled_masks.md`; `dataset/AerialFuseCV_reconciled` built. **Second finding of the same shape as the first:** the re-run showed exactly zero delta because the evaluation still re-derived GT by clipping the semantic mask and never read the released instance masks — `AerialFuseCVSplit.ground_truth_masks()` now resolves each label line to its iSAID instance via `pairs.jsonl`. Re-run then gave +0.0012 seg IoU, small but with per-class gains falling **only** on the classes the discrepancy measurement independently flagged as contaminated (plane, storage-tank, small/large-vehicle) and exactly 0.000 elsewhere — two independent measurements agreeing. EDA + 4 figures generated. Consolidated evidence: `results/AerialFuseCV_Testing/FINDINGS.md`. |
| Next actions | **Steps 7–8 deliberately not executed.** Step 7 (deliverable script) is blocked on licensing answers — NTUA research-data office, DOTA/iSAID authors, venue pre-submission enquiry — and step 8's deletion is gated on step 7's verified build. Remaining: make the extraction component-aware (step 2 residual, 2.61%); re-source P1 numerically from `dataset_statistics.json`; decide venue once the discrepancy analysis is sized; `argusvision` VBB→HBB rename. |

## 2026-08

### 2026-08-03 — Mode(s): STRATEGIST / OPERATOR / REVIEWER

| Field | Entry |
|---|---|
| Work hours | in progress (started before 12:00 EEST) |
| Work done | Added `ArgusVision_Strategic_Planning/Context/` as ATHENA's strategic context inbox; wired the survey rule into `ATHENA_RISE.md` and identical bootstrap stubs; created `Context/README.md`; reviewed `2504.09203v1.pdf` as `2504.09203v1_AerOSeg_REVIEW.md`; updated `ATHENA_STATE.md`. |
| Key issues | Strategic planning previously had no durable intake path for newly found papers/competitor context, so future sessions could miss evidence unless it had been promoted to the roadmap or state ledger. |
| Findings | AerOSeg uses SAM as frozen feature guidance for trained open-vocabulary semantic segmentation, not as an OBB/prompted instance segmenter. It does not kill the OBB-for-SAM prompt idea; it does strengthen related-work expectations around SAM use in remote sensing. |
| Notes | No roadmap revision required now. AerOSeg is a related-work anchor for SAM+CLIP remote-sensing segmentation and possible P4 context baseline family only if P4 expands beyond instance-level detect-to-segment systems. |
| Files changed | `ArgusVision_Strategic_Planning/Context/{README.md,2504.09203v1_AerOSeg_REVIEW.md}`; `Athena_Protocols/{ATHENA_RISE.md,ATHENA_STATE.md,WORK_LOG.md}`; `AGENTS.md`; `CLAUDE.md`; `GEMINI.md` |
| Verification | `git diff --check` passed; `AGENTS.md`, `CLAUDE.md`, and `GEMINI.md` confirmed byte-identical. |
| Next actions | Keep surveying `Context/` on startup and before strategic advice; if more papers are added, create review notes before letting them affect roadmap decisions. |

### 2026-08-04 — Mode(s): ADVISOR / OPERATOR

| Field | Entry |
|---|---|
| Work hours | not tracked |
| Work done | Surveyed and answered the iSAID-baseline threat question; logged the positioning in `ArgusVision_Strategic_Planning/Context/iSAID_baselines_positioning_NOTES.md`; mirrored the durable decision into `ATHENA_STATE.md`. |
| Key issues | Existing iSAID work already includes supervised instance segmentation, SAM-family/adapted-SAM remote-sensing work, and open-vocabulary semantic segmentation. ArgusVision cannot be framed as first iSAID segmentation or first SAM-in-remote-sensing work. |
| Findings | The literature narrows but does not invalidate ArgusVision. The strong need is the paired object-level detection-to-segmentation contract: detector geometry and outputs as prompts, evaluator separation of detector error from mask quality, and training-free-vs-supervised tradeoff analysis. |
| Notes | P2 remains a rigorous comparison against supervised baselines, not a claim that SAM must beat them. P1/AerialFuseCV remains justified because detector-to-SAM evaluation needs paired object-level DOTA/iSAID geometry, masks, pairing metadata, and discard accounting. |
| Files changed | `ArgusVision_Strategic_Planning/Context/iSAID_baselines_positioning_NOTES.md`; `Athena_Protocols/{ATHENA_STATE.md,WORK_LOG.md}` |
| Verification | `git diff --check` passed. |
| Next actions | Use this note when drafting P1/P2 related work and introduction; keep Mask R-CNN + YOLOv11-seg as P2 baselines; reserve PANet/Mask2Former/SAM-adaptation/open-vocabulary systems for related work or P4 expansion. |
