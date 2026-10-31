"use client";

import Link from "next/link";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { useState } from "react";

import { Button, buttonVariants } from "@/components/ui/button";
import {
  ACT_COUNT,
  GOV_CONTRACT,
  requestHref,
  useDemo,
  useDemoMode,
  useGoToAct,
} from "@/lib/demo";
import { useT } from "@/lib/prefs";
import { useSession } from "@/lib/session";

import { ResetControls, ResetFlash } from "./reset-controls";

/**
 * The presenter's bar, under the letterhead on every page while the demo is
 * running. Next and Previous only move the pointer; Go sets the persona and
 * opens the screen, so the presenter decides when the page changes.
 */
export function GuideBar() {
  const { state, update, leave } = useDemo();
  const demoMode = useDemoMode();
  const go = useGoToAct();
  const { setPersona } = useSession();
  const t = useT().demo;
  // Set when Go found no variation order for act 4.
  const [missingVo, setMissingVo] = useState(false);
  const [notesOpen, setNotesOpen] = useState(false);

  if (!state.active) return null;
  const act = t.acts[state.act];
  const move = (to: number) => {
    setMissingVo(false);
    update({ act: to, flash: null });
  };
  const notes = [...act.notes];
  if (state.act === 3 && missingVo) notes.unshift(t.noVoYet);
  if (state.act === 4 && !state.salamiCrId) notes.unshift(t.noSalami);

  return (
    <div data-guide-bar role="region" aria-label={t.barLabel} className="border-b border-rule bg-paper">
      <div className="mx-auto flex max-w-[90rem] flex-wrap items-center gap-x-3 gap-y-2 px-4 py-2 md:px-8">
        <span className="inline-flex items-center gap-1">
          <Button
            variant="ghost"
            size="sm"
            disabled={state.act === 0}
            onClick={() => move(state.act - 1)}
            data-guide-prev
          >
            <ChevronRight aria-hidden className="rtl:block ltr:hidden" />
            <ChevronLeft aria-hidden className="ltr:block rtl:hidden" />
            {t.prev}
          </Button>
          <Button
            variant="ghost"
            size="sm"
            disabled={state.act === ACT_COUNT - 1}
            onClick={() => move(state.act + 1)}
            data-guide-next
          >
            {t.next}
            <ChevronLeft aria-hidden className="rtl:block ltr:hidden" />
            <ChevronRight aria-hidden className="ltr:block rtl:hidden" />
          </Button>
        </span>

        <p className="min-w-0 text-sm" aria-live="polite">
          <span className="ref text-ink-muted">{t.actOf(state.act + 1, ACT_COUNT)}</span>{" "}
          <span className="font-medium">{act.title}</span>
        </p>

        <span className="inline-flex flex-wrap items-center gap-2">
          <Button
            size="sm"
            onClick={() => {
              void go(state.act).then((missing) => setMissingVo(missing));
            }}
            data-guide-go
          >
            {t.go}
          </Button>
          {state.act === 4 && state.salamiCrId && (
            <Link
              href={requestHref(GOV_CONTRACT, state.salamiCrId)}
              onClick={() => setPersona({ party: "GOVERNMENT_ENTITY", role: "LEGAL_ADVISOR" })}
              className={buttonVariants({ variant: "outline", size: "sm" })}
              data-guide-eighth
            >
              {t.openEighth}
            </Link>
          )}
          <Button
            variant="outline"
            size="sm"
            aria-expanded={notesOpen}
            onClick={() => setNotesOpen((open) => !open)}
            data-guide-notes
          >
            {notesOpen ? t.hideNotes : t.notes}
          </Button>
        </span>

        <span className="ms-auto inline-flex flex-wrap items-center gap-2">
          <ResetFlash />
          {demoMode && <ResetControls />}
          <Button variant="ghost" size="sm" onClick={leave} data-guide-leave>
            {t.leave}
          </Button>
        </span>
      </div>

      {notesOpen && (
        <div data-presenter-notes className="mx-auto max-w-[90rem] px-4 pb-3 md:px-8">
          <ul className="list-disc space-y-1 border-s-2 border-rule-strong ps-8 text-sm">
            {notes.map((n) => (
              <li key={n}>{n}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
