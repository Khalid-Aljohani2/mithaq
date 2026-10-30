"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import type { ReactNode } from "react";

import { Empty, ErrorState, Loading } from "@/components/file";
import { Seal } from "@/components/glyphs";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { ApiError, api, type BreakdownLine, type Contract, type VariationOrder } from "@/lib/api";
import { useContracts, useCurrentContract } from "@/lib/contracts";
import {
  formatDate,
  formatDateTime,
  formatDays,
  formatImpact,
  formatMoney,
  formatNumber,
} from "@/lib/format";
import { CONTRACT_TYPE_LABEL, ROLE_LABEL, TERMS, partyLabel } from "@/lib/labels";
import { useResource } from "@/lib/use-resource";

/**
 * The variation order as a formal document (FR-12): one A4 portrait page.
 * On screen it sits on the paper ground with a print button; in print only the
 * sheet remains.
 */
export default function VariationOrderPage() {
  const params = useParams<{ voId: string }>();
  const voId = decodeURIComponent(params.voId);
  const { id, contract } = useCurrentContract();
  const contracts = useContracts();

  const orders = useResource((s) => api.variationOrder(voId, s), [voId]);
  // The VO cites articles by their English reference; the ledger carries the
  // Arabic reference for each, straight from the regulation file.
  const ledger = useResource(id ? (s) => api.ledger(id, s) : null, [id]);
  const vo = orders.data?.variation_order;

  let body: ReactNode;
  const notFound = orders.status === "error" && orders.error instanceof ApiError && orders.error.status === 404;
  if (!notFound && (orders.status === "error" || contracts.status === "error")) {
    body = (
      <ErrorState
        error={orders.error ?? contracts.error}
        what="أمر التغيير"
        onRetry={() => {
          orders.reload();
          contracts.reload();
        }}
      />
    );
  } else if ((orders.status === "loading" && !notFound) || !contract) {
    body =
      contracts.status === "ready" && !contract ? (
        <Empty title={`لا يوجد عقد بالمرجع ${id ?? ""}`}>اختر عقدًا من أعلى الصفحة.</Empty>
      ) : (
        <Loading label="جارٍ تحميل أمر التغيير" rows={6} />
      );
  } else if (!vo) {
    body = (
      <Empty
        title={`لا يوجد أمر تغيير بالمرجع ${voId}`}
        action={
          <Link
            href={`/contracts/${encodeURIComponent(contract.id)}`}
            className={buttonVariants({ variant: "outline" })}
          >
            العودة إلى سجل الطلبات
          </Link>
        }
      >
        يصدر أمر التغيير بعد اكتمال سلسلة الاعتماد. افتح الطلب المعتمد وأصدره من ملفه.
      </Empty>
    );
  } else {
    const arabic: Record<string, string> = {};
    for (const s of Object.values(ledger.data?.usage ?? {})) {
      if (s?.article_ref_en && s.article_ref_ar) arabic[s.article_ref_en] = s.article_ref_ar;
    }
    return <VoDocument vo={vo} contract={contract} arabicRefs={arabic} />;
  }

  return <div className="mx-auto max-w-[90rem] px-4 pt-6 pb-16 md:px-8">{body}</div>;
}

