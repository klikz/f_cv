#!/usr/bin/env bash
# Ishlab chiqish: barcha servislarni bitta buyruq bilan ishga tushirish (Ctrl+C — hammasini to'xtatadi).
# Foydalanish: scripts/dev.sh [--no-frontend]
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/backend"

NO_FE=0
[[ "${1:-}" == "--no-frontend" ]] && NO_FE=1

pids=()
run() {  # run <nom> <rang> <buyruq...>
  local name=$1 color=$2; shift 2
  ( "$@" 2>&1 | sed -u "s/^/\x1b[${color}m[${name}]\x1b[0m /" ) &
  pids+=($!)
}

cleanup() {
  echo; echo "To'xtatilmoqda..."
  pkill -TERM -P $$ 2>/dev/null
  for p in "${pids[@]}"; do pkill -TERM -P "$p" 2>/dev/null; kill -TERM "$p" 2>/dev/null; done
  wait 2>/dev/null
  exit 0
}
trap cleanup INT TERM

uv run alembic upgrade head || { echo "Migratsiya xatosi"; exit 1; }

run api              32 uv run fcv api
run video            36 uv run fcv video-service
run logic            31 uv run fcv camera-logic --supervisor
run inference        35 uv run fcv inference-server
run trainer          33 uv run fcv trainer
run telegram         34 uv run fcv telegram-service
if [[ $NO_FE -eq 0 ]]; then
  run frontend 37 bash -c "cd '$ROOT/frontend' && pnpm dev"
fi

echo "API: http://localhost:8100   Frontend (dev): http://localhost:5180"
wait
