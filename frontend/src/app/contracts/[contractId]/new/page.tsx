"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useId, useState, type FormEvent } from "react";

import { Empty, ErrorState, Loading, Section, TermsKey } from "@/components/file";
import { ArabicOriginal } from "@/components/original";
import { Button, buttonVariants } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { api, type Contract, type Party } from "@/lib/api";
import { useContracts, useCurrentContract } from "@/lib/contracts";
import { errorMessage, PARTIES, partyLabel } from "@/lib/labels";
import { useT } from "@/lib/prefs";
import { useSession } from "@/lib/session";

/**
 * Document names the backend's checklist uses, as seen in the seeded data.
 * No endpoint lists the required documents per change type (API gap 5), so
 * these are offered as choices and any other name can be added. They are the
 * backend's own Arabic names, so they stay Arabic in both languages.
 */
const KNOWN_DOCUMENTS = [
  "طلب تغيير رسمي",
  "عرض سعر أو تحليل تكلفة",
  "برنامج زمني محدّث",
  "مواصفات المنتج البديل",
];

const MONEY = /^\d{1,13}(\.\d{1,2})?$/;
const DAYS = /^-?\d{1,4}$/;

export default function NewChangeRequestPage() {
  const { id, contract } = useCurrentContract();
  const contracts = useContracts();
  const t = useT().forms;

  return (
    <div className="mx-auto max-w-[90rem] px-4 pb-16 md:px-8">
      {contracts.status === "error" ? (
        <div className="pt-6">
          <ErrorState error={contracts.error} what={t.whatContract} onRetry={contracts.reload} />
        </div>
      ) : !contract ? (
        contracts.status === "loading" ? (
          <Loading label={t.loadingContract} />
        ) : (
          <div className="pt-6">
            <Empty title={t.noContract(id ?? "")}>{t.chooseThenSubmit}</Empty>
          </div>
        )
      ) : (
        <NewRequestForm contract={contract} />
      )}
    </div>
  );
}

