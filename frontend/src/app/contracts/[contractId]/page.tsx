"use client";

import Link from "next/link";
import { useEffect } from "react";

import { Empty, ErrorState, Field, Loading, Section, TermsKey } from "@/components/file";
import { ArabicOriginal } from "@/components/original";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { LimitRows, MeterKey, lawLimits, policyLimits } from "@/components/workspace/limits";
import { api, type ApprovalStep, type ChangeRequest, type Contract } from "@/lib/api";
import { useContracts, useCurrentContract } from "@/lib/contracts";
import { countRequests, formatDate, formatImpact, formatMoney } from "@/lib/format";
import {
  CONTRACT_TYPE_LABEL,
  RECOMMENDATION,
  ROLE_LABEL,
  STATE_LABEL,
  STATE_TONE,
  kindShort,
  partyLabel,
  type Term,
} from "@/lib/labels";
import { getDict, useBilingual, useT } from "@/lib/prefs";
import { rememberContract } from "@/lib/session";
import { useResource } from "@/lib/use-resource";

export default function ContractWorkspace() {
  const { id, contract } = useCurrentContract();
  const contracts = useContracts();
  const t = useT().workspace;

  useEffect(() => {
    if (contract) rememberContract(contract.id);
  }, [contract]);

  if (contracts.status === "error") {
    return (
      <Page>
        <ErrorState error={contracts.error} what={t.whatContract} onRetry={contracts.reload} />
      </Page>
    );
  }
  if (contracts.status === "loading") {
    return (
      <Page>
        <Loading label={t.loadingContract} />
      </Page>
    );
  }
  if (!contract) {
    return (
      <Page>
        <Empty
          title={t.noContract(id ?? "")}
          action={
            <Link href="/" className={buttonVariants({ variant: "outline" })}>
              {t.openFirst}
            </Link>
          }
        >
          {t.chooseFromList}
        </Empty>
      </Page>
    );
  }
  return <Workspace contract={contract} />;
}

function Page({ children }: { children: React.ReactNode }) {
  return <div className="mx-auto max-w-[90rem] px-4 pb-16 md:px-8">{children}</div>;
}

function Workspace({ contract }: { contract: Contract }) {
  const isGov = contract.contract_type === "GOVERNMENT";
  const t = useT().workspace;
  const pick = useBilingual();
  const ledger = useResource((s) => api.ledger(contract.id, s), [contract.id]);
  const register = useResource(async (signal) => {
    const list = await api.changeRequests(contract.id, signal);
    // The list has no chain, so the current approver needs each request's detail.
    const details = await Promise.all(
      list.requests.map((r) =>
        r.state === "IN_APPROVAL"
          ? api.changeRequest(r.id, signal).then((d) => d.chain)
          : Promise.resolve<ApprovalStep[]>([]),
      ),
    );
    return list.requests.map((request, i) => ({ request, chain: details[i] }));
  }, [contract.id]);

  const terms: Term[] = ["CR"];
  const kinds = new Set(register.data?.map((r) => r.request.kind));
  if (kinds.has("PCR")) terms.push("PCR");
  if (kinds.has("NCR")) terms.push("NCR");

  const newHref = `/contracts/${encodeURIComponent(contract.id)}/new`;

  return (
    <Page>
      <div className="pt-6">
        <TermsKey terms={terms} />
      </div>

      {/* Contract header: a definition table, not a hero number. */}
      <Section
        margin={
          <>
            <span className="block">{t.contractRef}</span>
            <span className="ref text-sm font-medium text-ink">{contract.id}</span>
          </>
        }
      >
        <div className="flex flex-wrap items-start gap-3">
          <ArabicOriginal as="span" showLabel={false} className="block">
            <h1 className="text-2xl font-semibold">{contract.title_ar}</h1>
          </ArabicOriginal>
          <Badge variant="neutral" className="mt-2">
            {t.contractOfType(CONTRACT_TYPE_LABEL[contract.contract_type])}
          </Badge>
        </div>
        <dl className="mt-5 grid grid-cols-2 gap-x-8 gap-y-4 md:grid-cols-[repeat(5,auto)] md:justify-start">
          <Field label={partyLabel("GOVERNMENT_ENTITY", contract.contract_type)}>
            <ArabicOriginal as="span" showLabel={false}>
              {contract.entity_name}
            </ArabicOriginal>
          </Field>
          <Field label={t.contractor}>
            <ArabicOriginal as="span" showLabel={false}>
              {contract.contractor_name}
            </ArabicOriginal>
          </Field>
          <Field label={t.originalValue}>{formatMoney(contract.original_value)}</Field>
          <Field label={t.startDate}>{formatDate(contract.start_date)}</Field>
          <Field label={t.endDate}>{formatDate(contract.end_date)}</Field>
        </dl>
      </Section>

      <Section
        id="limits"
        title={t.limitsTitle}
        action={
          <Link
            href={`/contracts/${encodeURIComponent(contract.id)}/limits`}
            className={buttonVariants({ variant: "outline" })}
          >
            {t.limitsDetails}
          </Link>
        }
        margin={
          ledger.status === "ready" ? (
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
          ) : null
        }
      >
        {ledger.status === "loading" ? (
          <Loading label={t.loadingLimits} rows={5} />
        ) : ledger.status === "error" ? (
          <ErrorState error={ledger.error} what={t.whatLimits} onRetry={ledger.reload} />
        ) : (
          <>
            <p className="mb-4 max-w-prose text-sm text-ink-muted">
              {isGov ? t.limitsIntroGov : t.limitsIntroPrivate}
            </p>
            <LimitRows limits={[...policyLimits(ledger.data), ...lawLimits(ledger.data)]} />
            <MeterKey />
          </>
        )}
      </Section>

      <Section
        id="register"
        title={t.registerTitle}
        margin={
          register.status === "ready" ? (
            <span>{countRequests(register.data.length)}</span>
          ) : null
        }
        action={
          <div className="flex flex-wrap items-center gap-3">
            <Link
              href={`/contracts/${encodeURIComponent(contract.id)}/audit`}
              className={buttonVariants({ variant: "outline" })}
            >
              {t.auditLog}
            </Link>
            <Link href={newHref} className={buttonVariants()}>
              {t.newRequest}
            </Link>
          </div>
        }
        className="border-b-0"
      >
        {register.status === "loading" ? (
          <Loading label={t.loadingRegister} />
        ) : register.status === "error" ? (
          <ErrorState error={register.error} what={t.whatRegister} onRetry={register.reload} />
        ) : register.data.length === 0 ? (
          <Empty
            title={t.emptyTitle}
            action={
              <Link href={newHref} className={buttonVariants()}>
                {t.submitFirst}
              </Link>
            }
          >
            {t.emptyHint}
          </Empty>
        ) : (
          <Register contract={contract} rows={register.data} />
        )}
      </Section>
    </Page>
  );
}

