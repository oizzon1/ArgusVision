# Licensing Emails — Ready to Send (F3)

**Drafted by ATHENA 2026-08-04.** Fill the `[bracketed]` fields, send from your
institutional address. Answers land back in this folder as notes.
All three can go today; none blocks the others.

---

## 1 → DOTA / iSAID authors (same group, Wuhan University / CAPTAIN-WHU)

**To:** [DOTA corresponding author email — check captain-whu.github.io/DOTA]
**Subject:** Permission request — releasing a derived instance-level correspondence between DOTA v1.0 and iSAID

Dear Professor Xia and colleagues,

I am a PhD candidate in Photogrammetry at the National Technical University of
Athens (supervisor: Prof. Charalampos Ioannidis). Building on your DOTA v1.0
and iSAID releases, I have computed an instance-level correspondence between
DOTA oriented boxes and iSAID instance masks over the shared train/val imagery
(125,722 verified pairs), for evaluating unified detection-to-segmentation
systems.

I would like to release this on Zenodo, respecting your academic-use terms, as:
(a) pairing metadata that **references** your annotations (image id, box index,
instance identifier) without reproducing coordinates or masks; (b) our own
statistics and matching scores; and (c) a script that rebuilds the paired
dataset locally from the official DOTA and iSAID downloads, so every user
obtains the data from you.

May I ask: (1) is this referencing release acceptable to you? (2) Would you
additionally permit redistribution of the derived annotation files themselves
(box coordinates and clipped masks) under a non-commercial licence, which would
simplify reuse? Both DOTA and iSAID will of course be cited as required.

Thank you for these datasets — they are the foundation of this work.

Kind regards,
Panagiotis Fragkos, PhD candidate, NTUA
[institutional email]

---

## 2 → Data in Brief editorial office (pre-submission enquiry)

**To:** dib-me@elsevier.com
**Subject:** Pre-submission enquiry — data article for a derived dataset whose sources restrict redistribution

Dear Editors,

I am preparing a Data in Brief submission describing AerialFuseCV, an
instance-level paired detection–segmentation dataset derived from two public
academic benchmarks (DOTA v1.0 and iSAID). Both sources permit academic use
but prohibit commercial use, and do not state a redistribution policy for
their annotations.

Our planned Zenodo deposit therefore contains: the pairing correspondence we
computed (referencing source annotations by index/identifier rather than
reproducing them), full per-class statistics and discard accounting, and a
verified construction script that rebuilds the complete dataset from the
official source downloads. The sources themselves are freely obtainable for
academic use.

Before investing in the template, may I confirm: (1) does a
correspondence-plus-script deposit of this kind satisfy the journal's data
availability requirement? (2) Is a data article describing such a derived
dataset within scope, given the source licence restrictions?

I would be happy to provide the deposit structure in detail.

Kind regards,
Panagiotis Fragkos, PhD candidate
National Technical University of Athens
[institutional email]

---

## 3 → NTUA research-data / legal support

**To:** [NTUA research support / library research-data service — confirm address]
**Subject:** Licensing guidance — releasing derived research data based on academic-only sources

Dear colleagues,

For my PhD (Photogrammetry, supervisor Prof. Ch. Ioannidis) I have produced a
derived dataset: a computed correspondence between the annotations of two
public academic benchmarks (DOTA v1.0 and iSAID), both released for academic
use only with commercial use prohibited.

I plan to deposit on Zenodo only our own contribution — the correspondence,
statistics, and construction script — with users rebuilding the full dataset
from the official sources. My questions: (1) does NTUA have guidance or
requirements on licensing such derived data (we are considering CC-BY-NC 4.0
to match the upstream restriction)? (2) Are there institutional requirements
for datasets deposited by NTUA PhD candidates (affiliation statements,
approval, repository preferences)?

A short answer or a pointer to the right office would help greatly; a
publication deadline makes this time-sensitive.

Thank you,
Panagiotis Fragkos, [school], NTUA
[institutional email]

---

**After sending:** note the date sent per email below; log replies as
`licensing_reply_<who>_NOTES.md` in this folder.

- [ ] Sent 1 (authors):
- [ ] Sent 2 (DiB):
- [ ] Sent 3 (NTUA):
