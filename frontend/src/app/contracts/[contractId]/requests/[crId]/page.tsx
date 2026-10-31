"use client";

import Link from "next/link";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { useReducedMotion } from "motion/react";
import { Suspense, useCallback, useEffect, useRef, useState } from "react";

import { ApprovalChain, type Decide } from "@/components/case/chain";
import {
  ClosedInScope,
  Flags,
  ImpactBlock,
  RecommendationBlock,
  contractLines,
} from "@/components/case/decision";
import { AwaitingDocuments } from "@/components/case/documents";
import { LegalRefusal } from "@/components/case/legal-refusal";
import { RequestZone } from "@/components/case/request-zone";
import { NextStep } from "@/components/case/next-step";
import { VoBlock } from "@/components/case/vo-block";
import { Trace, buildRows } from "@/components/case/trace";
import { Empty, ErrorState, Field, Loading, TermsKey } from "@/components/file";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import {
  api,
  ApiError,
  type ChangeRequest,
  type ChangeRequestResponse,
  type Contract,
  type LedgerResponse,
  type TraceResponse,
} from "@/lib/api";
import { useContracts, useCurrentContract } from "@/lib/contracts";
import { formatDate } from "@/lib/format";
import {
  KIND,
  STATE_LABEL,
  STATE_TONE,
  errorMessage,
  kindFull,
  type Term,
} from "@/lib/labels";
import {
  readCompliance,
  readDocuments,
  readImpact,
  readNarrative,
  stageOf,
} from "@/lib/payload";
import { useT } from "@/lib/prefs";
import { useSession } from "@/lib/session";
import { useResource } from "@/lib/use-resource";

const REVEAL_MS = 140;
const ANALYSABLE = new Set(["RECEIVED", "AWAITING_DOCUMENTS", "REVISION_REQUESTED"]);

export default function CaseFilePage() {
  const t = useT();
  return (
    <Suspense fallback={<Shell><Loading label={t.case.opening} /></Shell>}>
      <CaseFileRoute />
    </Suspense>
  );
}

function Shell({ children }: { children: React.ReactNode }) {
  return <div className="mx-auto max-w-[90rem] px-4 pb-16 md:px-8">{children}</div>;
}

function CaseFileRoute() {
  const t = useT();
  const params = useParams<{ crId: string }>();
  const crId = decodeURIComponent(params.crId);
  const { id, contract } = useCurrentContract();
  const contracts = useContracts();

  const detail = useResource((s) => api.changeRequest(crId, s), [crId]);
  const trace = useResource((s) => api.trace(crId, s), [crId]);

  const back = id ? `/contracts/${encodeURIComponent(id)}` : "/";

  if (detail.status === "error" || contracts.status === "error") {
    return (
      <Shell>
        <div className="pt-6">
          <ErrorState
            error={detail.error ?? contracts.error}
            what={t.case.whatFile}
            onRetry={() => {
              detail.reload();
              contracts.reload();
            }}
          />
          <Link href={back} className={buttonVariants({ variant: "link" }) + " mt-4"}>
            {t.case.backToRegister}
          </Link>
        </div>
      </Shell>
    );
  }
  if (detail.status === "loading" || !contract) {
    if (contracts.status === "ready" && !contract) {
      return (
        <Shell>
          <div className="pt-6">
            <Empty title={t.case.noContract(id ?? "")}>{t.case.chooseContract}</Empty>
          </div>
        </Shell>
      );
    }
    return (
      <Shell>
        <Loading label={t.case.opening} rows={6} />
      </Shell>
    );
  }
  return (
    <CaseFile
      contract={contract}
      data={detail.data}
      setData={detail.set}
      trace={trace.status === "ready" ? trace.data : null}
      traceError={trace.status === "error" ? trace.error : null}
      reloadTrace={trace.reload}
      setTrace={trace.set}
    />
  );
}

