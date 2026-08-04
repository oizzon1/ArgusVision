ATHENA WORKER TASK — P1-WRITE (paste this whole block into the writer model's terminal)

You are a WRITER worker. The orchestrator is the Claude Code session; you do
not decide scope, you execute this packet.

SETUP
  cd /mnt/d/Work/AV && git switch dev && git pull
  git switch -c task/p1-dib-rewrite
READ FIRST
  Athena_Protocols/ATHENA_RISE.md · ATHENA_STATE.md · ACTIVE_TASKS.md
  ArgusVision_Strategic_Planning/PUBLICATION_ROADMAP.md  (v2.4 — P1 section)
  ArgusVision_Strategic_Planning/Context/competitive_landscape_2026-08_NOTES.md
  results/AerialFuseCV_Testing/FINDINGS.md
  results/AerialFuseCV_Testing/eda/DATASET_ANALYSIS.md
  documentation/DECISION_reconciled_masks.md · DECISION_unpaired_annotations.md
  papers/shared/venues/data-in-brief/NOTES.md  (template v19 rules)
  papers/p1_aerialfusecv_descriptor/DRAFT_P1.md  (current draft — being replaced)

CLAIM
  Update ONLY your row in Athena_Protocols/ACTIVE_TASKS.md:
  ID=P1-WRITE, Owner=<your model name>, Status=active, Started=<date>.

LOCKED TO YOU
  papers/p1_aerialfusecv_descriptor/**
DO NOT EDIT
  Anything else. Especially: dataset/, src/, results/, zenodo_release/,
  ATHENA_STATE.md, PUBLICATION_ROADMAP.md, WORK_LOG.md.

OBJECTIVE
  Rewrite DRAFT_P1.md to the v2.3/v2.4 protocol spine: two expert annotation
  protocols on the same imagery disagree about what an object IS; we measure
  that disagreement, define a reconciled contract, and release instance-level
  pairing with discard accounting.

HARD CONSTRAINTS
  1. Every number from results/ artefacts only (dataset_statistics.json,
     FINDINGS.md, discrepancy_summary.json). The MSc thesis is NOT a source.
     Current verified totals: 1,862 images, 125,722 pairs, 98.34% box pairing.
  2. Data in Brief template v19 rules: title contains "dataset"; abstract
     100–500 words; keywords 4–8 not repeating title words; Limitations ≤200
     words; ≤20 numbered references; no interpretation/conclusions anywhere.
  3. Leave [[PLACEHOLDER: …]] for: Zenodo DOI, deposit inventory, data
     accessibility URL, authorship/affiliation/CRediT. These arrive from F1/F2.
  4. Claim landmines (never write): "first SAM in RS", "first OBB prompts",
     "YOLO+SAM is novel", "100% box–mask agreement" (state as evaluation
     validity instead). Use "detector → promptable segmenter", never brand
     names as requirements. Civilian applications lead; scope honesty:
     evaluated on the DOTA∩iSAID vocabulary.
  5. Known residual to state honestly in Limitations: 2.61% of pairs reference
     multi-piece colour instances (fix pending).

ON FINISH
  Set your ACTIVE_TASKS row Status=ready-for-review. Add one line to
  WORK_LOG.md is NOT yours — instead summarise in your final report.
  Commit with prefix [P1-WRITE], push task/p1-dib-rewrite ONLY (never dev),
  report the commit hash and open questions to the user.
