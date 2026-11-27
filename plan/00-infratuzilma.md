# Bosqich 0 — Infratuzilma va dizayn tizimi

**Holat:** 🟡 Jarayonda
**Bog'liqlik:** yo'q
**Maqsad:** server muhiti tayyor, loyiha skeleti (backend, frontend, barcha processlar) ishga tushadi, dizayn tizimi va asosiy ekranlar prototipi tasdiqlangan; hali biznes logika yo'q.

---

## 0.1. Server muhitini tekshirish

- [x] 0.1.1 Ubuntu versiyasi, yadro, disk bo'limlari va bo'sh joyni yozib olish (dev: Ubuntu 26.04.1, yadro 7.0.0-44, nvme0n1p2 1.8T / 691G bo'sh)
- [x] 0.1.2 NVIDIA drayver va `nvidia-smi` ishlashini tekshirish; drayver va CUDA versiyasini yozib olish (dev: RTX 4090, 595.99.02 / CUDA 13.2)
- [ ] 0.1.3 BIOS'da ichki grafika (UHD 770) yoqilganini tekshirish; `vainfo` orqali VAAPI dekod profillarini (H.264, H.265) ko'rish ← SERVERDA (dev'da iGPU yo'q)
- [x] 0.1.4 `ffmpeg` / `ffprobe` o'rnatish; VAAPI va NVDEC qo'llashini tekshirish (NVDEC: H.264 va H.265 1080p dekod sinovi o'tdi; VAAPI — serverda tekshiriladi)
- [x] 0.1.5 Python 3.12 va `uv` o'rnatish
- [x] 0.1.6 Node.js (LTS) va `pnpm` o'rnatish
- [x] 0.1.7 PostgreSQL ga ulanishni tekshirish (5432, postgres/postgres); `f_cv` bazasini yaratish (+ testlar uchun `f_cv_test`)
- [x] 0.1.8 Redis ishlashini tekshirish (`redis-cli ping`) (AOF tuzatildi; f_cv Redis'ning 5-bazasini ishlatadi — boshqa loyihalar kalitlari bilan aralashmaslik uchun)
- [x] 0.1.9 TensorRT o'rnatish (pip paketi) va versiyasini yozib olish (backend asosiy bog'liqliklarida)
- [x] 0.1.10 Ma'lumot papkalarini yaratish: `data/snapshots`, `data/datasets`, `data/models`, `data/engines`, `data/logs` (sozlamalar moduli ishga tushishda ham yaratadi)
- [x] 0.1.11 Server vaqt zonasi Asia/Tashkent; `chrony` o'rnatish (internet bor paytda sinxron, yo'q paytda o'z soati)
- [ ] 0.1.12 BIOS: "Restore on AC power loss = Power On" (UPS yo'q — elektr qaytganda o'zi yonadi) ← SERVERDA
- [ ] 0.1.13 Monitorni ona plataga (Intel iGPU) ulash; RTX da ekran jarayonlari yo'qligini `nvidia-smi` da tekshirish ← SERVERDA
- [ ] 0.1.14 Ubuntu desktop + Chrome; yonganda grid sahifasini avtomatik ochish (autostart, ixtiyoriy kiosk) ← SERVERDA (autostart fayli tayyor: deploy/autostart/)
- [x] 0.1.15 PostgreSQL da `fsync` va `synchronous_commit` yoqilganini tekshirish (ikkalasi `on`)

**Yozib olingan versiyalar** (to'ldiriladi):

| Narsa | Versiya |
|---|---|
| Ubuntu | dev: 26.04.1 LTS, yadro 7.0.0-44 · server: — |
| NVIDIA drayver / CUDA | dev: 595.99.02 / 13.2 (RTX 4090 24GB) · server: — (RTX 3070 kutilmoqda) |
| TensorRT | 11.5.0.63 (tensorrt-cu13; CUDA 13 → drayver ≥ 580 kerak — serverda tekshirish) |
| ffmpeg | n9.0.2 (`~/.local/bin`, cuda/vaapi/qsv) · ffprobe 8.0.1 |
| Python / Node | Python 3.12.16 (uv 0.13.6) / Node 22.23.4, pnpm 12.23.0 |
| PostgreSQL / Redis | 18.6 / 8.10.3 |

## 0.2. Repo va tuzilma

- [x] 0.2.1 `git init`, `.gitignore` (data/, .env, node_modules, __pycache__, *.engine, *.pt) (repo avvaldan bor edi)
- [x] 0.2.2 Papka tuzilmasini yaratish (PLAN.md 2-bo'lim bo'yicha)
- [x] 0.2.3 `.env.example` va `.env`: DB, Redis, data yo'llari, Telegram token (bo'sh), dekod backend
- [x] 0.2.4 Qisqa `README.md`: ishga tushirish buyruqlari

## 0.3. Backend skeleti

- [x] 0.3.1 `uv` loyihasi, asosiy bog'liqliklar (FastAPI, SQLAlchemy 2 async, Alembic, Pydantic, redis, uvicorn)
- [x] 0.3.2 Sozlamalar moduli (`pydantic-settings`, `.env` dan o'qish)
- [x] 0.3.3 Loglash: yagona format, fayl + journald, process nomi bilan
- [x] 0.3.4 PostgreSQL sessiyasi (async) va Redis klienti
- [x] 0.3.5 Alembic sozlash; birinchi migratsiya: `settings`, `shifts`
- [x] 0.3.6 Standart smenalarni kiritish (08:00–19:00, 19:00–08:00) va **smenani aniqlash funksiyasi** (vaqt → smena, smena sanasi; yarim tundan o'tish; smenadan tashqari)
- [x] 0.3.7 Smena funksiyasi uchun testlar (chegaraviy vaqtlar: 07:59, 08:00, 18:59, 19:00, 00:30) — 17 test o'tdi
- [x] 0.3.8 `/api/health`: DB, Redis, GPU (pynvml), disk holati
- [x] 0.3.9 `ruff` va `pytest` sozlash

## 0.4. Frontend skeleti

- [x] 0.4.1 Vite + React + TypeScript loyihasi
- [x] 0.4.2 Tailwind + shadcn/ui o'rnatish; dizayn tokenlari (ranglar, holat ranglari, radius, masofalar)
- [x] 0.4.3 Inter shriftini loyiha ichiga joylash (internetsiz)
- [x] 0.4.4 Qorong'i / yorug' mavzu o'tkazgichi (brauzerda eslab qolinadi; default — qorong'i)
- [x] 0.4.5 Asosiy layout: yig'iladigan yon menyu, yuqori panel (umumiy holat joyi)
- [x] 0.4.6 React Router: PLAN.md 4.2 dagi **barcha URL'lar** uchun bo'sh sahifalar + "Sahifa topilmadi"
- [x] 0.4.7 O'zbekcha matnlar uchun yagona tarjima fayli
- [x] 0.4.8 API klient + TanStack Query; WebSocket hook (avto qayta ulanish bilan)
- [x] 0.4.9 Umumiy komponentlar: toast, tasdiqlash oynasi, skeleton, bo'sh holat, xato holati
- [x] 0.4.10 Yuqori panelda `/api/health` asosida holat ko'rsatkichlari
- [x] 0.4.11 URL yordamchilari: oyna/yorliq/qadam holatini URL'da saqlash, brauzer yorlig'i nomi har sahifada, ichki havolalar haqiqiy `<a>`
- [x] 0.4.12 Atamalar lug'ati (o'zbekcha UI atamalari, bir joyda) va (?) izoh komponenti
- [x] 0.4.13 Buyruqlar oynasi (Ctrl+K) skeleti va `?` — qisqa tugmalar ro'yxati

## 0.6. Dizayn tizimi va prototiplar (PLAN.md 4.1)

- [x] 0.6.1 Dizayn tokenlari to'liq: ranglar (ikki mavzu), holat ranglari, masofa shkalasi, radius, soyalar, shrift o'lchamlari, animatsiya vaqtlari (`frontend/src/index.css`)
- [x] 0.6.2 `/dev/ui` dizayn tizimi sahifasi: tugmalar, formalar, jadval, kartochka, holat belgilari, toast, oyna, bo'sh/yuklanish/xato holatlari — ikkala mavzuda
- [x] 0.6.3 Video katagi komponenti (grid uchun) va AI qatlami uslubi (chiziq qalinligi, yorliqlar, ranglar) namunasi
- [x] 0.6.4 Asosiy ekranlar prototipi (soxta ma'lumot bilan, ishlaydigan URL'larda): grid, kamera sahifasi, sanash sozlamalari, belgilash, train monitoringi (alohida prototip o'rniga haqiqiy sahifalar ishlaydigan holda qilindi — soxta kameralar bilan jonli)
- [ ] 0.6.5 Prototiplarni foydalanuvchi bilan ko'rib chiqish, izohlarni yozib olish va tuzatish ← FOYDALANUVCHI KO'RIB CHIQISHI KERAK
- [ ] 0.6.6 Prototiplar tasdiqlandi (sana va izohlar quyidagi jadvalda) ← FOYDALANUVCHI TASDIQLASHI KERAK

**Prototip ko'rib chiqish** (to'ldiriladi):

| Ekran | Sana | Izohlar | Tasdiqlandi |
|---|---|---|---|
| Grid | | | |
| Kamera sahifasi | | | |
| Sanash sozlamalari | | | |
| Belgilash | | | |
| Train monitoringi | | | |

## 0.5. Process skeletlari va ishga tushirish

- [x] 0.5.1 Kirish nuqtalari: `api`, `video-service`, `inference-server`, `camera-logic`, `trainer`, `telegram-service` (hozircha bo'sh sikl)
- [x] 0.5.2 Har process Redis'ga **heartbeat** yozadi (nom, pid, vaqt); `/api/health` ularni ko'rsatadi
- [x] 0.5.3 Ishlab chiqish uchun bitta buyruq bilan hammasini ishga tushirish (`make dev` yoki skript)
- [x] 0.5.4 systemd unit fayllari (`deploy/`), `Restart=always`, ishga tushish tartibi
- [x] 0.5.5 Frontend build'ni backend orqali berish + SPA fallback (istalgan URL yangilanganda ochiladi)

---

## Qabul mezonlari

- [x] Barcha servislar bitta buyruq bilan ishga tushadi; `/api/health` hammasini "ok" ko'rsatadi (make dev / scripts/dev.sh)
- [x] Brauzerda layout ochiladi, barcha URL'lar ishlaydi, sahifa yangilanganda joyida qoladi
- [ ] `/dev/ui` sahifasi tayyor, asosiy ekranlar prototipi foydalanuvchi tomonidan tasdiqlangan (sahifa tayyor; ekranlar tasdig'i kutilmoqda)
- [x] Mavzu almashadi, shrift internetsiz yuklanadi
- [x] Smena funksiyasi testlari o'tadi

---

## Jurnal (to'xtash nuqtalari)

| Sana | Oxirgi bajarilgan qadam | Keyingi qadam | Izoh / muammo |
|---|---|---|---|
| 2026-11-26 | 0.5.5, 0.6.1 (0.1–0.5 asosan tayyor) | 0.6.2 `/dev/ui` | Dev kompyuter (i9-14900KF, RTX 4090) — rejadagi serverdan farq qiladi; BIOS/iGPU/kiosk qadamlari ← SERVERDA. Tizim Redis'i AOF buzilgani uchun ishlamayapti (sudo kerak) → 0.1.8, 0.5.2 kutilmoqda. Portlar: API 8100, Vite 5180 (8000/5173 boshqa loyihalarda band). |
| 2026-11-27 | 0.6.4 | 0.6.5 (foydalanuvchi ko'rib chiqishi) | Dizayn tizimi /dev/ui da; asosiy ekranlar haqiqiy ma'lumot bilan ishlaydi |
