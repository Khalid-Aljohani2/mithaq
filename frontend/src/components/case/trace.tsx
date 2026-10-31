"use client";

import { ChevronDown } from "lucide-react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { useState } from "react";

import { ActorGlyph } from "@/components/glyphs";
import { ArabicOriginal } from "@/components/original";
import { Badge } from "@/components/ui/badge";
import type { ActorType, ApprovalStep, ChangeRequest, StageResult } from "@/lib/api";
import { formatDateTime, formatDays, formatDuration, formatImpact } from "@/lib/format";
import { STAGES } from "@/lib/labels";
import { payloadEntries } from "@/lib/payload";
import { getDict, getLang, usePrefs, useT } from "@/lib/prefs";
import { cn } from "@/lib/utils";

type Marker = "done" | "active" | "waiting" | "blocked" | "held" | "na";

type Row = {
  no: number;
  name: string;
  actor: ActorType;
  marker: Marker;
  status: string;
  summary: string | null;
  /** True when the summary is Arabic shown in the English interface. */
  arabicOnly?: boolean;
  result: StageResult | null;
};

function fromResult(result: StageResult): Pick<Row, "marker" | "status"> {
  const t = getDict().case;
  // Missing paperwork holds the request; it is not a legal block, so it is
  // amber, not red.
  if (result.status === "BLOCKED" && result.stage === "DOCUMENT_VALIDATION") {
    return { marker: "held", status: t.awaitingDocs };
  }
  if (result.status === "BLOCKED") return { marker: "blocked", status: t.blocked };
  if (result.status === "OK") return { marker: "done", status: t.done };
  return { marker: "done", status: result.status };
}

/** Stages 8 to 11 from the workflow state, when the trace has no record of them. */
function humanStage(
  no: number,
  request: ChangeRequest,
  chain: ApprovalStep[],
): Pick<Row, "marker" | "status" | "summary"> {
  const t = getDict().case;
  const state = request.state ?? "RECEIVED";
  const signed = chain.filter((s) => s.decision === "APPROVED").length;
  const ended = state === "REJECTED" || state === "CLOSED_IN_SCOPE";
  const after = (states: string[]) => states.includes(state);

  if (ended) {
    if (no === 8 && state === "REJECTED") {
      return { marker: "blocked", status: t.rejected, summary: t.rejectedSummary };
    }
    return { marker: "na", status: t.notApplicable, summary: null };
  }
  switch (no) {
    case 8:
      if (state === "IN_APPROVAL") {
        return {
          marker: "active",
          status: t.signing,
          summary: t.signedOf(signed, chain.length),
        };
      }
      if (state === "REVISION_REQUESTED") {
        return { marker: "blocked", status: t.revisionStatus, summary: t.revisionSummary };
      }
      if (after(["APPROVED", "VO_ISSUED", "IN_EXECUTION", "CLOSED"])) {
        return { marker: "done", status: t.complete, summary: t.allSigned(chain.length) };
      }
      if (state === "RECOMMENDED") {
        return { marker: "waiting", status: t.notStarted, summary: t.awaitingApprovalStart };
      }
      return { marker: "waiting", status: t.notStarted, summary: null };
    case 9:
      if (after(["VO_ISSUED", "IN_EXECUTION", "CLOSED"])) return { marker: "done", status: t.issued, summary: null };
      return { marker: "waiting", status: t.notStarted, summary: state === "APPROVED" ? t.readyForVo : null };
    case 10:
      if (after(["VO_ISSUED", "IN_EXECUTION", "CLOSED"])) return { marker: "done", status: t.done, summary: null };
      return { marker: "waiting", status: t.notStarted, summary: null };
    default:
      if (state === "CLOSED") return { marker: "done", status: t.closed, summary: null };
      if (state === "IN_EXECUTION") return { marker: "active", status: t.inExecution, summary: null };
      return { marker: "waiting", status: t.notStarted, summary: null };
  }
}

/** Stage 5 is code and returns no summary; compose one from its numbers. */
function composedSummary(result: StageResult): string | null {
  if (result.stage !== "COST_SCHEDULE_IMPACT") return null;
  const p = result.payload ?? {};
  const cost = typeof p.cost_impact === "string" ? p.cost_impact : null;
  const days = typeof p.time_impact_days === "number" ? p.time_impact_days : null;
  return getDict().case.impactSummary(formatImpact(cost), formatDays(days));
}

