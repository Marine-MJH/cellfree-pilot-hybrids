#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

python experiments/presentation_k_sweep_common.py \
  --k-list 25 30 35 40 45 \
  --setups 50 \
  --channel-samples 10 \
  --num-aps 100 \
  --num-antennas 8 \
  --tau-c 100 \
  --tau-p 10 \
  --top-n 8 \
  --weight-threshold 10 \
  --out-prefix presentation_load_crossover_6method_50x10
