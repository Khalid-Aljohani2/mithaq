"use client";

import { Direction } from "radix-ui";
import type { ReactNode } from "react";

import { ContractsProvider } from "@/lib/contracts";
import { PrefsProvider, usePrefs } from "@/lib/prefs";
import { SessionProvider } from "@/lib/session";

export function Providers({ children }: { children: ReactNode }) {
  return (
    <PrefsProvider>
      <Directed>
        <SessionProvider>
          <ContractsProvider>{children}</ContractsProvider>
        </SessionProvider>
      </Directed>
    </PrefsProvider>
  );
}

function Directed({ children }: { children: ReactNode }) {
  const { lang } = usePrefs();
  return (
    <Direction.Provider dir={lang === "en" ? "ltr" : "rtl"}>{children}</Direction.Provider>
  );
}
