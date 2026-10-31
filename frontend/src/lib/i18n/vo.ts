/**
 * vo strings: the variation order document and the VO block in the case file.
 * Arabic is the source; English must carry exactly the same keys, which the
 * `typeof ar` annotation enforces. The VO is a formal document, so the
 * English keeps a formal register.
 */

const ar = {
  // Page states
  what: "أمر التغيير",
  noContract: (id: string) => `لا يوجد عقد بالمرجع ${id}`,
  chooseContract: "اختر عقدًا من أعلى الصفحة.",
  loading: "جارٍ تحميل أمر التغيير",
  notFound: (id: string) => `لا يوجد أمر تغيير بالمرجع ${id}`,
  backToRequests: "العودة إلى سجل الطلبات",
  notFoundHint: "يصدر أمر التغيير بعد اكتمال سلسلة الاعتماد. افتح الطلب المعتمد وأصدره من ملفه.",

  // Toolbar
  caseFile: "ملف الطلب",
  recorded: "صياغة مسجلة",
  print: "طباعة",

  // Letterhead
  contractLine: (type: string) => `عقد ${type} رقم`,
  title: "أمر تغيير",
  issuedFrom: "VO (أمر تغيير)، صادر عن الطلب",
  number: "الرقم",
  date: "التاريخ",
  firstParty: (client: string) => `الطرف الأول، ${client}`,
  secondParty: "الطرف الثاني، المقاول",

  // Sections
  scopeTitle: "وصف التغيير",
  linesTitle: "البنود المتأثرة وأسعار العقد",
  noLines: "لا يقابل هذا الأمر بندًا قائمًا في جدول الكميات، فهو بند جديد.",
  colItem: "البند",
  colDescription: "الوصف",
  colQuantity: "الكمية",
  colUnitRate: "سعر الوحدة في العقد",
  valueTitle: "القيمة والمدة",
  value: "قيمة الأمر",
  extension: "تمديد المدة",
  valueNote: "حسبت القيمة قاعدة برمجية من الكميات وأسعار العقد، واعتمدها أصحاب الصلاحية أدناه.",
  articlesTitle: "المواد النظامية المستشهد بها",
  noArticles: "لا يستشهد هذا الأمر بمواد نظامية.",
  signatures: "التواقيع",
  signer: (role: string, party: string) => `${role}، ${party}`,
  footerBefore: "صدر هذا الأمر في MithaqAi بعد اكتمال سلسلة الاعتماد للطلب",
  footerAfter: ". يوصي الوكيل ويصوغ، ولا يُلزم شيء إلا بتوقيع أصحاب الصلاحية أعلاه.",

  // VO block in the case file
  issueTitle: "إصدار أمر التغيير",
  issueIntro:
    "اكتملت سلسلة الاعتماد. يصدر VO (أمر تغيير) بالقيمة والمدة المعتمدتين، ويحمل تواقيع السلسلة وختم الاعتماد.",
  issue: "إصدار أمر التغيير",
  issuing: "جارٍ إصدار أمر التغيير",
  issueFailed: (reason: string) => `لم يصدر أمر التغيير. ${reason}`,
  issued: "صدر VO (أمر تغيير)",
  issuedNumber: "رقم",
  issuedSummary: (date: string, value: string, days: string) =>
    `بتاريخ ${date}، بقيمة ${value}، و${days}.`,
  view: "عرض أمر التغيير وطباعته",
  loadFailed: (reason: string) => `تعذر تحميل أمر التغيير. ${reason}`,
};

const en: typeof ar = {
  what: "the variation order",
  noContract: (id: string) => `No contract with reference ${id}`,
  chooseContract: "Choose a contract at the top of the page.",
  loading: "Loading the variation order",
  notFound: (id: string) => `No variation order with reference ${id}`,
  backToRequests: "Back to change requests",
  notFoundHint:
    "A variation order is issued once the approval chain is complete. Open the approved change request and issue it from its case file.",

  caseFile: "Case file",
  recorded: "Recorded wording",
  print: "Print",

  contractLine: (type: string) => `${type} contract no.`,
  title: "Variation Order",
  issuedFrom: "VO, issued from change request",
  number: "No.",
  date: "Date",
  firstParty: (client: string) => `First party, ${client}`,
  secondParty: "Second party, Contractor",

  scopeTitle: "Description of the change",
  linesTitle: "Affected items and contract rates",
  noLines: "This order does not correspond to an existing item in the bill of quantities; it is a new item.",
  colItem: "Item",
  colDescription: "Description",
  colQuantity: "Quantity",
  colUnitRate: "Contract unit rate",
  valueTitle: "Value and time",
  value: "Order value",
  extension: "Time extension",
  valueNote:
    "The value was calculated by a code rule from the contract quantities and rates, and approved by the authorised signatories below.",
  articlesTitle: "Articles cited",
  noArticles: "This order cites no articles.",
  signatures: "Signatures",
  signer: (role: string, party: string) => `${role}, ${party}`,
  footerBefore: "This order was issued in MithaqAi after the approval chain was completed for change request",
  footerAfter:
    ". The agent recommends and drafts; nothing is binding without the signatures of the authorised signatories above.",

  issueTitle: "Issue the variation order",
  issueIntro:
    "The approval chain is complete. The VO is issued at the approved value and time, and carries the chain's signatures and the approval seal.",
  issue: "Issue variation order",
  issuing: "Issuing the variation order",
  issueFailed: (reason: string) => `The variation order was not issued. ${reason}`,
  issued: "VO issued",
  issuedNumber: "no.",
  issuedSummary: (date: string, value: string, days: string) =>
    `Dated ${date}, value ${value}, ${days}.`,
  view: "View and print the variation order",
  loadFailed: (reason: string) => `Could not load the variation order. ${reason}`,
};

export const vo = { ar, en };
