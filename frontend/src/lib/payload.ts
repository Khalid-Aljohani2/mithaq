/**
 * Readers for the stage `payload` objects, which the OpenAPI schema leaves
 * untyped. Each reader checks what it takes and falls back to empty, so a
 * changed payload degrades to "not shown" instead of crashing the page.
 */

import type { StageResult, TraceResponse } from "./api";
import { getDict } from "./prefs";

type Obj = Record<string, unknown>;

function isObj(value: unknown): value is Obj {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
function str(value: unknown): string | null {
  return typeof value === "string" && value !== "" ? value : null;
}
function strList(value: unknown): string[] {
  return Array.isArray(value)
    ? value.filter((v): v is string => typeof v === "string" && v !== "")
    : [];
}
function bool(value: unknown): boolean {
  return value === true;
}

export function stageOf(
  trace: TraceResponse | null | undefined,
  stage: StageResult["stage"],
): StageResult | undefined {
  // The latest run of a stage wins: a resubmitted CR is analysed again.
  return trace?.stages.filter((s) => s.stage === stage).at(-1);
}

export type Narrative = {
  summary: string | null;
  reasons: string[];
  nextActions: string[];
  /** The same prose in English, from the same model call (narrative v2). */
  summaryEn: string | null;
  reasonsEn: string[];
  nextActionsEn: string[];
  reasonCodes: string[];
  conflicts: string[];
};

export function readNarrative(stage: StageResult | undefined): Narrative {
  const payload = isObj(stage?.payload) ? stage.payload : {};
  const narrative = isObj(payload.narrative) ? payload.narrative : {};
  return {
    summary: str(narrative.summary_ar) ?? str(stage?.summary_ar),
    reasons: strList(narrative.reasons_ar),
    nextActions: strList(narrative.next_actions_ar),
    summaryEn: str(narrative.summary_en),
    reasonsEn: strList(narrative.reasons_en),
    nextActionsEn: strList(narrative.next_actions_en),
    reasonCodes: strList(payload.reason_codes),
    conflicts: strList(payload.conflicts),
  };
}

export type Documents = {
  required: string[];
  provided: string[];
  missing: string[];
  complete: boolean;
  gapList: string | null;
};

export function readDocuments(stage: StageResult | undefined): Documents | null {
  if (!stage || !isObj(stage.payload)) return null;
  const p = stage.payload;
  return {
    required: strList(p.required),
    provided: strList(p.provided),
    missing: strList(p.missing),
    complete: bool(p.complete),
    gapList: str(p.gap_list_ar),
  };
}

export type Compliance = {
  policy: {
    costAfterPct: string | null;
    costCapPct: string | null;
    costExceeded: boolean;
    timeAfterPct: string | null;
    timeCapPct: string | null;
    timeExceeded: boolean;
    exceptionRole: string | null;
  } | null;
  legal: {
    applies: boolean;
    blocked: boolean;
    consent: boolean;
    articleRefs: string[];
  } | null;
  risk: { level: string | null; lines: { label: string; text: string }[] } | null;
};

export function readCompliance(stage: StageResult | undefined): Compliance {
  const p = isObj(stage?.payload) ? stage.payload : {};
  const policy = isObj(p.policy) ? p.policy : null;
  const legal = isObj(p.legal) ? p.legal : null;
  const risk = isObj(p.risk) ? p.risk : null;
  const r = getDict().common.risk;
  const riskLines = risk
    ? (
        [
          ["delivery_risk_ar", r.delivery],
          ["operational_risk_ar", r.operational],
          ["commercial_risk_ar", r.commercial],
          ["compliance_risk_ar", r.compliance],
        ] as const
      ).flatMap(([key, label]) => {
        const text = str(risk[key]);
        return text ? [{ label, text }] : [];
      })
    : [];
  return {
    policy: policy && {
      costAfterPct: str(policy.cost_after_pct),
      costCapPct: str(policy.cost_cap_pct),
      costExceeded: bool(policy.cost_exceeded),
      timeAfterPct: str(policy.time_after_pct),
      timeCapPct: str(policy.time_cap_pct),
      timeExceeded: bool(policy.time_exceeded),
      exceptionRole: str(policy.exception_role),
    },
    legal: legal && {
      applies: bool(legal.applies),
      blocked: bool(legal.blocked),
      consent: bool(legal.requires_contractor_consent),
      articleRefs: strList(legal.article_refs),
    },
    risk: risk && { level: str(risk.overall_risk_level), lines: riskLines },
  };
}

export type RateCheck = {
  lineId: string | null;
  contractRate: string | null;
  proposedRate: string | null;
  deviationPct: string | null;
  capPct: string | null;
  flagged: boolean;
};

export type Impact = {
  added: string | null;
  removed: string | null;
  rateChecks: RateCheck[];
};

export function readImpact(stage: StageResult | undefined): Impact {
  const p = isObj(stage?.payload) ? stage.payload : {};
  const checks = Array.isArray(p.rate_checks) ? p.rate_checks.filter(isObj) : [];
  return {
    added: str(p.added_value),
    removed: str(p.removed_value),
    rateChecks: checks.map((c) => ({
      lineId: str(c.line_id),
      contractRate: str(c.contract_rate),
      proposedRate: str(c.proposed_rate),
      deviationPct: str(c.deviation_pct),
      capPct: str(c.cap_pct),
      flagged: bool(c.flagged),
    })),
  };
}

/** Flat, labelled view of any payload for the expandable stage detail. */
export function payloadEntries(payload: unknown): { key: string; value: string }[] {
  if (!isObj(payload)) return [];
  const out: { key: string; value: string }[] = [];
  const walk = (obj: Obj, prefix: string) => {
    for (const [key, value] of Object.entries(obj)) {
      const path = prefix ? `${prefix}.${key}` : key;
      if (value === null || value === undefined || value === "") continue;
      if (isObj(value)) walk(value, path);
      else if (Array.isArray(value)) {
        const items = value.map((v) => (isObj(v) ? JSON.stringify(v) : String(v)));
        if (items.length) out.push({ key: path, value: items.join("\n") });
      } else out.push({ key: path, value: String(value) });
    }
  };
  walk(payload, "");
  return out;
}
