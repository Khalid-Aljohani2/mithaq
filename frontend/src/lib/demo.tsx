"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState, useSyncExternalStore } from "react";

import { api, ApiError } from "./api";
import { useSession, type Persona } from "./session";

/**
 * The guided demo: whether it is running and which act. Presenter notes
 * are deliberately not stored: they start closed on every load, so they
 * never reach the camera unless opened in this take. Kept as JSON in localStorage so a full reload
 * (after a reset) lands back on the same act. Storage is optional.
 */

export type DemoState = {
  active: boolean;
  act: number;
  /** The salami preset's eighth request, from the last preset reset. */
  salamiCrId: string | null;
  /** A confirmation to show once after a reset reloads the page. */
  flash: "reset" | "salami" | null;
};

const KEY = "mithaqai.demo";
export const ACT_COUNT = 6;
const DEFAULT: DemoState = {
  active: false,
  act: 0,
  salamiCrId: null,
  flash: null,
};

function parse(raw: string | null): DemoState {
  if (!raw) return DEFAULT;
  try {
    const p: unknown = JSON.parse(raw);
    if (typeof p !== "object" || p === null) return DEFAULT;
    const o = p as Record<string, unknown>;
    const act = typeof o.act === "number" ? Math.trunc(o.act) : 0;
    return {
      active: o.active === true,
      act: Math.min(Math.max(act, 0), ACT_COUNT - 1),
      salamiCrId: typeof o.salamiCrId === "string" ? o.salamiCrId : null,
      flash: o.flash === "reset" || o.flash === "salami" ? o.flash : null,
    };
  } catch {
    return DEFAULT;
  }
}

const listeners = new Set<() => void>();
let cached: DemoState = DEFAULT;
let cachedRaw: string | null = null;

function readRaw(): string | null {
  try {
    return window.localStorage.getItem(KEY);
  } catch {
    return null;
  }
}

function snapshot(): DemoState {
  const raw = readRaw();
  if (raw !== cachedRaw) {
    cached = parse(raw);
    cachedRaw = raw;
  }
  return cached;
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  window.addEventListener("storage", listener);
  return () => {
    listeners.delete(listener);
    window.removeEventListener("storage", listener);
  };
}

function write(patch: Partial<DemoState>): void {
  const next = { ...snapshot(), ...patch };
  const raw = JSON.stringify(next);
  try {
    window.localStorage.setItem(KEY, raw);
  } catch {
    // Without storage the demo still runs until reload.
  }
  cached = next;
  cachedRaw = raw;
  listeners.forEach((l) => l());
}

export function startDemo(): void {
  write({ active: true, act: 0, flash: null });
}

export function leaveDemo(): void {
  write({ active: false, flash: null });
}

export function useDemo() {
  const state = useSyncExternalStore(subscribe, snapshot, () => DEFAULT);
  return {
    state,
    update: write,
    start: startDemo,
    leave: leaveDemo,
  };
}

/** Whether the backend is in demo mode. Any failure, a 404 included, means no. */
export function useDemoMode(): boolean {
  const [on, setOn] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    api
      .demoStatus(controller.signal)
      .then((s) => setOn(s.demo_mode === true))
      .catch(() => setOn(false));
    return () => controller.abort();
  }, []);
  return on;
}

/** Reset the backend, remember what the preset built, and reload the page data. */
export function useDemoReset() {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const run = useCallback(
    async (preset?: "salami") => {
      setBusy(true);
      setError(null);
      try {
        const res = await api.demoReset(preset);
        const eighth = res.preset_detail?.awaiting_final_signature_id;
        write({
          flash: preset ? "salami" : "reset",
          salamiCrId: preset && typeof eighth === "string" ? eighth : null,
        });
        router.refresh();
        // Pages fetch from the browser, so only a reload refetches them.
        window.location.reload();
      } catch (e: unknown) {
        setError(e instanceof ApiError || e instanceof Error ? e : new Error(String(e)));
        setBusy(false);
      }
    },
    [router],
  );
  return { run, busy, error };
}

/* The six acts: who the presenter is and where each act opens. */

export const GOV_CONTRACT = "CT-2027-0418";
export const PRIVATE_CONTRACT = "CT-2027-0419";
export const DEMO_REQUEST = "CR-C-SUBSTITUTION";

const GOV_PM: Persona = { party: "GOVERNMENT_ENTITY", role: "PROJECT_MANAGER" };

export const ACT_PERSONA: readonly Persona[] = [
  GOV_PM,
  { party: "CONTRACTOR", role: "PROJECT_MANAGER" },
  GOV_PM,
  GOV_PM,
  { party: "GOVERNMENT_ENTITY", role: "LEGAL_ADVISOR" },
  GOV_PM,
];

const enc = encodeURIComponent;
export const requestHref = (contractId: string, crId: string) =>
  `/contracts/${enc(contractId)}/requests/${enc(crId)}`;
const demoRequestHref = requestHref(PRIVATE_CONTRACT, DEMO_REQUEST);

/** Where an act opens. Act 4 asks the API for the request's variation order. */
async function actHref(act: number): Promise<{ href: string; missing: boolean }> {
  switch (act) {
    case 0:
      return { href: `/contracts/${enc(GOV_CONTRACT)}`, missing: false };
    case 1:
    case 2:
      return { href: demoRequestHref, missing: false };
    case 3:
      try {
        const res = await api.changeRequest(DEMO_REQUEST);
        if (res.variation_order_id) {
          return {
            href: `/contracts/${enc(PRIVATE_CONTRACT)}/variation-orders/${enc(res.variation_order_id)}`,
            missing: false,
          };
        }
      } catch {
        // Fall through to the request itself.
      }
      return { href: demoRequestHref, missing: true };
    case 4:
      return { href: `/contracts/${enc(GOV_CONTRACT)}/limits`, missing: false };
    default:
      return { href: "/evaluation", missing: false };
  }
}

/** Set the act's persona and open its screen. `missing` says the target was absent. */
export function useGoToAct() {
  const router = useRouter();
  const { setPersona } = useSession();
  return useCallback(
    async (act: number): Promise<boolean> => {
      const persona = ACT_PERSONA[act] ?? GOV_PM;
      setPersona(persona);
      write({ active: true, act, flash: null });
      const { href, missing } = await actHref(act);
      router.push(href);
      return missing;
    },
    [router, setPersona],
  );
}
