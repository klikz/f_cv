# Bosqich 4 — Mahsulot sanash

**Holat:** 🟡 Dasturiy qismi tugagan; haqiqiy liniya sinovi va to'liq GPU benchmark qolgan
**Bog'liqlik:** Bosqich 2 va 3
**Maqsad:** kamerada faol mahsulotlar tanlanadi, ular aniqlanadi, chiziqni kesib o'tganda sanaladi, har sanoqqa ramkali snapshot saqlanadi. Noaniq sanoqlar tuzatiladi. GPU yuklamasi o'lchangan.

---

## 4.1. inference-server

- [x] 4.1.1 `camera-logic` ↔ `inference-server` aloqa usulini tanlash va yozib qo'yish (so'rov: kamera, kadr raqami, ROI kesimi, mahsulot modellari ro'yxati) (kadrlar shm'da, so'rov/javob Redis ro'yxatlari orqali — kadr nusxalanmaydi)
- [x] 4.1.2 Engine menejeri: yuklash, tushirish, faqat kerakli engine'lar xotirada; VRAM hisobi
- [x] 4.1.3 Oldindan ishlov: kadrdan ROI atrofini kesish → 640 ga keltirish
- [x] 4.1.4 Batch: bir xil engine uchun turli kameralar kadrlarini birlashtirish (maksimal kutish vaqti bilan)
- [x] 4.1.5 Natijani kadr koordinatasiga qaytarish; javobni kameraga yuborish
- [x] 4.1.6 "Inference to'xtatilsin" bayrog'iga bo'ysunish (train paytida engine'lar tushiriladi, keyin qayta yuklanadi)
- [x] 4.1.7 Statistika Redis'ga: sekundiga inference, navbat uzunligi, VRAM, kechikish
- [x] 4.1.8 Engine versiyasi mos kelmasa ogohlantirish (avto qayta qurish — 8-bosqich)

## 4.2. Sanash logikasi (camera-logic)

- [x] 4.2.1 Mavjudlik filtri: ROI da harakat ham, faol track ham bo'lmasa so'rov yuborilmaydi
- [x] 4.2.2 So'rovlar `inference_fps` tezligida, kameraning **tahlil oqimi** kadridan
- [x] 4.2.3 Faqat ROI poligon ichidagi aniqlashlarni qoldirish
- [x] 4.2.4 Turli mahsulot modellari ramkalarini birlashtirish (ustma-ust tushganlari — bitta obyekt)
- [x] 4.2.5 ByteTrack; har track uchun mahsulotlar bo'yicha ishonch ballarini yig'ish
- [x] 4.2.6 Chiziq kesish: kesma kesishuvi, burchak tekshiruvi, minimal track yoshi, ikki tomonda minimal masofa (histerezis)
- [x] 4.2.7 Bitta track — bitta sanoq; teskari o'tish siyosati (e'tiborsiz / ayirish / alohida)
- [x] 4.2.8 Mahsulotni aniqlash: eng yuqori ball + o'lcham tekshiruvi
- [x] 4.2.9 "Noaniq" qarori: farq kichik yoki ishonch past bo'lsa — nomzodlar ro'yxati bilan
- [x] 4.2.10 `count_events` ga yozish (smena va smena sanasi bilan)
- [x] 4.2.11 Snapshot: tahlil oqimi kadri + sanalgan mahsulot **ramkasi va nomi**; `data/snapshots/<kamera>/<sana>/...` (toza kadr saqlanadi, ramka UI/Telegram'da chiziladi)
- [x] 4.2.12 Redis'ga hodisa (UI va Telegram uchun)
- [x] 4.2.13 Qayta ishga tushganda joriy smena sanoqlarini bazadan tiklash
- [x] 4.2.14 Testlar: chiziq kesish geometriyasi (to'g'ri o'tish, chiziq bo'ylab yurish, orqaga qaytish, chiziq ustida titrash)

## 4.3. Sanash sozlamalari sahifasini to'ldirish

- [x] 4.3.1 Migratsiya: `counting_config_products`
- [x] 4.3.2 Faol mahsulotlarni tanlash (faqat faol modeli borlar), model versiyasini ko'rsatish
- [x] 4.3.3 GPU yuklama ko'rsatkichi: shu kamera qo'shadigan yuklama va umumiy byudjet
- [x] 4.3.4 Jonli test rejimi: aniqlashlar va "sanalgan bo'lardi" belgisi bazaga yozilmasdan ko'rinadi

## 4.4. AI qatlami va grid holati

- [x] 4.4.1 Aniqlash metadata'si kadr bilan birga WebSocket xabarida
- [x] 4.4.2 Overlay: mahsulot ramkasi, nomi, track; sanoq paytida chiziqning yonib-o'chishi
- [x] 4.4.3 Grid'da metadata faqat "AI Vision" yoqilganda yuboriladi; tahlil oqimi main bo'lsa `fov_match` qoidasi bo'yicha
- [x] 4.4.4 Grid katagida holat yozuvi: joriy smenada jami sanoq; katta katakda mahsulotlar kesimida va "noaniq" soni
- [x] 4.4.5 Kamera sahifasida joriy smena statistikasi va oxirgi sanoqlar lentasi

## 4.5. Sanoqlar jurnali

- [x] 4.5.1 `/counts`: ro'yxat/galereya; filtrlar (kamera, mahsulot, holat, sana, smena) — URL'da
- [x] 4.5.2 `/counts/:eventId`: snapshot, ma'lumotlar, nomzodlar
- [x] 4.5.3 Tuzatish: mahsulotni o'zgartirish; yolg'on sanoqni bekor qilish; asl qiymat saqlanadi
- [x] 4.5.4 "Datasetga qo'shish" tugmasi
- [x] 4.5.5 "Noaniq" sanoqlar uchun tezkor ko'rib chiqish rejimi

## 4.6. Aniqlikni tekshirish

- [x] 4.6.1 Migratsiya: `manual_counts`
- [x] 4.6.2 UI: vaqt oralig'i va mahsulot bo'yicha qo'lda sanalgan sonni kiritish
- [x] 4.6.3 Solishtirish: tizim soni, qo'lda son, farq, foiz

## 4.7. O'rganuvchi yordamchilar

- [x] 4.7.1 O'lcham oralig'ini o'rganish: har (kamera, mahsulot) uchun tasdiqlangan sanoqlardan
- [x] 4.7.2 Chalkashadigan juftliklar statistikasi (tuzatishlardan) → `/models` da "qayta train qilish" taklifi

## 4.8. GPU yuklama benchmark

- [ ] 4.8.1 Eng yomon holatni sinash: barcha sanash kameralari × faol mahsulotlar ← JARAYONDA (2 kamera × 4 mahsulot: ~33 inference/s, kechikish ~27 ms; 15 kamera × 6 mahsulot sinalmagan)
- [x] 4.8.2 Yuklama oshganda inference fps ni avtomatik pasaytirish va UI da ogohlantirish
- [ ] 4.8.3 Natijalarni jadvalga yozish ← JARAYONDA (yuqoridagi qisman natija)

| Holat | Kameralar | Faol mahsulotlar | Inference/s | GPU % | VRAM | Kechikish |
|---|---|---|---|---|---|---|
| Odatiy | 2026-11-27 | 4.7.2 | 4.8.1, 4.9 (haqiqiy liniya) | Sintetik liniya: toza oynada 42/42 (100%), TV43/TV55 o'lcham bo'yicha ajratildi | | |
| Eng yomon | | | | | | |

**Xulosa:** bir vaqtda nechta mahsulot modeli sig'adi: _______

## 4.9. Liniyada sinov

- [ ] 4.9.1 Bitta liniyada bir smena davomida sinash, qo'lda sanoq bilan solishtirish ← HAQIQIY LINIYADA (sintetik liniyada bajarildi: 42/42)
- [ ] 4.9.2 Xatolarni tahlil qilish (o'tkazib yuborilgan, yolg'on, chalkash) va sozlash ← HAQIQIY LINIYADA
- [ ] 4.9.3 Natijani yozish: aniqlik ____ % ← HAQIQIY LINIYADA (sintetik: 100%, 2 kamera × 3 sikl, chalkashlik 0)
- [ ] 4.9.4 Bir-biriga tegib ketgan mahsulotlar holatini alohida tekshirish (ikkalasi ham sanaladimi, ID almashib ketmaydimi); kerak bo'lsa tracker parametrlari va chiziq joyini sozlash ← HAQIQIY LINIYADA

---

## Qabul mezonlari

- [ ] Bosqichdagi barcha sahifalar dizayn tekshiruv ro'yxatidan (PLAN.md 4.1.6) o'tdi va o'z URL'i bilan ishlaydi
- [ ] Mahsulot chiziqni kesganda bir marta sanaladi, snapshotda ramka va nom bor
- [ ] Chiziq bo'ylab yurgan yoki chiziq ustida to'xtab turgan mahsulot sanalmaydi / ikki marta sanalmaydi
- [ ] Bir liniyada 5–6 model aralash o'tganda har biri o'z nomi bilan sanaladi
- [ ] Noaniq sanoqni tuzatish ishlaydi va hisobga ta'sir qiladi
- [ ] Train paytida sanash to'xtaydi, keyin o'zi tiklanadi; oraliq `coverage_gaps` da
- [ ] Liniyada aniqlik maqsadi: ≥ 99%
- [ ] GPU benchmark jadvali to'ldirilgan

---

## Jurnal (to'xtash nuqtalari)

| Sana | Oxirgi bajarilgan qadam | Keyingi qadam | Izoh / muammo |
|---|---|---|---|
| | | | |
