"use client";

import { Button } from "@/components/ui/button";
import { useDemo, useDemoReset } from "@/lib/demo";
import { errorMessage } from "@/lib/labels";
import { useT } from "@/lib/prefs";

/**
 * Reset and salami preset buttons. Render only when the backend says demo
 * mode is on; the backend needs no token from the browser in that mode.
 */
export function ResetControls({ size = "sm" }: { size?: "sm" | "default" }) {
  const t = useT().demo;
  const { run, busy, error } = useDemoReset();
  return (
    <span className="inline-flex flex-wrap items-center gap-2">
      <Button
        variant="outline"
        size={size}
        disabled={busy}
        onClick={() => void run()}
        data-demo-reset
      >
        {busy ? t.working : t.reset}
      </Button>
      <Button
        variant="outline"
        size={size}
        disabled={busy}
        onClick={() => void run("salami")}
        data-demo-salami
      >
        {t.salami}
      </Button>
      {error !== null && (
        <span role="alert" className="text-xs text-legal">
          {t.resetFailed} {errorMessage(error)}
        </span>
      )}
    </span>
  );
}

/** The one-time confirmation after a reset reloaded the page. */
export function ResetFlash() {
  const t = useT().demo;
  const { state, update } = useDemo();
  if (!state.flash) return null;
  return (
    <span role="status" className="inline-flex items-center gap-2 text-xs text-seal">
      {state.flash === "salami" ? t.doneSalami : t.doneReset}
      <button
        type="button"
        className="underline underline-offset-4"
        onClick={() => update({ flash: null })}
      >
        {t.dismiss}
      </button>
    </span>
  );
}
