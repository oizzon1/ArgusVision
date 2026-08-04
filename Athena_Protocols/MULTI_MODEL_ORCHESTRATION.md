# Multi-Model ATHENA Orchestration Plan

**Created:** 2026-08-04  
**Purpose:** coordinate multiple terminal-based AI models working in the same
ArgusVision repository without overlapping, duplicating work, or corrupting the
shared program state.

This plan assumes every model can access the repository from a terminal. The
user talks primarily to one model: the **ATHENA Orchestrator**. Other models are
**workers**. Workers receive bounded task packets from the Orchestrator, execute
only their assigned lane, and report back.

---

## Core Principle

There is one strategic brain and many hands.

- The Orchestrator owns the big picture.
- Workers own bounded execution tasks.
- Workers do not change scope.
- Workers do not edit another worker's locked files.
- Workers do not update roadmap/state unless explicitly assigned.
- The Orchestrator reviews worker outputs before they are merged into `dev`.

The user should not need to personally coordinate every model. The user talks
to the Orchestrator, then pastes Orchestrator-generated worker prompts into the
other model terminals.

---

## Roles

| Role | Typical model | Owns | May edit |
|---|---|---|---|
| ATHENA Orchestrator | strongest repo-connected strategist/integrator | task selection, sequencing, file locks, final review, merges | all coordination files; only task files it explicitly claims |
| Operator worker | Codex / strong coding model | scripts, tests, experiments, packaging | assigned code/data/package files only |
| Writer worker | Claude / strong writing model | paper sections, abstract, response-to-reviewer prose | assigned paper files only |
| Literature worker | Gemini Deep Research / research-capable model | literature scans, competitor tables, source summaries | context notes only, unless told otherwise |
| Reviewer worker | any strong independent model | hostile review, risk finding, critique | preferably no edits; review notes only |

If there is doubt, workers default to **no edit** and report the ambiguity.

---

## Shared Coordination Files

Recommended files:

| File | Purpose |
|---|---|
| `Athena_Protocols/MULTI_MODEL_ORCHESTRATION.md` | this operating plan |
| `Athena_Protocols/ACTIVE_TASKS.md` | live task claims, file locks, active branches |
| `Athena_Protocols/HANDOFFS.md` | completed worker handoffs and integration notes |
| `Athena_Protocols/WORK_LOG.md` | daily record; updated at session close |
| `Athena_Protocols/ATHENA_STATE.md` | milestone ledger; Orchestrator-owned unless delegated |
| `ArgusVision_Strategic_Planning/PUBLICATION_ROADMAP.md` | canonical plan; Orchestrator-owned unless delegated |

Minimum viable implementation: create `ACTIVE_TASKS.md`. `HANDOFFS.md` is useful
once multiple workers are active daily.

---

## Non-Overlap Rules

1. Each worker claims exactly one task.
2. Each task has one owner, one branch, and one locked file/area list.
3. Workers work only inside locked files/areas.
4. Shared control files are Orchestrator-owned:
   - `ATHENA_STATE.md`
   - `PUBLICATION_ROADMAP.md`
   - `ACTIVE_TASKS.md`
   - `HANDOFFS.md`
5. Workers may update `ACTIVE_TASKS.md` and `WORK_LOG.md` only as specified in
   their task packet.
6. Workers do not run broad cleanup, formatting, deletion, or refactor tasks
   unless explicitly assigned.
7. Workers do not invent new experiments, new claims, new venues, or new
   roadmap items.
8. Workers do not cite experimental numbers unless those numbers exist in
   `results/`.
9. Workers do not touch untracked artifacts outside their task.
10. If a worker sees a conflict, stale state, dirty worktree, or another active
    lock on the same files, it stops and reports.

---

## Branching Model

Daily base branch:

```bash
git switch dev
git pull
```

Each substantial worker task uses a short-lived branch:

```bash
git switch -c task/<task-id-short-name>
```

Examples:

```bash
git switch -c task/f1-deposit-rebuild
git switch -c task/p1-dib-value-data
git switch -c task/f6-maskrcnn-spike
git switch -c task/reviewer-p1-risk
```

