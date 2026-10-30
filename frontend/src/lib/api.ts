/**
 * Typed client for the MithaqAi FastAPI backend.
 *
 * Every type comes from `api-types.ts`, generated from the backend's OpenAPI
 * schema by `npm run gen:api`. Nothing here is written by hand from memory of
 * the backend, so a schema change shows up as a type error.
 */

import type { components } from "./api-types";

type Schemas = components["schemas"];

export type ActorType = Schemas["ActorType"];
export type AnalysisResponse = Schemas["AnalysisResponse"];
export type ApprovalDecision = Schemas["ApprovalDecision"];
export type ApprovalStep = Schemas["ApprovalStep"];
export type AttachmentsInput = Schemas["AttachmentsInput"];
export type BreakdownLine = Schemas["BreakdownLine"];
export type CapLine = Schemas["CapLine"];
export type ChangeKind = Schemas["ChangeKind"];
export type ChangeRequest = Schemas["ChangeRequest"];
export type ChangeRequestResponse = Schemas["ChangeRequestResponse"];
export type Contract = Schemas["Contract"];
export type ContractSummary = Schemas["ContractSummary"];
export type ContractType = Schemas["ContractType"];
export type CRState = Schemas["CRState"];
export type DecisionInput = Schemas["DecisionInput"];
export type DocumentChecklist = Schemas["DocumentChecklist"];
export type EvalSummaryResponse = Schemas["EvalSummaryResponse"];
export type HealthResponse = Schemas["HealthResponse"];
export type LedgerResponse = Schemas["LedgerResponse"];
export type NotificationListResponse = Schemas["NotificationListResponse"];
export type Party = Schemas["Party"];
export type PolicyThresholdOut = Schemas["PolicyThresholdOut"];
export type Recommendation = Schemas["Recommendation"];
export type RequiredDocumentsResponse = Schemas["RequiredDocumentsResponse"];
export type Role = Schemas["Role"];
export type Stage = Schemas["Stage"];
export type StageResult = Schemas["StageResult"];
export type SubmitRequestInput = Schemas["SubmitRequestInput"];
export type TraceResponse = Schemas["TraceResponse"];
export type UsageSnapshot = Schemas["UsageSnapshot"];
export type VariationOrder = Schemas["VariationOrder"];
export type VariationOrderResponse = Schemas["VariationOrderResponse"];

/**
 * The backend origin comes only from `NEXT_PUBLIC_API_URL`.
 *
 * Resolved lazily rather than at module load, so a missing variable fails the
 * request that needs it instead of `next build`. Outside development a missing
 * variable is a hard error rather than a silent fall back to localhost.
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

/**
 * A failed call. `status` 0 means the backend could not be reached. `code` is
 * the workflow error code the backend sends (`WRONG_ROLE`, `REASON_REQUIRED`,
 * ...), when there is one.
 */
export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    readonly detail: string,
  ) {
    super(detail || code || `HTTP ${status}`);
    this.name = "ApiError";
  }
}

/** Read FastAPI's `detail`: a string, a `{code, message}` object, or a list. */
function readDetail(body: unknown): { code: string; detail: string } {
  if (typeof body !== "object" || body === null || !("detail" in body)) {
    return { code: "", detail: "" };
  }
  const detail = body.detail;
  if (typeof detail === "string") return { code: "", detail };
  if (Array.isArray(detail)) {
    const messages = detail.map((item: unknown) =>
      typeof item === "object" && item !== null && "msg" in item
        ? String(item.msg)
        : "",
    );
    return { code: "VALIDATION", detail: messages.filter(Boolean).join("; ") };
  }
  if (typeof detail === "object" && detail !== null) {
    return {
      code: "code" in detail ? String(detail.code) : "",
      detail: "message" in detail ? String(detail.message) : "",
    };
  }
  return { code: "", detail: "" };
}

