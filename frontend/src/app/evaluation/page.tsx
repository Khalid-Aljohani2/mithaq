"use client";

import type { ReactNode } from "react";

import { Empty, ErrorState, Loading, Section } from "@/components/file";
import { Badge } from "@/components/ui/badge";
import { api, type EvalSummaryResponse } from "@/lib/api";
import {
  divideDecimal,
  formatDateTime,
  formatDuration,
  formatNumber,
  formatPct,
  formatUsd,
} from "@/lib/format";
import { STAGES } from "@/lib/labels";
import { useT } from "@/lib/prefs";
import { docAt } from "@/lib/source";
import { useResource } from "@/lib/use-resource";
import { cn } from "@/lib/utils";

/** Which pipeline stage produces each scored field. Names live in the dictionary. */
const FIELD: Record<string, { stage: number }> = {
  in_scope: { stage: 3 },
  kind: { stage: 3 },
  matched_line_ids: { stage: 3 },
  changes_approved_product: { stage: 4 },
  recommendation: { stage: 7 },
};

const STAGE_NAME = Object.fromEntries(STAGES.map((s) => [s.stage, s] as const));

/** The published evaluation (FR-17), readable by someone who has ten seconds. */
export default function EvaluationPage() {
  const summary = useResource((s) => api.evalSummary(s), []);
  const t = useT().evaluation;

  return (
    <div className="mx-auto max-w-[90rem] px-4 pb-16 md:px-8">
      {summary.status === "loading" ? (
        <Loading label={t.loading} rows={6} />
      ) : summary.status === "error" ? (
        <div className="pt-6">
          <ErrorState error={summary.error} what={t.what} onRetry={summary.reload} />
        </div>
      ) : !summary.data.available ? (
        <div className="pt-6">
          <Empty title={t.emptyTitle}>
            {t.emptyBody}
          </Empty>
        </div>
      ) : (
        <Report s={summary.data} />
      )}
    </div>
  );
}

