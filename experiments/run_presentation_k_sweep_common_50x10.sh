#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

mkdir -p logs
LOG="logs/presentation_k_sweep_common_50x10.log"
DONE="logs/presentation_k_sweep_common_50x10.done"
FAILED="logs/presentation_k_sweep_common_50x10.failed"

rm -f "$DONE" "$FAILED"

{
  echo "[start] $(date -Is)"
  python experiments/presentation_k_sweep_common.py \
    --k-list 30 40 50 60 70 \
    --setups 50 \
    --channel-samples 10 \
    --tau-p 15 \
    --tau-c 150 \
    --num-aps 200 \
    --num-antennas 8 \
    --carrier-frequency-mhz 3000 \
    --beam-detection-snr-db 20 \
    --weight-threshold 10 \
    --top-n 8 \
    --out-prefix presentation_k_sweep_common_50x10 \
    --progress-every 5
  echo "[done] $(date -Is)"
  touch "$DONE"
} >"$LOG" 2>&1 || {
  status=$?
  echo "[failed] $(date -Is) status=$status" >>"$LOG"
  touch "$FAILED"
  exit "$status"
}
