"use client";

import { useEffect, useMemo, useState } from "react";
import { motion } from "motion/react";

import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { apiBaseUrl, fetchHealth } from "@/lib/api";

type HealthState =
  | { kind: "loading" }
  | { kind: "online"; status: string }
  | { kind: "offline"; message: string };

export default function Home() {
  const [health, setHealth] = useState<HealthState>({ kind: "loading" });

  // Derived, not stored: apiBaseUrl() throws when NEXT_PUBLIC_API_URL is
  // missing in production, so the throw is contained here rather than taking
  // the render down.
  const endpoint = useMemo(() => {
    try {
      return `${apiBaseUrl()}/api/health`;
    } catch {
      return "NEXT_PUBLIC_API_URL is not set";
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();

    fetchHealth(controller.signal)
      .then((data) => setHealth({ kind: "online", status: data.status }))
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        setHealth({
          kind: "offline",
          message: error instanceof Error ? error.message : "Unknown error",
        });
      });

    return () => controller.abort();
  }, []);

  return (
    <main className="flex flex-1 items-center justify-center p-6">
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35, ease: "easeOut" }}
        className="w-full max-w-md"
      >
        <Card>
          <CardHeader>
            <CardTitle className="text-2xl">Mithaq</CardTitle>
            <CardDescription>
              One contract. Two parties. One record of every change.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center justify-between gap-4">
              <span className="text-muted-foreground text-sm">Backend</span>
              {health.kind === "loading" && (
                <Badge variant="secondary">checking…</Badge>
              )}
              {health.kind === "online" && (
                <Badge variant="secondary">{health.status}</Badge>
              )}
              {health.kind === "offline" && (
                <Badge variant="destructive">unreachable</Badge>
              )}
            </div>

            <p className="text-muted-foreground font-mono text-xs break-all">
              {endpoint}
            </p>

            {health.kind === "offline" && (
              <p className="text-destructive text-xs">{health.message}</p>
            )}
          </CardContent>
        </Card>
      </motion.div>
    </main>
  );
}
