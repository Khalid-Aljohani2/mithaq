"use client";

import type { ReactNode } from "react";

import { Field, toneText } from "@/components/file";
import { LineCard } from "@/components/case/request-zone";
import { ArabicOriginal } from "@/components/original";
import { Badge } from "@/components/ui/badge";
import type { BreakdownLine, ChangeRequest, Contract } from "@/lib/api";
import { formatConfidence, formatDays, formatImpact, formatMoney, formatPct } from "@/lib/format";
import { RECOMMENDATION, REASON_CODE, ROLE_LABEL, type Tone } from "@/lib/labels";
import type { Compliance, Impact, Narrative } from "@/lib/payload";
import { useT } from "@/lib/prefs";
import { cn } from "@/lib/utils";

export function RecommendationBlock({
  request,
  narrative,
  recorded,
}: {
  request: ChangeRequest;
  narrative: Narrative;
  recorded: boolean;
}) {
  const t = useT();
  if (!request.recommendation) return null;
  const rec = RECOMMENDATION[request.recommendation];
  // The agent's own reasons when it gave them; the code labels otherwise.
  // Showing both repeats the same points in two wordings.
  const reasons = narrative.reasons.length
    ? narrative.reasons
    : narrative.reasonCodes.map((c) => REASON_CODE[c] ?? c);

  return (
    <section aria-labelledby="recommendation" className="border-t-2 border-ink pt-4">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 id="recommendation" className="text-xs font-medium text-ink-muted">
          {t.case.agentRecommendation}
        </h2>
        <span className="flex items-center gap-2 text-xs text-ink-muted">
          {recorded && <Badge variant="muted">{t.case.recordedReply}</Badge>}
          {t.case.confidence} {formatConfidence(request.confidence)}
        </span>
      </div>
      <p className={cn("mt-1 font-doc text-xl font-semibold", toneText(rec.tone))}>{rec.verb}</p>
      {narrative.summary && (
        <ArabicOriginal as="p" className="mt-2 text-sm">
          {narrative.summary}
        </ArabicOriginal>
      )}

      {reasons.length > 0 && (
        <>
          <h3 className="mt-4 text-xs font-medium text-ink-muted">{t.case.reasons}</h3>
          {narrative.reasons.length ? (
            <ArabicOriginal showLabel={false}>
              <ul className="mt-1 divide-y divide-rule border-y border-rule text-sm">
                {reasons.map((r) => (
                  <li key={r} className="py-1.5">{r}</li>
                ))}
              </ul>
            </ArabicOriginal>
          ) : (
            <ul className="mt-1 divide-y divide-rule border-y border-rule text-sm">
              {reasons.map((r) => (
                <li key={r} className="py-1.5">{r}</li>
              ))}
            </ul>
          )}
        </>
      )}
      {narrative.conflicts.length > 0 && (
        <>
          <h3 className="mt-4 text-xs font-medium text-legal">{t.case.conflicts}</h3>
          <ArabicOriginal showLabel={false}>
            <ul className="mt-1 divide-y divide-rule border-y border-rule text-sm">
              {narrative.conflicts.map((c) => (
                <li key={c} className="py-1.5">{c}</li>
              ))}
            </ul>
          </ArabicOriginal>
        </>
      )}
      {narrative.nextActions.length > 0 && (
        <>
          <h3 className="mt-4 text-xs font-medium text-ink-muted">{t.case.nextActions}</h3>
          <ArabicOriginal showLabel={false}>
            <ol className="mt-1 list-decimal divide-y divide-rule border-y border-rule ps-5 text-sm">
              {narrative.nextActions.map((a) => (
                <li key={a} className="py-1.5">{a}</li>
              ))}
            </ol>
          </ArabicOriginal>
        </>
      )}
      <p className="mt-3 text-xs text-ink-muted">
        {t.case.recommendationOnly}
      </p>
    </section>
  );
}

type Flag = { tone: Tone; title: string; body: ReactNode; source: string };

