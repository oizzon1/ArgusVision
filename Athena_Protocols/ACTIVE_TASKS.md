# ACTIVE_TASKS

## MODE: SINGLE-OPERATOR (user directive, 2026-08-04)

**Parallel dispatch is suspended.** One task at a time, executed by the ATHENA
session, reported before the next begins. The user retains control by seeing
each task complete rather than tracking concurrent lanes.

Reason (user, verbatim): *"parallel works created too much overhead for me. I
want more control for now."* The overhead was real — three lanes produced two
branch-collision incidents, a 66 MB artefact in a merge, and a worktree that
outlived its task, all in one day. None of that was worker error; it is the
coordination cost of parallelism at this repo's size.

**The machinery below is retained, not deleted.** Locks, task packets, branch
rules, and `MULTI_MODEL_ORCHESTRATION.md` stay valid and stay documented.
Resume parallel dispatch when (a) a task is genuinely long-running and
file-disjoint — multi-day training is the archetype — and (b) the user asks.
Until then no packet is issued to another model.

Everything else in this file describes how parallel mode works **when it is
switched back on**.

---

**Rule:** if a file/area is locked by an `active` task, no other session edits it.
Claim **before** creating a task branch. One owner, one task, one locked area.

**Orchestrator rule (2026-08-04):** whichever session has repo access and reads
the protocol files is the orchestrator. Model brand tables are advisory only;
**context continuity beats vendor positioning.** Control files
(`ATHENA_STATE.md`, `PUBLICATION_ROADMAP.md`, this file) are orchestrator-owned
except for a worker’s own claim-row update when assigned.

**Fast-track parallelism (v2.4 corrected):** F1 → F2 → F3 → F4 are **serial**.
Do not parallelize P1 final numbers with F1. Genuinely parallel now: licensing
admin (no repo writes) and hostile review (notes only). Multi-model code
parallelism starts at F6–F8.

**Worktree rule (2026-08-04, learned twice in one day).** All sessions share
ONE checkout. `git switch` there changes the branch under every live session,
and `git add -A` then sweeps their uncommitted work into your commit. Any
session working on a branch other than the checkout current branch MUST use
`git worktree add .worktrees/<task> <branch>` and remove it when done. Never
switch the shared checkout while another session is active.

**Reporting rule (user directive 2026-08-04).** Reports to the user are
TABLES first — status board, then decisions needed, then one next action.
Prose only on request.

**Branch rule and its one exception.** Worker tasks run on `task/<id>-<slug>`
branches and are merged by the orchestrator. **Orchestrator-owned critical-path
work runs directly on `dev` by design** — there is no second writer to isolate
from, and a branch would add a merge step without adding safety. Any row whose
branch is `dev` must be orchestrator-owned and say so; workers always branch.

Allowed statuses: `planned` · `packet-ready` (packet written, awaiting a worker to claim) · `active` · `blocked` · `ready-for-review` · `merged` · `cancelled`

