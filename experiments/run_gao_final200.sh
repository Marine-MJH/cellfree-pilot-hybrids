#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

mkdir -p logs
rm -f logs/gao_final200.done logs/gao_final200.failed
echo "$$" > logs/gao_final200.runner.pid

echo "[start] $(date -Is)"
echo "[cwd] $ROOT_DIR"
echo "[python] $(command -v python)"

run_step() {
  local name="$1"
  shift
  echo "[step-start] ${name} $(date -Is)"
  echo "[command] $*"
  "$@"
  echo "[step-done] ${name} $(date -Is)"
}

trap 'status=$?; echo "[failed] $(date -Is) exit=${status}"; echo "${status}" > logs/gao_final200.failed; exit "${status}"' ERR

run_step "fig2-final200" \
  python experiments/fig2_cdf.py \
    --realizations 200 \
    --no-progress \
    --power-controls fractional full max-min \
    --gao-serving all-ap \
    --out-suffix _final200

run_step "fig3-final200" \
  python experiments/fig3_vs_pilot_number.py \
    --realizations 200 \
    --no-progress \
    --power-controls fractional full max-min \
    --gao-serving all-ap \
    --out-suffix _final200

run_step "fig4-final200" \
  python experiments/fig4_vs_ue_number.py \
    --realizations 200 \
    --no-progress \
    --power-controls fractional full max-min \
    --gao-serving all-ap \
    --out-suffix _final200

python -m pytest -q tests/

echo "[done] $(date -Is)" | tee logs/gao_final200.done

if command -v notify-send >/dev/null 2>&1; then
  notify-send "Gao final200 finished" "$ROOT_DIR" || true
fi
