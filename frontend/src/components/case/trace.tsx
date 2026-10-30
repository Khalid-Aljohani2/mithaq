"use client";

import { ChevronDown } from "lucide-react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { useState } from "react";

import { ActorGlyph } from "@/components/glyphs";
import { Badge } from "@/components/ui/badge";
import type { ActorType, ApprovalStep, ChangeRequest, StageResult } from "@/lib/api";
import { formatDateTime, formatDays, formatDuration, formatImpact } from "@/lib/format";
import { STAGES } from "@/lib/labels";
import { payloadEntries } from "@/lib/payload";
import { cn } from "@/lib/utils";

type Marker = "done" | "active" | "waiting" | "blocked" | "na";

type Row = {
  no: number;
  name: string;
  actor: ActorType;
  marker: Marker;
  status: string;
  summary: string | null;
  result: StageResult | null;
};

function fromResult(result: StageResult): Pick<Row, "marker" | "status"> {
  if (result.status === "BLOCKED") return { marker: "blocked", status: "محجوب" };
  if (result.status === "OK") return { marker: "done", status: "تم" };
  return { marker: "done", status: result.status };
}

/** Stages 8 to 11 from the workflow state, when the trace has no record of them. */
function humanStage(
  no: number,
  request: ChangeRequest,
  chain: ApprovalStep[],
): Pick<Row, "marker" | "status" | "summary"> {
  const state = request.state ?? "RECEIVED";
  const signed = chain.filter((s) => s.decision === "APPROVED").length;
  const ended = state === "REJECTED" || state === "CLOSED_IN_SCOPE";
  const after = (states: string[]) => states.includes(state);

  if (ended) {
    if (no === 8 && state === "REJECTED") {
      return { marker: "blocked", status: "رُفض", summary: "رفض أحد المعتمدين الطلب، وأُبلغ مقدمه." };
    }
    return { marker: "na", status: "لا ينطبق", summary: null };
  }
  switch (no) {
    case 8:
      if (state === "IN_APPROVAL") {
        return {
          marker: "active",
          status: "قيد التوقيع",
          summary: `وقّع ${signed} من ${chain.length} في سلسلة الاعتماد.`,
        };
      }
      if (state === "REVISION_REQUESTED") {
        return { marker: "blocked", status: "طُلب تعديل", summary: "أُعيد الطلب إلى مقدمه للتعديل." };
      }
      if (after(["APPROVED", "VO_ISSUED", "IN_EXECUTION", "CLOSED"])) {
        return { marker: "done", status: "اكتمل", summary: `وقّع جميع المعتمدين (${chain.length}).` };
      }
      if (state === "RECOMMENDED") {
        return { marker: "waiting", status: "لم يبدأ", summary: "ينتظر بدء مسار الاعتماد." };
      }
      return { marker: "waiting", status: "لم يبدأ", summary: null };
    case 9:
      if (after(["VO_ISSUED", "IN_EXECUTION", "CLOSED"])) return { marker: "done", status: "صدر", summary: null };
      return { marker: "waiting", status: "لم يبدأ", summary: state === "APPROVED" ? "جاهز لإصدار أمر التغيير." : null };
    case 10:
      if (after(["VO_ISSUED", "IN_EXECUTION", "CLOSED"])) return { marker: "done", status: "تم", summary: null };
      return { marker: "waiting", status: "لم يبدأ", summary: null };
    default:
      if (state === "CLOSED") return { marker: "done", status: "أُغلق", summary: null };
      if (state === "IN_EXECUTION") return { marker: "active", status: "قيد التنفيذ", summary: null };
      return { marker: "waiting", status: "لم يبدأ", summary: null };
  }
}

/** Stage 5 is code and returns no Arabic summary; compose one from its numbers. */
function arabicSummary(result: StageResult): string | null {
  if (result.stage !== "COST_SCHEDULE_IMPACT") return null;
  const p = result.payload ?? {};
  const cost = typeof p.cost_impact === "string" ? p.cost_impact : null;
  const days = typeof p.time_impact_days === "number" ? p.time_impact_days : null;
  return `أثر التكلفة ${formatImpact(cost)}، وأثر المدة ${formatDays(days)}.`;
}

