"use client";

import { useEffect, useState, type CSSProperties } from "react";

import { ArabicOriginal } from "@/components/original";
import { Badge } from "@/components/ui/badge";
import type { CapLine, LedgerResponse, UsageSnapshot } from "@/lib/api";
import { compareDecimal, formatImpact, formatMoney, formatNumber, formatPct } from "@/lib/format";
import { ROLE_LABEL, SCOPE_NAME, SOURCE_LABEL, type Tone } from "@/lib/labels";
import { getDict, getLang, useT } from "@/lib/prefs";
import { cn } from "@/lib/utils";

/**
 * One limit, whatever its source, in the shape the meters draw. Every value is
 * the API's own string: nothing here is computed in JavaScript.
 */
export type Limit = {
  key: string;
  name: string;
  source: string;
  /** Arabic citation, e.g. the article; null for policy limits. */
  citeAr: string | null;
  citeEn: string | null;
  capPct: string | null;
  capValue: string | null;
  usedPct: string;
  usedValue: string;
  pendingPct: string;
  pendingValue: string;
  headroomPct: string | null;
  headroomValue: string | null;
  unit: "SAR" | "days";
  /** Law is blocking (red); policy past its cap needs an exception (amber). */
  overTone: Tone;
  exceptionRole: string | null;
  description: string | null;
};

const LAW_ORDER = ["NEW_ITEMS", "INCREASE_EXISTING", "DECREASE_EXISTING", "NON_FINANCIAL", "COMBINED"];
const POLICY_ORDER = ["cost_increase", "time_extension"];

export function policyLimits(ledger: LedgerResponse): Limit[] {
  const usage = ledger.policy_usage as Record<string, CapLine | undefined>;
  return POLICY_ORDER.flatMap((key) => {
    const c = usage[key];
    if (!c) return [];
    return [
      {
        key,
        name: SCOPE_NAME[key] ?? key,
        source: c.source,
        citeAr: null,
        citeEn: null,
        capPct: c.cap_pct,
        capValue: c.cap_value,
        usedPct: c.used_pct,
        usedValue: c.used_value,
        pendingPct: c.pending_pct,
        pendingValue: c.pending_value,
        headroomPct: c.headroom_pct,
        headroomValue: c.headroom_value,
        unit: c.unit === "days" ? "days" : "SAR",
        overTone: c.blocking ? "legal" : "amber",
        exceptionRole: c.exception_role,
        description:
          getLang() === "en" && c.description_en ? c.description_en : c.description_ar,
      },
    ];
  });
}

export function lawLimits(ledger: LedgerResponse): Limit[] {
  if (!ledger.legal_limits_apply) return [];
  const usage = ledger.usage as Record<string, UsageSnapshot | undefined>;
  return LAW_ORDER.flatMap((key) => {
    const s = usage[key];
    if (!s) return [];
    return [
      {
        key,
        name: SCOPE_NAME[key] ?? key,
        source: s.source ?? "law",
        citeAr: s.article_ref_ar ?? null,
        citeEn: s.article_ref_en ?? null,
        capPct: s.cap_pct,
        capValue: s.cap_value,
        usedPct: s.before_pct,
        usedValue: s.before_value,
        pendingPct: s.pending_pct,
        pendingValue: s.pending_value,
        headroomPct: s.headroom_pct,
        headroomValue: s.headroom_value,
        unit: "SAR",
        overTone: "legal",
        exceptionRole: null,
        description: null,
      },
    ];
  });
}

/** The latest approved order behind a limit's total, as the ledger lists it. */
export type Latest = { value: string; ref: string };

/**
 * For each limit key, the most recent approved order that counts towards it:
 * by category for the Article 67 scopes, any cost order for the combined and
 * policy cost totals. Values are the ledger's strings, untouched.
 */
