/**
 * Display labels for backend enums and codes, in the current interface
 * language. The strings live in i18n/common.ts; these exports read them at
 * access time, so they follow a language change without changing shape.
 *
 * These are names for things, not legal assertions: no percentage, cap or
 * article text is written here. Articles come from the API.
 */

import {
  ApiError,
  type ActorType,
  type AuditAction,
  type NotificationKind,
  type ChangeKind,
  type ContractType,
  type CRState,
  type Party,
  type Recommendation,
  type Role,
  type Stage,
} from "./api";
import type { Dict } from "./i18n";
import { englishDocumentName } from "./documents";
import { getDict, getLang } from "./prefs";

/**
 * A read-only record whose values come from the current dictionary at access
 * time. Indexing, `in` and Object.keys all see the live map.
 */
function labelMap<K extends string, V>(
  source: (d: Dict) => Record<K, V>,
): Record<K, V> {
  const live = () => source(getDict()) as Record<string, V>;
  return new Proxy({} as Record<K, V>, {
    get: (_, key) => (typeof key === "string" ? live()[key] : undefined),
    has: (_, key) => typeof key === "string" && key in live(),
    ownKeys: () => Reflect.ownKeys(live()),
    getOwnPropertyDescriptor: (_, key) => {
      const desc = Reflect.getOwnPropertyDescriptor(live(), key);
      return desc ? { ...desc, configurable: true } : undefined;
    },
  });
}

/**
 * A required or attached document's name for display. The backend names
 * documents in Arabic; in English the known names read in English and any
 * other name stays as written.
 */
export function documentLabel(name: string): string {
  if (getLang() !== "en") return name;
  return englishDocumentName(name) ?? getDict().common.documentName[name] ?? name;
}

export type Tone = "neutral" | "seal" | "amber" | "legal";

export const STATE_LABEL: Record<CRState, string> = labelMap((d) => d.common.state);

export const STATE_TONE: Record<CRState, Tone> = {
  RECEIVED: "neutral",
  AWAITING_DOCUMENTS: "amber",
  IN_ANALYSIS: "neutral",
  RECOMMENDED: "neutral",
  IN_APPROVAL: "neutral",
  REVISION_REQUESTED: "amber",
  REJECTED: "legal",
  CLOSED_IN_SCOPE: "neutral",
  APPROVED: "seal",
  VO_ISSUED: "seal",
  IN_EXECUTION: "seal",
  CLOSED: "neutral",
};

/** Abbreviation (when the kind has one) and its full name. */
const KIND_ABBR: Record<ChangeKind, string | null> = {
  IN_SCOPE: null,
  PCR: "PCR",
  NCR: "NCR",
  SUBSTITUTION: null,
  UNCLEAR: null,
};

export const KIND: Record<ChangeKind, { abbr: string | null; name: string }> = labelMap((d) => {
  const names = d.common.kindName;
  const out = {} as Record<ChangeKind, { abbr: string | null; name: string }>;
  for (const k of Object.keys(KIND_ABBR) as ChangeKind[]) {
    out[k] = { abbr: KIND_ABBR[k], name: names[k] };
  }
  return out;
});

/** Short label for a kind once its full name has been shown on the screen. */
export function kindShort(kind: ChangeKind | null | undefined): string {
  if (!kind) return getDict().common.kindNotAnalysed;
  return KIND[kind].abbr ?? KIND[kind].name;
}

/** Full label for a kind: "PCR (طلب تغيير موجب)" or the name alone. */
export function kindFull(kind: ChangeKind | null | undefined): string {
  if (!kind) return getDict().common.kindNotClassified;
  const { abbr, name } = KIND[kind];
  return abbr ? `${abbr} (${name})` : name;
}

/** The terms key shown once at the top of a screen. */
export const TERMS: Readonly<Record<"CR" | "PCR" | "NCR" | "VO", string>> = labelMap(
  (d) => d.common.terms,
);
export type Term = keyof typeof TERMS;

export const CONTRACT_TYPE_LABEL: Record<ContractType, string> = labelMap(
  (d) => d.common.contractType,
);

/** GOVERNMENT_ENTITY is the client side: a government entity or a private owner. */
export function partyLabel(party: Party, contractType: ContractType | undefined): string {
  const c = getDict().common;
  if (party === "CONTRACTOR") return c.contractor;
  return contractType === "PRIVATE" ? c.owner : c.governmentEntity;
}

/** Used where no contract is in view: names both readings of the client side. */
export function partyLabelNeutral(party: Party): string {
  const c = getDict().common;
  return party === "CONTRACTOR" ? c.contractor : c.clientNeutral;
}

export const ROLE_LABEL: Record<Role, string> = labelMap((d) => d.common.role);

