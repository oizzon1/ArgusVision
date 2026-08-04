# 🦉 ATHENA_LESSONS — Operational Learning

**Read at startup, before taking an objective.** This is the file that stops a
future ATHENA repeating what a past one already paid for.

`WORK_LOG.md` records *what happened* chronologically. `ATHENA_STATE.md` records
*what is true* about the program. **This file records what to do differently** —
distilled, deduplicated, and short enough to actually be read.

## Rules for this file

- A lesson is added when something **cost real time, corrupted an artefact, or
  nearly put a wrong number in a paper**. Not for ordinary friction.
- Each entry states: **what happened → what it cost → the rule now**. A lesson
  without a rule is an anecdote.
- **Recurrence is the important signal.** If a lesson fires twice, mark it
  `⚠ REPEATED` and ask why the rule failed — the rule is probably wrong, not the
  operator.
- Reviewed at session close: promote new lessons here, retire ones made
  structurally impossible by a code change (note what made them obsolete).
- Keep it under ~30 entries. If it grows past that, the weakest have stopped
  earning their place.

---

## A. Environment — this machine specifically

**A1. Disk is the binding constraint, not the GPU.** ⚠ REPEATED
Launching a 456-image read while a 14 GB copy was running stalled the copy
completely for five minutes; both were I/O-bound on `D:`. Earlier the same day,
git commands timed out because git walks the whole tree even for ignored paths
while a build wrote thousands of files.
**Rule:** serialise anything that touches `dataset/`. Before starting a job, ask
what else is reading or writing that disk. GPU idle time is cheaper than a
corrupted or stalled long job.

**A2. `pkill` from WSL does not kill Windows-side processes.**
Python launched through `cmd.exe` interop survives `pkill -f`, keeps file locks,
and blocks directory deletion. Cost: a confusing ten minutes of "why won't this
delete".
**Rule:** identify the real PIDs via `wmic process ... get ProcessId,CommandLine`,
confirm by command line that they are the intended targets, then `taskkill /F`.

**A3. `conda run` buffers stdout until exit.**
A background job's log stays empty while it runs, so "no output" is
indistinguishable from "crashed". A monitor watching only for a success marker
stays silent through a failure.
**Rule:** scripts must create a visible artefact early (output directories at
startup). Monitors must match failure signatures — `Traceback|Error|FAILED` — not
just the happy path.

**A4. Inline `python -c` does not survive `cmd.exe` quoting.**
**Rule:** write a script file and invoke that. Documented in RISE §ENVIRONMENTS.

**A5. PDFs cannot be rendered here — no poppler in WSL.**
**Rule:** extract text with `pypdf` instead. The Read tool's PDF path is unavailable.

---

## B. Git — silent failure modes

**B1. Piping git output to `head` kills the command with SIGPIPE.**
`git add -A | head -2` staged **nothing** because git emits dozens of CRLF
warnings and dies when the pipe closes. The following commit reported "nothing
to commit" and looked like a no-op.
**Rule:** never pipe `git add`/`commit` to `head`. Redirect to `/dev/null` and
check the result with a separate `git status`.

**B2. Unanchored `.gitignore` patterns silently exclude source code.** ⚠ REPEATED
`datasets/` matched `src/datasets/`, so the thesis dataloaders were **never
version-controlled** — absent even from the `thesis-code-final` tag. Later,
`results/` re-inclusion rules matched only exact filenames, so
`build_manifest.json` and `colour_audit.json` fell through: note that
`!results/**/manifest.json` does **not** match `build_manifest.json`.
**Rule:** anchor patterns to the repo root (`/data/`, not `data/`). After adding
any ignore rule, verify intended files with `git check-ignore -v`. Remember that
git cannot re-include a file inside an excluded *directory*.

**B3. `git add -A` sweeps work belonging to another branch.**
**Rule:** stage explicit paths when a session has touched several concerns.

---

## C. Measurement — how numbers go wrong

**C1. Small samples mislead badly on this data.** ⚠ REPEATED
A 6-image smoke run put the seam defect at 18.8% of false positives; the full
456-image split gave **8.9%** — overstated 2×. Deposit-rebuild throughput was
estimated four times (30 min → 6.5 h → 4 h → ~2.5 h) because DOTA images span
800 px to ~13,000 px and short windows caught runs of one size.
**Rule:** never quote a rate or an effect from a smoke sample. State a range and
say what it is based on, or wait for the full run.

