/**
 * project strings: the new project form and its AI draft. Arabic is the
 * source; English must carry exactly the same keys, which the `typeof ar`
 * annotation enforces.
 */

const ar = {
  margin: "مشروع جديد",
  title: "مشروع جديد",
  intro:
    "سجّل العقد وجدول كمياته ليبدأ له سجل تغييرات واحد يراه الطرفان. لا يُحفظ شيء إلا عند الضغط على إنشاء المشروع.",
  newProject: "مشروع جديد",
  step: (n: number) => `الخطوة ${n}`,

  // Upload and AI draft
  uploadMargin: "مسودة",
  uploadTitle: "رفع تفاصيل المشروع",
  uploadHint:
    "ارفع ملف PDF للعقد أو الصق نصه، ويقترح الذكاء الاصطناعي تعبئة النموذج. المسودة لا تُحفظ، وكل حقل مقترح يبقى معلَّمًا حتى تراجعه.",
  pdf: "ملف PDF",
  pdfTooLarge: "حجم الملف أكبر من 10 ميغابايت. اختر ملفًا أصغر أو الصق النص.",
  pdfNotPdf: "الملف ليس PDF.",
  pdfChosen: (name: string) => `الملف المختار: ${name}`,
  clearFile: "إزالة الملف",
  or: "أو",
  pasteText: "نص العقد",
  pastePlaceholder: "الصق نص العقد أو تفاصيل المشروع هنا.",
  draft: "اقترح تعبئة النموذج بالذكاء الاصطناعي",
  drafting: "جارٍ إعداد المسودة",
  draftNeedsInput: "ارفع ملفًا أو الصق نصًا أولًا.",
  draftFailed: (error: string) => `تعذّر إعداد المسودة. ${error}`,
  draftDone: (n: number) => `عُبّئ ${n} حقلًا مقترحًا. راجع كل حقل معلَّم قبل الإنشاء.`,
  draftNotes: "ملاحظات المسودة",
  draftModel: (model: string, version: string) => `النموذج ${model}، نسخة التعليمات ${version}`,
  aiDraft: "مسودة ذكاء اصطناعي",
  confirm: "تأكيد",
  confirmAll: "تأكيد كل الحقول المقترحة",
  unconfirmed: (n: number) =>
    `${n} حقلًا اقترحها الذكاء الاصطناعي ولم تُراجع بعد. لا يُحفظ شيء إلا عند الإنشاء.`,
  readFailed: "تعذّرت قراءة الملف.",

  // Sections
  parties: "العقد والطرفان",
  valueAndDates: "القيمة والمدة",
  breakdown: "جدول الكميات",
  breakdownHint:
    "يُحسب إجمالي كل بند ومجموع الجدول بالضبط من الكمية وسعر الوحدة. يجب أن يساوي المجموع قيمة العقد تمامًا.",
  creator: "المُنشئ",

  // Fields
  titleAr: "عنوان العقد",
  entityGov: "الجهة الحكومية",
  entityPrivate: "المالك",
  contractor: "المقاول",
  contractType: "نوع العقد",
  government: "حكومي",
  private: "خاص",
  originalValue: "قيمة العقد",
  startDate: "تاريخ البدء",
  endDate: "تاريخ الانتهاء",
  createdBy: "اسمك",
  createdByHint: "يُسجَّل في سجل التدقيق بوصفه منشئ المشروع.",
  sar: "ر.س",

  // Breakdown columns
  description: "الوصف",
  unit: "الوحدة",
  quantity: "الكمية",
  unitRate: "سعر الوحدة",
  approvedProduct: "المنتج المعتمد",
  restrictions: "القيود",
  restrictionsHint: "قيد في كل سطر",
  optional: "اختياري",
  lineTotal: "الإجمالي",
  line: (n: number) => `البند ${n}`,
  addLine: "إضافة بند",
  removeLine: (n: number) => `حذف البند ${n}`,
  grandTotal: "مجموع الجدول",
  difference: "الفرق عن قيمة العقد",
  matches: "المجموع يساوي قيمة العقد.",
  notComputable: "يُحسب بعد تصحيح الأرقام",

  // Validation
  errRequired: "هذا الحقل مطلوب.",
  errMoney: "اكتب المبلغ بالأرقام، وبحد أقصى منزلتين عشريتين.",
  errPositive: "يجب أن تكون القيمة أكبر من صفر.",
  errQuantity: "اكتب الكمية بالأرقام، وبحد أقصى أربع منازل عشرية، أكبر من صفر.",
  errDate: "اختر التاريخ.",
  errEndBeforeStart: "يجب أن يكون تاريخ الانتهاء بعد تاريخ البدء.",
  errNoLines: "أضف بندًا واحدًا على الأقل.",
  errSum: "مجموع الجدول لا يساوي قيمة العقد.",
  fixFields: "صحّح الحقول التالية ثم أنشئ المشروع:",
  notCreated: (error: string) => `لم يُنشأ المشروع. ${error}`,

  // Persona
  cannotCreate:
    "إنشاء المشروع للجهة الحكومية فقط، بدور مدير المشروع أو الرئيس التنفيذي.",
  actAsPm: "العمل بصفة الجهة الحكومية، مدير المشروع",

  create: "إنشاء المشروع",
  creating: "جارٍ إنشاء المشروع",
  cancel: "إلغاء",
};