Workers push their task branch. The Orchestrator merges or instructs the user
when to merge.

Small documentation-only tasks may be done directly on `dev` only if the
Orchestrator explicitly assigns that.

---

## ACTIVE_TASKS.md Template

Create `Athena_Protocols/ACTIVE_TASKS.md` with this structure:

```markdown
# ACTIVE_TASKS

**Rule:** if a file/area is locked by an active task, no other worker edits it.

| ID | Owner | Role | Branch | Status | Locked files/areas | Started | Handoff |
|---|---|---|---|---|---|---|---|
| F1 | Codex-Operator | OPERATOR | task/f1-deposit-rebuild | active | dataset/build_aerialfusecv.py; dataset/README.md; zenodo_release/** | 2026-08-04 21:00 | none |
```

Allowed statuses:

- `planned`
- `active`
- `blocked`
- `ready-for-review`
- `merged`
- `cancelled`

---

## HANDOFFS.md Template

Create `Athena_Protocols/HANDOFFS.md` with this structure:

```markdown
# HANDOFFS

## YYYY-MM-DD - TASK-ID - Owner

| Field | Entry |
|---|---|
| Branch | task/... |
| Commit | abc1234 |
| Work completed | ... |
| Files changed | ... |
| Verification | ... |
| Blockers | ... |
| Risks / review notes | ... |
| Requested Orchestrator action | review / merge / unblock / revise |
```

---

## Orchestrator Startup Loop

The Orchestrator starts every session with:

1. `git switch dev`
2. `git pull`
3. Read:
   - `Athena_Protocols/ATHENA_RISE.md`
   - `Athena_Protocols/ATHENA_STATE.md`
   - `Athena_Protocols/WORK_LOG.md`
   - `Athena_Protocols/MULTI_MODEL_ORCHESTRATION.md`
   - `Athena_Protocols/ACTIVE_TASKS.md` if it exists
   - `ArgusVision_Strategic_Planning/Context/`
   - `ArgusVision_Strategic_Planning/PUBLICATION_ROADMAP.md`
4. Check `git status --short --branch`.
5. Decide the next bounded tasks.
6. Produce worker task packets for the user to paste.
7. Review worker handoffs before merge.
8. Update state/log/roadmap only when durable.

---

## Worker Startup Loop

Every worker prompt must instruct the worker to:

1. `git switch dev`
2. `git pull`
3. Read:
   - `Athena_Protocols/ATHENA_RISE.md`
   - `Athena_Protocols/ATHENA_STATE.md`
   - `Athena_Protocols/WORK_LOG.md`
   - `Athena_Protocols/MULTI_MODEL_ORCHESTRATION.md`
   - `Athena_Protocols/ACTIVE_TASKS.md`
   - `ArgusVision_Strategic_Planning/PUBLICATION_ROADMAP.md`
4. Confirm no active lock overlaps its task.
5. Create or switch to the assigned branch.
6. Claim/update the task in `ACTIVE_TASKS.md`.
7. Work only in assigned files/areas.
8. Verify.
9. Update `ACTIVE_TASKS.md` and `WORK_LOG.md` only as instructed.
10. Commit and push the task branch.
11. Report commit hash, verification, blockers, and changed files.

---

## Worker Task Packet Template

The Orchestrator gives the user one packet per worker. The user pastes the
packet into that worker terminal.

