/**
 * demo strings. Arabic is the source; English must carry exactly the same
 * keys, which the `typeof ar` annotation enforces.
 */

type Act = { title: string; line: string; notes: string[] };

const ar = {
  pageTitle: "العرض الموجَّه",
  pageIntro:
    "ستة فصول تمر على المنتج كاملًا. كل فصل يضبط صفة المستخدم ويفتح الشاشة المناسبة، فلا يحتاج المقدّم إلى ضبطها يدويًا.",
  margin: "فصول العرض",
  actsHeading: "الفصول",
  start: "ابدأ العرض",
  resume: "متابعة العرض",
  actLabel: "الفصل",
  actOf: (n: number, total: number) => `الفصل ${n} من ${total}`,
  prev: "السابق",
  next: "التالي",
  go: "اذهب",
  notes: "ملاحظات المقدّم",
  hideNotes: "إخفاء الملاحظات",
  leave: "إنهاء العرض",
  barLabel: "شريط العرض الموجَّه",
  openEighth: "افتح الطلب الثامن",
  resetMargin: "وضع العرض",
  resetHeading: "إعادة الضبط",
  resetIntro:
    "تعيد البيانات إلى حالتها الأولى، أو تحمّل حالة التجزئة: سبعة أوامر تغيير معتمدة وطلب ثامن ينقصه توقيع واحد. سجل التدقيق لا يُحذف منه شيء.",
  reset: "إعادة ضبط العرض",
  salami: "تحميل حالة التجزئة",
  working: "جارٍ التنفيذ",
  doneReset: "أُعيدت البيانات إلى حالتها الأولى.",
  doneSalami: "حُمّلت حالة التجزئة.",
  dismiss: "إغلاق",
  resetFailed: "تعذرت إعادة الضبط.",
  noVoYet:
    "لم يصدر أمر تغيير لهذا الطلب بعد، ففُتح الطلب نفسه. أكمل مسار الاعتماد ثم أصدر الأمر.",
  noSalami:
    "حالة التجزئة غير محمّلة في هذا المتصفح. حمّلها من شريط العرض أولًا ليظهر الطلب الثامن.",
  acts: [
    {
      title: "العقد وحدوده",
      line: "ملف العقد الحكومي وسجله الموحد وطبقتا الحدود.",
      notes: [
        "عقد واحد وطرفان وسجل واحد. لا توجد دفاتر ثانية.",
        "طبقتان من الحدود: سياسة الجهة، ويمكن لدور مسمّى تجاوزها، والمادة 67 وهي مانعة وتذكر مادتها.",
        "الدخول بالصفة بديل مؤقت عن تسجيل الدخول، والخادم هو من يفرض صلاحيات الأدوار.",
      ],
    },
    {
      title: "طلب جديد ومراحله الإحدى عشرة",
      line: "المقاول يفتح طلب استبدال منتج ويشغّل التحليل.",
      notes: [
        "اضغط تحليل الطلب. مع المزوّد المباشر يستغرق نحو 25 ثانية.",
        "في المرحلة 3 وجد النموذج البند المطابق وشرح السبب بالعربية.",
        "المرحلة 5 كود لا نموذج: 540,000 خارج و672,000 داخل.",
        "سعر الوحدة 56,000 مقابل 45,000 انحراف 24.44%، فوق حد السياسة 20%.",
      ],
    },
    {
      title: "التوصية ومسار الاعتماد",
      line: "الجهة الحكومية توقّع، ثم يوقّع المدير الفني.",
      notes: [
        "ابدأ مسار الاعتماد، ثم اكتب الاسم واضغط اعتماد. يظهر الختم بالاسم والوقت.",
        "التوقيع التالي للمدير الفني: بدّل الصفة من أعلى الصفحة.",
        "الوكيل أوصى ولم يعتمد شيئًا. كل توقيع لشخص.",
      ],
    },
    {
      title: "مستند أمر التغيير",
      line: "القيم والمواد من الكود، وفقرة النطاق وحدها من النموذج.",
      notes: [
        "الكود جمع القيم والإحالات إلى المواد، والنموذج صاغ فقرة النطاق فقط.",
        "اضغط طباعة: صفحة A4 واحدة بلا عناصر الواجهة.",
      ],
    },
    {
      title: "حالة التجزئة",
      line: "ثمانية طلبات سليمة، والثامن يُرفض بسبب السبعة قبله.",
      notes: [
        "المادة 67(1)(ب): 945,000 من 960,000 معتمد، والمتبقي 15,000.",
        "سبعة أوامر تغيير بقيمة 135,000 لكل منها، وكل واحد منها سليم وحده.",
        "افتح الطلب الثامن بصفة المستشار القانوني، واكتب الاسم واضغط اعتماد: يُرفض ويُحال إلى المراجعة القانونية.",
        "عد إلى صفحة الحدود: ما زال 945,000. لم يتغير شيء.",
      ],
    },
    {
      title: "النتائج المقيسة",
      line: "دقة التوصية على عينة اختبار محجوزة، قابلة للتتبع إلى إيداع.",
      notes: [
        "دقة التوصية على عينة الاختبار المحجوزة، مع صفر أخطاء.",
        "محاولات حقن الأوامر رُدّت كلها.",
        "القياس منشور، والتسميات التي غيّرناها منشورة مع سببها.",
      ],
    },
  ] as Act[],
};

