"use client";

import { motion, useReducedMotion } from "motion/react";
import { useId, useState } from "react";

import { Seal } from "@/components/glyphs";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import type { ApprovalDecision, ApprovalStep, ContractType } from "@/lib/api";
import { formatDate, formatDateTime } from "@/lib/format";
import { CHAIN_REASON, ROLE_LABEL, partyLabel } from "@/lib/labels";
import { useT } from "@/lib/prefs";
import type { Persona } from "@/lib/session";
import { cn } from "@/lib/utils";

export type Decide = (
  step: ApprovalStep,
  decision: Exclude<ApprovalDecision, "PENDING">,
  decidedBy: string,
  reason: string | null,
) => Promise<boolean>;

/**
 * The approval chain as signature slots (FR-09, FR-10). Only the next pending
 * slot, and only when it belongs to the active persona, carries actions.
 */
export function ApprovalChain({
  chain,
  contractType,
  persona,
  active,
  articleRefs,
  justSigned,
  onDecide,
}: {
  chain: ApprovalStep[];
  contractType: ContractType;
  persona: Persona;
  active: boolean;
  articleRefs: string[];
  justSigned: number | null;
  onDecide: Decide;
}) {
  const next = active ? chain.find((s) => s.decision === "PENDING") : undefined;
  const sorted = [...chain].sort((a, b) => a.position - b.position);

  return (
    <ol className="space-y-0">
      {sorted.map((step) => {
        const mine =
          next?.position === step.position &&
          step.party === persona.party &&
          step.role === persona.role;
        return (
          <Slot
            key={step.position}
            step={step}
            contractType={contractType}
            isNext={next?.position === step.position}
            mine={mine}
            articleRefs={articleRefs}
            stamped={justSigned === step.position}
            onDecide={onDecide}
          />
        );
      })}
    </ol>
  );
}

function Slot({
  step,
  contractType,
  isNext,
  mine,
  articleRefs,
  stamped,
  onDecide,
}: {
  step: ApprovalStep;
  contractType: ContractType;
  isNext: boolean;
  mine: boolean;
  articleRefs: string[];
  stamped: boolean;
  onDecide: Decide;
}) {
  const reduce = useReducedMotion();
  const t = useT();
  const who = `${ROLE_LABEL[step.role]}${t.case.whoSep}${partyLabel(step.party, contractType)}`;
  const why = CHAIN_REASON[step.reason_code] ?? step.reason_code;
  const cites =
    step.reason_code === "CONTRACTOR_CONSENT" || step.reason_code === "LEGAL_REVIEW_REQUIRED"
      ? articleRefs
      : [];

  return (
    <li
      className={cn(
        "relative grid grid-cols-[2rem_1fr] gap-x-3 border-b border-rule py-4",
        isNext && "bg-sheet",
        step.decision === "APPROVED" && "bg-seal-wash/50",
      )}
    >
      <span className="pt-0.5 text-center text-lg font-semibold tabular-nums">{step.position}</span>
      <div className="min-w-0 pe-28">
        <p className="font-medium">{who}</p>
        <p className="mt-0.5 text-xs text-ink-muted">
          {why}
          {cites.length > 0 && (
            <>
              {" "}
              {cites.map((ref, i) => (
                <span key={ref}>
                  <span className="ref">{ref}</span>
                  {i < cites.length - 1 ? t.case.listSep : ""}
                </span>
              ))}
            </>
          )}
        </p>

        <SignatureLine step={step} />

        {stamped && step.decision === "APPROVED" && step.decided_by && (
          <motion.p
            role="status"
            data-testid="signed-confirmation"
            initial={reduce ? false : { opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.25, delay: reduce ? 0 : 0.35 }}
            className="mt-2 inline-flex items-start gap-2 border-s-2 border-seal ps-3 text-sm text-seal text-pretty"
          >
            {t.case.signedConfirm(step.decided_by, ROLE_LABEL[step.role])}
          </motion.p>
        )}

        {isNext && !mine && (
          <p className="mt-3 border-s-2 border-amber ps-3 text-xs">
            {t.case.nextFor(who)}
          </p>
        )}
        {mine && <SlotActions step={step} onDecide={onDecide} />}
      </div>

      {step.decision === "APPROVED" && step.decided_at && (
        <motion.div
          className="absolute end-0 top-3 size-28"
          initial={stamped && !reduce ? { scale: 1.35, rotate: -14, opacity: 0 } : false}
          animate={{ scale: 1, rotate: -8, opacity: 0.92 }}
          transition={{ type: "spring", stiffness: 420, damping: 22, mass: 0.8 }}
        >
          {stamped && !reduce && (
            <motion.span
              aria-hidden
              className="absolute inset-0 rounded-full border-2 border-seal"
              initial={{ scale: 1, opacity: 0.6 }}
              animate={{ scale: 1.5, opacity: 0 }}
              transition={{ duration: 0.5, delay: 0.12 }}
            />
          )}
          <Seal date={formatDate(step.decided_at)} className="size-full" />
        </motion.div>
      )}
    </li>
  );
}