function VoDocument({
  vo,
  contract,
  arabicRefs,
}: {
  vo: VariationOrder;
  contract: Contract;
  arabicRefs: Record<string, string>;
}) {
  const caseHref = `/contracts/${encodeURIComponent(contract.id)}/requests/${encodeURIComponent(vo.cr_id)}`;
  const lines = vo.cited_line_ids
    .map((lineId) => contract.breakdown.find((l) => l.id === lineId))
    .filter((l): l is BreakdownLine => Boolean(l));
  const client = partyLabel("GOVERNMENT_ENTITY", contract.contract_type);

  return (
    <div className="px-4 pt-6 pb-16 md:px-8 print:p-0">
      {/* Screen-only toolbar */}
      <div className="mx-auto mb-4 flex max-w-[210mm] flex-wrap items-center justify-between gap-3 print:hidden">
        <Link href={caseHref} className="text-sm underline-offset-4 hover:underline">
          ملف الطلب <span className="ref">{vo.cr_id}</span>
        </Link>
        <div className="flex items-center gap-3">
          {vo.recorded && <Badge variant="muted">صياغة مسجلة</Badge>}
          <Button onClick={() => window.print()}>طباعة</Button>
        </div>
      </div>

      <article
        aria-labelledby="vo-title"
        className="mx-auto max-w-[210mm] border border-rule bg-sheet px-6 py-8 font-doc sm:px-[14mm] sm:py-[12mm] print:max-w-none print:border-0 print:p-0"
      >
        {/* Letterhead */}
        <header className="rule-double pb-4 print:pb-2">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="font-sans text-xs text-ink-muted">
                عقد {CONTRACT_TYPE_LABEL[contract.contract_type]} رقم{" "}
                <span className="ref">{contract.id}</span>
              </p>
              <h1 id="vo-title" className="mt-1 text-2xl font-bold">
                {TERMS.VO}
              </h1>
              <p className="font-sans text-xs text-ink-muted">
                VO ({TERMS.VO})، صادر عن الطلب <span className="ref">{vo.cr_id}</span>
              </p>
            </div>
            <dl className="grid grid-cols-[auto_auto] gap-x-4 gap-y-1 font-sans text-sm">
              <dt className="text-ink-muted">الرقم</dt>
              <dd className="ref font-semibold">{vo.number}</dd>
              <dt className="text-ink-muted">التاريخ</dt>
              <dd className="font-medium">{formatDate(vo.issued_at)}</dd>
            </dl>
          </div>
          <p className="mt-3 text-base font-semibold print:mt-1">{contract.title_ar}</p>
          <dl className="mt-3 grid grid-cols-1 gap-3 text-sm sm:grid-cols-2 print:mt-2 print:grid-cols-2">
            <div className="border-s-2 border-ink ps-3">
              <dt className="font-sans text-xs text-ink-muted">الطرف الأول، {client}</dt>
              <dd className="font-semibold">{contract.entity_name}</dd>
            </div>
            <div className="border-s-2 border-ink ps-3">
              <dt className="font-sans text-xs text-ink-muted">الطرف الثاني، المقاول</dt>
              <dd className="font-semibold">{contract.contractor_name}</dd>
            </div>
          </dl>
        </header>

        <DocSection n={1} title="وصف التغيير">
          <p className="text-[0.9375rem] leading-7 whitespace-pre-line print:text-sm print:leading-6">{vo.scope_ar}</p>
        </DocSection>

        <DocSection n={2} title="البنود المتأثرة وأسعار العقد">
          {lines.length === 0 ? (
            <p className="text-sm">لا يقابل هذا الأمر بندًا قائمًا في جدول الكميات، فهو بند جديد.</p>
          ) : (
            <table className="w-full border-collapse font-sans text-sm">
              <thead>
                <tr className="border-y border-rule-strong text-xs text-ink-muted">
                  <th scope="col" className="py-1.5 pe-3 text-start font-medium">البند</th>
                  <th scope="col" className="py-1.5 pe-3 text-start font-medium">الوصف</th>
                  <th scope="col" className="py-1.5 pe-3 text-end font-medium">الكمية</th>
                  <th scope="col" className="py-1.5 text-end font-medium">سعر الوحدة في العقد</th>
                </tr>
              </thead>
              <tbody>
                {lines.map((l) => (
                  <tr key={l.id} className="border-b border-rule">
                    <td className="py-1.5 pe-3"><span className="ref font-medium">{l.id}</span></td>
                    <td className="py-1.5 pe-3">{l.description_ar}</td>
                    <td className="py-1.5 pe-3 text-end whitespace-nowrap">
                      {formatNumber(l.quantity)} {l.unit_ar}
                    </td>
                    <td className="py-1.5 text-end whitespace-nowrap">{formatMoney(l.unit_rate)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </DocSection>

        <DocSection n={3} title="القيمة والمدة">
          <dl className="grid grid-cols-2 gap-4 font-sans">
            <div>
              <dt className="text-xs text-ink-muted">قيمة الأمر</dt>
              <dd className="text-xl font-semibold print:text-lg">{formatImpact(vo.value)}</dd>
            </div>
            <div>
              <dt className="text-xs text-ink-muted">تمديد المدة</dt>
              <dd className="text-xl font-semibold print:text-lg">{formatDays(vo.time_extension_days)}</dd>
            </div>
          </dl>
          <p className="mt-2 font-sans text-xs text-ink-muted">
            حسبت القيمة قاعدة برمجية من الكميات وأسعار العقد، واعتمدها أصحاب الصلاحية أدناه.
          </p>
        </DocSection>

        <DocSection n={4} title="المواد النظامية المستشهد بها">
          {vo.cited_articles.length === 0 ? (
            <p className="text-sm">لا يستشهد هذا الأمر بمواد نظامية.</p>
          ) : (
            <ul className="space-y-1 text-sm">
              {vo.cited_articles.map((a) => (
                <li key={a} className="flex flex-wrap items-baseline gap-x-3">
                  {arabicRefs[a] && <span className="font-semibold">{arabicRefs[a]}</span>}
                  <span className="ref font-sans text-xs text-ink-muted">{a}</span>
                </li>
              ))}
            </ul>
          )}
        </DocSection>

        {/* Signature blocks */}
        <section aria-labelledby="vo-signatures" className="rule-double-top relative mt-6 pt-4 break-inside-avoid print:mt-3 print:pt-2">
          <h2 id="vo-signatures" className="text-base font-bold">التواقيع</h2>
          <ol className="mt-3 grid grid-cols-1 gap-x-8 gap-y-4 pe-28 sm:grid-cols-2 sm:pe-32 print:mt-1 print:grid-cols-2 print:gap-y-2 print:pe-32">
            {vo.signatures.map((sig, i) => (
              <li key={`${sig.role}-${i}`} className="border-b border-rule pb-2">
                <p className="font-sans text-xs text-ink-muted">
                  {ROLE_LABEL[sig.role]}، {partyLabel(sig.party, contract.contract_type)}
                </p>
                <p className="mt-2 text-lg font-semibold text-seal print:mt-0.5 print:text-base">{sig.decided_by}</p>
                <p className="font-sans text-xs text-ink-muted">{formatDateTime(sig.decided_at)}</p>
              </li>
            ))}
          </ol>
          <Seal
            date={formatDate(vo.issued_at)}
            className="pointer-events-none absolute end-0 top-4 size-24 -rotate-[8deg] opacity-90 sm:size-28"
          />
        </section>

        <footer className="mt-6 border-t border-rule pt-2 print:mt-3 font-sans text-[0.6875rem] leading-4 text-ink-muted">
          صدر هذا الأمر في MithaqAi بعد اكتمال سلسلة الاعتماد للطلب{" "}
          <span className="ref">{vo.cr_id}</span>. يوصي الوكيل ويصوغ، ولا يُلزم شيء إلا بتوقيع
          أصحاب الصلاحية أعلاه.
        </footer>
      </article>
    </div>
  );
}

function DocSection({ n, title, children }: { n: number; title: string; children: ReactNode }) {
  return (
    <section className="grid grid-cols-[1.75rem_1fr] gap-x-2 border-b border-rule py-4 break-inside-avoid print:py-2.5">
      <span className="font-sans text-sm font-semibold tabular-nums">{n}</span>
      <div className="min-w-0">
        <h2 className="text-base font-bold">{title}</h2>
        <div className="mt-2 print:mt-1">{children}</div>
      </div>
    </section>
  );
}
