#!/usr/bin/env bash
# Regenerate every P1 artefact from a freshly built AerialFuseCV. INTERNAL TOOL.
#
# Runs the pipeline SERIALLY. Disk is the binding constraint on this machine —
# running two of these concurrently once stalled a build for five minutes
# (LESSONS A1) — so nothing here overlaps, by design.
#
# The log lives inside the repo, not in a session scratch directory, so an
# unexpected session close cannot destroy the record of what ran (LESSONS E1).
#
#   bash dataset/regenerate_p1_artefacts.sh
#
# Steps 2-5 wait for any measurement already in flight to finish first.

set -u
cd /mnt/d/Work/AV || exit 1

REPO_WIN='D:\Work\AV'
ISAID_WIN='D:\AI_Datasets\iSAID'
REGEN=results/experimental/AerialFuseCV_Testing/p1_regen
DISC=results/experimental/AerialFuseCV_Testing/annotation_discrepancy
LOG="$REGEN/pipeline.log"
STATUS="$REGEN/status.txt"

mkdir -p "$REGEN"

say() { echo "[$(date +%H:%M:%S)] $*" | tee -a "$LOG"; }
setstatus() { echo "$*" > "$STATUS"; }

winpy() {  # winpy "<label>" "<python args as one string>"
  local label="$1"; shift
  say "START  $label"
  setstatus "RUNNING $label"
  /mnt/c/Windows/system32/cmd.exe /c "cd /d $REPO_WIN && python $*" >> "$LOG" 2>&1
  local rc=$?
  if [ $rc -ne 0 ]; then
    say "FAILED $label (exit $rc)"
    setstatus "FAILED $label (exit $rc)"
    exit $rc
  fi
  say "DONE   $label"
}

say "=== P1 artefact regeneration ==="
say "dataset: dataset/AerialFuseCV  (rebuilt 2026-08-05, checksums PASS)"

# --- step 1: wait for the discrepancy measurement already running -----------
setstatus "WAITING for discrepancy measurement"
say "waiting for the running discrepancy measurement to finish ..."
while :; do
  alive=$(/mnt/c/Windows/system32/cmd.exe /c "tasklist" 2>/dev/null | grep -ci "python.exe")
  [ "$alive" -eq 0 ] && break
  sleep 60
done
if [ ! -f "$DISC/discrepancy_summary.json" ]; then
  say "FAILED step 1 — no discrepancy_summary.json; measurement did not complete"
  setstatus "FAILED step 1 (no summary written)"
  exit 1
fi
say "DONE   step 1/5  discrepancy measurement"

# --- steps 2-5 -------------------------------------------------------------
winpy "step 2/5  EDA + figures F2/F5/F6/F7" \
      "dataset\\analyze_aerialfusecv.py"

winpy "step 3/5  figures F1 + F4" \
      "dataset\\make_p1_figures.py --isaid $ISAID_WIN"

winpy "step 4/5  figure F3 construction pipeline" \
      "dataset\\make_pipeline_figure.py"

winpy "step 5/5  consolidated EDA report" \
      "dataset\\make_eda_report.py --dataset dataset\\AerialFuseCV --discrepancy $DISC\\per_pair.jsonl"

say "=== ALL STEPS COMPLETE ==="
setstatus "COMPLETE"
