"use client";

import type { ReactNode } from "react";

import { Field, toneText } from "@/components/file";
import { LineCard } from "@/components/case/request-zone";
import { Badge } from "@/components/ui/badge";
import type { BreakdownLine, ChangeRequest, Contract } from "@/lib/api";
import { formatConfidence, formatDays, formatImpact, formatMoney, formatPct } from "@/lib/format";
import { RECOMMENDATION, REASON_CODE, ROLE_LABEL, type Tone } from "@/lib/labels";
import type { Compliance, Impact, Narrative } from "@/lib/payload";
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
          توصية الوكيل
        </h2>
        <span className="flex items-center gap-2 text-xs text-ink-muted">
          {recorded && <Badge variant="muted">رد مسجل</Badge>}
          الثقة {formatConfidence(request.confidence)}
        </span>
      </div>
      <p className={cn("mt-1 font-doc text-xl font-semibold", toneText(rec.tone))}>{rec.verb}</p>
      {narrative.summary && <p className="mt-2 text-sm">{narrative.summary}</p>}

      {reasons.length > 0 && (
        <>
          <h3 className="mt-4 text-xs font-medium text-ink-muted">الأسباب</h3>
          <ul className="mt-1 divide-y divide-rule border-y border-rule text-sm">
            {reasons.map((r) => (
              <li key={r} className="py-1.5">{r}</li>
            ))}
          </ul>
        </>
      )}
      {narrative.conflicts.length > 0 && (
        <>
          <h3 className="mt-4 text-xs font-medium text-legal">تعارضات بين المراحل</h3>
          <ul className="mt-1 divide-y divide-rule border-y border-rule text-sm">
            {narrative.conflicts.map((c) => (
              <li key={c} className="py-1.5">{c}</li>
            ))}
          </ul>
        </>
      )}
      {narrative.nextActions.length > 0 && (
        <>
          <h3 className="mt-4 text-xs font-medium text-ink-muted">الإجراءات التالية</h3>
          <ol className="mt-1 list-decimal divide-y divide-rule border-y border-rule ps-5 text-sm">
            {narrative.nextActions.map((a) => (
              <li key={a} className="py-1.5">{a}</li>
            ))}
          </ol>
        </>
      )}
      <p className="mt-3 text-xs text-ink-muted">
        هذه توصية، والقرار لأصحاب الصلاحية في سلسلة الاعتماد.
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
  const flags: Flag[] = [];
  const refs = compliance.legal?.articleRefs ?? [];
  const refList = refs.length ? (
    <span>
      {" "}
      {refs.map((r, i) => (
        <span key={r}>
          <span className="ref">{r}</span>
          {i < refs.length - 1 ? "، " : ""}
        </span>
      ))}
    </span>
  ) : null;

  if (request.legally_blocked) {
    flags.push({
      tone: "legal",
      title: "محجوب نظامًا",
      body: <>يتجاوز الطلب حدًا نظاميًا، ولا يرفعه أي اعتماد داخلي.{refList}</>,
      source: "النظام",
    });
  }
  if (request.policy_exception_required) {
    const p = compliance.policy;
    const role = p?.exceptionRole && p.exceptionRole in ROLE_LABEL
      ? ROLE_LABEL[p.exceptionRole as keyof typeof ROLE_LABEL]
      : null;
    flags.push({
      tone: "amber",
      title: "يحتاج استثناءً من السياسة",
      body: (
        <>
          {p?.costExceeded && (
            <>التكلفة التراكمية بعد الطلب {formatPct(p.costAfterPct)} من قيمة العقد، والحد {formatPct(p.costCapPct)}. </>
          )}
          {p?.timeExceeded && (
            <>التمديد التراكمي {formatPct(p.timeAfterPct)} من المدة، والحد {formatPct(p.timeCapPct)}. </>
          )}
          {role && <>أُضيف {role} إلى سلسلة الاعتماد لاعتماد الاستثناء.</>}
          {request.legally_blocked && <> استثناء السياسة لا يرفع الحد النظامي.</>}
        </>
      ),
      source: "سياسة الجهة",
    });
  }
  if (request.needs_legal_review && !request.legally_blocked) {
    flags.push({
      tone: "amber",
      title: "يحتاج مراجعة قانونية",
      body: <>الطلب يمس حدًا نظاميًا.{refList}</>,
      source: "النظام",
    });
  }
  if (compliance.legal?.consent) {
    flags.push({
      tone: "amber",
      title: "موافقة المقاول مطلوبة",
      body: <>أُضيفت موافقة المقاول إلى سلسلة الاعتماد.{refList}</>,
      source: "النظام",
    });
  }
  if (request.unit_rate_flagged) {
    const flagged = impact.rateChecks.filter((c) => c.flagged);
    flags.push({
      tone: "amber",
      title: "سعر الوحدة معلَّم",
      body: flagged.length ? (
        <>
          {flagged.map((c) => (
            <span key={c.lineId ?? ""} className="block">
              <span className="ref">{c.lineId}</span>: المقترح {formatMoney(c.proposedRate)} مقابل{" "}
              {formatMoney(c.contractRate)} في العقد، بانحراف {formatPct(c.deviationPct)} والحد{" "}
              {formatPct(c.capPct)}.
            </span>
          ))}
        </>
      ) : (
        "السعر المقترح ينحرف عن سعر العقد بأكثر من الحد."
      ),
      source: "سياسة الجهة",
    });
  }
  if (request.rate_human_entered) {
    flags.push({
      tone: "neutral",
      title: "سعر مُدخل يدويًا",
      body: "لا يقابل السعر بندًا في العقد، فاعتُمد السعر الذي أدخله مقدم الطلب، ويحتاج تحققًا بشريًا.",
      source: "قاعدة",
    });
  }
  if (request.changes_approved_product) {
    flags.push({
      tone: "amber",
      title: "يغيّر منتجًا معتمدًا",
      body: "أُضيف اعتماد فني إلى سلسلة الاعتماد.",
      source: "قاعدة",
    });
  }

  if (flags.length === 0) {
    return (
      <section aria-labelledby="flags">
        <h2 id="flags" className="text-xs font-medium text-ink-muted">التنبيهات</h2>
        <p className="mt-1 text-sm">لا تنبيهات: الطلب ضمن الحدود ولا يغيّر منتجًا معتمدًا.</p>
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
      <h2 id="flags" className="text-xs font-medium text-ink-muted">التنبيهات</h2>
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
  const p = compliance.policy;
  return (
    <section aria-labelledby="impact">
      <h2 id="impact" className="text-xs font-medium text-ink-muted">أثر التكلفة والمدة</h2>
      <dl className="mt-2 grid grid-cols-2 gap-x-4 gap-y-3">
        <Field label="أثر التكلفة">
          <span className="text-lg">{formatImpact(request.cost_impact)}</span>
        </Field>
        <Field label="أثر المدة">
          <span className="text-lg">{formatDays(request.time_impact_days)}</span>
        </Field>
        {impact.removed && impact.removed !== "0" && (
          <>
            <Field label="قيمة المضاف">{formatMoney(impact.added)}</Field>
            <Field label="قيمة المحذوف">{formatMoney(impact.removed)}</Field>
          </>
        )}
        {p && (
          <>
            <Field label="التكلفة التراكمية بعد الطلب">
              <span className={cn(p.costExceeded && "text-amber")}>{formatPct(p.costAfterPct)}</span>
              <span className="text-xs text-ink-muted"> من حد {formatPct(p.costCapPct)}</span>
            </Field>
            <Field label="التمديد التراكمي بعد الطلب">
              <span className={cn(p.timeExceeded && "text-amber")}>{formatPct(p.timeAfterPct)}</span>
              <span className="text-xs text-ink-muted"> من حد {formatPct(p.timeCapPct)}</span>
            </Field>
          </>
        )}
      </dl>
      <p className="mt-2 text-xs text-ink-muted">حسبتها قاعدة برمجية من الكميات وأسعار العقد، لا الوكيل.</p>
    </section>
  );
}

export function ClosedInScope({ lines }: { lines: BreakdownLine[] }) {
  return (
    <section aria-labelledby="closed" className="border-t-2 border-ink pt-4">
      <h2 id="closed" className="font-doc text-xl font-semibold">أُغلق كطلب داخل النطاق</h2>
      <p className="mt-2 text-sm">
        الطلب مغطى ببنود العقد الحالية، فلا يُعد تغييرًا ولا يُحتسب من أي حد.
        هذه البنود هي الدليل:
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
