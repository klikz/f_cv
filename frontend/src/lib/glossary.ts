/**
 * Atamalar lug'ati — butun tizimda bir xil ishlatiladigan o'zbekcha UI atamalari (PLAN.md 4.1.1).
 * Texnik atama ishlatilganda yonida (?) belgisi shu izohni ko'rsatadi: <Term id="roi" />.
 */
export const glossary = {
  analysisStream: {
    term: 'Tahlil oqimi',
    hint: "Kameraning qaysi oqimi (asosiy yoki sub) sanash va uskuna tahlili uchun ishlatiladi. Shakllar shu oqim kadri ustiga chiziladi.",
  },
  mainStream: {
    term: 'Asosiy oqim',
    hint: "Kameraning yuqori sifatli oqimi (main, 1080p/4MP). Aniqlik yuqori, lekin dekod qimmatroq.",
  },
  subStream: {
    term: 'Sub oqim',
    hint: "Kameraning past sifatli qo'shimcha oqimi. Kameralar panelida ko'rsatish uchun ishlatiladi.",
  },
  roi: {
    term: 'ROI hududi',
    hint: "Kadrdagi tahlil qilinadigan soha (poligon). Undan tashqaridagi narsalar hisobga olinmaydi.",
  },
  countLine: {
    term: "Kesib o'tish chizig'i",
    hint: "Mahsulot shu chiziqni kesib o'tganda sanaladi. Strelka sanash yo'nalishini ko'rsatadi.",
  },
  direction: {
    term: "Yo'nalish",
    hint: "Qaysi tomonga kesib o'tish sanaladi: A→B, B→A yoki ikkalasi (alohida hisob).",
  },
  uncertainCount: {
    term: 'Noaniq sanoq',
    hint: "Tizim mahsulot turini ishonchli aniqlay olmagan sanoq. Sanoqlar jurnalida to'g'rilanadi.",
  },
  controlZone: {
    term: 'Nazorat zonasi',
    hint: "Uskunadan tashqaridagi qo'zg'almas joy. Kamera titrasa, shu zonadagi harakat umumiy harakatdan ayiriladi.",
  },
  excludeZone: {
    term: 'Istisno zonasi',
    hint: "Harakati hisobga olinmaydigan joy (masalan, miltillovchi lampa).",
  },
  cycle: {
    term: 'Sikl',
    hint: "Uskunaning bitta to'liq ish harakati (masalan, press bir marta tushib-ko'tarilishi).",
  },
  referenceCycle: {
    term: 'Etalon sikl vaqti',
    hint: "Normal sikl davomiyligi. Undan sezilarli uzoq sikllar mikro-to'xtash hisoblanadi.",
  },
  homePosition: {
    term: 'Tayanch holat',
    hint: "Uskunaning boshlang'ich (\"uy\") ko'rinishi. Sikl — shu holatdan chiqib, unga qaytish.",
  },
  fovMatch: {
    term: "Ko'rish maydoni bir xil",
    hint: "Asosiy va sub oqim kadri bir xil sohani ko'rsatadi. Belgilansa, AI qatlami sub oqim ustida to'g'ri chiziladi.",
  },
  aiVision: {
    term: 'AI Vision',
    hint: "Video ustida ROI, chiziq, aniqlangan mahsulotlar va harakat sohalarini ko'rsatish.",
  },
  coverageGap: {
    term: 'Sanalmagan oraliq',
    hint: "Kamera uzilgan, train ketgan yoki servis o'chgan vaqt. Bu oraliqda ma'lumot to'liq emas.",
  },
  modelVersion: {
    term: 'Model versiyasi',
    hint: "Mahsulot modelining train qilingan nusxasi. Faqat bitta versiya faol bo'ladi.",
  },
  engine: {
    term: 'Engine',
    hint: "GPU da tez ishlashi uchun TensorRT formatiga o'girilgan model.",
  },
  packaging: {
    term: 'Qadoq holati',
    hint: 'Mahsulot qutida yoki qutisiz ekanligi.',
  },
  readiness: {
    term: 'Tayyorlik',
    hint: "Mahsulotni train qilish uchun yetarli belgilangan rasm bor-yo'qligi (tavsiya ≥100–150 ta ramka).",
  },
  shiftDate: {
    term: 'Smena sanasi',
    hint: "Yarim tundan o'tuvchi smena boshlangan sana. Masalan 19:00–08:00 smenasidagi 00:30 dagi sanoq kechagi sanaga tegishli.",
  },
  heartbeat: {
    term: 'Servis holati',
    hint: "Har servis har 2 soniyada \"tirikman\" signali yuboradi. Signal kelmay qolsa, servis javob bermayapti deb ko'rsatiladi.",
  },
} as const satisfies Record<string, { term: string; hint: string }>

export type GlossaryId = keyof typeof glossary
