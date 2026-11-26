# Bajarilish rejasi — indeks

Bu papkada har bosqich uchun alohida fayl bor. Umumiy arxitektura va qarorlar — [../PLAN.md](../PLAN.md).

---

## Joriy holat (har ish seansi oxirida yangilanadi)

| | |
|---|---|
| **Joriy bosqich** | 0 — Infratuzilma va dizayn tizimi |
| **Oxirgi bajarilgan qadam** | — |
| **Keyingi qadam** | 0.1.1 |
| **To'siq / ochiq muammo** | — |
| **Oxirgi yangilanish** | — |

---

## Bosqichlar

| # | Fayl | Bosqich | Holat | Bajarildi |
|---|---|---|---|---|
| 0 | [00-infratuzilma.md](00-infratuzilma.md) | Infratuzilma va dizayn tizimi | ⬜ | 0 / 52 |
| 1 | [01-kameralar-video.md](01-kameralar-video.md) | Kameralar va video | ⬜ | 0 / 52 |
| 2 | [02-vazifalar-chizish.md](02-vazifalar-chizish.md) | Vazifalar karkasi va chizish | ⬜ | 0 / 36 |
| 3 | [03-dataset-train.md](03-dataset-train.md) | Katalog, dataset, belgilash, train | ⬜ | 0 / 52 |
| 4 | [04-sanash.md](04-sanash.md) | Mahsulot sanash | ⬜ | 0 / 48 |
| 5 | [05-uskuna.md](05-uskuna.md) | Uskuna ish vaqti va sikllar | ⬜ | 0 / 43 |
| 6 | [06-telegram.md](06-telegram.md) | Telegram (asos) | ⬜ | 0 / 31 |
| 7 | [07-smenalar-hisobotlar.md](07-smenalar-hisobotlar.md) | Smenalar va hisobotlar (asos) | ⬜ | 0 / 20 |
| 8 | [08-barqarorlik.md](08-barqarorlik.md) | Barqarorlik va ishga topshirish | ⬜ | 0 / 35 |

"Bajarildi" ustunida faqat raqamlangan qadamlar sanaladi (jami 369 ta); qabul mezonlari alohida belgilanadi.

Holat belgilari: ⬜ boshlanmagan · 🟡 jarayonda · ✅ tugagan · ⛔ to'siq bor

---

## Bosqichlar tartibi

```
0 ──► 1 ──► 2 ──► 4 ──► 6 ──► 7 ──► 8
       │     │     ▲     ▲     ▲
       │     └──► 5 ─────┴─────┘
       └──► 3 ─────┘
```

- 3-bosqich (dataset/train) 2-bosqich bilan parallel bajarilishi mumkin.
- 5-bosqich (uskuna) 4-bosqichdan (sanash) mustaqil.
- 4-bosqich 2 va 3 tugagandan keyin boshlanadi.

---

## Belgilash qoidalari

1. Qadam **bajarilib, tekshirilgandan keyin** belgilanadi: `- [ ]` → `- [x]`.
2. Qadam boshlangan, lekin tugamagan bo'lsa: `- [ ]` qoladi va oxiriga `← JARAYONDA` deb yoziladi (izoh bilan).
3. Qadam kerak emas deb topilsa: `- [x] ~~matn~~ (bekor: sababi)`.
4. Yangi qadam kerak bo'lsa — tegishli bo'limga keyingi raqam bilan qo'shiladi (mavjud raqamlar o'zgartirilmaydi).
5. Har ish seansi oxirida:
   - bosqich faylidagi **Jurnal** jadvaliga qator qo'shiladi (sana, oxirgi qadam, keyingi qadam, muammo);
   - shu fayldagi **Joriy holat** jadvali va bosqichlar jadvalidagi "Bajarildi" soni yangilanadi.
6. Bosqich fayli boshidagi **Holat** qatori ham yangilanadi (⬜ → 🟡 → ✅).
7. Bosqich faqat **qabul mezonlari**ning hammasi belgilangandan keyin ✅ bo'ladi.
8. O'lchov jadvallari (benchmark, versiyalar, sinov natijalari) joyida to'ldiriladi — ular keyingi qarorlar uchun asos.
9. Reja o'zgarsa (yangi talab, boshqa yechim) — avval `PLAN.md` yangilanadi, keyin tegishli bosqich fayli.

## Ishni davom ettirish

To'xtalishdan keyin ishni davom ettirish uchun:
1. Shu fayldagi **Joriy holat** jadvalini o'qish.
2. Joriy bosqich faylining **Jurnal** jadvalidagi oxirgi qatorni o'qish.
3. `← JARAYONDA` belgisi bor qadamdan yoki birinchi belgilanmagan qadamdan davom etish.
