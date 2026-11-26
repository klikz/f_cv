# Bosqich 1 — Kameralar va video

**Holat:** ⬜ Boshlanmagan
**Bog'liqlik:** Bosqich 0
**Maqsad:** kameralar UI orqali RTSP (asosiy usul) yoki ONVIF (qo'shimcha usul) bilan qo'shiladi/o'chiriladi; har kameradan ikki oqim (main va sub) olinadi; grid sub oqimdan, kamera sahifasi main oqimdan barqaror ko'rinadi. Dekod backend'i o'lchov asosida tanlangan.

**Oqimlardan foydalanish:** grid — sub, kamera sahifasi — main; kameraning tahlil oqimi (main/sub) ikkala vazifa uchun bitta, kamera sahifasida tanlanadi (PLAN.md 1.3, 2-bosqich).

---

## 1.1. Kameralar: baza va API

- [ ] 1.1.1 Migratsiya: `cameras` (nom, faol, tartib, ulanish usuli, main_rtsp_url, sub_rtsp_url, analysis_stream (default main), fov_match, ONVIF maydonlari), `camera_streams` (turi, kodek, o'lcham, fps, holat, oxirgi xato), `coverage_gaps`
- [ ] 1.1.2 CRUD API: ro'yxat, bitta, yaratish, tahrirlash, o'chirish, tartibni o'zgartirish
- [ ] 1.1.3 "Oqimni tekshirish" API: `ffprobe` orqali har oqim (main, sub) uchun kodek, o'lcham, FPS (timeout bilan), xatoni tushunarli matnda qaytarish
- [ ] 1.1.4 Ikkala oqimdan bittadan kadr olish API (ko'rish maydonini yonma-yon solishtirish va `fov_match` belgisi uchun)
- [ ] 1.1.5 Sub manzili ixtiyoriy: kiritilmasa, barcha vazifalar main dan ishlaydi
- [ ] 1.1.6 Parollar UI ro'yxatida yashirib ko'rsatiladi (RTSP manzilidagi va ONVIF)
- [ ] 1.1.7 Kamera o'zgarganda Redis orqali xabar (qo'shildi / o'zgardi / o'chirildi)
- [ ] 1.1.8 API testlari

## 1.2. ONVIF

- [ ] 1.2.1 WS-Discovery: LAN dagi ONVIF qurilmalarni qidirish (IP, ishlab chiqaruvchi, model; allaqachon qo'shilganlari belgilanadi)
- [ ] 1.2.2 Ulanish (IP, port, login, parol): qurilma ma'lumoti — ishlab chiqaruvchi, model, seriya raqami
- [ ] 1.2.3 Profillar ro'yxati: har profil uchun o'lcham, FPS, kodek va `GetStreamUri` orqali RTSP manzil
- [ ] 1.2.4 Main/sub ni avtomatik taklif qilish (eng katta o'lcham — main, kichigi — sub)
- [ ] 1.2.5 RTSP manzilga login/parolni qo'shish (kamera manzilni ularsiz qaytarsa)
- [ ] 1.2.6 Natijani `cameras` ga RTSP manzillari sifatida saqlash (video doim RTSP orqali olinadi)
- [ ] 1.2.7 "ONVIF orqali yangilash" API: manzillar/profillarni qayta o'qish
- [ ] 1.2.8 Xatolar: autentifikatsiya, ONVIF o'chirilgan — tushunarli matn; kamera soati farq qilsa — kamera vaqtini (`GetSystemDateAndTime`) o'qib, farqni hisobga olib ulanish (kamera vaqti hisobotlarda ishlatilmaydi)
- [ ] 1.2.9 Mavjud kameralarda sinash; qidirish tarmoqda ishlamasa — IP ni qo'lda kiritish yo'li

**Sinalgan kameralar** (to'ldiriladi):

| Ishlab chiqaruvchi / model | ONVIF qidirish | Profillar | Main | Sub | Izoh |
|---|---|---|---|---|---|
| | | | | | |

## 1.3. Dekod benchmark (backend tanlash)

- [ ] 1.3.1 Benchmark skripti: VAAPI, NVDEC, CPU — stsenariylar: 15 sub; 15 sub + 5 main; 15 sub + 10 main; 15 sub + 15 main
- [ ] 1.3.2 O'lchash: CPU %, GPU %, VRAM, haqiqiy FPS, tushib qolgan kadrlar, 10 daqiqa barqarorlik
- [ ] 1.3.3 Dekoderning o'zida 10 fps ga siyraklashtirish ishlashini tekshirish
- [ ] 1.3.4 Natijalarni quyidagi jadvalga yozish va backend tanlash (main va sub uchun turli backend ham bo'lishi mumkin)
- [ ] 1.3.5 Yetmasa: kamerada H.265 / past FPS variantlarini sinash va yozib qo'yish

**Benchmark natijalari** (to'ldiriladi):

| Backend | Sub | Main | CPU % | GPU % | VRAM | Kadr tushishi | Xulosa |
|---|---|---|---|---|---|---|---|
| VAAPI | 15 | 15 | | | | | |
| NVDEC | 15 | 15 | | | | | |
| CPU | 15 | 15 | | | | | |

**Tanlangan backend:** main — _______ , sub — _______

## 1.4. video-service

- [ ] 1.4.1 Dekod backend abstraksiyasi (bir xil interfeys: ochish, kadr olish, yopish)
- [ ] 1.4.2 Har oqim uchun dekod oqimi (thread); kadrlar 10 fps
- [ ] 1.4.3 Shared memory halqa-bufer: har kamera va oqim (main/sub) uchun segment, sarlavha (kadr raqami, vaqt, o'lcham, format), yozuvchi/o'quvchi kutubxonasi
- [ ] 1.4.4 **Talab bo'yicha ochish:** sub — har faol kamerada doim; main — iste'molchi bo'lsa (kamerada vazifa yoqilgan va tahlil oqimi main, sahifa ko'rilyapti, snapshot so'raldi); iste'molchilar Redis'da muddatli yozuv bilan qayd etiladi; iste'molchi qolmasa kutish vaqtidan keyin yopiladi
- [ ] 1.4.5 Sub yo'q yoki ishlamayotgan bo'lsa — sub iste'molchilariga main kadrlari beriladi (kichraytirib)
- [ ] 1.4.6 Avto qayta ulanish (ortib boruvchi kutish bilan); holat har oqim uchun Redis'ga: `online / connecting / offline / error`
- [ ] 1.4.7 "Qotib qolgan oqim" nazorati: N soniya kadr kelmasa qayta ulanish
- [ ] 1.4.8 Kamera qo'shish/o'zgartirish/o'chirishni qayta ishga tushirmasdan qo'llash
- [ ] 1.4.9 Kamera uzilgan oraliqlarni `coverage_gaps` ga yozish (sabab: kamera)
- [ ] 1.4.10 Shared memory va talab bo'yicha ochish uchun testlar

## 1.5. camera-logic skeleti va JPEG

- [ ] 1.5.1 Boshqaruvchi: har faol kamera uchun `camera-logic` processini ishga tushirish/to'xtatish, yiqilsa qayta ko'tarish
- [ ] 1.5.2 Shared memory'dan kerakli oqim kadrini o'qish
- [ ] 1.5.3 JPEG tayyorlash: grid profili (sub dan, ≈640×360, 3–5 fps), sahifa profili (main dan, 720p–1080p, 10 fps)
- [ ] 1.5.4 "Faqat ko'rayotgan bo'lsa" mexanizmi: tomoshabin yo'q bo'lsa JPEG tayyorlanmaydi; sahifa ochilganda main iste'molchisi qayd etiladi
- [ ] 1.5.5 Xabar formati: sarlavha (kamera, oqim, kadr raqami, vaqt, metadata joyi) + JPEG — bitta ikkilik xabarda

## 1.6. WebSocket

- [ ] 1.6.1 `/ws/grid`: mijoz ko'rayotgan kameralar ro'yxatiga obuna bo'ladi (sahifa almashganda yangilanadi)
- [ ] 1.6.2 `/ws/camera/:id`: bitta kamera, sahifa profili (main)
- [ ] 1.6.3 Sekin mijoz uchun eski kadrlarni tashlab yuborish (navbat to'lib ketmasin)
- [ ] 1.6.4 Oqimlar holati o'zgarishini ham shu kanaldan yuborish

## 1.7. Frontend

- [ ] 1.7.1 `/settings/cameras`: ro'yxat (main/sub holati bilan), tahrirlash, o'chirish (tasdiqlash bilan), sudrab tartiblash
- [ ] 1.7.2 Qo'shish oynasi — **RTSP** yorlig'i (default): nom, main va sub manzillari, har biri uchun "Tekshirish" (kodek/o'lcham/FPS)
- [ ] 1.7.3 Qo'shish oynasi — **ONVIF** yorlig'i: "Tarmoqdan qidirish" ro'yxati yoki IP ni qo'lda kiritish → login/parol → profillar → main/sub tanlash → RTSP manzillari avtomatik to'ldiriladi
- [ ] 1.7.4 Saqlashdan oldin main va sub kadrlari yonma-yon + "Ko'rish maydoni bir xil" belgisi (`fov_match`)
- [ ] 1.7.5 Tahrirlashda "ONVIF orqali yangilash" tugmasi (ONVIF bilan qo'shilgan kameralar uchun)
- [ ] 1.7.6 `/` grid (sub): 1×1 / 2×2 / 3×3 / 4×4 almashtirgich, pagination, rejim va sahifa URL'da (`?grid=&page=`)
- [ ] 1.7.7 Grid katagi: video (canvas), kamera nomi, ulanish holati belgisi, uzilganda "aloqa yo'q" ko'rinishi
- [ ] 1.7.8 To'liq ekran rejimi
- [ ] 1.7.9 Katakka **ikki marta bosish** → `/cameras/:id`
- [ ] 1.7.10 `/cameras/:id` (main): katta video preview, kamera ma'lumotlari (oqimlar, kodek, o'lcham, ONVIF qurilma ma'lumoti), orqaga qaytish
- [ ] 1.7.11 Kamera yo'q bo'lganda bo'sh holat ("Kamera qo'shing")

---

## Qabul mezonlari

- [ ] Bosqichdagi barcha sahifalar dizayn tekshiruv ro'yxatidan (PLAN.md 4.1.6) o'tdi va o'z URL'i bilan ishlaydi
- [ ] Kamera RTSP manzillari bilan qo'shiladi, tahrirlanadi, o'chiriladi — servislarni qayta ishga tushirmasdan
- [ ] Kamera ONVIF orqali topiladi va main/sub manzillari avtomatik to'ldiriladi
- [ ] Grid sub oqimdan, kamera sahifasi main oqimdan ochiladi
- [ ] Sahifa yopilgandan keyin (vazifasi yo'q yoki tahlil oqimi sub bo'lgan kamerada) main oqim yopiladi
- [ ] 15 ta kamera grid'da 1 soat barqaror ko'rinadi (4×4)
- [ ] Kamera kabeli uzilib qayta ulanganda o'zi tiklanadi, oraliq `coverage_gaps` ga yozilgan
- [ ] Benchmark jadvali to'ldirilgan, backend tanlangan
- [ ] Hech kim ko'rmayotganda JPEG tayyorlanmaydi (CPU yuklamasi pasayadi)

---

## Jurnal (to'xtash nuqtalari)

| Sana | Oxirgi bajarilgan qadam | Keyingi qadam | Izoh / muammo |
|---|---|---|---|
| | | | |
