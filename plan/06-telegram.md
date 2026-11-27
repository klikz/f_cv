# Bosqich 6 — Telegram (asos)

**Holat:** 🟡 Dasturiy qismi tugagan; bot tokeni bilan sinov qolgan
**Bog'liqlik:** Bosqich 4 (sanoq hodisalari), Bosqich 5 (uskuna hodisalari)
**Maqsad:** bot qo'shilgan chatlar UI da avtomatik ko'rinadi; checkbox matritsa orqali qaysi kamera va vazifadan xabar ketishi belgilanadi; sanoq xabari snapshot bilan yuboriladi. Internet uzilsa faqat Telegram to'xtaydi.

**Eslatma:** bu faqat asos. Hisobotlar va batafsil logika loyiha ishga tushgandan keyin alohida rejalashtiriladi.

---

## 6.1. telegram-service

- [x] 6.1.1 Bot tokeni `.env` da; token yo'q bo'lsa servis jim turadi, tizim ishlayveradi
- [x] 6.1.2 aiogram, **long polling**
- [x] 6.1.3 Tarmoq xatolariga chidamlilik: ortib boruvchi kutish bilan qayta urinish, yiqilmaslik
- [x] 6.1.4 Bot holati Redis'da: ulangan / internet yo'q / token xato

## 6.2. Chatlarni avtomatik aniqlash

- [x] 6.2.1 Migratsiya: `telegram_chats`, `telegram_subscriptions`, `notification_outbox`
- [x] 6.2.2 `my_chat_member`: bot guruhga qo'shilsa — chat bazaga yoziladi; chiqarilsa — "faol emas"
- [x] 6.2.3 Shaxsiy chat: `/start` bosilganda chat qayd etiladi
- [x] 6.2.4 Chat nomi o'zgarsa yangilash; guruh superguruhga aylansa identifikatorni yangilash
- [x] 6.2.5 Yangi chat paydo bo'lganda UI ga jonli xabar

## 6.3. Outbox (navbat)

- [x] 6.3.1 Hodisalarni tinglovchi: Redis hodisasi → mos obunalarni topish → `notification_outbox` ga yozish
- [x] 6.3.2 Yuboruvchi: navbatdan olib yuborish; holatlar (kutmoqda / yuborildi / xato)
- [x] 6.3.3 Tezlik chegarasi (chat bo'yicha) va Telegram "keyinroq urinib ko'ring" javobiga bo'ysunish
- [x] 6.3.4 Qayta urinish; eskirgan xabarlar uchun yashash muddati (sozlanadi)
- [x] 6.3.5 Bot chatdan chiqarilgan bo'lsa xabarlarni bekor qilish va chatni "faol emas" qilish

## 6.4. Xabar turlari registri

- [x] 6.4.1 Registr tuzilmasi: tur kodi, nomi, qaysi vazifaga tegishli, parametrlari, shablon (yangi tur qo'shish oson bo'lishi uchun)
- [x] 6.4.2 **Mahsulot sanaldi:** rasm (ramkali snapshot) + matn (mahsulot, kamera, vaqt, smena jami) — har mahsulotga alohida xabar
- [x] 6.4.3 **Uskuna to'xtadi (> N daqiqa)** / **qayta ishga tushdi:** matn (snapshotsiz)
- [x] 6.4.4 **Kamera uzildi / tiklandi:** matn
- [x] 6.4.5 **Train tugadi / xato:** matn
- [x] 6.4.6 Barcha matnlar o'zbek tilida

## 6.5. UI — `/telegram`

- [x] 6.5.1 Bot holati (ulangan / internet yo'q)
- [x] 6.5.2 Chatlar ro'yxati: nom, turi (shaxsiy/guruh), faol/faol emas
- [x] 6.5.3 Har chat uchun **matritsa**: kamera × vazifa × xabar turi — checkbox'lar
- [x] 6.5.4 Parametrli turlar uchun qiymat kiritish (masalan "N daqiqa")
- [x] 6.5.5 "Sinov xabari yuborish" tugmasi
- [x] 6.5.6 Navbat holati: kutayotgan, yuborilgan, xato xabarlar soni
- [x] 6.5.7 Yuqori panelda Telegram holati belgisi

## 6.6. Sinov

- [ ] 6.6.1 Botni yangi guruhga qo'shish → UI da paydo bo'lishini tekshirish ← BOT TOKENI KERAK
- [ ] 6.6.2 Internetni uzish: tizimning boshqa qismlari ishlashini, xabarlar navbatda to'planishini tekshirish ← BOT TOKENI KERAK
- [ ] 6.6.3 Internetni qaytarish: xabarlar ketishini tekshirish ← BOT TOKENI KERAK
- [ ] 6.6.4 Ko'p sanoq ketma-ket bo'lganda tezlik chegarasi ishlashini tekshirish ← BOT TOKENI KERAK

---

## Qabul mezonlari

- [ ] Bosqichdagi barcha sahifalar dizayn tekshiruv ro'yxatidan (PLAN.md 4.1.6) o'tdi va o'z URL'i bilan ishlaydi
- [ ] Bot guruhga qo'shilganda chat UI da o'zi chiqadi
- [ ] Belgilangan kamera va vazifadan xabar keladi, belgilanmaganidan kelmaydi
- [ ] Sanoq xabarida ramkali snapshot bor
- [ ] Internet yo'qligida tizim to'liq ishlaydi; internet qaytganda xabarlar yuboriladi
- [ ] Yangi xabar turini qo'shish faqat registrga yozuv qo'shishni talab qiladi

---

## Jurnal (to'xtash nuqtalari)

| Sana | Oxirgi bajarilgan qadam | Keyingi qadam | Izoh / muammo |
|---|---|---|---|
| 2026-11-27 | 6.5.7 | 6.6 (token kerak) | Token yo'qligi to'g'ri ko'rsatiladi; outbox/registr/matritsa tayyor |
