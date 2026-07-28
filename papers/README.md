# 📄 Papers — WTF-P Workspaces

One directory per paper from Publication Roadmap v2.0. Each is an isolated WTF-P project: its own `PROJECT.md`, `outline.md`, argument map, section plans, and `references.bib`. Isolation is deliberate — the papers make different arguments and must not be coherence-checked against each other.

| Dir | Paper | Venue (primary) | Status |
|---|---|---|---|
| `p1_aerialfusecv_descriptor/` | AerialFuseCV data descriptor | ISPRS Open Journal of P&RS | Not started — blocked by P0 (Zenodo DOI) |
| `p2_flagship_training_free/` | Training-Free Detection→Segmentation (flagship) | ISPRS Journal of P&RS | Not started — experiments first |
| `p3_conference/` | Condensed pipeline findings | EarthVision @ CVPR 2027 or IGARSS 2027 | Not started — condenses P2 |
| `p4_argusvision_benchmark/` | ArgusVision full benchmark | IEEE TGRS | Not started — PhD Year 1–2 |
| `shared/` | `master.bib` — union bibliography from the thesis; copy entries into per-paper `references.bib` | — | Seed from thesis |

## Workflow per paper

```
cd papers/<paper-dir>
/wtfp:new-paper        # guided interview → PROJECT.md
/wtfp:create-outline   # outline, argument map, word budgets
/wtfp:plan-section     # per section
/wtfp:write-section    # per section (commits per task)
/wtfp:review-section   # citation + coherence + rubric
/wtfp:audit-milestone  # pre-submission
/wtfp:export-latex     # → exports/ for submission
```

## Rules
- Every number in prose must trace to `results/**/…_metrics.json` or the thesis (see `ATHENA_STATE.md`)
- No paper cites AerialFuseCV before the Zenodo DOI exists
- P2 and P4 are distinct stories — no P4 results in P2 sections
