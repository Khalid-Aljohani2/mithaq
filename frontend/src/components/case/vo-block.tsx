"use client";

import Link from "next/link";
import { useState } from "react";

import { Button, buttonVariants } from "@/components/ui/button";
import { api, type ChangeRequest, type ChangeRequestResponse, type VariationOrder } from "@/lib/api";
import { formatDate, formatDays, formatImpact } from "@/lib/format";
import { errorMessage } from "@/lib/labels";
import { useT } from "@/lib/prefs";
import { useResource } from "@/lib/use-resource";

const HAS_VO = new Set(["VO_ISSUED", "IN_EXECUTION", "CLOSED"]);

/**
 * Step 9 in the case file. When the chain is fully approved, an authorised
 * person issues the VO here; once it exists, the block links to the document.
 */
export function VoBlock({
  contractId,
  request,
  voId,
  onIssued,
}: {
  contractId: string;
  request: ChangeRequest;
  /** From GET /api/change-requests/{id}: the VO issued for this request, if any. */
  voId: string | null;
  onIssued: (data: ChangeRequestResponse) => void;
}) {
  const t = useT().vo;
  const state = request.state ?? "RECEIVED";
  const hasVo = HAS_VO.has(state);
  const [issued, setIssued] = useState<VariationOrder | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const single = useResource(
    voId && !issued ? (s) => api.variationOrder(voId, s) : null,
    [voId, issued],
  );
  const vo = issued ?? single.data?.variation_order ?? null;

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
      setError(t.issueFailed(errorMessage(e)));
    } finally {
      setBusy(false);
    }
  }

  if (!hasVo && !issued) {
    return (
      <section aria-labelledby="vo-issue" className="border-t-2 border-seal pt-4">
        <h2 id="vo-issue" className="font-doc text-xl font-semibold">{t.issueTitle}</h2>
        <p className="mt-2 text-sm">
          {t.issueIntro}
        </p>
        {error && (
          <p role="alert" className="mt-3 border-s-4 border-legal bg-legal-wash px-3 py-2 text-sm">
            {error}
          </p>
        )}
        <Button className="mt-4" onClick={issue} disabled={busy}>
          {busy ? t.issuing : t.issue}
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
        {t.issued}
        {vo && (
          <>
            {" "}
            {t.issuedNumber} <span className="ref">{vo.number}</span>
          </>
        )}
      </h2>
      {vo ? (
        <>
          <p className="mt-1 text-sm">
            {t.issuedSummary(formatDate(vo.issued_at), formatImpact(vo.value), formatDays(vo.time_extension_days))}
          </p>
          {href && (
            <Link href={href} className={buttonVariants({ variant: "outline", className: "mt-3" })}>
              {t.view}
            </Link>
          )}
        </>
      ) : single.status === "error" ? (
        <p className="mt-1 text-sm">{t.loadFailed(errorMessage(single.error))}</p>
      ) : (
        <p className="mt-1 text-sm text-ink-muted" role="status">{t.loading}</p>
      )}
    </section>
  );
}
