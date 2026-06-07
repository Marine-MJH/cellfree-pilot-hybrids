#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

python experiments/presentation_high_k_6method_figures.py \
  --outdir figures/presentation_high_k_6method \
  --setups 200 \
  --workers 8 \
  --L 200 \
  --N 8 \
  --K-list 50 100 150 200 250 300 \
  --ecdf-K 300 \
  --tau-c 150 \
  --baseline-tau-p 15 \
  --fc-ghz 3 \
  --edge-threshold 10 \
  --mussbah-edge-threshold 0 \
  --power-control full \
  --power-model ref12-rf \
  --fronthaul-mode active_users