async function request<T>(
  path: string,
  init: RequestInit & { signal?: AbortSignal } = {},
): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${apiBaseUrl()}${path}`, {
      cache: "no-store",
      ...init,
      headers: {
        Accept: "application/json",
        ...(init.body ? { "Content-Type": "application/json" } : {}),
        ...init.headers,
      },
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw error;
    }
    throw new ApiError(0, "NETWORK", "");
  }

  if (!response.ok) {
    const body: unknown = await response.json().catch(() => null);
    const { code, detail } = readDetail(body);
    throw new ApiError(response.status, code, detail);
  }
  return (await response.json()) as T;
}

const enc = encodeURIComponent;

export const api = {
  health: (signal?: AbortSignal) =>
    request<HealthResponse>("/api/health", { signal }),

  contracts: (signal?: AbortSignal) =>
    request<Schemas["ContractListResponse"]>("/api/contracts", { signal }),

  contract: (id: string, signal?: AbortSignal) =>
    request<Contract>(`/api/contracts/${enc(id)}`, { signal }),

  ledger: (id: string, signal?: AbortSignal) =>
    request<LedgerResponse>(`/api/contracts/${enc(id)}/ledger`, { signal }),

  changeRequests: (contractId: string, signal?: AbortSignal) =>
    request<Schemas["ChangeRequestListResponse"]>(
      `/api/contracts/${enc(contractId)}/change-requests`,
      { signal },
    ),

  submitChangeRequest: (contractId: string, body: SubmitRequestInput) =>
    request<ChangeRequestResponse>(
      `/api/contracts/${enc(contractId)}/change-requests`,
      { method: "POST", body: JSON.stringify(body) },
    ),

  changeRequest: (crId: string, signal?: AbortSignal) =>
    request<ChangeRequestResponse>(`/api/change-requests/${enc(crId)}`, {
      signal,
    }),

  trace: (crId: string, signal?: AbortSignal) =>
    request<TraceResponse>(`/api/change-requests/${enc(crId)}/trace`, {
      signal,
    }),

  /** Answer a gap list with the documents now on file. Human action. */
  supplyAttachments: (crId: string, body: AttachmentsInput) =>
    request<ChangeRequestResponse>(
      `/api/change-requests/${enc(crId)}/attachments`,
      { method: "POST", body: JSON.stringify(body) },
    ),

  analyse: (crId: string) =>
    request<AnalysisResponse>(`/api/change-requests/${enc(crId)}/analyse`, {
      method: "POST",
    }),

  startApproval: (crId: string) =>
    request<ChangeRequestResponse>(
      `/api/change-requests/${enc(crId)}/start-approval`,
      { method: "POST" },
    ),

  decide: (crId: string, body: DecisionInput) =>
    request<ChangeRequestResponse>(
      `/api/change-requests/${enc(crId)}/decide`,
      { method: "POST", body: JSON.stringify(body) },
    ),

  variationOrder: (voId: string, signal?: AbortSignal) =>
    request<VariationOrderResponse>(`/api/variation-orders/${enc(voId)}`, {
      signal,
    }),

  variationOrders: (contractId: string, signal?: AbortSignal) =>
    request<Schemas["VariationOrderListResponse"]>(
      `/api/contracts/${enc(contractId)}/variation-orders`,
      { signal },
    ),

  /** The stage 2 checklist, so a requester sees it before stage 2 does. */
  requiredDocuments: (signal?: AbortSignal) =>
    request<RequiredDocumentsResponse>("/api/policy/required-documents", {
      signal,
    }),

  policyThresholds: (signal?: AbortSignal) =>
    request<PolicyThresholdOut[]>("/api/policy/thresholds", { signal }),

  /** The published evaluation result. `available: false` means not measured. */
  evalSummary: (signal?: AbortSignal) =>
    request<EvalSummaryResponse>("/api/eval/summary", { signal }),

  notifications: (party: Party, role: Role, signal?: AbortSignal) =>
    request<NotificationListResponse>(
      `/api/notifications?party=${enc(party)}&role=${enc(role)}`,
      { signal },
    ),
};