function NewRequestForm({ contract }: { contract: Contract }) {
  const router = useRouter();
  const { persona } = useSession();
  const t = useT().forms;
  const ids = { name: useId(), party: useId(), body: useId(), amount: useId(), rate: useId(), days: useId(), other: useId() };

  const [name, setName] = useState("");
  const [party, setParty] = useState<Party>(persona.party);
  const [body, setBody] = useState("");
  const [attachments, setAttachments] = useState<string[]>([KNOWN_DOCUMENTS[0]]);
  const [other, setOther] = useState("");
  const [amount, setAmount] = useState("");
  const [rate, setRate] = useState("");
  const [days, setDays] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [touched, setTouched] = useState(false);

  const choices = [...KNOWN_DOCUMENTS, ...attachments.filter((a) => !KNOWN_DOCUMENTS.includes(a))];
  const problems = {
    name: name.trim() ? null : t.errName,
    body: body.trim().length >= 10 ? null : t.errBody,
    amount: !amount || MONEY.test(amount) ? null : t.errAmount,
    rate: !rate || MONEY.test(rate) ? null : t.errRate,
    days: !days || DAYS.test(days) ? null : t.errDays,
  };
  const invalid = Object.values(problems).some(Boolean);

  function toggle(doc: string) {
    setAttachments((list) =>
      list.includes(doc) ? list.filter((d) => d !== doc) : [...list, doc],
    );
  }

  function addOther() {
    const doc = other.trim();
    if (doc && !attachments.includes(doc)) setAttachments((l) => [...l, doc]);
    setOther("");
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setTouched(true);
    if (invalid) return;
    setSubmitting(true);
    setError(null);
    try {
      const created = await api.submitChangeRequest(contract.id, {
        requester_name: name.trim(),
        requester_party: party,
        body_ar: body.trim(),
        attachments,
        human_entered_amount: amount || null,
        human_entered_unit_rate: rate || null,
        human_entered_days: days ? Number(days) : null,
      });
      // The case file runs the analysis, so the trace plays out where it is read.
      router.push(
        `/contracts/${encodeURIComponent(contract.id)}/requests/${encodeURIComponent(
          created.request.id,
        )}?run=1`,
      );
    } catch (e) {
      setError(errorMessage(e));
      setSubmitting(false);
    }
  }

  const show = (key: keyof typeof problems) => (touched ? problems[key] : null);

  return (
    <form onSubmit={onSubmit} noValidate>
      <div className="pt-6">
        <TermsKey terms={["CR"]} />
      </div>
      <Section
        margin={
          <>
            <span className="block">{t.onContract}</span>
            <span className="ref text-sm font-medium text-ink">{contract.id}</span>
          </>
        }
      >
        <h1 className="text-2xl font-semibold">{t.title}</h1>
        <p className="mt-1 max-w-prose text-sm text-ink-muted">
          {t.intro}
        </p>
      </Section>

      <Section margin={<FormStep n={1} />} title={t.requester}>
        <div className="grid max-w-2xl gap-4 sm:grid-cols-2">
          <div>
            <label htmlFor={ids.name} className="text-sm font-medium">{t.name}</label>
            <Input
              id={ids.name}
              value={name}
              onChange={(e) => setName(e.target.value)}
              aria-invalid={Boolean(show("name"))}
              aria-describedby={show("name") ? `${ids.name}-err` : undefined}
              className="mt-1"
              autoComplete="name"
            />
            <FieldError id={`${ids.name}-err`} message={show("name")} />
          </div>
          <div>
            <label htmlFor={ids.party} className="text-sm font-medium">{t.party}</label>
            <select
              id={ids.party}
              value={party}
              onChange={(e) => setParty(e.target.value as Party)}
              className="mt-1 h-10 w-full rounded-[var(--radius-ctl)] border border-rule-strong bg-sheet px-2"
            >
              {PARTIES.map((p) => (
                <option key={p} value={p}>{partyLabel(p, contract.contract_type)}</option>
              ))}
            </select>
          </div>
        </div>
      </Section>

      <Section margin={<FormStep n={2} />} title={t.body}>
        <label htmlFor={ids.body} className="sr-only">{t.body}</label>
        <Textarea
          id={ids.body}
          value={body}
          onChange={(e) => setBody(e.target.value)}
          rows={8}
          placeholder={t.bodyPlaceholder}
          aria-invalid={Boolean(show("body"))}
          aria-describedby={show("body") ? `${ids.body}-err` : undefined}
          className="max-w-3xl font-doc text-doc"
        />
        <FieldError id={`${ids.body}-err`} message={show("body")} />
      </Section>

      <Section margin={<FormStep n={3} />} title={t.attachments}>
        <fieldset>
          <legend className="mb-3 max-w-prose text-sm text-ink-muted">
            {t.attachmentsHint}
          </legend>
          <ul className="max-w-2xl divide-y divide-rule border-y border-rule">
            {choices.map((doc) => (
              <li key={doc}>
                <label className="flex cursor-pointer items-center gap-3 py-2.5">
                  <input
                    type="checkbox"
                    checked={attachments.includes(doc)}
                    onChange={() => toggle(doc)}
                    className="size-4 accent-[var(--seal)]"
                  />
                  <ArabicOriginal as="span" showLabel={false}>
                    {doc}
                  </ArabicOriginal>
                </label>
              </li>
            ))}
          </ul>
          <div className="mt-3 flex max-w-2xl gap-2">
            <label htmlFor={ids.other} className="sr-only">{t.otherAttachment}</label>
            <Input
              id={ids.other}
              value={other}
              onChange={(e) => setOther(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  addOther();
                }
              }}
              placeholder={t.otherAttachment}
            />
            <Button type="button" variant="outline" onClick={addOther} disabled={!other.trim()}>
              {t.addAttachment}
            </Button>
          </div>
        </fieldset>
      </Section>

      <Section margin={<FormStep n={4} />} title={t.amounts}>
        <p className="mb-4 max-w-prose border-s-2 border-ink ps-3 text-sm">
          {t.amountsRule}
        </p>
        <div className="grid max-w-3xl gap-4 sm:grid-cols-3">
          <NumberField
            id={ids.amount}
            label={t.amount}
            unit={t.sar}
            value={amount}
            onChange={setAmount}
            error={show("amount")}
          />
          <NumberField
            id={ids.rate}
            label={t.rate}
            unit={t.sar}
            value={rate}
            onChange={setRate}
            error={show("rate")}
          />
          <NumberField
            id={ids.days}
            label={t.extension}
            unit={t.dayUnit}
            value={days}
            onChange={setDays}
            error={show("days")}
            integer
          />
        </div>
        <p className="mt-2 text-xs text-ink-muted">
          {t.amountsHint}
        </p>
      </Section>

      <div className="grid grid-cols-1 gap-x-6 pt-6 md:grid-cols-[7.5rem_1fr]">
        <div />
        <div>
          {error && (
            <p role="alert" className="mb-4 max-w-prose border-s-4 border-legal bg-legal-wash px-4 py-3 text-sm">
              {t.notSubmitted(error)}
            </p>
          )}
          {touched && invalid && (
            <p role="alert" className="mb-4 text-sm text-legal">
              {t.fixFields}
            </p>
          )}
          <div className="flex flex-wrap gap-3">
            <Button type="submit" size="lg" disabled={submitting}>
              {submitting ? t.submitting : t.submit}
            </Button>
            <Link
              href={`/contracts/${encodeURIComponent(contract.id)}`}
              className={buttonVariants({ variant: "ghost", size: "lg" })}
            >
              {t.cancel}
            </Link>
          </div>
        </div>
      </div>
    </form>
  );
}

function FormStep({ n }: { n: number }) {
  const t = useT().forms;
  return <span className="text-sm font-medium text-ink">{t.step(n)}</span>;
}

function FieldError({ id, message }: { id: string; message: string | null }) {
  if (!message) return null;
  return (
    <p id={id} className="mt-1 text-xs text-legal">
      {message}
    </p>
  );
}

function NumberField({
  id,
  label,
  unit,
  value,
  onChange,
  error,
  integer = false,
}: {
  id: string;
  label: string;
  unit: string;
  value: string;
  onChange: (v: string) => void;
  error: string | null;
  integer?: boolean;
}) {
  return (
    <div>
      <label htmlFor={id} className="text-sm font-medium">{label}</label>
      <div className="mt-1 flex items-stretch">
        <Input
          id={id}
          value={value}
          onChange={(e) => onChange(e.target.value.replace(/[,\s]/g, ""))}
          inputMode={integer ? "numeric" : "decimal"}
          dir="ltr"
          aria-invalid={Boolean(error)}
          aria-describedby={error ? `${id}-err` : undefined}
          className="rounded-none text-end tabular-nums"
        />
        <span className="flex items-center rounded-e-[var(--radius-ctl)] border border-s-0 border-rule-strong bg-paper px-3 text-sm text-ink-muted">
          {unit}
        </span>
      </div>
      <FieldError id={`${id}-err`} message={error} />
    </div>
  );
}
