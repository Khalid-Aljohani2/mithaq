"use client";

import Link from "next/link";
import { AlarmClock, Bell, X } from "lucide-react";
import { Dialog } from "radix-ui";
import { useCallback, useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { api, type Notification } from "@/lib/api";
import { useContracts } from "@/lib/contracts";
import { formatDateTime } from "@/lib/format";
import { NOTIFICATION_KIND, ROLE_LABEL, errorMessage, partyLabelNeutral } from "@/lib/labels";
import { useSession } from "@/lib/session";
import { cn } from "@/lib/utils";

const POLL_MS = 30_000;

type Feed =
  | { status: "loading" }
  | { status: "ready"; items: Notification[] }
  | { status: "error"; error: unknown };

/**
 * The bell and its drawer (FR-11): notifications for the active party and
 * role, newest first. Reminders carry their own mark and label. The list is
 * polled every 30 seconds, which is the only polling in the app.
 */
export function NotificationBell() {
  const { persona } = useSession();
  const contracts = useContracts();
  const [feed, setFeed] = useState<Feed>({ status: "loading" });
  const [open, setOpen] = useState(false);
  const [tick, setTick] = useState(0);
  const refresh = useCallback(() => setTick((t) => t + 1), []);

  useEffect(() => {
    const controller = new AbortController();
    const load = () =>
      api
        .notifications(persona.party, persona.role, controller.signal)
        .then((r) => {
          const items = [...r.notifications].sort((a, b) =>
            b.created_at.localeCompare(a.created_at),
          );
          setFeed({ status: "ready", items });
        })
        .catch((error: unknown) => {
          if (!controller.signal.aborted) setFeed({ status: "error", error });
        });
    load();
    const timer = window.setInterval(load, POLL_MS);
    return () => {
      controller.abort();
      window.clearInterval(timer);
    };
  }, [persona.party, persona.role, tick]);

  const count = feed.status === "ready" ? feed.items.length : null;
  const reminders = feed.status === "ready" ? feed.items.filter((n) => n.is_reminder).length : 0;
  const contractType = (contractId: string) =>
    contracts.data?.find((c) => c.id === contractId)?.contract_type;
  const who = `${ROLE_LABEL[persona.role]}، ${partyLabelNeutral(persona.party)}`;

  const label =
    feed.status === "error"
      ? "الإشعارات: تعذر التحميل"
      : count === null
        ? "الإشعارات: جارٍ التحميل"
        : count === 0
          ? "الإشعارات: لا جديد"
          : `الإشعارات: ${count}`;

  return (
    <Dialog.Root
      open={open}
      onOpenChange={(next) => {
        setOpen(next);
        if (next) refresh();
      }}
    >
      <Dialog.Trigger
        aria-label={label}
        title={label}
        className="relative inline-flex size-11 items-center justify-center rounded-[var(--radius-ctl)] border border-rule-strong bg-sheet hover:bg-paper data-[state=open]:bg-paper"
      >
        <Bell aria-hidden className="size-5" />
        {count !== null && count > 0 && (
          <span
            aria-hidden
            className="absolute -top-1.5 -end-1.5 min-w-5 rounded-full border-2 border-sheet bg-amber px-1 text-center text-2xs leading-4 font-semibold text-sheet"
          >
            {count}
          </span>
        )}
        {feed.status === "error" && (
          <span aria-hidden className="absolute -top-1 -end-1 size-2.5 rounded-full bg-legal" />
        )}
      </Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-[rgb(15_20_26/0.45)] data-[state=open]:animate-in data-[state=open]:fade-in-0" />
        <Dialog.Content className="fixed inset-y-0 end-0 z-50 flex w-full max-w-[26rem] flex-col border-s border-rule-strong bg-sheet shadow-[0_8px_24px_color-mix(in_srgb,var(--ink)_12%,transparent)] data-[state=open]:animate-in data-[state=open]:slide-in-from-left-8 motion-reduce:animate-none">
          <header className="rule-double flex items-start justify-between gap-3 px-5 pt-[max(1rem,env(safe-area-inset-top))] pb-3">
            <div>
              <Dialog.Title className="text-lg font-semibold">الإشعارات</Dialog.Title>
              <Dialog.Description className="text-xs text-ink-muted">
                لدورك: {who}
                {reminders > 0 && <>، منها {reminders} تذكير</>}
              </Dialog.Description>
            </div>
            <Dialog.Close
              aria-label="إغلاق الإشعارات"
              className="inline-flex size-9 items-center justify-center rounded-[var(--radius-ctl)] hover:bg-paper"
            >
              <X aria-hidden className="size-5" />
            </Dialog.Close>
          </header>

          <div className="flex-1 overflow-y-auto px-5 pb-[max(1rem,env(safe-area-inset-bottom))]">
            {feed.status === "loading" ? (
              <p role="status" className="py-6 text-sm text-ink-muted">جارٍ تحميل الإشعارات</p>
            ) : feed.status === "error" ? (
              <div role="alert" className="mt-4 border-s-4 border-legal bg-legal-wash px-3 py-3 text-sm">
                <p className="font-medium text-legal">تعذر تحميل الإشعارات.</p>
                <p className="mt-1">{errorMessage(feed.error)}</p>
                <button type="button" onClick={refresh} className="mt-2 text-sm underline underline-offset-4">
                  إعادة المحاولة
                </button>
              </div>
            ) : feed.items.length === 0 ? (
              <div className="mt-4 border border-dashed border-rule-strong px-4 py-6 text-sm">
                <p className="font-medium">لا إشعارات لدورك الآن.</p>
                <p className="mt-1 text-ink-muted">
                  يصلك إشعار حين يحين دورك في سلسلة اعتماد، أو حين يتغير طلب قدّمه طرفك.
                  بدّل الدور من أعلى الصفحة لرؤية إشعارات دور آخر.
                </p>
              </div>
            ) : (
              <ol className="divide-y divide-rule">
                {feed.items.map((n, i) => (
                  <li key={n.id ?? `${n.cr_id}-${i}`}>
                    <Link
                      href={`/contracts/${encodeURIComponent(n.contract_id)}/requests/${encodeURIComponent(n.cr_id)}`}
                      onClick={() => setOpen(false)}
                      className={cn(
                        "-mx-5 block border-s-4 px-4 py-3 hover:bg-paper",
                        n.is_reminder ? "border-amber bg-amber-wash/50" : "border-transparent",
                      )}
                    >
                      <span className="flex items-center justify-between gap-2">
                        <span className="flex items-center gap-2 text-sm font-semibold">
                          {n.is_reminder && <AlarmClock aria-hidden className="size-4 text-amber" />}
                          {NOTIFICATION_KIND[n.kind]}
                        </span>
                        {n.is_reminder && <Badge variant="amber">تذكير</Badge>}
                      </span>
                      <span className="mt-1 block text-sm">{n.message_ar}</span>
                      <span className="mt-1 flex flex-wrap items-center gap-x-3 text-xs text-ink-muted">
                        <span className="ref">{n.cr_id}</span>
                        <span>
                          عقد <span className="ref">{n.contract_id}</span>
                          {contractType(n.contract_id) === "PRIVATE" ? "، خاص" : contractType(n.contract_id) === "GOVERNMENT" ? "، حكومي" : ""}
                        </span>
                        <time dateTime={n.created_at}>{formatDateTime(n.created_at)}</time>
                      </span>
                    </Link>
                  </li>
                ))}
              </ol>
            )}
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
