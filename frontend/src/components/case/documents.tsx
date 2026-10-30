"use client";

import { Check, X } from "lucide-react";
import { useId, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { api, type ChangeRequest, type ChangeRequestResponse } from "@/lib/api";
import { errorMessage } from "@/lib/labels";
import type { Documents } from "@/lib/payload";
import type { Persona } from "@/lib/session";
import { useResource } from "@/lib/use-resource";
import { cn } from "@/lib/utils";

const IMPACT_LABEL: Record<string, string> = {
  COST: "أثر على التكلفة",
  TIME: "أثر على المدة",
  BOTH: "أثر على التكلفة والمدة",
  NONE: "بلا أثر مالي أو زمني",
};

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
      setError(`لم تُرسل المستندات. ${errorMessage(e)}`);
      setBusy(false);
    }
  }

  return (
    <section aria-labelledby="awaiting" className="border-t-2 border-amber pt-4">
      <h2 id="awaiting" className="font-doc text-xl font-semibold text-amber">المستندات غير مكتملة</h2>
      <p className="mt-2 text-sm">
        أُرسلت إلى مقدم الطلب قائمة بالنواقص، وتوقف التحليل عند المرحلة الثانية حتى
        تُستكمل.
      </p>

      <h3 className="mt-4 text-xs font-medium text-ink-muted">
        المستندات المطلوبة{impact ? ` لطلب ${IMPACT_LABEL[impact] ?? impact}` : ""}
      </h3>
      {checklists.status === "error" && !documents ? (
        <p className="mt-1 text-sm text-legal">تعذر تحميل القائمة. {errorMessage(checklists.error)}</p>
      ) : (
        <ul className="mt-1 divide-y divide-rule border-y border-rule text-sm">
          {required.map((d) => {
            const has = onFile.includes(d);
            return (
              <li key={d} className={cn("flex items-center gap-2 py-2", !has && "text-amber")}>
                {has ? <Check aria-hidden className="size-4 text-seal" /> : <X aria-hidden className="size-4" />}
                <span className="flex-1">{d}</span>
                <span className="text-xs">{has ? "مرفق" : "ناقص"}</span>
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
          <legend className="text-base font-semibold">إعادة التقديم بالمستندات</legend>
          <p className="mt-1 text-xs text-ink-muted">
            حدّد كل ما أصبح مرفقًا. تُرسل القائمة كاملة وتحل محل السابقة، ثم يُعاد التحليل.
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
                  <span className="flex-1">{doc}</span>
                  {required.includes(doc) && !onFile.includes(doc) && (
                    <span className="text-xs text-amber">كان ناقصًا</span>
                  )}
                </label>
              </li>
            ))}
          </ul>
          <div className="mt-3 flex gap-2">
            <label htmlFor={otherId} className="sr-only">اسم مستند آخر</label>
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
              placeholder="اسم مستند آخر"
            />
            <Button type="button" variant="outline" onClick={addOther} disabled={!other.trim()}>
              إضافة
            </Button>
          </div>
        </fieldset>

        <div className="mt-4">
          <label htmlFor={nameId} className="text-xs font-medium">مقدَّم من</label>
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
            <p id={`${nameId}-err`} className="mt-1 text-xs text-legal">اكتب اسم من يقدّم المستندات.</p>
          )}
        </div>

        {stillMissing.length > 0 && (
          <p className="mt-3 border-s-2 border-amber ps-3 text-xs">
            ما زال ناقصًا: {stillMissing.join("، ")}. سيعود الطلب إلى الانتظار إن أُرسل هكذا.
          </p>
        )}
        {error && (
          <p role="alert" className="mt-3 border-s-4 border-legal bg-legal-wash px-3 py-2 text-sm">
            {error}
          </p>
        )}
        <Button type="submit" className="mt-4" disabled={busy}>
          {busy ? "جارٍ الإرسال والتحليل" : "إرسال المستندات وإعادة التحليل"}
        </Button>
      </form>
      {documents?.gapList && (
        <p className="mt-3 font-doc text-sm whitespace-pre-line">{documents.gapList}</p>
      )}
    </section>
  );
}
