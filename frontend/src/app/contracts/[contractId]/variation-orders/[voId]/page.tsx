"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import type { ReactNode } from "react";

import { Empty, ErrorState, Loading } from "@/components/file";
import { Seal } from "@/components/glyphs";
import { ArabicOriginal } from "@/components/original";
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
import { CONTRACT_TYPE_LABEL, ROLE_LABEL, partyLabel } from "@/lib/labels";
import { usePrefs, useT } from "@/lib/prefs";
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
  const t = useT();

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
        what={t.vo.what}
        onRetry={() => {
          orders.reload();
          contracts.reload();
        }}
      />
    );
  } else if ((orders.status === "loading" && !notFound) || !contract) {
    body =
      contracts.status === "ready" && !contract ? (
        <Empty title={t.vo.noContract(id ?? "")}>{t.vo.chooseContract}</Empty>
      ) : (
        <Loading label={t.vo.loading} rows={6} />
      );
  } else if (!vo) {
    body = (
      <Empty
        title={t.vo.notFound(voId)}
        action={
          <Link
            href={`/contracts/${encodeURIComponent(contract.id)}`}
            className={buttonVariants({ variant: "outline" })}
          >
            {t.vo.backToRequests}
          </Link>
        }
      >
        {t.vo.notFoundHint}
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
  const t = useT().vo;
  const { lang, t: all } = usePrefs();
  // The Arabic paragraph is the formal text. In English the drafted English
  // wording leads and the Arabic stays one click away; orders issued before
  // the English wording existed show the Arabic as before.
  const scopeEn = lang === "en" && vo.scope_en ? vo.scope_en : null;

  return (
    <div className="px-4 pt-6 pb-16 md:px-8 print:p-0">
      {/* Screen-only toolbar */}
      <div className="mx-auto mb-4 flex max-w-[210mm] flex-wrap items-center justify-between gap-3 print:hidden">
        <Link href={caseHref} className="text-sm underline-offset-4 hover:underline">
          {t.caseFile} <span className="ref">{vo.cr_id}</span>
        </Link>
        <div className="flex items-center gap-3">
          {vo.recorded && <Badge variant="muted">{t.recorded}</Badge>}
          <Button onClick={() => window.print()}>{t.print}</Button>
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
                {t.contractLine(CONTRACT_TYPE_LABEL[contract.contract_type])}{" "}
                <span className="ref">{contract.id}</span>
              </p>
              <h1 id="vo-title" className="mt-1 text-2xl font-bold">
                {t.title}
              </h1>
              <p className="font-sans text-xs text-ink-muted">
                {t.issuedFrom} <span className="ref">{vo.cr_id}</span>
              </p>
            </div>
            <dl className="grid grid-cols-[auto_auto] gap-x-4 gap-y-1 font-sans text-sm">
              <dt className="text-ink-muted">{t.number}</dt>
              <dd className="ref font-semibold">{vo.number}</dd>
              <dt className="text-ink-muted">{t.date}</dt>
              <dd className="font-medium">{formatDate(vo.issued_at)}</dd>
            </dl>
          </div>
          <ArabicOriginal as="span" showLabel={false} className="mt-3 block text-base font-semibold text-balance print:mt-1">
            {contract.title_ar}
          </ArabicOriginal>
          <dl className="mt-3 grid grid-cols-1 gap-3 text-sm sm:grid-cols-2 print:mt-2 print:grid-cols-2">
            <div className="border-s-2 border-ink ps-3">
              <dt className="font-sans text-xs text-ink-muted">{t.firstParty(client)}</dt>
              <dd className="font-semibold">
                <ArabicOriginal as="span" showLabel={false}>{contract.entity_name}</ArabicOriginal>
              </dd>
            </div>
            <div className="border-s-2 border-ink ps-3">
              <dt className="font-sans text-xs text-ink-muted">{t.secondParty}</dt>
              <dd className="font-semibold">
                <ArabicOriginal as="span" showLabel={false}>{contract.contractor_name}</ArabicOriginal>
              </dd>
            </div>
          </dl>
        </header>

        <DocSection n={1} title={t.scopeTitle}>
          {scopeEn ? (
            <>
              <p className="text-[0.9375rem] leading-7 print:text-sm print:leading-6">{scopeEn}</p>
              <details className="mt-2 font-sans text-xs text-ink-muted print:hidden">
                <summary className="cursor-pointer">{all.shell.originalArabic}</summary>
                <ArabicOriginal showLabel={false} className="mt-1 text-sm text-ink">
                  <p className="leading-7 whitespace-pre-line">{vo.scope_ar}</p>
                </ArabicOriginal>
              </details>
            </>
          ) : (
            <ArabicOriginal>
              <p className="text-[0.9375rem] leading-7 whitespace-pre-line print:text-sm print:leading-6">{vo.scope_ar}</p>
            </ArabicOriginal>
          )}
        </DocSection>

        <DocSection n={2} title={t.linesTitle}>
          {lines.length === 0 ? (
            <p className="text-sm">{t.noLines}</p>
          ) : (
            <table className="w-full border-collapse font-sans text-sm">
              <thead>
                <tr className="border-y border-rule-strong text-xs text-ink-muted">
                  <th scope="col" className="py-1.5 pe-3 text-start font-medium">{t.colItem}</th>
                  <th scope="col" className="py-1.5 pe-3 text-start font-medium">{t.colDescription}</th>
                  <th scope="col" className="py-1.5 pe-3 text-end font-medium">{t.colQuantity}</th>
                  <th scope="col" className="py-1.5 text-end font-medium">{t.colUnitRate}</th>
                </tr>
              </thead>
              <tbody>
                {lines.map((l) => (
                  <tr key={l.id} className="border-b border-rule">
                    <td className="py-1.5 pe-3"><span className="ref font-medium">{l.id}</span></td>
                    <td className="py-1.5 pe-3">
                      <ArabicOriginal as="span" showLabel={false}>{l.description_ar}</ArabicOriginal>
                    </td>
                    <td className="py-1.5 pe-3 text-end whitespace-nowrap">
                      {formatNumber(l.quantity)}{" "}
                      <ArabicOriginal as="span" showLabel={false}>{l.unit_ar}</ArabicOriginal>
                    </td>
                    <td className="py-1.5 text-end whitespace-nowrap">{formatMoney(l.unit_rate)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </DocSection>

        <DocSection n={3} title={t.valueTitle}>
          <dl className="grid grid-cols-2 gap-4 font-sans">
            <div>
              <dt className="text-xs text-ink-muted">{t.value}</dt>
              <dd className="text-xl font-semibold print:text-lg">{formatImpact(vo.value)}</dd>
            </div>
            <div>
              <dt className="text-xs text-ink-muted">{t.extension}</dt>
              <dd className="text-xl font-semibold print:text-lg">{formatDays(vo.time_extension_days)}</dd>
            </div>
          </dl>
          <p className="mt-2 font-sans text-xs text-ink-muted">
            {t.valueNote}
          </p>
        </DocSection>

        <DocSection n={4} title={t.articlesTitle}>
          {vo.cited_articles.length === 0 ? (
            <p className="text-sm">{t.noArticles}</p>
          ) : (
            <ul className="space-y-1 text-sm">
              {vo.cited_articles.map((a) => (
                <li key={a} className="flex flex-wrap items-baseline gap-x-3">
                  {arabicRefs[a] && (
                    <ArabicOriginal as="span" showLabel={false} className="font-semibold">
                      {arabicRefs[a]}
                    </ArabicOriginal>
                  )}
                  <span className="ref font-sans text-xs text-ink-muted">{a}</span>
                </li>
              ))}
            </ul>
          )}
        </DocSection>

        {/* Signature blocks */}
        <section aria-labelledby="vo-signatures" className="rule-double-top relative mt-6 pt-4 break-inside-avoid print:mt-3 print:pt-2">
          <h2 id="vo-signatures" className="text-base font-bold">{t.signatures}</h2>
          <ol className="mt-3 grid grid-cols-1 gap-x-8 gap-y-4 pe-28 sm:grid-cols-2 sm:pe-32 print:mt-1 print:grid-cols-2 print:gap-y-2 print:pe-32">
            {vo.signatures.map((sig, i) => (
              <li key={`${sig.role}-${i}`}>
                {/* A signature over its line, the signatory's capacity under it. */}
                <p className="border-b border-ink pb-1 text-lg font-semibold text-seal print:text-base">{sig.decided_by}</p>
                <p className="mt-1.5 font-sans text-xs font-medium">
                  {t.signer(ROLE_LABEL[sig.role], partyLabel(sig.party, contract.contract_type))}
                </p>
                <p className="font-sans text-xs text-ink-muted tabular-nums">{formatDateTime(sig.decided_at)}</p>
              </li>
            ))}
          </ol>
          <Seal
            date={formatDate(vo.issued_at)}
            className="pointer-events-none absolute end-0 top-4 size-24 -rotate-[8deg] opacity-90 sm:size-28"
          />
        </section>

        <footer className="mt-6 border-t border-rule pt-2 print:mt-3 font-sans text-[0.6875rem] leading-4 text-ink-muted">
          {t.footerBefore} <span className="ref">{vo.cr_id}</span>
          {t.footerAfter}
        </footer>
      </article>
    </div>
  );
}

function DocSection({ n, title, children }: { n: number; title: string; children: ReactNode }) {
  return (
    <section className="grid grid-cols-[1.75rem_1fr] items-baseline gap-x-2 border-b border-rule py-4 break-inside-avoid print:py-2.5">
      <span className="font-sans text-sm font-semibold tabular-nums">{n}</span>
      <div className="min-w-0">
        <h2 className="text-base font-bold text-balance">{title}</h2>
        <div className="mt-2 print:mt-1">{children}</div>
      </div>
    </section>
  );
}
