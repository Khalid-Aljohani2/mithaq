"use client";

import { useCallback, useEffect, useState } from "react";

/**
 * Load one thing from the API, abort on unmount, and allow a manual reload.
 *
 * This is the whole data layer for 5A. See docs/design/DESIGN_PLAN.md
 * section 5 for why no caching library is used.
 */
export type Resource<T> =
  | { status: "loading"; data: null; error: null }
  | { status: "ready"; data: T; error: null }
  | { status: "error"; data: null; error: unknown };

export function useResource<T>(
  load: ((signal: AbortSignal) => Promise<T>) | null,
  deps: readonly unknown[],
): Resource<T> & { reload: () => void; set: (data: T) => void } {
  const [state, setState] = useState<Resource<T>>({
    status: "loading",
    data: null,
    error: null,
  });
  const [tick, setTick] = useState(0);

  useEffect(() => {
    if (!load) return;
    const controller = new AbortController();
    load(controller.signal)
      .then((data) => {
        if (!controller.signal.aborted) {
          setState({ status: "ready", data, error: null });
        }
      })
      .catch((error: unknown) => {
        if (!controller.signal.aborted) {
          setState({ status: "error", data: null, error });
        }
      });
    return () => controller.abort();
    // `load` is recreated on every render; the caller's deps decide refetches.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick]);

  const reload = useCallback(() => {
    setState({ status: "loading", data: null, error: null });
    setTick((t) => t + 1);
  }, []);

  const set = useCallback((data: T) => {
    setState({ status: "ready", data, error: null });
  }, []);

  return { ...state, reload, set };
}
