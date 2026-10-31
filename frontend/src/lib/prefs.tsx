"use client";

import {
  createContext,
  Fragment,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useSyncExternalStore,
  type ReactNode,
} from "react";

import { DICTS, type Dict, type Lang } from "./i18n";
import { LANG_KEY, THEME_KEY } from "./prefs-script";

/**
 * Per-browser display preferences: theme and interface language.
 *
 * Both are applied to <html> before first paint by PREFS_SCRIPT (see
 * prefs-script.ts), so a reload never flashes the wrong theme or direction. This
 * module keeps them in sync afterwards. Storage is optional: if it is blocked
 * the choice still applies until reload.
 */

export type Theme = "light" | "dark";


function readStored<T extends string>(key: string, allowed: readonly T[]): T | null {
  try {
    const raw = window.localStorage.getItem(key);
    return allowed.includes(raw as T) ? (raw as T) : null;
  } catch {
    return null;
  }
}

function writeStored(key: string, value: string): void {
  try {
    window.localStorage.setItem(key, value);
  } catch {
    // Without storage the choice still applies until reload.
  }
}

const listeners = new Set<() => void>();
function notify() {
  listeners.forEach((l) => l());
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  window.addEventListener("storage", listener);
  const media = window.matchMedia("(prefers-color-scheme: dark)");
  media.addEventListener("change", listener);
  return () => {
    listeners.delete(listener);
    window.removeEventListener("storage", listener);
    media.removeEventListener("change", listener);
  };
}

function themeSnapshot(): Theme {
  const chosen = readStored<Theme>(THEME_KEY, ["light", "dark"]);
  if (chosen) return chosen;
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function langSnapshot(): Lang {
  return readStored<Lang>(LANG_KEY, ["ar", "en"]) ?? "ar";
}

// Module-level copy for helpers that are not components (formatting, error
// messages). The provider remounts the tree on a language change, so every
// render reads the current value.
let currentLang: Lang = "ar";

function setRenderLang(lang: Lang): void {
  currentLang = lang;
}

export function getLang(): Lang {
  return currentLang;
}

export function getDict(): Dict {
  return DICTS[currentLang];
}

type PrefsValue = {
  theme: Theme;
  toggleTheme: () => void;
  lang: Lang;
  t: Dict;
  setLang: (lang: Lang) => void;
};

const PrefsContext = createContext<PrefsValue | null>(null);

export function PrefsProvider({ children }: { children: ReactNode }) {
  const theme = useSyncExternalStore(subscribe, themeSnapshot, () => "light" as Theme);
  const lang = useSyncExternalStore(subscribe, langSnapshot, () => "ar" as Lang);
  // The render language must match what the tree renders (Arabic during
  // hydration), so it is set here rather than read from storage.
  setRenderLang(lang);

  useEffect(() => {
    const root = document.documentElement;
    root.lang = lang;
    root.dir = lang === "en" ? "ltr" : "rtl";
    root.removeAttribute("data-lang-pending");
  }, [lang]);

  const toggleTheme = useCallback(() => {
    const next: Theme = themeSnapshot() === "dark" ? "light" : "dark";
    writeStored(THEME_KEY, next);
    document.documentElement.setAttribute("data-theme", next);
    notify();
  }, []);

  const setLang = useCallback((next: Lang) => {
    writeStored(LANG_KEY, next);
    currentLang = next;
    notify();
  }, []);

  const value = useMemo(
    () => ({ theme, toggleTheme, lang, t: DICTS[lang], setLang }),
    [theme, toggleTheme, lang, setLang],
  );
  // Keyed on the language so every component, and every helper it calls,
  // renders again in the new language.
  return (
    <PrefsContext value={value}>
      <Fragment key={lang}>{children}</Fragment>
    </PrefsContext>
  );
}

export function usePrefs(): PrefsValue {
  const value = useContext(PrefsContext);
  if (!value) throw new Error("usePrefs must be used inside PrefsProvider");
  return value;
}

/** The dictionary for the current language. */
export function useT(): Dict {
  return usePrefs().t;
}

/** Choose between a backend field's Arabic and English versions. */
export function useBilingual(): (ar: string, en: string | null | undefined) => string {
  const { lang } = usePrefs();
  return useCallback((ar, en) => (lang === "en" && en ? en : ar), [lang]);
}
