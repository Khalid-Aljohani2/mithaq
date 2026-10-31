"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ChevronDown, Check, Moon, Sun } from "lucide-react";
import { Popover } from "radix-ui";
import { useId, useState } from "react";

import { ArabicOriginal } from "@/components/original";
import { Badge } from "@/components/ui/badge";
import type { Party, Role } from "@/lib/api";
import { useContracts, useCurrentContract } from "@/lib/contracts";
import {
  CONTRACT_TYPE_LABEL,
  PARTIES,
  ROLE_LABEL,
  ROLES,
  partyLabel,
  partyLabelNeutral,
} from "@/lib/labels";
import { usePrefs, useT } from "@/lib/prefs";
import { useSession } from "@/lib/session";
import { cn } from "@/lib/utils";

import { NotificationBell } from "./notifications";

export function SkipLink() {
  const t = useT();
  return (
    <a
      href="#main"
      className="sr-only z-50 bg-sheet print:hidden px-3 py-2 focus:not-sr-only focus:absolute focus:start-2 focus:top-2"
    >
      {t.shell.skipToContent}
    </a>
  );
}

export function Letterhead() {
  const pathname = usePathname();
  const t = useT();
  return (
    <header className="rule-double bg-sheet">
      <div className="mx-auto grid max-w-[90rem] grid-cols-[1fr_auto] items-center gap-x-4 gap-y-3 px-4 py-3 md:grid-cols-[auto_1fr_auto] md:px-8">
        <Wordmark />
        <div className="col-span-2 row-start-2 flex flex-wrap items-stretch gap-2 md:col-span-1 md:col-start-2 md:row-start-1">
          <ContractSwitcher />
          <RoleSwitcher />
        </div>
        <div className="col-start-2 row-start-1 flex items-center gap-2 md:col-start-3">
          <Link
            href="/evaluation"
            className="inline-flex min-h-11 items-center rounded-[var(--radius-ctl)] px-3 text-sm font-medium underline-offset-4 hover:underline aria-[current=page]:underline"
            aria-current={pathname === "/evaluation" ? "page" : undefined}
          >
            {t.shell.evaluation}
          </Link>
          <LanguageToggle />
          <ThemeToggle />
          <NotificationBell />
        </div>
      </div>
    </header>
  );
}

const toggleClass =
  "inline-flex size-11 items-center justify-center rounded-[var(--radius-ctl)] border border-rule-strong bg-sheet text-sm font-medium hover:bg-paper";

function ThemeToggle() {
  const { theme, toggleTheme, t } = usePrefs();
  const label = theme === "dark" ? t.shell.themeToLight : t.shell.themeToDark;
  return (
    <button type="button" data-theme-toggle onClick={toggleTheme} aria-label={label} title={label} className={toggleClass}>
      {theme === "dark" ? <Sun aria-hidden className="size-5" /> : <Moon aria-hidden className="size-5" />}
    </button>
  );
}

function LanguageToggle() {
  const { lang, setLang, t } = usePrefs();
  const next = lang === "ar" ? "en" : "ar";
  return (
    <button
      type="button"
      data-lang-toggle
      onClick={() => setLang(next)}
      aria-label={t.shell.langSwitchLabel}
      title={t.shell.langSwitchLabel}
      lang={next}
      className={cn(toggleClass, "w-auto px-3")}
    >
      {t.shell.langSwitch}
    </button>
  );
}

function Wordmark() {
  const t = useT();
  return (
    <Link
      href="/"
      className="text-xl leading-none font-semibold tracking-tight"
      aria-label={t.shell.homeLabel}
    >
      <span dir="ltr" className="inline-block">
        Mithaq<span className="font-normal text-ink-muted">Ai</span>
      </span>
    </Link>
  );
}

const triggerClass =
  "flex min-h-11 items-center gap-3 rounded-[var(--radius-ctl)] border border-rule-strong bg-sheet px-3 py-1.5 text-start hover:bg-paper data-[state=open]:bg-paper";

