# Bosqich 8 — Barqarorlik va ishga topshirish

**Holat:** ⬜ Boshlanmagan
**Bog'liqlik:** Bosqich 0–7
**Maqsad:** tizim nazoratsiz, uzluksiz ishlaydi; nosozliklardan o'zi tiklanadi; ma'lumot zaxiralanadi.

---

## 8.1. Nazorat va avto tiklanish

- [ ] 8.1.1 Barcha processlar heartbeat'ini kuzatuvchi nazoratchi; javob bermagan process qayta ishga tushiriladi
- [ ] 8.1.2 systemd: kompyuter yonganda avtomatik ishga tushish, to'g'ri tartib (DB, Redis → servislar)
- [ ] 8.1.3 Har servis qayta ishga tushganda holatini tiklashi (joriy smena sanoqlari, ochiq intervallar, train navbati)
- [ ] 8.1.4 Train paytida yiqilish: job "xato" holatiga o'tadi, inference bayrog'i olinadi (sanash abadiy to'xtab qolmaydi)
- [ ] 8.1.5 Servis o'chgan oraliqlar `coverage_gaps` ga yoziladi (sabab: servis)
- [ ] 8.1.6 Barcha fayllar (snapshot, model, engine, sozlama) atomar yoziladi (vaqtinchalik fayl → nomini almashtirish)
- [ ] 8.1.7 Elektr o'chib yonganda: yarim qurilgan engine'larni tozalash, to'xtagan train uchun "davom ettirish / qayta boshlash" tanlovi
- [ ] 8.1.8 Server vaqti keskin sakrasa ogohlantirish va jurnalga yozish

## 8.2. Engine'ni avto qayta qurish

- [ ] 8.2.1 Ishga tushganda drayver/TensorRT versiyasini engine'lardagi yozuv bilan solishtirish
- [ ] 8.2.2 Mos kelmasa: saqlangan `.pt` dan navbat bilan qayta qurish, UI da jarayonni ko'rsatish
- [ ] 8.2.3 Qayta qurilmaguncha tegishli mahsulot "model tayyor emas" deb ko'rinadi

## 8.3. Loglar

- [ ] 8.3.1 Log fayllarini aylantirish (hajm/kun bo'yicha), eski loglarni tozalash
- [ ] 8.3.2 Xato loglarini UI da ko'rish (oxirgi xatolar ro'yxati)
- [ ] 8.3.3 Muhim hodisalar jurnali: kamera uzilishi, train, servis qayta ishga tushishi

## 8.4. Disk va resurs monitoringi

- [ ] 8.4.1 Disk bandligi `/settings/general` va yuqori panelda; chegaradan oshsa ogohlantirish
- [ ] 8.4.2 Papkalar bo'yicha hajm: snapshotlar, datasetlar, modellar
- [ ] 8.4.3 GPU harorati, VRAM, CPU, RAM ko'rsatkichlari

## 8.5. Zaxira nusxa

- [ ] 8.5.1 Kunlik `pg_dump` (systemd timer), saqlash muddati
- [ ] 8.5.2 Modellar va sozlamalar zaxirasi
- [ ] 8.5.3 **Tiklashni sinab ko'rish** (zaxiradan bo'sh bazaga)
- [ ] 8.5.4 Zaxira holati UI da (oxirgi muvaffaqiyatli nusxa vaqti)

## 8.6. Nosozlik sinovlari

- [ ] 8.6.1 Har processni majburan o'chirish → o'zi tiklanishini tekshirish
- [ ] 8.6.2 Kamera kabelini uzish / kamerani o'chirib yoqish
- [ ] 8.6.3 Redis'ni qayta ishga tushirish
- [ ] 8.6.4 PostgreSQL'ni qayta ishga tushirish
- [ ] 8.6.5 Internetni uzish (faqat Telegram to'xtashi kerak)
- [ ] 8.6.6 Kompyuterni to'satdan o'chirib yoqish → hammasi o'zi ishga tushishi
- [ ] 8.6.7 Brauzerni uzoq ochiq qoldirish (grid 24 soat) — xotira o'smasligi

| Sinov | Natija | Tiklanish vaqti | Izoh |
|---|---|---|---|
| | | | |

## 8.7. Uzoq muddatli sinov

- [ ] 8.7.1 7 kun uzluksiz ishlatish
- [ ] 8.7.2 Xotira sizishi yo'qligini tekshirish (har process RAM / VRAM o'sishi)
- [ ] 8.7.3 Kadr tushishi va kechikish statistikasi
- [ ] 8.7.4 Topilgan muammolarni tuzatish va qayta sinash

## 8.8. Hujjatlar

- [ ] 8.8.1 O'rnatish qo'llanmasi (yangi serverga noldan)
- [ ] 8.8.2 Foydalanuvchi qo'llanmasi o'zbek tilida: kamera qo'shish, vazifa sozlash, mahsulot belgilash va train, sanoqni tuzatish
- [ ] 8.8.3 Nosozliklarni bartaraf etish bo'yicha qisqa yo'riqnoma

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
