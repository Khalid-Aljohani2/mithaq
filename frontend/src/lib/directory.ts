import type { Party, Role } from "./api";
import type { Lang } from "./i18n";

/**
 * A fictional directory of signatories, used only to prefill the signing
 * name when the backend reports demo mode. Every name stays editable, and
 * without demo mode nothing is prefilled.
 */
const DIRECTORY: Partial<Record<Party, Partial<Record<Role, { ar: string; en: string }>>>> = {
  GOVERNMENT_ENTITY: {
    PROJECT_MANAGER: { ar: "ريم الشهري", en: "Reem Al-Shehri" },
    FINANCE_MANAGER: { ar: "ماجد الحربي", en: "Majed Al-Harbi" },
    CEO: { ar: "عبدالرحمن المطيري", en: "Abdulrahman Al-Mutairi" },
    LEGAL_ADVISOR: { ar: "لمى الزهراني", en: "Lama Al-Zahrani" },
    TECHNICAL_MANAGER: { ar: "هدى الغامدي", en: "Huda Al-Ghamdi" },
  },
  CONTRACTOR: {
    PROJECT_MANAGER: { ar: "فهد القحطاني", en: "Fahad Al-Qahtani" },
    TECHNICAL_MANAGER: { ar: "نورة الدوسري", en: "Nora Al-Dosari" },
  },
};

export function demoSignatory(party: Party, role: Role, lang: Lang): string | null {
  return DIRECTORY[party]?.[role]?.[lang] ?? null;
}
