# AerialFuseCV: A Paired Detection–Segmentation Dataset for Aerial Imagery

## What This Is

A **Data in Brief data article** (Elsevier, templated) describing the
AerialFuseCV dataset: DOTA v1.0 oriented-box annotations reconciled with iSAID
instance masks at instance level, publicly deposited on Zenodo. The article's
job is to make the dataset citable, peer-reviewed, and reusable — fast. It is
paper #1 of the PhD publication sequence (Roadmap v2.2).

## Core Argument

*(Revised 2026-08-04, task P1-WRITE, to roadmap v2.3/v2.4 and build `d4c191a`.)*

Two expert annotation protocols on the same imagery disagree about what an
object **is**. AerialFuseCV measures that disagreement over every pair,
defines a reconciled mask contract as the response, and releases the
instance-level correspondence with exact discard accounting — 125,722 pairs
across 1,862 images and 15 categories, 98.34% box pairing, reproducible from
the official source downloads.

The novelty claim is the **contract**, not priority over any method line: a
correspondence neither source publishes, with pairing metadata and a logged
reason for every excluded object.

## Requirements

### Must Have

- [ ] Official Data in Brief template (Word) — **download into
      `papers/shared/venues/data-in-brief/` before writing; submissions
      without it are rejected**
- [ ] Specifications Table complete (subject area ≤150 chars; data
      accessibility = Zenodo DOI + direct URL)
- [ ] Value of the Data: 3+ bullets, no background/interpretation/conclusions
- [ ] Data Description covering every file/folder in the Zenodo deposit
- [ ] Experimental Design, Materials and Methods = construction pipeline
      (matching algorithm, IoU ≥ 0.1 conservative threshold, discard rules)
- [ ] Limitations ≤200 words
- [ ] Abstract 100–500 words (template v19), describes collection + data + reuse, no interpretation
- [ ] Title contains "data"/"dataset"; keywords 4–8, no title-word repeats; ≤20 numbered references incl. the Zenodo deposit
- [ ] Ethics statement, CRediT, Declaration of Competing Interests
- [ ] **Zenodo DOI live before submission (P0 — blocking dependency)**
- [ ] Every number traces to a `results/` artefact. The thesis is **not** a source

### Should Have

- [ ] Per-class match-rate table (worst: soccer-ball-field 94.2%, basketball-court 95.2%)
- [ ] Class-distribution figure (70.4% concentration in top-3 classes)
- [ ] Example image + paired annotations figure
- [ ] Construction-pipeline flow diagram

### Out of Scope

- Benchmark results (YOLO/SAM/pipeline numbers) — that is P2's story; DiB
  data articles describe data, not findings
- Comparison with other datasets' benchmark suitability — P4 territory
- Any claim requiring interpretation of model behavior

## Target Audience

Aerial/remote-sensing CV researchers who need paired box–mask supervision
(detect-then-segment pipelines, instance segmentation, weak supervision);
dataset users searching Scopus/ScienceDirect for aerial instance data;
future P2/P3/P4 reviewers checking the dataset citation.

## Constraints

- **Venue:** Data in Brief (Elsevier). Mandatory template **v19 (Dec 2024),
  in `papers/shared/venues/data-in-brief/`**. Single-anonymized review,
  ≥2 reviewers. Abstract 100–500 w; subject area ≤150 chars; Limitations
  ≤200 w; ≤20 references. APC ~$500 (VERIFY current amount).
- **Fallback:** ISPRS OJPRS as a regular application Paper (no data-paper
  type there) — requires reframing with validation as the research weight,
  ~2–3 days conversion.
- **Timeline:** P0 Zenodo release Aug 2026 → submit Sep 2026.
- **License chain:** DOTA/iSAID images are not redistributable — deposit
  contains annotations + pairing metadata + construction script (CC-BY 4.0 on
  our contribution). The article must state this plainly.
- "Related research article" field: none at submission (P2 not yet
  submitted); relate to the MSc thesis if the template requires an entry.

## Key Decisions

| Decision | Reasoning | Date |
|---|---|---|
| Data in Brief primary (was ISPRS OJPRS) | Verified guides: OJPRS has no data-paper type; DiB is purpose-built, templated, fast, near-certain — P1's job is a quick countable acceptance | 2026-07-29 |
| Core argument = first paired dataset | The novelty claim is the memorable fact; method and utility support it | 2026-07-29 |
| Workflow Interactive + Standard | First submission of the program; gates on | 2026-07-29 |
| Planning docs committed, no branches | Monorepo everything-in-git decision; existing branch policy | 2026-07-29 |
| Core argument = protocol divergence + reconciled contract (**supersedes "first paired dataset"**) | A bare priority claim invites a reviewer to hunt for a counterexample, and the competitive review found neighbours close enough to make that a real risk. The measured disagreement is ours regardless of who else pairs boxes with masks | 2026-08-04 |
| `DRAFT_P1.md` is the single source of truth; `sections/*.md` reduced to pointers | Two texts with different numbers for one dataset is how a wrong figure reaches submission | 2026-08-04 |
