# P1 Limitations — superseded 2026-08-04 (task P1-WRITE)

**Not maintained.** Canonical text: `../DRAFT_P1.md` § Limitations (174 words,
cap 200).

Two limitations claimed in v0.1 no longer hold and were removed rather than
softened: the one-to-one assignment means two boxes can no longer reference the
same mask component, and instance-identity masks ship, so adjacent objects of
one category are separable without the box.

Two were added: the released masks follow DOTA's extent convention wherever the
protocols disagree, and 3,283 pairs (2.61%) reference an iSAID instance whose
colour spans several disconnected components, which extraction does not yet
handle component-wise.

The remaining figures move to build `d4c191a`.
