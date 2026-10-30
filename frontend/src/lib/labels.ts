/**
 * Arabic display labels for backend enums and codes.
 *
 * These are names for things, not legal assertions: no percentage, cap or
 * article text is written here. Articles come from the API.
 */

import {
  ApiError,
  type ActorType,
  type AuditAction,
  type NotificationKind,
  type ChangeKind,
  type ContractType,
  type CRState,
  type Party,
  type Recommendation,
  type Role,
  type Stage,
} from "./api";

export type Tone = "neutral" | "seal" | "amber" | "legal";

export const STATE_LABEL: Record<CRState, string> = {
  RECEIVED: "مستلم",
  AWAITING_DOCUMENTS: "بانتظار المستندات",
  IN_ANALYSIS: "قيد التحليل",
  RECOMMENDED: "صدرت التوصية",
  IN_APPROVAL: "قيد الاعتماد",
  REVISION_REQUESTED: "طُلب تعديله",
  REJECTED: "مرفوض",
  CLOSED_IN_SCOPE: "مغلق داخل النطاق",
  APPROVED: "معتمد",
  VO_ISSUED: "صدر أمر التغيير",
  IN_EXECUTION: "قيد التنفيذ",
  CLOSED: "مغلق",
};

export const STATE_TONE: Record<CRState, Tone> = {
  RECEIVED: "neutral",
  AWAITING_DOCUMENTS: "amber",
  IN_ANALYSIS: "neutral",
  RECOMMENDED: "neutral",
  IN_APPROVAL: "neutral",
  REVISION_REQUESTED: "amber",
  REJECTED: "legal",
  CLOSED_IN_SCOPE: "neutral",
  APPROVED: "seal",
  VO_ISSUED: "seal",
  IN_EXECUTION: "seal",
  CLOSED: "neutral",
};

/** Abbreviation (when the kind has one) and its full Arabic name. */
export const KIND: Record<ChangeKind, { abbr: string | null; name: string }> = {
  IN_SCOPE: { abbr: null, name: "داخل نطاق العقد" },
  PCR: { abbr: "PCR", name: "طلب تغيير موجب" },
  NCR: { abbr: "NCR", name: "طلب تغيير سالب" },
  SUBSTITUTION: { abbr: null, name: "إحلال منتج أو مواصفة" },
  UNCLEAR: { abbr: null, name: "لم يُحدَّد النوع" },
};

/** Short label for a kind once its full name has been shown on the screen. */
export function kindShort(kind: ChangeKind | null | undefined): string {
  if (!kind) return "لم يُحلَّل";
  return KIND[kind].abbr ?? KIND[kind].name;
}

/** Full label for a kind: "PCR (طلب تغيير موجب)" or the name alone. */
export function kindFull(kind: ChangeKind | null | undefined): string {
  if (!kind) return "لم يُحلَّل بعد";
  const { abbr, name } = KIND[kind];
  return abbr ? `${abbr} (${name})` : name;
}

/** The terms key shown once at the top of a screen. */
export const TERMS = {
  CR: "طلب تغيير",
  PCR: "طلب تغيير موجب",
  NCR: "طلب تغيير سالب",
  VO: "أمر تغيير",
} as const;
export type Term = keyof typeof TERMS;

export const CONTRACT_TYPE_LABEL: Record<ContractType, string> = {
  GOVERNMENT: "حكومي",
  PRIVATE: "خاص",
};

/** GOVERNMENT_ENTITY is the client side: a government entity or a private owner. */
export function partyLabel(party: Party, contractType: ContractType | undefined): string {
  if (party === "CONTRACTOR") return "المقاول";
  return contractType === "PRIVATE" ? "المالك" : "الجهة الحكومية";
}

/** Used where no contract is in view: names both readings of the client side. */
export function partyLabelNeutral(party: Party): string {
  return party === "CONTRACTOR" ? "المقاول" : "الجهة الحكومية أو المالك";
}

export const ROLE_LABEL: Record<Role, string> = {
  PROJECT_MANAGER: "مدير المشروع",
  TECHNICAL_MANAGER: "المدير الفني",
  FINANCE_MANAGER: "المدير المالي",
  LEGAL_ADVISOR: "المستشار القانوني",
  CEO: "الرئيس التنفيذي",
};

export const PARTIES: readonly Party[] = ["GOVERNMENT_ENTITY", "CONTRACTOR"];
export const ROLES: readonly Role[] = [
  "PROJECT_MANAGER",
  "TECHNICAL_MANAGER",
  "FINANCE_MANAGER",
  "LEGAL_ADVISOR",
  "CEO",
];

