"use client";

import { useEffect, useSyncExternalStore } from "react";

import { api } from "./api";

/**
 * Document names in both languages, from the backend's checklist catalog
 * (GET /api/policy/required-documents). Requests carry the Arabic name; the
 * English interface looks the English one up here. Loaded once per page load.
 */

let names: Readonly<Record<string, string>> = {};
let requested = false;
const listeners = new Set<() => void>();

function load(): void {
  if (requested) return;
  requested = true;
  api
    .requiredDocuments()
    .then((r) => {
      names = Object.fromEntries(r.documents.map((d) => [d.name_ar, d.name_en]));
      listeners.forEach((l) => l());
    })
    .catch(() => {
      // Without the catalog a name shows as written; try again next mount.
      requested = false;
    });
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

/** Arabic name to English name, for every document the backend knows. */
export function useDocumentNames(): Readonly<Record<string, string>> {
  useEffect(load, []);
  return useSyncExternalStore(subscribe, () => names, () => names);
}

/** The English name of a known document, for helpers that are not components. */
export function englishDocumentName(name: string): string | undefined {
  return names[name];
}
