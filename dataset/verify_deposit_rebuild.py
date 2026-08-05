#!/usr/bin/env python3
"""Verify a rebuilt AerialFuseCV tree against the deposit's published checksums.

Standalone on purpose. `rebuild_aerialfusecv.py --verify` does this inline and
prints the result to stdout; when that stdout is lost, the verification is lost
with it and the whole multi-hour run proves nothing. This script re-runs the
check against an existing tree and writes the outcome to `results/` as an
artefact, so the reproducibility claim has a durable source.

    python dataset/verify_deposit_rebuild.py \
        --tree dataset/_deposit_test \
        --checksums papers/p1_aerialfusecv_descriptor/deposit/checksums.sha256 \
        --out results/experimental/AerialFuseCV_Testing/deposit_verification
"""

import argparse
import hashlib
import json
import platform
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git_sha():
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tree", type=Path, required=True)
    ap.add_argument("--checksums", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    expected = []
    for line in args.checksums.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        want, rel = line.strip().split("  ", 1)
        expected.append((want, rel))
    print(f"checksums to verify: {len(expected):,}", flush=True)

    missing, mismatch, ok = [], [], 0
    by_kind = Counter()
    t0 = time.time()
    for n, (want, rel) in enumerate(expected, 1):
        p = args.tree / rel
        kind = rel.split("/")[1] if "/" in rel else "?"
        if not p.exists():
            missing.append(rel)
            by_kind[f"missing:{kind}"] += 1
        elif sha256(p) != want:
            mismatch.append(rel)
            by_kind[f"mismatch:{kind}"] += 1
        else:
            ok += 1
        if n % 500 == 0:
            rate = n / max(time.time() - t0, 1e-9)
            print(f"  {n:,}/{len(expected):,}  ok={ok:,} "
                  f"missing={len(missing):,} mismatch={len(mismatch):,} "
                  f"({rate:.0f} files/s)", flush=True)

    elapsed = time.time() - t0
    passed = not missing and not mismatch
    report = {
        "verified_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "tree": str(args.tree),
        "checksums_file": str(args.checksums),
        "checksums_file_sha256": sha256(args.checksums),
        "expected_files": len(expected),
        "ok": ok,
        "missing": len(missing),
        "mismatched": len(mismatch),
        "result": "PASS" if passed else "FAIL",
        "elapsed_seconds": round(elapsed, 1),
        "by_kind": dict(by_kind),
        "missing_examples": missing[:50],
        "mismatch_examples": mismatch[:50],
        "git_sha": git_sha(),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
    }

    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "deposit_verification.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8")
    if missing:
        (args.out / "missing_files.txt").write_text(
            "\n".join(missing), encoding="utf-8")
    if mismatch:
        (args.out / "mismatched_files.txt").write_text(
            "\n".join(mismatch), encoding="utf-8")

    print(f"\n{ok:,}/{len(expected):,} verified, {len(missing):,} missing, "
          f"{len(mismatch):,} mismatched in {elapsed:.0f}s")
    print("RESULT: " + report["result"])
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