export const RECOMMENDATION: Record<
  Recommendation,
  { verb: string; short: string; tone: Tone }
> = {
  APPROVE: { verb: "يوصي الوكيل بالاعتماد", short: "اعتماد", tone: "seal" },
  REJECT: { verb: "يوصي الوكيل بالرفض", short: "رفض", tone: "legal" },
  REQUEST_REVISION: {
    verb: "يوصي الوكيل بطلب تعديل",
    short: "طلب تعديل",
    tone: "amber",
  },
  CLOSE_IN_SCOPE: {
    verb: "يوصي الوكيل بإغلاقه كطلب داخل النطاق",
    short: "إغلاق داخل النطاق",
    tone: "neutral",
  },
};

export const STAGES: readonly { stage: Stage; no: number; name: string; actor: ActorType }[] = [
  { stage: "INTAKE", no: 1, name: "استلام الطلب", actor: "AI" },
  { stage: "DOCUMENT_VALIDATION", no: 2, name: "التحقق من المستندات", actor: "CODE" },
  { stage: "SCOPE_ANALYSIS", no: 3, name: "تحليل النطاق", actor: "AI" },
  { stage: "TECHNICAL_ASSESSMENT", no: 4, name: "التقييم الفني", actor: "AI" },
  { stage: "COST_SCHEDULE_IMPACT", no: 5, name: "أثر التكلفة والمدة", actor: "CODE" },
  { stage: "RISK_COMPLIANCE", no: 6, name: "المخاطر والامتثال", actor: "AI" },
  { stage: "ORCHESTRATOR", no: 7, name: "التوصية الموحدة", actor: "CODE" },
  { stage: "APPROVAL_GATE", no: 8, name: "الاعتماد البشري", actor: "HUMAN" },
  { stage: "ISSUE_VO", no: 9, name: "إصدار أمر التغيير", actor: "HUMAN" },
  { stage: "UPDATE_RECORDS", no: 10, name: "تحديث سجلات المشروع", actor: "CODE" },
  { stage: "EXECUTION_FOLLOW_UP", no: 11, name: "التنفيذ والمتابعة", actor: "HUMAN" },
];

export const ACTOR_LABEL: Record<ActorType, string> = {
  CODE: "قاعدة برمجية",
  AI: "ذكاء اصطناعي",
  HUMAN: "إنسان",
};

/** Why a slot is in the approval chain. */
export const CHAIN_REASON: Record<string, string> = {
  DEFAULT_APPROVER: "المعتمد الافتراضي لكل طلب تغيير.",
  CONTRACTOR_CONSENT: "موافقة المقاول مطلوبة نظامًا لهذا التغيير.",
  TECHNICAL_APPROVAL_REQUIRED: "الطلب يغيّر منتجًا أو مواصفة معتمدة.",
  FINANCE_THRESHOLD: "أثر التكلفة يتجاوز حد الاعتماد المالي.",
  LEGAL_REVIEW_REQUIRED: "الطلب يمس حدًا نظاميًا ويحتاج مراجعة قانونية.",
  POLICY_EXCEPTION: "الطلب يتجاوز حد السياسة الداخلية ويحتاج استثناءً.",
};

/** The orchestrator's reason codes. */
export const REASON_CODE: Record<string, string> = {
  WITHIN_ALL_LIMITS: "ضمن جميع الحدود النظامية وحدود السياسة.",
  IN_SCOPE: "مغطى ببنود العقد الحالية.",
  TECHNICAL_APPROVAL_REQUIRED: "يحتاج اعتمادًا فنيًا لتغييره منتجًا معتمدًا.",
  UNIT_RATE_DEVIATION: "سعر الوحدة المقترح ينحرف عن سعر العقد.",
  NEW_ITEM_RATE_HUMAN_ENTERED: "سعر البند الجديد مُدخل يدويًا ولا يقابله بند في العقد.",
  POLICY_EXCEPTION_REQUIRED: "يتجاوز حد السياسة الداخلية ويحتاج استثناءً.",
  LEGAL_CAP_EXCEEDED: "يتجاوز حدًا نظاميًا.",
  POLICY_EXCEPTION_CANNOT_LIFT_LEGAL_CAP:
    "استثناء السياسة لا يرفع الحد النظامي.",
  DOCUMENTS_MISSING: "المستندات المطلوبة غير مكتملة.",
  LOW_CONFIDENCE: "ثقة التحليل منخفضة وتحتاج مراجعة بشرية.",
  STAGE_CONFLICT: "تعارض بين نتائج المراحل.",
};

