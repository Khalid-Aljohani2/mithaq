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
import { docAt } from "@/lib/source";
import { useResource } from "@/lib/use-resource";
import { cn } from "@/lib/utils";

/** What each scored field is, and which pipeline stage produces it. */
const FIELD: Record<string, { name: string; stage: number }> = {
  in_scope: { name: "قرار النطاق: هل الطلب مغطى بالعقد؟", stage: 3 },
  kind: { name: "نوع التغيير", stage: 3 },
  matched_line_ids: { name: "البنود المطابقة في العقد", stage: 3 },
  changes_approved_product: { name: "هل يغيّر منتجًا معتمدًا؟", stage: 4 },
  recommendation: { name: "التوصية النهائية", stage: 7 },
};

const STAGE_NAME = Object.fromEntries(STAGES.map((s) => [s.stage, s] as const));

/** The published evaluation (FR-17), readable by someone who has ten seconds. */
export default function EvaluationPage() {
  const summary = useResource((s) => api.evalSummary(s), []);

  return (
    <div className="mx-auto max-w-[90rem] px-4 pb-16 md:px-8">
      {summary.status === "loading" ? (
        <Loading label="جارٍ تحميل نتائج التقييم" rows={6} />
      ) : summary.status === "error" ? (
        <div className="pt-6">
          <ErrorState error={summary.error} what="نتائج التقييم" onRetry={summary.reload} />
        </div>
      ) : !summary.data.available ? (
        <div className="pt-6">
          <Empty title="لم يُنشر تقييم بعد">
            يظهر هنا آخر تقييم منشور حين يُشغَّل على مجموعة الاختبار وتُنشر نتيجته.
          </Empty>
        </div>
      ) : (
        <Report s={summary.data} />
      )}
    </div>
  );
}

