# Deposit script — performance fix, prepared but NOT yet applied

**Status: ready to apply once the current verification run finishes.**
Not applied now because `rebuild_aerialfusecv.py` is the file that run is
executing.

## The defect

`rebuild_image()` does two full-image operations **per pair**:

```python
colour   = np.array(rec["instance_rgb"], np.uint8)
instance = np.all(ins == colour, axis=-1)   # scans the whole ~20 MP mask
poly     = np.zeros(shape, np.uint8)        # allocates a full-image buffer
cv2.fillPoly(poly, [...], 1)                # rasterises into it
clipped  = instance & (poly > 0)            # another full-image pass
```

Cost is therefore **pairs × image pixels**. Measured consequence: on `P1387`
(1,718 pairs, the second-densest training image) the script produced no output
for over eleven minutes. `P1388` follows immediately at 1,522 pairs.

A typical image has tens of pairs and finishes in under a second, which is why
this never showed up until a full run reached the tail of the density
distribution.

**Why this is a correctness issue and not an optimisation.** This script is
what a stranger downloads from Zenodo and runs to reproduce the dataset. Facing
eleven minutes of silence on one image, they will conclude it has hung and kill
it. A reproduction script that appears to freeze does not support a
reproducibility claim.

## The fix

Three changes, all local to `rebuild_image()`.

**1 — Pack the instance mask once per image.** Reduce the (H, W, 3) comparison
to a single (H, W) integer array, so selecting an instance is one comparison
against a scalar rather than three-channel equality across the image:

```python
ik = (ins[:, :, 0].astype(np.int32) << 16) | \
     (ins[:, :, 1].astype(np.int32) << 8)  |  ins[:, :, 2].astype(np.int32)
# per pair:
key      = (int(c[0]) << 16) | (int(c[1]) << 8) | int(c[2])
instance = ik == key
```

**2 — Work inside the box's bounding rectangle.** The clip cannot extend beyond
the oriented box, so the polygon never needs a full-image buffer:

```python
pts = np.round(np.array(corners).reshape(4, 2)).astype(np.int32)
x1, y1 = np.clip(pts.min(0) - 1, 0, [w - 1, h - 1])
x2, y2 = np.clip(pts.max(0) + 2, 0, [w, h])
sub  = np.zeros((y2 - y1, x2 - x1), np.uint8)
cv2.fillPoly(sub, [pts - [x1, y1]], 1)
clipped_sub = (ik[y1:y2, x1:x2] == key) & (sub > 0)
```

Writes then target the same sub-window. The `instance.any()` fallback for an
empty clip still needs the full-image selection, but only on that rare path.

**3 — Report progress.** Emit a line every N images including the pair count,
so a user watching a dense image can see the script is working. Silence and
wedged must not look identical from outside — LESSONS A3 and D6.

## Expected effect

Per-pair work falls from ~20 M three-channel comparisons plus a full-image
allocation, to one scalar comparison over the box's bounding rectangle —
typically a few thousand pixels. On P1387 that is roughly 34 × 10⁹ element
operations replaced by order 10⁷.

## Verification required before this replaces the current script

1. Rebuild with the patched script into a fresh directory.
2. Confirm **byte-identical** output against tonight's run — all 7,448
   checksums, not a sample. A performance fix that changes one pixel is not a
   performance fix.
3. Record the timing on `P1387` and `P1388` specifically, since they are the
   worst cases in the dataset.

Only then does the patched script go into the deposit.
