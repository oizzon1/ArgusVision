#!/usr/bin/env python3
"""Bibliography plumbing between Zotero, the shared master, and each paper.

Papers are deliberately isolated — each keeps its own `references.bib` holding
only what it cites, because a submission bundle must not carry entries the
manuscript never uses. `papers/shared/master.bib` is the union everything is
drawn from.

That only works if the copies cannot silently drift from the master, which is
exactly what happened: master carried 5 entries while P1 carried 7, and nothing
reported it. `audit` exists to make that visible.

    # 1. bring a Zotero export into the master (idempotent, never overwrites
    #    an existing entry unless --force)
    python papers/shared/bib_tool.py merge ~/Downloads/thesis-library.bib

    # 2. see what a paper cites that the master does not have, and vice versa
    python papers/shared/bib_tool.py audit papers/p1_aerialfusecv_descriptor

    # 3. pull a subset out of the master into a paper
    python papers/shared/bib_tool.py extract --keys xia2018dota,zamir2019isaid \
        --out papers/p2_flagship_training_free/references.bib

    # 4. list what is available
    python papers/shared/bib_tool.py list --grep aerial

No third-party dependencies: a submission-critical tool should not stop working
because an environment moved.
"""

import argparse
import re
import sys
from pathlib import Path

MASTER = Path("papers/shared/master.bib")

ENTRY_RE = re.compile(r"@(\w+)\s*\{\s*([^,\s]+)\s*,", re.I)


def parse_bib(text):
    """Return {key: (entry_type, raw_text)} by brace matching.

    Regex alone cannot split BibTeX safely — a `note` field containing braces
    ends the entry early — so the body is walked with a depth counter.
    """
    entries, pos = {}, 0
    for m in ENTRY_RE.finditer(text):
        etype, key = m.group(1).lower(), m.group(2)
        i = text.index("{", m.start())
        depth, j = 0, i
        while j < len(text):
            if text[j] == "{":
                depth += 1
            elif text[j] == "}":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        entries[key] = (etype, text[m.start():j + 1])
        pos = j
    return entries


def load(path):
    if not Path(path).exists():
        return {}
    return parse_bib(Path(path).read_text(encoding="utf-8", errors="replace"))


def header(path):
    """Preserve the leading comment block of a .bib file."""
    if not Path(path).exists():
        return ""
    out = []
    for line in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("%") or not line.strip():
            out.append(line)
        else:
            break
    return "\n".join(out).rstrip() + "\n\n"


def normalise(raw):
    """Collapse whitespace so two formattings of one entry compare equal."""
    return re.sub(r"\s+", " ", raw).strip()


def field(raw, name):
    """Pull one field's value out of an entry by brace matching.

    The value may itself contain braces — Zotero writes titles like
    `{{BoxInst}}: {High}-{Performance}` — so counting depth is required.
    """
    m = re.search(rf"\b{name}\s*=\s*", raw, re.I)
    if not m:
        return None
    i = m.end()
    if i < len(raw) and raw[i] in "{\"":
        close = "}" if raw[i] == "{" else "\""
        depth, j = 0, i
        while j < len(raw):
            if raw[j] == "{":
                depth += 1
            elif raw[j] == "}":
                depth -= 1
                if depth == 0 and close == "}":
                    return raw[i + 1:j]
            elif raw[j] == close == "\"" and j > i:
                return raw[i + 1:j]
            j += 1
        return None
    return raw[i:].split(",")[0].strip()


def doi_of(raw):
    d = field(raw, "doi")
    if not d:
        u = field(raw, "url") or ""
        m = re.search(r"doi\.org/(.+)$", u.strip())
        d = m.group(1) if m else None
    if not d:
        return None
    # arXiv DOIs appear as both 10.48550/arXiv.x and 10.48550/ARXIV.x —
    # the same record, and the case difference is how a duplicate hides.
    return re.sub(r"^https?://(dx\.)?doi\.org/", "", d.strip()).lower()


def title_key(raw):
    t = field(raw, "title")
    if not t:
        return None
    t = re.sub(r"[{}\\]", "", t).lower()
    t = re.sub(r"[^a-z0-9]+", " ", t).strip()
    return t or None


