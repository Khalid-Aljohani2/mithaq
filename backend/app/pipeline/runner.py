"""Runs stages 1 to 7 and produces the trace (FR-15, FR-18).

Pure with respect to storage: it takes a contract, a ledger and a change
request, and returns a result. It writes nothing. The service layer decides
what to persist, which is what keeps the AI stages structurally unable to
change state (NFR-15).

Each stage is timed and recorded as a named agent, so the trace shows which
component said what rather than one opaque answer.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal

from app.analysis.provider import AnalysisProvider
from app.analysis.schemas import (
    BreakdownLineView,
    IntakeInput,
    IntakeOutput,
    NarrativeInput,
    NarrativeOutput,
    RiskInput,
    RiskOutput,
    ScopeInput,
    ScopeOutput,
    TechnicalInput,
    TechnicalOutput,
)
from app.domain.change_request import ApprovalStep, ChangeRequest, StageResult
from app.domain.enums import (
    ActorType,
    ChangeKind,
    CRState,
    ImpactType,
    Recommendation,
    Stage,
    stage_number,
)
from app.domain.models import ChangeLedger, ChangeOrder, Contract
from app.pipeline.approvals import ChainFacts, build_chain
from app.pipeline.costing import CostImpact, compute_impact
from app.pipeline.decisions import Decision, decide
from app.pipeline.documents import DocumentCheck, check_documents
from app.pipeline.limits import (
    LegalCheck,
    PolicyCheck,
    check_article_67,
    check_policy,
    to_ledger_entries,
)

STATUS_OK = "OK"
STATUS_BLOCKED = "BLOCKED"
STATUS_SKIPPED = "SKIPPED"


@dataclass
class PipelineResult:
    """Everything one analysis run produced."""

    request: ChangeRequest
    stages: list[StageResult] = field(default_factory=list)
    chain: tuple[ApprovalStep, ...] = ()
    ledger_entries: tuple[ChangeOrder, ...] = ()
    decision: Decision | None = None
    narrative: NarrativeOutput | None = None
    documents: DocumentCheck | None = None
    impact: CostImpact | None = None
    policy: PolicyCheck | None = None
    legal: LegalCheck | None = None


class _Clock:
    """Monotonic-enough timing that still yields real timestamps."""

    def __init__(self) -> None:
        self.now = datetime.now(UTC)

    def tick(self) -> datetime:
        self.now = datetime.now(UTC)
        return self.now


def _record(
    result: PipelineResult,
    stage: Stage,
    actor: ActorType,
    started: datetime,
    finished: datetime,
    status: str,
    summary_en: str,
    summary_ar: str = "",
    payload: dict[str, object] | None = None,
    provider: str | None = None,
    recorded: bool = False,
) -> None:
    result.stages.append(
        StageResult(
            cr_id=result.request.id,
            stage=stage,
            stage_no=stage_number(stage),
            actor_type=actor,
            provider=provider,
            recorded=recorded,
            started_at=started,
            finished_at=finished,
            duration_ms=max(0, int((finished - started).total_seconds() * 1000)),
            status=status,
            summary_en=summary_en,
            summary_ar=summary_ar,
            payload=payload or {},
        )
    )


def _breakdown_views(contract: Contract) -> tuple[BreakdownLineView, ...]:
    """The read-only view a model is given. No rates: it never prices anything."""
    return tuple(
        BreakdownLineView(
            id=line.id,
            description_ar=line.description_ar,
            unit_ar=line.unit_ar,
            approved_product_ar=line.approved_product_ar,
            restrictions_ar=line.restrictions_ar,
        )
        for line in contract.breakdown
    )


def run_analysis(
    contract: Contract,
    ledger: ChangeLedger,
    request: ChangeRequest,
    provider: AnalysisProvider,
    cumulative_cost_before: Decimal,
    cumulative_days_before: int,
) -> PipelineResult:
    """Run stages 1 to 7 over one change request.

    Returns the result; persisting it is the caller's job. Stage 8 onwards are
    driven by humans and live in the service layer.
    """
    result = PipelineResult(request=request)
    clock = _Clock()

    # ---- Stage 1: Intake (AI) ------------------------------------------
    started = clock.tick()
    intake: IntakeOutput = provider.intake(
        IntakeInput(
            cr_id=request.id,
            body_ar=request.body_ar,
            attachments=request.attachments,
            contract_title_ar=contract.title_ar,
        )
    )
    _record(
        result,
        Stage.INTAKE,
        ActorType.AI,
        started,
        clock.tick(),
        STATUS_OK,
        f"Extracted the request and its impact type ({intake.impact_type.value}).",
        intake.requested_change_ar,
        intake.model_dump(mode="json"),
        provider.name,
        intake.recorded,
    )

    # ---- Stage 2: Document validation (code) ---------------------------
    started = clock.tick()
    documents = check_documents(intake.impact_type, request.attachments)
    result.documents = documents
    _record(
        result,
        Stage.DOCUMENT_VALIDATION,
        ActorType.CODE,
        started,
        clock.tick(),
        STATUS_OK if documents.complete else STATUS_BLOCKED,
        documents.summary_en,
        documents.gap_list_ar,
        {
            "required": list(documents.required),
            "provided": list(documents.provided),
            "missing": list(documents.missing),
            "complete": documents.complete,
        },
    )

    if not documents.complete:
        # A non-commitment action: ask for the paperwork, decide nothing.
        result.request = request.model_copy(
            update={
                "state": CRState.AWAITING_DOCUMENTS,
                "impact_type": intake.impact_type,
                "recommendation": Recommendation.REQUEST_REVISION,
                "confidence": intake.confidence,
            }
        )
        return result

    # ---- Stage 3: Contract and scope analysis (AI) ---------------------
    started = clock.tick()
    scope: ScopeOutput = provider.scope_analysis(
        ScopeInput(cr_id=request.id, body_ar=request.body_ar, breakdown=_breakdown_views(contract))
    )
    _record(
        result,
        Stage.SCOPE_ANALYSIS,
        ActorType.AI,
        started,
        clock.tick(),
        STATUS_OK,
        f"in_scope={scope.in_scope}, classified as {scope.kind.value}.",
        scope.reasoning_ar,
        scope.model_dump(mode="json"),
        provider.name,
        scope.recorded,
    )

    # ---- Stage 4: Technical assessment (AI) ----------------------------
    started = clock.tick()
    affected = tuple(
        view for view in _breakdown_views(contract) if view.id in scope.matched_line_ids
    )
    technical: TechnicalOutput = provider.technical_assessment(
        TechnicalInput(cr_id=request.id, body_ar=request.body_ar, affected_lines=affected)
    )
    _record(
        result,
        Stage.TECHNICAL_ASSESSMENT,
        ActorType.AI,
        started,
        clock.tick(),
        STATUS_OK,
        f"changes_approved_product={technical.changes_approved_product}.",
        technical.reasoning_ar,
        technical.model_dump(mode="json"),
        provider.name,
        technical.recorded,
    )

    # ---- Stage 5: Cost and schedule impact (code) ----------------------
    started = clock.tick()
    impact = compute_impact(contract, request, scope)
    result.impact = impact
    _record(
        result,
        Stage.COST_SCHEDULE_IMPACT,
        ActorType.CODE,
        started,
        clock.tick(),
        STATUS_OK,
        f"Cost impact {impact.cost_impact} SAR, {impact.time_impact_days} days.",
        "",
        {
            "cost_impact": str(impact.cost_impact),
            "added_value": str(impact.added_value),
            "removed_value": str(impact.removed_value),
            "time_impact_days": impact.time_impact_days,
            "impact_type": impact.impact_type.value,
            "rate_human_entered": impact.rate_human_entered,
            "unit_rate_flagged": impact.unit_rate_flagged,
            "rate_checks": [
                {
                    "line_id": check.line_id,
                    "contract_rate": str(check.contract_rate),
                    "proposed_rate": str(check.proposed_rate),
                    "deviation_pct": str(check.deviation_pct),
                    "cap_pct": str(check.cap_pct),
                    "flagged": check.flagged,
                }
                for check in impact.rate_checks
            ],
            "notes_en": list(impact.notes_en),
        },
    )

    # ---- Stage 6: Risk and compliance (code findings + AI narrative) ---
    started = clock.tick()
    entries = to_ledger_entries(request, scope.kind, impact, scope.matched_line_ids, clock.now)
    policy = check_policy(contract, cumulative_cost_before, cumulative_days_before, impact)
    legal = check_article_67(contract, ledger, entries)
    result.ledger_entries = entries
    result.policy = policy
    result.legal = legal

    risk: RiskOutput = provider.risk_assessment(
        RiskInput(
            cr_id=request.id,
            body_ar=request.body_ar,
            kind=scope.kind,
            cost_impact=impact.cost_impact,
            time_impact_days=impact.time_impact_days,
            legal_findings_en=legal.findings_en,
            policy_findings_en=policy.findings_en,
        )
    )
    _record(
        result,
        Stage.RISK_COMPLIANCE,
        ActorType.AI,
        started,
        clock.tick(),
        STATUS_BLOCKED if legal.blocked else STATUS_OK,
        f"Risk {risk.overall_risk_level}; policy_exceeded={policy.exception_required}, "
        f"legally_blocked={legal.blocked}.",
        risk.compliance_risk_ar,
        {
            "risk": risk.model_dump(mode="json"),
            "policy": {
                "cost_after_pct": str(policy.cost_after_pct),
                "cost_cap_pct": str(policy.cost_cap_pct),
                "cost_exceeded": policy.cost_exceeded,
                "time_after_pct": str(policy.time_after_pct),
                "time_cap_pct": str(policy.time_cap_pct),
                "time_exceeded": policy.time_exceeded,
                "exception_role": policy.exception_role,
                "findings_en": list(policy.findings_en),
            },
            "legal": {
                "applies": legal.applies,
                "blocked": legal.blocked,
                "requires_contractor_consent": legal.requires_contractor_consent,
                "article_refs": list(legal.article_refs),
                "findings_en": list(legal.findings_en),
            },
        },
        provider.name,
        risk.recorded,
    )

    # ---- Stage 7: Orchestrator (code decides, AI narrates) -------------
    started = clock.tick()
    decision = decide(
        scope,
        technical,
        impact,
        documents,
        policy,
        legal,
        (intake.confidence, scope.confidence, technical.confidence, risk.confidence),
    )
    result.decision = decision

    updated = request.model_copy(
        update={
            "kind": scope.kind,
            "impact_type": impact.impact_type
            if impact.impact_type != ImpactType.NONE
            else intake.impact_type,
            "matched_line_ids": scope.matched_line_ids,
            "cost_impact": impact.cost_impact,
            "time_impact_days": impact.time_impact_days,
            "recommendation": decision.recommendation,
            "confidence": decision.confidence,
            "changes_approved_product": technical.changes_approved_product,
            "policy_exception_required": decision.policy_exception_required,
            "needs_legal_review": decision.needs_legal_review,
            "legally_blocked": decision.legally_blocked,
            "unit_rate_flagged": impact.unit_rate_flagged,
            "rate_human_entered": impact.rate_human_entered,
            "state": CRState.CLOSED_IN_SCOPE
            if decision.recommendation is Recommendation.CLOSE_IN_SCOPE
            else CRState.RECOMMENDED,
            "closed_reason": "in scope"
            if decision.recommendation is Recommendation.CLOSE_IN_SCOPE
            else None,
        }
    )

    chain: tuple[ApprovalStep, ...] = ()
    if decision.recommendation is not Recommendation.CLOSE_IN_SCOPE:
        chain = build_chain(
            updated,
            ChainFacts.from_request(
                updated, contractor_consent_required=legal.requires_contractor_consent
            ),
            clock.now,
        )
    result.chain = chain

    narrative = provider.recommendation_narrative(
        NarrativeInput(
            cr_id=request.id,
            recommendation=decision.recommendation.value,
            reason_codes=decision.reason_codes,
            cost_impact=impact.cost_impact,
            time_impact_days=impact.time_impact_days,
            chain_roles=tuple(f"{step.party.value}:{step.role.value}" for step in chain),
        )
    )
    result.narrative = narrative
    result.request = updated

    _record(
        result,
        Stage.ORCHESTRATOR,
        ActorType.CODE,
        started,
        clock.tick(),
        STATUS_BLOCKED if decision.legally_blocked else STATUS_OK,
        f"Recommendation {decision.recommendation.value} "
        f"(confidence {decision.confidence}); chain of {len(chain)}.",
        narrative.summary_ar,
        {
            "recommendation": decision.recommendation.value,
            "reason_codes": list(decision.reason_codes),
            "confidence": str(decision.confidence),
            "conflicts": list(decision.conflicts),
            "chain": [
                {
                    "position": step.position,
                    "party": step.party.value,
                    "role": step.role.value,
                    "reason_code": step.reason_code,
                }
                for step in chain
            ],
            "narrative": narrative.model_dump(mode="json"),
            "narrative_provider": provider.name,
        },
    )
    return result


def is_in_scope(result: PipelineResult) -> bool:
    """True when the run concluded the request needs no change order."""
    return result.request.kind is ChangeKind.IN_SCOPE
