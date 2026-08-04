# Publication Roadmap v2.4
### ArgusVision PhD — Panagiotis Fragkos
**Base:** Master Thesis (Phase 0) — Object Detection and Semantic Segmentation of Aerial and Satellite Imagery with Deep Learning
**Program:** PhD in Photogrammetry, NTUA | **Supervisor:** Prof. Charalampos Ioannidis
**Roadmap version:** 2.4, 2026-08-04 (FAST TRACK — most science done; compress to submission critical path) | **Replaces:** v2.3, 2026-08-04

> **Status: LIVING DOCUMENT.** Revised only through the Roadmap Revision Protocol in `Athena_Protocols/ATHENA_RISE.md` (triggers: supervisor instruction · new finding · milestone outcome · external event). Minor version bump for date/venue/scope changes, major bump for papers added/cancelled/merged. Every revision is recorded with reasoning in the changelog at the bottom of this file and mirrored to `ATHENA_STATE.md`.

---

## Strategy Change from v1

The draft planned four journal papers, opening with a VBB vs OBB letter. That letter compared COCO-pretrained VBB models against DOTA-pretrained OBB models, which confounds representation with training domain. Rather than defend a vulnerable standalone claim, the VBB/OBB material moves inside the flagship paper together with a new ablation (VBB trained on DOTA HBB annotations) that resolves the confound.

The fast first publication is now the dataset descriptor at a fast community venue instead of Scientific Data, whose review times run 4 to 8 months. A conference paper is added as insurance and visibility.

**Regulation context:** NTUA requires at least 3 peer-reviewed publications to defend. Conference papers count. This plan yields 4 countable items, with the third expected accepted by mid Year 2.

### v2.4 directive — publish fast

Most of the science is already done. The bottleneck is no longer discovery; it is **release → write → submit**. v2.4 compresses the calendar to the critical path, freezes scope, and defers everything that does not unblock a submission.

**Need statement (locked for P1/P2 intros):**

> Many aerial workflows are box-rich and mask-poor. A detector→promptable-segmenter pipeline tests whether existing detection assets can yield usable instance masks without training a segmenter. That question is only measurable with object-level paired detection–segmentation data. Supervised segmenters remain the ceiling under full mask supervision; we evaluate the conversion on DOTA∩iSAID classes, with operational relevance to urban mapping, maritime surveillance, infrastructure inspection, environmental monitoring, and rapid damage assessment.

### v2.3 competitive upgrade (positioning, not a new sequence)

The 2024–2026 literature is dense on *methods* (RSPrompter, SAM-RSIS, OBSeg, SOPSeg/ReSOS, InstructSAM, AerOSeg, YOLO+SAM engineering papers) and still thin on *annotation contracts* and *cascade failure science*. ArgusVision therefore does **not** compete as “another SAM wrapper.” It competes on three durable assets:

1. **Instance-level DOTA↔iSAID pairing with discard accounting** — iSAID shares DOTA imagery but was annotated from scratch; no public release links oriented boxes to masks object-by-object with pairing metadata and discard reasons.
2. **Protocol divergence, measured exhaustively** — extent disagreement vs foreign contamination across all matched pairs; class-level conventions (e.g. harbor, baseball-diamond) disagree by design, not noise. Evidence: `results/experimental/AerialFuseCV_Testing/` and `documentation/DECISION_reconciled_masks.md`.
3. **An evaluator that separates detector failure from mask quality** under a pairs-only contract — so a cascade paper remains valid even if supervised baselines win on absolute score.

Full competitive map and claim landmines: `ArgusVision_Strategic_Planning/Context/competitive_landscape_2026-08_NOTES.md`.

**What we stop claiming (reviewer landmines):**

- “First SAM in remote sensing”
- “First iSAID segmentation”
- “First OBB prompts for SAM” (OBSeg, SOPSeg already own this)
- “YOLO+SAM is novel” (tutorials + YOLOSAM + RSPrompter SAM-det lineage)
- Any number that does not live in `results/` (MSc thesis is not a source)

