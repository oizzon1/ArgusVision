# Data in Brief — editorial scope ruling on the AerialFuseCV deposit

**Received:** 2026-08-06 · **From:** Arunabha Bose, PhD, Scientific Editor, Data
in Brief (Elsevier), relaying notes from the Executive Editor · **In reply to:**
our pre-submission enquiry (`licensing_emails_DRAFTS.md`) · **Raw text:**
`papers/p1_aerialfusecv_descriptor/DiB Editor Responce.txt`

This is the authoritative scope ruling for P1. It is an editorial position in
writing, not our interpretation of policy, and it should be cited as such in
any future discussion of P1's viability.

## What was ruled

**The correspondence-plus-script deposit is in scope and compliant.** Verbatim:
the structure and manuscript are *"completely within scope of Data in Brief, and
satisfy our data availability requirements, provided specific standard
conditions are met"*, and where third-party licences prohibit redistribution,
*"a reproducibility pipeline deposit (correspondence metadata, discard logs, and
an automated build script) is fully compliant."*

**Derived datasets are in scope.** *"Data articles describing novel derived,
fused, or transformed datasets are fully within the scope. The proposed dataset
adds clear value through instance-level paired alignment and quality filtering.
The creation approach constitutes valuable data descriptor research."*

## Effect on open risks

| Risk | Before | After |
|---|---|---|
| **B6** data-ownership / desk-reject | Hostile review's strongest structural objection: DiB requires data "produced and owned by the author", ours is derived correspondence, and the argument was never made in prose | **Retired.** The editor states derived datasets are in scope and this deposit model is compliant. The `Provenance and ownership` section becomes supporting material, not a defence |
| **S7** licensing unconfirmed | Academic-use derivation claim rested on unanswered emails; treated as blocking | **Downgraded.** The editor prescribes the wording — non-commercial research/academic use per the source licences — so the manuscript can proceed without waiting on the NTUA research-data office. Chase the office for institutional cover, not for permission to submit |

## Conditions attached — all mandatory

### Zenodo deposit

| # | Condition | Status at time of writing |
|---|---|---|
| i | Script(s) must run without error, using official source URLs/APIs to download, pair, process and output the dataset | Runs clean and verified (1,862 images, 100% resolve, 7,448/7,448 checksums). **Does not download** — see caveat below |
| ii | Clear index/identifier correspondence files and full discard accounting logs | Met. `correspondence.jsonl` + `discarded.jsonl`; accounting identity exact (351,837 = 2,121 + 349,716) |
| iii | Step-by-step documentation: prerequisites, environment setup, source download locations, execution commands | **Not written** (`SETUP.md`) |
| iv | Static, accessible Zenodo DOI | Pending F2 |

### Manuscript

| # | Condition | Status at time of writing |
|---|---|---|
| i | Licensing constraints of DOTA v1.0 and iSAID stated in **Specifications Table** *and* **Value of the Data**; explicit non-commercial research/academic use statement | **Absent.** "Non-commercial" appears nowhere in the draft |
| ii | Pairing logic, **alignment verification**, discard criteria and filtering statistics in Experimental Design, Materials and Methods | Pairing logic, discard criteria, filtering statistics present. **Alignment verification absent** |
| iii | Direct citations and working URLs to the official download pages of both parent datasets | **Absent** from both the draft and `references.bib` |

## Two judgements this ruling forces

**Condition i for Zenodo asks the script to *download* from official
URLs/APIs. Ours does not, and should not pretend to.** DOTA v1.0 and iSAID are
distributed through Google Drive folders; automated fetching is unreliable and
sits badly with their terms. The defensible position is a script that verifies
the sources and fails with exact, actionable instructions, plus `SETUP.md`
documenting the download precisely — and to state that openly rather than let a
reviewer discover it. **Recommend a short clarifying reply to the editor before
submission** rather than submitting on an unstated divergence from a condition.

**"Alignment verification" is B4.** The editor is asking for evidence that a
paired box and mask describe the same physical object. That is exactly the
~200-pair stratified identity audit already identified as the strongest
evidence still addable. It is now an editor expectation rather than an optional
strengthening, and it cannot be satisfied by the IoU statistics already in the
draft — IoU ≥ 0.1 is an acceptance rule, not proof of identity.

## Standing instruction

Work these conditions one at a time to completion, verifying each with the user
before moving to the next, until all seven are met. Partial compliance on a
condition the editor named in writing is worse than no attempt, because it
reads as having been addressed.

## Decision — 2026-08-06 (user directive)

**Proceed on the editor's prescribed wording. Do not block publication on legal
resolution.**

Reasoning, recorded because it will otherwise be re-litigated: neither parent
dataset publishes a formal licence — DOTA and iSAID each carry a *statement*
("academic purposes only, commercial use prohibited"), not a licence document
with defined terms. Zenodo, meanwhile, permits commercial licences. There is no
authority that can reconcile these into a clean answer, and pursuing one has no
terminating condition. The editor of the target journal has stated in writing
what the manuscript must say; that is the operative standard.

**Consequences:**

- **S7 is no longer a blocker.** The licensing emails stay sent as courtesy and
  for institutional cover, not as a gate on submission. A reply that never
  arrives changes nothing.
- **The manuscript states inherited intent, not an invented licence.** It
  reports both parents' terms verbatim and declares non-commercial academic use
  in accordance with them. It does not assert a licence for our contribution,
  because that is NTUA's call and asserting it would be a claim we cannot
  support.
- **One real inconsistency must still be fixed before Z-iv:**
  `zenodo_release/README.md` specifies **CC-BY 4.0** on our contribution, which
  permits commercial use and contradicts both the parent terms and the
  manuscript. This is not a legal question — it is two of our own documents
  disagreeing, visible to any reviewer in seconds. Resolve at packaging time by
  matching the deposit's stated terms to the manuscript's.

This is an engineering decision about where to stop, not a legal opinion.

## Decision — 2026-08-06, Zenodo condition i (user directive)

**No clarifying reply to the editor. The divergence is stated in the
manuscript instead.**

This supersedes the recommendation above to write to Abha before submitting.

The condition asks that the script *"download"* via official source URLs/APIs.
It does not, and cannot: both parent datasets are distributed through Baidu
Drive and Google Drive folders — confirmed on both official pages, 2026-08-06 —
neither of which offers a programmatic interface, and automated fetching would
sit badly with terms that restrict use to academic purposes.

Stating it in the paper is the stronger option. It is permanent, it reaches
every reviewer and reader rather than one inbox, and it removes a
correspondence round-trip from the critical path. An emailed clarification that
never reaches the reviewers would leave exactly the impression we are trying to
avoid.

What the manuscript must therefore say plainly:

- the sources are distributed via Drive folders with no API;
- the script verifies the sources and fails with named diagnostics rather than
  fetching them;
- `SETUP.md` documents the download and extraction precisely;
- the deposited checksums are what make the result verifiable, which is the
  substance the condition is protecting.

The obligation this creates: the verification path has to be genuinely good,
because it is now the answer to the condition rather than a workaround for it.
