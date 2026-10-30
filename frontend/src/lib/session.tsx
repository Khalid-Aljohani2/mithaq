"use client";

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useSyncExternalStore,
  type ReactNode,
} from "react";

import type { Party, Role } from "./api";
import { PARTIES, ROLES } from "./labels";

/**
 * Who is using the app right now (FR-02 role switch).
 *
 * There is no authentication in this MVP (WON'T). The persona is a party plus
 * a role, kept in localStorage, and sent wherever the backend asks for it.
 */
export type Persona = { party: Party; role: Role };

const KEY = "mithaqai.persona";
const DEFAULT: Persona = { party: "GOVERNMENT_ENTITY", role: "PROJECT_MANAGER" };

function read(): Persona {
  try {
    const raw = window.localStorage.getItem(KEY);
    if (!raw) return DEFAULT;
    const parsed: unknown = JSON.parse(raw);
    if (
      typeof parsed === "object" &&
      parsed !== null &&
      "party" in parsed &&
      "role" in parsed &&
      PARTIES.includes(parsed.party as Party) &&
      ROLES.includes(parsed.role as Role)
    ) {
      return { party: parsed.party as Party, role: parsed.role as Role };
    }
  } catch {
    // Storage blocked or corrupt: fall back to the default persona.
  }
  return DEFAULT;
}

// A tiny external store, so every component sees the same persona and a
// change in one tab's switcher re-renders the rest of the page.
const listeners = new Set<() => void>();
let cached: Persona | null = null;
let cachedRaw: string | null = null;

function snapshot(): Persona {
  let raw: string | null = null;
  try {
    raw = window.localStorage.getItem(KEY);
  } catch {
    raw = null;
  }
  if (cached === null || raw !== cachedRaw) {
    cached = read();
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

type SessionValue = {
  persona: Persona;
  setPersona: (persona: Persona) => void;
};

const SessionContext = createContext<SessionValue | null>(null);

export function SessionProvider({ children }: { children: ReactNode }) {
  const persona = useSyncExternalStore(subscribe, snapshot, () => DEFAULT);

  const setPersona = useCallback((next: Persona) => {
    try {
      window.localStorage.setItem(KEY, JSON.stringify(next));
    } catch {
      // Without storage the choice still applies until reload.
    }
    cached = next;
    cachedRaw = JSON.stringify(next);
    listeners.forEach((l) => l());
  }, []);

  const value = useMemo(() => ({ persona, setPersona }), [persona, setPersona]);
  return <SessionContext value={value}>{children}</SessionContext>;
}

export function useSession(): SessionValue {
  const value = useContext(SessionContext);
  if (!value) throw new Error("useSession must be used inside SessionProvider");
  return value;
}

const CONTRACT_KEY = "mithaqai.contract";

export function rememberContract(id: string): void {
  try {
    window.localStorage.setItem(CONTRACT_KEY, id);
  } catch {
    // Not remembering is fine.
  }
}

export function lastContract(): string | null {
  try {
    return window.localStorage.getItem(CONTRACT_KEY);
  } catch {
    return null;
  }
}
