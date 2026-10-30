/** Typed client for the Mithaq FastAPI backend. */

/**
 * The backend origin comes only from `NEXT_PUBLIC_API_URL`.
 *
 * Resolved lazily rather than at module load: this module is pulled into a
 * statically prerendered page, so throwing at import time would break
 * `next build` instead of the request that is actually misconfigured.
 *
 * Outside development a missing variable is a hard error rather than a silent
 * fall back to localhost, which would otherwise ship a build that quietly
 * points at nothing.
 */
export function apiBaseUrl(): string {
  const configured = process.env.NEXT_PUBLIC_API_URL?.trim();
  if (configured) {
    return configured.replace(/\/+$/, "");
  }
  if (process.env.NODE_ENV === "production") {
    throw new Error(
      "NEXT_PUBLIC_API_URL is not set. Set it in the Vercel project's environment variables.",
    );
  }
  return "http://localhost:8000";
}

/** Mirrors backend `app.schemas.health.HealthResponse`. */
export type HealthResponse = {
  status: string;
};

export async function fetchHealth(
  signal?: AbortSignal,
): Promise<HealthResponse> {
  const response = await fetch(`${apiBaseUrl()}/api/health`, {
    signal,
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(`Backend returned HTTP ${response.status}`);
  }

  return (await response.json()) as HealthResponse;
}