**Preferred claim language:**

> Paired object-level detect→segment contract; protocol reconciliation; cascade error decomposition; training-free vs supervised tradeoff when masks are scarce.

---

## Overview (fast-track dates)

| # | Order | Paper | Type | Target Submit | Expected Acceptance |
|---|---|---|---|---|---|
| P0 | prereq | AerialFuseCV Zenodo release (DOI) | Data release | **by 2026-08-22** | DOI live immediately |
| P1 | 1st | AerialFuseCV: protocol-aware paired detection–segmentation dataset | Data descriptor | **by 2026-09-05** | Oct–Nov 2026 (DiB) |
| P2 | 2nd | Cascade reliability: training-free detection→segmentation | Full journal | **by 2027-01-31** | Late 2027 |
| P3 | 3rd | Conference paper (condensed cascade findings) | Conference | **IGARSS ~Jan 2027** (primary) | Spring 2027 |
| P4 | 4th | ArgusVisionBench | Benchmark | Sep–Oct 2027 | 2028 — **frozen until P1+P2 submitted** |

Beyond P0–P4: parked / candidate papers stay **frozen**. No C1/C2/C3 activation until P1 is submitted and P2 experiments are complete.

---

## FAST TRACK — Done vs Remaining vs Deferred

### Already done (do not re-open)

| Asset | Status |
|---|---|
| Corrected AerialFuseCV build (oriented matching, pairs-only, reconciled masks) | Done — evidence in `results/experimental/AerialFuseCV_Testing/` |
| Protocol divergence measurement (extent vs foreign) | Done |
| Pipeline evaluation on reconciled masks | Done |
| EDA + P1 figures | Done |
| Codebase restructure + frozen evaluator | Done |
| Competitive positioning + need statement | Done (v2.3 / this session) |
| P1 section drafts | Exist — need rewrite, not invent |
| Internal one-pass builder `dataset/build_aerialfusecv.py` | Exists (OPEN 6 largely mitigated) |

### Remaining on the critical path (only these unblock submissions)

| # | Task | Blocks | Effort | Owner mode |
|---|---|---|---|---|
| F1 | Deposit-ready rebuild script + verify identical to internal build | P0 | 2–3 days | OPERATOR |
| F2 | Zenodo package: annotations, `pairs.jsonl`, discard logs, README, LICENSE, checksums; **v1.0** label | P0 / P1 | 2 days | OPERATOR |
| F3 | Licensing MVP: reference DOTA/iSAID images (do not redistribute); CC-BY on our contribution; chase NTUA office in parallel, do not wait forever | P0 | 1 day + parallel admin | STRATEGIST+user |
| F4 | P1 rewrite: protocol spine + numbers from `results/` only + DiB template | P1 | 4–5 days | OPERATOR/writing |
| F5 | P1 REVIEWER pass + submit DiB | P1 | 1–2 days | REVIEWER |
| F6 | OPEN 5: Mask R-CNN path on Windows (MMDetection or torchvision) | P2 | 2–4 days | OPERATOR |
| F7 | Train Mask R-CNN + YOLOv11-seg on AerialFuseCV | P2 / P3 | 5–7 days | OPERATOR |
| F8 | Confidence filtering + PR curves | P2 / P3 | 2–3 days | OPERATOR |
| F9 | P2 write + submit ISPRS Journal | P2 | 3–4 weeks writing after F7–F8 | writing |
| F10 | P3 condense + submit IGARSS | P3 | 1–2 weeks after F7–F8 | writing |

### Explicitly deferred (do not touch until F5 done)

- P4 experiments / DIOR / NWPU / SAM2 grid
- Candidate papers C1–C3 as separate submissions (C1 evidence may live *inside* P1 only)
- Parked VBB-vs-OBB, SAM batch, standalone OBB paper
- Component-aware extraction fix (2.61%) — **disclose in Limitations**, do not block P0
- Legacy `src/` deletion sweep, env polish, non-critical refactors
- Stretch venue upgrade of P1 to OJPRS — DiB first for speed

