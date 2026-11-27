# Nosozliklarni bartaraf etish

| Belgi | Tekshirish | Yechim |
|---|---|---|
| Yuqori panelda "N ta muammo" | Panelni bosing — qaysi servis/komponent | `systemctl status fcv-<nom>`, `journalctl -u fcv-<nom> -n 100` |
| Kamera katagida "Aloqa yo'q" | Kamera sahifasi → Oqimlar xatosi | Matn sababni aytadi: login/parol, manzil yo'li, IP/kabel. Kamerani tahrirlab *Tekshirish* |
| ONVIF qidiruvda kamera yo'q | Kamera boshqa tarmoq segmentida / multicast yopiq | IP ni qo'lda kiriting yoki RTSP usulidan foydalaning |
| ONVIF "kamera soati farq qiladi" | — | Avtomatik hisobga olinadi; davom etsa kamera vaqtini NTP ga sozlang |
| Sanash ishlamayapti | Kamera sahifasi → Vazifalar ogohlantirishlari; Sozlash → Mahsulotlar | ROI/chiziq chizilganini, faol modeli bor mahsulot tanlanganini tekshiring. "Train ketmoqda" — navbat tugashini kuting |
| Ko'p "noaniq" sanoq | Sanoqlar jurnali, Modellar → chalkash juftliklar | Chalkashgan mahsulotlarning rasmlarini ko'proq belgilang va qayta train qiling; o'lcham oralig'ini o'rganing |
| O'tkazib yuborilgan sanoqlar | Aniqlikni tekshirish | Chiziqni mahsulot to'liq ko'rinadigan joyga suring; inference fps ni oshiring; GPU yuklamasini tekshiring |
| "Yuklama yuqori — fps pasaytirildi" | Sanash sozlamasi → GPU yuklama | Faol mahsulotlar sonini kamaytiring yoki inference fps ni pasaytiring |
| Model "Qayta qurish kerak" | Drayver/TensorRT yangilangan | Avtomatik navbatga qo'yiladi (Train sahifasida "Engine qayta qurish") |
| Uskuna doim "to'xtagan"/"ishlayapti" | Uskuna sozlamasi → jonli grafik | Harakat chegarasini grafik bo'yicha o'rnating; titrash bo'lsa nazorat zonasi, lampa bo'lsa istisno zonasi qo'shing |
| Sikllar sanalmayapti | Tayanch kadr olinganmi | Uskuna boshlang'ich holatida *Hozirgi kadr*; chegaralarni *Avto-aniqlash* bilan sozlang |
| Telegram xabarlari ketmayapti | Telegram sahifasi holati va "Oxirgi xabarlar" | "Internet yo'q" — xabarlar navbatda, internet qaytganda ketadi. "Token xato" — tokenni qayta kiriting |
| Diskda joy kam | Umumiy sozlamalar → Holat → papkalar | Eski snapshotlarni boshqa diskka ko'chiring yoki disk qo'shing |
| Elektr o'chib yondi | Umumiy sozlamalar → Hodisalar jurnali | Servislar o'zi ishga tushadi; o'chgan vaqt "sanalmagan oraliq" bo'lib yoziladi; to'xtagan train — *Davom ettirish* yoki *Qayta boshlash* |
| Zaxira | Umumiy sozlamalar → Holat → Zaxira | `scripts/backup.sh` (qo'lda), `scripts/backup.sh --verify` (tiklash sinovi). Tiklash: `pg_restore --clean -d f_cv data/backups/db_*.dump` |

Loglar: `data/logs/<servis>.log` (kunlik aylanadi, 30 kun) va `journalctl -u fcv-*`. UI: Umumiy sozlamalar → Xatolar.
