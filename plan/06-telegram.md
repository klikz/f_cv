# Bosqich 6 — Telegram (asos)

**Holat:** ⬜ Boshlanmagan
**Bog'liqlik:** Bosqich 4 (sanoq hodisalari), Bosqich 5 (uskuna hodisalari)
**Maqsad:** bot qo'shilgan chatlar UI da avtomatik ko'rinadi; checkbox matritsa orqali qaysi kamera va vazifadan xabar ketishi belgilanadi; sanoq xabari snapshot bilan yuboriladi. Internet uzilsa faqat Telegram to'xtaydi.

**Eslatma:** bu faqat asos. Hisobotlar va batafsil logika loyiha ishga tushgandan keyin alohida rejalashtiriladi.

---

## 6.1. telegram-service

- [ ] 6.1.1 Bot tokeni `.env` da; token yo'q bo'lsa servis jim turadi, tizim ishlayveradi
- [ ] 6.1.2 aiogram, **long polling**
- [ ] 6.1.3 Tarmoq xatolariga chidamlilik: ortib boruvchi kutish bilan qayta urinish, yiqilmaslik
- [ ] 6.1.4 Bot holati Redis'da: ulangan / internet yo'q / token xato

## 6.2. Chatlarni avtomatik aniqlash

- [ ] 6.2.1 Migratsiya: `telegram_chats`, `telegram_subscriptions`, `notification_outbox`
- [ ] 6.2.2 `my_chat_member`: bot guruhga qo'shilsa — chat bazaga yoziladi; chiqarilsa — "faol emas"
- [ ] 6.2.3 Shaxsiy chat: `/start` bosilganda chat qayd etiladi
- [ ] 6.2.4 Chat nomi o'zgarsa yangilash; guruh superguruhga aylansa identifikatorni yangilash
- [ ] 6.2.5 Yangi chat paydo bo'lganda UI ga jonli xabar

## 6.3. Outbox (navbat)

- [ ] 6.3.1 Hodisalarni tinglovchi: Redis hodisasi → mos obunalarni topish → `notification_outbox` ga yozish
- [ ] 6.3.2 Yuboruvchi: navbatdan olib yuborish; holatlar (kutmoqda / yuborildi / xato)
- [ ] 6.3.3 Tezlik chegarasi (chat bo'yicha) va Telegram "keyinroq urinib ko'ring" javobiga bo'ysunish
- [ ] 6.3.4 Qayta urinish; eskirgan xabarlar uchun yashash muddati (sozlanadi)
- [ ] 6.3.5 Bot chatdan chiqarilgan bo'lsa xabarlarni bekor qilish va chatni "faol emas" qilish

## 6.4. Xabar turlari registri

- [ ] 6.4.1 Registr tuzilmasi: tur kodi, nomi, qaysi vazifaga tegishli, parametrlari, shablon (yangi tur qo'shish oson bo'lishi uchun)
- [ ] 6.4.2 **Mahsulot sanaldi:** rasm (ramkali snapshot) + matn (mahsulot, kamera, vaqt, smena jami) — har mahsulotga alohida xabar
- [ ] 6.4.3 **Uskuna to'xtadi (> N daqiqa)** / **qayta ishga tushdi:** matn (snapshotsiz)
- [ ] 6.4.4 **Kamera uzildi / tiklandi:** matn
- [ ] 6.4.5 **Train tugadi / xato:** matn
- [ ] 6.4.6 Barcha matnlar o'zbek tilida

## 6.5. UI — `/telegram`

- [ ] 6.5.1 Bot holati (ulangan / internet yo'q)
- [ ] 6.5.2 Chatlar ro'yxati: nom, turi (shaxsiy/guruh), faol/faol emas
- [ ] 6.5.3 Har chat uchun **matritsa**: kamera × vazifa × xabar turi — checkbox'lar
- [ ] 6.5.4 Parametrli turlar uchun qiymat kiritish (masalan "N daqiqa")
- [ ] 6.5.5 "Sinov xabari yuborish" tugmasi
- [ ] 6.5.6 Navbat holati: kutayotgan, yuborilgan, xato xabarlar soni
- [ ] 6.5.7 Yuqori panelda Telegram holati belgisi

## 6.6. Sinov

- [ ] 6.6.1 Botni yangi guruhga qo'shish → UI da paydo bo'lishini tekshirish
- [ ] 6.6.2 Internetni uzish: tizimning boshqa qismlari ishlashini, xabarlar navbatda to'planishini tekshirish
- [ ] 6.6.3 Internetni qaytarish: xabarlar ketishini tekshirish
- [ ] 6.6.4 Ko'p sanoq ketma-ket bo'lganda tezlik chegarasi ishlashini tekshirish

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
| | | | |