---

## Week-by-week sprint plan

```
WEEK 1  (2026-08-04 → 08-10)   CRITICAL PATH
  Mon–Wed  F1 deposit rebuild script + verification build
  Thu–Fri  F2 package skeleton + F3 licensing MVP text
  Parallel Writing: freeze need-statement paragraphs for P1 Value-of-the-Data

WEEK 2  (08-11 → 08-17)
  Mon–Tue  F2 Zenodo upload → DOI live  (= P0 DONE, target ≤ 08-15)
  Wed–Fri  F4 P1 rewrite begins (Spec table, Value of Data, Data Description,
           Methods, Limitations) — all numbers from results/ only
  Parallel F6 start OPEN 5 Mask R-CNN path (does not block P1)

WEEK 3  (08-18 → 08-24)
  Mon–Wed  F4 finish P1 + figures check
  Thu      F5 REVIEWER pass
  Fri      P1 SUBMIT Data in Brief  (target ≤ 2026-09-05; stretch = this week)
  Parallel F6 complete; begin F7 YOLOv11-seg (faster than Mask R-CNN)

WEEK 4–5 (08-25 → 09-07)
  F7 Mask R-CNN + YOLOv11-seg training/eval on AerialFuseCV
  F8 confidence filtering + PR curves
  P2 experiment block COMPLETE (target ≤ 2026-09-15)

WEEK 6–10 (09-15 → 10-31)
  P2 writing (cascade reliability framing; related-work posture from v2.3)
  P3 condensation draft from same results (do not invent new experiments)

NOV–DEC 2026
  P1 review/revision cycles (DiB)
  P2 polish; prepare P3 for IGARSS call

JAN 2027
  P3 SUBMIT IGARSS (primary). EarthVision only if IGARSS missed / weak fit.

BY 2027-01-31
  P2 SUBMIT ISPRS Journal (pulled forward from Feb)

AFTER P1 accepted + P2 submitted
  Unlock P4 planning; consider C1 letter only if discrepancy material was cut from P1
```

**Acceptance targets under fast track**

| Milestone | When | Countable |
|---|---|---|
| P0 DOI | ≤ 2026-08-22 | — |
| P1 submitted | ≤ 2026-09-05 | — |
| P1 accepted | Oct–Nov 2026 | **#1** |
| P2 experiments done | ≤ 2026-09-15 | — |
| P3 submitted | Jan 2027 | — |
| P2 submitted | ≤ 2027-01-31 | — |
| P3 accepted | Spring 2027 | **#2** |
| P2 accepted | Late 2027 | **#3 — NTUA met** |

---

## Competitive Landscape (summary)

| Competitor | What they own | Threat / response |
|---|---|---|
| **RSPrompter** (TGRS 2024) | Learned prompts for SAM on RS | High if P2 claims “first automated SAM”; cite as related; differentiate as training-free cascade + paired contract |
| **SAM-RSIS** | Fine-tuned SAM + box prompts | Medium — adapted, not training-free; cite in related work |
| **OBSeg** | OBB prompt encoder for SAM | **Kills parked “first OBB prompts” as written** → reframe (geometry/evaluation under reconciled GT) |
| **SOPSeg / ReSOS** | OBB→mask generation; ~750k small-object masks from SODA-A | Closest dataset neighbour — *synthetic* masks, not dual-protocol reconciliation; AerialFuseCV remains the dual-human pairing test bed |
| **InstructSAM** | Training-free LVLM+SAM2+CLIP recognition | Related work for P2; different task |
| **AerOSeg / SegEarth-OV / ConInfer** | Open-vocab semantic segmentation | Different output contract; P4 context baselines only if deliberately broadened |
| **YOLOSAM / SILCON YOLO+SAM** | Engineering pipelines, often single-class | Low if P2 is analysis-first |

**Strategic verdict:** publish the **contract and the failure science**, not another foundation-model recipe.

