#!/usr/bin/env python3
"""Export DRAFT_P1.md to a reviewable .docx with figures placed inline.

For supervisor review. This is NOT the submission file: Data in Brief mandates
its own partially locked template, and the content must be transferred into that
`.docx` at submission time. This export exists so the draft can be read and
commented on as a document rather than as markdown.

    python papers/p1_aerialfusecv_descriptor/export_to_docx.py

What it does beyond a plain pandoc run:

- Moves each figure from the trailing "Figures" list to the point in the text
  where it is first discussed, and embeds the image. A reviewer should not have
  to hold nine tables and five figure captions in mind and reunite them at the
  end.
- Strips the repo-relative artefact paths from captions. They are provenance for
  us and noise for a reader.
- Leaves every `[[PLACEHOLDER: ...]]` visibly intact, and lists them at the top,
  so nothing unresolved can pass unnoticed.
"""

import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DRAFT = HERE / "DRAFT_P1.md"
FIGDIR = Path("results/experimental/AerialFuseCV_Testing/eda/figures")

# where each figure is first discussed; the figure is moved to just before it
ANCHORS = {
    1: "### Image properties",
    2: "### Category distribution",
    3: "## Experimental Design, Materials and Methods",
    4: "### Deposit contents",
    5: "**Output and verification.**",
}


def main():
    text = DRAFT.read_text(encoding="utf-8")

    # ---- pull the figure list apart ------------------------------------
    m = re.search(r"### Figures\n(.*?)\n---\n", text, re.S)
    if not m:
        sys.exit("could not find the Figures section")
    figs = {}
    for block in re.split(r"\n(?=- \*\*Figure )", m.group(1).strip()):
        n = re.match(r"- \*\*Figure (\d+)\.\*\*", block)
        if not n:
            continue
        num = int(n.group(1))
        path = re.search(r"`(results/[^`]+\.png)`", block)
        caption = re.sub(r"`results/[^`]+`", "", block)
        caption = re.sub(r"^- \*\*Figure \d+\.\*\* ", "", caption).strip()
        caption = re.sub(r"\s+", " ", caption)
        figs[num] = (path.group(1) if path else None, caption)
    text = text[:m.start()] + text[m.end():]

    # ---- place each figure at its anchor -------------------------------
    placed, missing = 0, []
    for num in sorted(figs):
        path, caption = figs[num]
        if not path or not Path(path).exists():
            missing.append(num)
            continue
        block = (f"\n![**Figure {num}.** {caption}]"
                 f"({Path(path).resolve().as_posix()})\n\n")
        anchor = ANCHORS.get(num)
        i = text.find(anchor) if anchor else -1
        if i < 0:
            text += block
        else:
            text = text[:i] + block + text[i:]
        placed += 1

    # ---- header for the reviewer ---------------------------------------
    ph = re.findall(r"\[\[PLACEHOLDER:([^\]]+)\]\]", text, re.S)
    note = ["# AerialFuseCV — data article draft\n",
            "*Draft for supervisor review. Not the submission file: Data in Brief "
            "mandates its own template, into which this content is transferred at "
            "submission.*\n",
            f"\n**{len(ph)} items still unresolved**, marked `[[PLACEHOLDER: …]]` "
            "in place. They are decisions or values that cannot be settled here:\n"]
    for p in ph:
        note.append(f"- {re.sub(r'\\s+', ' ', p).strip()[:150]}\n")
    note.append("\n---\n\n")
    text = "".join(note) + text

    out_md = HERE / "exports" / "AerialFuseCV_DiB_draft.md"
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(text, encoding="utf-8")

    out_docx = HERE / "exports" / "AerialFuseCV_DiB_draft.docx"
    cmd = ["pandoc", str(out_md), "-o", str(out_docx),
           "--from", "markdown+pipe_tables", "--toc", "--toc-depth=2",
           "--resource-path", str(Path.cwd())]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr, file=sys.stderr)
        sys.exit("pandoc failed")

    print(f"  figures placed inline : {placed}" +
          (f"  (missing: {missing})" if missing else ""))
    print(f"  placeholders flagged  : {len(ph)}")
    print(f"  markdown -> {out_md}")
    print(f"  docx     -> {out_docx}  ({out_docx.stat().st_size/1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
