"use client";

import type { ReactNode } from "react";

import { useT } from "@/lib/prefs";

/**
 * What to do now, after a key action: a short line and its actions, the first
 * of them the screen's one primary. Sits at the top of the decision column.
 */
export function NextStep({
  id,
  children,
  actions,
}: {
  id: string;
  children: ReactNode;
  actions: ReactNode;
}) {
  const t = useT();
  return (
    <section
      aria-labelledby={`next-${id}`}
      data-next-step={id}
      className="border-s-4 border-seal bg-sheet px-4 py-3 print:hidden"
    >
      <h2 id={`next-${id}`} className="text-xs font-semibold text-seal">
        {t.case.nextStep}
      </h2>
      <div className="mt-1 text-sm text-pretty">{children}</div>
      <div className="mt-3 flex flex-wrap items-center gap-2">{actions}</div>
    </section>
  );
}
