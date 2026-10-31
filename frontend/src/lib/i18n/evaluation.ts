/**
 * evaluation strings: the published evaluation page (FR-17).
 * Arabic is the source; English must carry exactly the same keys, which the
 * `typeof ar` annotation enforces.
 */

const ar = {
  loading: "جارٍ تحميل نتائج التقييم",
  what: "نتائج التقييم",
  emptyTitle: "لم يُنشر تقييم بعد",
  emptyBody: "يظهر هنا آخر تقييم منشور حين يُشغَّل على مجموعة الاختبار وتُنشر نتيجته.",
  notAvailable: "غير متاح",

  fields: {
    in_scope: "قرار النطاق: هل الطلب مغطى بالعقد؟",
    kind: "نوع التغيير",
    matched_line_ids: "البنود المطابقة في العقد",
    changes_approved_product: "هل يغيّر منتجًا معتمدًا؟",
    recommendation: "التوصية النهائية",
  } as Record<string, string>,

  kicker: "نتيجة التقييم",
  headline: (pct: string, n: string) =>
    `أصابت توصية الوكيل في ${pct} من ${n} طلب تغيير لم تُستخدم في ضبطه.`,
  lede: (passed: string, total: string, errors: string) =>
    `طلبات اختبار عربية محجوزة، لكل منها إجابة صحيحة معروفة سلفًا. صمد الوكيل أمام ${passed} من ${total} محاولات لتمرير تعليمات مدسوسة في نص الطلب، وانتهى التشغيل ${errors}.`,
  noRunErrors: "دون أي خطأ تشغيل",
  runErrors: (n: string) => `${n} أخطاء تشغيل`,

  labelsTitle: "الدقة قبل تدقيق الإجابات الصحيحة وبعده",
  labelsMargin: "تشغيل واحد، مُقيَّم مرتين",
  labelsIntro:
    "راجعنا إجابات صحيحة بدت خاطئة قبل إعادة التشغيل، وأبقينا الأصلية. كل رقم يظهر مرتين: مقابل الإجابات الأصلية، ومقابل المدققة. الفرق بين العمودين هو أثر التدقيق وحده.",
  auditLink: "أسباب التدقيق لكل حالة",
  auditedCases: "(الحالات المدققة:",
  listSep: "، ",
  colStage: "المرحلة",
  colMeasure: "ما يُقاس",
  colOriginal: "الإجابات الأصلية",
  colAudited: "بعد التدقيق",

  speedTitle: "الزمن والتكلفة",
  requests: (n: string) => `${n} طلبًا`,
  p50: "الزمن الوسيط لتحليل طلب",
  p95: "زمن 95% من الطلبات أقل من",
  costPerRequest: "تكلفة الطلب الواحد",
  costTotal: "تكلفة التشغيل كله",
  tokens: (input: string, output: string) => `الرموز: ${input} مدخلة، و${output} مخرجة.`,
  costNote: "تكلفة الطلب هي تكلفة التشغيل مقسومة على عدد الطلبات.",
  stageLatency: "زمن كل مرحلة",
  colActor: "المنفذ",
  colMedian: "الوسيط",
  colP95: "95%",
  actorAi: "ذكاء اصطناعي",
  actorCode: "قاعدة برمجية",

  modelsTitle: "مقارنة النماذج الأربعة",
  modelsBadge: "لا يقدّمها الخادم بعد",
  modelsBody:
    "قورنت أربعة نماذج على مجموعة الاختبار نفسها قبل اختيار النموذج المعتمد. جدول المقارنة منشور في مستند المقارنة ولا تقدّمه الواجهة البرمجية بعد، لذا لا ننسخ أرقامه هنا.",
  modelsLink: "مستند مقارنة النماذج",

  methodTitle: "كيف بُنيت مجموعة التقييم",
  methodMargin: "الطريقة",
  byConstruction: "الإجابة الصحيحة بالبناء لا بالحكم. ",
  byConstructionBody:
    "كُتب كل طلب على بند معروف من العقد ونتيجة مقصودة سلفًا، فإجابته هي ما بُني ليكونه، لا ما قاله نموذج عنه.",
  separation: "فصل الضبط عن الاختبار. ",
  separationBody: (dev: string, test: string) =>
    `ضُبطت التعليمات على مجموعة التطوير (${dev} طلبًا) وحدها، ولم تُفتح مجموعة الاختبار (${test} طلبًا) إلا بعد آخر تعديل، ولم يُغيَّر شيء بعد تشغيلها.`,
  promptVersions: "نسخة التعليمات المقيسة. ",
  listEnd: ".",

  source: "المصدر: الإيداع",
  unknown: "غير معروف",
  generatedAt: (date: string) => `بتاريخ ${date}`,
  model: "النموذج",
  split: (name: string) => `مجموعة ${name}`,
  testSplit: "الاختبار",
};