function CaseFile({
  contract,
  data,
  setData,
  trace,
  traceError,
  reloadTrace,
  setTrace,
}: {
  contract: Contract;
  data: ChangeRequestResponse;
  setData: (d: ChangeRequestResponse) => void;
  trace: TraceResponse | null;
  traceError: unknown;
  reloadTrace: () => void;
  setTrace: (t: TraceResponse) => void;
}) {
  const t = useT();
  const { request, chain } = data;
  const state = request.state ?? "RECEIVED";
  const { persona } = useSession();
  const router = useRouter();
  const search = useSearchParams();
  const reduce = useReducedMotion();

  const [running, setRunning] = useState(false);
  const [revealed, setRevealed] = useState(11);
  const [actionError, setActionError] = useState<string | null>(null);
  const [justSigned, setJustSigned] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [refusal, setRefusal] = useState<{ articles: string[]; ledger: LedgerResponse | null } | null>(null);
  const autoRan = useRef(false);

  // Reveal stages one by one once the analysis response has landed.
  useEffect(() => {
    if (running || revealed >= 7) return;
    const timer = window.setTimeout(() => setRevealed((n) => n + 1), REVEAL_MS);
    return () => window.clearTimeout(timer);
  }, [running, revealed]);

  const analyse = useCallback(async () => {
    setActionError(null);
    setRunning(true);
    setRevealed(0);
    try {
      const result = await api.analyse(request.id);
      setData({ request: result.request, chain: result.chain });
      setTrace({
        cr_id: result.request.id,
        stages: result.trace,
        total_duration_ms: result.trace.reduce((sum, s) => sum + s.duration_ms, 0),
      });
      setRunning(false);
      setRevealed(reduce ? 11 : 0);
    } catch (e) {
      setRunning(false);
      setRevealed(11);
      setActionError(t.case.analysisFailed(errorMessage(e)));
    }
  }, [request.id, setData, setTrace, reduce, t]);

  // Arriving from the new-request form with ?run=1 starts the analysis here.
  useEffect(() => {
    if (autoRan.current || search.get("run") !== "1") return;
    autoRan.current = true;
    router.replace(
      `/contracts/${encodeURIComponent(contract.id)}/requests/${encodeURIComponent(request.id)}`,
      { scroll: false },
    );
    // Started from a task, not the effect body: the analysis is an external
    // call. No cleanup on purpose, so StrictMode's remount cannot cancel it.
    if (ANALYSABLE.has(state)) window.setTimeout(() => void analyse(), 0);
  }, [search, state, analyse, router, contract.id, request.id]);

  async function startApproval() {
    setActionError(null);
    setBusy(true);
    try {
      setData(await api.startApproval(request.id));
      reloadTrace();
    } catch (e) {
      setActionError(t.case.approvalFailed(errorMessage(e)));
    } finally {
      setBusy(false);
    }
  }

  const decide: Decide = async (step, decision, decidedBy, reason) => {
    setActionError(null);
    setRefusal(null);
    try {
      const result = await api.decide(request.id, {
        party: persona.party,
        role: persona.role,
        decided_by: decidedBy,
        decision,
        reason,
      });
      setData(result);
      if (decision === "APPROVED") setJustSigned(step.position);
      reloadTrace();
      return true;
    } catch (e) {
      if (e instanceof ApiError && e.code === "LEGAL_CAP_EXCEEDED") {
        // The refusal panel shows the arithmetic from the ledger's own values.
        setRefusal({ articles: e.articles, ledger: null });
        try {
          const ledger = await api.ledger(contract.id);
          setRefusal({ articles: e.articles, ledger });
        } catch {
          // The panel still states the refusal and the article without numbers.
        }
        return false;
      }
      setActionError(t.case.decisionFailed(errorMessage(e)));
      return false;
    }
  };

  const stages = trace?.stages ?? [];
  const rows = buildRows(stages, request, chain);
  const settled = !running && revealed >= 7;
  const orchestrator = stageOf(trace, "ORCHESTRATOR");
  const narrative = readNarrative(orchestrator);
  const compliance = readCompliance(stageOf(trace, "RISK_COMPLIANCE"));
  const impact = readImpact(stageOf(trace, "COST_SCHEDULE_IMPACT"));
  const documents = readDocuments(stageOf(trace, "DOCUMENT_VALIDATION"));
  // The recommendation rests on AI stages; if any of them was a recorded
  // output rather than a live call, the recommendation says so too.
  const recorded = stages.some((s) => s.actor_type === "AI" && s.recorded);

  const terms: Term[] = ["CR"];
  const abbr = request.kind ? KIND[request.kind].abbr : null;
  if (abbr === "PCR" || abbr === "NCR") terms.push(abbr);
  if (["APPROVED", "VO_ISSUED", "IN_EXECUTION", "CLOSED"].includes(state)) terms.push("VO");

  return (
    <Shell>
      {/* Case header */}
      <header className="rule-double grid gap-3 pt-6 pb-5 md:grid-cols-[1fr_auto] md:items-end">
        <div>
          <Link
            href={`/contracts/${encodeURIComponent(contract.id)}`}
            className={buttonVariants({ variant: "outline", size: "sm", className: "mb-3 print:hidden" })}
            data-back-to-contract
          >
            {t.case.backToContract}
          </Link>
          <nav aria-label={t.case.breadcrumb} className="text-xs text-ink-muted">
            <Link href={`/contracts/${encodeURIComponent(contract.id)}`} className="underline-offset-4 hover:underline">
              {t.case.contractRegister} <span className="ref">{contract.id}</span>
            </Link>
          </nav>
          <h1 className="mt-1 flex flex-wrap items-baseline gap-x-4 gap-y-1">
            <span className="ref text-2xl font-semibold">{request.id}</span>
            <span className="text-lg font-medium">{kindFull(request.kind)}</span>
          </h1>
          <div className="mt-2">
            <TermsKey terms={terms} />
          </div>
        </div>
        <dl className="flex flex-wrap items-end gap-x-6 gap-y-2">
          <Field label={t.case.submittedOn}>{formatDate(request.submitted_at)}</Field>
          <Field label={t.case.state}>
            <Badge variant={STATE_TONE[state]} className="text-sm">
              {running ? t.case.analysing : STATE_LABEL[state]}
            </Badge>
          </Field>
        </dl>
      </header>

      {actionError && (
        <p role="alert" className="mt-4 border-s-4 border-legal bg-legal-wash px-4 py-3 text-sm">
          {actionError}
        </p>
      )}

      <div className="mt-6 grid grid-cols-1 gap-y-10 lg:grid-cols-[minmax(0,30fr)_minmax(0,34fr)_minmax(0,36fr)] lg:gap-x-8">
        {/* First zone (start side): the request. Last on narrow screens. */}
        <div className="order-3 lg:order-none">
          <RequestZone request={request} contract={contract} documents={documents} />
        </div>

        {/* Middle zone: the trace. */}
        <div className="order-2 lg:order-none lg:border-x lg:border-rule lg:px-8">
          {traceError ? (
            <ErrorState error={traceError} what={t.case.whatTrace} onRetry={reloadTrace} />
          ) : !trace && !running ? (
            <Loading label={t.case.loadingTrace} rows={7} />
          ) : (
            <Trace
              rows={rows}
              running={running}
              revealed={revealed}
              totalMs={trace && stages.length ? trace.total_duration_ms : null}
            />
          )}
        </div>

        {/* Last zone (end side): decision. First on narrow screens. */}
        <div className="order-1 space-y-6 lg:order-none">
          {settled && state === "RECOMMENDED" && data.chain.length > 0 && (
            <NextStep
              id="start-approval"
              actions={
                <Button onClick={startApproval} disabled={busy}>
                  {busy ? t.case.sending : t.case.startApproval}
                </Button>
              }
            >
              {t.case.nextStartApproval}
              <span className="mt-1 block text-xs text-ink-muted">{t.case.startApprovalNote}</span>
            </NextStep>
          )}
          {settled && (
            <VoBlock
              contractId={contract.id}
              request={request}
              voId={data.variation_order_id ?? null}
              onIssued={(next) => {
                setData(next);
                reloadTrace();
              }}
            />
          )}
          <DecisionZone
            contract={contract}
            request={request}
            data={data}
            running={running}
            settled={settled}
            narrative={narrative}
            compliance={compliance}
            impact={impact}
            documents={documents}
            recorded={recorded}
            persona={persona}
            justSigned={justSigned}
            refusal={refusal}
            onAnalyse={analyse}
            onSupplied={setData}
            onDecide={decide}
          />
        </div>
      </div>
    </Shell>
  );
}