const en: typeof ar = {
  margin: "New project",
  title: "New project",
  intro:
    "Register the contract and its bill of quantities to open one change ledger that both parties see. Nothing is saved until you press Create project.",
  newProject: "New project",
  step: (n: number) => `Step ${n}`,

  uploadMargin: "Draft",
  uploadTitle: "Upload project details",
  uploadHint:
    "Upload the contract as a PDF or paste its text, and the AI proposes how to fill in the form. The draft is not saved, and every proposed field stays marked until you review it.",
  pdf: "PDF file",
  pdfTooLarge: "The file is larger than 10 MB. Choose a smaller file or paste the text.",
  pdfNotPdf: "The file is not a PDF.",
  pdfChosen: (name: string) => `Chosen file: ${name}`,
  clearFile: "Remove file",
  or: "or",
  pasteText: "Contract text",
  pastePlaceholder: "Paste the contract text or the project details here.",
  draft: "Draft the form with AI",
  drafting: "Drafting",
  draftNeedsInput: "Upload a file or paste text first.",
  draftFailed: (error: string) => `The draft could not be prepared. ${error}`,
  draftDone: (n: number) =>
    `${n} proposed ${n === 1 ? "field was" : "fields were"} filled in. Review each marked field before creating the project.`,
  draftNotes: "Draft notes",
  draftModel: (model: string, version: string) => `Model ${model}, prompt version ${version}`,
  aiDraft: "AI draft",
  confirm: "Confirm",
  confirmAll: "Confirm all drafted fields",
  unconfirmed: (n: number) =>
    `${n} ${n === 1 ? "field was" : "fields were"} drafted by AI and not reviewed yet. Nothing is saved until you create the project.`,
  readFailed: "The file could not be read.",

  parties: "Contract and parties",
  valueAndDates: "Value and duration",
  breakdown: "Bill of quantities",
  breakdownHint:
    "Each line total and the grand total are calculated exactly from quantity and unit rate. The grand total must equal the contract value exactly.",
  creator: "Created by",

  titleAr: "Contract title",
  entityGov: "Government entity",
  entityPrivate: "Owner",
  contractor: "Contractor",
  contractType: "Contract type",
  government: "Government",
  private: "Private",
  originalValue: "Contract value",
  startDate: "Start date",
  endDate: "End date",
  createdBy: "Your name",
  createdByHint: "Recorded in the audit log as the person who created the project.",
  sar: "SAR",

  description: "Description",
  unit: "Unit",
  quantity: "Quantity",
  unitRate: "Unit rate",
  approvedProduct: "Approved product",
  restrictions: "Restrictions",
  restrictionsHint: "One per line",
  optional: "optional",
  lineTotal: "Total",
  line: (n: number) => `Line ${n}`,
  addLine: "Add line",
  removeLine: (n: number) => `Remove line ${n}`,
  grandTotal: "Grand total",
  difference: "Difference from contract value",
  matches: "The grand total equals the contract value.",
  notComputable: "Calculated once the numbers are corrected",

  errRequired: "This field is required.",
  errMoney: "Enter the amount in digits, with at most two decimal places.",
  errPositive: "The value must be greater than zero.",
  errQuantity: "Enter the quantity in digits, with at most four decimal places, greater than zero.",
  errDate: "Choose the date.",
  errEndBeforeStart: "The end date must be after the start date.",
  errNoLines: "Add at least one line.",
  errSum: "The grand total does not equal the contract value.",
  fixFields: "Correct the following fields, then create the project:",
  notCreated: (error: string) => `The project was not created. ${error}`,

  cannotCreate:
    "Only the government entity can create a project, acting as project manager or CEO.",
  actAsPm: "Act as Government entity, Project manager",

  create: "Create project",
  creating: "Creating the project",
  cancel: "Cancel",
};

export const project = { ar, en };
