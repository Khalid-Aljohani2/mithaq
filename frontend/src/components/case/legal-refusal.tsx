"use client";

import { motion, useReducedMotion } from "motion/react";
import { useEffect, useRef } from "react";

import type { ChangeRequest, LedgerResponse } from "@/lib/api";
import {
  absDecimal,
  addDecimal,
  compareDecimal,
  formatMoney,
  subtractDecimal,
} from "@/lib/format";
import { useT } from "@/lib/prefs";

type Usage = LedgerResponse["usage"][string];

/**
 * The usage line the refusal rests on: a capped scope cited by the refusal
 * whose approved total plus this request goes above its cap. Every number is
 * the ledger's own; the only arithmetic is exact decimal addition for display.
 */
function citedUsage(
  ledger: LedgerResponse,
  articles: string[],
  cost: string,
): { usage: Usage; total: string; over: string } | null {
  const capped = Object.values(ledger.usage).filter((u) => u.cap_value && u.source === "law");
  const cited = capped.filter((u) =>
    articles.some((a) => a && (a.includes(u.article_ref_en) || u.article_ref_en.includes(a))),
  );
  for (const usage of [...cited, ...capped]) {
    const total = addDecimal(usage.before_value, cost);
    const cap = usage.cap_value;
    if (!total || !cap) continue;
    if ((compareDecimal(total, cap) ?? 0) > 0) {
      const over = subtractDecimal(total, cap);
      if (over) return { usage, total, over };
    }
  }
  return null;
}

/**
 * Final approval refused under a legal cap (Act 5). The arithmetic, the
 * article in both languages, and what happens next. There is no button here:
 * no internal approval can lift a legal limit (NFR-16).
 */
export function LegalRefusal({
  request,
  articles,
  ledger,
}: {
  request: ChangeRequest;
  articles: string[];
  ledger: LedgerResponse | null;
}) {
  const t = useT();
  const reduce = useReducedMotion();
  const ref = useRef<HTMLElement>(null);
  const cost = request.cost_impact ? absDecimal(request.cost_impact) : null;
  const line = ledger && cost ? citedUsage(ledger, articles, cost) : null;

  useEffect(() => {
    ref.current?.scrollIntoView({ block: "nearest", behavior: reduce ? "auto" : "smooth" });
  }, [reduce]);

  return (
    <motion.section
      ref={ref}
      role="alert"
      data-testid="legal-refusal"
      initial={reduce ? false : { opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
      className="mt-4 border-2 border-legal bg-paper"
    >
      <header className="bg-legal px-4 py-2.5 text-paper">
        <h3 className="text-base font-semibold text-balance">{t.case.refusedTitle}</h3>
      </header>
      <div className="space-y-4 px-4 py-4">
        <p className="text-sm text-pretty">{t.case.refusedLead}</p>

        {line && cost && (
          <dl className="font-doc tabular-nums">
            <Sum label={t.case.refusedApproved} value={formatMoney(line.usage.before_value)} />
            <Sum label={t.case.refusedThis} value={`+ ${formatMoney(cost)}`} />
            <Sum label={t.case.refusedNew} value={formatMoney(line.total)} strong />
            <Sum label={t.case.refusedCap} value={formatMoney(line.usage.cap_value)} muted />
            <p className="mt-2 border-s-4 border-legal bg-legal-wash px-3 py-1.5 font-sans text-sm font-semibold text-legal">
              {t.case.refusedOver(formatMoney(line.over))}
            </p>
          </dl>
        )}

        <div className="border-t border-rule pt-3">
          <p className="text-xs text-ink-muted">{t.case.refusedCited}</p>
          {line?.usage.article_ref_ar && (
            <p dir="rtl" lang="ar" className="mt-1 text-start font-doc text-sm font-semibold">
              {line.usage.article_ref_ar}
            </p>
          )}
          <p dir="ltr" lang="en" className="ref mt-0.5 text-start text-sm">
            {(articles.length ? articles : line ? [line.usage.article_ref_en] : []).join(", ")}
          </p>
        </div>

        <div className="border-t border-rule pt-3">
          <p className="text-xs font-medium">{t.case.refusedNextTitle}</p>
          <ol className="mt-1.5 space-y-1 text-sm">
            {t.case.refusedNext.map((item, i) => (
              <li key={item} className="grid grid-cols-[1.25rem_1fr] gap-x-1">
                <span className="tabular-nums text-ink-muted">{i + 1}</span>
                <span className="text-pretty">{item}</span>
              </li>
            ))}
          </ol>
        </div>
      </div>
    </motion.section>
  );
}

function Sum({
  label,
  value,
  strong,
  muted,
}: {
  label: string;
  value: string;
  strong?: boolean;
  muted?: boolean;
}) {
  return (
    <div
      className={
        "flex items-baseline justify-between gap-4 py-1" +
        (strong ? " border-t-2 border-ink font-semibold text-legal" : "") +
        (muted ? " text-ink-muted" : "")
      }
    >
      <dt className="font-sans text-sm">{label}</dt>
      <dd className={strong ? "text-lg" : "text-base"}>{value}</dd>
    </div>
  );
}