function ContractSwitcher() {
  const { status, data } = useContracts();
  const { id, contract } = useCurrentContract();
  const [open, setOpen] = useState(false);
  const t = useT();

  return (
    <Popover.Root open={open} onOpenChange={setOpen}>
      <Popover.Trigger className={cn(triggerClass, "min-w-0 flex-1 md:flex-none")}>
        <span className="min-w-0">
          <span className="block text-2xs text-ink-muted">{t.shell.contract}</span>
          <span className="flex items-center gap-2 text-sm font-medium">
            {contract ? (
              <>
                <span className="ref">{contract.id}</span>
                <Badge variant="muted">{CONTRACT_TYPE_LABEL[contract.contract_type]}</Badge>
              </>
            ) : status === "error" ? (
              t.shell.contractsFailed
            ) : id ? (
              <span className="ref">{id}</span>
            ) : (
              t.shell.chooseContract
            )}
          </span>
        </span>
        <ChevronDown aria-hidden className="ms-auto size-4 text-ink-muted" />
      </Popover.Trigger>
      <Popover.Portal>
        <Popover.Content
          align="start"
          sideOffset={6}
          className="z-50 w-[min(26rem,calc(100vw-2rem))] border border-rule-strong bg-sheet shadow-[0_8px_24px_color-mix(in_srgb,var(--ink)_12%,transparent)]"
        >
          <p className="border-b border-rule px-4 py-2 text-xs text-ink-muted">
            {t.shell.availableContracts}
          </p>
          <ul>
            {(data ?? []).map((c) => (
              <li key={c.id}>
                <Link
                  href={`/contracts/${encodeURIComponent(c.id)}`}
                  onClick={() => setOpen(false)}
                  aria-current={c.id === id ? "page" : undefined}
                  className="flex items-start gap-3 border-b border-rule px-4 py-3 last:border-b-0 hover:bg-paper"
                >
                  <Check
                    aria-hidden
                    className={cn("mt-1 size-4", c.id === id ? "text-seal" : "invisible")}
                  />
                  <span className="min-w-0 flex-1">
                    <span className="flex items-center gap-2">
                      <span className="ref text-sm font-medium">{c.id}</span>
                      <Badge variant="muted">{CONTRACT_TYPE_LABEL[c.contract_type]}</Badge>
                    </span>
                    <ArabicOriginal as="span" showLabel={false} className="block text-sm">
                      {c.title_ar}
                    </ArabicOriginal>
                    <span className="block text-xs text-ink-muted">
                      {partyLabel("GOVERNMENT_ENTITY", c.contract_type)}:{" "}
                      <ArabicOriginal as="span" showLabel={false}>
                        {c.entity_name}
                      </ArabicOriginal>
                    </span>
                  </span>
                </Link>
              </li>
            ))}
          </ul>
          {status === "loading" && (
            <p className="px-4 py-3 text-sm text-ink-muted">{t.shell.loadingContracts}</p>
          )}
          <Link
            href="/projects/new"
            onClick={() => setOpen(false)}
            className="block border-t border-rule px-4 py-3 text-sm font-medium text-seal hover:bg-paper"
            data-switcher-new-project
          >
            + {t.project.newProject}
          </Link>
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
  );
}

function RoleSwitcher() {
  const { persona, setPersona } = useSession();
  const { contract } = useCurrentContract();
  const partyId = useId();
  const roleId = useId();
  const t = useT();
  const partyName = (p: Party) =>
    contract ? partyLabel(p, contract.contract_type) : partyLabelNeutral(p);

  return (
    <Popover.Root>
      <Popover.Trigger className={cn(triggerClass, "min-w-0 flex-1 md:flex-none")}>
        <span className="min-w-0">
          <span className="block text-2xs text-ink-muted">{t.shell.actingAs}</span>
          <span className="block truncate text-sm font-medium">
            {ROLE_LABEL[persona.role]}
            {t.common.listSep}
            {partyName(persona.party)}
          </span>
        </span>
        <ChevronDown aria-hidden className="ms-auto size-4 text-ink-muted" />
      </Popover.Trigger>
      <Popover.Portal>
        <Popover.Content
          align="start"
          sideOffset={6}
          className="z-50 w-[min(22rem,calc(100vw-2rem))] border border-rule-strong bg-sheet p-4 shadow-[0_8px_24px_color-mix(in_srgb,var(--ink)_12%,transparent)]"
        >
          <p className="mb-3 text-xs text-ink-muted">
            {t.shell.roleHint}
          </p>
          <label htmlFor={partyId} className="block text-xs font-medium">
            {t.shell.party}
          </label>
          <select
            id={partyId}
            value={persona.party}
            onChange={(e) => setPersona({ ...persona, party: e.target.value as Party })}
            className="mt-1 mb-3 h-10 w-full rounded-[var(--radius-ctl)] border border-rule-strong bg-sheet px-2"
          >
            {PARTIES.map((p) => (
              <option key={p} value={p}>
                {partyName(p)}
              </option>
            ))}
          </select>
          <label htmlFor={roleId} className="block text-xs font-medium">
            {t.shell.role}
          </label>
          <select
            id={roleId}
            value={persona.role}
            onChange={(e) => setPersona({ ...persona, role: e.target.value as Role })}
            className="mt-1 h-10 w-full rounded-[var(--radius-ctl)] border border-rule-strong bg-sheet px-2"
          >
            {ROLES.map((r) => (
              <option key={r} value={r}>
                {ROLE_LABEL[r]}
              </option>
            ))}
          </select>
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
  );
}
