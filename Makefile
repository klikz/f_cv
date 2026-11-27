.PHONY: install start stop restart status logs dev migrate test lint fmt build serve push update

install:            ## Bog'liqliklarni o'rnatish
	cd backend && uv sync
	cd frontend && pnpm install

start:              ## Hamma servis fonda: backend + frontend (FAKE=0 — sintetik kameralarsiz)
	./scripts/svc.sh up

stop:               ## Hamma servisni to'xtatish
	./scripts/svc.sh down

restart: stop start

status:
	./scripts/svc.sh status

logs:               ## make logs S=api  (S: api video logic inference trainer telegram fake vite)
	./scripts/svc.sh log $(or $(S),api) 60

dev:                ## Hamma servis + Vite dev server
	./scripts/dev.sh

migrate:            ## DB migratsiyalari
	cd backend && uv run alembic upgrade head

test:
	cd backend && uv run pytest -q

lint:
	cd backend && uv run ruff check . && uv run ruff format --check .
	cd frontend && pnpm lint && npx tsc -b

fmt:
	cd backend && uv run ruff check --fix . && uv run ruff format .

build:              ## Frontend production build (API uni / da beradi)
	cd frontend && pnpm build

serve: build        ## Production rejimiga yaqin: build + servislar (Vite'siz), http://localhost:8100
	./scripts/dev.sh --no-frontend

push:               ## GitHub'ga yuklash: make push M="xabar" (M bo'lmasa — sana bilan)
	git add -A
	@if git diff --cached --quiet; then \
		echo "Commit qilinadigan o'zgarish yo'q"; \
	else \
		git commit -m "$(or $(M),Yangilanish: $(shell date '+%Y-%m-%d %H:%M'))"; \
	fi
	git push origin $$(git branch --show-current)

update:             ## GitHub'dan yangilash: kod + bog'liqliklar + migratsiya + build + restart (FORCE=1 — majburiy)
	FORCE=$(FORCE) ./scripts/update.sh