def find_duplicates(entries):
    """Group keys that denote the same work, by DOI then by title."""
    by_doi, by_title = {}, {}
    for key, (_etype, raw) in entries.items():
        d, t = doi_of(raw), title_key(raw)
        if d:
            by_doi.setdefault(d, []).append(key)
        if t:
            by_title.setdefault(t, []).append(key)
    groups, seen = [], set()
    for bucket in (by_doi, by_title):
        for val, keys in bucket.items():
            if len(keys) > 1 and tuple(sorted(keys)) not in seen:
                seen.add(tuple(sorted(keys)))
                groups.append((val, sorted(keys)))
    return groups


def strip_fields(raw, names):
    """Remove whole fields from an entry, brace-safely.

    Zotero exports carry full abstracts — five sixths of the file by size — and
    a submission bibliography has no use for them. The source of truth stays in
    Zotero, so dropping them here loses nothing recoverable.
    """
    for name in names:
        while True:
            m = re.search(rf"\n\s*{name}\s*=\s*", raw, re.I)
            if not m:
                break
            i = m.end()
            if i < len(raw) and raw[i] in "{\"":
                close, depth, j = ("}" if raw[i] == "{" else "\""), 0, i
                while j < len(raw):
                    if close == "}" and raw[j] == "{":
                        depth += 1
                    elif close == "}" and raw[j] == "}":
                        depth -= 1
                        if depth == 0:
                            break
                    elif close == "\"" and raw[j] == "\"" and j > i:
                        break
                    j += 1
                end = j + 1
            else:
                end = raw.find(",", i)
                end = len(raw) - 1 if end == -1 else end
            while end < len(raw) and raw[end] in ", ":
                end += 1
            raw = raw[:m.start()] + raw[end:].rstrip()
            if not raw.endswith("}"):
                raw += "\n}"
    return raw


def cmd_merge(args):
    incoming = load(args.source)
    if not incoming:
        sys.exit(f"no BibTeX entries found in {args.source}")

    skip = {k.strip() for k in (args.skip or "").split(",") if k.strip()}
    if skip:
        unknown = skip - set(incoming)
        if unknown:
            sys.exit("--skip names entries not in the source: " + ", ".join(sorted(unknown)))
        for k in skip:
            del incoming[k]
        print(f"skipped   : {len(skip):>4} entry/entries by --skip")

    if args.strip:
        names = [f.strip() for f in args.strip.split(",") if f.strip()]
        incoming = {k: (t, strip_fields(r, names)) for k, (t, r) in incoming.items()}
        print(f"stripped  :      fields {', '.join(names)}")
    master = load(MASTER)

    # Same work already in the master under a DIFFERENT key. Key-only deduping
    # misses this entirely: Zotero writes `xia_dota_2018` where the master has
    # `xia2018dota`, and a merge would silently create a second DOTA entry.
    master_doi = {doi_of(r): k for k, (_t, r) in master.items() if doi_of(r)}
    master_ttl = {title_key(r): k for k, (_t, r) in master.items() if title_key(r)}

    added, identical, conflict, cross = [], [], [], []

    for key, (etype, raw) in sorted(incoming.items()):
        if key not in master:
            hit = master_doi.get(doi_of(raw)) or master_ttl.get(title_key(raw))
            if hit:
                cross.append((key, hit))
                if not args.allow_dupes:
                    continue
            added.append(key)
            master[key] = (etype, raw)
        elif normalise(master[key][1]) == normalise(raw):
            identical.append(key)
        else:
            conflict.append(key)
            if args.force:
                master[key] = (etype, raw)

    print(f"incoming : {len(incoming):>4} entries from {args.source}")
    print(f"new      : {len(added):>4}")
    print(f"identical: {len(identical):>4}")
    print(f"conflict : {len(conflict):>4}"
          + ("  (overwritten, --force)" if conflict and args.force else
             "  (kept master's version; re-run with --force to take theirs)"
             if conflict else ""))
    for k in conflict:
        print(f"    ! {k}")

    if cross:
        print(f"\nSAME WORK, DIFFERENT KEY ({len(cross)}) — "
              + ("added anyway, --allow-dupes" if args.allow_dupes
                 else "SKIPPED, master keeps its own key"))
        for new, old in cross:
            print(f"    {new:38} == {old}")

    dupes = find_duplicates(incoming)
    if dupes:
        print(f"\nDUPLICATES WITHIN {args.source} ({len(dupes)} group(s)) — "
              "dedupe these in Zotero:")
        for val, keys in dupes:
            print(f"    {val[:64]}")
            for k in keys:
                print(f"        {k}")

    if args.dry_run:
        print("\ndry run — nothing written")
        return 0

    body = "\n\n".join(master[k][1] for k in sorted(master))
    MASTER.write_text(header(MASTER) + body + "\n", encoding="utf-8")
    print(f"\nmaster now holds {len(master)} entries -> {MASTER}")
    return 0


