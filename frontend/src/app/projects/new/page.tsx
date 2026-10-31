"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useId, useRef, useState, type ChangeEvent, type FormEvent, type ReactNode } from "react";

import { Section } from "@/components/file";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  api,
  ApiError,
  type ContractDraft,
  type ContractType,
  type DraftContractInput,
  type DraftContractResponse,
  type FieldProblem,
} from "@/lib/api";
import { useContracts } from "@/lib/contracts";
import { lineTotal, moneyAtTotalScale, scaled, TOTAL_PLACES, unscale } from "@/lib/decimal";
import { formatMoneyExact } from "@/lib/format";
import { errorMessage } from "@/lib/labels";
import { usePrefs, useT } from "@/lib/prefs";
import { useSession } from "@/lib/session";
import { cn } from "@/lib/utils";

/** Mirrors the backend: money at most 2 places, quantity at most 4. */
const MONEY = /^\d{1,13}(\.\d{1,2})?$/;
const QUANTITY = /^\d{1,10}(\.\d{1,4})?$/;
const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/;
const MAX_PDF_BYTES = 10 * 1024 * 1024;

type TextField =
  | "title_ar"
  | "entity_name"
  | "contractor_name"
  | "original_value"
  | "start_date"
  | "end_date";
type HeaderField = TextField | "contract_type";
type LineField =
  | "description_ar"
  | "unit_ar"
  | "quantity"
  | "unit_rate"
  | "approved_product_ar"
  | "restrictions_ar";

type Header = Record<TextField, string> & { contract_type: ContractType };
type Line = { key: number; values: Record<LineField, string>; ai: LineField[] };

const SECTION_FIELDS = {
  parties: ["title_ar", "entity_name", "contractor_name", "contract_type"],
  value: ["original_value", "start_date", "end_date"],
} as const satisfies Record<string, readonly HeaderField[]>;

const LINE_FIELDS: readonly LineField[] = [
  "description_ar",
  "unit_ar",
  "quantity",
  "unit_rate",
  "approved_product_ar",
  "restrictions_ar",
];

let lineKey = 0;
function newLine(values: Partial<Record<LineField, string>> = {}, ai: LineField[] = []): Line {
  lineKey += 1;
  return {
    key: lineKey,
    values: {
      description_ar: "",
      unit_ar: "",
      quantity: "",
      unit_rate: "",
      approved_product_ar: "",
      restrictions_ar: "",
      ...values,
    },
    ai,
  };
}

const EMPTY_HEADER: Header = {
  title_ar: "",
  entity_name: "",
  contractor_name: "",
  contract_type: "GOVERNMENT",
  original_value: "",
  start_date: "",
  end_date: "",
};

/** Strip grouping a person (or a draft) may type into a number. */
function cleanNumber(value: string): string {
  return value.replace(/[,\s٬]/g, "");
}

function draftText(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value.trim() : null;
}

function readPdf(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const result = typeof reader.result === "string" ? reader.result : "";
      const comma = result.indexOf(",");
      if (comma < 0) reject(new Error("unreadable"));
      else resolve(result.slice(comma + 1));
    };
    reader.onerror = () => reject(reader.error ?? new Error("unreadable"));
    reader.readAsDataURL(file);
  });
}

export default function NewProjectPage() {
  return (
    <div className="mx-auto max-w-[90rem] px-4 pb-16 md:px-8">
      <NewProjectForm />
    </div>
  );
}

