#!/usr/bin/env bash
# Regenerate every P1 artefact from a built AerialFuseCV. INTERNAL TOOL.
#
# Runs SERIALLY. Disk is the binding constraint on this machine — running two
# jobs concurrently once stalled a build for five minutes (LESSONS A1) — so
# nothing here overlaps, by design.
#
# The log lives inside the repo, not a session scratch directory, so an
# unexpected session close cannot destroy the record of what ran (LESSONS E1).
#
#   bash dataset/regenerate_p1_artefacts.sh
#
# The discrepancy measurement (~93 min) is SKIPPED when its summary already
# exists: it reads instance_rgb, the labels and the original iSAID masks, none
# of which the rebuild changes, so a completed measurement stays valid.
# Delete discrepancy_summary.json to force it.

set -u
cd /mnt/d/Work/AV || exit 1

REPO_WIN='D:\Work\AV'
DOTA_WIN='D:\AI_Datasets\DOTA_v1'
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

# --- step 1: rebuild, to regenerate pairs.jsonl with the correct schema -----
# The previous run wrote `mask_px` where every consumer filters on
# `instance_area_px`, so the EDA had nothing to plot. Masks and labels are
# unchanged by this, and --verify re-proves that against the 7,448 checksums.
winpy "step 1/5  rebuild (pairs.jsonl schema fix) + checksum verify" \
      "papers\\p1_aerialfusecv_descriptor\\deposit\\rebuild_aerialfusecv.py" \
      "--dota $DOTA_WIN --isaid $ISAID_WIN --out dataset\\AerialFuseCV --verify --yes"

# --- step 2: discrepancy measurement, skipped when already valid ------------
if [ -f "$DISC/discrepancy_summary.json" ]; then
  say "SKIP   step 2/5  discrepancy measurement — summary already present"
else
  winpy "step 2/5  discrepancy measurement (~93 min)" \
        "dataset\\measure_discrepancy.py --dataset dataset\\AerialFuseCV --isaid $ISAID_WIN"
fi

# --- steps 3-5 -------------------------------------------------------------
winpy "step 3/5  EDA + figures F2/F5/F6/F7" \
      "dataset\\analyze_aerialfusecv.py"

winpy "step 4/5  figures F1 + F4a/F4b/F4c divergence set" \
      "dataset\\make_p1_figures.py --isaid $ISAID_WIN"

winpy "step 5/5  figure F3 + consolidated EDA report" \
      "dataset\\make_pipeline_figure.py"
winpy "step 5/5  consolidated EDA report" \
      "dataset\\make_eda_report.py --dataset dataset\\AerialFuseCV --discrepancy $DISC\\per_pair.jsonl"

say "=== ALL STEPS COMPLETE ==="
setstatus "COMPLETE"
