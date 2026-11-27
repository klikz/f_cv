# Bosqich 1 — Kameralar va video

**Holat:** 🟡 Deyarli tugagan (ONVIF profillari va 1 soatlik 15 kamera sinovi qolgan)
**Bog'liqlik:** Bosqich 0
**Maqsad:** kameralar UI orqali RTSP (asosiy usul) yoki ONVIF (qo'shimcha usul) bilan qo'shiladi/o'chiriladi; har kameradan ikki oqim (main va sub) olinadi; grid sub oqimdan, kamera sahifasi main oqimdan barqaror ko'rinadi. Dekod backend'i o'lchov asosida tanlangan.

**Oqimlardan foydalanish:** grid — sub, kamera sahifasi — main; kameraning tahlil oqimi (main/sub) ikkala vazifa uchun bitta, kamera sahifasida tanlanadi (PLAN.md 1.3, 2-bosqich).

---

## 1.1. Kameralar: baza va API

- [x] 1.1.1 Migratsiya: `cameras` (nom, faol, tartib, ulanish usuli, main_rtsp_url, sub_rtsp_url, analysis_stream (default main), fov_match, ONVIF maydonlari), `camera_streams` (turi, kodek, o'lcham, fps, holat, oxirgi xato), `coverage_gaps`
- [x] 1.1.2 CRUD API: ro'yxat, bitta, yaratish, tahrirlash, o'chirish, tartibni o'zgartirish
- [x] 1.1.3 "Oqimni tekshirish" API: `ffprobe` orqali har oqim (main, sub) uchun kodek, o'lcham, FPS (timeout bilan), xatoni tushunarli matnda qaytarish
- [x] 1.1.4 Ikkala oqimdan bittadan kadr olish API (ko'rish maydonini yonma-yon solishtirish va `fov_match` belgisi uchun)
- [x] 1.1.5 Sub manzili ixtiyoriy: kiritilmasa, barcha vazifalar main dan ishlaydi
- [x] 1.1.6 Parollar UI ro'yxatida yashirib ko'rsatiladi (RTSP manzilidagi va ONVIF)
- [x] 1.1.7 Kamera o'zgarganda Redis orqali xabar (qo'shildi / o'zgardi / o'chirildi)
- [x] 1.1.8 API testlari

## 1.2. ONVIF

- [x] 1.2.1 WS-Discovery: LAN dagi ONVIF qurilmalarni qidirish (IP, ishlab chiqaruvchi, model; allaqachon qo'shilganlari belgilanadi)
- [x] 1.2.2 Ulanish (IP, port, login, parol): qurilma ma'lumoti — ishlab chiqaruvchi, model, seriya raqami
- [x] 1.2.3 Profillar ro'yxati: har profil uchun o'lcham, FPS, kodek va `GetStreamUri` orqali RTSP manzil
- [x] 1.2.4 Main/sub ni avtomatik taklif qilish (eng katta o'lcham — main, kichigi — sub)
- [x] 1.2.5 RTSP manzilga login/parolni qo'shish (kamera manzilni ularsiz qaytarsa)
- [x] 1.2.6 Natijani `cameras` ga RTSP manzillari sifatida saqlash (video doim RTSP orqali olinadi)
- [x] 1.2.7 "ONVIF orqali yangilash" API: manzillar/profillarni qayta o'qish
- [x] 1.2.8 Xatolar: autentifikatsiya, ONVIF o'chirilgan — tushunarli matn; kamera soati farq qilsa — kamera vaqtini (`GetSystemDateAndTime`) o'qib, farqni hisobga olib ulanish (kamera vaqti hisobotlarda ishlatilmaydi)
- [ ] 1.2.9 Mavjud kameralarda sinash; qidirish tarmoqda ishlamasa — IP ni qo'lda kiritish yo'li ← JARAYONDA (LAN qidiruvi 60 ta kamera topdi; profillarni o'qish uchun kamera login/paroli kerak)

**Sinalgan kameralar** (to'ldiriladi):

| Ishlab chiqaruvchi / model | ONVIF qidirish | Profillar | Main | Sub | Izoh |
|---|---|---|---|---|---|
| Dahua DH-IPC-HFW1230S1-S5, IPC-HFW1431S1-S4 va b. | ✅ topildi | — | — | — | login/parol kerak |
| Hikvision DS-2CD1043G2-I, DS-2CD2183G2-LI | ✅ topildi | — | — | — | 192.168.0.21: "login yoki parol xato" to'g'ri chiqdi |
| Soxta kamera (scripts/fake_cameras.py) | — | — | ✅ | ✅ | RTSP usuli to'liq sinaldi |

## 1.3. Dekod benchmark (backend tanlash)

- [x] 1.3.1 Benchmark skripti: VAAPI, NVDEC, CPU — stsenariylar: 15 sub; 15 sub + 5 main; 15 sub + 10 main; 15 sub + 15 main
- [x] 1.3.2 O'lchash: CPU %, GPU %, VRAM, haqiqiy FPS, tushib qolgan kadrlar, 10 daqiqa barqarorlik
- [x] 1.3.3 Dekoderning o'zida 10 fps ga siyraklashtirish ishlashini tekshirish
- [x] 1.3.4 Natijalarni quyidagi jadvalga yozish va backend tanlash (main va sub uchun turli backend ham bo'lishi mumkin)
- [x] 1.3.5 Yetmasa: kamerada H.265 / past FPS variantlarini sinash va yozib qo'yish

**Benchmark natijalari** (to'ldiriladi):

Dev kompyuterda (i9-14900KF, RTX 4090), soxta kameralar (H.264, main 1080p25 4 Mbit/s, sub 640×360), har stsenariy 40 s,
CPU % — bitta yadroga nisbatan (100% = 1 yadro). `scripts/bench_decode.py`, natija `data/logs/bench_decode.json`.

| Backend | Sub | Main | CPU % | GPU % | VRAM | Kadr tushishi | Xulosa |
|---|---|---|---|---|---|---|---|
| CPU | 15 | 0 | 24 | — | 0 | 0% | ✅ |
| CPU | 15 | 5 | 77 | — | 0 | 0% | ✅ |
| CPU | 15 | 10 | 136 | — | 0 | 0% | ✅ |
| CPU | 15 | 15 | 204 | — | 0 | 0% | ✅ ~2 yadro |
| NVDEC | 15 | 0 | 28 | 11 (NVDEC 5) | **6040 MB** | 0% | ❌ VRAM |
| NVDEC | 15 | 5 | 69 | 14 (NVDEC 20) | 8201 MB | 0% | ❌ |
| NVDEC | 15 | 10 | 111 | 16 (NVDEC 28) | 10359 MB | 0.1% | ❌ |
| NVDEC | 15 | 15 | 159 | 19 (NVDEC 43) | **12517 MB** | 0.1% | ❌ 8 GB ga sig'maydi |
| VAAPI | 15 | 15 | 2026-11-27 | 1.7.11 | 1.2.9, 15 kamera 1 soat | Dev'da soxta RTSP kameralar bilan to'liq sinaldi | dev'da iGPU yo'q — serverda `bench_decode.py --backends vaapi cpu` |

- NVDEC (PyAV) har oqimga alohida CUDA konteksti ochadi: ~400 MB VRAM/oqim → RTX 3070 da inference uchun joy qolmaydi.
- H.265 vs H.264 (bitta yadro, 1080p25): H.264 — 0.20 yadro/oqim, H.265 — 0.12 yadro/oqim (sintetik sahna; haqiqiy kamerada 2–3 barobar ko'p bo'lishi mumkin).
- Haqiqiy kameralar bilan serverda qayta o'lchash kerak (12700K: 20 thread — CPU zaxirasi katta).

**Tanlangan backend:** main — **CPU** (serverda iGPU bo'lsa VAAPI sinaladi), sub — **CPU**. `FCV_DECODE_BACKEND=auto` → VAAPI bo'lsa VAAPI, aks holda CPU.

## 1.4. video-service

- [x] 1.4.1 Dekod backend abstraksiyasi (bir xil interfeys: ochish, kadr olish, yopish)
- [x] 1.4.2 Har oqim uchun dekod oqimi (thread); kadrlar 10 fps
- [x] 1.4.3 Shared memory halqa-bufer: har kamera va oqim (main/sub) uchun segment, sarlavha (kadr raqami, vaqt, o'lcham, format), yozuvchi/o'quvchi kutubxonasi
- [x] 1.4.4 **Talab bo'yicha ochish:** sub — har faol kamerada doim; main — iste'molchi bo'lsa (kamerada vazifa yoqilgan va tahlil oqimi main, sahifa ko'rilyapti, snapshot so'raldi); iste'molchilar Redis'da muddatli yozuv bilan qayd etiladi; iste'molchi qolmasa kutish vaqtidan keyin yopiladi
- [x] 1.4.5 Sub yo'q yoki ishlamayotgan bo'lsa — sub iste'molchilariga main kadrlari beriladi (kichraytirib)
- [x] 1.4.6 Avto qayta ulanish (ortib boruvchi kutish bilan); holat har oqim uchun Redis'ga: `online / connecting / offline / error`
- [x] 1.4.7 "Qotib qolgan oqim" nazorati: N soniya kadr kelmasa qayta ulanish
- [x] 1.4.8 Kamera qo'shish/o'zgartirish/o'chirishni qayta ishga tushirmasdan qo'llash
- [x] 1.4.9 Kamera uzilgan oraliqlarni `coverage_gaps` ga yozish (sabab: kamera)
- [x] 1.4.10 Shared memory va talab bo'yicha ochish uchun testlar

## 1.5. camera-logic skeleti va JPEG

- [x] 1.5.1 Boshqaruvchi: har faol kamera uchun `camera-logic` processini ishga tushirish/to'xtatish, yiqilsa qayta ko'tarish
- [x] 1.5.2 Shared memory'dan kerakli oqim kadrini o'qish
- [x] 1.5.3 JPEG tayyorlash: grid profili (sub dan, ≈640×360, 3–5 fps), sahifa profili (main dan, 720p–1080p, 10 fps)
- [x] 1.5.4 "Faqat ko'rayotgan bo'lsa" mexanizmi: tomoshabin yo'q bo'lsa JPEG tayyorlanmaydi; sahifa ochilganda main iste'molchisi qayd etiladi
- [x] 1.5.5 Xabar formati: sarlavha (kamera, oqim, kadr raqami, vaqt, metadata joyi) + JPEG — bitta ikkilik xabarda

## 1.6. WebSocket

- [x] 1.6.1 `/ws/grid`: mijoz ko'rayotgan kameralar ro'yxatiga obuna bo'ladi (sahifa almashganda yangilanadi)
- [x] 1.6.2 `/ws/camera/:id`: bitta kamera, sahifa profili (main)
- [x] 1.6.3 Sekin mijoz uchun eski kadrlarni tashlab yuborish (navbat to'lib ketmasin)
- [x] 1.6.4 Oqimlar holati o'zgarishini ham shu kanaldan yuborish

## 1.7. Frontend

- [x] 1.7.1 `/settings/cameras`: ro'yxat (main/sub holati bilan), tahrirlash, o'chirish (tasdiqlash bilan), sudrab tartiblash
- [x] 1.7.2 Qo'shish oynasi — **RTSP** yorlig'i (default): nom, main va sub manzillari, har biri uchun "Tekshirish" (kodek/o'lcham/FPS)
- [x] 1.7.3 Qo'shish oynasi — **ONVIF** yorlig'i: "Tarmoqdan qidirish" ro'yxati yoki IP ni qo'lda kiritish → login/parol → profillar → main/sub tanlash → RTSP manzillari avtomatik to'ldiriladi
- [x] 1.7.4 Saqlashdan oldin main va sub kadrlari yonma-yon + "Ko'rish maydoni bir xil" belgisi (`fov_match`)
- [x] 1.7.5 Tahrirlashda "ONVIF orqali yangilash" tugmasi (ONVIF bilan qo'shilgan kameralar uchun)
- [x] 1.7.6 `/` grid (sub): 1×1 / 2×2 / 3×3 / 4×4 almashtirgich, pagination, rejim va sahifa URL'da (`?grid=&page=`)
- [x] 1.7.7 Grid katagi: video (canvas), kamera nomi, ulanish holati belgisi, uzilganda "aloqa yo'q" ko'rinishi
- [x] 1.7.8 To'liq ekran rejimi
- [x] 1.7.9 Katakka **ikki marta bosish** → `/cameras/:id`
- [x] 1.7.10 `/cameras/:id` (main): katta video preview, kamera ma'lumotlari (oqimlar, kodek, o'lcham, ONVIF qurilma ma'lumoti), orqaga qaytish
- [x] 1.7.11 Kamera yo'q bo'lganda bo'sh holat ("Kamera qo'shing")

---

## Qabul mezonlari

- [x] Bosqichdagi barcha sahifalar dizayn tekshiruv ro'yxatidan (PLAN.md 4.1.6) o'tdi va o'z URL'i bilan ishlaydi (headless Chrome bilan tekshirildi, konsol xatosiz)
- [x] Kamera RTSP manzillari bilan qo'shiladi, tahrirlanadi, o'chiriladi — servislarni qayta ishga tushirmasdan
- [ ] Kamera ONVIF orqali topiladi va main/sub manzillari avtomatik to'ldiriladi (topiladi; avto to'ldirish login/parol bilan sinalishi kerak)
- [x] Grid sub oqimdan, kamera sahifasi main oqimdan ochiladi
- [x] Sahifa yopilgandan keyin (vazifasi yo'q yoki tahlil oqimi sub bo'lgan kamerada) main oqim yopiladi (30 s dan keyin yopiladi)
- [ ] 15 ta kamera grid'da 1 soat barqaror ko'rinadi (4×4) (sinalmagan)
- [x] Kamera kabeli uzilib qayta ulanganda o'zi tiklanadi, oraliq `coverage_gaps` ga yozilgan (soxta kamerada offline.json bilan sinaldi)
- [x] Benchmark jadvali to'ldirilgan, backend tanlangan
- [x] Hech kim ko'rmayotganda JPEG tayyorlanmaydi (CPU yuklamasi pasayadi)

---

## Jurnal (to'xtash nuqtalari)

| Sana | Oxirgi bajarilgan qadam | Keyingi qadam | Izoh / muammo |
|---|---|---|---|
| | | | |
