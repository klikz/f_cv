# Bosqich 7 — Smenalar va hisobotlar (asos)

**Holat:** ⬜ Boshlanmagan
**Bog'liqlik:** Bosqich 4 va 5
**Maqsad:** smenalar UI orqali o'zgartiriladi; kun / smena / soat kesimida sanoq va uskuna hisobotlari ko'rinadi.

**Eslatma:** smenani aniqlash funksiyasi va standart smenalar 0-bosqichda qilingan; hodisalar smena bilan 4- va 5-bosqichlardan beri yozilmoqda. Hisobotlarni chuqurlashtirish — loyiha ishga tushgandan keyin.

---

## 7.1. Smenalarni boshqarish

- [ ] 7.1.1 API: smenalar ro'yxati, yangi jadval kiritish (`effective_from` bilan), tarix
- [ ] 7.1.2 Tekshiruvlar: smenalar ustma-ust tushmasligi; bo'shliq bo'lsa ogohlantirish
- [ ] 7.1.3 `/settings/shifts`: joriy jadval, o'zgartirish formasi, "qachondan kuchga kiradi", o'zgarishlar tarixi
- [ ] 7.1.4 O'zgarish faqat kelajakdagi hodisalarga ta'sir qilishini tekshirish
- [ ] 7.1.5 Smena almashganda grid va kamera sahifasidagi hisoblagichlar noldan boshlanishi
- [ ] 7.1.6 Smenadan tashqari hodisalar alohida belgilanishi

## 7.2. Hisobot API

- [ ] 7.2.1 Sanoq: kun / smena / soat bo'yicha; kamera va mahsulot kesimida; bekor qilingan va tuzatilganlar hisobga olingan
- [ ] 7.2.2 Uskuna: ishlagan vaqt, to'xtagan vaqt, ish vaqti foizi, sikllar soni, o'rtacha sikl vaqti, mikro-to'xtashlar
- [ ] 7.2.3 Sanalmagan oraliqlar (`coverage_gaps`) shu davr uchun
- [ ] 7.2.4 Uskuna holat lentasi (timeline) ma'lumoti
- [ ] 7.2.5 Katta davrlar uchun tezlik (indekslar, kerak bo'lsa yig'ma jadval)

## 7.3. Hisobotlar sahifasi — `/reports`

- [ ] 7.3.1 Filtrlar: davr, smena, kamera, mahsulot — URL'da saqlanadi
- [ ] 7.3.2 Sanoq: jami kartochkalar, soatlik ustunli grafik, mahsulotlar bo'yicha jadval
- [ ] 7.3.3 Uskuna: ish vaqti foizi, holat lentasi, sikllar grafigi, sikl vaqti taqsimoti
- [ ] 7.3.4 Sanalmagan oraliqlarni grafik va jadvalda belgilash ("ma'lumot to'liq emas")
- [ ] 7.3.5 Jadvaldan tegishli sanoqlar jurnaliga o'tish (`/counts` filtr bilan)
- [ ] 7.3.6 Excel eksport

## 7.4. Tekshirish

- [ ] 7.4.1 Hisobot raqamlarini xom hodisalar bilan solishtirish (bir kun, ikki smena)
- [ ] 7.4.2 Yarim tundan o'tuvchi smena to'g'ri sanaga tushishini tekshirish
- [ ] 7.4.3 Sanoqni tuzatish/bekor qilish hisobotda aks etishini tekshirish

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
| | | | |
