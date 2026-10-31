"use client";

import { Check, X } from "lucide-react";
import { useId, useState } from "react";

import { ArabicOriginal, DocumentName } from "@/components/original";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { api, type ChangeRequest, type ChangeRequestResponse } from "@/lib/api";
import { documentLabel, errorMessage } from "@/lib/labels";
import type { Documents } from "@/lib/payload";
import { useT } from "@/lib/prefs";
import type { Persona } from "@/lib/session";
import { useResource } from "@/lib/use-resource";
import { cn } from "@/lib/utils";

/**
 * FR-04: the request is waiting on paperwork. The checklist for its impact
 * type comes from the API; the requester ticks what is now attached, the list
 * is sent, and the analysis runs again from stage 1.
 */
export function AwaitingDocuments({
  request,
  documents,
  persona,
  onSupplied,
  onAnalyse,
}: {
  request: ChangeRequest;
  documents: Documents | null;
  persona: Persona;
  onSupplied: (data: ChangeRequestResponse) => void;
  onAnalyse: () => Promise<void> | void;
}) {
  const t = useT();
  const checklists = useResource((s) => api.requiredDocuments(s), []);
  const impact = request.impact_type ?? null;
  const fromApi = checklists.data?.checklists.find((c) => c.impact_type === impact)?.required;
  const required = fromApi ?? documents?.required ?? [];
  const onFile = request.attachments ?? [];
  const extras = onFile.filter((a) => !required.includes(a));

  const nameId = useId();
  const otherId = useId();
  const [chosen, setChosen] = useState<string[]>(onFile);
  const [other, setOther] = useState("");
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [touched, setTouched] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const stillMissing = required.filter((d) => !chosen.includes(d));
  const choices = [...required, ...extras, ...chosen.filter((c) => !required.includes(c) && !extras.includes(c))];

  function toggle(doc: string) {
    setChosen((l) => (l.includes(doc) ? l.filter((d) => d !== doc) : [...l, doc]));
  }
  function addOther() {
    const doc = other.trim();
    if (doc && !chosen.includes(doc)) setChosen((l) => [...l, doc]);
    setOther("");
  }

  async function submit() {
    setTouched(true);
    if (!name.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const result = await api.supplyAttachments(request.id, {
        party: persona.party,
        role: persona.role,
        submitted_by: name.trim(),
        attachments: chosen,
      });
      onSupplied(result);
      await onAnalyse();
    } catch (e) {
      setError(t.case.docsSendFailed(errorMessage(e)));
      setBusy(false);
    }
  }

  return (
    <section aria-labelledby="awaiting" className="border-t-2 border-amber pt-4">
      <h2 id="awaiting" className="font-doc text-xl font-semibold text-amber">{t.case.docsIncomplete}</h2>
      <p className="mt-2 text-sm">
        {t.case.docsIncompleteBody}
      </p>

      <h3 className="mt-4 text-xs font-medium text-ink-muted">
        {t.case.requiredDocs}
        {impact ? t.case.requiredFor(t.case.impactLabel[impact] ?? impact) : ""}
      </h3>
      {checklists.status === "error" && !documents ? (
        <p className="mt-1 text-sm text-legal">{t.case.listFailed(errorMessage(checklists.error))}</p>
      ) : (
        <ul className="mt-1 divide-y divide-rule border-y border-rule text-sm">
          {required.map((d) => {
            const has = onFile.includes(d);
            return (
              <li key={d} className={cn("flex items-center gap-2 py-2", !has && "text-amber")}>
                {has ? <Check aria-hidden className="size-4 text-seal" /> : <X aria-hidden className="size-4" />}
                <DocumentName name={d} className="flex-1" />
                <span className="text-xs">{has ? t.case.attached : t.case.missing}</span>
              </li>
            );
          })}
        </ul>
      )}

      <form
        className="mt-6 border border-rule-strong bg-sheet p-4"
        onSubmit={(e) => {
          e.preventDefault();
          void submit();
        }}
        noValidate
      >
        <fieldset>
          <legend className="text-base font-semibold">{t.case.resubmit}</legend>
          <p className="mt-1 text-xs text-ink-muted">
            {t.case.resubmitNote}
          </p>
          <ul className="mt-3 divide-y divide-rule border-y border-rule">
            {choices.map((doc) => (
              <li key={doc}>
                <label className="flex cursor-pointer items-center gap-3 py-2 text-sm">
                  <input
                    type="checkbox"
                    checked={chosen.includes(doc)}
                    onChange={() => toggle(doc)}
                    className="size-4 accent-[var(--seal)]"
                  />
                  <span dir="auto" className="flex-1 text-start">
                    {documentLabel(doc)}
                  </span>
                  {required.includes(doc) && !onFile.includes(doc) && (
                    <span className="text-xs text-amber">{t.case.wasMissing}</span>
                  )}
                </label>
              </li>
            ))}
          </ul>
          <div className="mt-3 flex gap-2">
            <label htmlFor={otherId} className="sr-only">{t.case.otherDoc}</label>
            <Input
              id={otherId}
              value={other}
              onChange={(e) => setOther(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  addOther();
                }
              }}
              placeholder={t.case.otherDoc}
            />
            <Button type="button" variant="outline" onClick={addOther} disabled={!other.trim()}>
              {t.case.add}
            </Button>
          </div>
        </fieldset>

        <div className="mt-4">
          <label htmlFor={nameId} className="text-xs font-medium">{t.case.submittedBy}</label>
          <Input
            id={nameId}
            value={name}
            onChange={(e) => setName(e.target.value)}
            aria-invalid={touched && !name.trim()}
            aria-describedby={touched && !name.trim() ? `${nameId}-err` : undefined}
            className="mt-1 font-doc"
            autoComplete="name"
          />
          {touched && !name.trim() && (
            <p id={`${nameId}-err`} className="mt-1 text-xs text-legal">{t.case.submittedByMissing}</p>
          )}
        </div>

        {stillMissing.length > 0 && (
          <p className="mt-3 border-s-2 border-amber ps-3 text-xs">
            {t.case.stillMissing(stillMissing.map(documentLabel).join(t.case.listSep))}
          </p>
        )}
        {error && (
          <p role="alert" className="mt-3 border-s-4 border-legal bg-legal-wash px-3 py-2 text-sm">
            {error}
          </p>
        )}
        <Button type="submit" className="mt-4" disabled={busy}>
          {busy ? t.case.sendingAndAnalysing : t.case.sendAndAnalyse}
        </Button>
      </form>
      {documents?.gapList && (
        <ArabicOriginal as="p" className="mt-3 font-doc text-sm whitespace-pre-line">
          {documents.gapList}
        </ArabicOriginal>
      )}
    </section>
  );
}
