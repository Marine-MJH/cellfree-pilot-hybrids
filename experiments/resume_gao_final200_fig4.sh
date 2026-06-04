#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

mkdir -p logs
rm -f logs/gao_final200_resume.done logs/gao_final200_resume.failed
echo "$$" > logs/gao_final200_resume.runner.pid

echo "[resume-start] $(date -Is)"
echo "[cwd] $ROOT_DIR"
echo "[python] $(command -v python)"

trap 'status=$?; echo "[resume-failed] $(date -Is) exit=${status}"; echo "${status}" > logs/gao_final200_resume.failed; exit "${status}"' ERR

echo "[step-start] fig4-final200 $(date -Is)"
python experiments/fig4_vs_ue_number.py \
  --realizations 200 \
  --no-progress \
  --power-controls fractional full max-min \
  --gao-serving all-ap \
  --out-suffix _final200
echo "[step-done] fig4-final200 $(date -Is)"

python -m pytest -q tests/
python experiments/summarize_gao_final200.py

echo "[resume-done] $(date -Is)" | tee logs/gao_final200_resume.done

if command -v notify-send >/dev/null 2>&1; then
  notify-send "Gao final200 resume finished" "$ROOT_DIR/logs/gao_final200_summary.md" || true
fi
