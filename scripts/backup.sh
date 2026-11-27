#!/usr/bin/env bash
# Kunlik zaxira (8.5): PostgreSQL (pg_dump) + modellar (.pt) va sozlamalar. Saqlash muddati: KEEP_DAYS (14).
#   scripts/backup.sh            — zaxira olish
#   scripts/backup.sh --verify   — oxirgi zaxirani bo'sh bazaga tiklab tekshirish
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
set -a; [[ -f "$ROOT/.env" ]] && source "$ROOT/.env"; set +a
DB_URL="${FCV_DATABASE_URL:-postgresql+asyncpg://postgres:postgres@localhost:5432/f_cv}"
PG_URL="${DB_URL/+asyncpg/}"
OUT="$ROOT/data/backups"; mkdir -p "$OUT"
KEEP_DAYS="${KEEP_DAYS:-14}"
TS=$(date +%Y%m%d_%H%M%S)

status() {  # status <ok|error> <xabar> [fayllar...]
  local st=$1 msg=$2; shift 2
  python3 - "$OUT/last.json" "$st" "$msg" "$@" <<'PY'
import json, os, sys, time
p, st, msg, *files = sys.argv[1:]
old = {}
try:
    old = json.load(open(p))
except Exception:
    pass
d = {"status": st, "message": msg, "ts": time.time(), "files": [{"name": os.path.basename(f), "size": os.path.getsize(f)} for f in files if os.path.exists(f)]}
d["last_success_ts"] = d["ts"] if st == "ok" else old.get("last_success_ts")
if "verify" in msg:
    d["files"], d["last_success_ts"] = old.get("files", []), old.get("last_success_ts")
    d["status"], d["message"] = old.get("status", st), old.get("message", msg)
    d["last_verify"] = {"ts": d["ts"], "status": st, "message": msg}
elif old.get("last_verify"):
    d["last_verify"] = old["last_verify"]
tmp = p + ".tmp"; json.dump(d, open(tmp, "w"), ensure_ascii=False, indent=2); os.replace(tmp, p)
PY
}

if [[ "${1:-}" == "--verify" ]]; then
  F=$(ls -1t "$OUT"/db_*.dump 2>/dev/null | head -1)
  [[ -n "$F" ]] || { status error "verify: zaxira topilmadi"; exit 1; }
  BASE="${PG_URL%/*}"; TEST_DB="f_cv_restore_test"
  psql "$BASE/postgres" -qc "DROP DATABASE IF EXISTS $TEST_DB" -c "CREATE DATABASE $TEST_DB"
  pg_restore --no-owner -d "$BASE/$TEST_DB" "$F"
  ORIG=$(psql "$PG_URL" -Atc "select count(*) from count_events")
  REST=$(psql "$BASE/$TEST_DB" -Atc "select count(*) from count_events")
  TABLES=$(psql "$BASE/$TEST_DB" -Atc "select count(*) from information_schema.tables where table_schema='public'")
  psql "$BASE/postgres" -qc "DROP DATABASE $TEST_DB"
  if [[ "$REST" -gt 0 || "$ORIG" -eq 0 ]]; then
    status ok "verify: $(basename "$F") tiklandi — $TABLES jadval, count_events: zaxirada $REST (hozir $ORIG)"; echo "Tiklash sinovi muvaffaqiyatli ($TABLES jadval, $REST sanoq)"
  else
    status error "verify: tiklangan bazada ma'lumot yo'q"; exit 1
  fi
  exit 0
fi

DB_F="$OUT/db_$TS.dump"
MODELS_F="$OUT/models_$TS.tar.gz"
if ! pg_dump --format=custom --compress=6 -f "$DB_F.tmp" "$PG_URL"; then
  rm -f "$DB_F.tmp"; status error "pg_dump xatosi"; exit 1
fi
mv "$DB_F.tmp" "$DB_F"
# modellar (.pt — engine'lar qayta quriladi), tayanch kadrlar, sozlamalar
# uskuna tayanch kadrlari vazifa papkasida (rasmlar umumiy papkasi data/ dan tashqarida ham bo'lishi mumkin)
HOME_LIST="$OUT/.home_refs.txt"
psql "$PG_URL" -Atc "select home_reference from equipment_configs where home_reference is not null" 2>/dev/null \
  | sed -e '/^\//!s|^|data/|' > "$HOME_LIST" || : > "$HOME_LIST"
tar -C "$ROOT" -czf "$MODELS_F.tmp" --exclude='data/models/runs' --exclude='data/models/ultralytics' data/models data/equipment .env -T "$HOME_LIST" 2>/dev/null || true
rm -f "$HOME_LIST"
mv "$MODELS_F.tmp" "$MODELS_F"
find "$OUT" -maxdepth 1 \( -name 'db_*.dump' -o -name 'models_*.tar.gz' \) -mtime +"$KEEP_DAYS" -delete
status ok "Zaxira olindi" "$DB_F" "$MODELS_F"
echo "Zaxira: $DB_F ($(du -h "$DB_F" | cut -f1)), $MODELS_F ($(du -h "$MODELS_F" | cut -f1))"