export function latestChanges(
  ledger: LedgerResponse,
  refFor: (crId: string) => string | null = () => null,
): Record<string, Latest> {
  const approved = ledger.orders
    .map((o, i) => ({ o, i }))
    .filter(({ o }) => o.status === "APPROVED")
    .sort((a, b) => a.o.created_at.localeCompare(b.o.created_at) || a.i - b.i)
    .map(({ o }) => o);
  const toLatest = (o: (typeof approved)[number]): Latest => ({
    value: o.value,
    ref: (o.change_request_id && refFor(o.change_request_id)) || o.change_request_id || o.id,
  });
  const out: Record<string, Latest> = {};
  for (const o of approved) {
    out[o.type] = toLatest(o);
    if (o.type !== "NON_FINANCIAL") {
      out.COMBINED = toLatest(o);
      out.cost_increase = toLatest(o);
    }
  }
  return out;
}

function LatestDelta({ latest, className }: { latest?: Latest; className?: string }) {
  const t = useT().limits;
  if (!latest) return null;
  return (
    <p className={cn("text-xs text-ink-muted", className)} data-testid="latest-delta">
      <span className="font-semibold text-ink tabular-nums">{formatImpact(latest.value)}</span>
      <span>{t.latestOrder("")}</span>
      <span className="ref">{latest.ref}</span>
    </p>
  );
}

/** True once the meter has painted at zero, so the first fill animates too. */
function useMounted(): boolean {
  const [mounted, setMounted] = useState(false);
  useEffect(() => {
    const id = window.requestAnimationFrame(() => setMounted(true));
    return () => window.cancelAnimationFrame(id);
  }, []);
  return mounted;
}

const GROW =
  "transition-[inline-size,inset-inline-start] duration-700 ease-out motion-reduce:transition-none";

function over(limit: Limit): boolean {
  return Boolean(limit.headroomPct?.trim().startsWith("-"));
}

function amount(limit: Limit, value: string | null): string {
  const t = getDict().limits;
  if (value === null) return t.noLimit;
  return limit.unit === "days" ? t.days(formatNumber(value)) : formatMoney(value);
}

const OVER_BG: Record<Tone, string> = {
  neutral: "bg-ink",
  seal: "bg-seal",
  amber: "bg-amber",
  legal: "bg-legal",
};
const OVER_TEXT: Record<Tone, string> = {
  neutral: "text-ink",
  seal: "text-seal",
  amber: "text-amber",
  legal: "text-legal",
};

/**
 * A ruled meter. The track runs to 1.5x the cap, so the cap mark always sits
 * two thirds along. Widths come from CSS `calc()` on the API's strings.
 */
export function Meter({ limit, className }: { limit: Limit; className?: string }) {
  const t = useT().limits;
  const mounted = useMounted();
  if (!limit.capPct) {
    return <span className={cn("text-xs text-ink-muted", className)}>{t.noRelativeLimit}</span>;
  }
  const isOver = over(limit);
  // Widths are CSS calc() on the API's strings; before the first frame they
  // are zero, so the fill grows in, and later updates glide (CSS transition).
  const style = {
    "--cap": limit.capPct,
    "--used": mounted ? limit.usedPct : "0",
    "--pending": mounted ? limit.pendingPct : "0",
  } as CSSProperties;
  const label = t.meterLabel(
    formatPct(limit.usedPct),
    formatPct(limit.pendingPct),
    formatPct(limit.capPct),
  );

  return (
    <span
      role="img"
      aria-label={label}
      style={style}
      className={cn("relative block h-5 [--scale:calc(var(--cap)*1.5)]", className)}
    >
      <span className="absolute inset-x-0 top-1/2 h-2 -translate-y-1/2 border border-rule-strong bg-sheet" />
      <span
        className={cn("absolute start-0 top-1/2 h-2 -translate-y-1/2", GROW, isOver ? OVER_BG[limit.overTone] : "bg-ink")}
        style={{ inlineSize: "calc(min(var(--used), var(--scale)) / var(--scale) * 100%)" }}
      />
      <span
        className={cn("hatch absolute top-1/2 h-2 -translate-y-1/2 border-y border-e border-rule-strong", GROW)}
        style={{
          insetInlineStart: "calc(min(var(--used), var(--scale)) / var(--scale) * 100%)",
          inlineSize:
            "calc(min(var(--pending), max(var(--scale) - var(--used), 0)) / var(--scale) * 100%)",
        }}
      />
      <span className="absolute inset-y-0 w-0.5 bg-ink" style={{ insetInlineStart: "calc(100% / 1.5)" }} />
    </span>
  );
}