```text
ATHENA WORKER TASK PACKET

Role: <OPERATOR / WRITER / LITERATURE / REVIEWER>
Task ID: <F1 / P1-WRITE / F6 / REVIEW-P1 / etc.>
Branch: task/<short-name>
Mode: <ATHENA mode tag>

Objective:
<one concrete outcome>

Locked files/areas:
- <path or glob>
- <path or glob>

Do not edit:
- Athena_Protocols/ATHENA_STATE.md
- ArgusVision_Strategic_Planning/PUBLICATION_ROADMAP.md
- any active task's locked files
- untracked artifacts outside this task

Required startup:
1. Run from repo root.
2. git switch dev
3. git pull
4. Read ATHENA_RISE, ATHENA_STATE, WORK_LOG,
   MULTI_MODEL_ORCHESTRATION, ACTIVE_TASKS, and PUBLICATION_ROADMAP.
5. Confirm no lock conflict.
6. Create/switch to Branch.
7. Claim Task ID in ACTIVE_TASKS.

Work steps:
1. <step>
2. <step>
3. <step>

Verification required:
- <command or manual check>
- <expected artifact>

Handoff required:
1. Update ACTIVE_TASKS status to ready-for-review or blocked.
2. Append a concise WORK_LOG note for today.
3. Commit and push the task branch.
4. Report:
   - branch
   - commit hash
   - files changed
   - verification result
   - blockers
   - what the Orchestrator should review

Stop conditions:
- lock conflict
- dirty worktree that is not yours
- missing data or dependency
- command failure that changes scientific output
- uncertainty about claims or numbers
```

---

## Example Worker Packets for Current Fast Track

### F1 Operator Worker

```text
ATHENA WORKER TASK PACKET

Role: OPERATOR
Task ID: F1
Branch: task/f1-deposit-rebuild
Mode: OPERATOR

Objective:
Create a deposit-scoped rebuild/verification path for AerialFuseCV that can be
used for Zenodo v1.0 packaging. It must rebuild from official DOTA/iSAID inputs
and verify against the internal corrected build.

Locked files/areas:
- dataset/build_aerialfusecv.py
- dataset/README.md
- zenodo_release/**
- results/experimental/AerialFuseCV_Testing/aerialfusecv_build/**

Do not edit:
- ATHENA_STATE.md
- PUBLICATION_ROADMAP.md
- papers/**
- unrelated results/**

Work steps:
1. Inspect the current builder and verification scripts.
2. Identify what is internal-only versus deposit-ready.
3. Add or document a deposit-safe invocation path.
4. Add verification outputs suitable for Zenodo packaging.
5. Run the smallest verification that proves the path is wired correctly.

Verification required:
- Run relevant dataset verification from repo root using AV_env.
- Produce or update manifest/statistics under results only if the run is valid.

Handoff:
Report exact command, output artifact path, commit hash, and any licensing or
data-layout blockers.
```

### P1 Writer Worker

```text
ATHENA WORKER TASK PACKET

Role: WRITER
Task ID: P1-WRITE-VALUE
Branch: task/p1-value-data
Mode: ADVISOR

Objective:
Rewrite P1 Value of the Data / need-statement prose around the locked v2.4
claim: box-rich, mask-poor aerial workflows; paired detect-to-segment contract;
supervised segmenters as full-mask-supervision ceiling.

Locked files/areas:
- papers/p1_aerialfusecv_descriptor/sections/**
- papers/p1_aerialfusecv_descriptor/.planning/**

Do not edit:
- dataset/**
- results/**
- ATHENA_STATE.md
- PUBLICATION_ROADMAP.md

Work steps:
1. Read roadmap v2.4 need statement and context positioning notes.
2. Draft prose without adding unsupported experimental numbers.
3. Strengthen application fields: urban mapping, maritime surveillance,
   infrastructure inspection, environmental monitoring, rapid damage
   assessment, agriculture, insurance/risk, defense/security, UAV mapping.
4. Mark any placeholder that waits on P0 DOI or corrected-build statistics.

Verification required:
- No experimental numbers unless traced to results.
- DiB tone: concise, data-article appropriate, no inflated novelty claims.

Handoff:
Report changed sections, remaining placeholders, and reviewer risks.
```

### F6 Operator Worker

