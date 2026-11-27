# Bosqich 5 — Uskuna ish vaqti va sikllar

**Holat:** 🟡 Dasturiy qismi tugagan; haqiqiy press/stanok sinovi qolgan
**Bog'liqlik:** Bosqich 2 (4-bosqichdan mustaqil — parallel bajarilishi mumkin)
**Maqsad:** ROI dagi harakat bo'yicha uskunaning ishlagan/to'xtagan vaqti va sikllar soni hisoblanadi; sikl vaqti real-time o'lchanadi; parametrlar UI orqali sozlanadi.

**Eslatma:** bu vazifada snapshot saqlanmaydi. Harakat bor = "ishlayapti" (bo'sh aylanish ham). GPU ishlatilmaydi — train paytida ham ishlaydi.

---

## 5.1. Harakat signali

- [x] 5.1.1 Kameraning **tahlil oqimidan** ROI kesimi → kulrang → kichraytirish
- [x] 5.1.2 Kadrlar farqi + MOG2 (fon ayirish) → harakat maskasi → **harakat foizi** (10 fps)
- [x] 5.1.3 Istisno zonalarini maskadan chiqarish
- [x] 5.1.4 Nazorat zonasi: undagi harakat (kamera titrashi) asosiy signaldan ayiriladi
- [x] 5.1.5 Signalni silliqlash
- [x] 5.1.6 Xom signal Redis'ga (oxirgi bir necha soat saqlanadi)
- [x] 5.1.7 Testlar: sintetik kadrlar (harakatsiz, harakatli, butun kadr titrashi)

## 5.2. Holat mashinasi

- [x] 5.2.1 Migratsiya: `equipment_intervals`, `cycle_events`, `equipment_minute_stats`
- [x] 5.2.2 `ISHLAYAPTI ⇄ TO'XTAGAN`: threshold, `min_on_sec`, `min_off_sec`
- [x] 5.2.3 Kamera uzilsa — `NOMA'LUM`
- [x] 5.2.4 Intervallarni bazaga yozish (smena bilan); smena chegarasida interval bo'linadi
- [x] 5.2.5 Qayta ishga tushganda ochiq qolgan intervalni to'g'ri yopish
- [x] 5.2.6 Joriy holat va joriy smenadagi ishlagan vaqt Redis'da (UI uchun)
- [x] 5.2.7 Testlar: qisqa to'xtashlar (debounce), smena chegarasi

## 5.3. Sikl aniqlash

**Tayanch holat rejimi (asosiy):**
- [x] 5.3.1 Tayanch ("uy") kadrni saqlash: UI tugmasi bilan olish
- [x] 5.3.2 Signal: joriy ROI ning tayanch ko'rinishdan farqi
- [x] 5.3.3 "Chiqdi" / "qaytdi" chegaralari (histerezis bilan)
- [x] 5.3.4 Sikl = tayanchga K marta qaytish (K sozlanadi: press — 1, ikki marta aylanish — 2)
- [x] 5.3.5 Tayanch kadrni avtomatik taklif qilish (eng ko'p uchraydigan tinch holat)
- [x] 5.3.6 Yorug'lik o'zgarishiga chidamlilik (tayanchni sekin yangilab borish)

**Cho'qqilar rejimi (muqobil):**
- [x] 5.3.7 Harakat signalida cho'qqilarni topish; sikl = K cho'qqi
- [x] 5.3.8 Avto-aniqlash: autokorrelyatsiya bilan davrni topib, K va chegaralarni taklif qilish

**Umumiy:**
- [x] 5.3.9 Har sikl `cycle_events` ga (boshlanish, tugash, davomiylik, etalondan og'ish, smena)
- [x] 5.3.10 Etalon sikl vaqti: dastlabki N sikl medianasi (avto) yoki qo'lda kiritilgan qiymat
- [x] 5.3.11 Mikro-to'xtash: sikl > etalon × koeffitsient
- [x] 5.3.12 Joriy smena sikllar soni, oxirgi va o'rtacha sikl vaqti Redis'da
- [x] 5.3.13 Testlar: sintetik signal (muntazam, notekis, to'xtash bilan)

## 5.4. Daqiqalik yig'indi

- [x] 5.4.1 Har daqiqada: o'rtacha harakat, ishlagan soniyalar → `equipment_minute_stats`
- [x] 5.4.2 Xom signal bazaga yozilmasligini tekshirish

## 5.5. Uskuna sozlamalari sahifasini to'ldirish

- [x] 5.5.1 Jonli signal grafigi (oxirgi daqiqalar), threshold chizig'i — sudrab o'zgartirish
- [x] 5.5.2 Grafikda holat (ishlayapti/to'xtagan) va aniqlangan sikllar belgilari
- [x] 5.5.3 Sikl rejimini tanlash: tayanch holat / cho'qqilar / avto
- [x] 5.5.4 "Tayanch kadrni olish" tugmasi va uning ko'rinishi
- [x] 5.5.5 "Avto-aniqlash" tugmasi: taklif qilingan parametrlarni ko'rsatish va qabul qilish
- [x] 5.5.6 Etalon sikl vaqti: joriy avto qiymat, qo'lda kiritish, qayta hisoblash
- [x] 5.5.7 Jonli test: sozlamani saqlamasdan natijani ko'rish

## 5.6. AI qatlami va grid holati

- [x] 5.6.1 Harakat sohalari: maskadan soddalashtirilgan konturlar metadata'da
- [x] 5.6.2 Overlay: harakat joylari yarim shaffof; ROI rangi holatga qarab (yashil / qizil)
- [x] 5.6.3 Grid katagida holat yozuvi: joriy holat, ishlagan vaqt, sikllar soni; katta katakda oxirgi sikl vaqti va ish vaqti foizi
- [x] 5.6.4 Kamera sahifasida joriy smena statistikasi

## 5.7. Uskunada sinov

- [ ] 5.7.1 Press va stanokda bir smena davomida sinash ← HAQIQIY USKUNADA
- [ ] 5.7.2 Qo'lda kuzatuv bilan solishtirish: ish vaqti, sikllar soni ← HAQIQIY USKUNADA (sintetik press: 26/26 sikl, sikl 3.00 s, ish vaqti 76/78 s)
- [ ] 5.7.3 Natijalarni yozish ← HAQIQIY USKUNADA

| Uskuna | Rejim | Qo'lda sikl | Tizim sikl | Farq | Izoh |
|---|---|---|---|---|---|
| 2026-11-27 | 5.6.4 | 5.7 (haqiqiy uskuna) | Holat mashinasi siklik tanaffuslarga moslandi (test bilan) | | |

---

## Qabul mezonlari

- [ ] Bosqichdagi barcha sahifalar dizayn tekshiruv ro'yxatidan (PLAN.md 4.1.6) o'tdi va o'z URL'i bilan ishlaydi
- [ ] Ishlagan va to'xtagan vaqt qo'lda kuzatuv bilan mos
- [ ] Sikllar soni qo'lda sanoq bilan mos (press: tushib-ko'tarilish; aylanuvchi qism: 2 aylanish = 1 sikl)
- [ ] Sikl vaqti real-time ko'rinadi, etalon avtomatik hisoblanadi va qo'lda o'zgartiriladi
- [ ] Press zarbidan kamera titrashi yolg'on "ishlayapti" bermaydi
- [ ] Train paytida uskuna vazifasi to'xtamaydi
- [ ] Grid'da holat, ishlagan vaqt va sikl soni yozilib turadi

---

## Jurnal (to'xtash nuqtalari)

| Sana | Oxirgi bajarilgan qadam | Keyingi qadam | Izoh / muammo |
|---|---|---|---|
| | | | |