export function buildRows(
  stages: StageResult[],
  request: ChangeRequest,
  chain: ApprovalStep[],
): Row[] {
  const t = getDict().case;
  const english = getLang() === "en";
  const latest = new Map<string, StageResult>();
  for (const s of stages) latest.set(s.stage, s);

  return STAGES.map(({ stage, no, name, actor }) => {
    const result = latest.get(stage) ?? null;
    if (result) {
      return {
        no,
        name,
        actor: result.actor_type,
        ...fromResult(result),
        summary: english
          ? result.summary_en || composedSummary(result) || result.summary_ar || null
          : result.summary_ar || composedSummary(result) || result.summary_en || null,
        arabicOnly:
          english && !result.summary_en && !composedSummary(result) && Boolean(result.summary_ar),
        result,
      };
    }
    if (no >= 8) return { no, name, actor, ...humanStage(no, request, chain), result: null };
    const ended = request.state === "CLOSED_IN_SCOPE" || request.state === "AWAITING_DOCUMENTS";
    return {
      no,
      name,
      actor,
      marker: ended && stages.length > 0 ? "na" : "waiting",
      status: ended && stages.length > 0 ? t.notApplicable : t.notStarted,
      summary: null,
      result: null,
    };
  });
}

/**
 * The 11-stage trace (FR-15). While analysis runs, stages 1 to 7 wait under a
 * moving rule. When the response lands, `revealed` counts up and each stage
 * settles in order: the one orchestrated motion moment on the page.
 */
export function Trace({
  rows,
  running,
  revealed,
  totalMs,
}: {
  rows: Row[];
  running: boolean;
  revealed: number;
  totalMs: number | null;
}) {
  const reduce = useReducedMotion();
  const t = useT();
  return (
    <div>
      <div className="mb-3 flex items-baseline justify-between gap-3">
        <h2 className="text-lg font-semibold">{t.case.traceHeading}</h2>
        <span className="text-xs text-ink-muted" aria-live="polite">
          {running
            ? t.case.agentAnalysingNow
            : totalMs !== null
              ? t.case.analysisTime(formatDuration(totalMs))
              : null}
        </span>
      </div>
      <ActorKey />
      <ol className="relative mt-3">
        {/* The spine that joins the markers. */}
        <span aria-hidden className="absolute inset-y-4 start-[0.6875rem] w-px bg-rule-strong" />
        {rows.map((row, i) => {
          const hidden = row.no <= 7 && (running || i >= revealed);
          const pending = hidden && running;
          return (
            <TraceRow
              key={row.no}
              row={hidden ? { ...row, marker: pending && i === 0 ? "active" : "waiting", status: pending ? t.case.queued : row.status, summary: null, result: null } : row}
              running={pending && i === 0}
              reduce={Boolean(reduce)}
              justRevealed={!hidden && i === revealed - 1 && row.no <= 7}
            />
          );
        })}
      </ol>
    </div>
  );
}

function ActorKey() {
  const t = useT();
  return (
    <p className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-ink-muted">
      {(["CODE", "AI", "HUMAN"] as const).map((a) => (
        <span key={a} className="inline-flex items-center gap-1.5">
          <ActorGlyph actor={a} className="size-5" />
          {a === "CODE" ? t.case.actorCode : a === "AI" ? t.case.actorAi : t.case.actorHuman}
        </span>
      ))}
    </p>
  );
}

function MarkerDot({ marker }: { marker: Marker }) {
  return (
    <span
      aria-hidden
      className={cn(
        "relative z-10 mt-1 inline-flex size-[1.375rem] shrink-0 items-center justify-center rounded-full border-2 bg-paper",
        marker === "done" && "border-ink bg-ink",
        marker === "active" && "border-ink",
        marker === "waiting" && "border-rule-strong",
        marker === "blocked" && "border-legal bg-legal",
        marker === "held" && "border-amber bg-amber",
        marker === "na" && "border-dashed border-rule-strong",
      )}
    >
      {marker === "active" && <span className="size-2.5 rounded-full bg-ink" />}
    </span>
  );
}

