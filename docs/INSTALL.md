# O'rnatish qo'llanmasi (yangi serverga noldan)

Docker ishlatilmaydi — hamma narsa systemd + Python venv.

## 1. Uskuna va BIOS
- Monitor **ona plataga (Intel iGPU)** ulanadi — RTX faqat inference/train uchun qoladi.
- BIOS: ichki grafika yoqilgan; **Restore on AC power loss = Power On** (UPS yo'q).

## 2. Tizim paketlari (Ubuntu)
```bash
sudo apt install -y postgresql redis-server ffmpeg chrony vainfo intel-media-va-driver-non-free git curl
sudo timedatectl set-timezone Asia/Tashkent
```
- NVIDIA drayver (≥ 580 — CUDA 13 / TensorRT 11 uchun): `sudo ubuntu-drivers install`, so'ng `nvidia-smi`.
- `uv` (Python 3.12): `curl -LsSf https://astral.sh/uv/install.sh | sh`
- Node.js LTS + pnpm: `corepack enable && corepack prepare pnpm@latest --activate`

## 3. Baza
```bash
sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'postgres';"
sudo -u postgres createdb f_cv
```
PostgreSQL'da `fsync` va `synchronous_commit` yoqilgan bo'lishi kerak (standart).

## 4. Loyiha
```bash
git clone <repo> /opt/f_cv && cd /opt/f_cv
cp .env.example .env            # kerak bo'lsa tahrirlang
make install                    # backend (uv sync) + frontend (pnpm install)
make migrate
make build                      # frontend → frontend/dist
```
**Internetsiz ishlash uchun** (bir marta, o'rnatishda): `data/models/base/` ga `yolo26n.pt`, `yolo26s.pt` va `Arial.ttf`
nusxalang (ultralytics bularni internetdan yuklamasligi uchun).

## 5. Dekod backend'ini tanlash
```bash
cd backend && FAKE_CONVEYOR=8 FAKE_PRESS=7 ../scripts/svc.sh start fake   # yoki haqiqiy kameralar
uv run python ../scripts/bench_decode.py --backends vaapi cpu
```
Natijaga qarab `.env` da `FCV_DECODE_BACKEND=vaapi` yoki `cpu` (NVDEC tavsiya etilmaydi — har oqimga ~400 MB VRAM).

## 6. systemd
```bash
sudo deploy/install.sh
sudo systemctl start fcv.target
systemctl status 'fcv-*'
```
Unitlar: `fcv-migrate` → `fcv-api`, `fcv-video`, `fcv-logic`, `fcv-inference`, `fcv-trainer`, `fcv-telegram`,
`fcv-backup.timer` (har kuni 03:30). Barchasida `Restart=always` va `WatchdogSec=30` (osilib qolsa qayta ishga tushadi).

## 7. Avtomatik ishga tushish (Ubuntu 26.04 LTS)
UI → **Umumiy sozlamalar → Avtomatik ishga tushish**:
- **F_CV servislari** — kompyuter yonganda `fcv.target` (systemd `enable`/`disable`; o'chirilsa ishlab turgan servislar to'xtatilmaydi).
- **Brauzerda kuzatuv paneli** — `~/.config/autostart/fcv-kiosk.desktop` (Chrome / Chromium / Firefox, to'liq ekran yoki oyna). Root kerak emas.
- **Avtomatik kirish** — GDM (`/etc/gdm3/custom.conf`), panel login oynasisiz ochilishi uchun.

Servislar va avtomatik kirish root huquqini talab qiladi: `sudo deploy/install.sh` `/usr/local/sbin/fcv-autostart`
yordamchisini va faqat shu skript uchun parolsiz sudo qoidasini (`/etc/sudoers.d/fcv-autostart`, sudo-rs bilan mos) o'rnatadi.
Qo'lda: `sudo fcv-autostart services on|off`, `sudo fcv-autostart autologin on|off`.

## 8. Tekshirish
- `http://localhost:8100/api/health` — hammasi `ok`.
- UI → Umumiy sozlamalar → Holat: disk, GPU, zaxira.
- Zaxirani tiklashni sinash: `scripts/backup.sh && scripts/backup.sh --verify`.
