/**
 * forms strings: the new change request form. Arabic is the source; English
 * must carry exactly the same keys, which the `typeof ar` annotation enforces.
 */

const ar = {
  whatContract: "العقد",
  loadingContract: "جارٍ تحميل العقد",
  noContract: (id: string) => `لا يوجد عقد بالمرجع ${id}`,
  chooseThenSubmit: "اختر عقدًا من قائمة العقود أعلى الصفحة، ثم قدّم الطلب عليه.",
  errName: "اكتب اسم مقدم الطلب.",
  errBody: "اكتب نص الطلب كما ورد، عشرة أحرف على الأقل.",
  errAmount: "اكتب المبلغ بالأرقام، وبحد أقصى منزلتين عشريتين.",
  errRate: "اكتب سعر الوحدة بالأرقام، وبحد أقصى منزلتين عشريتين.",
  errDays: "اكتب عدد الأيام رقمًا صحيحًا.",
  onContract: "على العقد",
  title: "طلب تغيير جديد",
  intro: "يُسجَّل الطلب بمرجع جديد، ثم يحلله الوكيل ويعرض توصيته. لا يُعتمد شيء إلا بتوقيع أصحاب الصلاحية.",
  requester: "مقدم الطلب",
  name: "الاسم",
  party: "الطرف",
  body: "نص الطلب",
  bodyPlaceholder: "الصق نص الطلب كما ورد من مقدمه.",
  attachments: "المرفقات",
  attachmentsHint:
    "حدّد المستندات المرفقة فعلًا. يطابقها الوكيل بقائمة المستندات المطلوبة لنوع الطلب، ويعيد إليك قائمة بالنواقص إن وُجدت.",
  otherAttachment: "اسم مرفق آخر",
  addAttachment: "إضافة المرفق",
  amounts: "المبالغ والمدة",
  amountsRule: "المبالغ يُدخلها الأشخاص دائمًا، ولا يقترحها الوكيل ولا يسعّر بها بندًا.",
  amount: "المبلغ المطلوب",
  rate: "سعر الوحدة المقترح",
  extension: "التمديد المطلوب",
  sar: "ر.س",
  dayUnit: "يوم",
  amountsHint:
    "اترك الحقل فارغًا إذا لم يذكره الطلب. تُحسب التكلفة من الكميات وأسعار العقد، ويُعلَّم أي سعر مُدخل يدويًا.",
  notSubmitted: (error: string) => `لم يُقدَّم الطلب. ${error}`,
  fixFields: "صحّح الحقول المعلَّمة أعلاه ثم قدّم الطلب.",
  submitting: "جارٍ تقديم الطلب",
  submit: "تقديم الطلب وتحليله",
  cancel: "إلغاء",
  step: (n: number) => `البند ${n}`,
};

const en: typeof ar = {
  whatContract: "the contract",
  loadingContract: "Loading the contract",
  noContract: (id: string) => `No contract with reference ${id}`,
  chooseThenSubmit: "Choose a contract from the list at the top of the page, then submit the request on it.",
  errName: "Enter the requester's name.",
  errBody: "Enter the request text as received, at least ten characters.",
  errAmount: "Enter the amount in digits, with at most two decimal places.",
  errRate: "Enter the unit rate in digits, with at most two decimal places.",
  errDays: "Enter the number of days as a whole number.",
  onContract: "On contract",
  title: "New change request",
  intro:
    "The request is recorded with a new reference, then the agent analyses it and gives its recommendation. Nothing is approved without the signatures of the authorised people.",
  requester: "Requester",
  name: "Name",
  party: "Party",
  body: "Request text",
  bodyPlaceholder: "Paste the request text exactly as the requester sent it.",
  attachments: "Attachments",
  attachmentsHint:
    "Tick the documents actually attached. The agent checks them against the documents required for the request type and lists anything missing.",
  otherAttachment: "Name of another attachment",
  addAttachment: "Add attachment",
  amounts: "Amounts and duration",
  amountsRule: "Amounts are always entered by people. The agent never proposes them or uses them to price an item.",
  amount: "Requested amount",
  rate: "Proposed unit rate",
  extension: "Requested extension",
  sar: "SAR",
  dayUnit: "days",
  amountsHint:
    "Leave a field empty if the request does not state it. Cost is calculated from contract quantities and rates, and any rate entered by hand is flagged.",
  notSubmitted: (error: string) => `The request was not submitted. ${error}`,
  fixFields: "Correct the marked fields above, then submit the request.",
  submitting: "Submitting the request",
  submit: "Submit and analyse",
  cancel: "Cancel",
  step: (n: number) => `Step ${n}`,
};

export const forms = { ar, en };
