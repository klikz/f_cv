# Bosqich 3 — Katalog, dataset, belgilash va train

**Holat:** ⬜ Boshlanmagan
**Bog'liqlik:** Bosqich 1 (2-bosqich bilan parallel bo'lishi mumkin)
**Maqsad:** mahsulot katalogga qo'shiladi → snapshotlar olinadi → belgilanadi → **shu mahsulotning alohida modeli** train qilinadi → TensorRT engine'ga aylanadi → versiya sifatida saqlanadi. Train jarayoni UI da kuzatiladi.

**Qoida:** bitta mahsulot = bitta model. Ko'p klassli umumiy model yo'q.

---

## 3.1. Mahsulotlar katalogi

- [ ] 3.1.1 Migratsiya: `products` (kod, nom, kategoriya, rasm)
- [ ] 3.1.2 CRUD API + qidiruv
- [ ] 3.1.3 `/products`: ro'yxat, qidiruv, kategoriya filtri, qo'shish/tahrirlash/o'chirish
- [ ] 3.1.4 `/products/:id`: mahsulot kartasi (dataset holati, model versiyalari uchun joy)

## 3.2. Snapshot olish

- [ ] 3.2.1 Migratsiya: `dataset_images` (kamera, oqim, fayl, manba, holat), `annotations`
- [ ] 3.2.2 Fayllar tuzilmasi: `data/datasets/images/<kamera>/<sana>/...` (kameraning **tahlil oqimidan**, oqim rasm bilan birga yoziladi)
- [ ] 3.2.3 Qo'lda snapshot: kamera sahifasi va dataset sahifasida tugma (tahlil oqimi main bo'lib, u yopiq bo'lsa qisqa muddatga ochiladi)
- [ ] 3.2.4 Avto-yig'ish: kamera bo'yicha yoqiladi; ROI da harakat bo'lsa har N soniyada; kunlik limit
- [ ] 3.2.5 Bir xil (deyarli takror) kadrlarni o'tkazib yuborish

## 3.3. Belgilash

- [ ] 3.3.1 `/dataset`: rasmlar galereyasi; filtrlar (kamera, mahsulot, holat: belgilanmagan / avto / tasdiqlangan, sana) — URL'da
- [ ] 3.3.2 `/dataset/annotate/:imageId`: ramka (bbox) chizish, o'lchamini o'zgartirish, o'chirish
- [ ] 3.3.3 Mahsulot tanlash: qidiruv + oxirgi ishlatilganlar
- [ ] 3.3.4 "Qadoq holati" atributi: qutili / qutisiz
- [ ] 3.3.5 "Bo'sh rasm" belgisi (mahsulot yo'q — negativ namuna)
- [ ] 3.3.6 Tezlashtirish: keyingi/oldingi rasm, oldingi rasm ramkalarini nusxalash, klaviatura qisqa tugmalari
- [ ] 3.3.7 Kattalashtirish va surish
- [ ] 3.3.8 Rasmni o'chirish (tasdiqlash bilan)
- [ ] 3.3.9 Bir-biriga tegib turgan mahsulotlar: har biri alohida ramka bilan belgilanadi; tayyorlik indikatorida "tegib turgan holatlar" soni alohida ko'rsatiladi

## 3.4. Tayyorlik indikatori

- [ ] 3.4.1 Har mahsulot bo'yicha hisob: belgilangan obyektlar soni, qutili/qutisiz, kameralar bo'yicha, negativ rasmlar soni
- [ ] 3.4.2 Holat: "yetarli emas" / "minimal" / "tayyor" (chegaralar sozlamalarda; tavsiya ≥100–150 obyekt)
- [ ] 3.4.3 Katalog va dataset sahifalarida ko'rsatish

## 3.5. Trainer

- [ ] 3.5.1 Migratsiya: `training_jobs`, `training_metrics`, `model_versions`
- [ ] 3.5.2 YOLO26 boshlang'ich og'irliklarini lokal joylash; Ultralytics'ning internetga murojaatlarini o'chirish
- [ ] 3.5.3 Dataset tayyorlovchi: bitta mahsulot uchun YOLO formatida — ijobiy: shu mahsulot ramkalari (1 klass); **negativ: boshqa mahsulotli va bo'sh rasmlar yorliqsiz**; negativlar nisbati sozlanadi
- [ ] 3.5.4 Train/val bo'linishi barqaror (rasm identifikatori bo'yicha — qayta train'da o'zgarmaydi)
- [ ] 3.5.5 Kameraga xos variant: faqat tanlangan kamera rasmlaridan; dataset oqimlar bo'yicha taqsimoti ko'rsatiladi (kamera tahlil oqimidan farqli rasmlar ko'p bo'lsa ogohlantirish)
- [ ] 3.5.6 Navbat (Redis): bir vaqtda bitta job; bir nechta mahsulot tanlansa — alohida job'lar
- [ ] 3.5.7 Train ishga tushirish: parametrlar (model o'lchami n/s, epoch, o'lcham), standart qiymatlar
- [ ] 3.5.8 Har epoch'da metrikalar `training_metrics` ga va jonli holat Redis'ga (epoch, loss, mAP, ETA)
- [ ] 3.5.9 Bekor qilish; xatoni ushlash va tushunarli matn bilan saqlash
- [ ] 3.5.10 Rejalashtirish: "hozir" yoki "belgilangan vaqtda"
- [ ] 3.5.11 Train boshlanganda "inference to'xtatilsin" bayrog'i (Redis) va `coverage_gaps` yozuvi; navbat bo'shaganda bayroq olinadi

