# Deposit verification — AerialFuseCV

Independent check that a rebuild from the deposit reproduces the published
dataset byte for byte.

`rebuild_aerialfusecv.py --verify` performs this check inline and prints the
result to stdout. On 2026-08-04 that stdout was redirected into a session
scratch directory that did not survive an accidental session close, so the run
completed and its verification result was lost. `dataset/verify_deposit_rebuild.py`
re-runs the check against an existing tree and writes the outcome here, so the
reproducibility claim in the P1 data article has a durable `results/` source.

| Field | Value |
|---|---|
| Tree verified | `dataset/_deposit_test` (rebuilt 2026-08-04, `--image-mode copy`) |
| Checksums | `papers/p1_aerialfusecv_descriptor/deposit/checksums.sha256` |
| Files checked | 7,448 (labels_obb, labels_hbb, instance_masks, semantic_masks × 1,862 images) |
| Result | **PASS** — 0 missing, 0 mismatched |
| Verified | 2026-08-05 07:31 UTC |

Reproduce:

```bash
python dataset/verify_deposit_rebuild.py \
    --tree dataset/_deposit_test \
    --checksums papers/p1_aerialfusecv_descriptor/deposit/checksums.sha256 \
    --out results/experimental/AerialFuseCV_Testing/deposit_verification
```

Note: the 7,448 checksums cover annotations and masks only. Source imagery is
copied unchanged from DOTA and is not checksummed, since it is not part of what
the deposit produces.
