"use client";

import { Check, X } from "lucide-react";

import { Field } from "@/components/file";
import type { BreakdownLine, ChangeRequest, Contract } from "@/lib/api";
import { formatDate, formatDays, formatMoney, formatNumber } from "@/lib/format";
import { partyLabel } from "@/lib/labels";
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
        <h2 id="request-text" className="text-lg font-semibold">نص الطلب</h2>
        <dl className="mt-2 grid grid-cols-2 gap-3 text-sm">
          <Field label="مقدم الطلب">{request.requester_name}</Field>
          <Field label="الطرف">{partyLabel(request.requester_party, contract.contract_type)}</Field>
          <Field label="تاريخ التقديم">{formatDate(request.submitted_at)}</Field>
          {(request.revision_count ?? 0) > 0 && (
            <Field label="مرات التعديل">{request.revision_count}</Field>
          )}
        </dl>
        <blockquote className="mt-4 border-s-2 border-ink ps-4 font-doc text-doc whitespace-pre-line">
          {request.body_ar}
        </blockquote>
      </section>

      <section aria-labelledby="matched-lines">
        <h2 id="matched-lines" className="text-lg font-semibold">البنود المطابقة في العقد</h2>
        {matched.length === 0 ? (
          <p className="mt-2 text-sm text-ink-muted">
            {request.kind
              ? "لا يقابل الطلب أي بند في جدول الكميات، فهو بند جديد."
              : "تظهر البنود المطابقة بعد تحليل الطلب."}
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
        <h2 id="attachments" className="text-lg font-semibold">المرفقات</h2>
        <Attachments request={request} documents={documents} />
      </section>

      {human && (
        <section aria-labelledby="human-values">
          <h2 id="human-values" className="text-lg font-semibold">قيم أدخلها مقدم الطلب</h2>
          <dl className="mt-2 grid grid-cols-2 gap-3 text-sm">
            {request.human_entered_amount != null && (
              <Field label="المبلغ">{formatMoney(request.human_entered_amount)}</Field>
            )}
            {request.human_entered_unit_rate != null && (
              <Field label="سعر الوحدة">{formatMoney(request.human_entered_unit_rate)}</Field>
            )}
            {request.human_entered_days != null && (
              <Field label="المدة">{formatDays(request.human_entered_days)}</Field>
            )}
          </dl>
        </section>
      )}
    </div>
  );
}

/** A matched breakdown line, highlighted as the evidence the analysis used. */
export function LineCard({ line }: { line: BreakdownLine }) {
  return (
    <li className="border-s-4 border-seal bg-seal-wash/60 px-4 py-3">
      <p className="flex flex-wrap items-baseline gap-x-3">
        <span className="ref text-sm font-semibold">{line.id}</span>
        <span className="text-sm font-medium">{line.description_ar}</span>
      </p>
      <dl className="mt-2 grid grid-cols-3 gap-2 text-sm">
        <Field label="الكمية">
          {formatNumber(line.quantity)} {line.unit_ar}
        </Field>
        <Field label="سعر العقد">{formatMoney(line.unit_rate)}</Field>
        <Field label="الإجمالي">{formatMoney(line.total)}</Field>
      </dl>
      {line.approved_product_ar && (
        <p className="mt-2 text-xs">
          <span className="text-ink-muted">المنتج المعتمد: </span>
          {line.approved_product_ar}
        </p>
      )}
      {(line.restrictions_ar ?? []).length > 0 && (
        <ul className="mt-1 list-disc ps-5 text-xs text-ink-muted">
          {line.restrictions_ar?.map((r) => <li key={r}>{r}</li>)}
        </ul>
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
  const provided = request.attachments ?? [];
  const missing = documents?.missing ?? [];
  if (provided.length === 0 && missing.length === 0) {
    return <p className="mt-2 text-sm text-ink-muted">لم يُرفق مقدم الطلب أي مستند.</p>;
  }
  return (
    <ul className="mt-2 divide-y divide-rule border-y border-rule text-sm">
      {provided.map((doc) => (
        <li key={doc} className="flex items-center gap-2 py-2">
          <Check aria-hidden className="size-4 text-seal" />
          {doc}
        </li>
      ))}
      {missing.map((doc) => (
        <li key={doc} className={cn("flex items-center gap-2 py-2 text-amber")}>
          <X aria-hidden className="size-4" />
          {doc}
          <span className="ms-auto text-xs">ناقص</span>
        </li>
      ))}
    </ul>
  );
}
