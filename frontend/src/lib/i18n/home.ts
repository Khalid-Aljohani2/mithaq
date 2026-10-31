/**
 * home strings. Arabic is the source; English must carry exactly the same
 * keys, which the `typeof ar` annotation enforces.
 */

const ar = {
  tagline: "عقد واحد، وطرفان، وسجل واحد لكل تغيير.",
  whatMargin: "التعريف",
  what:
    "ميثاق وكيل عربي لحوكمة أوامر التغيير في العقود الحكومية السعودية. يخدم طرفي العقد نفسه، الجهة الحكومية والمقاول، بسجل تغييرات واحد يرى فيه كل طرف المجاميع والحدود ذاتها.",
  principleMargin: "مبدأ الضبط",
  principleHeading: "من يفعل ماذا",
  principle: [
    { label: "الذكاء الاصطناعي يقرأ", body: "يقرأ الطلب ويطابقه ببنود العقد ويصوغ المستندات ويوصي ويشرح السبب." },
    { label: "الكود يقرر المال والنظام", body: "كل مبلغ ونسبة وحد نظامي يحسبه الكود من نص النظام، مع ذكر المادة." },
    { label: "الأشخاص يعتمدون", body: "لا يتغير اعتماد ولا يصدر أمر تغيير إلا بتوقيع شخص مخوَّل." },
  ],
  evalMargin: "التقييم",
  evalHeading: "النتيجة المقيسة",
  evalWhat: "نتيجة التقييم",
  recAccuracy: "دقة التوصية",
  onSplit: (cases: number) => `على عينة اختبار محجوزة من ${cases} حالة`,
  injection: "محاولات حقن الأوامر المردودة",
  notMeasured: "لم يُنشر قياس بعد.",
  evalLink: "تفاصيل التقييم",
  entriesMargin: "البدء",
  startDemo: "ابدأ العرض الموجَّه",
  openContract: "افتح عقدًا",
  noContracts: "لا توجد عقود بعد",
};

const en: typeof ar = {
  tagline: "One contract. Two parties. One record of every change.",
  whatMargin: "About",
  what:
    "MithaqAi is an Arabic-first change-order governance agent for Saudi government contracts. It serves both parties of the same contract, the government entity and the contractor, through one change ledger that shows each side the same totals and limits.",
  principleMargin: "Control principle",
  principleHeading: "Who does what",
  principle: [
    { label: "AI reads", body: "It reads the request, matches it to the contract, drafts documents, recommends and explains why." },
    { label: "Code decides money and law", body: "Every amount, percentage and legal limit is computed by code from the regulation text, with its article." },
    { label: "People approve", body: "No approval changes and no variation order is issued without an authorised person's signature." },
  ],
  evalMargin: "Evaluation",
  evalHeading: "Measured result",
  evalWhat: "the evaluation result",
  recAccuracy: "Recommendation accuracy",
  onSplit: (cases: number) => `on a held-out test split of ${cases} cases`,
  injection: "Prompt injection attempts turned away",
  notMeasured: "No measurement has been published yet.",
  evalLink: "Evaluation details",
  entriesMargin: "Start",
  startDemo: "Start the guided demo",
  openContract: "Open a contract",
  noContracts: "No contracts yet",
};

export const home = { ar, en };