const en: typeof ar = {
  pageTitle: "Guided demo",
  pageIntro:
    "Six acts that walk through the whole product. Each act sets the persona and opens the right screen, so the presenter never sets them by hand.",
  margin: "Run of show",
  actsHeading: "Acts",
  start: "Start",
  resume: "Resume",
  actLabel: "Act",
  actOf: (n: number, total: number) => `Act ${n} of ${total}`,
  prev: "Previous",
  next: "Next",
  go: "Go",
  notes: "Presenter notes",
  hideNotes: "Hide notes",
  leave: "Leave demo",
  barLabel: "Guided demo bar",
  openEighth: "Open the eighth request",
  resetMargin: "Demo mode",
  resetHeading: "Reset",
  resetIntro:
    "Restore the seed state, or load the salami preset: seven approved variation orders and an eighth request one signature short. Audit rows are never deleted.",
  reset: "Reset demo",
  salami: "Load salami preset",
  working: "Working",
  doneReset: "The seed state was restored.",
  doneSalami: "The salami preset was loaded.",
  dismiss: "Dismiss",
  resetFailed: "The reset failed.",
  noVoYet:
    "No variation order has been issued for this request yet, so the request itself is open. Complete the approval chain, then issue the order.",
  noSalami:
    "The salami preset has not been loaded in this browser. Load it from the demo bar first to reach the eighth request.",
  acts: [
    {
      title: "The contract and its limits",
      line: "The government contract file, its shared ledger and both layers of limits.",
      notes: [
        "One contract, two parties, one record. Nobody keeps a second set of books.",
        "Two layers of limits: organisation policy, which a named role can escalate past, and Article 67, which blocks and cites its article.",
        "The persona switch stands in for sign-in. The backend enforces every role check.",
      ],
    },
    {
      title: "A new request and its 11 stages",
      line: "The contractor opens a product substitution and runs the analysis.",
      notes: [
        "Click Analyse. With the live provider it takes about 25 seconds.",
        "Stage 3: the model found the matching line and explained why, in Arabic.",
        "Stage 5 is code, not the model: 540,000 out, 672,000 in.",
        "Unit rate 56,000 against 45,000 is a 24.44% deviation, above the 20% policy limit.",
      ],
    },
    {
      title: "The recommendation and the approval chain",
      line: "The government entity signs, then the technical manager.",
      notes: [
        "Start approval, type a name and approve. The seal stamps the name and time.",
        "The technical manager signs next: switch persona at the top of the page.",
        "The agent recommended. It approved nothing. Every signature is a person's.",
      ],
    },
    {
      title: "The variation order",
      line: "Values and articles come from code; only the scope paragraph from the model.",
      notes: [
        "Code assembled the values and the citations. The model drafted only the scope paragraph.",
        "Click Print: one A4 page, no app chrome.",
      ],
    },
    {
      title: "The salami case",
      line: "Eight sound requests. The eighth is refused because of the seven before it.",
      notes: [
        "Article 67(1)(b): 945,000 of 960,000 approved, 15,000 left.",
        "Seven variation orders of 135,000 each, each legitimate on its own.",
        "Open the eighth request as Legal advisor, type a name and approve: refused and sent to legal review.",
        "Back on the limits page: still 945,000. Nothing moved.",
      ],
    },
    {
      title: "Measured results",
      line: "Recommendation accuracy on a held-out split, traceable to a commit.",
      notes: [
        "Recommendation accuracy on the held-out test split, with zero errors.",
        "Every prompt injection attempt was turned away.",
        "The measurement is published, with the labels we changed and why.",
      ],
    },
  ],
};

export const demo = { ar, en };