export function MeterKey() {
  const t = useT().limits;
  return (
    <p className="mt-3 flex flex-wrap items-center gap-x-5 gap-y-1 text-xs text-ink-muted">
      <span className="inline-flex items-center gap-1.5">
        <span aria-hidden className="inline-block h-2 w-5 bg-ink" />
        {t.keyApproved}
      </span>
      <span className="inline-flex items-center gap-1.5">
        <span aria-hidden className="hatch inline-block h-2 w-5 border border-rule-strong" />
        {t.keyPending}
      </span>
      <span className="inline-flex items-center gap-1.5">
        <span aria-hidden className="inline-block h-3 w-0.5 bg-ink" />
        {t.keyCap}
      </span>
    </p>
  );
}

/** Compact rows for the workspace summary. */
export function LimitRows({ limits, latest = {} }: { limits: Limit[]; latest?: Record<string, Latest> }) {
  const t = useT().limits;
  const en = getLang() === "en";
  return (
    <ul className="divide-y divide-rule border-y border-rule">
      {limits.map((l) => (
        <li
          key={l.key}
          className="grid grid-cols-[1fr_auto] items-center gap-x-6 gap-y-2 py-3 md:grid-cols-[7.5rem_14rem_1fr_15rem]"
        >
          <span className="margin-ref order-3 col-span-2 md:order-none md:col-span-1">
            {(en ? (l.citeEn ?? l.citeAr) : l.citeAr) ?? SOURCE_LABEL[l.source] ?? l.source}
          </span>
          <span className={cn("text-sm font-medium", (l.key === "COMBINED") && "font-semibold")}>{l.name}</span>
          <Meter limit={l} className="order-4 col-span-2 md:order-none md:col-span-1" />
          <span className="text-end text-sm">
            <span className={cn("font-medium", over(l) && OVER_TEXT[l.overTone])}>{formatPct(l.usedPct)}</span>
            {l.capPct && <span className="text-ink-muted"> {t.of} {formatPct(l.capPct)}</span>}
            <span className="block text-xs text-ink-muted">
              {amount(l, l.usedValue)}
              {l.capValue && <> {t.of} {amount(l, l.capValue)}</>}
            </span>
            <LatestDelta latest={latest[l.key]} className="mt-0.5" />
          </span>
        </li>
      ))}
    </ul>
  );
}

