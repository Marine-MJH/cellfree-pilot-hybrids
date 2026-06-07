#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

python experiments/presentation_n_sweep_6method_figures.py \
  --outdir figures/presentation_n_sweep_6method \
  --setups 200 \
  --workers 8 \
  --L 200 \
  --K 50 \
  --N-list 1 2 3 4 5 6 7 8 \
  --ecdf-N 8 \
  --tau-c 150 \
  --baseline-tau-p 15 \
  --fc-ghz 3 \
  --edge-threshold 10 \
  --mussbah-edge-threshold 0 \
  --power-control full \
  --power-model ref12-rf \
  --fronthaul-mode active_users
