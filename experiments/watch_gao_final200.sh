#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

mkdir -p logs
echo "$$" > logs/gao_final200.watcher.pid

notify() {
  local title="$1"
  local body="$2"
  if command -v notify-send >/dev/null 2>&1; then
    notify-send "$title" "$body" || true
  fi
}

while true; do
  if [[ -f logs/gao_final200.done ]]; then
    python experiments/summarize_gao_final200.py >> logs/gao_final200.log 2>&1 || true
    echo "[watcher-done] $(date -Is)" > logs/gao_final200.watch.done
    notify "Gao final200 finished" "$ROOT_DIR/logs/gao_final200_summary.md"
    exit 0
  fi

  if [[ -f logs/gao_final200.failed ]]; then
    echo "[watcher-failed] $(date -Is)" > logs/gao_final200.watch.failed
    notify "Gao final200 failed" "$ROOT_DIR/logs/gao_final200.log"
    exit 1
  fi

  if [[ -f logs/gao_final200.runner.pid ]]; then
    runner_pid="$(cat logs/gao_final200.runner.pid)"
    if ! kill -0 "$runner_pid" >/dev/null 2>&1; then
      echo "[watcher-lost-runner] $(date -Is)" > logs/gao_final200.watch.failed
      notify "Gao final200 runner stopped" "$ROOT_DIR/logs/gao_final200.log"
      exit 1
    fi
  fi

  sleep 60
done
