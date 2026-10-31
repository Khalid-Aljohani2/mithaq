"use client";

/**
 * The building blocks of the contract-file look: a section with its margin
 * reference, the terms key, and the three view states.
 */

import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

import { Button } from "@/components/ui/button";
import { errorMessage, TERMS, type Term, type Tone } from "@/lib/labels";
import { useT } from "@/lib/prefs";

/** A ruled section. `margin` is its citation, set in the start-side column. */
export function Section({
  margin,
  title,
  action,
  children,
  className,
  id,
}: {
  margin?: ReactNode;
  title?: ReactNode;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
  id?: string;
}) {
  const headingId = id ? `${id}-title` : undefined;
  return (
    <section
      aria-labelledby={title ? headingId : undefined}
      className={cn(
        "grid grid-cols-1 gap-x-6 border-b border-rule py-6 md:grid-cols-[7.5rem_1fr]",
        className,
      )}
    >
      <div className="margin-ref mb-2 md:mb-0 md:pt-1">{margin}</div>
      <div className="min-w-0">
        {(title || action) && (
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            {title && (
              <h2 id={headingId} className="text-lg font-semibold">
                {title}
              </h2>
            )}
            {action}
          </div>
        )}
        {children}
      </div>
    </section>
  );
}

/** The once-per-screen key for every abbreviation the screen uses. */
export function TermsKey({ terms }: { terms: readonly Term[] }) {
  const t = useT().common;
  if (!terms.length) return null;
  return (
    <p className="text-xs text-ink-muted">
      <span className="font-medium text-ink">{t.termsLabel}</span>
      {terms.map((term, i) => (
        <span key={term}>
          <span className="ref font-medium text-ink">{term}</span> ({TERMS[term]})
          {i < terms.length - 1 ? t.listSep : "."}
        </span>
      ))}
    </p>
  );
}

const TONE_TEXT: Record<Tone, string> = {
  neutral: "text-ink",
  seal: "text-seal",
  amber: "text-amber",
  legal: "text-legal",
};
export function toneText(tone: Tone): string {
  return TONE_TEXT[tone];
}

/** Ruled skeleton rows: the shape of what is loading, without a spinner. */
export function Loading({ label, rows = 4 }: { label: string; rows?: number }) {
  return (
    <div role="status" aria-live="polite" className="py-2">
      <span className="sr-only">{label}</span>
      {Array.from({ length: rows }, (_, i) => (
        <div
          key={i}
          aria-hidden
          className="flex items-center gap-4 border-b border-rule py-3"
        >
          <div className="h-3 w-16 animate-pulse bg-rule" />
          <div
            className="h-3 animate-pulse bg-rule"
            style={{ inlineSize: `${60 - i * 9}%` }}
          />
        </div>
      ))}
      <p aria-hidden className="pt-3 text-xs text-ink-muted">
        {label}
      </p>
    </div>
  );
}

export function Empty({
  title,
  children,
  action,
}: {
  title: string;
  children?: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className="border border-dashed border-rule-strong px-6 py-8">
      <p className="font-medium">{title}</p>
      {children && <div className="mt-1 text-sm text-ink-muted">{children}</div>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

export function ErrorState({
  error,
  what,
  onRetry,
}: {
  error: unknown;
  what: string;
  onRetry?: () => void;
}) {
  const t = useT().common;
  return (
    <div
      role="alert"
      className="border-s-4 border-legal bg-legal-wash px-4 py-4 text-ink"
    >
      <p className="font-medium text-legal">{t.couldNotLoad(what)}</p>
      <p className="mt-1 text-sm">{errorMessage(error)}</p>
      {onRetry && (
        <Button variant="outline" size="sm" className="mt-3" onClick={onRetry}>
          {t.retry}
        </Button>
      )}
    </div>
  );
}

/** A labelled value: label above, value below. Replaces "a · b · c" strings. */
export function Field({
  label,
  children,
  className,
}: {
  label: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("min-w-0", className)}>
      <dt className="text-xs text-ink-muted">{label}</dt>
      <dd className="mt-0.5 font-medium">{children}</dd>
    </div>
  );
}