const en: typeof ar = {
  loading: "Loading evaluation results",
  what: "the evaluation results",
  emptyTitle: "No evaluation published yet",
  emptyBody: "The latest published evaluation appears here once it has been run on the test set and its result published.",
  notAvailable: "Not available",

  fields: {
    in_scope: "Scope decision: is the request covered by the contract?",
    kind: "Type of change",
    matched_line_ids: "Matched contract items",
    changes_approved_product: "Does it change an approved product?",
    recommendation: "Final recommendation",
  },

  kicker: "Evaluation result",
  headline: (pct: string, n: string) =>
    `The agent's recommendation was correct in ${pct} of ${n} change requests not used to tune it.`,
  lede: (passed: string, total: string, errors: string) =>
    `Held-out Arabic test requests, each with a correct answer known in advance. The agent resisted ${passed} of ${total} attempts to pass instructions hidden in the request text, and the run finished ${errors}.`,
  noRunErrors: "with no run errors",
  runErrors: (n: string) => `with ${n} run errors`,

  labelsTitle: "Accuracy before and after auditing the correct answers",
  labelsMargin: "One run, scored twice",
  labelsIntro:
    "Before rerunning, we reviewed correct answers that looked wrong, and kept the originals. Every figure appears twice: against the original answers and against the audited ones. The difference between the two columns is the effect of the audit alone.",
  auditLink: "Audit reasons for each case",
  auditedCases: "(Audited cases:",
  listSep: ", ",
  colStage: "Stage",
  colMeasure: "What is measured",
  colOriginal: "Original answers",
  colAudited: "After audit",

  speedTitle: "Time and cost",
  requests: (n: string) => `${n} requests`,
  p50: "Median time to analyse a request",
  p95: "95% of requests finish within",
  costPerRequest: "Cost per request",
  costTotal: "Cost of the full run",
  tokens: (input: string, output: string) => `Tokens: ${input} input, ${output} output.`,
  costNote: "Cost per request is the run cost divided by the number of requests.",
  stageLatency: "Time per stage",
  colActor: "Performed by",
  colMedian: "Median",
  colP95: "95%",
  actorAi: "AI",
  actorCode: "Code rule",

  modelsTitle: "Comparison of the four models",
  modelsBadge: "Not yet served by the backend",
  modelsBody:
    "Four models were compared on the same test set before the approved model was chosen. The comparison table is published in the comparison document and is not yet served by the API, so its figures are not copied here.",
  modelsLink: "Model comparison document",

  methodTitle: "How the evaluation set was built",
  methodMargin: "Method",
  byConstruction: "Correct by construction, not by judgement. ",
  byConstructionBody:
    "Each request was written against a known contract item with an intended outcome set in advance, so its answer is what it was built to be, not what a model said about it.",
  separation: "Tuning kept apart from testing. ",
  separationBody: (dev: string, test: string) =>
    `The instructions were tuned on the development set (${dev} requests) only. The test set (${test} requests) was opened only after the last change, and nothing was changed after it ran.`,
  promptVersions: "Instruction versions measured. ",
  listEnd: ".",

  source: "Source: commit",
  unknown: "unknown",
  generatedAt: (date: string) => `on ${date}`,
  model: "Model",
  split: (name: string) => `${name} set`,
  testSplit: "Test",
};

export const evaluation = { ar, en };