def cmd_audit(args):
    paper = Path(args.paper)
    refs = paper / "references.bib"
    if not refs.exists():
        sys.exit(f"no references.bib in {paper}")
    master, local = load(MASTER), load(refs)

    missing = sorted(set(local) - set(master))
    drifted = sorted(k for k in set(local) & set(master)
                     if normalise(local[k][1]) != normalise(master[k][1]))

    print(f"paper  : {refs}  ({len(local)} entries)")
    print(f"master : {MASTER}  ({len(master)} entries)")
    print()
    if missing:
        print(f"NOT IN MASTER ({len(missing)}) — the master is not the union:")
        for k in missing:
            print(f"    {k}")
    if drifted:
        print(f"\nDIFFERENT CONTENT ({len(drifted)}) — same key, two versions:")
        for k in drifted:
            print(f"    {k}")
    if not missing and not drifted:
        print("OK — every entry the paper cites is in the master and matches.")
        return 0
    print("\nFix with:  bib_tool.py merge " + str(refs) +
          ("  --force" if drifted else ""))
    return 1


def cmd_extract(args):
    master = load(MASTER)
    keys = [k.strip() for k in args.keys.split(",") if k.strip()]
    missing = [k for k in keys if k not in master]
    if missing:
        sys.exit("not in master: " + ", ".join(missing))
    out = Path(args.out)
    body = "\n\n".join(master[k][1] for k in keys)
    out.write_text(
        f"% Extracted from {MASTER} — {len(keys)} entries.\n"
        f"% Papers are isolated: this file holds only what this manuscript cites.\n"
        f"% Re-check with: python papers/shared/bib_tool.py audit {out.parent}\n\n"
        + body + "\n", encoding="utf-8")
    print(f"wrote {len(keys)} entries -> {out}")
    return 0


def cmd_list(args):
    master = load(MASTER)
    for key in sorted(master):
        etype, raw = master[key]
        t = re.search(r"title\s*=\s*[{\"](.+?)[}\"]\s*,", raw, re.S | re.I)
        title = re.sub(r"\s+", " ", t.group(1)).strip("{} ") if t else ""
        line = f"  {key:32} {etype:14} {title[:70]}"
        if not args.grep or args.grep.lower() in line.lower():
            print(line)
    print(f"\n{len(master)} entries in {MASTER}")
    return 0


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    m = sub.add_parser("merge", help="merge a .bib (e.g. a Zotero export) into the master")
    m.add_argument("source")
    m.add_argument("--force", action="store_true",
                   help="on a key collision, take the incoming version")
    m.add_argument("--allow-dupes", action="store_true",
                   help="add entries whose DOI or title already exists in the "
                        "master under another key (default: skip and report)")
    m.add_argument("--skip", help="comma-separated keys in the source to ignore "
                                  "(use for duplicates you have decided against)")
    m.add_argument("--strip", help="comma-separated fields to drop from incoming "
                                   "entries, e.g. abstract,keywords,file")
    m.add_argument("--dry-run", action="store_true")
    m.set_defaults(func=cmd_merge)

    a = sub.add_parser("audit", help="check a paper's references.bib against the master")
    a.add_argument("paper")
    a.set_defaults(func=cmd_audit)

    e = sub.add_parser("extract", help="pull selected keys out of the master")
    e.add_argument("--keys", required=True, help="comma-separated citation keys")
    e.add_argument("--out", required=True)
    e.set_defaults(func=cmd_extract)

    l = sub.add_parser("list", help="list what the master holds")
    l.add_argument("--grep", help="filter on key, type or title")
    l.set_defaults(func=cmd_list)

    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
