/**
 * workspace strings: the contract workspace and its change request register.
 * Arabic is the source; English must carry exactly the same keys, which the
 * `typeof ar` annotation enforces.
 */

const ar = {
  whatContract: "العقد",
  loadingContract: "جارٍ تحميل العقد",
  noContract: (id: string) => `لا يوجد عقد بالمرجع ${id}`,
  openFirst: "فتح أول عقد متاح",
  chooseFromList: "اختر عقدًا من قائمة العقود أعلى الصفحة.",
  contractRef: "مرجع العقد",
  contractOfType: (type: string) => `عقد ${type}`,
  contractor: "المقاول",
  originalValue: "القيمة الأصلية",
  startDate: "تاريخ البداية",
  endDate: "تاريخ النهاية",
  limitsTitle: "حدود التغيير التراكمية",
  limitsDetails: "تفاصيل الحدود",
  officialText: "النص الرسمي",
  loadingLimits: "جارٍ تحميل الحدود",
  whatLimits: "الحدود",
  limitsIntroGov:
    "المستخدم من حدود السياسة الداخلية ومن كل حد في المادة السابعة والستين، محسوبًا من قيمة العقد ومدته الأصليتين.",
  limitsIntroPrivate:
    "المستخدم من حدود السياسة الداخلية، محسوبًا من قيمة العقد ومدته الأصليتين. حدود المادة السابعة والستين تنطبق على العقود الحكومية.",
  registerTitle: "سجل طلبات التغيير",
  auditLog: "سجل التدقيق",
  newRequest: "طلب تغيير جديد",
  loadingRegister: "جارٍ تحميل سجل الطلبات",
  whatRegister: "سجل الطلبات",
  emptyTitle: "لا توجد طلبات تغيير على هذا العقد",
  submitFirst: "تقديم أول طلب تغيير",
  emptyHint: "كل طلب يُسجَّل هنا بمرجعه وحالته وأثره، ويراه الطرفان معًا.",
  chainComplete: "اكتملت السلسلة",
  approvalNotStarted: "لم يبدأ الاعتماد",
  none: "لا يوجد",
  colRef: "المرجع",
  colState: "الحالة",
  colKind: "النوع",
  colCost: "أثر التكلفة",
  colRecommendation: "التوصية",
  colApprover: "المعتمد الحالي",
  notCalculated: "لم يُحسب",
  awaitingAnalysis: "بانتظار التحليل",
  approverLine: (who: string) => `المعتمد الحالي: ${who}`,
};

const en: typeof ar = {
  whatContract: "the contract",
  loadingContract: "Loading the contract",
  noContract: (id: string) => `No contract with reference ${id}`,
  openFirst: "Open the first available contract",
  chooseFromList: "Choose a contract from the list at the top of the page.",
  contractRef: "Contract reference",
  contractOfType: (type: string) => `${type} contract`,
  contractor: "Contractor",
  originalValue: "Original value",
  startDate: "Start date",
  endDate: "End date",
  limitsTitle: "Cumulative change limits",
  limitsDetails: "Limit details",
  officialText: "Official text",
  loadingLimits: "Loading limits",
  whatLimits: "the limits",
  limitsIntroGov:
    "Usage of the internal policy limits and of every limit in Article 67, calculated from the original contract value and duration.",
  limitsIntroPrivate:
    "Usage of the internal policy limits, calculated from the original contract value and duration. The Article 67 limits apply to government contracts.",
  registerTitle: "Change request register",
  auditLog: "Audit log",
  newRequest: "New change request",
  loadingRegister: "Loading the request register",
  whatRegister: "the request register",
  emptyTitle: "No change requests on this contract",
  submitFirst: "Submit the first change request",
  emptyHint:
    "Every request is recorded here with its reference, state and impact, and both parties see it.",
  chainComplete: "Chain complete",
  approvalNotStarted: "Approval not started",
  none: "None",
  colRef: "Reference",
  colState: "State",
  colKind: "Type",
  colCost: "Cost impact",
  colRecommendation: "Recommendation",
  colApprover: "Current approver",
  notCalculated: "Not calculated",
  awaitingAnalysis: "Awaiting analysis",
  approverLine: (who: string) => `Current approver: ${who}`,
};

export const workspace = { ar, en };