function NewProjectForm() {
  const router = useRouter();
  const contracts = useContracts();
  const { persona, setPersona } = useSession();
  const { lang } = usePrefs();
  const t = useT().project;
  const uid = useId();
  const fid = (name: string) => `${uid}-${name}`;

  const [header, setHeader] = useState<Header>(EMPTY_HEADER);
  const [createdBy, setCreatedBy] = useState("");
  // The first row has a fixed key: the module counter runs on the server and
  // again in the browser, and its ids must match for hydration.
  const [lines, setLines] = useState<Line[]>(() => [{ ...newLine(), key: 0 }]);
  const [aiFields, setAiFields] = useState<HeaderField[]>([]);
  const [touched, setTouched] = useState(false);
  const [serverProblems, setServerProblems] = useState<FieldProblem[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Upload and draft
  const [file, setFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const [fileInputKey, setFileInputKey] = useState(0);
  const [pasted, setPasted] = useState("");
  const [drafting, setDrafting] = useState(false);
  const [draftError, setDraftError] = useState<{ amber: boolean; text: string } | null>(null);
  const [draftResult, setDraftResult] = useState<{ filled: number; response: DraftContractResponse } | null>(null);
  // Seconds since the draft call started; the backend reports no finer progress.
  const [draftSeconds, setDraftSeconds] = useState(0);
  // The pasted text last sent, so leaving the field again does not redraft it.
  const lastDraftedText = useRef<string | null>(null);

  useEffect(() => {
    if (!drafting) return;
    const started = Date.now();
    const timer = window.setInterval(
      () => setDraftSeconds(Math.floor((Date.now() - started) / 1000)),
      250,
    );
    return () => window.clearInterval(timer);
  }, [drafting]);

  const canCreate =
    persona.party === "GOVERNMENT_ENTITY" &&
    (persona.role === "PROJECT_MANAGER" || persona.role === "CEO");

  // ---- Live totals, exact on scaled integers ----
  const totals = lines.map((l) => lineTotal(l.values.quantity, l.values.unit_rate));
  const grand = totals.every((v): v is bigint => v !== null)
    ? totals.reduce((sum, v) => sum + v, BigInt(0))
    : null;
  const value = MONEY.test(header.original_value) ? moneyAtTotalScale(header.original_value) : null;
  const difference = grand !== null && value !== null ? grand - value : null;

  // ---- Client checks, keyed by the API's field paths ----
  const problems: Record<string, string> = {};
  if (!header.title_ar.trim()) problems.title_ar = t.errRequired;
  if (!header.entity_name.trim()) problems.entity_name = t.errRequired;
  if (!header.contractor_name.trim()) problems.contractor_name = t.errRequired;
  if (!header.original_value) problems.original_value = t.errRequired;
  else if (!MONEY.test(header.original_value)) problems.original_value = t.errMoney;
  else if (scaled(header.original_value, 2) === BigInt(0)) problems.original_value = t.errPositive;
  if (!ISO_DATE.test(header.start_date)) problems.start_date = t.errDate;
  if (!ISO_DATE.test(header.end_date)) problems.end_date = t.errDate;
  else if (ISO_DATE.test(header.start_date) && header.end_date <= header.start_date) {
    problems.end_date = t.errEndBeforeStart;
  }
  if (!createdBy.trim()) problems.created_by = t.errRequired;
  if (!lines.length) problems.breakdown = t.errNoLines;
  lines.forEach((l, i) => {
    const p = (f: LineField) => `breakdown[${i}].${f}`;
    if (!l.values.description_ar.trim()) problems[p("description_ar")] = t.errRequired;
    if (!l.values.unit_ar.trim()) problems[p("unit_ar")] = t.errRequired;
    if (!QUANTITY.test(l.values.quantity) || scaled(l.values.quantity, 4) === BigInt(0)) {
      problems[p("quantity")] = l.values.quantity ? t.errQuantity : t.errRequired;
    }
    if (!MONEY.test(l.values.unit_rate)) {
      problems[p("unit_rate")] = l.values.unit_rate ? t.errMoney : t.errRequired;
    }
  });
  if (difference !== null && difference !== BigInt(0)) problems.breakdown = t.errSum;
  const invalid = Object.keys(problems).length > 0;

  const serverMessage = (p: FieldProblem) => (lang === "en" ? p.message_en : p.message_ar);
  function errorFor(path: string): string | null {
    if (touched && problems[path]) return problems[path];
    const server = serverProblems.find((p) => p.field === path);
    return server ? serverMessage(server) : null;
  }
  function clearServer(path: string) {
    setServerProblems((list) => (list.some((p) => p.field === path) ? list.filter((p) => p.field !== path) : list));
  }

  const colLabel: Record<LineField, string> = {
    description_ar: t.description,
    unit_ar: t.unit,
    quantity: t.quantity,
    unit_rate: t.unitRate,
    approved_product_ar: t.approvedProduct,
    restrictions_ar: t.restrictions,
  };
  const entityLabel = header.contract_type === "PRIVATE" ? t.entityPrivate : t.entityGov;
  const topLabel: Record<string, string> = {
    title_ar: t.titleAr,
    entity_name: entityLabel,
    contractor_name: t.contractor,
    contract_type: t.contractType,
    original_value: t.originalValue,
    start_date: t.startDate,
    end_date: t.endDate,
    created_by: t.createdBy,
    breakdown: t.breakdown,
  };
  function labelFor(path: string): string {
    const m = /^breakdown\[(\d+)\]\.(\w+)$/.exec(path);
    if (m) {
      const col = colLabel[m[2] as LineField] ?? m[2];
      return `${t.line(Number(m[1]) + 1)}, ${col}`;
    }
    return topLabel[path] ?? path;
  }

  const summary: { path: string; message: string }[] = [
    ...(touched ? Object.entries(problems).map(([path, message]) => ({ path, message })) : []),
    ...serverProblems
      .filter((p) => !(touched && problems[p.field]))
      .map((p) => ({ path: p.field, message: serverMessage(p) })),
  ];

  // ---- Editing ----
  function setField(field: TextField, next: string) {
    setHeader((h) => ({ ...h, [field]: next }));
    setAiFields((list) => list.filter((f) => f !== field));
    clearServer(field);
  }
  function setType(next: ContractType) {
    setHeader((h) => ({ ...h, contract_type: next }));
    setAiFields((list) => list.filter((f) => f !== "contract_type"));
    clearServer("contract_type");
  }
  function setLineField(index: number, field: LineField, next: string) {
    setLines((list) =>
      list.map((l, i) =>
        i === index
          ? { ...l, values: { ...l.values, [field]: next }, ai: l.ai.filter((f) => f !== field) }
          : l,
      ),
    );
    clearServer(`breakdown[${index}].${field}`);
    if (field === "quantity" || field === "unit_rate") clearServer("breakdown");
  }
  function removeLine(index: number) {
    setLines((list) => list.filter((_, i) => i !== index));
    // Server paths after this index no longer point at the same line.
    setServerProblems((list) => list.filter((p) => !p.field.startsWith("breakdown")));
  }
  function confirmSection(fields: readonly HeaderField[]) {
    setAiFields((list) => list.filter((f) => !fields.includes(f)));
  }
  function confirmLines() {
    setLines((list) => list.map((l) => (l.ai.length ? { ...l, ai: [] } : l)));
  }
  function confirmAll() {
    setAiFields([]);
    confirmLines();
  }

  const unconfirmed = aiFields.length + lines.reduce((n, l) => n + l.ai.length, 0);
  const isAi = (field: HeaderField) => aiFields.includes(field);
  const sectionHasAi = (fields: readonly HeaderField[]) => fields.some(isAi);
  const linesHaveAi = lines.some((l) => l.ai.length > 0);

  // ---- Draft ----
  function onFile(event: ChangeEvent<HTMLInputElement>) {
    const chosen = event.target.files?.[0] ?? null;
    setFileError(null);
    if (!chosen) {
      setFile(null);
      return;
    }
    if (chosen.type && chosen.type !== "application/pdf") {
      setFile(null);
      setFileError(t.pdfNotPdf);
      setFileInputKey((k) => k + 1);
      return;
    }
    if (chosen.size > MAX_PDF_BYTES) {
      setFile(null);
      setFileError(t.pdfTooLarge);
      setFileInputKey((k) => k + 1);
      return;
    }
    setFile(chosen);
    // Choosing a PDF starts the draft straight away.
    void onDraft({ file: chosen });
  }
  function clearFile() {
    setFile(null);
    setFileError(null);
    setFileInputKey((k) => k + 1);
  }

  function applyDraft(draft: ContractDraft): number {
    const filled: HeaderField[] = [];
    const next: Header = { ...header };
    for (const field of ["title_ar", "entity_name", "contractor_name"] as const) {
      const v = draftText(draft[field]);
      if (v) {
        next[field] = v;
        filled.push(field);
      }
    }
    if (draft.contract_type === "GOVERNMENT" || draft.contract_type === "PRIVATE") {
      next.contract_type = draft.contract_type;
      filled.push("contract_type");
    }
    const money = draftText(draft.original_value);
    if (money) {
      next.original_value = cleanNumber(money);
      filled.push("original_value");
    }
    for (const field of ["start_date", "end_date"] as const) {
      const v = draftText(draft[field]);
      if (v && ISO_DATE.test(v)) {
        next[field] = v;
        filled.push(field);
      }
    }
    let lineCount = 0;
    const drafted = (draft.breakdown ?? []).map((d) => {
      const values: Partial<Record<LineField, string>> = {};
      const ai: LineField[] = [];
      for (const field of ["description_ar", "unit_ar", "approved_product_ar"] as const) {
        const v = draftText(d[field]);
        if (v) {
          values[field] = v;
          ai.push(field);
        }
      }
      for (const field of ["quantity", "unit_rate"] as const) {
        const v = draftText(d[field]);
        if (v) {
          values[field] = cleanNumber(v);
          ai.push(field);
        }
      }
      const restrictions = (d.restrictions_ar ?? []).map((r) => r.trim()).filter(Boolean);
      if (restrictions.length) {
        values.restrictions_ar = restrictions.join("\n");
        ai.push("restrictions_ar");
      }
      lineCount += ai.length;
      return newLine(values, ai);
    });
    setHeader(next);
    setAiFields(filled);
    if (drafted.length) setLines(drafted);
    setServerProblems([]);
    return filled.length + lineCount;
  }

  /**
   * Run the AI draft. Called with the source when it is just chosen (the file
   * or text state has not updated yet), or with none from the button.
   */
  async function onDraft(source?: { file?: File; text?: string }) {
    if (drafting) return;
    const useFile = source ? (source.file ?? null) : file;
    const useText = (source ? (source.text ?? "") : pasted).trim();
    if (!useFile && !useText) {
      setDraftError({ amber: false, text: t.draftNeedsInput });
      return;
    }
    setDraftSeconds(0);
    setDrafting(true);
    setDraftError(null);
    setDraftResult(null);
    try {
      let body: DraftContractInput;
      if (useFile) {
        let pdf: string;
        try {
          pdf = await readPdf(useFile);
        } catch {
          setDraftError({ amber: false, text: t.readFailed });
          return;
        }
        body = { party: persona.party, role: persona.role, pdf_base64: pdf, filename: useFile.name };
      } else {
        lastDraftedText.current = useText;
        body = { party: persona.party, role: persona.role, text: useText };
      }
      const response = await api.draftContract(body);
      const filled = applyDraft(response.draft);
      setDraftResult({ filled, response });
      // Take the reader to the filled form.
      const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      window.requestAnimationFrame(() =>
        document
          .getElementById("project-step-1-title")
          ?.scrollIntoView({ block: "start", behavior: reduce ? "auto" : "smooth" }),
      );
    } catch (e) {
      const needsLive = e instanceof ApiError && e.code === "DRAFT_NEEDS_LIVE_PROVIDER";
      setDraftError({ amber: needsLive, text: needsLive ? errorMessage(e) : t.draftFailed(errorMessage(e)) });
    } finally {
      setDrafting(false);
    }
  }

  // ---- Create ----
  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setTouched(true);
    if (!canCreate || invalid) return;
    setSubmitting(true);
    setError(null);
    try {
      const created = await api.createContract({
        party: persona.party,
        role: persona.role,
        created_by: createdBy.trim(),
        title_ar: header.title_ar.trim(),
        entity_name: header.entity_name.trim(),
        contractor_name: header.contractor_name.trim(),
        contract_type: header.contract_type,
        original_value: header.original_value,
        start_date: header.start_date,
        end_date: header.end_date,
        breakdown: lines.map((l) => ({
          description_ar: l.values.description_ar.trim(),
          unit_ar: l.values.unit_ar.trim(),
          quantity: l.values.quantity,
          unit_rate: l.values.unit_rate,
          approved_product_ar: l.values.approved_product_ar.trim() || null,
          restrictions_ar: l.values.restrictions_ar
            .split("\n")
            .map((r) => r.trim())
            .filter(Boolean),
        })),
      });
      contracts.reload();
      router.push(`/contracts/${encodeURIComponent(created.id)}`);
    } catch (e) {
      if (e instanceof ApiError && e.problems.length) setServerProblems(e.problems);
      setError(errorMessage(e));
      setSubmitting(false);
    }
  }

  const draftMeta = draftResult?.response;
  const notes = (draftMeta ? (lang === "en" ? draftMeta.draft.notes_en : draftMeta.draft.notes_ar) : null) ?? [];

  return (
    <>
      <Section margin={<span className="text-sm font-medium text-ink">{t.margin}</span>} className="pt-8">
        <h1 className="text-2xl font-semibold">{t.title}</h1>
        <p className="mt-1 max-w-prose text-sm text-ink-muted">{t.intro}</p>
      </Section>

      {/* Upload and AI draft: secondary, above the form. */}
      <Section margin={t.uploadMargin} title={t.uploadTitle} id="project-upload">
        <p className="mb-4 max-w-prose text-sm text-ink-muted">{t.uploadHint}</p>
        <div className="grid max-w-3xl gap-4 md:grid-cols-[1fr_auto_1fr] md:items-start">
          <div>
            <label htmlFor={fid("pdf")} className="text-sm font-medium">{t.pdf}</label>
            <input
              key={fileInputKey}
              id={fid("pdf")}
              type="file"
              accept="application/pdf"
              onChange={onFile}
              aria-describedby={fileError ? `${fid("pdf")}-err` : undefined}
              className="mt-1 block w-full text-sm file:me-3 file:rounded-[var(--radius-ctl)] file:border file:border-rule-strong file:bg-sheet file:px-3 file:py-1.5 file:text-sm"
            />
            {file && (
              <p className="mt-1 flex flex-wrap items-center gap-2 text-xs text-ink-muted">
                <span>{t.pdfChosen(file.name)}</span>
                <Button type="button" variant="link" size="sm" onClick={clearFile} className="h-auto p-0 text-xs">
                  {t.clearFile}
                </Button>
              </p>
            )}
            <FieldError id={`${fid("pdf")}-err`} message={fileError} />
          </div>
          <p className="text-sm text-ink-muted md:pt-7">{t.or}</p>
          <div>
            <label htmlFor={fid("paste")} className="text-sm font-medium">{t.pasteText}</label>
            <Textarea
              id={fid("paste")}
              value={pasted}
              onChange={(e) => setPasted(e.target.value)}
              onBlur={(e) => {
                // Pasted text starts the draft when the field loses focus.
                const text = e.target.value.trim();
                if (text && !file && text !== lastDraftedText.current) void onDraft({ text });
              }}
              rows={4}
              dir="auto"
              placeholder={t.pastePlaceholder}
              className="mt-1 font-doc"
            />
          </div>
        </div>
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <Button type="button" variant="outline" onClick={() => void onDraft()} disabled={drafting} data-draft-project>
            {drafting ? t.drafting : draftResult ? t.draftAgain : t.draft}
          </Button>
          {!drafting && !draftResult && <span className="text-xs text-ink-muted">{t.draftAuto}</span>}
        </div>
        {drafting && (
          <div
            role="status"
            aria-live="polite"
            data-draft-progress
            className="mt-4 flex max-w-prose items-center gap-3 border-s-4 border-ink bg-sheet px-4 py-3"
          >
            <span aria-hidden className="size-2.5 animate-pulse rounded-full bg-ink motion-reduce:animate-none" />
            <span className="font-medium">{t.readingContract}</span>
            <span className="ms-auto tabular-nums text-ink-muted" dir="ltr">
              {t.elapsed(draftSeconds)}
            </span>
          </div>
        )}
        {draftError && (
          <p
            role="alert"
            className={cn(
              "mt-4 max-w-prose border-s-4 px-4 py-3 text-sm",
              draftError.amber ? "border-amber bg-amber-wash" : "border-legal bg-legal-wash",
            )}
          >
            {draftError.text}
          </p>
        )}
        {draftResult && (
          <div role="status" className="mt-4 max-w-prose border-s-4 border-amber bg-amber-wash px-4 py-3 text-sm">
            <p className="font-medium">{t.draftDone(draftResult.filled)}</p>
            {notes.length > 0 && (
              <>
                <p className="mt-2 text-xs font-medium">{t.draftNotes}</p>
                <ul className="mt-1 list-disc space-y-1 ps-5">
                  {notes.map((n, i) => (
                    <li key={i}>{n}</li>
                  ))}
                </ul>
              </>
            )}
            <p className="mt-2 text-xs text-ink-muted" dir="auto">
              {t.draftModel(draftResult.response.model, draftResult.response.prompt_version)}
            </p>
          </div>
        )}
      </Section>

      <form onSubmit={onSubmit} noValidate>
        <Section
          id="project-step-1"
          margin={<StepRef n={1} />}
          title={t.parties}
          action={
            sectionHasAi(SECTION_FIELDS.parties) && (
              <ConfirmButton onClick={() => confirmSection(SECTION_FIELDS.parties)} />
            )
          }
        >
          <div className="grid max-w-3xl gap-4 sm:grid-cols-2">
            <TextInput
              className="sm:col-span-2"
              id={fid("title_ar")}
              name="title_ar"
              label={t.titleAr}
              value={header.title_ar}
              onChange={(v) => setField("title_ar", v)}
              error={errorFor("title_ar")}
              ai={isAi("title_ar")}
              dir="rtl"
            />
            <fieldset className="sm:col-span-2">
              <legend className="flex items-center gap-2 text-sm font-medium">
                {t.contractType}
                {isAi("contract_type") && <AiBadge />}
              </legend>
              <div
                className={cn(
                  "mt-1 flex flex-wrap gap-4 rounded-[var(--radius-ctl)] border border-transparent px-2 py-1.5",
                  isAi("contract_type") && "border-amber bg-amber-wash/40",
                )}
              >
                {(["GOVERNMENT", "PRIVATE"] as const).map((type) => (
                  <label key={type} className="flex cursor-pointer items-center gap-2 text-sm">
                    <input
                      type="radio"
                      name="contract_type"
                      value={type}
                      checked={header.contract_type === type}
                      onChange={() => setType(type)}
                      className="size-4 accent-[var(--seal)]"
                    />
                    {type === "GOVERNMENT" ? t.government : t.private}
                  </label>
                ))}
              </div>
            </fieldset>
            <TextInput
              id={fid("entity_name")}
              name="entity_name"
              label={entityLabel}
              value={header.entity_name}
              onChange={(v) => setField("entity_name", v)}
              error={errorFor("entity_name")}
              ai={isAi("entity_name")}
              dir="auto"
            />
            <TextInput
              id={fid("contractor_name")}
              name="contractor_name"
              label={t.contractor}
              value={header.contractor_name}
              onChange={(v) => setField("contractor_name", v)}
              error={errorFor("contractor_name")}
              ai={isAi("contractor_name")}
              dir="auto"
            />
          </div>
        </Section>

        <Section
          margin={<StepRef n={2} />}
          title={t.valueAndDates}
          action={
            sectionHasAi(SECTION_FIELDS.value) && (
              <ConfirmButton onClick={() => confirmSection(SECTION_FIELDS.value)} />
            )
          }
        >
          <div className="grid max-w-3xl gap-4 sm:grid-cols-3">
            <TextInput
              id={fid("original_value")}
              name="original_value"
              label={t.originalValue}
              value={header.original_value}
              onChange={(v) => setField("original_value", cleanNumber(v))}
              error={errorFor("original_value")}
              ai={isAi("original_value")}
              dir="ltr"
              inputMode="decimal"
              unit={t.sar}
              numeric
            />
            <TextInput
              id={fid("start_date")}
              name="start_date"
              label={t.startDate}
              type="date"
              value={header.start_date}
              onChange={(v) => setField("start_date", v)}
              error={errorFor("start_date")}
              ai={isAi("start_date")}
              dir="ltr"
            />
            <TextInput
              id={fid("end_date")}
              name="end_date"
              label={t.endDate}
              type="date"
              value={header.end_date}
              onChange={(v) => setField("end_date", v)}
              error={errorFor("end_date")}
              ai={isAi("end_date")}
              dir="ltr"
            />
          </div>
        </Section>

        <Section
          margin={<StepRef n={3} />}
          title={t.breakdown}
          action={linesHaveAi && <ConfirmButton onClick={confirmLines} />}
        >
          <p className="mb-4 max-w-prose border-s-2 border-ink ps-3 text-sm">{t.breakdownHint}</p>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[64rem] border-collapse text-sm">
              <thead>
                <tr className="border-b border-rule-strong text-start text-xs text-ink-muted">
                  <th className="w-20 py-2 pe-2 text-start font-medium">#</th>
                  <th className="py-2 pe-2 text-start font-medium">{t.description}</th>
                  <th className="w-28 py-2 pe-2 text-start font-medium">{t.unit}</th>
                  <th className="w-28 py-2 pe-2 text-start font-medium">{t.quantity}</th>
                  <th className="w-32 py-2 pe-2 text-start font-medium">{t.unitRate} ({t.sar})</th>
                  <th className="w-40 py-2 pe-2 text-start font-medium">
                    {t.approvedProduct} <span className="font-normal">({t.optional})</span>
                  </th>
                  <th className="w-44 py-2 pe-2 text-start font-medium">
                    {t.restrictions} <span className="font-normal">({t.optional}, {t.restrictionsHint})</span>
                  </th>
                  <th className="w-36 py-2 pe-2 text-end font-medium">{t.lineTotal}</th>
                  <th className="w-10 py-2" />
                </tr>
              </thead>
              <tbody>
                {lines.map((line, index) => {
                  const total = totals[index];
                  return (
                    <tr key={line.key} data-line-row className="border-b border-rule align-top">
                      <td className="py-2 pe-2">
                        <span className="ref text-xs text-ink-muted">{index + 1}</span>
                        {line.ai.length > 0 && <AiBadge className="mt-1 block" />}
                      </td>
                      {LINE_FIELDS.map((field) => {
                        const path = `breakdown[${index}].${field}`;
                        const err = errorFor(path);
                        const id = fid(`${line.key}-${field}`);
                        const numeric = field === "quantity" || field === "unit_rate";
                        const common = {
                          id,
                          name: field,
                          value: line.values[field],
                          "aria-label": `${t.line(index + 1)}, ${colLabel[field]}`,
                          "aria-invalid": Boolean(err),
                          "aria-describedby": err ? `${id}-err` : undefined,
                          className: cn(
                            "h-9 text-sm",
                            numeric && "text-end tabular-nums",
                            line.ai.includes(field) && "border-amber bg-amber-wash/40",
                          ),
                        };
                        return (
                          <td key={field} className="py-2 pe-2">
                            {field === "restrictions_ar" ? (
                              <Textarea
                                {...common}
                                rows={2}
                                dir="auto"
                                className={cn(common.className, "h-auto min-h-9 py-1.5")}
                                onChange={(e) => setLineField(index, field, e.target.value)}
                              />
                            ) : (
                              <Input
                                {...common}
                                dir={numeric ? "ltr" : "auto"}
                                inputMode={numeric ? "decimal" : undefined}
                                onChange={(e) =>
                                  setLineField(index, field, numeric ? cleanNumber(e.target.value) : e.target.value)
                                }
                              />
                            )}
                            <FieldError id={`${id}-err`} message={err} />
                          </td>
                        );
                      })}
                      <td className="py-2 pe-2 pt-4 text-end tabular-nums" dir="ltr">
                        {total === null ? (
                          <span className="text-ink-muted">-</span>
                        ) : (
                          formatMoneyExact(unscale(total, TOTAL_PLACES))
                        )}
                      </td>
                      <td className="py-2">
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          onClick={() => removeLine(index)}
                          aria-label={t.removeLine(index + 1)}
                          title={t.removeLine(index + 1)}
                          data-remove-line
                        >
                          ×
                        </Button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <div className="mt-3">
            <Button type="button" variant="outline" size="sm" onClick={() => setLines((l) => [...l, newLine()])} data-add-line>
              {t.addLine}
            </Button>
          </div>

          <dl className="mt-6 grid max-w-3xl gap-4 border-t border-rule-strong pt-4 sm:grid-cols-3">
            <div>
              <dt className="text-xs text-ink-muted">{t.grandTotal}</dt>
              <dd className="mt-0.5 text-lg font-semibold tabular-nums" data-grand-total>
                {grand === null ? (
                  <span className="text-sm font-normal text-ink-muted">{t.notComputable}</span>
                ) : (
                  <span dir="ltr" className="inline-block">{formatMoneyExact(unscale(grand, TOTAL_PLACES))}</span>
                )}
              </dd>
            </div>
            <div>
              <dt className="text-xs text-ink-muted">{t.originalValue}</dt>
              <dd className="mt-0.5 text-lg font-semibold tabular-nums">
                {value === null ? (
                  <span className="text-sm font-normal text-ink-muted">-</span>
                ) : (
                  <span dir="ltr" className="inline-block">{formatMoneyExact(unscale(value, TOTAL_PLACES))}</span>
                )}
              </dd>
            </div>
            <div>
              <dt className="text-xs text-ink-muted">{t.difference}</dt>
              <dd
                className={cn(
                  "mt-0.5 text-lg font-semibold tabular-nums",
                  difference !== null && (difference === BigInt(0) ? "text-seal" : "text-legal"),
                )}
                data-difference
              >
                {difference === null ? (
                  <span className="text-sm font-normal text-ink-muted">-</span>
                ) : difference === BigInt(0) ? (
                  <span className="text-sm">{t.matches}</span>
                ) : (
                  <span dir="ltr" className="inline-block">
                    {formatMoneyExact(unscale(difference, TOTAL_PLACES), true)}
                  </span>
                )}
              </dd>
            </div>
          </dl>
          <FieldError id={fid("breakdown-err")} message={errorFor("breakdown")} />
        </Section>

        <Section margin={<StepRef n={4} />} title={t.creator}>
          <div className="max-w-sm">
            <TextInput
              id={fid("created_by")}
              name="created_by"
              label={t.createdBy}
              value={createdBy}
              onChange={(v) => {
                setCreatedBy(v);
                clearServer("created_by");
              }}
              error={errorFor("created_by")}
              ai={false}
              dir="auto"
              autoComplete="name"
            />
            <p className="mt-1 text-xs text-ink-muted">{t.createdByHint}</p>
          </div>
        </Section>

        <div className="grid grid-cols-1 gap-x-6 pt-6 md:grid-cols-[7.5rem_1fr]">
          <div />
          <div>
            {error && (
              <p role="alert" className="mb-4 max-w-prose border-s-4 border-legal bg-legal-wash px-4 py-3 text-sm">
                {t.notCreated(error)}
              </p>
            )}
            {summary.length > 0 && (
              <div role="alert" className="mb-4 max-w-prose text-sm text-legal">
                <p className="font-medium">{t.fixFields}</p>
                <ul className="mt-1 list-disc space-y-0.5 ps-5">
                  {summary.map((s) => (
                    <li key={s.path}>
                      <span className="font-medium">{labelFor(s.path)}</span>: {s.message}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {!canCreate && (
              <div className="mb-4 max-w-prose border-s-4 border-amber bg-amber-wash px-4 py-3 text-sm">
                <p>{t.cannotCreate}</p>
                <Button
                  type="button"
                  variant="link"
                  className="mt-1 h-auto p-0"
                  onClick={() => setPersona({ party: "GOVERNMENT_ENTITY", role: "PROJECT_MANAGER" })}
                  data-act-as-pm
                >
                  {t.actAsPm}
                </Button>
              </div>
            )}
            <div className="flex flex-wrap items-center gap-3">
              <Button type="submit" size="lg" disabled={submitting || !canCreate} data-create-project>
                {submitting ? t.creating : t.create}
              </Button>
              <Link href="/" className={buttonVariants({ variant: "ghost", size: "lg" })}>
                {t.cancel}
              </Link>
              {unconfirmed > 0 && (
                <span className="flex flex-wrap items-center gap-2 text-sm text-amber" data-unconfirmed>
                  <AiBadge />
                  {t.unconfirmed(unconfirmed)}
                  <Button type="button" variant="link" size="sm" className="h-auto p-0" onClick={confirmAll}>
                    {t.confirmAll}
                  </Button>
                </span>
              )}
            </div>
          </div>
        </div>
      </form>
    </>
  );
}

function StepRef({ n }: { n: number }) {
  const t = useT().project;
  return <span className="text-sm font-medium text-ink">{t.step(n)}</span>;
}

function AiBadge({ className }: { className?: string }) {
  const t = useT().project;
  return (
    <Badge variant="amber" className={cn("w-fit", className)} data-ai-draft>
      {t.aiDraft}
    </Badge>
  );
}

function ConfirmButton({ onClick }: { onClick: () => void }) {
  const t = useT().project;
  return (
    <Button type="button" variant="outline" size="sm" onClick={onClick}>
      {t.confirm}
    </Button>
  );
}

function FieldError({ id, message }: { id: string; message: string | null }) {
  if (!message) return null;
  return (
    <p id={id} className="mt-1 text-xs text-legal">
      {message}
    </p>
  );
}

function TextInput({
  id,
  name,
  label,
  value,
  onChange,
  error,
  ai,
  dir,
  type = "text",
  inputMode,
  unit,
  numeric = false,
  autoComplete,
  className,
}: {
  id: string;
  name: string;
  label: ReactNode;
  value: string;
  onChange: (v: string) => void;
  error: string | null;
  ai: boolean;
  dir: "rtl" | "ltr" | "auto";
  type?: "text" | "date";
  inputMode?: "decimal";
  unit?: string;
  numeric?: boolean;
  autoComplete?: string;
  className?: string;
}) {
  const input = (
    <Input
      id={id}
      name={name}
      type={type}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      dir={dir}
      inputMode={inputMode}
      autoComplete={autoComplete ?? "off"}
      aria-invalid={Boolean(error)}
      aria-describedby={error ? `${id}-err` : undefined}
      className={cn(
        unit ? "rounded-none" : "mt-1",
        numeric && "text-end tabular-nums",
        ai && "border-amber bg-amber-wash/40",
      )}
    />
  );
  return (
    <div className={className}>
      <label htmlFor={id} className="flex items-center gap-2 text-sm font-medium">
        {label}
        {ai && <AiBadge />}
      </label>
      {unit ? (
        <div className="mt-1 flex items-stretch">
          {input}
          <span className="flex items-center rounded-e-[var(--radius-ctl)] border border-s-0 border-rule-strong bg-paper px-3 text-sm text-ink-muted">
            {unit}
          </span>
        </div>
      ) : (
        input
      )}
      <FieldError id={`${id}-err`} message={error} />
    </div>
  );
}