**C2. Inspect visually before implementing a fix.**
Aggregate IoU said ground-truth masks disagreed 81% of the time and I
recommended switching to iSAID instance masks. The figures showed `extra=0px` in
every worst case: the disagreement was **different annotated extent**, not
contamination, and the change would have scored box-prompted predictions against
regions the prompt never covered. The user asked for figures first; that request
prevented a bad change.
**Rule:** before changing ground truth or a metric, render the worst cases and
look at them. An aggregate statistic does not identify a mechanism.

**C3. Write prose from the source, never from recollection.**
A Methods draft described the *evaluation* code's algorithm as the dataset's
construction. Caught only by reading the script.
**Rule:** every claim about how something works is sourced from the code line or
data artefact before it is written.

**C4. Verify the port before trusting the improvement.**
Reproducing the precursor build exactly (0 label mismatches, 0 mask mismatches)
is what made the corrected build's +620 pairs attributable to the fix rather
than to a porting bug.
**Rule:** when replacing a pipeline, first reproduce the old one bit-for-bit,
then change one thing.

**C5. Verify a number BEFORE writing it, not before publishing it.** ⚠ NEAR MISS
While correcting an implausible ground-sample-distance range in the P1 draft, I
wrote "15 images report exactly 0.000 m/px" — a figure I had read nowhere. It
was caught only because the artefact was checked before committing. The truth:
*zero* images report 0.000; 21 carry 1.34e-06 m/px, which merely rounds to
0.000 at three decimals. A fabricated number is hardest to spot once it sits in
finished prose, surrounded by correct ones and matching the sentence's rhythm —
the very plausibility that makes it dangerous is what writing it creates.
**Rule:** open the artefact *first*, then write the sentence around what it
says. "Every number traces to `results/`" is not a review step; it is a
precondition for typing the number. This is the strict form of C3.

---

## D. Process

**D1. Two processes writing one output directory corrupt it silently.**
Two deposit rebuilds with different flags interleaved into one tree; file counts
diverged (714 images against 875 labels) and `--verify` would have failed for
reasons unrelated to the script.
**Rule:** before starting a long job, check for an existing instance. Scratch
outputs get a run-specific path or an explicit lock.

**D2. A limited/smoke run must not overwrite a full result.**
A `--limit 2` smoke test destroyed an 8.8-minute full audit by writing the same
report path.
**Rule:** smoke runs write to a distinct path derived from their limit.

**D3. Session state must be restorable, not remembered.**
A session closed unexpectedly mid-sequence. Recovery worked only because the
work was committed.
**Rule:** `WORK_LOG.md` is updated *during* the session — every ~30 min of work,
~20 min idle — and carries a `TODO SEQUENCE (restore point)`.

**D6. In a shipped script, pathological slowness is a correctness defect.**
The deposit's rebuild script scans the full instance mask once per pair, so cost
is pairs x pixels. On the second-densest image (1,718 pairs) it produced no
output for over eleven minutes. It was computing correctly the whole time — but
a stranger running the deposit would have concluded it had hung and killed it,
and a reproduction script that appears to freeze is a reproducibility claim in
name only. I diagnosed it only by sampling the CPU counter and checking pair
density.
**Rule:** anything shipped to a stranger is profiled on the *worst* input in the
dataset, not the median one, and reports progress often enough that working and
wedged are distinguishable from outside.

**D5. Never close a log entry over a running job.**
A closed entry asserts the session's work finished. Today three long jobs
overlapped a session that had already closed once unexpectedly; a close stamped
while the deposit rebuild was still writing would have told the next session
the work was done and left it to discover a live process by collision.
**Rule:** the entry stays **SESSION OPEN** and refreshing until the last
background job completes and its outcome is recorded. Completion is a fact to
be written down, not assumed.

**D4. Own a withdrawn recommendation explicitly.**
Two recommendations were withdrawn after evidence contradicted them (instance
masks as GT; "tiled precision is contaminated"). Both are recorded with the
reasoning that killed them.
**Rule:** when evidence overturns advice, state that plainly in the log and the
decision record. The reasoning that killed a position is more valuable later
than the position.

---

*Seeded 2026-08-04 from `WORK_LOG.md` entries 2026-07-28 → 2026-08-04.*
