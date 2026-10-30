"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { Empty, ErrorState, Loading } from "@/components/file";
import { useContracts } from "@/lib/contracts";
import { lastContract } from "@/lib/session";

/** Opens the last contract used, or the first one. */
export default function Home() {
  const router = useRouter();
  const contracts = useContracts();

  useEffect(() => {
    if (contracts.status !== "ready" || contracts.data.length === 0) return;
    const remembered = lastContract();
    const target =
      contracts.data.find((c) => c.id === remembered) ?? contracts.data[0];
    router.replace(`/contracts/${encodeURIComponent(target.id)}`);
  }, [contracts, router]);

  return (
    <div className="mx-auto max-w-3xl px-4 py-10 md:px-8">
      {contracts.status === "error" ? (
        <ErrorState error={contracts.error} what="العقود" onRetry={contracts.reload} />
      ) : contracts.status === "ready" && contracts.data.length === 0 ? (
        <Empty title="لا توجد عقود بعد">
          حمّل بيانات العرض التجريبي في الخادم، ثم أعد تحميل الصفحة.
        </Empty>
      ) : (
        <Loading label="جارٍ فتح ملف العقد" rows={3} />
      )}
    </div>
  );
}
