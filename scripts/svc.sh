#!/usr/bin/env bash
# Ishlab chiqishda alohida servislarni fonda boshqarish (pid-fayl bilan).
# scripts/svc.sh up|down  — hammasi (make start / make stop)
# scripts/svc.sh start|stop|restart|status|log <nom>   (nom: api video logic inference trainer telegram fake vite all)
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RUN="$ROOT/data/run"; mkdir -p "$RUN"

cmd_of() {
  case "$1" in
    api) echo "cd $ROOT/backend && exec uv run fcv api" ;;
    video) echo "cd $ROOT/backend && exec uv run fcv video-service" ;;
    logic) echo "cd $ROOT/backend && exec uv run fcv camera-logic --supervisor" ;;
    inference) echo "cd $ROOT/backend && exec uv run fcv inference-server" ;;
    trainer) echo "cd $ROOT/backend && exec uv run fcv trainer" ;;
    telegram) echo "cd $ROOT/backend && exec uv run fcv telegram-service" ;;
    fake) echo "cd $ROOT/backend && exec uv run python ../scripts/fake_cameras.py serve --conveyor ${FAKE_CONVEYOR:-2} --press ${FAKE_PRESS:-1}" ;;
    vite) echo "cd $ROOT/frontend && exec pnpm dev" ;;
    *) return 1 ;;
  esac
}
ALL="fake api video logic inference trainer telegram"
# make start/stop uchun to'liq to'plam (FAKE=0 — sintetik kameralarsiz, NO_VITE=1 — frontend dev serversiz)
UP="api video logic inference trainer telegram"

running() { [[ -f "$RUN/$1.pid" ]] && kill -0 "$(cat "$RUN/$1.pid")" 2>/dev/null; }

start() {
  if running "$1"; then echo "$1: allaqachon ishlayapti"; return; fi
  local c; c=$(cmd_of "$1") || { echo "noma'lum: $1"; return 1; }
  setsid bash -c "$c" > "$RUN/$1.log" 2>&1 < /dev/null &
  echo $! > "$RUN/$1.pid"; echo "$1: ishga tushdi (pid $!)"
}
stop() {
  if ! running "$1"; then rm -f "$RUN/$1.pid"; return; fi
  local pid; pid=$(cat "$RUN/$1.pid")
  kill -TERM -- "-$pid" 2>/dev/null || kill -TERM "$pid"
  for _ in $(seq 1 50); do kill -0 "$pid" 2>/dev/null || break; sleep 0.2; done
  kill -KILL -- "-$pid" 2>/dev/null; rm -f "$RUN/$1.pid"; echo "$1: to'xtadi"
}
deps() {  # PostgreSQL va Redis tayyorligini tekshirish
  local ok=0
  (cd "$ROOT/backend" && uv run python - <<'PY'
import asyncio, sys
from app.core.config import get_settings
settings = get_settings()
async def main():
    import asyncpg, redis.asyncio as r
    try:
        c = await asyncpg.connect(settings.database_url.replace("+asyncpg", ""), timeout=5); await c.close()
    except Exception as e:
        print(f"PostgreSQL ishlamayapti: {e}"); sys.exit(1)
    try:
        await r.from_url(settings.redis_url, socket_timeout=5).ping()
    except Exception as e:
        print(f"Redis ishlamayapti: {e}"); sys.exit(1)
asyncio.run(main())
PY
  ) || ok=1
  return $ok
}
wait_api() {
  for _ in $(seq 1 60); do curl -fs -o /dev/null "http://localhost:${API_PORT:-8100}/api/health" && return 0; sleep 0.5; done
  return 1
}
up() {
  deps || { echo "Avval PostgreSQL va Redis'ni ishga tushiring (sudo systemctl start postgresql redis-server)"; exit 1; }
  (cd "$ROOT/backend" && uv run alembic upgrade head) > "$RUN/migrate.log" 2>&1 || { echo "Migratsiya xatosi:"; tail -n 20 "$RUN/migrate.log"; exit 1; }
  echo "migratsiya: OK"
  local list="$UP"
  [[ "${FAKE:-1}" != "0" ]] && list="fake $list"
  [[ "${NO_VITE:-0}" != "1" ]] && list="$list vite"
  for n in $list; do start "$n"; done
  if wait_api; then echo; echo "Tayyor:  UI (dev) http://localhost:5180   |   API/UI (build) http://localhost:${API_PORT:-8100}"
  else echo "API javob bermadi — loglar: scripts/svc.sh log api"; exit 1; fi
}
strays() {  # pid-faylsiz qolib ketgan shu loyiha jarayonlari (masalan, make dev yoki qo'lda ishga tushirilgan)
  pgrep -f "$ROOT/frontend/node_modules/.*vite/bin/vite.js"
  pgrep -f "$ROOT/backend/.venv/bin/(python[0-9.]* )?[^ ]*fcv "
  pgrep -f "scripts/fake_cameras.py serve"
}
down() {
  for n in vite $ALL; do stop "$n"; done
  local p; p=$(strays | tr '\n' ' ')
  if [[ -n "${p// }" ]]; then
    kill -TERM $p 2>/dev/null; sleep 2; p=$(strays | tr '\n' ' '); [[ -n "${p// }" ]] && kill -KILL $p 2>/dev/null
    echo "qolib ketgan jarayonlar ham to'xtatildi"
  fi
  echo "Hammasi to'xtadi"
}
names() { [[ "$1" == "all" ]] && echo $ALL || echo "$1"; }

case "${1:-}" in
  start) for n in $(names "$2"); do start "$n"; done ;;
  stop) for n in $(names "$2"); do stop "$n"; done ;;
  restart) for n in $(names "$2"); do stop "$n"; start "$n"; done ;;
  up) up ;;
  down) down ;;
  status) for n in $ALL vite; do running "$n" && echo "$n: ishlayapti" || echo "$n: -"; done ;;
  log) tail -n "${3:-40}" "$RUN/$2.log" ;;
  *) echo "scripts/svc.sh start|stop|restart|status|log <nom>"; exit 1 ;;
esac
