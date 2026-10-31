/**
 * Shell strings: the letterhead, its switchers and toggles, the skip link.
 * Arabic is the source; English must carry exactly the same keys, which the
 * `typeof ar` annotation enforces.
 */

const ar = {
  skipToContent: "انتقل إلى المحتوى",
  homeLabel: "MithaqAi، الصفحة الرئيسية",
  evaluation: "نتائج التقييم",
  contract: "العقد",
  contractsFailed: "تعذر تحميل العقود",
  chooseContract: "اختر عقدًا",
  availableContracts: "العقود المتاحة",
  loadingContracts: "جارٍ تحميل العقود",
  actingAs: "تعمل بصفة",
  roleHint: "يحدد الدور الإجراءات المتاحة لك في سلسلة الاعتماد.",
  party: "الطرف",
  role: "الدور",
  themeToDark: "التبديل إلى الوضع الداكن",
  themeToLight: "التبديل إلى الوضع الفاتح",
  langSwitch: "English",
  langSwitchLabel: "Switch the interface to English",
  originalArabic: "النص الأصلي بالعربية",
};

const en: typeof ar = {
  skipToContent: "Skip to content",
  homeLabel: "MithaqAi, home",
  evaluation: "Evaluation",
  contract: "Contract",
  contractsFailed: "Could not load contracts",
  chooseContract: "Choose a contract",
  availableContracts: "Available contracts",
  loadingContracts: "Loading contracts",
  actingAs: "Acting as",
  roleHint: "Your role decides which approval actions you can take.",
  party: "Party",
  role: "Role",
  themeToDark: "Switch to dark theme",
  themeToLight: "Switch to light theme",
  langSwitch: "العربية",
  langSwitchLabel: "التبديل إلى الواجهة العربية",
  originalArabic: "Original Arabic",
};

export const shell = { ar, en };
