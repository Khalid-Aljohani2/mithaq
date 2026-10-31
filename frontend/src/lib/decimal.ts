/**
 * Exact decimal arithmetic on strings, for the money a person types into a
 * form. Values are held as BigInt integers scaled by 10^places, in the style
 * of `divideDecimal` in format.ts. No value ever passes through a float.
 */

// BigInt() rather than `10n` literals: the tsconfig target is ES2017.
const TEN = BigInt(10);
const ZERO = BigInt(0);

/** Quantity (4 places) times unit rate (2 places) lands on 6 places. */
export const TOTAL_PLACES = 6;

/** A plain non-negative decimal with at most `places` decimals, else null. */
export function scaled(value: string, places: number): bigint | null {
  const m = /^(\d+)(?:\.(\d+))?$/.exec(value.trim());
  if (!m) return null;
  const [, int, frac = ""] = m;
  if (frac.length > places) return null;
  return BigInt(int + frac.padEnd(places, "0"));
}

/** Back to a decimal string, trailing zeros after the point trimmed. */
export function unscale(value: bigint, places: number): string {
  const negative = value < ZERO;
  const abs = negative ? -value : value;
  const scale = TEN ** BigInt(places);
  const whole = (abs / scale).toString();
  const rest = (abs % scale).toString().padStart(places, "0").replace(/0+$/, "");
  return `${negative ? "-" : ""}${whole}${rest ? `.${rest}` : ""}`;
}

/** quantity x unit rate, exact, at TOTAL_PLACES. Null when either is not a number. */
export function lineTotal(quantity: string, unitRate: string): bigint | null {
  const q = scaled(quantity, 4);
  const r = scaled(unitRate, 2);
  if (q === null || r === null) return null;
  return q * r;
}

/** A money string (at most 2 places) at TOTAL_PLACES, for comparison with totals. */
export function moneyAtTotalScale(value: string): bigint | null {
  const v = scaled(value, 2);
  return v === null ? null : v * TEN ** BigInt(TOTAL_PLACES - 2);
}