function Report({ s }: { s: EvalSummaryResponse }) {
  const n = s.case_count ?? 0;
  const fields = [...(s.fields ?? [])].sort(
    (a, b) => (FIELD[a.field]?.stage ?? 99) - (FIELD[b.field]?.stage ?? 99),
  );
  const stages = [...(s.stage_latency ?? [])].sort(
    (a, b) => (STAGE_NAME[a.stage]?.no ?? 99) - (STAGE_NAME[b.stage]?.no ?? 99),
  );
  const perRequest = s.total_cost_usd && n ? divideDecimal(s.total_cost_usd, n, 4) : null;
  const auditUrl = docAt(s.commit, "docs/eval_label_audit.md");
  const comparisonUrl = docAt(s.commit, "docs/eval_comparison.md");
  const ms = (v: string | null | undefined) => (v ? formatDuration(Math.round(Number(v))) : "غير متاح");
  const source = <SourceLine s={s} />;

  return (
    <>
      {/* The headline: one line, first. */}
      <section aria-labelledby="headline" className="rule-double pt-10 pb-8">
        <p className="text-xs text-ink-muted">نتيجة التقييم</p>
        <h1 id="headline" className="mt-2 max-w-6xl font-doc text-2xl leading-[1.6] font-semibold text-balance md:text-[2rem] md:leading-[1.5]">
          أصابت توصية الوكيل في{" "}
          {formatPct(s.overall_accuracy_pct)} من{" "}
          {formatNumber(n)} طلب تغيير لم تُستخدم في ضبطه.
        </h1>
        <p className="mt-3 max-w-prose text-sm">
          طلبات اختبار عربية محجوزة، لكل منها إجابة صحيحة معروفة سلفًا. صمد الوكيل
          أمام {formatNumber(s.injection_passed ?? 0)} من {formatNumber(s.injection_total ?? 0)}{" "}
          محاولات لتمرير تعليمات مدسوسة في نص الطلب، وانتهى التشغيل{" "}
          {(s.errors ?? 0) === 0 ? "دون أي خطأ تشغيل" : `${formatNumber(s.errors ?? 0)} أخطاء تشغيل`}.
        </p>
        <div className="mt-4">{source}</div>
      </section>

      <Section
        id="labels"
        title="الدقة قبل تدقيق الإجابات الصحيحة وبعده"
        margin={<span>تشغيل واحد، مُقيَّم مرتين</span>}
      >
        <p className="mb-4 max-w-prose text-sm text-ink-muted">
          راجعنا إجابات صحيحة بدت خاطئة قبل إعادة التشغيل، وأبقينا الأصلية. كل رقم
          يظهر مرتين: مقابل الإجابات الأصلية، ومقابل المدققة. الفرق بين العمودين هو أثر
          التدقيق وحده.{" "}
          <a href={auditUrl} target="_blank" rel="noreferrer" className="underline underline-offset-4">
            أسباب التدقيق لكل حالة
          </a>
          {s.audited_case_ids && s.audited_case_ids.length > 0 && (
            <>
              {" "}(الحالات المدققة:{" "}
              {s.audited_case_ids.map((id, i) => (
                <span key={id}>
                  <span className="ref">{id}</span>
                  {i < (s.audited_case_ids?.length ?? 0) - 1 ? "، " : ""}
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
                <th scope="col" className="py-2 pe-4 text-start font-medium">المرحلة</th>
                <th scope="col" className="py-2 pe-4 text-start font-medium">ما يُقاس</th>
                <th scope="col" className="py-2 pe-4 text-end font-medium">الإجابات الأصلية</th>
                <th scope="col" className="py-2 text-end font-medium">بعد التدقيق</th>
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
                    <td className="py-2.5 pe-4">{meta?.name ?? f.field}</td>
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

      <Section id="speed" title="الزمن والتكلفة" margin={<span>{formatNumber(n)} طلبًا</span>}>
        <dl className="grid max-w-4xl grid-cols-2 gap-x-8 gap-y-4 sm:grid-cols-4">
          <Stat label="الزمن الوسيط لتحليل طلب" value={ms(s.latency_p50_ms)} />
          <Stat label="زمن 95% من الطلبات أقل من" value={ms(s.latency_p95_ms)} />
          <Stat label="تكلفة الطلب الواحد" value={formatUsd(perRequest)} />
          <Stat label="تكلفة التشغيل كله" value={formatUsd(s.total_cost_usd)} />
        </dl>
        <p className="mt-2 text-xs text-ink-muted">
          الرموز: {formatNumber(s.input_tokens ?? 0)} مدخلة، و{formatNumber(s.output_tokens ?? 0)} مخرجة.
          تكلفة الطلب هي تكلفة التشغيل مقسومة على عدد الطلبات.
        </p>

        <h3 className="mt-6 text-sm font-semibold">زمن كل مرحلة</h3>
        <div className="mt-2 overflow-x-auto">
          <table className="w-full max-w-3xl border-collapse text-sm">
            <thead>
              <tr className="border-y border-rule-strong text-xs text-ink-muted">
                <th scope="col" className="py-2 pe-4 text-start font-medium">المرحلة</th>
                <th scope="col" className="py-2 pe-4 text-start font-medium">المنفذ</th>
                <th scope="col" className="py-2 pe-4 text-end font-medium">الوسيط</th>
                <th scope="col" className="py-2 text-end font-medium">95%</th>
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
                      {meta?.actor === "AI" ? "ذكاء اصطناعي" : meta?.actor === "CODE" ? "قاعدة برمجية" : ""}
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

      <Section id="models" title="مقارنة النماذج الأربعة" margin={<Badge variant="muted">لا يقدّمها الخادم بعد</Badge>}>
        <p className="max-w-prose text-sm">
          قورنت أربعة نماذج على مجموعة الاختبار نفسها قبل اختيار النموذج المعتمد. جدول
          المقارنة منشور في مستند المقارنة ولا تقدّمه الواجهة البرمجية بعد، لذا لا ننسخ
          أرقامه هنا.{" "}
          <a href={comparisonUrl} target="_blank" rel="noreferrer" className="underline underline-offset-4">
            مستند مقارنة النماذج
          </a>
        </p>
      </Section>

      <Section id="method" title="كيف بُنيت مجموعة التقييم" margin={<span>الطريقة</span>} className="border-b-0">
        <ul className="max-w-prose space-y-3 text-sm">
          <li>
            <span className="font-semibold">الإجابة الصحيحة بالبناء لا بالحكم. </span>
            كُتب كل طلب على بند معروف من العقد ونتيجة مقصودة سلفًا، فإجابته هي ما بُني
            ليكونه، لا ما قاله نموذج عنه.
          </li>
          <li>
            <span className="font-semibold">فصل الضبط عن الاختبار. </span>
            ضُبطت التعليمات على مجموعة التطوير وحدها، ولم تُفتح مجموعة الاختبار (
            {formatNumber(n)} طلبًا) إلا بعد آخر تعديل.
          </li>
          <li>
            <span className="font-semibold">نسخة التعليمات المقيسة. </span>
            {Object.entries(s.prompt_versions ?? {}).map(([stage, v], i, all) => (
              <span key={stage}>
                {STAGE_NAME[stage]?.name ?? stage} <span className="ref">{v}</span>
                {i < all.length - 1 ? "، " : "."}
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
  return (
    <p className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-ink-muted">
      <span>
        المصدر: الإيداع <span className="ref text-ink">{s.commit ?? "غير معروف"}</span>
      </span>
      {s.generated_at && <span>بتاريخ {formatDateTime(s.generated_at)}</span>}
      {s.model && (
        <span>
          النموذج <span className="ref text-ink">{s.model}</span>
        </span>
      )}
      {s.split && <span>مجموعة {s.split === "test" ? "الاختبار" : s.split}</span>}
    </p>
  );
}
