# 📦 AerialFuseCV — Zenodo Release Packaging (P0)

Target: Zenodo record with DOI, August 2026. The DOI is the citation anchor for P1–P4 — this blocks everything downstream.

## Licensing constraint
DOTA v1.0 and iSAID images **cannot be redistributed**. The release therefore contains our contribution only (CC-BY 4.0): annotations, pairing metadata, and a construction script that rebuilds AerialFuseCV from the official DOTA and iSAID downloads, with verification checksums. Standard practice in the DOTA ecosystem.

## Release contents (to assemble here)

| Item | Source | Status |
|---|---|---|
| Paired annotations + pairing metadata (train/val) | NTUA PC — AerialFuseCV_Refined | ☐ |
| Construction script (single entry point) | `dataset/merge_aerialfusecv_refined.py` + `dataset/refine_aerialfusecv.py` → consolidate | ☐ |
| Verification checksums (per-file SHA-256 + expected instance counts) | generate | ☐ |
| `LICENSE` (CC-BY 4.0, our contribution) | write | ☐ |
| `README.md` (file structure, formats, per-class stats, usage) | write — stats in `ATHENA_STATE.md` | ☐ |
| Reproducibility log (one clean end-to-end rebuild) | run on NTUA PC | ☐ |

## Effort (roadmap estimate)
~1 week total: packaging 2d · script + checksums 2–3d · README 1d · upload + DOI 1d.