## 3.6. TensorRT eksport

- [ ] 3.6.1 Train tugagach avtomatik eksport: FP16, dinamik batch
- [ ] 3.6.2 Engine bilan validatsiya; `.pt` natijasi bilan solishtirish (farq katta bo'lsa ogohlantirish)
- [ ] 3.6.3 Engine yoniga drayver/TensorRT versiyasini yozish (keyin avto qayta qurish uchun)
- [ ] 3.6.4 Fayllar: `data/models/<mahsulot>/<versiya>/...`, `data/engines/...`

## 3.7. Model registri

- [ ] 3.7.1 API: mahsulot versiyalari, metrikalar, faollashtirish, oldingi versiyaga qaytarish, o'chirish
- [ ] 3.7.2 `/models`: mahsulotlar bo'yicha joriy faol versiya va holat
- [ ] 3.7.3 `/models/:productId`: versiyalar ro'yxati, metrikalarni solishtirish, "Faollashtirish" tugmasi
- [ ] 3.7.4 Yangi versiya avtomatik faollashmaydi

## 3.8. Train monitoringi (UI)

- [ ] 3.8.1 `/training`: navbat va tarix (holat, mahsulot, boshlangan vaqt, davomiylik)
- [ ] 3.8.2 `/training/:jobId`: holat va bosqich (navbatda → dataset → train → validatsiya → eksport → tayyor)
- [ ] 3.8.3 Epoch X/Y, **boshlangan vaqt, o'tgan vaqt, qolgan vaqt (ETA)**, jarayon chizig'i
- [ ] 3.8.4 Grafiklar: loss, mAP50, mAP50-95
- [ ] 3.8.5 GPU yuklamasi, VRAM, harorat
- [ ] 3.8.6 Loglar oynasi, "Bekor qilish" tugmasi
- [ ] 3.8.7 Yuqori panelda "Train ketmoqda" belgisi; grid kataklarida ham

## 3.9. Avto-belgilash

- [ ] 3.9.1 Mahsulotning joriy (yoki qoralama) modeli bilan belgilanmagan rasmlarga ramka taklif qilish
- [ ] 3.9.2 Takliflar "avto" holatida saqlanadi; UI da tasdiqlash / tuzatish / rad etish
- [ ] 3.9.3 "Tez qoralama train" (kam epoch) — dastlabki ~30 rasmdan keyin
- [ ] 3.9.4 Ommaviy tasdiqlash (ishonch yuqori bo'lganlarini)

## 3.10. O'lchovlar

- [ ] 3.10.1 Bitta mahsulot train vaqti va engine qurish vaqtini o'lchab yozish

| Model | Rasmlar | Epoch | Train vaqti | Eksport vaqti | mAP50-95 |
|---|---|---|---|---|---|
| YOLO26n | | | | | |
| YOLO26s | | | | | |

---

## Qabul mezonlari

- [ ] Bosqichdagi barcha sahifalar dizayn tekshiruv ro'yxatidan (PLAN.md 4.1.6) o'tdi va o'z URL'i bilan ishlaydi
- [ ] Yangi mahsulot: katalogga qo'shish → snapshot → belgilash → train → engine → versiya — hammasi UI orqali
- [ ] Train sahifasida epoch, boshlangan/qolgan vaqt va grafiklar jonli yangilanadi
- [ ] Train'ni bekor qilish ishlaydi; xato tushunarli ko'rsatiladi
- [ ] Ikkinchi mahsulotni train qilish birinchisining modeliga tegmaydi
- [ ] Internet uzilgan holatda train ishlaydi

---

## Jurnal (to'xtash nuqtalari)

| Sana | Oxirgi bajarilgan qadam | Keyingi qadam | Izoh / muammo |
|---|---|---|---|
| | | | |