/** Full rows for the limits page: cap, used, pending, headroom and source. */
export function LimitDetail({ limits, latest = {} }: { limits: Limit[]; latest?: Record<string, Latest> }) {
  const t = useT().limits;
  return (
    <ul className="divide-y divide-rule border-y border-rule-strong">
      {limits.map((l) => {
        const isOver = over(l);
        return (
          <li key={l.key} className="grid gap-x-6 gap-y-3 py-5 md:grid-cols-[7.5rem_1fr]">
            <div className="margin-ref">
              <Badge variant={l.source === "law" ? "neutral" : "muted"}>
                {SOURCE_LABEL[l.source] ?? l.source}
              </Badge>
              {l.citeAr && (
                <ArabicOriginal as="span" showLabel={false} className="mt-2 block text-ink">
                  {l.citeAr}
                </ArabicOriginal>
              )}
              {l.citeEn && <span className="ref mt-0.5 block">{l.citeEn}</span>}
            </div>
            <div className="min-w-0">
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <h3 className="text-base font-semibold">{l.name}</h3>
                {isOver && (
                  <Badge variant={l.overTone === "legal" ? "legal" : "amber"}>
                    {l.overTone === "legal" ? t.overLegal : t.overPolicy}
                  </Badge>
                )}
              </div>
              {l.description && <p className="mt-0.5 text-sm text-ink-muted">{l.description}</p>}
              <LatestDelta latest={latest[l.key]} className="mt-1 text-sm" />
              <Meter limit={l} className="mt-3 max-w-3xl" />
              <dl className="mt-3 grid max-w-3xl grid-cols-2 gap-x-6 gap-y-3 text-sm sm:grid-cols-4">
                <Figure label={t.figCap} pct={l.capPct} value={amount(l, l.capValue)} />
                <Figure label={t.figUsed} pct={l.usedPct} value={amount(l, l.usedValue)} tone={isOver ? OVER_TEXT[l.overTone] : undefined} />
                <Figure label={t.figPending} pct={l.pendingPct} value={amount(l, l.pendingValue)} />
                <Figure label={t.figHeadroom} pct={l.headroomPct} value={amount(l, l.headroomValue)} tone={isOver ? OVER_TEXT[l.overTone] : undefined} />
              </dl>
              {l.exceptionRole && (
                <p className="mt-3 text-xs text-ink-muted">
                  {t.exceptionBefore}{" "}
                  {l.exceptionRole in ROLE_LABEL
                    ? ROLE_LABEL[l.exceptionRole as keyof typeof ROLE_LABEL]
                    : l.exceptionRole}{" "}
                  {t.exceptionAfter}
                </p>
              )}
              {l.overTone === "legal" && l.source === "law" && l.capPct && (
                <p className="mt-3 text-xs text-ink-muted">
                  {t.bindingLegal}
                </p>
              )}
            </div>
          </li>
        );
      })}
    </ul>
  );
}

function Figure({ label, pct, value, tone }: { label: string; pct: string | null; value: string; tone?: string }) {
  const t = useT().limits;
  return (
    <div>
      <dt className="text-xs text-ink-muted">{label}</dt>
      <dd className={cn("font-medium", tone)}>{pct ? formatPct(pct) : t.noLimit}</dd>
      <dd className="text-xs text-ink-muted">{value}</dd>
    </div>
  );
}

/**
 * The legal limit with the least headroom, as a headline above the detail:
 * the ledger's own approved, cap, pending and headroom values, compared
 * exactly. Nothing is computed beyond picking the smallest headroom.
 */
export function ClosestLegalLimit({ ledger }: { ledger: LedgerResponse }) {
  const t = useT().limits;
  const en = getLang() === "en";
  const capped = lawLimits(ledger).filter((l) => l.capValue && l.headroomValue);
  if (capped.length === 0) return null;
  const closest = capped.reduce((a, b) =>
    (compareDecimal(b.headroomValue ?? "", a.headroomValue ?? "") ?? 0) < 0 ? b : a,
  );
  const tight = over(closest) || closest.headroomPct?.startsWith("0");
  return (
    <a
      href="#law"
      data-testid="closest-legal-limit"
      className={cn(
        "mt-5 grid max-w-4xl gap-x-6 gap-y-2 border-s-4 bg-paper px-4 py-3 md:grid-cols-[1fr_auto] md:items-center",
        tight ? "border-legal" : "border-ink",
      )}
    >
      <span className="min-w-0">
        <span className="block text-xs text-ink-muted">
          {t.closestTitle}
          <span className="ref ms-2 text-ink">{en ? closest.citeEn : closest.citeAr}</span>
        </span>
        <span className="mt-0.5 block font-doc text-xl font-semibold tabular-nums text-balance">
          {t.closestUsed(formatMoney(closest.usedValue), formatMoney(closest.capValue))}
        </span>
        <span className="mt-0.5 block text-sm text-ink-muted tabular-nums">
          {closest.name}
          {" · "}
          {t.closestPending(formatMoney(closest.pendingValue))}
        </span>
      </span>
      <span className={cn("font-doc text-2xl font-semibold tabular-nums", tight ? "text-legal" : "text-ink")}>
        {t.closestLeft(formatMoney(closest.headroomValue))}
      </span>
      <Meter limit={closest} className="md:col-span-2" />
    </a>
  );
}
