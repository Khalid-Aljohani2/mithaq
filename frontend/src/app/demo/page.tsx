"use client";

import { Section } from "@/components/file";
import { ResetControls, ResetFlash } from "@/components/demo/reset-controls";
import { Button } from "@/components/ui/button";
import { startDemo, useDemo, useDemoMode, useGoToAct } from "@/lib/demo";
import { useT } from "@/lib/prefs";

/** The run of show: six acts, a Start button, and the reset controls. */
export default function DemoPage() {
  const t = useT().demo;
  const { state } = useDemo();
  const demoMode = useDemoMode();
  const go = useGoToAct();

  return (
    <div className="mx-auto max-w-4xl px-4 py-8 md:px-8">
      <h1 className="text-2xl font-semibold">{t.pageTitle}</h1>
      <p className="mt-2 max-w-prose text-ink-muted">{t.pageIntro}</p>

      <Section
        margin={t.margin}
        title={t.actsHeading}
        id="acts"
        action={
          <Button
            data-demo-start
            onClick={() => {
              if (state.active) {
                void go(state.act);
              } else {
                startDemo();
                void go(0);
              }
            }}
          >
            {state.active ? t.resume : t.start}
          </Button>
        }
      >
        <ol className="border-t border-rule">
          {t.acts.map((act, i) => (
            <li
              key={act.title}
              className="grid grid-cols-[2.5rem_1fr] gap-x-3 border-b border-rule py-3"
              aria-current={state.active && state.act === i ? "step" : undefined}
            >
              <span className="ref text-lg font-semibold text-ink-muted">{i + 1}</span>
              <span>
                <span className="block font-medium">{act.title}</span>
                <span className="block text-sm text-ink-muted">{act.line}</span>
              </span>
            </li>
          ))}
        </ol>
      </Section>

      {demoMode && (
        <Section margin={t.resetMargin} title={t.resetHeading} id="reset">
          <p className="mb-4 max-w-prose text-sm text-ink-muted">{t.resetIntro}</p>
          <div className="flex flex-wrap items-center gap-3">
            <ResetControls size="default" />
            <ResetFlash />
          </div>
        </Section>
      )}
    </div>
  );
}