export function Flags({
  request,
  compliance,
  impact,
}: {
  request: ChangeRequest;
  compliance: Compliance;
  impact: Impact;
}) {
  const t = useT();
  const flags: Flag[] = [];
  const refs = compliance.legal?.articleRefs ?? [];
  const refList = refs.length ? (
    <span>
      {" "}
      {refs.map((r, i) => (
        <span key={r}>
          <span className="ref">{r}</span>
          {i < refs.length - 1 ? t.case.listSep : ""}
        </span>
      ))}
    </span>
  ) : null;

  if (request.legally_blocked) {
    flags.push({
      tone: "legal",
      title: t.case.blockedTitle,
      body: <>{t.case.blockedBody}{refList}</>,
      source: t.case.sourceLaw,
    });
  }
  if (request.policy_exception_required) {
    const p = compliance.policy;
    const role = p?.exceptionRole && p.exceptionRole in ROLE_LABEL
      ? ROLE_LABEL[p.exceptionRole as keyof typeof ROLE_LABEL]
      : null;
    flags.push({
      tone: "amber",
      title: t.case.policyTitle,
      body: (
        <>
          {p?.costExceeded && (
            <>{t.case.policyCost(formatPct(p.costAfterPct), formatPct(p.costCapPct))}</>
          )}
          {p?.timeExceeded && (
            <>{t.case.policyTime(formatPct(p.timeAfterPct), formatPct(p.timeCapPct))}</>
          )}
          {role && <>{t.case.policyRole(role)}</>}
          {request.legally_blocked && <>{t.case.policyNotLegal}</>}
        </>
      ),
      source: t.case.sourcePolicy,
    });
  }
  if (request.needs_legal_review && !request.legally_blocked) {
    flags.push({
      tone: "amber",
      title: t.case.legalReviewTitle,
      body: <>{t.case.legalReviewBody}{refList}</>,
      source: t.case.sourceLaw,
    });
  }
  if (compliance.legal?.consent) {
    flags.push({
      tone: "amber",
      title: t.case.consentTitle,
      body: <>{t.case.consentBody}{refList}</>,
      source: t.case.sourceLaw,
    });
  }
  if (request.unit_rate_flagged) {
    const flagged = impact.rateChecks.filter((c) => c.flagged);
    flags.push({
      tone: "amber",
      title: t.case.rateTitle,
      body: flagged.length ? (
        <>
          {flagged.map((c) => (
            <span key={c.lineId ?? ""} className="block">
              <span className="ref">{c.lineId}</span>
              {t.case.rateLine(
                formatMoney(c.proposedRate),
                formatMoney(c.contractRate),
                formatPct(c.deviationPct),
                formatPct(c.capPct),
              )}
            </span>
          ))}
        </>
      ) : (
        t.case.rateBody
      ),
      source: t.case.sourcePolicy,
    });
  }
  if (request.rate_human_entered) {
    flags.push({
      tone: "neutral",
      title: t.case.manualRateTitle,
      body: t.case.manualRateBody,
      source: t.case.sourceRule,
    });
  }
  if (request.changes_approved_product) {
    flags.push({
      tone: "amber",
      title: t.case.productTitle,
      body: t.case.productBody,
      source: t.case.sourceRule,
    });
  }

  if (flags.length === 0) {
    return (
      <section aria-labelledby="flags">
        <h2 id="flags" className="text-xs font-medium text-ink-muted">{t.case.flags}</h2>
        <p className="mt-1 text-sm">{t.case.noFlags}</p>
      </section>
    );
  }

  const bar: Record<Tone, string> = {
    neutral: "border-rule-strong",
    seal: "border-seal",
    amber: "border-amber",
    legal: "border-legal bg-legal-wash",
  };

  return (
    <section aria-labelledby="flags">
      <h2 id="flags" className="text-xs font-medium text-ink-muted">{t.case.flags}</h2>
      <ul className="mt-2 space-y-2">
        {flags.map((f) => (
          <li key={f.title} className={cn("border-s-4 py-2 ps-3 pe-2", bar[f.tone])}>
            <p className="flex items-baseline justify-between gap-2">
              <span className={cn("text-sm font-semibold", toneText(f.tone))}>{f.title}</span>
              <span className="text-2xs text-ink-muted">{f.source}</span>
            </p>
            <p className="mt-0.5 text-sm">{f.body}</p>
          </li>
        ))}
      </ul>
    </section>
  );
}

export function ImpactBlock({
  request,
  impact,
  compliance,
}: {
  request: ChangeRequest;
  impact: Impact;
  compliance: Compliance;
}) {
  const t = useT();
  const p = compliance.policy;
  return (
    <section aria-labelledby="impact">
      <h2 id="impact" className="text-xs font-medium text-ink-muted">{t.case.impactHeading}</h2>
      <dl className="mt-2 grid grid-cols-2 gap-x-4 gap-y-3">
        <Field label={t.case.costImpact}>
          <span className="text-lg">{formatImpact(request.cost_impact)}</span>
        </Field>
        <Field label={t.case.timeImpact}>
          <span className="text-lg">{formatDays(request.time_impact_days)}</span>
        </Field>
        {impact.removed && impact.removed !== "0" && (
          <>
            <Field label={t.case.addedValue}>{formatMoney(impact.added)}</Field>
            <Field label={t.case.removedValue}>{formatMoney(impact.removed)}</Field>
          </>
        )}
        {p && (
          <>
            <Field label={t.case.cumulativeCost}>
              <span className={cn(p.costExceeded && "text-amber")}>{formatPct(p.costAfterPct)}</span>
              <span className="text-xs text-ink-muted">{t.case.ofCap(formatPct(p.costCapPct))}</span>
            </Field>
            <Field label={t.case.cumulativeTime}>
              <span className={cn(p.timeExceeded && "text-amber")}>{formatPct(p.timeAfterPct)}</span>
              <span className="text-xs text-ink-muted">{t.case.ofCap(formatPct(p.timeCapPct))}</span>
            </Field>
          </>
        )}
      </dl>
      <p className="mt-2 text-xs text-ink-muted">{t.case.computedByCode}</p>
    </section>
  );
}

export function ClosedInScope({ lines }: { lines: BreakdownLine[] }) {
  const t = useT();
  return (
    <section aria-labelledby="closed" className="border-t-2 border-ink pt-4">
      <h2 id="closed" className="font-doc text-xl font-semibold">{t.case.closedTitle}</h2>
      <p className="mt-2 text-sm">
        {t.case.closedBody}
      </p>
      <ul className="mt-3 space-y-3">
        {lines.map((l) => (
          <LineCard key={l.id} line={l} />
        ))}
      </ul>
    </section>
  );
}

export function contractLines(contract: Contract, request: ChangeRequest): BreakdownLine[] {
  return (request.matched_line_ids ?? [])
    .map((id) => contract.breakdown.find((l) => l.id === id))
    .filter((l): l is BreakdownLine => Boolean(l));
}