function Report({ s }: { s: EvalSummaryResponse }) {
  const t = useT().evaluation;
  const n = s.case_count ?? 0;
  const dev = s.dev_case_count ?? 0;
  const fields = [...(s.fields ?? [])].sort(
    (a, b) => (FIELD[a.field]?.stage ?? 99) - (FIELD[b.field]?.stage ?? 99),
  );
  const stages = [...(s.stage_latency ?? [])].sort(
    (a, b) => (STAGE_NAME[a.stage]?.no ?? 99) - (STAGE_NAME[b.stage]?.no ?? 99),
  );
  const perRequest = s.total_cost_usd && n ? divideDecimal(s.total_cost_usd, n, 4) : null;
  const auditUrl = docAt(s.commit, "docs/eval_label_audit.md");
  const comparisonUrl = docAt(s.commit, "docs/eval_comparison.md");
  const ms = (v: string | null | undefined) => (v ? formatDuration(Math.round(Number(v))) : t.notAvailable);
  const source = <SourceLine s={s} />;

  return (
    <>
      {/* The headline: one line, first. */}
      <section aria-labelledby="headline" className="rule-double pt-10 pb-8">
        <p className="text-xs text-ink-muted">{t.kicker}</p>
        <h1 id="headline" className="mt-2 max-w-6xl font-doc text-2xl leading-[1.6] font-semibold text-balance md:text-[2rem] md:leading-[1.5]">
          {t.headline(formatPct(s.overall_accuracy_pct), formatNumber(n))}
        </h1>
        <p className="mt-3 max-w-prose text-sm">
          {t.lede(
            formatNumber(s.injection_passed ?? 0),
            formatNumber(s.injection_total ?? 0),
            (s.errors ?? 0) === 0 ? t.noRunErrors : t.runErrors(formatNumber(s.errors ?? 0)),
          )}
        </p>
        <div className="mt-4">{source}</div>
      </section>

      <Section
        id="labels"
        title={t.labelsTitle}
        margin={<span>{t.labelsMargin}</span>}
      >
        <p className="mb-4 max-w-prose text-sm text-ink-muted">
          {t.labelsIntro}{" "}
          <a href={auditUrl} target="_blank" rel="noreferrer" className="underline underline-offset-4">
            {t.auditLink}
          </a>
          {s.audited_case_ids && s.audited_case_ids.length > 0 && (
            <>
              {" "}
              {t.auditedCases}{" "}
              {s.audited_case_ids.map((id, i) => (
                <span key={id}>
                  <span className="ref">{id}</span>
                  {i < (s.audited_case_ids?.length ?? 0) - 1 ? t.listSep : ""}
                </span>
              ))}
              ).
            </>
          )}
        </p>
        <div className="overflow-x-auto">
          <table className="w-full max-w-4xl border-collapse text-sm">
            <thead>
              <tr className="border-y border-rule-strong text-xs text-ink-muted">
                <th scope="col" className="py-2 pe-4 text-start font-medium">{t.colStage}</th>
                <th scope="col" className="py-2 pe-4 text-start font-medium">{t.colMeasure}</th>
                <th scope="col" className="py-2 pe-4 text-end font-medium">{t.colOriginal}</th>
                <th scope="col" className="py-2 text-end font-medium">{t.colAudited}</th>
              </tr>
            </thead>
            <tbody>
              {fields.map((f) => {
                const meta = FIELD[f.field];
                const changed = f.accuracy_pct !== f.audited_accuracy_pct;
                return (
                  <tr
                    key={f.field}
                    className={cn("border-b border-rule", f.field === "recommendation" && "font-semibold")}
                  >
                    <td className="py-2.5 pe-4 tabular-nums">
                      {meta ? `${meta.stage} ${STAGES[meta.stage - 1]?.name ?? ""}` : ""}
                    </td>
                    <td className="py-2.5 pe-4">{t.fields[f.field] ?? f.field}</td>
                    <td className="py-2.5 pe-4 text-end">{formatPct(f.accuracy_pct)}</td>
                    <td className={cn("py-2.5 text-end", changed && "text-seal")}>
                      {formatPct(f.audited_accuracy_pct)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        <div className="mt-3">{source}</div>
      </Section>

      <Section id="speed" title={t.speedTitle} margin={<span>{t.requests(formatNumber(n))}</span>}>
        <dl className="grid max-w-4xl grid-cols-2 gap-x-8 gap-y-4 sm:grid-cols-4">
          <Stat label={t.p50} value={ms(s.latency_p50_ms)} />
          <Stat label={t.p95} value={ms(s.latency_p95_ms)} />
          <Stat label={t.costPerRequest} value={formatUsd(perRequest)} />
          <Stat label={t.costTotal} value={formatUsd(s.total_cost_usd)} />
        </dl>
        <p className="mt-2 text-xs text-ink-muted">
          {t.tokens(formatNumber(s.input_tokens ?? 0), formatNumber(s.output_tokens ?? 0))}{" "}
          {t.costNote}
        </p>

        <h3 className="mt-6 text-sm font-semibold">{t.stageLatency}</h3>
        <div className="mt-2 overflow-x-auto">
          <table className="w-full max-w-3xl border-collapse text-sm">
            <thead>
              <tr className="border-y border-rule-strong text-xs text-ink-muted">
                <th scope="col" className="py-2 pe-4 text-start font-medium">{t.colStage}</th>
                <th scope="col" className="py-2 pe-4 text-start font-medium">{t.colActor}</th>
                <th scope="col" className="py-2 pe-4 text-end font-medium">{t.colMedian}</th>
                <th scope="col" className="py-2 text-end font-medium">{t.colP95}</th>
              </tr>
            </thead>
            <tbody>
              {stages.map((st) => {
                const meta = STAGE_NAME[st.stage];
                return (
                  <tr key={st.stage} className="border-b border-rule">
                    <td className="py-2 pe-4">
                      <span className="tabular-nums">{meta?.no ?? ""}</span> {meta?.name ?? st.stage}
                    </td>
                    <td className="py-2 pe-4 text-ink-muted">
                      {meta?.actor === "AI" ? t.actorAi : meta?.actor === "CODE" ? t.actorCode : ""}
                    </td>
                    <td className="py-2 pe-4 text-end">{ms(st.median_ms)}</td>
                    <td className="py-2 text-end">{ms(st.p95_ms)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        <div className="mt-3">{source}</div>
      </Section>

      <Section id="models" title={t.modelsTitle} margin={<Badge variant="muted" className="whitespace-normal">{t.modelsBadge}</Badge>}>
        <p className="max-w-prose text-sm">
          {t.modelsBody}{" "}
          <a href={comparisonUrl} target="_blank" rel="noreferrer" className="underline underline-offset-4">
            {t.modelsLink}
          </a>
        </p>
      </Section>

      <Section id="method" title={t.methodTitle} margin={<span>{t.methodMargin}</span>} className="border-b-0">
        <ul className="max-w-prose space-y-3 text-sm">
          <li>
            <span className="font-semibold">{t.byConstruction}</span>
            {t.byConstructionBody}
          </li>
          <li>
            <span className="font-semibold">{t.separation}</span>
            {t.separationBody(formatNumber(dev), formatNumber(n))}
          </li>
          <li>
            <span className="font-semibold">{t.promptVersions}</span>
            {Object.entries(s.prompt_versions ?? {}).map(([stage, v], i, all) => (
              <span key={stage}>
                {STAGE_NAME[stage]?.name ?? stage} <span className="ref">{v}</span>
                {i < all.length - 1 ? t.listSep : t.listEnd}
              </span>
            ))}
          </li>
          {s.notes && (
            <li className="text-ink-muted">
              <span lang="en" dir="ltr" className="inline-block">{s.notes}</span>
            </li>
          )}
        </ul>
        <div className="mt-4">{source}</div>
      </Section>
    </>
  );
}

function Stat({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div>
      <dt className="text-xs text-ink-muted">{label}</dt>
      <dd className="mt-0.5 text-xl font-semibold">{value}</dd>
    </div>
  );
}

/** Every number names its run: commit, date, model, split. */
function SourceLine({ s }: { s: EvalSummaryResponse }) {
  const t = useT().evaluation;
  return (
    <p className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-ink-muted">
      <span>
        {t.source} <span className="ref text-ink">{s.commit ?? t.unknown}</span>
      </span>
      {s.generated_at && <span>{t.generatedAt(formatDateTime(s.generated_at))}</span>}
      {s.model && (
        <span>
          {t.model} <span className="ref text-ink">{s.model}</span>
        </span>
      )}
      {s.split && <span>{t.split(s.split === "test" ? t.testSplit : s.split)}</span>}
    </p>
  );
}