export function buildRows(
  stages: StageResult[],
  request: ChangeRequest,
  chain: ApprovalStep[],
): Row[] {
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
        summary: result.summary_ar || arabicSummary(result) || result.summary_en || null,
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
      status: ended && stages.length > 0 ? "لا ينطبق" : "لم يبدأ",
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
  return (
    <div>
      <div className="mb-3 flex items-baseline justify-between gap-3">
        <h2 className="text-lg font-semibold">مسار الطلب</h2>
        <span className="text-xs text-ink-muted" aria-live="polite">
          {running
            ? "يحلل الوكيل الطلب الآن"
            : totalMs !== null
              ? `زمن التحليل ${formatDuration(totalMs)}`
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
              row={hidden ? { ...row, marker: pending && i === 0 ? "active" : "waiting", status: pending ? "قيد الانتظار" : row.status, summary: null, result: null } : row}
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
  return (
    <p className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-ink-muted">
      {(["CODE", "AI", "HUMAN"] as const).map((a) => (
        <span key={a} className="inline-flex items-center gap-1.5">
          <ActorGlyph actor={a} className="size-5" />
          {a === "CODE" ? "قاعدة برمجية تحسب" : a === "AI" ? "ذكاء اصطناعي يقرأ ويصنّف" : "إنسان يقرر ويوقّع"}
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
              row.marker === "blocked" ? "font-medium text-legal" : "text-ink-muted",
            )}
          >
            {row.status}
          </span>
          {detail && (
            <span className="text-xs text-ink-muted">{formatDuration(detail.duration_ms)}</span>
          )}
          {detail?.recorded && <Badge variant="muted">رد مسجل</Badge>}
          {detail && (
            <button
              type="button"
              aria-expanded={open}
              aria-controls={panelId}
              onClick={() => setOpen((o) => !o)}
              className="ms-auto inline-flex items-center gap-1 rounded-[var(--radius-ctl)] px-1 text-xs text-ink-muted hover:text-ink"
            >
              {open ? "إخفاء التفاصيل" : "التفاصيل"}
              <ChevronDown aria-hidden className={cn("size-3.5 transition-transform", open && "rotate-180")} />
            </button>
          )}
        </div>

        {running && (
          <span aria-hidden className="mt-2 block h-0.5 w-full overflow-hidden bg-rule">
            <motion.span
              className="block h-full w-1/3 bg-ink"
              initial={{ x: "100%" }}
              animate={reduce ? { x: "0%" } : { x: ["100%", "-300%"] }}
              transition={reduce ? { duration: 0 } : { duration: 1.4, repeat: Infinity, ease: "easeInOut" }}
            />
          </span>
        )}

        {row.summary && (
          <motion.p
            initial={justRevealed && !reduce ? { opacity: 0, y: 4 } : false}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.22 }}
            className={cn("mt-1 text-sm", muted && "text-ink-muted")}
          >
            {row.summary}
          </motion.p>
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

const KEY_LABEL: Record<string, string> = {
  provider: "المزوّد",
  recorded: "رد مسجل",
  confidence: "الثقة",
  requester_name_ar: "مقدم الطلب",
  requested_change_ar: "التغيير المطلوب",
  impact_type: "نوع الأثر",
  quoted_phrase_ar: "العبارة المقتبسة",
  required: "المستندات المطلوبة",
  provided: "المستندات المقدمة",
  missing: "المستندات الناقصة",
  complete: "مكتملة",
  in_scope: "داخل النطاق",
  kind: "النوع",
  matched_line_ids: "البنود المطابقة",
  quantity_delta: "فرق الكمية",
  substitute_product_ar: "المنتج البديل",
  reasoning_ar: "التعليل",
  changes_approved_product: "يغيّر منتجًا معتمدًا",
  affected_line_ids: "البنود المتأثرة",
  restriction_conflicts_ar: "تعارض مع القيود",
  cost_impact: "أثر التكلفة",
  added_value: "قيمة المضاف",
  removed_value: "قيمة المحذوف",
  time_impact_days: "أثر المدة بالأيام",
  rate_human_entered: "سعر مُدخل يدويًا",
  unit_rate_flagged: "سعر الوحدة معلَّم",
  rate_checks: "فحص أسعار الوحدات",
  notes_en: "ملاحظات (إنجليزية)",
  findings_en: "النتائج (إنجليزية)",
  article_refs: "المواد",
  recommendation: "التوصية",
  reason_codes: "رموز الأسباب",
  conflicts: "التعارضات",
};

function labelFor(path: string): string {
  const parts = path.split(".");
  const last = parts[parts.length - 1];
  const prefix =
    parts[0] === "risk" ? "المخاطر: " : parts[0] === "policy" ? "السياسة: " : parts[0] === "legal" ? "النظام: " : parts[0] === "narrative" ? "الصياغة: " : "";
  return prefix + (KEY_LABEL[last] ?? last);
}

function StageDetail({ result }: { result: StageResult }) {
  const entries = payloadEntries(result.payload).filter(
    (e) => !["chain", "narrative_provider"].some((k) => e.key.startsWith(k)),
  );
  return (
    <div className="mt-3 border-s-2 border-rule-strong ps-3 text-sm">
      <dl className="grid grid-cols-1 gap-x-4 gap-y-2 sm:grid-cols-[minmax(8rem,auto)_1fr]">
        <dt className="text-xs text-ink-muted">المنفذ</dt>
        <dd>
          {result.actor_type === "AI" ? "ذكاء اصطناعي" : result.actor_type === "CODE" ? "قاعدة برمجية" : "إنسان"}
          {result.provider ? <span className="ref ms-2 text-xs text-ink-muted">{result.provider}</span> : null}
        </dd>
        <dt className="text-xs text-ink-muted">بدأ وانتهى</dt>
        <dd className="text-xs">
          {formatDateTime(result.started_at)}، {formatDuration(result.duration_ms)}
        </dd>
        {entries.map((e) => (
          <div key={e.key} className="contents">
            <dt className="text-xs text-ink-muted">{labelFor(e.key)}</dt>
            <dd className={cn("break-words whitespace-pre-line", /_en$/.test(e.key) && "text-start [direction:ltr]")}>
              {e.value === "true" ? "نعم" : e.value === "false" ? "لا" : e.value}
            </dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
