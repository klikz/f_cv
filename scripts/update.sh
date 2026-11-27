#!/usr/bin/env bash
# GitHub'dan yangilash: kodni olish → bog'liqliklar → migratsiyalar → frontend build → servislarni qayta ishga tushirish.
#   make update            — yangilik bo'lsa yangilaydi
#   make update FORCE=1    — yangilik bo'lmasa ham bog'liqlik/build/restart bajariladi
# data/, .env, modellar (.pt/.engine) git'da emas — ularga tegilmaydi.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

say() { printf '\n\033[1;36m==> %s\033[0m\n' "$*"; }
die() { printf '\n\033[1;31mXATO: %s\033[0m\n' "$*" >&2; exit 1; }

BRANCH="$(git branch --show-current)"
[[ -n "$BRANCH" ]] || die "Git branch aniqlanmadi (detached HEAD?)"

# shu kompyuterda qo'lda o'zgartirilgan fayllar bo'lsa — ustiga yozmaymiz
if ! git diff --quiet || ! git diff --cached --quiet; then
  git status --short
  die "Bu kompyuterda o'zgartirilgan fayllar bor. Ularni saqlash uchun: git stash  (yoki bekor qilish: git checkout -- .), keyin qayta: make update"
fi

say "GitHub'dan olinmoqda (origin/$BRANCH)"
OLD="$(git rev-parse HEAD)"
git fetch origin "$BRANCH"
NEW="$(git rev-parse "origin/$BRANCH")"

if [[ "$OLD" == "$NEW" && "${FORCE:-0}" != "1" ]]; then
  echo "Yangilik yo'q — versiya allaqachon oxirgi ($(git log -1 --format='%h %s'))."
  exit 0
fi

if [[ "$OLD" != "$NEW" ]]; then
  git merge --ff-only "origin/$BRANCH" \
    || die "Mahalliy commitlar GitHub bilan ajralib ketgan. Qo'lda hal qiling: git log --oneline --graph HEAD origin/$BRANCH"
  echo "Yangi commitlar:"
  git log --oneline "$OLD..$NEW"
fi

changed() { [[ "$OLD" == "$NEW" ]] || ! git diff --quiet "$OLD" "$NEW" -- "$@"; }

if changed backend/pyproject.toml backend/uv.lock; then
  say "Backend bog'liqliklari (uv sync)"
  (cd backend && uv sync)
fi

FRONT_CHANGED=0
if changed frontend/package.json frontend/pnpm-lock.yaml; then
  say "Frontend bog'liqliklari (pnpm install)"
  (cd frontend && pnpm install --frozen-lockfile)
fi
if changed frontend || [[ ! -d frontend/dist ]]; then FRONT_CHANGED=1; fi

say "DB migratsiyalari (alembic upgrade head)"
(cd backend && uv run alembic upgrade head)

if [[ "$FRONT_CHANGED" == "1" ]]; then
  say "Frontend build"
  (cd frontend && pnpm build)
fi

say "Servislarni qayta ishga tushirish"
if systemctl is-active --quiet fcv.target 2>/dev/null; then
  # systemd rejimi (deploy/install.sh bilan o'rnatilgan)
  sudo systemctl restart fcv.target fcv-api.service fcv-video.service fcv-logic.service \
    fcv-inference.service fcv-trainer.service fcv-telegram.service \
    || die "systemd servislarini qayta ishga tushirib bo'lmadi — qo'lda: sudo systemctl restart fcv.target"
  systemctl --no-pager --plain list-units 'fcv-*' | head -20
elif ls data/run/*.pid >/dev/null 2>&1; then
  # make start rejimi
  ./scripts/svc.sh down
  ./scripts/svc.sh up
else
  echo "Ishlab turgan servis topilmadi — ishga tushirish: make start"
fi

say "Tayyor: $(git log -1 --format='%h %s (%cd)' --date=format:'%Y-%m-%d %H:%M')"