```text
ATHENA WORKER TASK PACKET

Role: OPERATOR
Task ID: F6
Branch: task/f6-maskrcnn-feasibility
Mode: OPERATOR

Objective:
Resolve the Mask R-CNN-on-Windows path for P2. Try MMDetection first. If it is
not operational quickly, define the torchvision fallback path.

Locked files/areas:
- experiments/**
- src/argusvision/models/**
- src/argusvision/data/**
- tests/**
- documentation/**

Do not edit:
- dataset/AerialFuseCV/**
- papers/**
- ATHENA_STATE.md
- PUBLICATION_ROADMAP.md

Work steps:
1. Inspect current environment and model-adapter patterns.
2. Test MMDetection feasibility on Windows AV_env without breaking the existing
   environment.
3. If MMDetection is blocked, design torchvision Mask R-CNN fallback.
4. Produce a short implementation note and, if safe, a minimal adapter skeleton.

Verification required:
- Import check and/or minimal smoke test.
- No dependency install that destabilizes AV_env without explicit approval.

Handoff:
Report chosen path, exact blockers, required installs, and next implementation
steps.
```

### Reviewer Worker

```text
ATHENA WORKER TASK PACKET

Role: REVIEWER
Task ID: REVIEW-V24
Branch: task/review-v24
Mode: REVIEWER

Objective:
Hostile-review roadmap v2.4 and the P1/P2 positioning. Find contradictions,
unsupported claims, venue risks, missing baselines, and schedule risks.

Locked files/areas:
- ArgusVision_Strategic_Planning/Context/reviewer_notes/**

Do not edit:
- PUBLICATION_ROADMAP.md
- ATHENA_STATE.md
- dataset/**
- papers/**
- results/**

Work steps:
1. Read roadmap v2.4 and context notes.
2. Write a review note with findings ordered by severity.
3. Separate fatal blockers, fix-before-submit issues, and optional polish.

Verification required:
- Every criticism must cite a local file/section or an explicitly named
  literature gap.

Handoff:
Report review note path and top 5 risks.
```

---

## Integration Protocol

Only the Orchestrator integrates worker branches into `dev`.

For each worker handoff:

1. Inspect branch diff.
2. Check it stayed inside locked files.
3. Run relevant verification.
4. Decide:
   - merge,
   - request revision,
   - cherry-pick partial work,
   - reject.
5. Update `ACTIVE_TASKS.md`.
6. Update `WORK_LOG.md`.
7. Update `ATHENA_STATE.md` only if a durable decision or milestone changed.
8. Push `dev`.

---

## Current Recommended Assignment (corrected 2026-08-04)

**Context continuity beats model brand.** Whichever session has repo access and
reads the protocol files is the orchestrator. Vendor “best for X” tables are
advisory only.

**Critical path is serial:** F1 → F2 → F3 → F4 (deposit script → package →
licensing MVP → P1 rewrite). Handing F1 to one model and P1 prose to another
mostly produces prose that gets rewritten when numbers and DOI land.

| Track | Assignment | Start now? | Notes |
|---|---|---|---|
| F1 deposit rebuild + verify | **Orchestrator, single-threaded** | yes | highest priority; do not hand off for fake parallelism |
| F2 Zenodo packaging | Orchestrator after F1 | after F1 | same lane |
| F3 licensing/admin checklist | user + optional scout | yes | admin; Context notes only; no code lock |
| F4 P1 rewrite | after F1+F2 | no | needs numbers + DOI |
| REVIEW-V24 hostile review | optional reviewer worker | yes | **no edits**; notes only — cleanest parallel task |
| F6–F8 Mask R-CNN / YOLO-seg / filtering | OPERATOR workers | later | real parallelism window |
| P4 / C1 / C2 / C3 | frozen | no | until P1 submitted and P2 experiments done |

Hard stop rule stands: if coordination becomes confusing, one orchestrator-controlled task at a time.

---

## User Operating Pattern

The user talks to one model:

```text
ATHENA Orchestrator: decide the next parallel work packets for today.
```

The Orchestrator replies with one or more task packets.

The user pastes each packet into the assigned model terminal.

Workers execute and return:

```text
Task complete.
Branch:
Commit:
Verification:
Blockers:
Please review/merge.
```

The user pastes worker reports back into the Orchestrator.

The Orchestrator reviews, merges, updates logs/state, and issues the next
packets.

---

## Hard Stop Rule

If coordination becomes confusing, stop all workers and return to one
Orchestrator-controlled task at a time. Parallelism is useful only when it
reduces wall-clock time without weakening scientific control.