---

## P0 — AerialFuseCV Zenodo Release (prerequisite, not a paper)

DOTA v1.0 and iSAID are released for academic use and cannot be redistributed as images. The release therefore contains annotations, pairing metadata, reconciled-mask derivation artefacts we own, and a construction script that rebuilds AerialFuseCV from official DOTA and iSAID downloads. This is standard practice in the DOTA ecosystem.

| Task | Effort |
|---|---|
| Package annotations and pairing metadata (CC-BY 4.0 on our contribution) | 2 days |
| Construction script with verification checksums | 2–3 days — internal builder exists; deposit-scoped script + verify still required (F1) |
| README with file structure, formats, usage, reconciled-mask definition | 1 day |
| Zenodo upload, DOI minted | 1 day |
| **Total** | **~1 week (F1–F3). Target DOI ≤ 2026-08-22** |

The DOI becomes the citation anchor for P1, P2, P3, P4, and any activated candidate paper.

**Versioning decision (OPEN 7):** recommend **v1.0 = first public release**, with a note that earlier internal experiments used an unreleased precursor — one DOI, no phantom version history.

---

## P1 — AerialFuseCV Data Descriptor (protocol-aware)

> **v2.3 argument upgrade.** Do not sell P1 as “we joined DOTA and iSAID.” Sell it as:
>
> Two expert annotation protocols on the same imagery disagree about what an object *is*. We measure that disagreement (extent vs foreign contamination), define a reconciled contract for detect→segment evaluation, release instance-level pairing with discard accounting, and make the cascade question measurable.
>
> That differentiates AerialFuseCV from iSAID alone (masks without DOTA identity linkage) and from ReSOS (model-generated masks from boxes).

| Field | Detail |
|---|---|
| Type | Data descriptor, ~3000 words (DiB template) |
| Target submit | **≤ 2026-09-05** (fast track) |
| Content source | Corrected build + `results/experimental/AerialFuseCV_Testing/` + decision records; **not** the MSc thesis as evidence |
| Scale (corrected build; cite `results/` at write time) | Pairs-only dataset; 15 classes; oriented-polygon matching; reconciled masks = matched iSAID instance ∩ oriented DOTA box |

### Central claims (must survive hostile review)

1. **Novelty of contract** — validated one-to-one box↔mask pairs with pairing metadata and discard logs; not “first aerial segmentation dataset.”
2. **Protocol divergence** — measured disagreement between DOTA extent conventions and iSAID instance extents; reconciled masks justified for box-prompted evaluation.
3. **Scope honesty** — pairs-only by design (`documentation/DECISION_unpaired_annotations.md`); detectors absolute precision → DOTA; segmenters → iSAID; unified systems → AerialFuseCV.
4. **Reproducibility** — deposit = annotations + pairing metadata + construction script + checksums; rebuild from official downloads.

### Venues

| Priority | Journal | IF (2024) | Notes |
|---|---|---|---|
| Primary | **Data in Brief (Elsevier)** | ~1.2 | Fast first acceptance; mandatory template; DOI required at submission. Keep for timeline insurance |
| Stretch / upgrade path | ISPRS Open Journal of Photogrammetry and Remote Sensing | no IF yet | Reframe as application/methods Paper if the discrepancy analysis is centered and word budget allows |
| Deferred | Scientific Data | higher | Only if review latency becomes acceptable; not the Year-1 first-acceptance vehicle |

Venue guides: `papers/shared/venues/{data-in-brief,isprs-ojprs}/`. DiB hard requirements: mandatory template, deposit DOI live at submission, Limitations ≤200 w.

### Extra Work Needed

| Task | Effort |
|---|---|
| P0 complete (blocking), including OPEN 6 construction Stages 1+3 | see P0 |
| Re-source all P1 numbers from corrected-build `results/` (not thesis tables) | 1–2 days |
| Center Value-of-the-Data + Methods on protocol divergence + reconciled masks | 2–3 days (rewrite of drafts) |
| End-to-end reproducibility run | 3–5 days |
| **Total** | **~1 week after P0 DOI (F4–F5)** |

