# Competitive Landscape Notes — August 2026

**Created by ATHENA:** 2026-08-04  
**Trigger:** user requested thorough investigation of ArgusVision material and a deep
competitive search for publication ideas that can stand competition.  
**Roadmap impact:** Publication Roadmap → **v2.3** (positioning upgrade; P0–P4
countable sequence unchanged).

## Short Verdict

The 2024–2026 remote-sensing literature is dense on foundation-model *methods*
and still thin on *annotation contracts* and *cascade failure science*.
ArgusVision should not compete as another SAM wrapper. It should publish the
paired detect→segment contract, the measured protocol divergence between DOTA
and iSAID, and the evaluator that separates detector error from mask quality.

## What ArgusVision Uniquely Owns

1. **Instance-level DOTA↔iSAID pairing with discard accounting**  
   iSAID uses DOTA-v1.0 imagery but was annotated from scratch (~250% more
   instances than original DOTA boxes). No public release was found that links
   oriented boxes to masks object-by-object with pairing metadata and discard
   reasons.

2. **Protocol divergence, measured exhaustively**  
   Evidence in `results/AerialFuseCV_Testing/` (see `FINDINGS.md`): over all
   matched pairs, disagreement decomposes into ~90% extent / ~10% foreign
   contamination; harbor and baseball-diamond are convention differences, not
   noise. Reconciled masks = matched iSAID instance ∩ oriented DOTA box
   (`documentation/DECISION_reconciled_masks.md`).

3. **Cascade evaluator under a pairs-only contract**  
   Scope: detector → DOTA; segmentation → iSAID; unified detect→segment →
   AerialFuseCV (`documentation/DECISION_unpaired_annotations.md`). Enables a
   paper that remains valid even if supervised baselines win on absolute score.

## Competitor Map

| Work | Core claim | Overlap with ArgusVision | Response |
|---|---|---|---|
| **RSPrompter** (TGRS 2024; Chen et al.) | Learn prompts for SAM; automated RS instance segmentation | High if we claim “first automated SAM” | Cite; differentiate as training-free cascade + paired DOTA/iSAID contract |
| **SAM-RSIS** (TGRS 2024) | Progressively adapt SAM with box prompting | Medium — fine-tuned, not training-free | Related work; P4 optional comparison family |
| **OBSeg** (arXiv 2401.08174) | OBB prompt encoder for SAM-based RS instance segmentation | **Kills “first OBB prompts” novelty** | Reframe parked OBB idea as geometry/evaluation under reconciled GT; prefer P4 block |
| **SOPSeg / ReSOS** (arXiv 2509.03002; CVPR 2026F variant) | Small-object SAM adaptation; ~750k masks generated from SODA-A OBBs | Closest dataset neighbour | Different claim: *synthetic* masks vs dual-human protocol reconciliation; AerialFuseCV can score auto-maskers |
| **InstructSAM** (arXiv 2505.15818) | Training-free LVLM+SAM2+CLIP instruction-oriented recognition | Related training-free framing | Different task; cite carefully in P2 related work |
| **AerOSeg** (arXiv 2504.09203) | Open-vocab semantic segmentation; SAM as feature guidance | Low for P2 instance cascade | Local review already exists; P4 context baseline only if broadened |
| **SegEarth-OV / ConInfer / DGL-RSIS** | Training-free open-vocab RS semantic segmentation | Low for instance detect→segment | Different output contract |
| **YOLOSAM / SILCON YOLO+SAM** | Engineering detect→segment pipelines | Low if P2 is analysis-first | Do not claim pipeline recipe novelty |
| **iSAID original + Mask R-CNN/PANet** | Supervised instance segmentation baselines | Defines P2 comparison floor | Already logged in `iSAID_baselines_positioning_NOTES.md` |

## Claim Landmines (never write these)

- “First SAM in remote sensing”
- “First iSAID segmentation”
- “First OBB prompts for SAM”
- “YOLO+SAM is novel”
- “iSAID lacks segmentation baselines”
- Any experimental number not in `results/`
- Citing the MSc thesis as a source of results

## Preferred Claim Language

> We study whether aerial object detectors and their geometry can serve as a
> practical interface to promptable foundation segmentation, under a paired
> detection–segmentation benchmark that makes detector error and mask quality
> jointly measurable, and we quantify the training-free vs supervised tradeoff
> when dense masks are scarce.

## Publication Implications (mirrored in roadmap v2.3)

| Item | Decision |
|---|---|
| P1 | Upgrade argument to protocol divergence + reconciled pairs; DiB stays primary for speed |
| P2 | Cascade-reliability paper; experiment block unchanged; related-work posture mandatory |
| Parked OBB | Reframe; do not claim prompt-encoder novelty; prefer absorb into P4 |
| P4 | Narrow brand to instance detect→segment pipelines; dual-GT / cascade metrics |
| C1 candidate | Annotation Protocol Divergence letter — highest originality-per-effort |
| C2 candidate | Auto-mask quality against AerialFuseCV — follow-on after P0/P2 |
| C3 candidate | Optional systems split only if P2 writing pressure forces it |
| Hard rule | No new experimental fronts before P0 DOI |

## Evidence Index (ArgusVision)

| Artefact | Role |
|---|---|
| `results/AerialFuseCV_Testing/FINDINGS.md` | Consolidated rebuild + discrepancy findings |
| `documentation/DECISION_reconciled_masks.md` | Released-mask definition |
| `documentation/DECISION_unpaired_annotations.md` | Pairs-only scope |
| `Context/iSAID_baselines_positioning_NOTES.md` | Why iSAID baselines do not kill the program |
| `Context/2504.09203v1_AerOSeg_REVIEW.md` | AerOSeg local review |

## Decision

Roadmap revised to **v2.3** (minor bump): countable P0–P4 sequence stands;
positioning, P1/P2 framing, parked OBB reframe, and candidate papers recorded.
No paper added to the scheduled countable sequence without a further Revision
Protocol event (major bump).
