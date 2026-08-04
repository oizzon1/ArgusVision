# P1 Data Description — superseded 2026-08-04 (task P1-WRITE)

**Not maintained.** Canonical text: `../DRAFT_P1.md` § Data Description.

Every number in the v0.1 text is superseded, and its structural description is
wrong for the shipped dataset. Specifically:

- The layout is five subdirectories per split (`images/`, `labels_obb/`,
  `labels_hbb/`, `instance_masks/`, `semantic_masks/`), not three. Instance
  identity masks now ship, so the claim that adjacent objects of one category
  are inseparable no longer holds.
- The instance-side figures marked ⚠ in v0.1 (330,693 source instances, 37.8%
  retention, 205,591 unpaired) were derived by connected-component counting and
  are wrong. The exhaustive colour audit measures 475,438 instances, a 26.44%
  instance pairing rate and 349,716 unpaired instances.
- Per-category rates, the split table, the excluded-image count and the
  distribution shares all move to build `d4c191a`.
- The protocol-divergence measurement, the matching-quality distribution, the
  threshold-sensitivity table and the discard-reason breakdown are new and have
  no v0.1 counterpart.