function DecisionZone({
  contract,
  request,
  data,
  running,
  settled,
  narrative,
  compliance,
  impact,
  documents,
  recorded,
  persona,
  justSigned,
  refusal,
  onAnalyse,
  onSupplied,
  onDecide,
}: {
  contract: Contract;
  request: ChangeRequest;
  data: ChangeRequestResponse;
  running: boolean;
  settled: boolean;
  narrative: ReturnType<typeof readNarrative>;
  compliance: ReturnType<typeof readCompliance>;
  impact: ReturnType<typeof readImpact>;
  documents: ReturnType<typeof readDocuments>;
  recorded: boolean;
  persona: ReturnType<typeof useSession>["persona"];
  justSigned: number | null;
  refusal: { articles: string[]; ledger: LedgerResponse | null } | null;
  onAnalyse: () => Promise<void> | void;
  onSupplied: (data: ChangeRequestResponse) => void;
  onDecide: Decide;
}) {
  const t = useT();
  const state = request.state ?? "RECEIVED";

  if (running || !settled) {
    return (
      <section className="border-t-2 border-ink pt-4" aria-live="polite">
        <h2 className="text-xs font-medium text-ink-muted">{t.case.agentRecommendation}</h2>
        <p className="mt-1 font-doc text-xl">{t.case.agentAnalysingNow}</p>
        <p className="mt-2 text-sm text-ink-muted">{t.case.analysingNote}</p>
      </section>
    );
  }

  if (state === "RECEIVED" || state === "REVISION_REQUESTED") {
    const revision = data.chain.find((s) => s.decision === "REVISION_REQUESTED");
    return (
      <section className="border-t-2 border-ink pt-4">
        <h2 className="font-doc text-xl font-semibold">
          {state === "REVISION_REQUESTED" ? t.case.revisionRequested : t.case.notAnalysed}
        </h2>
        {revision?.reason && (
          <p dir="auto" className="mt-2 border-s-2 border-amber ps-3 text-start font-doc text-sm">
            {revision.reason}
          </p>
        )}
        <p className="mt-2 text-sm text-ink-muted">{t.case.sevenStages}</p>
        <Button className="mt-4" size="lg" onClick={onAnalyse}>
          {t.case.analyse}
        </Button>
      </section>
    );
  }

  if (state === "AWAITING_DOCUMENTS") {
    return (
      <AwaitingDocuments
        request={request}
        documents={documents}
        persona={persona}
        onSupplied={onSupplied}
        onAnalyse={onAnalyse}
      />
    );
  }

  if (state === "CLOSED_IN_SCOPE") {
    return <ClosedInScope lines={contractLines(contract, request)} />;
  }

  const inApproval = state === "IN_APPROVAL";

  return (
    <>
      <RecommendationBlock request={request} narrative={narrative} recorded={recorded} />
      <Flags request={request} compliance={compliance} impact={impact} />
      <ImpactBlock request={request} impact={impact} compliance={compliance} />

      <section aria-labelledby="chain" className="rule-double-top pt-4">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h2 id="chain" className="text-lg font-semibold">{t.case.approvalChain}</h2>
          <span className="text-xs text-ink-muted">
            {t.case.signaturesInOrder(data.chain.length)}
          </span>
        </div>
        <StateNote state={state} />
        {data.chain.length === 0 ? (
          <p className="mt-2 text-sm text-ink-muted">{t.case.noChain}</p>
        ) : (
          <div className="mt-2">
            <ApprovalChain
              chain={data.chain}
              contractType={contract.contract_type}
              persona={persona}
              active={inApproval}
              articleRefs={compliance.legal?.articleRefs ?? []}
              justSigned={justSigned}
              onDecide={onDecide}
            />
          </div>
        )}
        {refusal && (
          <LegalRefusal request={request} articles={refusal.articles} ledger={refusal.ledger} />
        )}
      </section>
    </>
  );
}

function StateNote({ state }: { state: string }) {
  const t = useT();
  if (state === "APPROVED") {
    return (
      <p className="mt-2 border-s-4 border-seal bg-seal-wash px-3 py-2 text-sm text-seal">
        {t.case.approvedNote}
      </p>
    );
  }
  if (state === "REJECTED") {
    return (
      <p className="mt-2 border-s-4 border-legal bg-legal-wash px-3 py-2 text-sm text-legal">
        {t.case.rejectedNote}
      </p>
    );
  }
  return null;
}
