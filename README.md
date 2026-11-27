# F_CV — mahsulot sanash va uskuna ish vaqti tizimi

Arxitektura va qarorlar: [PLAN.md](PLAN.md) · bosqichlar va joriy holat: [plan/README.md](plan/README.md)

Hujjatlar: [O'rnatish](docs/INSTALL.md) · [Foydalanuvchi qo'llanmasi](docs/USER_GUIDE.md) · [Nosozliklar](docs/TROUBLESHOOTING.md)

## Talablar

Ubuntu, NVIDIA drayver, Python 3.12 + [uv](https://docs.astral.sh/uv/), Node.js LTS + pnpm,
PostgreSQL (5432), Redis (6379), ffmpeg. Docker ishlatilmaydi.

## Birinchi o'rnatish

```bash
cp .env.example .env                 # kerak bo'lsa tahrirlang
createdb -h localhost -U postgres f_cv
make install                         # backend (uv) + frontend (pnpm)
make migrate                         # jadvallar + standart smenalar
```

## Ishlab chiqish

```bash
make start      # hamma servis fonda: backend + frontend → http://localhost:5180 (API: 8100)
make stop       # hammasini to'xtatish
make status     # qaysi servis ishlayapti
make logs S=api # servis logi (api video logic inference trainer telegram fake vite)
make dev        # xuddi shu, lekin oldingi planda, loglar ekranda (Ctrl+C — to'xtatish)
make test       # backend testlari
make lint       # ruff + oxlint + tsc
```

`make start` sozlamalari: `FAKE=0` — sintetik kameralarsiz, `NO_VITE=1` — Vite'siz (build qilingan UI 8100 da). Servislarni alohida boshqarish: `scripts/svc.sh start|stop|restart|status|log <api|video|logic|inference|trainer|telegram|fake|vite|all>`

Sinov uchun soxta kameralar (haqiqiy kamerasiz): `cd backend && uv run python ../scripts/fake_cameras.py generate`, so'ng `scripts/svc.sh start fake` → `rtsp://127.0.0.1:8654/cam1/main`

Bitta servisni alohida: `cd backend && uv run fcv <api|video-service|inference-server|camera-logic --camera-id N|trainer|telegram-service>`

## Production (systemd)

```bash
make build                  # frontend → frontend/dist (API uni / da beradi)
cd backend && uv sync --no-dev --extra ml
sudo deploy/install.sh      # unitlar: fcv.target, fcv-api, fcv-video, ...
sudo systemctl start fcv.target
```

UI: `http://<server>:8100/`. Brauzerni yonganda avtomatik ochish: `deploy/autostart/fcv-kiosk.desktop` → `~/.config/autostart/`.

Holat: `GET /api/health` (DB, Redis, GPU, disk, servislar heartbeat'i). Loglar: `journalctl -u fcv-api` va `data/logs/`.
