#!/usr/bin/env bash
# Operator chain (2026-10-07, owner-approved schedule): 0233 development → 0234 (screening, dispatch, NOT_RUN fill, easy)
# → 0233 easy/screening/confirmation. 0234 starts only after root writes SMOKE_OK (SMOKE_FAIL skips 0234).
set -uo pipefail
L3=$HOME/.local/share/nx01/0233-live; L4=$HOME/.local/share/nx01/0234-live
H4=$HOME/.local/share/nx01/0234-apparatus/autoresearch/experiments/0234
cd "$L3" && ./drive2.sh cells.tsv:d >> measure.log 2>&1 || { echo "chain: 0233 development stopped"; exit 1; }
until [ -e "$L4/SMOKE_OK" ] || [ -e "$L4/SMOKE_FAIL" ]; do sleep 60; done
if [ -e "$L4/SMOKE_OK" ]; then
  cd "$L4" && ./drive.sh screening.tsv >> measure.log 2>&1 || { echo "chain: 0234 screening stopped"; exit 1; }
  (cd "$H4" && python3 generate_cells.py --dispatch-order "$L4/out" > dispatch.tsv) || { echo "chain: 0234 gating stopped (adjudication?)"; exit 1; }
  ./drive.sh dispatch.tsv cells.tsv:d cells.tsv:c cells.tsv:e >> measure.log 2>&1 || { echo "chain: 0234 drive stopped"; exit 1; }
  echo "$(date -u +%FT%TZ) chain: 0234 finished" >> measure.log
fi
cd "$L3" && ./drive2.sh cells.tsv:e screening.tsv cells.tsv:c >> measure.log 2>&1 || { echo "chain: 0233 rest stopped"; exit 1; }
echo "chain: all finished"