---

## P2 — Flagship: Cascade Reliability (Training-Free Detection→Segmentation)

> **v2.3 framing upgrade.** P2 is a **cascade-reliability** paper, not a “SAM beats Mask R-CNN” or “novel YOLO+SAM” paper.
>
> Winning claim: when only boxes exist (or masks are costly), a training-free detector→promptable-segmenter path is operationally useful **if** we quantify where it dies (recall bottleneck, prompt geometry, FP overhead) against supervised baselines on the **same paired contract**.
>
> **Scope finalized with supervisor, 2026-07-29** (unchanged experimentally): pipeline + Mask R-CNN + YOLOv11-seg + confidence filtering + PR curves. VBB-on-DOTA-HBB ablation remains **out**. VBB(COCO) 0.34% F1 may appear only as motivation with the domain confound acknowledged — never as a representation claim.

| Field | Detail |
|---|---|
| Type | Full journal paper, ~9000–10000 words |
| Target submit | **≤ 2027-01-31** (fast track; was Feb 2027) |
| Content source | Re-run experiments into `results/`; GT-prompt upper bound vs full pipeline; supervised baselines on AerialFuseCV |

### Related-work posture (mandatory)

Cite as neighbours, then differentiate:

- RSPrompter / SAM-RSIS — learned or adapted SAM for RS instance segmentation
- OBSeg / SOPSeg — OBB prompting (they own prompt-encoder novelty)
- InstructSAM / AerOSeg — training-free or OV semantic/recognition lines (different contracts)

**Our wedge:** GT-prompt upper bound vs detector-prompted pipeline; detector bottleneck; confidence filtering; PR curves; honest failure taxonomy; training-free vs supervised tradeoff under AerialFuseCV’s pairs-only evaluator.

**Survival rule:** if supervised baselines win on absolute score, the paper still stands — the contribution is the quantified tradeoff and failure analysis, not a guaranteed win claim.

### Venues

| Priority | Journal | IF (2024) | Notes |
|---|---|---|---|
| Primary | ISPRS Journal of Photogrammetry and Remote Sensing | ~10.6 | Fits if cascade analysis + photogrammetric evaluation depth are strong |
| Fallback | IEEE TGRS | ~7.5 | Stronger if the paper reads as systems/benchmark comparison |

### Experiment Block (unchanged from v2.1)

| Experiment | Purpose | Effort |
|---|---|---|
| Mask R-CNN trained on AerialFuseCV | Supervised classic baseline | 3–5 days |
| YOLOv11-seg trained on AerialFuseCV | Supervised baseline, same family as detector | 2–3 days |
| Confidence-based segmentation filtering | Addresses false-positive overhead from detector | 2–3 days |
| PR curves at IoU 0.1 / 0.3 / 0.5 | Sensitivity analysis | 2–3 days |
| **Total** | | **~2–3 weeks, parallelizable** |

**Blocked by:** Mask R-CNN-on-Windows path (STATE OPEN 5 — MMDetection primary, torchvision fallback) before Sep 2026.

---

## P3 — Conference Paper (insurance and visibility)

> Condensed cascade findings. Conference-to-journal extension is accepted practice; no conflict with P2.
>
> **Confirmed kept (2026-07-29).** Nothing new — same P2 material at conference length. Value: NTUA 3-paper insurance + visibility before the journal lands.

| Field | Detail |
|---|---|
| Type | Short/full conference paper, peer reviewed |
| Content source | P2 condensed, ~1–2 weeks writing |

### Venues (decide when calls open)

| Priority | Venue | Deadline | Notes |
|---|---|---|---|
| Earlier option | IGARSS 2027 | ~Jan 2027 | 4 pages excl. refs |
| Visibility option | EarthVision @ CVPR 2027 | ~Feb–Mar 2027 | 8 pages excl. refs, CVPR template, double-blind |