| ID | Owner | Role | Branch | Status | Locked files/areas | Started | Handoff |
|---|---|---|---|---|---|---|---|
| F1 | Claude-Orchestrator | OPERATOR | `dev` — orchestrator-owned, per branch exception above | active | `dataset/build_aerialfusecv.py`; `dataset/verify_build.py`; `dataset/README.md`; `zenodo_release/**`; deposit packaging docs under `documentation/` as needed | 2026-08-04 | Blocks F2–F4; no other writer on final P1 numbers until ready-for-review |
| F2 | — | OPERATOR | — | planned | `zenodo_release/**` (after F1) | — | Needs F1 |
| F3 | **user** (drafts ready) | STRATEGIST | no-edit | active | `Context/licensing_emails_DRAFTS.md` — three emails ready to send | 2026-08-04 | Send today; log replies in `Context/` |
| P1-WRITE (F4) | Cursor-Writer (Opus 5) | WRITER | `task/p1-dib-rewrite` | **merged** (73d5c6f) | `papers/p1_aerialfusecv_descriptor/**` | 2026-08-04 | Draft rewritten from build `d4c191a`. Open: deposit DOI, deposit inventory, authorship/CRediT, 4 figures. **Merge note:** this row and F6's row are adjacent — expect a conflict in this table, resolve by keeping both |
| F5 | — | REVIEWER | — | planned | review notes only | — | After F4 draft |
| P1-FIX | Claude-Orchestrator | REVIEWER/OPERATOR | `dev` — orchestrator-owned, per branch exception above | active | `papers/p1_aerialfusecv_descriptor/DRAFT_P1.md` | 2026-08-04 | Remediating second hostile review. B6 (data-ownership argument) in progress. Still open after B6: B3 box_index integrity, B4 pair-correctness audit, S7 licensing (user-owned via F3) |
| F6 | Codex-Operator | OPERATOR | `task/f6-maskrcnn-windows` | **merged** | `experiments/maskrcnn_setup/**`; `dataset/convert_aerialfusecv_to_coco.py` (new files only; NEW conda env, never AV_env) | 2026-08-04 | Chosen path: torchvision fallback in `P2_env`; COCO smoke subset + 50-iteration CUDA smoke run complete; see `experiments/maskrcnn_setup/REPORT.md` |
| F6b | Codex-Operator | OPERATOR | `task/f6b-tiling` | **merged** | — | 2026-08-04 | Last task dispatched before single-operator mode; it was already running when the mode changed, so it was allowed to finish. Full-image vs tiled YOLOv11x-OBB on the 456-image val split: recall 0.607→0.852, AP 0.487→0.669 at IoU 0.5. Tiling becomes the P2 detector protocol, full-image the ablation. **Open:** no tile-border truncation handling — objects spanning a seam are counted twice; quantify before P2 numbers are final |
| F7–F8 | Claude-Orchestrator | OPERATOR | `dev` | planned | experiments / training | — | After F6b. Needs `InstanceSegmenter` protocol + `models/baselines/`; baselines must run tiled to match the detector protocol |
| REVIEW-V24 | — | REVIEWER | no-edit | planned | `ArgusVision_Strategic_Planning/Context/**_REVIEW.md` only | — | Deferred with parallel mode |

## How to claim

1. `git switch dev && git pull`
2. Read this file; confirm no lock overlap.
3. Add or update **one** row: Owner, Branch, Status=`active`, Locked files/areas, Started.
4. Work only inside the lock.
5. On finish: Status → `ready-for-review` or `blocked`; update `WORK_LOG.md`; commit; push.
6. Orchestrator merges to `dev` (workers do not merge independently).

## Releasing a lock

A lock is live for exactly as long as the row says `active` or
`ready-for-review`. Nothing else releases it — not a finished branch, not a
closed session.

- The **orchestrator** sets the row to `merged` and clears the locked-files cell
  at merge time. That is the only moment a lock lifts.
- A worker that stops without finishing sets `blocked`, records why in the
  Handoff cell, and keeps the lock only over files it actually changed.
- Any row `active` for **more than 3 days** with no matching commits is stale:
  challenge it, and the orchestrator may reclaim it. A stale lock blocking live
  work is the failure mode this table exists to prevent — an abandoned claim is
  worse than no claim, because it looks authoritative.

## Worker rules (every task packet repeats these)

- **Push your task branch only. Never push to `dev`.** The orchestrator merges.
- **Prefix every commit message with your task ID** — `[F1] ...`, `[REVIEW-V24] ...`.
  All models commit as the same git author, so the prefix is the *only*
  attribution signal. Without it `git log` cannot tell you which lane produced
  what.
- Tell the user when you finish. The orchestrator has no notification of other
  sessions and will not review a commit it does not know exists.

## Orchestrator audit (run before any merge, and whenever in doubt)

```bash
# who last touched each control file — should be the orchestrator only
for f in Athena_Protocols/ATHENA_STATE.md Athena_Protocols/ACTIVE_TASKS.md \
         ArgusVision_Strategic_Planning/PUBLICATION_ROADMAP.md \
         Athena_Protocols/WORK_LOG.md; do
  printf "%-30s " "$(basename $f)"; git log -1 --format="%h %an %ar" -- "$f"
done

# work in flight outside dev
git branch -a --format="%(refname:short) %(committerdate:relative)" | grep -v dev
```

## Control files (orchestrator-owned)

Do not edit unless the orchestrator explicitly assigns:

- `Athena_Protocols/ATHENA_STATE.md`
- `Athena_Protocols/ATHENA_RISE.md`
- `ArgusVision_Strategic_Planning/PUBLICATION_ROADMAP.md`
- `Athena_Protocols/ACTIVE_TASKS.md` (except your claim row)
- `Athena_Protocols/MULTI_MODEL_ORCHESTRATION.md`
