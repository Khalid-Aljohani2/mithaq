/**
 * audit strings: the append-only audit log page. Arabic is the source;
 * English must carry exactly the same keys, which the `typeof ar` annotation
 * enforces.
 */

const ar = {
  whatContract: "العقد",
  loadingContract: "جارٍ تحميل العقد",
  noContract: (id: string) => `لا يوجد عقد بالمرجع ${id}`,
  chooseAbove: "اختر عقدًا من أعلى الصفحة.",
  contractRef: "مرجع العقد",
  title: "سجل التدقيق",
  appendOnly: "سجل إلحاقي: تُضاف القيود بترتيب وقوعها، ولا يُعدَّل قيد ولا يُحذف.",
  loading: "جارٍ تحميل سجل التدقيق",
  what: "سجل التدقيق",
  emptyTitle: "لا قيود بعد على هذا العقد",
  emptyBefore:
    "يُسجَّل هنا كل تغيير في حالة أي طلب: الاستلام، والتحليل، وكل توقيع، وإصدار أمر التغيير.",
  emptyLink: "قدّم طلب تغيير",
  emptyAfter: "ليبدأ السجل.",
  colTime: "الوقت",
  colActor: "المنفذ",
  colAction: "الإجراء",
  colEntity: "الكيان",
  colPrevious: "الحالة السابقة",
  colNew: "الحالة الجديدة",
  colReason: "السبب",
  noReason: "بلا سبب مسجل",
  state: "الحالة",
  stateChange: (from: string, to: string) => `${from} إلى ${to}`,
  noChange: "لا تغيير",
  recommendation: (short: string) => `التوصية: ${short}`,
  none: "لا يوجد",
};

const en: typeof ar = {
  whatContract: "the contract",
  loadingContract: "Loading the contract",
  noContract: (id: string) => `No contract with reference ${id}`,
  chooseAbove: "Choose a contract at the top of the page.",
  contractRef: "Contract reference",
  title: "Audit log",
  appendOnly:
    "Append-only log: entries are added in the order they happen, and no entry is edited or deleted.",
  loading: "Loading the audit log",
  what: "the audit log",
  emptyTitle: "No entries on this contract yet",
  emptyBefore:
    "Every change in a request's state is recorded here: receipt, analysis, each signature and the issue of the variation order.",
  emptyLink: "Submit a change request",
  emptyAfter: "to start the log.",
  colTime: "Time",
  colActor: "Actor",
  colAction: "Action",
  colEntity: "Entity",
  colPrevious: "Previous state",
  colNew: "New state",
  colReason: "Reason",
  noReason: "No reason recorded",
  state: "State",
  stateChange: (from: string, to: string) => `${from} to ${to}`,
  noChange: "No change",
  recommendation: (short: string) => `Recommendation: ${short}`,
  none: "None",
};

export const audit = { ar, en };
