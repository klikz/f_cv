# Dataset qo'llanmasi: snapshot olish va mahsulotlarni belgilash

Model mahsulotni faqat siz ko'rsatgan misollardan o'rganadi. Har bir rasmda mahsulot atrofiga ramka chizasiz va qaysi mahsulot ekanini aytasiz. Ramkalar qanchalik aniq va xilma-xil bo'lsa, sanoq shunchalik to'g'ri chiqadi.

## 1. Tayyorgarlik

1. **Mahsulot katalogda bo'lsin**: **Mahsulotlar → Qo'shish**.
2. **Kamerada ROI chizilgan bo'lsin**: kamera → **Sanash sozlamalari → ROI**. ROI — konveyerning mahsulot o'tadigan qismi. ROI bo'lmasa ham ishlaydi, lekin unda faqat butun kadr olinadi.

## 2. Snapshot olish

1. **Dataset** sahifasini oching.
2. Filtrdan **kamerani** tanlang — ostida jonli video chiqadi (ROI uzuq chiziq bilan ko'rsatiladi).
3. Filtrdan **mahsulotni** tanlang. Shundan keyin olingan rasmlar shu mahsulotga biriktiriladi va ro'yxatda faqat shu mahsulot rasmlari ko'rinadi.
4. **Snapshot hududi**ni tanlang:
   - **ROI** (tavsiya etiladi) — faqat ROI atrofidagi kesim saqlanadi; xiralashmagan oq ramka ichidagi qism. Model ishlayotganda ham aynan shu kesimni ko'radi, mahsulot rasmda kattaroq chiqadi va belgilash osonroq.
   - **Butun kadr** — butun tasvir. ROI hali chizilmagan bo'lsa yoki ROI keyin o'zgarishi mumkin bo'lsa.
5. Mahsulot ROI ichida ko'ringan paytda **Snapshot olish** tugmasini yoki **S** ni bosing. Rasm darhol ro'yxatda paydo bo'ladi.

**Qanday rasmlar kerak** — bir xil rasmlarni ko'paytirgandan ko'ra xilma-xillik muhimroq:

- mahsulot ROI ning turli joylarida (kirishda, o'rtada, chiqishda);
- turli burilishlarda, qutili va qutisiz holda;
- bir nechta mahsulot yonma-yon va bir-biriga tegib turgan holatlar;
- turli yorug'lik: kunduzi, kechasi, chiroq yoqilgan/o'chgan;
- **bo'sh konveyer** rasmlari ham kerak (negativ namuna — model "hech narsa yo'q" holatini ham o'rganadi). Taxminan har 5–10 rasmdan bittasi bo'sh bo'lsin.

Ko'p rasm kerak bo'lsa, **Avto-yig'ish**ni yoqing: ROI da harakat bo'lganda har N soniyada o'zi rasm oladi, deyarli bir xil kadrlarni tashlab yuboradi. Avto-yig'ilgan rasmlar mahsulotga biriktirilmaydi — ular mahsulot filtrida belgilangandan keyin ko'rinadi.

## 3. Belgilash

**Belgilanmagan** yorlig'ini tanlang va **Belgilashni boshlash** tugmasini bosing (yoki istalgan rasmni bosing). Belgilash oynasi ochiladi; filtrdagi mahsulot avtomatik tanlangan bo'ladi.

### Har bir rasmda

1. **Mahsulotni tanlang** — o'ng paneldan, **1–9** (oxirgi ishlatilganlar) yoki **/** bilan qidiring.
2. **Ramka chizing** — rasmning bo'sh joyida sichqonchani bosib sudrang.
3. Kerak bo'lsa **ramkani tuzating** — bosib tanlang, burchaklaridan cho'zing yoki surib qo'ying.
4. Tanlangan ramka uchun belgilar:
   - **B** — qutili / qutisiz;
   - **T** — boshqa mahsulotga tegib turibdi;
   - **Delete** — ramkani o'chirish.
5. Rasmdagi **har bir** mahsulot nusxasini belgilang, so'ng **→** yoki **D** — saqlash va keyingi rasm.

Mahsulot umuman yo'q rasm uchun **E** (bo'sh rasm / negativ) bosing va keyingisiga o'ting.

### Ramka chizish qoidalari

- **Zich chizing**: ramka mahsulotning chetidan-chetiga, ortiqcha fonsiz, lekin mahsulotning biror qismini kesmasdan.
- **Har bir nusxa — alohida ramka.** Ikki mahsulot tegib tursa ham ikkita ramka chizing va **T** belgilang. Bir nechta mahsulotni bitta ramkaga olmang.
- **Qisman ko'ringan mahsulot** (kadr yoki ROI chetida, boshqa narsa to'sib turgan): taxminan yarmidan ko'pi ko'rinsa — faqat ko'rinadigan qismini belgilang; juda oz ko'rinsa — belgilamang. Butun kadrli rasmda ramka ROI kesimiga 30% dan kam tushsa, u train'ga kirmaydi.
- **Hech birini tashlab ketmang.** Belgilanmagan mahsulot model uchun "bu mahsulot emas" degan noto'g'ri saboq bo'ladi. Ishonchingiz komil bo'lmagan rasmni o'chirib yuborgan ma'qul.
- **Nomi to'g'ri bo'lsin**: o'xshash mahsulotlarda (bir xil shakl, boshqa o'lcham/rang) ayniqsa ehtiyot bo'ling.

### Tezlashtiruvchi tugmalar

| Tugma | Vazifasi |
|---|---|
| sudrash | yangi ramka |
| **1–9** | mahsulot (oxirgi ishlatilganlar) |
| **/** | mahsulot qidirish |
| **→ / D** | saqlash va keyingi |
| **← / A** | saqlash va oldingi |
| **Enter** | barcha ramkalarni tasdiqlash va keyingi |
| **C** | oldingi rasm ramkalarini nusxalash (ketma-ket deyarli bir xil kadrlarda qulay) |
| **E** | bo'sh rasm (negativ) |
| **B / T** | qutili-qutisiz / tegib turgan |
| **Delete** | tanlangan ramkani o'chirish |
| **Ctrl+Z** | bekor qilish |
| g'ildirak / **0** | zoom / zoomni tiklash |
| **Probel** + sudrash | zoomda rasmni surish |
| **?** | barcha tugmalar |

## 4. Avto-belgilash bilan tezlashtirish

Hamma rasmni qo'lda belgilash shart emas:

1. Mahsulotga **~30 ta** rasmni qo'lda belgilang.
2. **Train → Yangi train → Tez qoralama** — tezkor model o'qitiladi.
3. **Dataset → Avto-belgilash** — mahsulotni tanlang; model belgilanmagan rasmlarga ramka taklif qiladi.
4. **Avto** yorlig'ini oching. Takliflar uzuq chiziq va ishonch foizi bilan ko'rinadi:
   - to'g'ri bo'lsa — **Enter** (tasdiqlash va keyingi);
   - noto'g'ri bo'lsa — ramkani tuzating, o'chiring yoki yangisini chizing, so'ng **→**;
   - ko'p rasm bo'lsa — **Ishonchlilarini tasdiqlash** (ishonchi ≥70%). Shundan keyin ham bir qismini tanlab ko'zdan kechiring.

Train'ga faqat **tasdiqlangan** ramkalar kiradi.

## 5. Qachon yetarli?

Sahifa tepasidagi **Tayyorlik indikatori** har mahsulot bo'yicha tasdiqlangan ramkalar sonini ko'rsatadi:

| Holat | Tasdiqlangan ramka |
|---|---|
| Yetarli emas | 50 dan kam |
| Minimal | 50 – 119 |
| Tayyor | 120 va undan ko'p |

Shuningdek tekshiring:

- **Kameralar** ustuni — mahsulot ishlatiladigan har bir kameradan rasm bormi;
- **Qutili / qutisiz** — ikkala holat ham uchraydigan bo'lsa, ikkalasidan ham misol bormi;
- **Negativ** — bo'sh rasmlar bormi.

"Tayyor" bo'lgach — **Train → Yangi train → To'liq train**.

## 6. Ko'p uchraydigan xatolar

- **Bir rasmdagi barcha mahsulotlarni belgilamaslik** — eng zararli xato; model ularni fon deb o'rganadi.
- **Bir xil rasmlar** — 100 ta deyarli bir xil kadrdan ko'ra 30 ta turli kadr foydaliroq.
- **Faqat kunduzgi rasmlar** — model kechasi yomon ishlaydi.
- **Bo'sh rasmlarning yo'qligi** — model fondagi narsalarni mahsulot deb sanay boshlaydi.
- **ROI ni o'zgartirib, eski rasmlarni qoldirish** — ROI rejimida olingan eski kesimlar yangi ROI ga mos kelmaydi. ROI sezilarli o'zgarsa, shu kamera uchun yangi snapshotlar oling.