Both land after P2 experiments (Oct 2026). Facts: `papers/shared/venues/earthvision-igarss/NOTES.md`.

---

## P4 — ArgusVisionBench (detector × segmenter)

> Full configuration space for aerial **instance-level detect→segment pipelines** (not open-vocabulary semantic segmentation unless deliberately revised).
>
> **v2.3 brand narrowing:** frozen evaluator; dual GT modes where useful (raw iSAID instance vs reconciled mask); cascade metrics that separate detection error from mask quality; detector axis × segmenter axis.
>
> Stretch: community leaderboard. Do **not** broaden into AerOSeg/ConInfer turf without a Revision Protocol event.

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

No CVPR/ICCV gamble for the benchmark (v2.0 decision stands).

### Experiment Blocks

| Block | Content | Effort |
|---|---|---|
| SAM2 family | tiny/small/base+/large × Box/Point (8 configs) | 3–4 weeks (with lightweight variants) |
| Lightweight variants | MobileSAM, FastSAM, EfficientSAM × Box/Point (6 configs) | included above |
| Fine-tuned SAM ViT-B on AerialFuseCV | Domain adaptation, GPU-intensive | 4–6 weeks |
| Prompt strategies | Hybrid (box+point); **HBB vs OBB geometry under reconciled GT** (absorbs reframed parked OBB idea) | 2–3 weeks |
| Cross-dataset validation | DIOR, NWPU VHR-10 | 2–3 weeks |
| Detector axis | Detector variants × segmenter pairings — block design due before Mar 2027 | TBD |
| Optional context baselines | RSPrompter / SAM-RSIS / OBSeg as comparison families if schedule allows | TBD |
| Writing and review cycles | | 6–8 weeks |
| **Total** | | **~4–5 months active work (before detector-axis sizing)** |

---

## Parked Single-Scope Papers (not scheduled)

Parked means: no venue, no date, no experiments committed; activation = Revision Protocol event (major version bump if scheduled into the countable sequence).

| Idea | Core content | Status after v2.3 |
|---|---|---|
| VBB vs OBB for aerial detection | Representation question with VBB-on-DOTA-HBB ablation | Still parked; scientifically clean but crowded; activate only if early fourth countable item is needed |
| SAM batch processing | Throughput/efficiency of batched SAM for large-scale aerial processing | Still parked; operational filler after P2; unlikely flagship |
| **OBB prompt support (REFRAMED)** | ~~“First OBB prompts for SAM”~~ → **Geometry/evaluation study:** under protocol-reconciled GT, how much does HBB vs OBB prompting change cascade error, and when does prompt geometry fight annotation-extent conventions? | **Must not claim prompt-encoder novelty** (OBSeg, SOPSeg). Prefer absorb into P4 prompt-strategies block; standalone only with the reframed claim |

---

## Candidate Opportunity Papers (not scheduled — Tier S/A)

Ideas identified in the 2026-08-04 competitive review that can stand competition because they exploit unique ArgusVision evidence. **Not** in the P0–P4 countable sequence. Activate only after P0 is live and P1/P2 are on track.

| ID | Idea | Why it can compete | Suggested venues | Earliest activation |
|---|---|---|---|---|
| **C1** | **Annotation Protocol Divergence** — extent vs contamination on DOTA∩iSAID | Original exhaustive measurement; few papers quantify dual-protocol disagreement | ISPRS Journal / IJRS methods letter; or spine already inside P1 | After P1 submit (or as P1 stretch rewrite) |
| **C2** | **Annotation amplification / auto-mask quality** — score SAM/SOPSeg-style box→mask generators against AerialFuseCV dual-human pairs | Turns dataset into a test bed for automatic annotation without racing ReSOS on scale | TGRS / ISPRS OJPRS / EarthVision | After P2 core experiments |
| **C3** | **Cascade reliability systems note** (if P2 is too long) — confidence filtering + operational photogrammetry angle | Fits Ioannidis lab narrative; lower novelty than C1/C2 | IGARSS / photogrammetry venue | Only if P2 splits |

