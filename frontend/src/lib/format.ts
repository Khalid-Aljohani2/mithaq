/**
 * Display formatting. Arabic locale, Western digits, tabular figures (set in CSS).
 *
 * Money and percentages arrive from the API as decimal strings and are handed
 * to Intl as strings, which formats them exactly. Nothing here parses them
 * into a float or does arithmetic on them.
 */

const LOCALE = "ar-SA";

const money = new Intl.NumberFormat(LOCALE, {
  numberingSystem: "latn",
  style: "currency",
  currency: "SAR",
  minimumFractionDigits: 0,
  maximumFractionDigits: 2,
});

const moneySigned = new Intl.NumberFormat(LOCALE, {
  numberingSystem: "latn",
  style: "currency",
  currency: "SAR",
  minimumFractionDigits: 0,
  maximumFractionDigits: 2,
  signDisplay: "exceptZero",
});

const plain = new Intl.NumberFormat(LOCALE, {
  numberingSystem: "latn",
  maximumFractionDigits: 2,
});

const dateFmt = new Intl.DateTimeFormat(LOCALE, {
  numberingSystem: "latn",
  calendar: "gregory",
  day: "numeric",
  month: "long",
  year: "numeric",
});

const dateTimeFmt = new Intl.DateTimeFormat(LOCALE, {
  numberingSystem: "latn",
  calendar: "gregory",
  day: "numeric",
  month: "short",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
});

type Decimal = `${number}` | string;

function asLiteral(value: Decimal): Intl.StringNumericLiteral {
  return value as Intl.StringNumericLiteral;
}

/** "4,800,000 ر.س" style, from a decimal string. */
export function formatMoney(value: Decimal | null | undefined): string {
  if (value === null || value === undefined || value === "") return "غير محدد";
  return money.format(asLiteral(value));
}

/** As formatMoney, with an explicit + or - sign for impacts. */
export function formatImpact(value: Decimal | null | undefined): string {
  if (value === null || value === undefined || value === "") return "غير محدد";
  return moneySigned.format(asLiteral(value));
}

/** A count or quantity from a decimal string. */
export function formatNumber(value: Decimal | number): string {
  return typeof value === "number"
    ? plain.format(value)
    : plain.format(asLiteral(value));
}

/**
 * Wrap a left-to-right run (a number with its sign) in Unicode isolates, so
 * an RTL paragraph cannot reorder "20%" into "%20".
 */
function ltr(text: string): string {
  return `\u2066${text}\u2069`;
}

/** "21.0000" -> "21%". The value is already a percentage. */
export function formatPct(value: Decimal | null | undefined): string {
  if (value === null || value === undefined || value === "") return "بلا حد";
  return ltr(`${plain.format(asLiteral(value))}%`);
}

/** A confidence in [0, 1] as a string ("0.88") shown as "88%". */
export function formatConfidence(value: string | null | undefined): string {
  if (!value || !/^\d+(\.\d*)?$/.test(value)) return "غير محددة";
  // Shift the decimal point two places as text, so no float is involved.
  const [int, frac = ""] = value.split(".");
  const digits = frac.padEnd(2, "0");
  const whole = Number(int) * 100 + Number(digits.slice(0, 2));
  const rest = digits.slice(2).replace(/0+$/, "");
  return ltr(`${plain.format(asLiteral(rest ? `${whole}.${rest}` : `${whole}`))}%`);
}

export function formatDate(value: string): string {
  return dateFmt.format(new Date(value));
}

export function formatDateTime(value: string): string {
  return dateTimeFmt.format(new Date(value));
}

export function formatDays(days: number | null | undefined): string {
  if (days === null || days === undefined) return "غير محدد";
  if (days === 0) return "بلا أثر على المدة";
  const n = plain.format(Math.abs(days));
  const sign = days > 0 ? "+" : "-";
  if (Math.abs(days) === 1) return `${sign}يوم واحد`;
  if (Math.abs(days) === 2) return `${sign}يومان`;
  return `${sign}${n} ${Math.abs(days) <= 10 ? "أيام" : "يومًا"}`;
}

/** Arabic count agreement for "request": 1, 2, 3 to 10, 11 and up. */
export function countRequests(n: number): string {
  if (n === 1) return "طلب واحد";
  if (n === 2) return "طلبان";
  if (n >= 3 && n <= 10) return `${plain.format(n)} طلبات`;
  return `${plain.format(n)} طلبًا`;
}

/** As countRequests, for audit log entries (قيد). */
export function countEntries(n: number): string {
  if (n === 1) return "قيد واحد";
  if (n === 2) return "قيدان";
  if (n >= 3 && n <= 10) return `${plain.format(n)} قيود`;
  return `${plain.format(n)} قيدًا`;
}

export function formatDuration(ms: number): string {
  if (ms < 1000) return `${plain.format(ms)} ملّي ث`;
  return `${plain.format(Math.round(ms / 100) / 10)} ث`;
}
