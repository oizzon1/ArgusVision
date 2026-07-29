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
| Next actions | User-gated: legacy `src/` deletion sweep. P0 Zenodo (Aug) — unblocks P1 Data Description + methods. Verify DiB APC. P2 prep: MMDetection-on-Windows (STATE OPEN 5), driver class_map passthrough for any VBB eval. Resolve `LEGACY_BRANCH.md` worktree state before the next clean close. |
