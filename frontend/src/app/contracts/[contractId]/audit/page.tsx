"use client";

import Link from "next/link";

import { Empty, ErrorState, Loading, Section, TermsKey } from "@/components/file";
import { Badge } from "@/components/ui/badge";
import { api, type AuditEvent, type Contract, type ContractType } from "@/lib/api";
import { useContracts, useCurrentContract } from "@/lib/contracts";
import { countEntries, formatDateTime } from "@/lib/format";
import { AUDIT_ACTION, RECOMMENDATION, STATE_LABEL, auditActor, partyLabel } from "@/lib/labels";
import { useResource } from "@/lib/use-resource";

/** The append-only audit log for one contract (FR-16), oldest entry first. */
export default function AuditPage() {
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
        <AuditLog contract={contract} />
      )}
    </div>
  );
}

function AuditLog({ contract }: { contract: Contract }) {
  const log = useResource((s) => api.audit(contract.id, s), [contract.id]);
  const workspace = `/contracts/${encodeURIComponent(contract.id)}`;
  const crHref = (crId: string) =>
    `${workspace}/requests/${encodeURIComponent(crId)}`;
  const events = log.data?.events ?? [];

  return (
    <>
      <div className="pt-6">
        <TermsKey terms={["CR", "VO"]} />
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
        <h1 className="text-2xl font-semibold">سجل التدقيق</h1>
        <p className="mt-1 max-w-prose text-sm text-ink-muted">{contract.title_ar}</p>
        <p className="mt-3 max-w-prose border-s-2 border-ink ps-3 text-sm">
          سجل إلحاقي: تُضاف القيود بترتيب وقوعها، ولا يُعدَّل قيد ولا يُحذف.
        </p>
      </Section>

      <Section
        margin={log.status === "ready" ? <span>{countEntries(events.length)}</span> : null}
        className="border-b-0"
      >
        {log.status === "loading" ? (
          <Loading label="جارٍ تحميل سجل التدقيق" rows={6} />
        ) : log.status === "error" ? (
          <ErrorState error={log.error} what="سجل التدقيق" onRetry={log.reload} />
        ) : events.length === 0 ? (
          <Empty title="لا قيود بعد على هذا العقد">
            يُسجَّل هنا كل تغيير في حالة أي طلب: الاستلام، والتحليل، وكل توقيع، وإصدار
            أمر التغيير. <Link href={`${workspace}/new`} className="underline underline-offset-4">قدّم طلب تغيير</Link> ليبدأ السجل.
          </Empty>
        ) : (
          <>
            <div className="hidden overflow-x-auto md:block">
              <table className="w-full border-collapse text-sm">
                <thead>
                  <tr className="border-y border-rule-strong text-xs text-ink-muted">
                    <th scope="col" className="py-2 pe-4 text-start font-medium">#</th>
                    <th scope="col" className="py-2 pe-4 text-start font-medium">الوقت</th>
                    <th scope="col" className="py-2 pe-4 text-start font-medium">المنفذ</th>
                    <th scope="col" className="py-2 pe-4 text-start font-medium">الإجراء</th>
                    <th scope="col" className="py-2 pe-4 text-start font-medium">الكيان</th>
                    <th scope="col" className="py-2 pe-4 text-start font-medium">الحالة السابقة</th>
                    <th scope="col" className="py-2 pe-4 text-start font-medium">الحالة الجديدة</th>
                    <th scope="col" className="py-2 text-start font-medium">السبب</th>
                  </tr>
                </thead>
                <tbody>
                  {events.map((e, i) => (
                    <tr key={e.id ?? i} className="border-b border-rule align-top">
                      <td className="py-2.5 pe-4 text-ink-muted tabular-nums">{e.id ?? i + 1}</td>
                      <td className="py-2.5 pe-4 whitespace-nowrap">{formatDateTime(e.occurred_at)}</td>
                      <td className="py-2.5 pe-4"><Actor event={e} contractType={contract.contract_type} /></td>
                      <td className="py-2.5 pe-4 font-medium">{AUDIT_ACTION[e.action]}</td>
                      <td className="py-2.5 pe-4"><Entity event={e} href={crHref} /></td>
                      <td className="py-2.5 pe-4 text-ink-muted">{stateText(e.previous_state)}</td>
                      <td className="py-2.5 pe-4">{stateText(e.new_state)}</td>
                      <td className="py-2.5 font-doc">{reasonText(e.reason) ?? <span className="font-sans text-ink-muted">بلا سبب مسجل</span>}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <ol className="divide-y divide-rule border-y border-rule-strong md:hidden">
              {events.map((e, i) => (
                <li key={e.id ?? i} className="py-3 text-sm">
                  <p className="flex items-baseline justify-between gap-3">
                    <span className="font-medium">{AUDIT_ACTION[e.action]}</span>
                    <span className="text-xs text-ink-muted tabular-nums">#{e.id ?? i + 1}</span>
                  </p>
                  <p className="mt-1 text-xs text-ink-muted">{formatDateTime(e.occurred_at)}</p>
                  <dl className="mt-2 grid grid-cols-2 gap-x-3 gap-y-1">
                    <dt className="text-xs text-ink-muted">المنفذ</dt>
                    <dd><Actor event={e} contractType={contract.contract_type} /></dd>
                    <dt className="text-xs text-ink-muted">الكيان</dt>
                    <dd><Entity event={e} href={crHref} /></dd>
                    <dt className="text-xs text-ink-muted">الحالة</dt>
                    <dd>
                      {e.previous_state || e.new_state
                        ? `${stateText(e.previous_state)} إلى ${stateText(e.new_state)}`
                        : "لا تغيير"}
                    </dd>
                    {e.reason && (
                      <>
                        <dt className="text-xs text-ink-muted">السبب</dt>
                        <dd className="font-doc">{reasonText(e.reason)}</dd>
                      </>
                    )}
                  </dl>
                </li>
              ))}
            </ol>
          </>
        )}
      </Section>
    </>
  );
}

/** Analysis entries record the recommendation code as their reason. */
function reasonText(reason: string | null | undefined): string | null {
  if (!reason) return null;
  return reason in RECOMMENDATION
    ? `التوصية: ${RECOMMENDATION[reason as keyof typeof RECOMMENDATION].short}`
    : reason;
}

function stateText(state: AuditEvent["previous_state"]): string {
  return state ? STATE_LABEL[state] : "لا يوجد";
}

/** Who acted: the system, or a person with their role and side. */
function Actor({ event, contractType }: { event: AuditEvent; contractType: ContractType }) {
  const actor = event.actor_role;
  if (actor === "CODE" || actor === "AI") {
    return <Badge variant="muted">{auditActor(actor)}</Badge>;
  }
  const party =
    event.actor_party === "GOVERNMENT_ENTITY" || event.actor_party === "CONTRACTOR"
      ? partyLabel(event.actor_party, contractType)
      : null;
  return (
    <span className="block">
      {event.actor_name && <span className="block font-doc font-medium">{event.actor_name}</span>}
      <span className={event.actor_name ? "block text-xs text-ink-muted" : "block"}>
        {auditActor(actor)}
        {party && <>، {party}</>}
      </span>
    </span>
  );
}

function Entity({ event, href }: { event: AuditEvent; href: (id: string) => string }) {
  if (event.entity_type === "change_request") {
    return (
      <Link href={href(event.entity_id)} className="ref underline-offset-4 hover:underline">
        {event.entity_id}
      </Link>
    );
  }
  return <span className="ref">{event.entity_id}</span>;
}
