"use client";

import Link from "next/link";

import { Empty, ErrorState, Loading, Section, TermsKey } from "@/components/file";
import { ArabicOriginal } from "@/components/original";
import { ClosestLegalLimit, LimitDetail, MeterKey, lawLimits, latestChanges, policyLimits } from "@/components/workspace/limits";
import { api, type Contract } from "@/lib/api";
import { useContracts, useCurrentContract } from "@/lib/contracts";
import { formatDate, formatDays, formatImpact, formatMoney } from "@/lib/format";
import { useBilingual, useT } from "@/lib/prefs";
import { useResource } from "@/lib/use-resource";

/**
 * Every limit on one contract: the organisation's policy caps and, on a
 * government contract, each Article 67 category, with the approved VOs that
 * make up the totals.
 */
export default function LimitsPage() {
  const { id, contract } = useCurrentContract();
  const contracts = useContracts();
  const t = useT().limits;

  return (
    <div className="mx-auto max-w-[90rem] px-4 pb-16 md:px-8">
      {contracts.status === "error" ? (
        <div className="pt-6">
          <ErrorState error={contracts.error} what={t.whatContract} onRetry={contracts.reload} />
        </div>
      ) : !contract ? (
        contracts.status === "loading" ? (
          <Loading label={t.loadingContract} />
        ) : (
          <div className="pt-6">
            <Empty title={t.noContract(id ?? "")}>{t.chooseAbove}</Empty>
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
  const t = useT().limits;
  const pick = useBilingual();
  const voNumber = (crId: string) =>
    orders.status === "ready"
      ? (orders.data.variation_orders.find((vo) => vo.cr_id === crId)?.number ?? null)
      : null;
  const latest = ledger.status === "ready" ? latestChanges(ledger.data, voNumber) : {};

  return (
    <>
      <div className="pt-6">
        <TermsKey terms={["VO"]} />
      </div>
      <Section
        margin={
          <>
            <span className="block">{t.contractRef}</span>
            <Link href={workspace} className="ref text-sm font-medium text-ink underline-offset-4 hover:underline">
              {contract.id}
            </Link>
          </>
        }
      >
        <h1 className="text-2xl font-semibold">{t.title}</h1>
        <ArabicOriginal as="span" showLabel={false} className="mt-1 block max-w-prose text-sm text-ink-muted">
          {contract.title_ar}
        </ArabicOriginal>
        <dl className="mt-4 flex flex-wrap gap-x-8 gap-y-2 text-sm">
          <div>
            <dt className="text-xs text-ink-muted">{t.originalValue}</dt>
            <dd className="font-medium">{formatMoney(contract.original_value)}</dd>
          </div>
          <div>
            <dt className="text-xs text-ink-muted">{t.originalDuration}</dt>
            <dd className="font-medium">
              {t.dateRange(formatDate(contract.start_date), formatDate(contract.end_date))}
            </dd>
          </div>
        </dl>
        {ledger.status === "ready" && ledger.data.legal_limits_apply && (
          <ClosestLegalLimit ledger={ledger.data} />
        )}
      </Section>

      {ledger.status === "loading" ? (
        <Loading label={t.loadingLimits} rows={6} />
      ) : ledger.status === "error" ? (
        <div className="py-6">
          <ErrorState error={ledger.error} what={t.whatLimits} onRetry={ledger.reload} />
        </div>
      ) : (
        <>
          <Section
            id="policy"
            title={t.policyTitle}
            margin={<span>{t.policyMargin}</span>}
          >
            <p className="mb-4 max-w-prose text-sm text-ink-muted">
              {t.policyIntro}
            </p>
            <LimitDetail limits={policyLimits(ledger.data)} latest={latest} />
            <MeterKey />
          </Section>

          <Section
            id="law"
            title={t.lawTitle}
            margin={
              <>
                <span className="block">
                  {pick(ledger.data.regulation.law_name_ar, ledger.data.regulation.law_name_en)}
                </span>
                <a
                  href={ledger.data.regulation.source_url}
                  target="_blank"
                  rel="noreferrer"
                  className="underline underline-offset-2"
                >
                  {t.officialText}
                </a>
              </>
            }
          >
            {ledger.data.legal_limits_apply ? (
              <>
                <p className="mb-4 max-w-prose text-sm text-ink-muted">
                  {t.lawIntro}
                </p>
                <LimitDetail limits={lawLimits(ledger.data)} latest={latest} />
                <MeterKey />
              </>
            ) : (
              <p className="max-w-prose text-sm text-ink-muted">
                {isGov ? t.lawNotApplyGov : t.lawNotApplyPrivate}
              </p>
            )}
          </Section>
        </>
      )}

      <Section
        id="orders"
        title={t.ordersTitle}
        margin={<span>{t.ordersMargin}</span>}
        className="border-b-0"
      >
        {orders.status === "loading" ? (
          <Loading label={t.loadingOrders} rows={3} />
        ) : orders.status === "error" ? (
          <ErrorState error={orders.error} what={t.whatOrders} onRetry={orders.reload} />
        ) : orders.data.variation_orders.length === 0 ? (
          <Empty title={t.noOrders}>
            {t.noOrdersBefore}{" "}
            <Link href={workspace} className="underline underline-offset-4">{t.noOrdersLink}</Link>{" "}
            {t.noOrdersAfter}
          </Empty>
        ) : (
          <table className="w-full max-w-4xl border-collapse text-sm">
            <thead>
              <tr className="border-y border-rule-strong text-xs text-ink-muted">
                <th scope="col" className="py-2 pe-4 text-start font-medium">{t.colOrder}</th>
                <th scope="col" className="py-2 pe-4 text-start font-medium">{t.colRequest}</th>
                <th scope="col" className="hidden py-2 pe-4 text-start font-medium sm:table-cell">{t.colDate}</th>
                <th scope="col" className="py-2 pe-4 text-end font-medium">{t.colValue}</th>
                <th scope="col" className="py-2 text-end font-medium">{t.colDuration}</th>
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
