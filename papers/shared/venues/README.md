# Venue Guides — Shared Reference

One folder per candidate venue. Each holds:

- `guide-for-authors.*` — the official guide as retrieved (PDF or copied text)
- `NOTES.md` — the distilled ten facts that drive writing decisions: word/page
  limits, mandated section structure, citation style, figure/table rules,
  required statements (data availability, CRediT, ethics), review model,
  submission system, APC. **Must end with source URL + retrieval date.**

| Folder | Venue | Paper |
|---|---|---|
| `isprs-ojprs/` | ISPRS Open Journal of Photogrammetry & RS | P1 primary |
| `data-in-brief/` | Data in Brief (Elsevier) | P1 fallback |
| `isprs-journal/` | ISPRS Journal of Photogrammetry & RS | P2 primary |
| `ieee-tgrs/` | IEEE Transactions on Geoscience & RS | P4 primary, P2 fallback |
| `earthvision-igarss/` | EarthVision @ CVPR / IGARSS | P3 (decide when calls open) |

Rules:
- Publishers revise guides quietly — `/wtfp:audit-milestone` before any
  submission must include re-checking the guide against the publisher's
  current version.
- Distill each `NOTES.md` into a custom WTF-P venue YAML in
  `.claude/write-the-f-paper/venues/` so `/wtfp:create-outline` builds against
  real constraints, not the closest generic template.
