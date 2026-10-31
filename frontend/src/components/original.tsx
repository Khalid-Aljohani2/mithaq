"use client";

import type { ReactNode } from "react";

import { cn } from "@/lib/utils";
import { usePrefs } from "@/lib/prefs";

/**
 * Contract content written in Arabic (descriptions, request text, legal
 * text). It stays Arabic in both interface languages; in English it is set
 * right to left and labelled as the original Arabic.
 */
export function ArabicOriginal({
  children,
  className,
  as: Tag = "div",
  showLabel = true,
}: {
  children: ReactNode;
  className?: string;
  as?: "div" | "span" | "p";
  showLabel?: boolean;
}) {
  const { lang, t } = usePrefs();
  if (lang === "ar") {
    return <Tag className={className}>{children}</Tag>;
  }
  return (
    <Tag
      lang="ar"
      dir="rtl"
      // A labelled passage reads as an Arabic block. A short inline value (a
      // name, a unit, an item) sits on the English column's left edge: `left`,
      // not `start`, which under dir=rtl would push it to the right.
      className={cn(
        showLabel ? "text-start" : Tag === "span" ? "text-left" : "[text-align:match-parent]",
        className,
      )}
    >
      {showLabel && (
        <span
          lang="en"
          dir="ltr"
          className="mb-1 block text-2xs font-medium text-ink-muted"
        >
          {t.shell.originalArabic}
        </span>
      )}
      {children}
    </Tag>
  );
}

/**
 * A document name from the backend. Known names read in the interface
 * language; any other name is Arabic data and is shown as the original.
 */
export function DocumentName({ name, className }: { name: string; className?: string }) {
  const { lang, t } = usePrefs();
  const english = lang === "en" ? t.common.documentName[name] : undefined;
  if (english) {
    return (
      <span className={className} title={name}>
        {english}
      </span>
    );
  }
  return (
    <ArabicOriginal as="span" showLabel={false} className={className}>
      {name}
    </ArabicOriginal>
  );
}
