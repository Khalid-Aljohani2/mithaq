"use client";

import type { CSSProperties } from "react";

import type { LedgerResponse, UsageSnapshot } from "@/lib/api";
import { formatMoney, formatPct } from "@/lib/format";
import { SCOPE } from "@/lib/labels";
import { cn } from "@/lib/utils";

/** Order in which the scopes are listed: the categories, then the total. */
const ORDER = ["NEW_ITEMS", "INCREASE_EXISTING", "DECREASE_EXISTING", "NON_FINANCIAL", "COMBINED"];

/** True when the API reports negative headroom, i.e. the cap is exceeded. */
function overCap(s: UsageSnapshot): boolean {
  return Boolean(s.headroom_pct?.trim().startsWith("-"));
}

/**
 * Article 67 limits as ruled meters (government contracts only).
 *
 * The track runs to 1.5x the cap, so the cap tick always sits two thirds of
 * the way along. Widths are computed by CSS `calc()` straight from the API's
 * percentage strings: JavaScript never turns a percentage into a float.
 */
export function LimitsSummary({ ledger }: { ledger: LedgerResponse }) {
  const usage = ledger.usage as Record<string, UsageSnapshot | undefined>;
  const scopes = ORDER.flatMap((key) => {
    const s = usage[key];
    return s ? [{ key, s }] : [];
  });

  return (
    <div>
      <ul className="divide-y divide-rule border-y border-rule">
        {scopes.map(({ key, s }) => (
          <li
            key={key}
            className="grid grid-cols-[1fr_auto] items-center gap-x-6 gap-y-2 py-3 md:grid-cols-[7.5rem_10rem_1fr_15rem]"
          >
            <span className="margin-ref order-3 col-span-2 md:order-none md:col-span-1">
              <span className="ref">{SCOPE[key]?.articleEn ?? key}</span>
            </span>
            <span
              className={cn(
                "text-sm font-medium",
                key === "COMBINED" && "font-semibold",
              )}
            >
              {SCOPE[key]?.name ?? key}
            </span>
            <span className="order-4 col-span-2 md:order-none md:col-span-1">
              {s.cap_pct ? (
                <Meter snapshot={s} />
              ) : (
                <span className="text-xs text-ink-muted">بلا حد نسبي</span>
              )}
            </span>
            <span className="text-end text-sm">
              <span className={cn("font-medium", overCap(s) && "text-legal")}>
                {formatPct(s.before_pct)}
              </span>
              {s.cap_pct && (
                <span className="text-ink-muted"> من {formatPct(s.cap_pct)}</span>
              )}
              <span className="block text-xs text-ink-muted">
                {formatMoney(s.before_value)}
                {s.cap_value && <> من {formatMoney(s.cap_value)}</>}
              </span>
            </span>
          </li>
        ))}
      </ul>
      <MeterKey />
    </div>
  );
}

function Meter({ snapshot: s }: { snapshot: UsageSnapshot }) {
  const over = overCap(s);
  const style = {
    "--cap": s.cap_pct ?? "0",
    "--used": s.before_pct,
    "--pending": s.pending_pct,
  } as CSSProperties;
  const label = `المستخدم ${formatPct(s.before_pct)}، والمعلّق ${formatPct(
    s.pending_pct,
  )}، والحد ${formatPct(s.cap_pct)}`;

  return (
    <span
      role="img"
      aria-label={label}
      style={style}
      className="relative block h-5 [--scale:calc(var(--cap)*1.5)]"
    >
      {/* Track */}
      <span className="absolute inset-x-0 top-1/2 h-2 -translate-y-1/2 border border-rule-strong bg-sheet" />
      {/* Used */}
      <span
        className={cn(
          "absolute start-0 top-1/2 h-2 -translate-y-1/2",
          over ? "bg-legal" : "bg-ink",
        )}
        style={{
          inlineSize: "calc(min(var(--used), var(--scale)) / var(--scale) * 100%)",
        }}
      />
      {/* Pending, hatched, after the used part */}
      <span
        className="hatch absolute top-1/2 h-2 -translate-y-1/2"
        style={{
          insetInlineStart: "calc(min(var(--used), var(--scale)) / var(--scale) * 100%)",
          inlineSize:
            "calc(min(var(--pending), max(var(--scale) - var(--used), 0)) / var(--scale) * 100%)",
        }}
      />
      {/* Cap tick at two thirds of the track */}
      <span
        className="absolute inset-y-0 w-0.5 bg-ink"
        style={{ insetInlineStart: "calc(100% / 1.5)" }}
      />
    </span>
  );
}

function MeterKey() {
  return (
    <p className="mt-3 flex flex-wrap items-center gap-x-5 gap-y-1 text-xs text-ink-muted">
      <span className="inline-flex items-center gap-1.5">
        <span aria-hidden className="inline-block h-2 w-5 bg-ink" />
        المعتمد
      </span>
      <span className="inline-flex items-center gap-1.5">
        <span aria-hidden className="hatch inline-block h-2 w-5 border border-rule-strong" />
        قيد الاعتماد
      </span>
      <span className="inline-flex items-center gap-1.5">
        <span aria-hidden className="inline-block h-3 w-0.5 bg-ink" />
        الحد النظامي
      </span>
    </p>
  );
}