function SignatureLine({ step }: { step: ApprovalStep }) {
  const t = useT();
  if (step.decision === "PENDING" || !step.decision) {
    return (
      <div className="mt-4 flex items-end gap-2 text-xs text-ink-muted">
        <span>{t.case.signature}</span>
        <span aria-hidden className="mb-1 flex-1 border-b border-dotted border-rule-strong" />
      </div>
    );
  }
  const tone =
    step.decision === "APPROVED" ? "text-seal" : step.decision === "REJECTED" ? "text-legal" : "text-amber";
  const verb =
    step.decision === "APPROVED"
      ? t.case.verbApproved
      : step.decision === "REJECTED"
        ? t.case.verbRejected
        : t.case.verbRevision;
  return (
    <div className="mt-3">
      <p className={cn("font-doc text-base font-semibold", tone)}>
        {verb}: {step.decided_by}
      </p>
      {step.decided_at && (
        <p className="text-xs text-ink-muted">{formatDateTime(step.decided_at)}</p>
      )}
      {step.reason && (
        <p dir="auto" className="mt-1 border-s-2 border-rule-strong ps-3 text-start font-doc text-sm">
          {step.reason}
        </p>
      )}
    </div>
  );
}

function SlotActions({ step, onDecide }: { step: ApprovalStep; onDecide: Decide }) {
  const t = useT();
  const nameId = useId();
  const reasonId = useId();
  const [name, setName] = useState("");
  const [mode, setMode] = useState<"REJECTED" | "REVISION_REQUESTED" | null>(null);
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [touched, setTouched] = useState(false);

  const nameMissing = !name.trim();
  const reasonMissing = mode !== null && !reason.trim();

  async function submit(decision: Exclude<ApprovalDecision, "PENDING">) {
    setTouched(true);
    if (nameMissing) return;
    if (decision !== "APPROVED" && !reason.trim()) return;
    setBusy(true);
    const ok = await onDecide(step, decision, name.trim(), decision === "APPROVED" ? null : reason.trim());
    if (!ok) setBusy(false);
  }

  return (
    <div className="mt-4 space-y-3">
      <div>
        <label htmlFor={nameId} className="text-xs font-medium">
          {t.case.signAs}
        </label>
        <Input
          id={nameId}
          value={name}
          onChange={(e) => setName(e.target.value)}
          aria-invalid={touched && nameMissing}
          aria-describedby={touched && nameMissing ? `${nameId}-err` : undefined}
          className="mt-1 font-doc"
          autoComplete="name"
        />
        {touched && nameMissing && (
          <p id={`${nameId}-err`} className="mt-1 text-xs text-legal">
            {t.case.nameMissing}
          </p>
        )}
      </div>

      {mode === null ? (
        <div className="flex flex-wrap gap-2">
          <Button onClick={() => submit("APPROVED")} disabled={busy}>
            {t.case.approve}
          </Button>
          <Button variant="destructive" onClick={() => setMode("REJECTED")} disabled={busy}>
            {t.case.reject}
          </Button>
          <Button variant="amber" onClick={() => setMode("REVISION_REQUESTED")} disabled={busy}>
            {t.case.requestRevision}
          </Button>
        </div>
      ) : (
        <div>
          <label htmlFor={reasonId} className="text-xs font-medium">
            {mode === "REJECTED" ? t.case.rejectReason : t.case.revisionWanted}
          </label>
          <Textarea
            id={reasonId}
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            rows={3}
            autoFocus
            aria-invalid={touched && reasonMissing}
            aria-describedby={`${reasonId}-hint`}
            className="mt-1 font-doc"
          />
          <p
            id={`${reasonId}-hint`}
            className={cn("mt-1 text-xs", touched && reasonMissing ? "text-legal" : "text-ink-muted")}
          >
            {t.case.reasonHint}
          </p>
          <div className="mt-2 flex flex-wrap gap-2">
            <Button
              variant={mode === "REJECTED" ? "destructive" : "amber"}
              onClick={() => submit(mode)}
              disabled={busy}
            >
              {mode === "REJECTED" ? t.case.confirmReject : t.case.sendRevision}
            </Button>
            <Button
              variant="ghost"
              onClick={() => {
                setMode(null);
                setReason("");
                setTouched(false);
              }}
              disabled={busy}
            >
              {t.case.cancel}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
