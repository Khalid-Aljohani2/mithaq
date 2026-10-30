/** Typed client for the Mithaq FastAPI backend. */

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/** Mirrors backend `app.schemas.health.HealthResponse`. */
export type HealthResponse = {
  status: string;
};

export async function fetchHealth(
  signal?: AbortSignal,
): Promise<HealthResponse> {
  const response = await fetch(`${API_BASE_URL}/api/health`, {
    signal,
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(`Backend returned HTTP ${response.status}`);
  }

  return (await response.json()) as HealthResponse;
}
