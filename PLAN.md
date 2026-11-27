# F_CV — Mahsulot sanash va uskuna ish vaqtini hisoblash tizimi

Reja hujjati (2-tahrir). Kod Ubuntu serverda yoziladi; bu hujjat arxitektura, qarorlar va bosqichlarni belgilaydi.

---

## 0. Qabul qilingan talablar

| Parametr | Qiymat |
|---|---|
| Server | Ubuntu, i7-12700K (12 yadro, UHD 770 iGPU), RTX 3070 (8GB VRAM), 32GB RAM |
| Kameralar | maks. 15 ta, LAN; **ikki oqim: asosiy (main, 1080p/4MP, 25fps) va sub (substream)**; kodek noma'lum (H.264/H.265 ikkalasi qo'llanadi) |
| Ulanish | **RTSP — asosiy usul** (main va sub manzillari qo'lda kiritiladi); **ONVIF — qo'shimcha** (tarmoqdan qidirish, oqim manzillarini avtomatik olish) |
| Kamera ↔ obyekt | bitta kamera = bitta liniya yoki bitta uskuna |
| Mahsulotlar | katta (TV, muzlatgich, kir yuvish mashinasi), konveyer sekin, ~200 tur; qutili ham, qutisiz ham |
| Liniyada | 5–6 xil model ketma-ket aralash o'tishi mumkin; har biri o'z nomi bilan aniqlanadi |
| O'xshashlik | o'lchami bir xil / dizayni farqli va dizayni bir xil / o'lchami farqli mahsulotlar bor |
| **Train** | **har bir mahsulot alohida train qilinadi; mahsulotlar umumiy (bitta ko'p klassli modelda) train qilinmaydi** |
| Detektor | YOLO26 (Ultralytics) → TensorRT FP16 engine |
| Sanash | ROI poligon + chiziq; mahsulot chiziqni kesib o'tadi; yo'nalish chapdan yoki o'ngdan |
| Sanash aniqligi | imkoni boricha maksimal |
| Sanash snapshoti | har sanoqqa rasm, sanalgan mahsulot **kontur (ramka) bilan belgilangan** |
| Train paytida | inference to'xtatilishi mumkin |
| Uskunalar | press, stanok; harakat ko'rinadi; odam ROI ga deyarli kirmaydi; 10 fps tahlil yetarli |
| Uskuna holati | harakat bor = "ishlayapti" (bo'sh aylanish ham ish hisoblanadi); snapshot **kerak emas** |
| Sikl | 1 ta to'liq tushib-ko'tarilish yoki belgilangan joy N marta aylanishi; sikl vaqti real-time o'lchanadi va etalon bo'ladi |
| Smenalar | 08:00–19:00 va 19:00–08:00; UI orqali o'zgartiriladi |
| Telegram | bot tayyor; chat avtomatik UI ga chiqadi; checkbox matritsa; sanash xabari har mahsulotga alohida + snapshot. Chuqur rejalashtirish — ishga tushgandan keyin |
| Tarmoq | lokal ishlaydi; internet faqat Telegram uchun |
| DB | PostgreSQL lokal (5432), Redis lokal |
| UI | o'zbek tilida, auth yo'q; asosan **serverning o'zidan** (server monitori va brauzeri) ochiladi; belgilashni 1 kishi qiladi |
| Yorug'lik | kechasi ham doimiy; kameralar doim rangli rejimda (IR rejim yo'q) |
| Mahsulotlar oralig'i | asosan bo'sh joy bor, lekin bir-biriga tegib ketish holati bo'lishi mumkin |
| Vaqt | hamma hisob **faqat server vaqti** bo'yicha; kamera vaqti hisobga olinmaydi |
| Katalog | tayyor ro'yxat yo'q — mahsulotlar UI da qo'lda kiritiladi |
| Integratsiya | boshqa tizimlar (1C, ERP) bilan kerak emas |
| Tarmoq | kameralar va server bitta tarmoqda |
| Elektr | **UPS yo'q** — to'satdan o'chishga chidamlilik kerak |
| Saqlash | doimiy, disk cheklovi yo'q |
| Video yozish / video fayl manba | **kerak emas** |

---

## 1. Arxitektura qarorlari

### 1.1. Processlar va GPU xotirasi

8GB VRAM asosiy cheklov, shuning uchun **CUDA ishlatadigan processlar soni minimal**:

| Process | Soni | GPU | Vazifasi |
|---|---|---|---|
| `video-service` | 1 | dekod backend'ga qarab | asosiy va sub oqimlarni dekod qiladi (thread), kadrlarni shared memory'ga yozadi |
| `inference-server` | 1 | RTX (CUDA) | TRT engine menejeri, batch inference; **holatsiz** (tracker bu yerda emas) |
| `camera-logic` | har kameraga 1 | yo'q (CPU) | tracker, chiziq kesish, sanash, harakat/sikl, JPEG tayyorlash |
| `trainer` | 1 | RTX (train paytida) | train navbati, TRT eksport |
| `api` | 1 | yo'q | FastAPI REST + WebSocket |
| `telegram-service` | 1 | yo'q | polling + outbox |

### 1.2. Kamera ulanishi: RTSP va ONVIF

**RTSP (asosiy usul):** kamera qo'shishda ikki manzil kiritiladi — asosiy oqim (main) va sub oqim. Sub ixtiyoriy: kiritilmasa, hamma ish asosiy oqimdan bajariladi.

**ONVIF (qo'shimcha usul):**
- **Tarmoqdan qidirish:** WS-Discovery orqali LAN dagi ONVIF kameralar ro'yxati (IP, ishlab chiqaruvchi, model). Server kameralar bilan bitta tarmoq segmentida bo'lishi kerak; aks holda IP qo'lda kiritiladi.
- Login/parol kiritilgach: qurilma ma'lumoti (ishlab chiqaruvchi, model, seriya raqami), profillar ro'yxati, har profil uchun **RTSP manzil** (`GetStreamUri`), o'lcham, FPS, kodek.
- Profillardan main va sub avtomatik taklif qilinadi (eng katta o'lcham — main, kichigi — sub); foydalanuvchi o'zgartirishi mumkin.
- Natija baribir **RTSP manzillari** sifatida saqlanadi — video har doim RTSP orqali olinadi; ONVIF faqat sozlashni osonlashtiradi.
- "ONVIF orqali yangilash" tugmasi: kamera IP yoki manzillari o'zgarsa, qayta o'qib oladi.
- PTZ boshqaruvi, ONVIF hodisalari kerak emas.

### 1.3. Tahlil oqimini tanlash (kamera bo'yicha)

Har kamera uchun bitta **tahlil oqimi** tanlanadi: `main` yoki `sub`. U shu kameradagi **ikkala vazifaga** (sanash va uskuna) birdek amal qiladi.

- Tanlov kamera sahifasida, vazifalar ro'yxati ustida (oqim o'lchami ko'rsatiladi).
- **Main tanlansa** — ROI, chiziq va zonalar **main kadri ustiga** chiziladi va ikkala vazifa tahlili main dan bajariladi.
- **Sub tanlansa** — hammasi **sub kadri ustiga** chiziladi va tahlil sub dan bajariladi.
- Koordinatalar tahlil oqimi kadriga nisbatan (0–1) saqlanadi.
- Default: **main** (maksimal aniqlik). Kamerada sub bo'lmasa — faqat main.
- **Oqimni almashtirish:** tasdiqlash oynasi — shu kameraning barcha vazifalari shakllari qayta chiziladi (main va sub ko'rish maydoni har doim ham bir xil emas); sanash yoqilgan bo'lsa qo'shimcha ogohlantirish: modellar boshqa oqim rasmlarida train qilingan bo'lsa, aniqlik tushishi mumkin.

| Qayerda | Oqim |
|---|---|
| Grid | sub (sub bo'lmasa — main kichraytirilgan) |
| Kamera sahifasi | main |
| Sozlash sahifalari, sanash inference'i, sanoq snapshoti, harakat va sikl tahlili | kameraning tahlil oqimi |
| Dataset snapshotlari | kameraning tahlil oqimi (train va inference bir xil oqimda bo'lishi uchun) |

**Talab bo'yicha dekod:**
- Sub oqim har faol kamera uchun doim dekod qilinadi (grid uchun, arzon).
- Main oqim faqat kerak bo'lganda ochiladi: kamerada vazifa yoqilgan va tahlil oqimi main bo'lsa (doim), kamera sahifasi ko'rilayotgan bo'lsa, yoki qo'lda snapshot olinsa (qisqa muddatga). Kerak bo'lmay qolsa, kutish vaqtidan keyin yopiladi.

**Grid'da AI Vision qatlami:** grid sub dan ko'rsatiladi, tahlil esa main da bo'lishi mumkin. Shuning uchun kamera qo'shishda main va sub kadrlari yonma-yon ko'rsatiladi va foydalanuvchi **"ko'rish maydoni bir xil"** belgisini qo'yadi (`fov_match`):
- `fov_match` = ha → main ga chizilgan shakllar va aniqlashlar sub kadri ustida to'g'ri chiziladi;
- `fov_match` = yo'q → AI Vision yoqilganda shu kamera katagi main dan (kichraytirilgan) ko'rsatiladi.

### 1.4. Dekodlash

Dekod backend'i abstraksiya qilinadi va **1-bosqich benchmarkida tanlanadi**:

1. **VAAPI (Intel UHD 770 iGPU)** — birinchi nomzod: RTX VRAM'ini umuman band qilmaydi. (BIOS'da iGPU yoqilgan bo'lishi kerak.)
2. **NVDEC (RTX)** — bitta process ichida, bitta CUDA konteksti; ~1.5–2 GB VRAM oladi (taxmin).
3. **CPU** — zaxira; 12700K qisman ko'tara oladi.

- **Benchmark natijasi (1-bosqich):** NVDEC chiqarildi — PyAV har oqimga alohida CUDA konteksti ochadi (~400 MB VRAM/oqim). Tanlov: **CPU** (VAAPI — serverda iGPU bo'lsa). 15 sub + 15 main ≈ 2 yadro (sintetik oqimda).
- Kadrlar dekoderning o'zida **10 fps gacha siyraklashtiriladi**, keyin xotiraga ko'chiriladi (25 fps ni to'liq ko'chirish ortiqcha).
- Kamera qo'shilganda har oqim uchun `ffprobe` orqali kodek/o'lcham/FPS avto aniqlanadi va UI da ko'rsatiladi.
- Har oqimga **bitta RTSP ulanish**, faqat `video-service` ulanadi (boshqa hech bir komponent kameraga ulanmaydi).
- Avto-reconnect, holat har oqim uchun alohida: `online / connecting / offline / error`.

### 1.5. Brauzerga video

go2rtc/WebRTC ishlatilmaydi. Barcha video serverdan **JPEG + metadata bitta WebSocket xabarida** keladi (kadr va bbox doim mos):

- **Grid:** sub oqimdan, ≈640×360, 3–5 fps.
- **Kamera sahifasi:** main oqimdan, 720p–1080p, 10 fps.
- **Sozlash sahifalari:** kameraning tahlil oqimidan, 10 fps.
- JPEG faqat **kimdir ko'rayotgan** kameralar uchun tayyorlanadi (lazy).
- ROI, chiziq, bbox, sanoq — brauzerda canvas qatlamida chiziladi.

### 1.6. Model strategiyasi — har mahsulotga alohida model

**Qoida:** bitta mahsulot = bitta alohida YOLO26 modeli (bitta klassli detektor) = alohida train = alohida TensorRT engine. Ko'p klassli umumiy model yo'q.

- **Yangi mahsulot qo'shish boshqa mahsulotlar modeliga tegmaydi.**
- **Negativ namunalar:** A mahsulotni train qilganda datasetdagi boshqa mahsulotli va bo'sh konveyerli rasmlar *fon* (yorliqsiz) sifatida qo'shiladi. Bu umumiy train emas — model baribir bitta mahsulotniki — lekin o'xshash mahsulotlarni chalkashtirmaslik uchun shart.
- **Versiyalar:** `model_versions(product_id, camera_id?)`. `camera_id` bo'sh — umumiy (barcha kameralar rasmlaridan); to'ldirilgan — **shu kameraga xos engine** (faqat shu kamera rasmlaridan).
- **Qutili/qutisiz:** bitta mahsulot modeli ikkala ko'rinishni o'rganadi; annotatsiyada "qadoq holati" atributi saqlanadi, tayyorlik indikatori ikkala holat bo'yicha rasm sonini ko'rsatadi.
- **Model o'lchami:** default YOLO26n (kerak bo'lsa mahsulot bo'yicha YOLO26s), kirish — ROI atrofidan kesilgan kadr → 640.

**Kamerada ishlashi:** kameraga **faol mahsulotlar ro'yxati** biriktiriladi (liniyada ketadigan 5–6 model). Har kadrda shu mahsulotlarning engine'lari ishlaydi.

**Bir obyektga bir nechta model javob bersa (chalkashlikni hal qilish):**
1. Turli modellarning ustma-ust tushgan bbox'lari (IoU yuqori) bitta fizik obyektga birlashtiriladi; tracker shu birlashgan bbox bilan ishlaydi.
2. Track davomida har mahsulot bo'yicha ishonch ballari yig'iladi → chiziq kesilganda eng yuqori yig'indi g'olib.
3. **O'lcham tekshiruvi:** kamera qo'zg'almas, shuning uchun har mahsulotning chiziq oldidagi bbox o'lchami barqaror. Har (kamera, mahsulot) uchun kutilgan o'lcham oralig'i tasdiqlangan sanoqlardan o'rganiladi — dizayni bir xil, o'lchami farqli mahsulotlarni ajratadi.
4. G'olib va ikkinchi o'rin orasidagi farq kichik bo'lsa yoki ishonch past bo'lsa → **"Noaniq"** deb sanaladi (nomzodlar ro'yxati bilan), foydalanuvchi keyin to'g'rilaydi.
5. Tuzatishlar statistikasi **chalkashadigan juftliklarni** ko'rsatadi → UI "A ni B rasmlari negativ sifatida qayta train qilish"ni taklif qiladi.

**Resurs byudjeti (taxmin, 4-bosqichda benchmark bilan aniqlanadi):**
- Yuklama = Σ kameralar (inference fps × faol mahsulotlar). Eng yomon holat: 15 × 5 fps × 6 = 450 inference/s — YOLO26n uchun 3070 chegarasiga yaqin.
- **Mavjudlik filtri:** ROI da harakat ham, faol track ham bo'lmasa modellar ishlamaydi → real yuklama ancha past.
- Bir xil mahsulot modelini ishlatgan kameralar bitta engine'ni bo'lishadi va kadrlari batch qilinadi.
- Engine menejeri: faqat faol mahsulotlar yuklanadi; VRAM byudjeti va yuklama UI da ko'rsatiladi; limitdan oshsa ogohlantiradi va inference fps ni avtomatik pasaytiradi.
- ⚠️ Har mahsulotga alohida model — ko'p klassli modelga nisbatan bir necha barobar ko'p GPU talab qiladi. Agar benchmark yetishmovchilik ko'rsatsa, variantlar qayta muhokama qilinadi.

**Engine'ni avto qayta qurish:** drayver/TensorRT versiyasi o'zgarsa engine yaroqsiz bo'ladi → tizim buni aniqlab, saqlangan `.pt` dan qayta quradi.

### 1.7. Sanash logikasi

1. Faol mahsulot modellari → faqat ROI poligon ichidagi aniqlashlar → birlashtirish (1.6).
2. Tracker **ByteTrack** — `camera-logic` processida, har kamera uchun alohida holat. Inference 5 fps (sozlanadi, 1–10), kameraning **tahlil oqimi** kadridan.
3. Chiziq A→B nuqtalar bilan chiziladi; UI da **yo'nalish strelkasi**. Sozlama: `A→B` / `B→A` / `ikkalasi (alohida hisob)`.
4. Track nuqtasi (markaz yoki pastki-markaz — sozlanadi) chiziq **kesmasini** kesib o'tganda:
   - harakat vektori va chiziq normali orasidagi burchak ≤ `max_angle` (default 60°);
   - track kamida `min_track_frames` kadr yashagan;
   - histerezis: nuqta chiziqning ikki tomonida ham kamida `min_distance` px masofada ko'rilgan bo'lishi kerak (titrash va chiziq yonida tug'ilgan tracklardan himoya).
5. Bitta track faqat **bir marta** sanaladi.
6. Teskari kesib o'tish: `e'tiborsiz` / `ayirish` / `alohida hisoblash`.
7. Tavsiya (UI da maslahat sifatida): chiziq mahsulot kadrda **to'liq ko'rinadigan** joyga qo'yiladi (kadrga kirib kelayotgan katta obyektning bbox markazi sun'iy siljiydi).
8. Sanoq paytida: `count_events` ga yoziladi (smena shu paytda aniqlanib yoziladi) + **snapshot**: tahlil oqimi kadri, unda sanalgan mahsulot **kontur (ramka) va nomi bilan belgilangan** + Redis pub/sub → UI va Telegram.

**Sanoqni tuzatish:**
- "Noaniq" sanoqlar va istalgan sanoq UI da ko'riladi (snapshot bilan): mahsulotni o'zgartirish yoki yolg'on sanoqni bekor qilish. Asl qiymat saqlanadi (audit).
- Tuzatilgan snapshot bir tugma bilan datasetga qo'shiladi.

**Aniqlikni tekshirish (videosiz):** UI da "qo'lda sanoq bilan solishtirish" — foydalanuvchi vaqt oralig'i uchun haqiqiy sonni kiritadi, tizim farqni ko'rsatadi. Snapshotlar yolg'on sanoqlarni ko'rsatadi; o'tkazib yuborilganlar shu solishtirish orqali aniqlanadi.

**Sanalmagan oraliqlar jurnali (`coverage_gaps`):** kamera uzilgan, train ketgan yoki servis o'chgan vaqtlar yoziladi; hisobotlarda ma'lumot to'liq emasligi ko'rinadi.

*Ixtiyoriy (keyinroq):* hech bir model tanimagan, lekin chiziqdan o'tgan obyektni fon ayirish orqali "noma'lum obyekt" deb qayd etish — yangi mahsulotlar uchun rasm yig'ishga ham xizmat qiladi.

### 1.8. Uskuna ish vaqti va sikl logikasi

Bu vazifada **snapshot saqlanmaydi**, faqat hisob.

**Harakat signali** (CPU, 10 fps, kameraning **tahlil oqimidan**):
- ROI crop → kulrang → kichraytirish → frame-differencing + MOG2 → **harakat foizi**.
- **Nazorat zonasi (ixtiyoriy):** uskunadan tashqaridagi qo'zg'almas joy; press zarbidan kamera titrasa global harakat ayiriladi.
- **Istisno zonalari** (masalan miltillovchi lampa).

**Holat mashinasi:** `ISHLAYAPTI ⇄ TO'XTAGAN`; kamera uzilsa — `NOMA'LUM`. (Train paytida ham ishlayveradi — GPU kerak emas.)
- Harakat bor = ishlayapti (bo'sh aylanish ham).
- `motion_threshold`, `min_on_sec`, `min_off_sec` — UI da sozlanadi.
- Natija: `equipment_intervals`.

**Sikl aniqlash rejimlari:**
1. **Tayanch holat bo'yicha (asosiy):** ROI ning boshlang'ich ("uy") ko'rinishi eslab qolinadi. Signal = joriy kadrning tayanch ko'rinishdan farqi. **Sikl = tayanchdan chiqib, unga K marta qaytish** (press: K=1 — bitta tushib-ko'tarilish; aylanuvchi qism: K=2 — ikki aylanish). Tayanch kadr UI da tugma bilan olinadi yoki avtomatik (eng ko'p uchraydigan tinch holat) taklif qilinadi.
2. **Harakat cho'qqilari bo'yicha (muqobil):** silliqlangan harakat signalida cho'qqilar; sikl = K cho'qqi. **Avto-aniqlash:** autokorrelyatsiya orqali davr topilib, parametrlar taklif qilinadi.
3. **Shablon o'rgatish (keyinroq, kerak bo'lsa):** foydalanuvchi signal grafigida 2–3 siklni belgilaydi → DTW shablon moslash.

**Etalon sikl vaqti:** dastlabki N sikl medianasi avtomatik hisoblanadi yoki qo'lda kiritiladi/o'zgartiriladi.

**Ko'rsatkichlar:** sikllar soni, oxirgi/o'rtacha sikl vaqti, etalondan og'ish, mikro-to'xtashlar (sikl > etalon × koeffitsient), ish vaqti %, to'xtash vaqti.

**Signalni saqlash:** xom signal faqat Redis'da (oxirgi bir necha soat — UI grafigi va sozlash uchun). PostgreSQL ga faqat **daqiqalik yig'indi**, intervallar va sikl hodisalari yoziladi.

### 1.9. Train

- Train birligi — **bitta mahsulot** (ixtiyoriy: bitta kamera uchun). Bir nechta mahsulot tanlansa, navbatga alohida-alohida job bo'lib tushadi.
- **Navbat:** bir vaqtda bitta job. Navbat ishlayotganda **mahsulot inference to'xtatiladi** (engine'lar tushiriladi); video va uskuna vazifasi (CPU) davom etadi. Oraliq `coverage_gaps` ga yoziladi. Navbat bo'shagach inference avtomatik yoqiladi.
- Rejalashtirish: "hozir" yoki "belgilangan vaqtda".
- Bosqichlar: `navbatda → dataset tayyorlash → train → validatsiya → TensorRT eksport → tayyor` (yoki `xato / bekor qilindi`).
- Taxminiy davomiylik: bitta mahsulot uchun train 5–15 daqiqa + engine qurish 3–5 daqiqa (benchmarkda aniqlanadi).
- Yangi versiya avtomatik ishga tushmaydi: metrikalar joriy versiya bilan solishtiriladi → **"Faollashtirish"**, **rollback**.

**Dataset va belgilash:**
- Snapshot olish (kameraning **tahlil oqimidan** — train va inference bir xil oqimda bo'lishi uchun; oqim rasm bilan birga saqlanadi): qo'lda (tugma) va **avto-yig'ish** (ROI da harakat bo'lganda har N soniyada; sanoq snapshotlari).
- Belgilash: bbox + mahsulot tanlash (qidiruv, oxirgi ishlatilganlar) + qadoq holati.
- **Avto-belgilash (iterativ):** yangi mahsulotning dastlabki ~30 rasmi qo'lda belgilanadi → tez qoralama model → qolgan rasmlarni model taklif qiladi, foydalanuvchi tasdiqlaydi/tuzatadi.
- **Tayyorlik indikatori** har mahsulot bo'yicha: belgilangan obyektlar soni (tavsiya ≥100–150), qutili/qutisiz taqsimoti, kameralar bo'yicha taqsimot, negativ rasmlar soni.

### 1.10. Telegram (hozir faqat asos)

- Alohida `telegram-service`, **long polling**.
- `my_chat_member` → bot qo'shilgan chat/guruh UI da paydo bo'ladi; chiqarilsa — "faol emas".
- **Outbox:** xabarlar avval `notification_outbox` ga yoziladi; internet yo'q bo'lsa navbatda kutadi. Tizimning qolgan qismi Telegramga bog'liq emas.
- **Kengaytiriladigan xabar turlari registri.** Boshlang'ich turlar:

| Xabar turi | Vazifa | Tarkib |
|---|---|---|
| Mahsulot sanaldi | sanash | mahsulot, kamera, vaqt, smena jami + **snapshot** (har mahsulotga alohida xabar) |
| Uskuna to'xtadi (> N daq) / qayta ishga tushdi | uskuna | matn (snapshotsiz) |
| Kamera uzildi / tiklandi | tizim | matn |
| Train tugadi / xato | tizim | metrikalar |

- UI: har chat uchun **kamera × vazifa × xabar turi** checkbox matritsasi.
- Hisobotlar va batafsil logika — loyiha ishga tushgandan keyin rejalashtiriladi.

### 1.11. Smenalar

- `shifts` jadvali `effective_from` bilan versiyalanadi — o'zgartirish faqat kelajakka ta'sir qiladi.
- Smena va smena sanasi **hodisa yozilayotgan paytda** aniqlanib, hodisaning o'ziga yoziladi (eski ma'lumot o'zgarmaydi).
- Yarim tundan o'tuvchi smena **boshlangan sanaga** tegishli.
- Smenalar orasida bo'shliq bo'lsa — hodisa "smenadan tashqari" deb belgilanadi.
- Vaqt: bazada UTC, UI da Asia/Tashkent.

### 1.12. Offline-first

- Frontend to'liq lokal build (CDN yo'q, shriftlar ichida).
- YOLO26 boshlang'ich og'irliklari o'rnatishda bir marta yuklanadi; Ultralytics'ning internetga murojaatlari o'chiriladi.
- Telegram — yagona tashqi bog'liqlik.

### 1.13. Saqlash

- Disk cheklovi yo'q; sanoq snapshotlari doimiy saqlanadi (taxmin: ~2–3 GB/kun). Disk bandligi UI da monitoring uchun ko'rsatiladi.
- Ishga tushirish: **systemd** unitlar (Docker'siz), Python venv.

### 1.14. Server — ish stansiyasi va elektr uzilishlari

**UI serverning o'zidan ochiladi:**
- Monitor **ona plataga (Intel iGPU)** ulanadi — ekran va brauzer RTX ni band qilmasligi uchun; RTX faqat inference va train uchun qoladi.
- Ubuntu desktop + Chrome; kompyuter yonganda brauzer avtomatik grid sahifasini ochadi (ixtiyoriy kiosk rejim).
- Brauzer yuklamasi (16 katak) 1-bosqich benchmarkida hisobga olinadi.

**UPS yo'qligi sababli:**
- BIOS: elektr qaytganda kompyuter o'zi yonadi ("Restore on AC power loss = Power On").
- PostgreSQL: `fsync` va `synchronous_commit` yoqilgan (default) — o'chishda baza buzilmaydi.
- Fayllar (snapshot, model, engine, sozlama) **atomar** yoziladi: avval vaqtinchalik fayl, keyin nomini almashtirish — yarim yozilgan fayl qolmaydi.
- Train to'xtab qolsa: oxirgi saqlangan epoch'dan **davom ettirish** (resume) yoki qayta boshlash tanlovi.
- Yarim qurilgan engine o'chirib tashlanadi va qayta quriladi.
- O'chgan vaqt `coverage_gaps` ga yoziladi (servis heartbeat'idagi oxirgi vaqtdan yonguncha).
- **Tavsiya:** kichik UPS (10–15 daqiqa) — to'g'ri o'chirish uchun yetarli; bo'lsa NUT orqali avtomatik to'g'ri o'chirish qo'shiladi.

**Server vaqti:** hisobotlar faqat server vaqtiga tayanadi. Internet bor paytda `chrony` vaqtni sinxronlaydi; internet yo'q paytda server o'z soati bilan ishlaydi. Yuqori panelda server vaqti ko'rsatiladi; vaqt keskin sakrasa (masalan BIOS soati xato bo'lsa) — ogohlantirish va jurnalga yozuv.

---

## 2. Tizim sxemasi

```
                    ┌──────────── Brauzer (React, o'zbek UI) ────────────┐
                    │  Grid / Kamera sahifasi: JPEG + metadata (WS)      │
                    └───────────────────────▲────────────────────────────┘
                                            │ REST / WebSocket
                                   ┌────────┴────────┐
                                   │  api (FastAPI)  │
                                   └───┬─────────┬───┘
                          PostgreSQL ◄─┘         └─► Redis (holat, pub/sub, navbat, signal)
                                                        ▲
 Kameralar ─RTSP─► ┌───────────────┐  shared   ┌────────┴─────────┐
   (main + sub)    │ video-service │──memory──►│ camera-logic ×15 │  tracker, sanash,
                   │ (dekod, 10fps)│  (kadr)   │      (CPU)       │  harakat/sikl, JPEG
                   └───────────────┘     │     └────────▲─────────┘
                                         ▼              │ aniqlashlar
                               ┌──────────────────┐     │
                               │ inference-server │─────┘
                               │ (RTX: mahsulot   │        ┌─────────┐   ┌──────────────────┐
                               │  engine'lari)    │        │ trainer │   │ telegram-service │─► internet
                               └──────────────────┘        └─────────┘   └──────────────────┘
```

| Komponent | Texnologiya |
|---|---|
| Backend API | Python 3.12, FastAPI, SQLAlchemy 2 + Alembic, Pydantic |
| Video | PyAV / GStreamer (VAAPI / NVDEC / CPU), OpenCV |
| Kamera qidirish | ONVIF: WS-Discovery + onvif-zeep (async) |
| ML | Ultralytics YOLO26, TensorRT, ByteTrack |
| Navbat/holat | Redis (pub/sub, streams, arq yoki RQ) |
| DB | PostgreSQL |
| Telegram | aiogram 3 |
| Frontend | React + TypeScript + Vite, React Router, TanStack Query, Tailwind + shadcn/ui, Konva.js, ECharts |
| Ishga tushirish | systemd |

### Papka tuzilmasi

```
f_cv/
├── backend/
│   ├── app/                # api, models, schemas, services, core
│   ├── vision/
│   │   ├── video/          # video-service: dekod backend'lari, oqimlarni talab bo'yicha ochish, shared memory
│   │   ├── onvif/          # ONVIF: tarmoqdan qidirish, profillar va RTSP manzillarini o'qish
│   │   ├── inference/      # inference-server, engine menejeri, batch
│   │   ├── logic/          # camera-logic: tracker, chiziq kesish, birlashtirish, snapshot
│   │   └── motion/         # harakat signali, holat mashinasi, sikl rejimlari
│   ├── training/           # dataset tayyorlash, train, TRT eksport, registry
│   ├── telegram/           # bot, outbox, xabar turlari registri
│   └── alembic/
├── frontend/
├── deploy/                 # systemd, .env.example
├── data/                   # (gitignore) snapshots/, datasets/, models/, engines/
├── plan/                   # bosqichlar bo'yicha batafsil, belgilab boriladigan qadamlar
└── PLAN.md
```

---

## 3. Ma'lumotlar bazasi (asosiy jadvallar)

| Jadval | Mazmuni |
|---|---|
| `cameras` | nom, faol, tartib, ulanish usuli (`rtsp` / `onvif`), main_rtsp_url, sub_rtsp_url (ixtiyoriy), analysis_stream (`main` / `sub`), fov_match, ONVIF: host, port, login, parol, ishlab chiqaruvchi, model, seriya raqami, profil tokenlari |
| `camera_streams` | camera_id, turi (`main` / `sub`), kodek, o'lcham, fps, holat, oxirgi xato |
| `camera_tasks` | camera_id, task_type (`counting` / `equipment`), enabled |
| `counting_configs` | camera_id, roi_polygon, line (A,B), direction, reverse_policy, max_angle, track_point, inference_fps |
| `counting_config_products` | config_id, product_id, model_version_id, kutilgan bbox o'lcham oralig'i |
| `products` | katalog: kod, nom, kategoriya (faqat guruhlash uchun), rasm |
| `count_events` | camera_id, product_id, original_product_id, status (`tasdiqlangan` / `noaniq` / `tuzatilgan` / `bekor`), nomzodlar, direction, confidence, bbox, ts, shift_id, shift_date, snapshot_path |
| `manual_counts` | camera_id, product_id, vaqt oralig'i, qo'lda sanalgan son (aniqlikni solishtirish) |
| `coverage_gaps` | camera_id, task_type, sabab (`kamera` / `train` / `servis`), start_ts, end_ts |
| `equipment_configs` | camera_id, roi_polygon, control_zone, exclude_zones, motion_threshold, min_on/off, cycle_mode (`home` / `peaks` / `template`), returns_per_cycle, home_reference, reference_cycle_sec, auto_reference |
| `equipment_intervals` | camera_id, state, start_ts, end_ts, shift_id, shift_date |
| `cycle_events` | camera_id, start_ts, end_ts, duration, deviation, shift_id, shift_date |
| `equipment_minute_stats` | camera_id, daqiqa, o'rtacha harakat, ish soniyalari |
| `dataset_images` | camera_id, stream (`main` / `sub`), fayl, manba (`qo'lda` / `avto` / `sanoq`), holat |
| `annotations` | image_id, product_id, bbox, qadoq holati, holat (`avto` / `tasdiqlangan`) |
| `model_versions` | product_id, camera_id (ixtiyoriy), model o'lchami, metrikalar, pt_path, engine_path, trt/drayver versiyasi, status, aktiv |
| `training_jobs` | product_id, camera_id (ixtiyoriy), parametrlar, status, bosqich, epoch, boshlangan/tugagan, ETA, xato |
| `training_metrics` | job_id, epoch, loss'lar, mAP50, mAP50-95 |
| `shifts` | nom, boshlanish, tugash, effective_from |
| `telegram_chats` | chat_id, nom, turi, faol |
| `telegram_subscriptions` | chat_id, camera_id, task_type, message_type, params |
| `notification_outbox` | chat_id, turi, payload, rasm yo'li, status, urinishlar |
| `settings` | umumiy sozlamalar |

---

## 4. UI sahifalari

1. **Bosh sahifa — grid:** 1×1 / 2×2 / 3×3 / 4×4, pagination. **Ikki marta bosish** → kamera sahifasi. Har katakda video ustida **yoqilgan vazifalar holati real-time yozilib turadi** (joriy smena bo'yicha, WebSocket orqali yangilanadi):
   - **umumiy:** kamera nomi, ulanish holati (online / offline);
   - **Mahsulot sanash:** sanalgan mahsulotlar jami soni; joy yetsa (1×1, 2×2) mahsulotlar kesimida ham (masalan "Muzlatgich A — 42, Muzlatgich B — 17"), "noaniq" sanoqlar soni;
   - **Uskuna ish vaqti:** joriy holat (ishlayapti / to'xtagan), ishlagan vaqt, sikllar soni; joy yetsa oxirgi sikl vaqti va ish vaqti %;
   - ikkala vazifa yoqilgan bo'lsa ikkalasi ham ko'rsatiladi; vazifa yoqilmagan bo'lsa — yozuv yo'q;
   - 3×3 va 4×4 rejimda faqat asosiy raqamlar (qisqa ko'rinish), matn o'lchami katak o'lchamiga moslashadi;
   - train sababli sanash to'xtagan bo'lsa katakda "Train ketmoqda" belgisi.

   **"AI Vision" checkbox** (grid sahifasi yuqorisida). Yoqilganda **barcha kameralar** ustida AI qatlami chiziladi:
   - **sanash vazifasi:** ROI poligon, kesib o'tish chizig'i va yo'nalish strelkasi, aniqlangan mahsulotlar ramkasi va nomi (track bilan), sanoq paytida chiziqning qisqa yonib-o'chishi;
   - **uskuna vazifasi:** ROI, nazorat/istisno zonalari, ROI ichida **harakat bo'layotgan joylar** (yarim shaffof bo'yalgan sohalar), holatga qarab ROI rangi (yashil — ishlayapti, qizil — to'xtagan);
   - o'chirilganda — faqat toza video va vazifa holati yozuvlari (ular AI Vision'ga bog'liq emas, doim ko'rinadi);
   - holat URL'da (`/?grid=3&page=2&ai=1`) va brauzerda eslab qolinadi;
   - kameraning tahlil oqimi main bo'lsa, qatlam sub dagi grid ustida `fov_match` qoidasi bo'yicha ko'rsatiladi (1.3);
   - qatlam brauzerda canvas'da chiziladi (kadr bilan birga kelgan metadata asosida, 1.5); server aniqlash/harakat metadata'sini grid'ga **faqat AI Vision yoqilganda** yuboradi;
   - harakat sohalari uchun `camera-logic` harakat maskasidan soddalashtirilgan konturlar (yoki past o'lchamli maska) tayyorlaydi;
   - kichik kataklarda (3×3, 4×4) yozuvlar qisqaradi, chiziqlar qalinligi katak o'lchamiga moslashadi.
   - Kamera sahifasida ham xuddi shu qatlam uchun alohida o'tkazgich bor (default — yoqilgan).
2. **Kamera sahifasi:** jonli video + overlay; **tahlil oqimi tanlovi (main / sub)** — ikkala vazifa uchun bitta; vazifalar checkbox bilan (Mahsulot sanash, Uskuna ish vaqti); yoqilgan vazifaning **"Sozlash"** tugmasi faollashadi; joriy statistika.
3. **Sanash sozlamalari:** kameraning tahlil oqimi kadri ustida ROI va chiziq chizish, yo'nalish strelkasi, faol mahsulotlar va ularning model versiyalari, parametrlar, jonli test rejimi, GPU yuklama ko'rsatkichi.
4. **Uskuna sozlamalari:** kameraning tahlil oqimi kadri ustida ROI, nazorat/istisno zonalari, jonli signal grafigi + threshold, sikl rejimi (tayanch holat / cho'qqilar / avto), tayanch kadr olish, etalon sikl vaqti.
5. **Kameralar boshqaruvi:** qo'shish ikki usulda — **RTSP** (default: main va sub manzillarini kiritish) yoki **ONVIF** (tarmoqdan qidirish → login/parol → profillardan main/sub tanlash); har oqim uchun ulanish testi va kodek/o'lcham/FPS avto aniqlash; main va sub kadrlari yonma-yon va "ko'rish maydoni bir xil" belgisi; tahrirlash, "ONVIF orqali yangilash", o'chirish, tartib.
6. **Mahsulotlar katalogi.**
7. **Dataset va belgilash:** snapshot olish, avto-yig'ish, bbox chizish, avto-belgilash, tayyorlik indikatori.
8. **Train monitoringi:** navbat, status/bosqich, epoch X/Y, boshlangan vaqt, o'tgan va qolgan vaqt (ETA), loss/mAP grafiklari, GPU yuklama/VRAM/harorat, loglar, bekor qilish.
9. **Modellar:** mahsulot bo'yicha versiyalar, metrikalar, faollashtirish/rollback, chalkashadigan juftliklar, VRAM byudjeti.
10. **Sanoqlar jurnali:** snapshot galereyasi, "noaniq" sanoqlarni tuzatish, bekor qilish, datasetga qo'shish, qo'lda sanoq bilan solishtirish.
11. **Hisobotlar (asos):** kun/smena/soat bo'yicha sanoqlar, uskuna ish/to'xtash vaqti, sikllar, sanalmagan oraliqlar. Batafsil — keyin.
12. **Telegram:** bot holati, chatlar, obuna matritsasi, outbox holati.
13. **Sozlamalar:** smenalar, umumiy parametrlar, disk bandligi.

### 4.1. Dizayn talablari

Dizayn — loyihaning alohida ustuvor yo'nalishi. To'rt asosiy talab: **chiroyli, tushunarli, ixcham, juda qulay**. Har sahifa quyidagi qoidalar va 4.1.6 dagi tekshiruv ro'yxati bo'yicha qabul qilinadi.

#### 4.1.1. Tushunarli

- Har sahifada **bitta asosiy amal** ko'zga tashlanadi (asosiy tugma bitta); ikkinchi darajali amallar — kamroq urg'u bilan yoki "…" menyuda.
- Atamalar butun tizimda bir xil (bitta lug'at fayli): "Tahlil oqimi", "ROI hududi", "Kesib o'tish chizig'i", "Noaniq sanoq" va h.k. Texnik atama ishlatilsa — yonida (?) belgisi va qisqa izoh.
- Holat har doim ko'rinadi va **rang + ikon + matn** bilan ifodalanadi (faqat rangga tayanilmaydi).
- Bo'sh holatlar yo'l ko'rsatadi: "Kamera yo'q → Kamera qo'shish", "ROI chizilmagan → Sozlash".
- Xato xabarlari nima bo'lganini va nima qilish kerakligini aytadi ("Kameraga ulanib bo'lmadi: login yoki parol xato").
- Sozlash sahifalari bosqichma-bosqich: 1) ROI chizing → 2) Chiziq chizing → 3) Mahsulotlarni tanlang → 4) Sinab ko'ring; har qadam holati belgilanadi.

#### 4.1.2. Ixcham

- Ma'lumot zichligi yuqori, lekin tartibli: kichik bo'shliqlar, aniq guruhlash, ortiqcha bezaksiz.
- Kamdan-kam ishlatiladigan parametrlar **"Qo'shimcha sozlamalar"** ostiga yig'iladi; standart qiymatlar o'ylangan, ko'p holatda o'zgartirish shart emas.
- Jadvallar ixcham qatorli, kerakli ustunlar tanlanadi; uzun ro'yxatlarda virtual scroll.
- Grid kataklarida faqat eng kerakli raqamlar (4-bo'lim, 1-band).
- Video sahifalarida video eng katta joyni egallaydi; panellar yon tomonda va yig'iladi.

#### 4.1.3. Juda qulay

- **Kamroq bosish:** ko'p ishlatiladigan amallar bir bosishda (qayta bosish, sahifa almashtirmasdan); inline tahrirlash (modal o'rniga, iloji bo'lsa).
- **Klaviatura:** belgilash va jurnal sahifalari to'liq klaviatura bilan ishlaydi (keyingi/oldingi, tasdiqlash, mahsulot tanlash raqamlari); `?` tugmasi qisqa tugmalar ro'yxatini ochadi.
- **Buyruqlar oynasi (Ctrl+K):** kamera, mahsulot, sahifani nomidan tez topib ochish.
- **Hech narsa yo'qolmaydi:** saqlanmagan o'zgarish bo'lsa ogohlantirish; o'chirish va bekor qilish amallarida "Qaytarish" (undo) toast'i; xavfli amallarda tasdiqlash.
- **Tez javob:** har amalga darhol vizual javob (optimistic update, yuklanish ko'rsatkichi); sahifalar 1 soniyadan tez ochiladi.
- **Eslab qolish:** oxirgi tanlangan grid rejimi, filtrlar, yig'ilgan panellar, oxirgi ishlatilgan mahsulotlar.
- **Chizish vositalari:** nuqtalarni sudrash, magnitlanish (chiziq uchlari va poligon yopilishi), undo/redo, zoom/pan, klaviatura (Esc, Delete, Ctrl+Z/Y).
- Belgilash sahifasi — eng ko'p vaqt o'tkaziladigan joy (200 mahsulot × 100+ ramka, 1 kishi): har ramka maksimal 2–3 harakatda (chizish → raqam tugmasi bilan mahsulot → keyingi rasm).

#### 4.1.4. Chiroyli

- **Komponentlar:** Tailwind CSS + shadcn/ui (Radix asosida), lucide ikonlar.
- **Dizayn tokenlari:** ranglar, masofa shkalasi (4px asos), radius, soyalar, shrift o'lchamlari — bitta joyda; komponentlarda "qo'lda" rang/o'lcham yozilmaydi.
- **Mavzu:** qorong'i — asosiy (server monitori, katta ekran), yorug' — o'tkazgich bilan; ikkalasi ham to'liq ishlangan.
- **Shrift:** Inter (loyiha ichida, internetsiz); raqamlar bir xil kenglikda (`tabular-nums`) — sanoq o'zgarganda matn sakramaydi.
- **Holat ranglari** hamma joyda bir xil: yashil — ishlayapti/online, sariq — ogohlantirish/noaniq, qizil — to'xtagan/offline, kulrang — o'chirilgan; ko'k — tanlangan/faol element.
- **Harakat (animatsiya):** qisqa va yumshoq (150–250 ms): sanoq o'zgarishi, panel ochilishi, toast; ortiqcha animatsiya yo'q.
- **Grafiklar:** ECharts, mavzu tokenlaridan rang oladi, bir xil uslubda.
- **AI qatlami** (ROI, chiziq, ramkalar): yupqa, toza chiziqlar, yarim shaffof to'ldirish, o'qiladigan yorliqlar (fon bilan), video ustida ham aniq ko'rinadi.

#### 4.1.5. Tuzilma va ekranlar

- Chap tomonda yig'iladigan yon menyu (guruhlar: Kuzatuv, Ma'lumotlar, AI, Sozlamalar); yuqorida sahifa nomi, "non bo'laklari" (breadcrumbs) va umumiy holat (GPU, train, Telegram, server vaqti).
- Grid uchun to'liq ekran rejimi (yon menyu va panel yashirinadi).
- Asosiy ekran — server monitori (1920×1080 va katta); planshetda ham buzilmaydi.
- Brauzer yorlig'ida sahifa nomi ("Kamera 3 — Sanash sozlamalari").

#### 4.1.6. Dizayn tekshiruv ro'yxati (har sahifa uchun)

- [ ] Asosiy amal bitta va aniq ko'rinadi
- [ ] Bo'sh, yuklanish va xato holatlari ishlangan
- [ ] Atamalar lug'atga mos, texnik atamalarda izoh bor
- [ ] Qorong'i va yorug' mavzuda ham chiroyli
- [ ] 1920×1080 da sig'adi, keraksiz scroll yo'q; planshetda buzilmaydi
- [ ] Klaviatura bilan ishlatish mumkin (fokus ko'rinadi)
- [ ] Saqlanmagan o'zgarish va xavfli amallar himoyalangan
- [ ] Sahifa o'z URL'i bilan ochiladi va yangilanganda holati saqlanadi
- [ ] Rang/masofa faqat dizayn tokenlaridan

#### 4.1.7. Dizayn jarayoni

1. **Dizayn tizimi sahifasi** (`/dev/ui`, faqat ishlab chiqishda): barcha komponentlar, ranglar, holatlar bir joyda — yangi sahifa shulardan yig'iladi.
2. **Asosiy ekranlar prototipi** kod yozishdan oldin: grid, kamera sahifasi, sanash sozlamalari, belgilash, train monitoringi. Siz ko'rib tasdiqlaysiz, keyin amalga oshiriladi.
3. Har bosqich oxirida sahifalar 4.1.6 ro'yxati bo'yicha tekshiriladi.

### 4.2. URL tuzilmasi (har sahifa alohida manzilda)

React Router ishlatiladi. Har sahifa o'z URL'iga ega: to'g'ridan-to'g'ri havola orqali ochiladi, sahifani yangilaganda shu joyda qoladi, brauzerning orqaga/oldinga tugmalari ishlaydi. Server barcha noma'lum yo'llarni frontend'ga qaytaradi (SPA fallback).

| URL | Sahifa |
|---|---|
| `/` | Bosh sahifa — grid. Rejim va sahifa URL'da: `/?grid=3&page=2` |
| `/cameras/:id` | Kamera sahifasi (preview + vazifalar) |
| `/cameras/:id/counting` | Shu kameraning sanash vazifasi sozlamalari |
| `/cameras/:id/equipment` | Shu kameraning uskuna vazifasi sozlamalari |
| `/settings/cameras` | Kameralar ro'yxati |
| `/settings/cameras/new` | Kamera qo'shish (RTSP / ONVIF yorlig'i URL'da: `?via=onvif`) |
| `/settings/cameras/:id/edit` | Kamerani tahrirlash |
| `/products` , `/products/:id` | Mahsulotlar katalogi, mahsulot kartasi |
| `/products/new` | Mahsulot qo'shish |
| `/dataset` | Dataset: rasmlar, tayyorlik indikatori |
| `/dataset/annotate/:imageId` | Belgilash sahifasi |
| `/training` , `/training/:jobId` | Train navbati, bitta train monitoringi |
| `/models` , `/models/:productId` | Modellar, mahsulot versiyalari |
| `/counts` , `/counts/:eventId` | Sanoqlar jurnali, bitta sanoq (snapshot, tuzatish) |
| `/reports` | Hisobotlar |
| `/telegram` | Telegram chatlar va obunalar |
| `/settings/shifts` | Smenalar |
| `/settings/general` | Umumiy sozlamalar |

- Filtrlar (sana, kamera, mahsulot, smena) ham URL query'da saqlanadi — havolani ulashsa, xuddi shu ko'rinish ochiladi.
- Mavjud bo'lmagan manzil uchun "Sahifa topilmadi" sahifasi.
- **Har ko'rinish o'z manzilida:** qo'shish/tahrirlash oynalari, yorliqlar (tabs), tanlangan element ham URL'da — masalan `/cameras/3/counting?step=line`, `/training/12?tab=logs`. Oyna ochiq holda sahifa yangilansa, oyna yana ochiladi; "orqaga" tugmasi oynani yopadi.
- Belgilash sahifasida keyingi/oldingi rasmga o'tish URL'ni almashtiradi (`/dataset/annotate/:imageId`), filtr esa saqlanadi — to'xtagan joydan davom etish oson.
- Har sahifaning brauzer yorlig'idagi nomi alohida.
- Ichki havolalar haqiqiy havola (`<a>`): o'rta tugma yoki Ctrl+bosish bilan yangi yorliqda ochiladi.
- URL nomlari inglizcha va barqaror (keyin o'zgartirilmaydi), sahifa matnlari o'zbekcha.

---

## 5. Bosqichlar va qabul mezonlari

Har bosqichning batafsil qadamlari (belgilab boriladigan) alohida fayllarda: [plan/README.md](plan/README.md).

| # | Bosqich | Qabul mezoni |
|---|---|---|
| 0 | **Infratuzilma + dizayn tizimi** — server muhiti (BIOS, iGPU monitor, chrony), repo, skelet, Alembic, Redis, config, systemd; dizayn tokenlari, `/dev/ui`, asosiy ekranlar prototipi | servislar ishga tushadi, health-check; prototiplar tasdiqlangan |
| 1 | **Kameralar + video** — CRUD (RTSP + ONVIF, ffprobe), video-service (main/sub, talab bo'yicha dekod), shared memory, JPEG/WS, grid (sub) + pagination, kamera sahifasi (main); **dekod benchmark (VAAPI / NVDEC / CPU): 15 sub + N main** | kamera RTSP va ONVIF orqali qo'shiladi; 15 kamera barqaror, uzilsa qayta ulanadi; backend tanlangan, CPU/GPU/VRAM o'lchangan |
| 2 | **Vazifalar karkasi + chizish** — kamera tahlil oqimi tanlovi (main/sub), vazifa checkbox'lari, Sozlash sahifalari, ROI/chiziq/zona chizish, AI Vision qatlami | konfiguratsiya saqlanadi va overlay'da ko'rinadi |
| 3 | **Katalog + dataset + train** — snapshot, belgilash, avto-belgilash, mahsulot bo'yicha train navbati, TRT eksport, model registry, train monitoringi | mahsulotni belgilab → train → engine UI orqali to'liq bajariladi; train vaqti o'lchangan |
| 4 | **Sanash** — inference-server, engine menejeri, mavjudlik filtri, birlashtirish, tracker, chiziq kesish, snapshot (kontur bilan), noaniq/tuzatish, coverage_gaps; **GPU yuklama benchmark** | real liniyada qo'lda sanoq bilan solishtirish; maqsad ≥ 99%, chalkashliklar tuzatish orqali kamayadi |
| 5 | **Uskuna ish vaqti** — harakat signali, holat mashinasi, sikl (tayanch holat + cho'qqilar/avto), etalon | ish vaqti va sikllar soni qo'lda kuzatuv bilan mos |
| 6 | **Telegram asosi** — polling, chatni avto aniqlash, outbox, obuna matritsasi, sanoq xabari + snapshot | internet uzilganda tizim ishlaydi, qaytganda xabarlar ketadi |
| 7 | **Smenalar + hisobotlar asosi** | smena kesimidagi raqamlar xom hodisalar bilan mos |
| 8 | **Barqarorlik** — watchdog, loglar, disk monitoringi, backup, engine avto qayta qurish | 7 kun uzluksiz ishlash |

---

## 6. Risklar

| Risk | Chora |
|---|---|
| Har mahsulotga alohida model GPU'ni to'ldirishi | mavjudlik filtri, YOLO26n, engine bo'lishish, fps avto pasaytirish; 4-bosqichda benchmark |
| O'xshash mahsulotlarning chalkashishi | negativ namunalar, ball yig'ish, o'lcham tekshiruvi, "noaniq" holat, chalkash juftliklarni qayta train |
| Dekod yuklamasi (main tanlangan vazifalarda 4MP doim ochiq) | vazifa uchun sub tanlash imkoni; VAAPI / NVDEC / CPU benchmark; kerak bo'lsa kamerada H.265 yoki past FPS |
| Sub oqim ko'rish maydoni main dan farq qilishi (kesilgan) | shakllar tahlil oqimining o'ziga chiziladi; grid uchun `fov_match` belgisi |
| Model bir oqimda train qilinib, boshqasida ishlatilishi | dataset rasmlari oqim bilan saqlanadi; oqim almashtirilganda ogohlantirish |
| ONVIF qidirish tarmoqda ishlamasligi (boshqa segment, multicast yopiq) | IP ni qo'lda kiritish; RTSP usuli doim ishlaydi |
| Hech bir model tanimagan mahsulot sanalmasligi | qo'lda sanoq bilan solishtirish; keyinroq "noma'lum obyekt" aniqlash |
| Press zarbidan kamera titrashi | nazorat zonasi; kamerani mustahkam o'rnatish |
| Yorug'lik o'zgarishi (kechasi ham doimiy yorug'lik, rangli rejim — xavf kam) | adaptiv fon, tayanch kadrni yangilash, tungi rasmlarni ham datasetga qo'shish |
| Bir-biriga tegib ketgan mahsulotlar bitta bo'lib ko'rinishi | datasetda tegib turgan holatlar alohida-alohida ramka bilan belgilanadi; tracker parametrlari shu holatda sinaladi; chiziq mahsulotlar eng ajralgan joyga qo'yiladi |
| To'satdan elektr o'chishi (UPS yo'q) | atomar fayl yozish, PostgreSQL fsync, train davom ettirish, BIOS avto yonish; UPS tavsiya etiladi |
| ONVIF ulanishi kamera soati noto'g'ri bo'lgani uchun rad etilishi | kamera vaqtini o'qib, farqni hisobga olib ulanish (hisobotga ta'sir qilmaydi) |
| Train paytida sanoq to'xtashi | rejalashtirish (tanaffus vaqti), coverage_gaps |
| 200 mahsulotni belgilash mehnati (1 kishi) | avto-yig'ish, iterativ avto-belgilash, sanoq snapshotlarini datasetga qo'shish, klaviatura bilan tez ishlash |

---

## 7. Keyinga qoldirilgan

- Telegram logikasi va hisobotlarni chuqur rejalashtirish — loyiha ishga tushgandan keyin.
- Saqlash muddati siyosati — hozircha doimiy.
- Shablon (DTW) sikl rejimi, "noma'lum obyekt" aniqlash — ehtiyoj tug'ilsa.
