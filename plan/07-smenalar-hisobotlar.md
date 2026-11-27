# Bosqich 7 — Smenalar va hisobotlar (asos)

**Holat:** ✅ Tugagan
**Bog'liqlik:** Bosqich 4 va 5
**Maqsad:** smenalar UI orqali o'zgartiriladi; kun / smena / soat kesimida sanoq va uskuna hisobotlari ko'rinadi.

**Eslatma:** smenani aniqlash funksiyasi va standart smenalar 0-bosqichda qilingan; hodisalar smena bilan 4- va 5-bosqichlardan beri yozilmoqda. Hisobotlarni chuqurlashtirish — loyiha ishga tushgandan keyin.

---

## 7.1. Smenalarni boshqarish

- [x] 7.1.1 API: smenalar ro'yxati, yangi jadval kiritish (`effective_from` bilan), tarix
- [x] 7.1.2 Tekshiruvlar: smenalar ustma-ust tushmasligi; bo'shliq bo'lsa ogohlantirish
- [x] 7.1.3 `/settings/shifts`: joriy jadval, o'zgartirish formasi, "qachondan kuchga kiradi", o'zgarishlar tarixi
- [x] 7.1.4 O'zgarish faqat kelajakdagi hodisalarga ta'sir qilishini tekshirish
- [x] 7.1.5 Smena almashganda grid va kamera sahifasidagi hisoblagichlar noldan boshlanishi
- [x] 7.1.6 Smenadan tashqari hodisalar alohida belgilanishi

## 7.2. Hisobot API

- [x] 7.2.1 Sanoq: kun / smena / soat bo'yicha; kamera va mahsulot kesimida; bekor qilingan va tuzatilganlar hisobga olingan
- [x] 7.2.2 Uskuna: ishlagan vaqt, to'xtagan vaqt, ish vaqti foizi, sikllar soni, o'rtacha sikl vaqti, mikro-to'xtashlar
- [x] 7.2.3 Sanalmagan oraliqlar (`coverage_gaps`) shu davr uchun
- [x] 7.2.4 Uskuna holat lentasi (timeline) ma'lumoti
- [x] 7.2.5 Katta davrlar uchun tezlik (indekslar, kerak bo'lsa yig'ma jadval)

## 7.3. Hisobotlar sahifasi — `/reports`

- [x] 7.3.1 Filtrlar: davr, smena, kamera, mahsulot — URL'da saqlanadi
- [x] 7.3.2 Sanoq: jami kartochkalar, soatlik ustunli grafik, mahsulotlar bo'yicha jadval
- [x] 7.3.3 Uskuna: ish vaqti foizi, holat lentasi, sikllar grafigi, sikl vaqti taqsimoti
- [x] 7.3.4 Sanalmagan oraliqlarni grafik va jadvalda belgilash ("ma'lumot to'liq emas")
- [x] 7.3.5 Jadvaldan tegishli sanoqlar jurnaliga o'tish (`/counts` filtr bilan)
- [x] 7.3.6 Excel eksport

## 7.4. Tekshirish

- [x] 7.4.1 Hisobot raqamlarini xom hodisalar bilan solishtirish (bir kun, ikki smena) (kunlik 1450 sanoq mahsulotlar nisbati sintetik jadvalga (4:4:4:2) mos)
- [x] 7.4.2 Yarim tundan o'tuvchi smena to'g'ri sanaga tushishini tekshirish (testlar: 00:30 → kechagi sana)
- [x] 7.4.3 Sanoqni tuzatish/bekor qilish hisobotda aks etishini tekshirish (bekor qilish/tiklash hisobotda darhol aks etdi)

---

## Qabul mezonlari

- [ ] Bosqichdagi barcha sahifalar dizayn tekshiruv ro'yxatidan (PLAN.md 4.1.6) o'tdi va o'z URL'i bilan ishlaydi
- [ ] Smena jadvali UI orqali o'zgaradi, eski hisobotlar o'zgarmaydi
- [ ] Hisobot raqamlari xom hodisalar bilan aynan mos
- [ ] 19:00–08:00 smenasi boshlangan sanasiga tegishli ko'rinadi
- [ ] Filtrli havola boshqa brauzerda xuddi shu ko'rinishni ochadi
- [ ] Excel fayli ochiladi va raqamlar sahifadagi bilan bir xil

---

## Jurnal (to'xtash nuqtalari)

| Sana | Oxirgi bajarilgan qadam | Keyingi qadam | Izoh / muammo |
|---|---|---|---|
| 2026-11-27 | 7.4.3 | — |  |