/** Ledger scopes and the English article ref the API returns for each (gap 3). */
export const SCOPE: Record<string, { name: string; articleEn: string }> = {
  NEW_ITEMS: { name: "بنود جديدة", articleEn: "Article 67(1)(a)" },
  INCREASE_EXISTING: { name: "زيادة كميات قائمة", articleEn: "Article 67(1)(b)" },
  DECREASE_EXISTING: { name: "تخفيض كميات قائمة", articleEn: "Article 67(1)(c)" },
  NON_FINANCIAL: { name: "تغييرات غير مالية", articleEn: "Article 67(3)" },
  COMBINED: { name: "إجمالي التغييرات", articleEn: "Article 67(2)" },
};

/** What went wrong, and what to do about it. */
export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    switch (error.code) {
      case "NETWORK":
        return "تعذر الوصول إلى الخادم. تحقق من تشغيله ثم أعد المحاولة.";
      case "WRONG_ROLE":
        return "هذه الخطوة ليست لدورك الحالي. بدّل الدور من أعلى الصفحة إلى صاحب الخطوة.";
      case "REASON_REQUIRED":
        return "اكتب سبب القرار، فالرفض وطلب التعديل لا يُقبلان دون سبب.";
      case "NOT_ANALYSABLE":
        return "لا يمكن تحليل الطلب في حالته الحالية. أعد تحميل الصفحة لرؤية حالته.";
      case "NOT_IN_APPROVAL":
        return "الطلب ليس في مسار الاعتماد الآن. أعد تحميل الصفحة لرؤية حالته.";
      case "NO_CHAIN":
        return "لا توجد سلسلة اعتماد لهذا الطلب. حلّل الطلب أولًا.";
      case "CHAIN_COMPLETE":
        return "اكتملت سلسلة الاعتماد بالفعل.";
      case "CR_NOT_FOUND":
        return "لم يُعثر على الطلب. ارجع إلى سجل الطلبات واختر طلبًا آخر.";
      case "CONTRACT_NOT_FOUND":
        return "لم يُعثر على العقد. اختر عقدًا آخر من أعلى الصفحة.";
      case "VALIDATION":
        return `بيانات غير مقبولة: ${error.detail}. صحّح الحقول ثم أعد الإرسال.`;
    }
    if (error.status === 404) return "لم يُعثر على المطلوب. تحقق من الرابط.";
    if (error.status === 429) return "طلبات كثيرة خلال وقت قصير. انتظر دقيقة ثم أعد المحاولة.";
    if (error.status >= 500) return "حدث خطأ في الخادم. أعد المحاولة بعد قليل.";
    return error.detail || `رفض الخادم الطلب (HTTP ${error.status}).`;
  }
  return "حدث خطأ غير متوقع. أعد تحميل الصفحة.";
}

export const NOTIFICATION_KIND: Record<NotificationKind, string> = {
  // The backend also uses this kind for "chain complete", so the label stays neutral.
  APPROVAL_PENDING: "مسار الاعتماد",
  APPROVAL_REMINDER: "تذكير بالاعتماد",
  DOCUMENTS_REQUIRED: "مستندات مطلوبة",
  DOCUMENTS_REMINDER: "تذكير بالمستندات",
  CR_REJECTED: "رُفض الطلب",
  CR_REVISION_REQUESTED: "طُلب تعديل",
  CR_CLOSED_IN_SCOPE: "أُغلق داخل النطاق",
  VO_ISSUED: "صدر أمر التغيير",
};

export const AUDIT_ACTION: Record<AuditAction, string> = {
  CR_RECEIVED: "استلام الطلب",
  CR_ANALYSED: "تحليل الطلب",
  CR_IN_APPROVAL: "بدء مسار الاعتماد",
  CR_STEP_APPROVED: "اعتماد خطوة",
  CR_APPROVED: "اكتمال الاعتماد",
  CR_REJECTED: "رفض الطلب",
  CR_REVISION_REQUESTED: "طلب تعديل",
  VO_ISSUED: "إصدار أمر التغيير",
  EXECUTION_STARTED: "بدء التنفيذ",
  CR_CLOSED: "إغلاق الطلب",
  DEMO_RESET: "إعادة ضبط العرض",
};

/** The audit log's actor: a role name, or CODE for the system itself. */
export function auditActor(actor: string): string {
  if (actor === "CODE") return "النظام";
  if (actor === "AI") return "الوكيل";
  return actor in ROLE_LABEL ? ROLE_LABEL[actor as Role] : actor;
}