**Priority among candidates:** C1 highest originality-per-effort (evidence already in `results/experimental/AerialFuseCV_Testing/`); C2 strongest follow-on once P0 DOI exists; C3 only if writing pressure forces a split.

---

## Sequencing (fast track — authoritative)

```
≤ 2026-08-22   P0 Zenodo DOI
≤ 2026-09-05   P1 SUBMIT (Data in Brief)
≤ 2026-09-15   P2 experiments complete (F6–F8)
Oct–Nov 2026   P1 expected acceptance (= countable #1)
Sep–Oct 2026   P2 writing + P3 draft
Jan 2027       P3 SUBMIT IGARSS (= path to countable #2)
≤ 2027-01-31   P2 SUBMIT ISPRS Journal
Spring 2027    P3 expected acceptance
Late 2027      P2 expected acceptance (= countable #3, NTUA met)
After P2 sub   Unlock P4; optional C1 only if cut from P1
```

## Regulation Tracking (3 peer-reviewed papers required to defend)

| Milestone | Expected | Count |
|---|---|---|
| P1 accepted | Oct–Nov 2026 | 1 |
| P3 accepted | Spring 2027 | 2 |
| P2 accepted | Late 2027 | 3 — requirement met |
| P4 accepted | 2028 | 4 — slack |

## Key Dependencies

| Dependency | Blocks |
|---|---|
| F1–F3 → P0 Zenodo DOI | P1 submission; citations in P2/P3/P4 |
| Re-source P1 from corrected-build `results/` | Honest P1 numbers |
| F6 Mask R-CNN-on-Windows (OPEN 5) | P2 supervised baselines |
| F7–F8 P2 experiments | P2 writing + P3 condensation |
| P1 submitted | Unlock optional C1 consideration |
| P2 submitted | Unlock P4 planning |

## Tooling

- Writing: WTF-P (`npx wtf-p`) via Claude Code
- Experiments: Python, PyTorch, Ultralytics, SAM/SAM2 official repos, MMDetection / torchvision Mask R-CNN
- Dataset hosting: Zenodo
- GPU: RTX 3090 Ti
- Strategic context: `ArgusVision_Strategic_Planning/Context/`

*Last updated: 2026-08-04 (v2.4 — fast track).*

---

## Changelog

| Version | Date | Trigger | Change & reasoning |
|---|---|---|---|
| v1 (draft) | Jul 2026 | — | Four journal papers, opening with VBB-vs-OBB letter at GRSL. |
| v2.0 | Jul 2026 | Strategy review | Letter cancelled; Scientific Data dropped; P3 added; RT-DETR-seg dropped; no CVPR/ICCV for P4. |
| v2.0 (annot.) | 2026-07-28 | Environment restructure | Living-document header + changelog; P2 scope open item. |
| v2.1 | 2026-07-29 | Supervisor instruction | P2 trimmed; ablation parked; P4 → detector × segmenter; parked section added. |
| v2.2 | 2026-07-29 | Venue guides verified | P1 → Data in Brief; P3 deadlines corrected. |
| v2.3 | 2026-08-04 | Competitive literature review | Positioning upgrade; P1 protocol spine; P2 cascade framing; OBB reframe; candidates C1–C3. |
| **v2.4** | **2026-08-04** | **User directive — publish fast; most science done** | **Fast-track execution plan.** Compress dates: P0 ≤ 08-22, P1 ≤ 09-05, P2 experiments ≤ 09-15, P2 submit ≤ 2027-01-31, P3 → IGARSS Jan primary. Inventory: done vs remaining (F1–F10) vs deferred. Freeze P4/C1–C3/parked until P1 submitted and P2 experiments done. OPEN 6 largely mitigated by `build_aerialfusecv.py`; remaining P0 work is deposit-scoped script + packaging + licensing MVP. Need statement locked. Minor bump: countable sequence unchanged. |
