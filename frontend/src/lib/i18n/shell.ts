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
  notifications: "الإشعارات",
  notifFailedLabel: "الإشعارات: تعذر التحميل",
  notifLoadingLabel: "الإشعارات: جارٍ التحميل",
  notifNoneLabel: "الإشعارات: لا جديد",
  notifCountLabel: (n: number) => `الإشعارات: ${n}`,
  forRole: (who: string) => `لدورك: ${who}`,
  remindersOf: (n: number) => `، منها ${n} تذكير`,
  closeNotifications: "إغلاق الإشعارات",
  loadingNotifications: "جارٍ تحميل الإشعارات",
  notificationsFailed: "تعذر تحميل الإشعارات.",
  noNotifications: "لا إشعارات لدورك الآن.",
  noNotificationsHint:
    "يصلك إشعار حين يحين دورك في سلسلة اعتماد، أو حين يتغير طلب قدّمه طرفك. بدّل الدور من أعلى الصفحة لرؤية إشعارات دور آخر.",
  reminder: "تذكير",
  contractWord: "عقد",
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
  notifications: "Notifications",
  notifFailedLabel: "Notifications: could not load",
  notifLoadingLabel: "Notifications: loading",
  notifNoneLabel: "Notifications: nothing new",
  notifCountLabel: (n: number) => `Notifications: ${n}`,
  forRole: (who: string) => `For your role: ${who}`,
  remindersOf: (n: number) => `, ${n} of them ${n === 1 ? "a reminder" : "reminders"}`,
  closeNotifications: "Close notifications",
  loadingNotifications: "Loading notifications",
  notificationsFailed: "Could not load notifications.",
  noNotifications: "No notifications for your role right now.",
  noNotificationsHint:
    "You are notified when it is your turn in an approval chain, or when a request from your party changes. Switch roles at the top of the page to see another role's notifications.",
  reminder: "Reminder",
  contractWord: "Contract",
};

export const shell = { ar, en };
