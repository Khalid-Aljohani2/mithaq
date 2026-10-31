"use client";

import Link from "next/link";

import { ErrorState, Field, Loading, Section } from "@/components/file";
import { ActorGlyph } from "@/components/glyphs";
import { buttonVariants } from "@/components/ui/button";
import { api } from "@/lib/api";
import { STAGES } from "@/lib/labels";
import { useContracts } from "@/lib/contracts";
import { startDemo } from "@/lib/demo";
import { useT } from "@/lib/prefs";
import { lastContract } from "@/lib/session";
import { useResource } from "@/lib/use-resource";

/** The front page: what this is, who decides what, the measured result, and two ways in. */
export default function Home() {
  const t = useT().home;
  const contracts = useContracts();
  const summary = useResource((signal) => api.evalSummary(signal), []);

  const remembered = lastContract();
  const target =
    contracts.data?.find((c) => c.id === remembered) ?? contracts.data?.[0] ?? null;

  const rec = summary.data?.fields.find((f) => f.field === "recommendation");

  return (
    <div className="mx-auto max-w-5xl px-4 py-8 md:px-8">
      <h1 className="text-2xl font-semibold">
        <span dir="ltr" className="inline-block">
          Mithaq<span className="font-normal text-ink-muted">Ai</span>
        </span>
      </h1>
      <p className="mt-1 font-naskh text-xl text-balance">{t.tagline}</p>

      <Section margin={t.whatMargin}>
        <p className="max-w-prose leading-relaxed text-pretty">{t.what}</p>
      </Section>

      <Section margin={t.principleMargin} title={t.principleHeading} id="principle">
        <ol className="grid gap-4 md:grid-cols-3">
          {t.principle.map((p, i) => (
            <li key={p.label} className="border-s-2 border-rule-strong ps-3">
              <span className="ref text-xs text-ink-muted">{i + 1}</span>
              <p className="font-semibold">{p.label}</p>
              <p className="mt-1 text-sm text-ink-muted">{p.body}</p>
            </li>
          ))}
        </ol>
        <p className="mt-5 text-xs text-ink-muted">{t.stagesCaption}</p>
        <ol className="mt-2 grid grid-cols-2 border-s border-t border-rule-strong sm:grid-cols-3 lg:grid-cols-4" data-testid="home-stages">
          {STAGES.map((s) => (
            <li key={s.stage} className="flex items-center gap-2 border-e border-b border-rule px-2 py-1.5">
              <span className="w-5 shrink-0 text-end text-xs font-semibold tabular-nums">{s.no}</span>
              <ActorGlyph actor={s.actor} className="size-5" />
              <span className="min-w-0 text-xs leading-tight text-ink-muted">{s.name}</span>
            </li>
          ))}
        </ol>
      </Section>

      <Section
        margin={t.evalMargin}
        title={t.evalHeading}
        id="eval"
        action={
          <Link href="/evaluation" className={buttonVariants({ variant: "link" })}>
            {t.evalLink}
          </Link>
        }
      >
        {summary.status === "loading" ? (
          <Loading label={t.evalHeading} rows={2} />
        ) : summary.status === "error" ? (
          <ErrorState error={summary.error} what={t.evalWhat} onRetry={summary.reload} />
        ) : !summary.data.available ? (
          <p className="text-sm text-ink-muted">{t.notMeasured}</p>
        ) : (
          <dl className="grid gap-4 sm:grid-cols-2">
            <Field label={t.recAccuracy}>
              <span className="ref text-3xl font-semibold" dir="ltr">
                {rec?.accuracy_pct ?? summary.data.overall_accuracy_pct}%
              </span>
              <span className="mt-1 block text-xs font-normal text-ink-muted">
                {t.onSplit(summary.data.case_count)}
              </span>
            </Field>
            {summary.data.injection_total > 0 && (
              <Field label={t.injection}>
                <span className="ref text-xl" dir="ltr">
                  {summary.data.injection_passed}/{summary.data.injection_total}
                </span>
              </Field>
            )}
          </dl>
        )}
      </Section>

      <Section margin={t.entriesMargin}>
        <div className="flex flex-wrap items-center gap-3">
          <Link
            href="/demo"
            onClick={startDemo}
            className={buttonVariants({ size: "lg" })}
            data-home-demo
          >
            {t.startDemo}
          </Link>
          {target ? (
            <Link
              href={`/contracts/${encodeURIComponent(target.id)}`}
              className={buttonVariants({ variant: "outline", size: "lg" })}
            >
              {t.openContract}
            </Link>
          ) : contracts.status === "ready" ? (
            <span className="text-sm text-ink-muted">{t.noContracts}</span>
          ) : null}
        </div>
      </Section>
    </div>
  );
}
