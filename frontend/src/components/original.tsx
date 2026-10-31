"use client";

import { Children, isValidElement, type ReactNode } from "react";

import { cn } from "@/lib/utils";
import { useDocumentNames } from "@/lib/documents";
import { usePrefs } from "@/lib/prefs";

/**
 * The text of children, walking into nested elements (a blockquote around the
 * request text, say). Null when there is no text to judge by.
 */
function plainText(children: ReactNode): string | null {
  let text = "";
  const walk = (node: ReactNode) => {
    Children.forEach(node, (child) => {
      if (typeof child === "string" || typeof child === "number") text += String(child);
      else if (isValidElement<{ children?: ReactNode }>(child)) walk(child.props.children);
    });
  };
  walk(children);
  return text.trim() ? text : null;
}

/** True when most letters are Arabic script. Digits and punctuation do not count. */
export function isMainlyArabic(text: string): boolean {
  const arabic = text.match(/[؀-ۿݐ-ݿﭐ-﷿ﹰ-﻿]/g)?.length ?? 0;
  const latin = text.match(/[A-Za-zÀ-ɏ]/g)?.length ?? 0;
  return arabic > 0 && arabic >= latin;
}

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
  // Only text that is mainly Arabic is labelled and set right to left. Any
  // other free text (an English request, a Latin name) keeps its own
  // direction and no label.
  const text = plainText(children);
  if (text !== null && !isMainlyArabic(text)) {
    return (
      <Tag dir="auto" className={cn("[text-align:match-parent]", className)}>
        {children}
      </Tag>
    );
  }
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
  const catalog = useDocumentNames();
  const english = lang === "en" ? (catalog[name] ?? t.common.documentName[name]) : undefined;
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
