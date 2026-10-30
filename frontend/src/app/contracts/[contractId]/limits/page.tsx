"use client";

import Link from "next/link";

import { Empty, ErrorState, Loading, Section, TermsKey } from "@/components/file";
import { LimitDetail, MeterKey, lawLimits, policyLimits } from "@/components/workspace/limits";
import { api, type Contract } from "@/lib/api";
import { useContracts, useCurrentContract } from "@/lib/contracts";
import { formatDate, formatDays, formatImpact, formatMoney } from "@/lib/format";
import { useResource } from "@/lib/use-resource";

/**
 * Every limit on one contract: the organisation's policy caps and, on a
 * government contract, each Article 67 category, with the approved VOs that
 * make up the totals.
 */
export default function LimitsPage() {
  const { id, contract } = useCurrentContract();
  const contracts = useContracts();

  return (
    <div className="mx-auto max-w-[90rem] px-4 pb-16 md:px-8">
      {contracts.status === "error" ? (
        <div className="pt-6">
          <ErrorState error={contracts.error} what="العقد" onRetry={contracts.reload} />
        </div>
      ) : !contract ? (
        contracts.status === "loading" ? (
          <Loading label="جارٍ تحميل العقد" />
        ) : (
          <div className="pt-6">
            <Empty title={`لا يوجد عقد بالمرجع ${id ?? ""}`}>اختر عقدًا من أعلى الصفحة.</Empty>
          </div>
        )
      ) : (
        <Limits contract={contract} />
      )}
    </div>
  );
}

function Limits({ contract }: { contract: Contract }) {
  const ledger = useResource((s) => api.ledger(contract.id, s), [contract.id]);
  const orders = useResource((s) => api.variationOrders(contract.id, s), [contract.id]);
  const workspace = `/contracts/${encodeURIComponent(contract.id)}`;
  const isGov = contract.contract_type === "GOVERNMENT";

  return (
    <>
      <div className="pt-6">
        <TermsKey terms={["VO"]} />
      </div>
      <Section
        margin={
          <>
            <span className="block">مرجع العقد</span>
            <Link href={workspace} className="ref text-sm font-medium text-ink underline-offset-4 hover:underline">
              {contract.id}
            </Link>
          </>
        }
      >
        <h1 className="text-2xl font-semibold">حدود التغيير</h1>
        <p className="mt-1 max-w-prose text-sm text-ink-muted">{contract.title_ar}</p>
        <dl className="mt-4 flex flex-wrap gap-x-8 gap-y-2 text-sm">
          <div>
            <dt className="text-xs text-ink-muted">القيمة الأصلية</dt>
            <dd className="font-medium">{formatMoney(contract.original_value)}</dd>
          </div>
          <div>
            <dt className="text-xs text-ink-muted">المدة الأصلية</dt>
            <dd className="font-medium">
              {formatDate(contract.start_date)} إلى {formatDate(contract.end_date)}
            </dd>
          </div>
        </dl>
      </Section>

      {ledger.status === "loading" ? (
        <Loading label="جارٍ تحميل الحدود" rows={6} />
      ) : ledger.status === "error" ? (
        <div className="py-6">
          <ErrorState error={ledger.error} what="الحدود" onRetry={ledger.reload} />
        </div>
      ) : (
        <>
          <Section
            id="policy"
            title="حدود السياسة الداخلية"
            margin={<span>تُحتسب إجمالية على كل الطلبات المعتمدة</span>}
          >
            <p className="mb-4 max-w-prose text-sm text-ink-muted">
              حدود الجهة نفسها على التكلفة والمدة. لا يُتجاوز أي منهما إلا باستثناء
              يعتمده صاحب الصلاحية المسمّى أدناه.
            </p>
            <LimitDetail limits={policyLimits(ledger.data)} />
            <MeterKey />
          </Section>

          <Section
            id="law"
            title="حدود المادة السابعة والستين"
            margin={
              <>
                <span className="block">{ledger.data.regulation.law_name_ar}</span>
                <a
                  href={ledger.data.regulation.source_url}
                  target="_blank"
                  rel="noreferrer"
                  className="underline underline-offset-2"
                >
                  النص الرسمي
                </a>
              </>
            }
          >
            {ledger.data.legal_limits_apply ? (
              <>
                <p className="mb-4 max-w-prose text-sm text-ink-muted">
                  حدود نظامية ملزمة، كل منها بمادته، ومحسوبة من قيمة العقد الأصلية.
                </p>
                <LimitDetail limits={lawLimits(ledger.data)} />
                <MeterKey />
              </>
            ) : (
              <p className="max-w-prose text-sm text-ink-muted">
                {isGov
                  ? "لا تنطبق حدود المادة السابعة والستين على هذا العقد."
                  : "هذا عقد خاص، وحدود المادة السابعة والستين تنطبق على العقود الحكومية."}
              </p>
            )}
          </Section>
        </>
      )}

      <Section
        id="orders"
        title="أوامر التغيير المعتمدة"
        margin={<span>هي ما يكوّن الإجمالي المعتمد أعلاه</span>}
        className="border-b-0"
      >
        {orders.status === "loading" ? (
          <Loading label="جارٍ تحميل أوامر التغيير" rows={3} />
        ) : orders.status === "error" ? (
          <ErrorState error={orders.error} what="أوامر التغيير" onRetry={orders.reload} />
        ) : orders.data.variation_orders.length === 0 ? (
          <Empty title="لم يصدر أمر تغيير على هذا العقد بعد">
            يُحتسب الطلب من الحدود حين يصدر أمره بعد اكتمال سلسلة اعتماده. افتح{" "}
            <Link href={workspace} className="underline underline-offset-4">سجل الطلبات</Link>{" "}
            لمتابعة الطلبات قيد الاعتماد.
          </Empty>
        ) : (
          <table className="w-full max-w-4xl border-collapse text-sm">
            <thead>
              <tr className="border-y border-rule-strong text-xs text-ink-muted">
                <th scope="col" className="py-2 pe-4 text-start font-medium">الأمر</th>
                <th scope="col" className="py-2 pe-4 text-start font-medium">الطلب</th>
                <th scope="col" className="hidden py-2 pe-4 text-start font-medium sm:table-cell">التاريخ</th>
                <th scope="col" className="py-2 pe-4 text-end font-medium">القيمة</th>
                <th scope="col" className="py-2 text-end font-medium">المدة</th>
              </tr>
            </thead>
            <tbody>
              {orders.data.variation_orders.map((vo) => (
                <tr key={vo.id} className="border-b border-rule">
                  <td className="py-2.5 pe-4">
                    <Link
                      href={`${workspace}/variation-orders/${encodeURIComponent(vo.id)}`}
                      className="ref font-medium underline underline-offset-4"
                    >
                      {vo.number}
                    </Link>
                  </td>
                  <td className="py-2.5 pe-4">
                    <Link href={`${workspace}/requests/${encodeURIComponent(vo.cr_id)}`} className="ref underline-offset-4 hover:underline">
                      {vo.cr_id}
                    </Link>
                  </td>
                  <td className="hidden py-2.5 pe-4 sm:table-cell">{formatDate(vo.issued_at)}</td>
                  <td className="py-2.5 pe-4 text-end whitespace-nowrap">{formatImpact(vo.value)}</td>
                  <td className="py-2.5 text-end whitespace-nowrap">{formatDays(vo.time_extension_days)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Section>
    </>
  );
}
