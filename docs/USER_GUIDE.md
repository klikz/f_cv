# Foydalanuvchi qo'llanmasi

UI serverning o'zidan ochiladi: `http://localhost:8100/`. Qisqa tugmalar: **Ctrl+K** — buyruqlar oynasi, **?** — tugmalar ro'yxati.

## 1. Kamera qo'shish
**Sozlamalar → Kameralar → Kamera qo'shish**
- **RTSP** (asosiy usul): nom, asosiy oqim (main) va ixtiyoriy sub oqim manzili. Har birini **Tekshirish** — kodek, o'lcham, FPS.
- **ONVIF**: *Tarmoqdan qidirish* (yoki IP ni qo'lda) → login/parol → *Ulanish* → profillardan asosiy/sub tanlang → *Manzillarni to'ldirish*.
- **Kadrlarni solishtirish**: ikkala oqim bir xil sohani ko'rsatsa — *Ko'rish maydoni bir xil* belgisini qo'ying.
- Saqlangach kamera paneli (bosh sahifa)da paydo bo'ladi; katakka **ikki marta bosish** — kamera sahifasi.

## 2. Vazifani sozlash
Kamera sahifasi → **Tahlil oqimi** (asosiy/sub) → vazifa belgisi → **Sozlash**.

**Mahsulot sanash** (4 qadam):
1. *ROI hududi* — konveyerning mahsulot o'tadigan qismini poligon bilan chizing (nuqtalarni bosing, birinchi nuqta yoki Enter — yopish).
2. *Kesib o'tish chizig'i* — A va B nuqtalar. Strelka — mahsulot harakat yo'nalishi (kerak bo'lsa **A↔B**). Chiziqni mahsulot to'liq ko'rinadigan joyga qo'ying.
3. *Mahsulotlar* — liniyada ketadigan mahsulotlarni tanlang (faqat faol modeli borlar).
4. *Sinab ko'ring* — aniqlashlar va "sanalgan bo'lardi" belgisi bazaga yozilmasdan ko'rinadi.

**Uskuna ish vaqti**: ROI (uskuna harakatlanadigan joy), ixtiyoriy *nazorat zonasi* (kamera titrashini ayirish uchun qo'zg'almas joy) va *istisno zonalari* (miltillovchi lampa). Jonli grafikda harakat chegarasini o'rnating. Sikl rejimi *Tayanch holat* bo'lsa — uskuna boshlang'ich holatida turganda **Tayanch kadr → Hozirgi kadr** (yoki *Avto taklif*). **Avto-aniqlash** sikl parametrlarini taklif qiladi.

Chizish: nuqtani sudrash, shaklni ichidan surish, qirraga 2× bosish — nuqta qo'shish, o'ng tugma/Delete — nuqtani o'chirish, g'ildirak — zoom, Space+sudrash — surish, Ctrl+Z/Y.

## 3. Mahsulot qo'shish, belgilash va train
1. **Mahsulotlar → Mahsulot qo'shish** — kod va nom.
2. **Dataset** — kamera va mahsulotni tanlang, jonli ko'rinish ostida *ROI* yoki *Butun kadr* rejimida *Snapshot olish* (**S**), yoki *Avto-yig'ish*ni yoqing. So'ng *Belgilashni boshlash*. Batafsil: [DATASET_GUIDE.md](DATASET_GUIDE.md).
3. Belgilash: mahsulotni tanlang (o'ngdan yoki **1–9**), rasmda ramka chizing (sudrang). **B** — qutili/qutisiz, **T** — tegib turgan, **E** — bo'sh rasm (negativ), **C** — oldingi rasm ramkalarini nusxalash, **→/Enter** — saqlash va keyingi. Tegib turgan mahsulotlar — har biri alohida ramka.
4. Har mahsulotga ~30 ramka bo'lgach: **Train → Yangi train → Tez qoralama** → so'ng **Dataset → Avto-belgilash** (model qolgan rasmlarga taklif beradi; *Avto* yorlig'ida tasdiqlang yoki tuzating).
5. Tayyorlik indikatori "Tayyor" (≥120 ramka) bo'lgach — **To'liq train**. Train paytida sanash to'xtatiladi (video va uskuna ishlayveradi).
6. **Modellar → mahsulot → Faollashtirish** (yangi versiya avtomatik faollashmaydi; metrikalarni solishtiring). Kerak bo'lsa *Oldingi versiyaga qaytish*.

## 4. Sanoqni tuzatish
**Sanoqlar jurnali** — har sanoq snapshot bilan.
- *Noaniqlarni ko'rib chiqish* → tezkor rejim: **1–9** — nomzod, **Enter** — tasdiqlash, **X** — yolg'on sanoq.
- Mahsulotni o'zgartirish yoki bekor qilish — asl qiymat saqlanadi. *Datasetga qo'shish* — tuzatilgan snapshot belgilangan holda datasetga.
- *Aniqlikni tekshirish* yorlig'i: vaqt oralig'idagi qo'lda sanalgan sonni kiriting — tizim farqni ko'rsatadi.
- Kamera sanash sozlamasida *O'lcham oralig'ini o'rganish* — o'lchami farqli, dizayni bir xil mahsulotlarni ajratishga yordam beradi.

## 5. Telegram
**Telegram** sahifasi: bot tokenini kiriting. Botni guruhga qo'shing yoki shaxsiy chatda `/start` — chat avtomatik paydo bo'ladi. Har chat uchun kamera × xabar turi belgilang, *Sinov xabari* bilan tekshiring.

## 6. Smenalar va hisobotlar
- **Smenalar**: yangi jadval *qachondan kuchga kirishi* bilan saqlanadi — eski ma'lumot o'zgarmaydi. Yarim tundan o'tuvchi smena boshlangan sanaga tegishli.
- **Hisobotlar**: davr, smena, kamera, mahsulot bo'yicha; sanalmagan oraliqlar (kamera uzilgan, train, servis o'chgan) belgilanadi; **Excel** eksport.
