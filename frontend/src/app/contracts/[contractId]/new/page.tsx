"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useId, useState, type FormEvent } from "react";

import { Empty, ErrorState, Loading, Section, TermsKey } from "@/components/file";
import { Button, buttonVariants } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { api, type Contract, type Party } from "@/lib/api";
import { useContracts, useCurrentContract } from "@/lib/contracts";
import { errorMessage, PARTIES, partyLabel } from "@/lib/labels";
import { useSession } from "@/lib/session";

/**
 * Document names the backend's checklist uses, as seen in the seeded data.
 * No endpoint lists the required documents per change type (API gap 5), so
 * these are offered as choices and any other name can be added.
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

  return (
    <div className="mx-auto max-w-[90rem] px-4 pb-16 md:px-8">
      {contracts.status === "error" ? (
        <div className="pt-6">
          <ErrorState error={contracts.error} what="العقد" onRetry={contracts.reload} />
        </div>
      ) : !contract ? (
        contracts.status === "loading" ? (
          <Loading label="جارٍ تحميل العقد" />
        ) : (
          <div className="pt-6">
            <Empty title={`لا يوجد عقد بالمرجع ${id ?? ""}`}>
              اختر عقدًا من قائمة العقود أعلى الصفحة، ثم قدّم الطلب عليه.
            </Empty>
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
    name: name.trim() ? null : "اكتب اسم مقدم الطلب.",
    body: body.trim().length >= 10 ? null : "اكتب نص الطلب كما ورد، عشرة أحرف على الأقل.",
    amount: !amount || MONEY.test(amount) ? null : "اكتب المبلغ بالأرقام، وبحد أقصى منزلتين عشريتين.",
    rate: !rate || MONEY.test(rate) ? null : "اكتب سعر الوحدة بالأرقام، وبحد أقصى منزلتين عشريتين.",
    days: !days || DAYS.test(days) ? null : "اكتب عدد الأيام رقمًا صحيحًا.",
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
            <span className="block">على العقد</span>
            <span className="ref text-sm font-medium text-ink">{contract.id}</span>
          </>
        }
      >
        <h1 className="text-2xl font-semibold">طلب تغيير جديد</h1>
        <p className="mt-1 max-w-prose text-sm text-ink-muted">
          يُسجَّل الطلب بمرجع جديد، ثم يحلله الوكيل ويعرض توصيته. لا يُعتمد شيء
          إلا بتوقيع أصحاب الصلاحية.
        </p>
      </Section>

      <Section margin={<FormStep n={1} />} title="مقدم الطلب">
        <div className="grid max-w-2xl gap-4 sm:grid-cols-2">
          <div>
            <label htmlFor={ids.name} className="text-sm font-medium">الاسم</label>
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
            <label htmlFor={ids.party} className="text-sm font-medium">الطرف</label>
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

      <Section margin={<FormStep n={2} />} title="نص الطلب">
        <label htmlFor={ids.body} className="sr-only">نص الطلب</label>
        <Textarea
          id={ids.body}
          value={body}
          onChange={(e) => setBody(e.target.value)}
          rows={8}
          placeholder="الصق نص الطلب كما ورد من مقدمه."
          aria-invalid={Boolean(show("body"))}
          aria-describedby={show("body") ? `${ids.body}-err` : undefined}
          className="max-w-3xl font-doc text-doc"
        />
        <FieldError id={`${ids.body}-err`} message={show("body")} />
      </Section>

      <Section margin={<FormStep n={3} />} title="المرفقات">
        <fieldset>
          <legend className="mb-3 max-w-prose text-sm text-ink-muted">
            حدّد المستندات المرفقة فعلًا. يطابقها الوكيل بقائمة المستندات المطلوبة
            لنوع الطلب، ويعيد إليك قائمة بالنواقص إن وُجدت.
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
                  <span>{doc}</span>
                </label>
              </li>
            ))}
          </ul>
          <div className="mt-3 flex max-w-2xl gap-2">
            <label htmlFor={ids.other} className="sr-only">اسم مرفق آخر</label>
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
              placeholder="اسم مرفق آخر"
            />
            <Button type="button" variant="outline" onClick={addOther} disabled={!other.trim()}>
              إضافة المرفق
            </Button>
          </div>
        </fieldset>
      </Section>

      <Section margin={<FormStep n={4} />} title="المبالغ والمدة">
        <p className="mb-4 max-w-prose border-s-2 border-ink ps-3 text-sm">
          المبالغ يُدخلها الأشخاص دائمًا، ولا يقترحها الوكيل ولا يسعّر بها بندًا.
        </p>
        <div className="grid max-w-3xl gap-4 sm:grid-cols-3">
          <NumberField
            id={ids.amount}
            label="المبلغ المطلوب"
            unit="ر.س"
            value={amount}
            onChange={setAmount}
            error={show("amount")}
          />
          <NumberField
            id={ids.rate}
            label="سعر الوحدة المقترح"
            unit="ر.س"
            value={rate}
            onChange={setRate}
            error={show("rate")}
          />
          <NumberField
            id={ids.days}
            label="التمديد المطلوب"
            unit="يوم"
            value={days}
            onChange={setDays}
            error={show("days")}
            integer
          />
        </div>
        <p className="mt-2 text-xs text-ink-muted">
          اترك الحقل فارغًا إذا لم يذكره الطلب. تُحسب التكلفة من الكميات وأسعار
          العقد، ويُعلَّم أي سعر مُدخل يدويًا.
        </p>
      </Section>

      <div className="grid grid-cols-1 gap-x-6 pt-6 md:grid-cols-[7.5rem_1fr]">
        <div />
        <div>
          {error && (
            <p role="alert" className="mb-4 max-w-prose border-s-4 border-legal bg-legal-wash px-4 py-3 text-sm">
              لم يُقدَّم الطلب. {error}
            </p>
          )}
          {touched && invalid && (
            <p role="alert" className="mb-4 text-sm text-legal">
              صحّح الحقول المعلَّمة أعلاه ثم قدّم الطلب.
            </p>
          )}
          <div className="flex flex-wrap gap-3">
            <Button type="submit" size="lg" disabled={submitting}>
              {submitting ? "جارٍ تقديم الطلب" : "تقديم الطلب وتحليله"}
            </Button>
            <Link
              href={`/contracts/${encodeURIComponent(contract.id)}`}
              className={buttonVariants({ variant: "ghost", size: "lg" })}
            >
              إلغاء
            </Link>
          </div>
        </div>
      </div>
    </form>
  );
}

function FormStep({ n }: { n: number }) {
  return <span className="text-sm font-medium text-ink">البند {n}</span>;
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
