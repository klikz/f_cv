# Bosqich 2 — Vazifalar karkasi va chizish vositalari

**Holat:** ⬜ Boshlanmagan
**Bog'liqlik:** Bosqich 1
**Maqsad:** kamera sahifasida vazifalar yoqib-o'chiriladi, har vazifaning sozlash sahifasi ochiladi, ROI / chiziq / zonalar chiziladi, saqlanadi va video ustida ko'rinadi. Hali aniqlash/hisoblash yo'q.

---

## 2.1. Baza va API

- [ ] 2.1.1 Migratsiya: `camera_tasks`, `counting_configs`, `equipment_configs` 
- [ ] 2.1.2 Vazifalarni yoqish/o'chirish API (kamera + vazifa turi)
- [ ] 2.1.3 Sanash sozlamalari API (o'qish/saqlash): ROI, chiziq, yo'nalish, teskari o'tish siyosati, burchak, kuzatuv nuqtasi, inference fps
- [ ] 2.1.4 Uskuna sozlamalari API: ROI, nazorat zonasi, istisno zonalari, threshold, min_on/off, sikl parametrlari
- [ ] 2.1.5 Tekshiruvlar: poligon kamida 3 nuqta, chiziq kadr ichida, qiymat chegaralari
- [ ] 2.1.6 Koordinatalar kameraning **tahlil oqimi** kadriga nisbatan **(0–1)** saqlanadi; default main; kamerada sub bo'lmasa faqat main
- [ ] 2.1.7 Sozlama o'zgarganda Redis xabari → `camera-logic` qayta ishga tushmasdan yangi sozlamani oladi
- [ ] 2.1.8 Kamera tahlil oqimini almashtirish API: shu kameraning barcha vazifalari shakllari tozalanadi (yoki tasdiq bilan saqlanadi), vazifalar "sozlanmagan" holatiga o'tadi

## 2.2. Kamera sahifasi — vazifalar

- [ ] 2.2.0 **Tahlil oqimi tanlovi** (main / sub, o'lchami bilan) — vazifalar ro'yxati ustida, ikkala vazifa uchun bitta; almashtirishda tasdiqlash oynasi va "shakllarni qayta chizing" ogohlantirishi
- [ ] 2.2.1 Vazifalar ro'yxati checkbox bilan: "Mahsulot sanash", "Uskuna ish vaqti"
- [ ] 2.2.2 Har vazifa yonida **"Sozlash"** tugmasi: checkbox o'chiq — tugma nofaol; yoqilgan — faol
- [ ] 2.2.3 "Sozlash" → `/cameras/:id/counting` yoki `/cameras/:id/equipment`
- [ ] 2.2.4 Vazifa yoqilgan, lekin sozlanmagan bo'lsa ogohlantirish belgisi ("ROI chizilmagan")

## 2.3. Chizish komponenti (Konva)

- [ ] 2.3.1 Video kadri ustida chizish qatlami, o'lchamga moslashish
- [ ] 2.3.2 Poligon: nuqta qo'shish, yopish, nuqtani sudrash, nuqtani o'chirish, butun shaklni surish
- [ ] 2.3.3 Chiziq: A va B nuqtalar, **yo'nalish strelkasi**, yo'nalishni almashtirish tugmasi
- [ ] 2.3.4 To'rtburchak/poligon zonalar (nazorat, istisno) — turli rangda
- [ ] 2.3.5 Bekor qilish / qaytarish (undo/redo), tozalash
- [ ] 2.3.6 Kattalashtirish va surish (zoom/pan)
- [ ] 2.3.7 Klaviatura qisqa tugmalari (Esc, Delete, Ctrl+Z, Ctrl+Y)
- [ ] 2.3.8 Saqlanmagan o'zgarish bo'lsa sahifadan chiqishda ogohlantirish

## 2.4. Sanash sozlamalari sahifasi

- [ ] 2.4.1 Jonli video (kameraning tahlil oqimidan) + chizish: ROI poligon va kesib o'tish chizig'i
- [ ] 2.4.2 Yo'nalish tanlash: A→B / B→A / ikkalasi
- [ ] 2.4.3 Parametrlar formasi (teskari o'tish siyosati, burchak, kuzatuv nuqtasi, inference fps)
- [ ] 2.4.4 Maslahat matni: "chiziqni mahsulot to'liq ko'rinadigan joyga qo'ying"
- [ ] 2.4.5 Faol mahsulotlar bo'limi uchun joy (4-bosqichda to'ldiriladi)
- [ ] 2.4.6 Saqlash, bekor qilish, standart qiymatlarga qaytarish

## 2.5. Uskuna sozlamalari sahifasi

- [ ] 2.5.1 Jonli video (kameraning tahlil oqimidan) + chizish: ROI, nazorat zonasi, istisno zonalari
- [ ] 2.5.2 Parametrlar formasi (threshold, min_on, min_off, sikl rejimi, qaytishlar soni K, etalon sikl vaqti, avto-etalon)
- [ ] 2.5.3 Signal grafigi uchun joy (5-bosqichda to'ldiriladi)
- [ ] 2.5.4 Saqlash, bekor qilish

## 2.6. AI qatlami (geometriya)

- [ ] 2.6.1 Qayta ishlatiladigan overlay komponenti: saqlangan ROI, chiziq, zonalarni video ustida chizadi
- [ ] 2.6.2 Grid sahifasida **"AI Vision"** checkbox; holati URL'da (`&ai=1`) va brauzerda saqlanadi
- [ ] 2.6.3 Kamera sahifasida qatlam o'tkazgichi (default — yoqilgan)
- [ ] 2.6.4 Kichik kataklarda chiziq qalinligi va yozuvlarning moslashishi
- [ ] 2.6.5 `fov_match` qoidasi: ha — main shakllari sub katak ustida chiziladi; yo'q — AI Vision yoqilganda tahlil oqimi main bo'lgan kamera katagi main dan (kichraytirilgan) ko'rsatiladi

---

## Qabul mezonlari

- [ ] Bosqichdagi barcha sahifalar dizayn tekshiruv ro'yxatidan (PLAN.md 4.1.6) o'tdi va o'z URL'i bilan ishlaydi
- [ ] Checkbox yoqilganda "Sozlash" faollashadi, bosilganda to'g'ri URL ochiladi
- [ ] ROI, chiziq, zonalar chiziladi, saqlanadi, sahifa yangilangandan keyin ham joyida
- [ ] Grid'da "AI Vision" yoqilganda barcha kameralarda saqlangan ROI va chiziqlar ko'rinadi
- [ ] Main tanlansa shakllar main ga, sub tanlansa sub ga chiziladi va tahlil shu oqimdan ishlaydi
- [ ] Kamera o'lchami o'zgarsa ham shakllar to'g'ri joyda (nisbiy koordinata)

---

## Jurnal (to'xtash nuqtalari)

| Sana | Oxirgi bajarilgan qadam | Keyingi qadam | Izoh / muammo |
|---|---|---|---|
| | | | |