type Row = { request: ChangeRequest; chain: ApprovalStep[] };

function currentApprover(row: Row, contract: Contract): string {
  const { request, chain } = row;
  const d = getDict();
  if (request.state === "IN_APPROVAL") {
    const next = chain.find((s) => s.decision === "PENDING");
    return next
      ? `${ROLE_LABEL[next.role]}${d.common.listSep}${partyLabel(next.party, contract.contract_type)}`
      : d.workspace.chainComplete;
  }
  if (request.state === "RECOMMENDED") return d.workspace.approvalNotStarted;
  return d.workspace.none;
}

function Register({ contract, rows }: { contract: Contract; rows: Row[] }) {
  const t = useT().workspace;
  const href = (id: string) =>
    `/contracts/${encodeURIComponent(contract.id)}/requests/${encodeURIComponent(id)}`;

  return (
    <>
      {/* Wide: a real table. */}
      <div className="hidden overflow-x-auto md:block">
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="border-y border-rule-strong text-start text-xs text-ink-muted">
              <th scope="col" className="py-2 pe-4 text-start font-medium">{t.colRef}</th>
              <th scope="col" className="py-2 pe-4 text-start font-medium">{t.colState}</th>
              <th scope="col" className="py-2 pe-4 text-start font-medium">{t.colKind}</th>
              <th scope="col" className="py-2 pe-4 text-end font-medium">{t.colCost}</th>
              <th scope="col" className="py-2 pe-4 text-start font-medium">{t.colRecommendation}</th>
              <th scope="col" className="py-2 text-start font-medium">{t.colApprover}</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const r = row.request;
              const state = r.state ?? "RECEIVED";
              return (
                <tr key={r.id} className="border-b border-rule hover:bg-sheet">
                  <td className="py-3 pe-4">
                    <Link href={href(r.id)} className="ref font-medium underline-offset-4 hover:underline">
                      {r.id}
                    </Link>
                    <ArabicOriginal
                      as="span"
                      showLabel={false}
                      className="block max-w-[22rem] truncate text-xs text-ink-muted"
                    >
                      {r.requester_name}
                    </ArabicOriginal>
                  </td>
                  <td className="py-3 pe-4">
                    <Badge variant={STATE_TONE[state]}>{STATE_LABEL[state]}</Badge>
                  </td>
                  <td className="py-3 pe-4">{kindShort(r.kind)}</td>
                  <td className="py-3 pe-4 text-end">
                    {r.cost_impact === null || r.cost_impact === undefined
                      ? <span className="text-ink-muted">{t.notCalculated}</span>
                      : formatImpact(r.cost_impact)}
                  </td>
                  <td className="py-3 pe-4">
                    {r.recommendation ? (
                      RECOMMENDATION[r.recommendation].short
                    ) : (
                      <span className="text-ink-muted">{t.awaitingAnalysis}</span>
                    )}
                  </td>
                  <td className="py-3">{currentApprover(row, contract)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Narrow: ruled blocks. */}
      <ul className="divide-y divide-rule border-y border-rule-strong md:hidden">
        {rows.map((row) => {
          const r = row.request;
          const state = r.state ?? "RECEIVED";
          return (
            <li key={r.id}>
              <Link href={href(r.id)} className="block py-3">
                <span className="flex items-center justify-between gap-3">
                  <span className="ref font-medium">{r.id}</span>
                  <Badge variant={STATE_TONE[state]}>{STATE_LABEL[state]}</Badge>
                </span>
                <dl className="mt-2 grid grid-cols-3 gap-2 text-sm">
                  <Field label={t.colKind}>{kindShort(r.kind)}</Field>
                  <Field label={t.colCost}>
                    {r.cost_impact == null ? t.notCalculated : formatImpact(r.cost_impact)}
                  </Field>
                  <Field label={t.colRecommendation}>
                    {r.recommendation ? RECOMMENDATION[r.recommendation].short : t.awaitingAnalysis}
                  </Field>
                </dl>
                <p className="mt-2 text-xs text-ink-muted">
                  {t.approverLine(currentApprover(row, contract))}
                </p>
              </Link>
            </li>
          );
        })}
      </ul>
    </>
  );
}
