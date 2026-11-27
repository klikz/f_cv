# Bosqich 8 — Barqarorlik va ishga topshirish

**Holat:** 🟡 Dasturiy qismi tugagan; nosozlik va 7 kunlik sinovlar serverda
**Bog'liqlik:** Bosqich 0–7
**Maqsad:** tizim nazoratsiz, uzluksiz ishlaydi; nosozliklardan o'zi tiklanadi; ma'lumot zaxiralanadi.

---

## 8.1. Nazorat va avto tiklanish

- [x] 8.1.1 Barcha processlar heartbeat'ini kuzatuvchi nazoratchi; javob bermagan process qayta ishga tushiriladi (systemd WatchdogSec=30 + sd_notify; camera-logic bolalari supervisor tomonidan)
- [x] 8.1.2 systemd: kompyuter yonganda avtomatik ishga tushish, to'g'ri tartib (DB, Redis → servislar)
- [x] 8.1.3 Har servis qayta ishga tushganda holatini tiklashi (joriy smena sanoqlari, ochiq intervallar, train navbati)
- [x] 8.1.4 Train paytida yiqilish: job "xato" holatiga o'tadi, inference bayrog'i olinadi (sanash abadiy to'xtab qolmaydi)
- [x] 8.1.5 Servis o'chgan oraliqlar `coverage_gaps` ga yoziladi (sabab: servis)
- [x] 8.1.6 Barcha fayllar (snapshot, model, engine, sozlama) atomar yoziladi (vaqtinchalik fayl → nomini almashtirish)
- [x] 8.1.7 Elektr o'chib yonganda: yarim qurilgan engine'larni tozalash, to'xtagan train uchun "davom ettirish / qayta boshlash" tanlovi
- [x] 8.1.8 Server vaqti keskin sakrasa ogohlantirish va jurnalga yozish

## 8.2. Engine'ni avto qayta qurish

- [x] 8.2.1 Ishga tushganda drayver/TensorRT versiyasini engine'lardagi yozuv bilan solishtirish
- [x] 8.2.2 Mos kelmasa: saqlangan `.pt` dan navbat bilan qayta qurish, UI da jarayonni ko'rsatish
- [x] 8.2.3 Qayta qurilmaguncha tegishli mahsulot "model tayyor emas" deb ko'rinadi

## 8.3. Loglar

- [x] 8.3.1 Log fayllarini aylantirish (hajm/kun bo'yicha), eski loglarni tozalash
- [x] 8.3.2 Xato loglarini UI da ko'rish (oxirgi xatolar ro'yxati)
- [x] 8.3.3 Muhim hodisalar jurnali: kamera uzilishi, train, servis qayta ishga tushishi

## 8.4. Disk va resurs monitoringi

- [x] 8.4.1 Disk bandligi `/settings/general` va yuqori panelda; chegaradan oshsa ogohlantirish
- [x] 8.4.2 Papkalar bo'yicha hajm: snapshotlar, datasetlar, modellar
- [x] 8.4.3 GPU harorati, VRAM, CPU, RAM ko'rsatkichlari

## 8.5. Zaxira nusxa

- [x] 8.5.1 Kunlik `pg_dump` (systemd timer), saqlash muddati
- [x] 8.5.2 Modellar va sozlamalar zaxirasi
- [x] 8.5.3 **Tiklashni sinab ko'rish** (zaxiradan bo'sh bazaga) (backup.sh --verify: 25 jadval, 2676 sanoq tiklandi)
- [x] 8.5.4 Zaxira holati UI da (oxirgi muvaffaqiyatli nusxa vaqti)

## 8.6. Nosozlik sinovlari

- [x] 8.6.1 Har processni majburan o'chirish → o'zi tiklanishini tekshirish (camera-logic:2 kill -9 → supervisor 2 s da qayta ko'tardi)
- [ ] 8.6.2 Kamera kabelini uzish / kamerani o'chirib yoqish ← HAQIQIY KAMERADA (soxta kamerada sinaldi)
- [ ] 8.6.3 Redis'ni qayta ishga tushirish ← SUDO KERAK
- [ ] 8.6.4 PostgreSQL'ni qayta ishga tushirish ← SUDO KERAK
- [ ] 8.6.5 Internetni uzish (faqat Telegram to'xtashi kerak) ← TELEGRAM TOKENI BILAN
- [ ] 8.6.6 Kompyuterni to'satdan o'chirib yoqish → hammasi o'zi ishga tushishi ← SERVERDA (systemd + BIOS)
- [ ] 8.6.7 Brauzerni uzoq ochiq qoldirish (grid 24 soat) — xotira o'smasligi ← UZOQ SINOV

| Sinov | Natija | Tiklanish vaqti | Izoh |
|---|---|---|---|
| 2026-11-27 | 8.8.3 | 8.6, 8.7 (serverda) | Zaxira va tiklash sinovi muvaffaqiyatli |

## 8.7. Uzoq muddatli sinov

- [ ] 8.7.1 7 kun uzluksiz ishlatish ← SERVERDA 7 KUN
- [ ] 8.7.2 Xotira sizishi yo'qligini tekshirish (har process RAM / VRAM o'sishi) ← SERVERDA
- [ ] 8.7.3 Kadr tushishi va kechikish statistikasi ← SERVERDA
- [ ] 8.7.4 Topilgan muammolarni tuzatish va qayta sinash ← SERVERDA

## 8.8. Hujjatlar

- [x] 8.8.1 O'rnatish qo'llanmasi (yangi serverga noldan)
- [x] 8.8.2 Foydalanuvchi qo'llanmasi o'zbek tilida: kamera qo'shish, vazifa sozlash, mahsulot belgilash va train, sanoqni tuzatish
- [x] 8.8.3 Nosozliklarni bartaraf etish bo'yicha qisqa yo'riqnoma

---

## Qabul mezonlari

- [ ] 7 kun uzluksiz ishladi, qo'lda aralashuvsiz
- [ ] Barcha nosozlik sinovlari o'tdi (jadval to'ldirilgan)
- [ ] Zaxiradan tiklash sinab ko'rilgan
- [ ] Kompyuter o'chib yonganda tizim o'zi ishga tushadi
- [ ] Qo'llanmalar yozilgan

---

## Jurnal (to'xtash nuqtalari)

| Sana | Oxirgi bajarilgan qadam | Keyingi qadam | Izoh / muammo |
|---|---|---|---|
| | | | |
