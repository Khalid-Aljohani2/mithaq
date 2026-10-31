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
    <Tag lang="ar" dir="rtl" className={cn("text-start", className)}>
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