function TraceRow({
  row,
  running,
  reduce,
  justRevealed,
}: {
  row: Row;
  running: boolean;
  reduce: boolean;
  justRevealed: boolean;
}) {
  const { lang, t } = usePrefs();
  const [open, setOpen] = useState(false);
  const detail = row.result;
  const panelId = `stage-${row.no}-detail`;
  const muted = row.marker === "waiting" || row.marker === "na";

  return (
    <li className="relative flex gap-3 pb-1">
      <MarkerDot marker={row.marker} />
      <div className={cn("min-w-0 flex-1 border-b border-rule pb-3", row.no === 7 && "border-b-ink")}>
        <div className="flex flex-wrap items-center gap-x-2 gap-y-1 pt-0.5">
          <span className="w-5 text-sm font-semibold tabular-nums">{row.no}</span>
          <span className={cn("text-sm font-medium", muted && "text-ink-muted")}>{row.name}</span>
          <ActorGlyph actor={row.actor} className="size-5" />
          <span
            className={cn(
              "text-xs",
              row.marker === "blocked"
                ? "font-medium text-legal"
                : row.marker === "held"
                  ? "font-medium text-amber"
                  : "text-ink-muted",
            )}
          >
            {row.status}
          </span>
          {detail && (
            <span className="text-xs text-ink-muted">{formatDuration(detail.duration_ms)}</span>
          )}
          {detail?.recorded && <Badge variant="muted">{t.case.recordedReply}</Badge>}
          {detail && (
            <button
              type="button"
              aria-expanded={open}
              aria-controls={panelId}
              onClick={() => setOpen((o) => !o)}
              className="ms-auto inline-flex items-center gap-1 rounded-[var(--radius-ctl)] px-1 text-xs text-ink-muted hover:text-ink"
            >
              {open ? t.case.hideDetails : t.case.details}
              <ChevronDown aria-hidden className={cn("size-3.5 transition-transform", open && "rotate-180")} />
            </button>
          )}
        </div>

        {running && (
          <span aria-hidden className="mt-2 block h-0.5 w-full overflow-hidden bg-rule">
            <motion.span
              className="block h-full w-1/3 bg-ink"
              initial={{ x: lang === "en" ? "-100%" : "100%" }}
              animate={
                reduce ? { x: "0%" } : { x: lang === "en" ? ["-100%", "300%"] : ["100%", "-300%"] }
              }
              transition={reduce ? { duration: 0 } : { duration: 1.4, repeat: Infinity, ease: "easeInOut" }}
            />
          </span>
        )}

        {row.summary && (
          <motion.div
            initial={justRevealed && !reduce ? { opacity: 0, y: 4 } : false}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.22 }}
            className={cn("mt-1 text-sm", muted && "text-ink-muted")}
          >
            {row.arabicOnly ? (
              <ArabicOriginal as="p" showLabel={false}>
                {row.summary}
              </ArabicOriginal>
            ) : (
              <p>{row.summary}</p>
            )}
          </motion.div>
        )}

        <AnimatePresence initial={false}>
          {open && detail && (
            <motion.div
              id={panelId}
              initial={reduce ? false : { height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={reduce ? { opacity: 0 } : { height: 0, opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="overflow-hidden"
            >
              <StageDetail result={detail} />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </li>
  );
}

function labelFor(path: string, t: ReturnType<typeof getDict>["case"]): string {
  const parts = path.split(".");
  const last = parts[parts.length - 1];
  const prefix =
    parts[0] === "risk"
      ? t.prefixRisk
      : parts[0] === "policy"
        ? t.prefixPolicy
        : parts[0] === "legal"
          ? t.prefixLegal
          : parts[0] === "narrative"
            ? t.prefixNarrative
            : "";
  return prefix + (t.keyLabel[last] ?? last);
}

function StageDetail({ result }: { result: StageResult }) {
  const t = useT().case;
  const entries = payloadEntries(result.payload).filter(
    (e) => !["chain", "narrative_provider"].some((k) => e.key.startsWith(k)),
  );
  return (
    <div className="mt-3 border-s-2 border-rule-strong ps-3 text-sm">
      <dl className="grid grid-cols-1 gap-x-4 gap-y-2 sm:grid-cols-[minmax(8rem,auto)_1fr]">
        <dt className="text-xs text-ink-muted">{t.executor}</dt>
        <dd>
          {result.actor_type === "AI" ? t.ai : result.actor_type === "CODE" ? t.code : t.human}
          {result.provider ? <span className="ref ms-2 text-xs text-ink-muted">{result.provider}</span> : null}
        </dd>
        <dt className="text-xs text-ink-muted">{t.startedEnded}</dt>
        <dd className="text-xs">
          {formatDateTime(result.started_at)}
          {t.listSep}
          {formatDuration(result.duration_ms)}
        </dd>
        {entries.map((e) => (
          <div key={e.key} className="contents">
            <dt className="text-xs text-ink-muted">{labelFor(e.key, t)}</dt>
            <dd
              dir="auto"
              className={cn("break-words whitespace-pre-line text-start", /_en$/.test(e.key) && "[direction:ltr]")}
            >
              {e.value === "true" ? t.yes : e.value === "false" ? t.no : e.value}
            </dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
