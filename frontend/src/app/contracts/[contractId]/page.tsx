"use client";

import Link from "next/link";
import { useEffect } from "react";

import { Empty, ErrorState, Field, Loading, Section, TermsKey } from "@/components/file";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { LimitsSummary } from "@/components/workspace/limits";
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
import { rememberContract } from "@/lib/session";
import { useResource } from "@/lib/use-resource";

export default function ContractWorkspace() {
  const { id, contract } = useCurrentContract();
  const contracts = useContracts();

  useEffect(() => {
    if (contract) rememberContract(contract.id);
  }, [contract]);

  if (contracts.status === "error") {
    return (
      <Page>
        <ErrorState error={contracts.error} what="العقد" onRetry={contracts.reload} />
      </Page>
    );
  }
  if (contracts.status === "loading") {
    return (
      <Page>
        <Loading label="جارٍ تحميل العقد" />
      </Page>
    );
  }
  if (!contract) {
    return (
      <Page>
        <Empty
          title={`لا يوجد عقد بالمرجع ${id ?? ""}`}
          action={
            <Link href="/" className={buttonVariants({ variant: "outline" })}>
              فتح أول عقد متاح
            </Link>
          }
        >
          اختر عقدًا من قائمة العقود أعلى الصفحة.
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
            <span className="block">مرجع العقد</span>
            <span className="ref text-sm font-medium text-ink">{contract.id}</span>
          </>
        }
      >
        <div className="flex flex-wrap items-start gap-3">
          <h1 className="text-2xl font-semibold">{contract.title_ar}</h1>
          <Badge variant="neutral" className="mt-2">
            عقد {CONTRACT_TYPE_LABEL[contract.contract_type]}
          </Badge>
        </div>
        <dl className="mt-5 grid grid-cols-2 gap-x-8 gap-y-4 md:grid-cols-[repeat(5,auto)] md:justify-start">
          <Field label={partyLabel("GOVERNMENT_ENTITY", contract.contract_type)}>
            {contract.entity_name}
          </Field>
          <Field label="المقاول">{contract.contractor_name}</Field>
          <Field label="القيمة الأصلية">{formatMoney(contract.original_value)}</Field>
          <Field label="تاريخ البداية">{formatDate(contract.start_date)}</Field>
          <Field label="تاريخ النهاية">{formatDate(contract.end_date)}</Field>
        </dl>
      </Section>

      <Section
        id="limits"
        title="حدود التغيير التراكمية"
        margin={
          ledger.status === "ready" ? (
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
          ) : null
        }
      >
        {!isGov ? (
          <p className="max-w-prose text-sm text-ink-muted">
            حدود المادة السابعة والستين تنطبق على العقود الحكومية. يعرض ملف كل
            طلب نتيجة فحص حدود السياسة الداخلية الخاصة به.
          </p>
        ) : ledger.status === "loading" ? (
          <Loading label="جارٍ تحميل الحدود" rows={5} />
        ) : ledger.status === "error" ? (
          <ErrorState error={ledger.error} what="الحدود" onRetry={ledger.reload} />
        ) : (
          <>
            <p className="mb-4 max-w-prose text-sm text-ink-muted">
              المستخدم من كل حد في المادة السابعة والستين، محسوبًا من قيمة العقد
              الأصلية. حدود السياسة الداخلية تظهر في ملف كل طلب.
            </p>
            <LimitsSummary ledger={ledger.data} />
          </>
        )}
      </Section>

      <Section
        id="register"
        title="سجل طلبات التغيير"
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
              سجل التدقيق
            </Link>
            <Link href={newHref} className={buttonVariants()}>
              طلب تغيير جديد
            </Link>
          </div>
        }
        className="border-b-0"
      >
        {register.status === "loading" ? (
          <Loading label="جارٍ تحميل سجل الطلبات" />
        ) : register.status === "error" ? (
          <ErrorState error={register.error} what="سجل الطلبات" onRetry={register.reload} />
        ) : register.data.length === 0 ? (
          <Empty
            title="لا توجد طلبات تغيير على هذا العقد"
            action={
              <Link href={newHref} className={buttonVariants()}>
                تقديم أول طلب تغيير
              </Link>
            }
          >
            كل طلب يُسجَّل هنا بمرجعه وحالته وأثره، ويراه الطرفان معًا.
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
  if (request.state === "IN_APPROVAL") {
    const next = chain.find((s) => s.decision === "PENDING");
    return next
      ? `${ROLE_LABEL[next.role]}، ${partyLabel(next.party, contract.contract_type)}`
      : "اكتملت السلسلة";
  }
  if (request.state === "RECOMMENDED") return "لم يبدأ الاعتماد";
  return "لا يوجد";
}

function Register({ contract, rows }: { contract: Contract; rows: Row[] }) {
  const href = (id: string) =>
    `/contracts/${encodeURIComponent(contract.id)}/requests/${encodeURIComponent(id)}`;

  return (
    <>
      {/* Wide: a real table. */}
      <div className="hidden overflow-x-auto md:block">
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="border-y border-rule-strong text-start text-xs text-ink-muted">
              <th scope="col" className="py-2 pe-4 text-start font-medium">المرجع</th>
              <th scope="col" className="py-2 pe-4 text-start font-medium">الحالة</th>
              <th scope="col" className="py-2 pe-4 text-start font-medium">النوع</th>
              <th scope="col" className="py-2 pe-4 text-end font-medium">أثر التكلفة</th>
              <th scope="col" className="py-2 pe-4 text-start font-medium">التوصية</th>
              <th scope="col" className="py-2 text-start font-medium">المعتمد الحالي</th>
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
                    <span className="block max-w-[22rem] truncate text-xs text-ink-muted">
                      {r.requester_name}
                    </span>
                  </td>
                  <td className="py-3 pe-4">
                    <Badge variant={STATE_TONE[state]}>{STATE_LABEL[state]}</Badge>
                  </td>
                  <td className="py-3 pe-4">{kindShort(r.kind)}</td>
                  <td className="py-3 pe-4 text-end">
                    {r.cost_impact === null || r.cost_impact === undefined
                      ? <span className="text-ink-muted">لم يُحسب</span>
                      : formatImpact(r.cost_impact)}
                  </td>
                  <td className="py-3 pe-4">
                    {r.recommendation ? (
                      RECOMMENDATION[r.recommendation].short
                    ) : (
                      <span className="text-ink-muted">بانتظار التحليل</span>
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
                  <Field label="النوع">{kindShort(r.kind)}</Field>
                  <Field label="أثر التكلفة">
                    {r.cost_impact == null ? "لم يُحسب" : formatImpact(r.cost_impact)}
                  </Field>
                  <Field label="التوصية">
                    {r.recommendation ? RECOMMENDATION[r.recommendation].short : "بانتظار التحليل"}
                  </Field>
                </dl>
                <p className="mt-2 text-xs text-ink-muted">
                  المعتمد الحالي: {currentApprover(row, contract)}
                </p>
              </Link>
            </li>
          );
        })}
      </ul>
    </>
  );
}
