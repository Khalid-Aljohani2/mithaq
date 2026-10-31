"use client";

import { Check, X } from "lucide-react";

import { Field } from "@/components/file";
import { ArabicOriginal, DocumentName } from "@/components/original";
import type { BreakdownLine, ChangeRequest, Contract } from "@/lib/api";
import { formatDate, formatDays, formatMoney, formatNumber } from "@/lib/format";
import { partyLabel } from "@/lib/labels";
import { useT } from "@/lib/prefs";
import type { Documents } from "@/lib/payload";
import { cn } from "@/lib/utils";

export function RequestZone({
  request,
  contract,
  documents,
}: {
  request: ChangeRequest;
  contract: Contract;
  documents: Documents | null;
}) {
  const t = useT();
  const matched = (request.matched_line_ids ?? [])
    .map((id) => contract.breakdown.find((l) => l.id === id))
    .filter((l): l is BreakdownLine => Boolean(l));
  const human =
    request.human_entered_amount != null ||
    request.human_entered_unit_rate != null ||
    request.human_entered_days != null;

  return (
    <div className="space-y-8">
      <section aria-labelledby="request-text">
        <h2 id="request-text" className="text-lg font-semibold">{t.case.requestText}</h2>
        <dl className="mt-2 grid grid-cols-2 gap-3 text-sm">
          <Field label={t.case.requester}>{request.requester_name}</Field>
          <Field label={t.case.party}>{partyLabel(request.requester_party, contract.contract_type)}</Field>
          <Field label={t.case.submittedOn}>{formatDate(request.submitted_at)}</Field>
          {(request.revision_count ?? 0) > 0 && (
            <Field label={t.case.revisions}>{request.revision_count}</Field>
          )}
        </dl>
        <ArabicOriginal className="mt-4">
          <blockquote className="border-s-2 border-ink ps-4 font-doc text-doc whitespace-pre-line">
            {request.body_ar}
          </blockquote>
        </ArabicOriginal>
      </section>

      <section aria-labelledby="matched-lines">
        <h2 id="matched-lines" className="text-lg font-semibold">{t.case.matchedLines}</h2>
        {matched.length === 0 ? (
          <p className="mt-2 text-sm text-ink-muted">
            {request.kind
              ? t.case.newItem
              : t.case.matchedAfterAnalysis}
          </p>
        ) : (
          <ul className="mt-3 space-y-3">
            {matched.map((line) => (
              <LineCard key={line.id} line={line} />
            ))}
          </ul>
        )}
      </section>

      <section aria-labelledby="attachments">
        <h2 id="attachments" className="text-lg font-semibold">{t.case.attachments}</h2>
        <Attachments request={request} documents={documents} />
      </section>

      {human && (
        <section aria-labelledby="human-values">
          <h2 id="human-values" className="text-lg font-semibold">{t.case.humanValues}</h2>
          <dl className="mt-2 grid grid-cols-2 gap-3 text-sm">
            {request.human_entered_amount != null && (
              <Field label={t.case.amount}>{formatMoney(request.human_entered_amount)}</Field>
            )}
            {request.human_entered_unit_rate != null && (
              <Field label={t.case.unitRate}>{formatMoney(request.human_entered_unit_rate)}</Field>
            )}
            {request.human_entered_days != null && (
              <Field label={t.case.duration}>{formatDays(request.human_entered_days)}</Field>
            )}
          </dl>
        </section>
      )}
    </div>
  );
}

/** A matched breakdown line, highlighted as the evidence the analysis used. */
export function LineCard({ line }: { line: BreakdownLine }) {
  const t = useT();
  return (
    <li className="border-s-4 border-seal bg-seal-wash/60 px-4 py-3">
      <p className="flex flex-wrap items-baseline gap-x-3">
        <span className="ref text-sm font-semibold">{line.id}</span>
        <ArabicOriginal as="span" showLabel={false} className="text-sm font-medium">
          {line.description_ar}
        </ArabicOriginal>
      </p>
      <dl className="mt-2 grid grid-cols-3 gap-2 text-sm">
        <Field label={t.case.quantity}>
          {formatNumber(line.quantity)}{" "}
          <ArabicOriginal as="span" showLabel={false}>
            {line.unit_ar}
          </ArabicOriginal>
        </Field>
        <Field label={t.case.contractRate}>{formatMoney(line.unit_rate)}</Field>
        <Field label={t.case.total}>{formatMoney(line.total)}</Field>
      </dl>
      {line.approved_product_ar && (
        <p className="mt-2 text-xs">
          <span className="text-ink-muted">{t.case.approvedProduct}</span>
          <ArabicOriginal as="span" showLabel={false}>
            {line.approved_product_ar}
          </ArabicOriginal>
        </p>
      )}
      {(line.restrictions_ar ?? []).length > 0 && (
        <ArabicOriginal showLabel={false}>
          <ul className="mt-1 list-disc ps-5 text-xs text-ink-muted">
            {line.restrictions_ar?.map((r) => <li key={r}>{r}</li>)}
          </ul>
        </ArabicOriginal>
      )}
    </li>
  );
}

function Attachments({
  request,
  documents,
}: {
  request: ChangeRequest;
  documents: Documents | null;
}) {
  const t = useT();
  const provided = request.attachments ?? [];
  const missing = documents?.missing ?? [];
  if (provided.length === 0 && missing.length === 0) {
    return <p className="mt-2 text-sm text-ink-muted">{t.case.noAttachments}</p>;
  }
  return (
    <ul className="mt-2 divide-y divide-rule border-y border-rule text-sm">
      {provided.map((doc) => (
        <li key={doc} className="flex items-center gap-2 py-2">
          <Check aria-hidden className="size-4 text-seal" />
          <DocumentName name={doc} />
        </li>
      ))}
      {missing.map((doc) => (
        <li key={doc} className={cn("flex items-center gap-2 py-2 text-amber")}>
          <X aria-hidden className="size-4" />
          <DocumentName name={doc} />
          <span className="ms-auto text-xs">{t.case.missing}</span>
        </li>
      ))}
    </ul>
  );
}
