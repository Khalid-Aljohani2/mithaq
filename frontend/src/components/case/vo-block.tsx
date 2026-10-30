"use client";

import Link from "next/link";
import { useState } from "react";

import { Button, buttonVariants } from "@/components/ui/button";
import { api, type ChangeRequest, type ChangeRequestResponse, type VariationOrder } from "@/lib/api";
import { formatDate, formatDays, formatImpact } from "@/lib/format";
import { errorMessage } from "@/lib/labels";
import { useResource } from "@/lib/use-resource";

const HAS_VO = new Set(["VO_ISSUED", "IN_EXECUTION", "CLOSED"]);

/**
 * Step 9 in the case file. When the chain is fully approved, an authorised
 * person issues the VO here; once it exists, the block links to the document.
 */
export function VoBlock({
  contractId,
  request,
  onIssued,
}: {
  contractId: string;
  request: ChangeRequest;
  onIssued: (data: ChangeRequestResponse) => void;
}) {
  const state = request.state ?? "RECEIVED";
  const hasVo = HAS_VO.has(state);
  const [issued, setIssued] = useState<VariationOrder | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // No endpoint returns the VO for a CR, so the contract's list is searched.
  const list = useResource(
    hasVo && !issued ? (s) => api.variationOrders(contractId, s) : null,
    [contractId, hasVo, issued],
  );
  const vo = issued ?? list.data?.variation_orders.find((v) => v.cr_id === request.id) ?? null;

  if (state !== "APPROVED" && !hasVo) return null;

  async function issue() {
    setBusy(true);
    setError(null);
    try {
      const result = await api.issueVariationOrder(request.id);
      setIssued(result.variation_order);
      const current = await api.changeRequest(request.id);
      onIssued(current);
    } catch (e) {
      setError(`لم يصدر أمر التغيير. ${errorMessage(e)}`);
    } finally {
      setBusy(false);
    }
  }

  if (!hasVo && !issued) {
    return (
      <section aria-labelledby="vo-issue" className="border-t-2 border-seal pt-4">
        <h2 id="vo-issue" className="font-doc text-xl font-semibold">إصدار أمر التغيير</h2>
        <p className="mt-2 text-sm">
          اكتملت سلسلة الاعتماد. يصدر VO (أمر تغيير) بالقيمة والمدة المعتمدتين، ويحمل
          تواقيع السلسلة وختم الاعتماد.
        </p>
        {error && (
          <p role="alert" className="mt-3 border-s-4 border-legal bg-legal-wash px-3 py-2 text-sm">
            {error}
          </p>
        )}
        <Button className="mt-4" onClick={issue} disabled={busy}>
          {busy ? "جارٍ إصدار أمر التغيير" : "إصدار أمر التغيير"}
        </Button>
      </section>
    );
  }

  const href = vo
    ? `/contracts/${encodeURIComponent(contractId)}/variation-orders/${encodeURIComponent(vo.id)}`
    : null;

  return (
    <section aria-labelledby="vo-ready" className="border-s-4 border-seal bg-seal-wash px-4 py-3">
      <h2 id="vo-ready" className="text-sm font-semibold text-seal">
        صدر VO (أمر تغيير){vo && <> رقم <span className="ref">{vo.number}</span></>}
      </h2>
      {vo ? (
        <>
          <p className="mt-1 text-sm">
            بتاريخ {formatDate(vo.issued_at)}، بقيمة {formatImpact(vo.value)}، و{formatDays(vo.time_extension_days)}.
          </p>
          {href && (
            <Link href={href} className={buttonVariants({ variant: "outline", className: "mt-3" })}>
              عرض أمر التغيير وطباعته
            </Link>
          )}
        </>
      ) : list.status === "error" ? (
        <p className="mt-1 text-sm">تعذر تحميل أمر التغيير. {errorMessage(list.error)}</p>
      ) : (
        <p className="mt-1 text-sm text-ink-muted" role="status">جارٍ تحميل أمر التغيير</p>
      )}
    </section>
  );
}
