/**
 * Display formatting in the interface language's locale, Western digits,
 * tabular figures (set in CSS).
 *
 * Money and percentages arrive from the API as decimal strings and are handed
 * to Intl as strings, which formats them exactly. Nothing here parses them
 * into a float or does arithmetic on them.
 */

import { getDict, getLang } from "./prefs";

const LOCALES = { ar: "ar-SA", en: "en-GB" } as const;

/**
 * One formatter per language, built on first use. The language is read at
 * call time, so a language change needs no reload.
 */
function perLang<T>(make: (locale: string) => T): () => T {
  const cache: Partial<Record<keyof typeof LOCALES, T>> = {};
  return () => {
    const lang = getLang();
    return (cache[lang] ??= make(LOCALES[lang]));
  };
}

const money = perLang((locale) => new Intl.NumberFormat(locale, {
  numberingSystem: "latn",
  style: "currency",
  currency: "SAR",
  minimumFractionDigits: 0,
  maximumFractionDigits: 2,
}));

const moneySigned = perLang((locale) => new Intl.NumberFormat(locale, {
  numberingSystem: "latn",
  style: "currency",
  currency: "SAR",
  minimumFractionDigits: 0,
  maximumFractionDigits: 2,
  signDisplay: "exceptZero",
}));

const plain = perLang((locale) => new Intl.NumberFormat(locale, {
  numberingSystem: "latn",
  maximumFractionDigits: 2,
}));

const dateFmt = perLang((locale) => new Intl.DateTimeFormat(locale, {
  numberingSystem: "latn",
  calendar: "gregory",
  day: "numeric",
  month: "long",
  year: "numeric",
}));

const dateTimeFmt = perLang((locale) => new Intl.DateTimeFormat(locale, {
  numberingSystem: "latn",
  calendar: "gregory",
  day: "numeric",
  month: "short",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
}));

type Decimal = `${number}` | string;

function asLiteral(value: Decimal): Intl.StringNumericLiteral {
  return value as Intl.StringNumericLiteral;
}

/** "4,800,000 ر.س" style, from a decimal string. */
export function formatMoney(value: Decimal | null | undefined): string {
  if (value === null || value === undefined || value === "") return getDict().common.notSet;
  return money().format(asLiteral(value));
}

const moneyExact = perLang((locale) => new Intl.NumberFormat(locale, {
  numberingSystem: "latn",
  style: "currency",
  currency: "SAR",
  minimumFractionDigits: 2,
  maximumFractionDigits: 6,
}));

const moneyExactSigned = perLang((locale) => new Intl.NumberFormat(locale, {
  numberingSystem: "latn",
  style: "currency",
  currency: "SAR",
  minimumFractionDigits: 2,
  maximumFractionDigits: 6,
  signDisplay: "exceptZero",
}));

/**
 * As formatMoney, without rounding: every decimal of an exact line total is
 * shown (up to six), so a total that misses the value by a fraction says so.
 */
export function formatMoneyExact(value: Decimal, signed = false): string {
  return (signed ? moneyExactSigned() : moneyExact()).format(asLiteral(value));
}

/** As formatMoney, with an explicit + or - sign for impacts. */
export function formatImpact(value: Decimal | null | undefined): string {
  if (value === null || value === undefined || value === "") return getDict().common.notSet;
  return moneySigned().format(asLiteral(value));
}

/** A count or quantity from a decimal string. */
export function formatNumber(value: Decimal | number): string {
  return typeof value === "number"
    ? plain().format(value)
    : plain().format(asLiteral(value));
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
  if (value === null || value === undefined || value === "") return getDict().common.noLimit;
  return ltr(`${plain().format(asLiteral(value))}%`);
}

/** A confidence in [0, 1] as a string ("0.88") shown as "88%". */
export function formatConfidence(value: string | null | undefined): string {
  if (!value || !/^\d+(\.\d*)?$/.test(value)) return getDict().common.notSetFem;
  // Shift the decimal point two places as text, so no float is involved.
  const [int, frac = ""] = value.split(".");
  const digits = frac.padEnd(2, "0");
  const whole = Number(int) * 100 + Number(digits.slice(0, 2));
  const rest = digits.slice(2).replace(/0+$/, "");
  return ltr(`${plain().format(asLiteral(rest ? `${whole}.${rest}` : `${whole}`))}%`);
}

export function formatDate(value: string): string {
  return dateFmt().format(new Date(value));
}

export function formatDateTime(value: string): string {
  return dateTimeFmt().format(new Date(value));
}

export function formatDays(days: number | null | undefined): string {
  if (days === null || days === undefined) return getDict().common.notSet;
  const c = getDict().common;
  if (days === 0) return c.noScheduleImpact;
  const sign = days > 0 ? "+" : "-";
  return `${sign}${c.days(days, plain().format(Math.abs(days)))}`;
}

/** Request count with agreement: Arabic 1, 2, 3 to 10, 11 and up; English plural. */
export function countRequests(n: number): string {
  return getDict().common.requests(n, plain().format(n));
}

/** As countRequests, for audit log entries (قيد). */
export function countEntries(n: number): string {
  return getDict().common.entries(n, plain().format(n));
}

/**
 * Exact decimal division for display, e.g. total cost over case count. Done
 * on scaled integers (BigInt), so no binary float enters the result.
 */
export function divideDecimal(value: string, divisor: number, places = 4): string | null {
  const m = /^(-?)(\d+)(?:\.(\d+))?$/.exec(value.trim());
  if (!m || !Number.isInteger(divisor) || divisor <= 0) return null;
  const [, sign, int, frac = ""] = m;
  // BigInt() rather than `10n` literals: the tsconfig target is ES2017.
  const ten = BigInt(10);
  const scale = ten ** BigInt(places);
  const scaled = BigInt(int + frac.padEnd(places, "0").slice(0, places));
  const q = ((scaled * ten) / BigInt(divisor) + BigInt(5)) / ten; // round half up
  const whole = q / scale;
  const rest = (q % scale).toString().padStart(places, "0");
  return `${sign}${whole}.${rest}`;
}

const usd = perLang((locale) => new Intl.NumberFormat(locale, {
  numberingSystem: "latn",
  minimumFractionDigits: 2,
  maximumFractionDigits: 4,
}));

/** "$0.0841", kept left to right inside right-to-left text. */
export function formatUsd(value: string | null | undefined): string {
  if (!value) return getDict().common.notAvailable;
  return ltr(`$${usd().format(asLiteral(value))}`);
}

export function formatDuration(ms: number): string {
  const c = getDict().common;
  if (ms < 1000) return c.ms(plain().format(ms));
  return c.seconds(plain().format(Math.round(ms / 100) / 10));
}
