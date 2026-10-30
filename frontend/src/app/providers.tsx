"use client";

import { Direction } from "radix-ui";
import type { ReactNode } from "react";

import { ContractsProvider } from "@/lib/contracts";
import { SessionProvider } from "@/lib/session";

export function Providers({ children }: { children: ReactNode }) {
  return (
    <Direction.Provider dir="rtl">
      <SessionProvider>
        <ContractsProvider>{children}</ContractsProvider>
      </SessionProvider>
    </Direction.Provider>
  );
}