export const PARTIES: readonly Party[] = ["GOVERNMENT_ENTITY", "CONTRACTOR"];
export const ROLES: readonly Role[] = [
  "PROJECT_MANAGER",
  "TECHNICAL_MANAGER",
  "FINANCE_MANAGER",
  "LEGAL_ADVISOR",
  "CEO",
];

const RECOMMENDATION_TONE: Record<Recommendation, Tone> = {
  APPROVE: "seal",
  REJECT: "legal",
  REQUEST_REVISION: "amber",
  CLOSE_IN_SCOPE: "neutral",
};

export const RECOMMENDATION: Record<
  Recommendation,
  { verb: string; short: string; tone: Tone }
> = labelMap((d) => {
  const out = {} as Record<Recommendation, { verb: string; short: string; tone: Tone }>;
  for (const k of Object.keys(RECOMMENDATION_TONE) as Recommendation[]) {
    out[k] = { ...d.common.recommendation[k], tone: RECOMMENDATION_TONE[k] };
  }
  return out;
});

const STAGE_ORDER: readonly { stage: Stage; no: number; actor: ActorType }[] = [
  { stage: "INTAKE", no: 1, actor: "AI" },
  { stage: "DOCUMENT_VALIDATION", no: 2, actor: "CODE" },
  { stage: "SCOPE_ANALYSIS", no: 3, actor: "AI" },
  { stage: "TECHNICAL_ASSESSMENT", no: 4, actor: "AI" },
  { stage: "COST_SCHEDULE_IMPACT", no: 5, actor: "CODE" },
  { stage: "RISK_COMPLIANCE", no: 6, actor: "AI" },
  { stage: "ORCHESTRATOR", no: 7, actor: "CODE" },
  { stage: "APPROVAL_GATE", no: 8, actor: "HUMAN" },
  { stage: "ISSUE_VO", no: 9, actor: "HUMAN" },
  { stage: "UPDATE_RECORDS", no: 10, actor: "CODE" },
  { stage: "EXECUTION_FOLLOW_UP", no: 11, actor: "HUMAN" },
];

/** The eleven stages; `name` is read from the dictionary on access. */
export const STAGES: readonly { stage: Stage; no: number; name: string; actor: ActorType }[] =
  STAGE_ORDER.map((s) => ({
    ...s,
    get name() {
      return getDict().common.stage[s.stage];
    },
  }));

export const ACTOR_LABEL: Record<ActorType, string> = labelMap((d) => d.common.actor);

/** Why a slot is in the approval chain. */
export const CHAIN_REASON: Record<string, string> = labelMap((d) => d.common.chainReason);

/** The orchestrator's reason codes. */
export const REASON_CODE: Record<string, string> = labelMap((d) => d.common.reasonCode);

/** Display names for limit scopes. Citations come from the API, not from here. */
export const SCOPE_NAME: Record<string, string> = labelMap((d) => d.common.scopeName);

/** Where a threshold comes from (NFR-16). */
export const SOURCE_LABEL: Record<string, string> = labelMap((d) => d.common.source);

/** What went wrong, and what to do about it. */
export function errorMessage(error: unknown): string {
  const e = getDict().common.error;
  if (error instanceof ApiError) {
    switch (error.code) {
      case "NETWORK":
      case "WRONG_ROLE":
      case "REASON_REQUIRED":
      case "NOT_ANALYSABLE":
      case "NOT_IN_APPROVAL":
      case "NO_CHAIN":
      case "WRONG_PARTY":
      case "NOT_AWAITING_DOCUMENTS":
      case "NOT_PRICED":
      case "CHAIN_COMPLETE":
      case "CR_NOT_FOUND":
      case "CONTRACT_NOT_FOUND":
      case "CONTRACT_INVALID":
      case "DRAFT_NEEDS_LIVE_PROVIDER":
        return e[error.code];
      case "LEGAL_CAP_EXCEEDED":
        // The one refusal no internal approval can lift, so it says which
        // provision it rests on rather than only that it was refused.
        return e.legalCap(error.articles);
      case "VALIDATION":
        return e.validation(error.detail);
    }
    if (error.status === 404) return e.notFound;
    if (error.status === 429) return e.tooMany;
    if (error.status >= 500) return e.server;
    return error.detail || e.refused(error.status);
  }
  return e.unexpected;
}

export const NOTIFICATION_KIND: Record<NotificationKind, string> = labelMap(
  (d) => d.common.notification,
);

export const AUDIT_ACTION: Record<AuditAction, string> = labelMap((d) => d.common.auditAction);

/** The audit log's actor: a role name, or CODE for the system itself. */
export function auditActor(actor: string): string {
  if (actor === "CODE") return getDict().common.auditSystem;
  if (actor === "AI") return getDict().common.auditAgent;
  return actor in ROLE_LABEL ? ROLE_LABEL[actor as Role] : actor;
}
