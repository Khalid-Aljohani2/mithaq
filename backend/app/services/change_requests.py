"""Change-request orchestration: the workflow around the pipeline.

Layering (NFR-11): routers do HTTP, this module does the workflow, the pipeline
does analysis, the rules engine does the law, the repository does storage.

NFR-15 lives here in practice. Every state change goes through
``state_machine.transition`` with an explicit actor, and the actor is
``HUMAN`` or ``CODE`` - never ``AI``. The pipeline returns evidence; this
module is what acts on it.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.analysis.provider import AnalysisProvider
from app.analysis.schemas import VODraftInput
from app.config import get_settings
from app.domain.audit import AuditAction, AuditEvent
from app.domain.change_request import (
    ApprovalStep,
    ChangeRequest,
    ExecutionRecord,
    Notification,
    Signature,
    StageResult,
    VariationOrder,
)
from app.domain.durations import waited_phrase
from app.domain.enums import (
    PENDING_STATUSES,
    ActorType,
    ApprovalDecision,
    ChangeKind,
    CRState,
    NotificationKind,
    OrderStatus,
    Party,
    Recommendation,
    Role,
    Stage,
    stage_number,
)
from app.domain.models import ChangeOrder, Contract
from app.domain.money import money
from app.domain.state_machine import transition
from app.pipeline.approvals import chain_is_complete, current_step
from app.pipeline.limits import check_article_67, cited_articles, ledger_entries_for
from app.pipeline.runner import PipelineResult, run_analysis
from app.policy.loader import get_policy
from app.repositories.base import ContractRepository


class WorkflowError(Exception):
    """A workflow failure carrying a stable code."""

    def __init__(self, code: str, message: str, articles: tuple[str, ...] = ()) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        #: Articles the refusal rests on, when it rests on the law. Carried to
        #: the client rather than buried in prose: a party told their change
        #: order is refused is entitled to the provision it was refused under
        #: (NFR-02).
        self.articles = articles


class NotFoundError(WorkflowError):
    """The contract, request or variation order does not exist."""


class WrongRoleError(WorkflowError):
    """This party and role may not act at this point in the chain (FR-10)."""


class InvalidStateError(WorkflowError):
    """The request is not in a state where this action makes sense."""


class LegallyBlockedError(WorkflowError):
    """Approving this would push the contract past an Article 67 cap.

    Raised at the *final* approval, not at the first, because that is the
    moment the commitment is made and therefore the moment the cumulative
    position has to be true. A request that was inside every cap when it
    entered the chain can be outside them by the time the chain finishes, if
    something else was approved in between - which is exactly the gap a
    cumulative ledger exists to close (FR-10, NFR-02).
    """


@dataclass(frozen=True)
class RequestInput:
    """What a requester submits (FR-03)."""

    requester_name: str
    requester_party: Party
    body_ar: str
    attachments: tuple[str, ...] = ()
    human_entered_amount: Decimal | None = None
    human_entered_unit_rate: Decimal | None = None
    human_entered_days: int | None = None


def _require_contract(repo: ContractRepository, contract_id: str) -> Contract:
    contract = repo.get_contract(contract_id)
    if contract is None:
        raise NotFoundError("CONTRACT_NOT_FOUND", f"contract {contract_id} not found")
    return contract


def _require_request(repo: ContractRepository, cr_id: str) -> ChangeRequest:
    request = repo.get_change_request(cr_id)
    if request is None:
        raise NotFoundError("CR_NOT_FOUND", f"change request {cr_id} not found")
    return request


def _audit(
    repo: ContractRepository,
    request: ChangeRequest,
    action: AuditAction,
    actor_role: str,
    previous: CRState,
    new: CRState,
    now: datetime,
    reason: str | None = None,
    actor_party: str | None = None,
    actor_name: str | None = None,
) -> None:
    repo.append_audit(
        AuditEvent(
            occurred_at=now,
            actor_role=actor_role,
            actor_party=actor_party,
            actor_name=actor_name,
            action=action,
            entity_type="change_request",
            entity_id=request.id,
            contract_id=request.contract_id,
            previous_state=previous,
            new_state=new,
            reason=reason,
        )
    )


def _notify(
    repo: ContractRepository,
    request: ChangeRequest,
    party: Party,
    role: Role,
    kind: NotificationKind,
    message_ar: str,
    message_en: str,
    now: datetime,
    is_reminder: bool = False,
) -> None:
    repo.append_notification(
        Notification(
            cr_id=request.id,
            contract_id=request.contract_id,
            party=party,
            role=role,
            kind=kind,
            message_ar=message_ar,
            message_en=message_en,
            created_at=now,
            is_reminder=is_reminder,
        )
    )


def cumulative_totals(repo: ContractRepository, contract_id: str) -> tuple[Decimal, int]:
    """Cost and days already committed by approved requests on this contract.

    Only requests that reached APPROVED or beyond count. A recommendation is
    not a commitment.
    """
    committed = {CRState.APPROVED, CRState.VO_ISSUED, CRState.IN_EXECUTION, CRState.CLOSED}
    cost = Decimal("0")
    days = 0
    for request in repo.list_change_requests(contract_id):
        if request.state in committed:
            cost += request.cost_impact or Decimal("0")
            days += request.time_impact_days or 0
    return cost, days


def pending_totals(repo: ContractRepository, contract_id: str) -> tuple[Decimal, int]:
    """Cost and days that would be committed if everything in flight is approved.

    Reported beside the committed figures rather than added to them: a request
    under consideration must never silently consume headroom, which is the same
    rule the Article 67 engine follows for PENDING orders (FR-10).
    """
    # IN_APPROVAL only, so this agrees with the Article 67 ledger: entries are
    # written when a request enters approval, and a request that is merely
    # recommended has none. One record, one meaning of "in flight".
    in_flight = {CRState.IN_APPROVAL}
    cost = Decimal("0")
    days = 0
    for request in repo.list_change_requests(contract_id):
        if request.state in in_flight:
            cost += request.cost_impact or Decimal("0")
            days += request.time_impact_days or 0
    return cost, days


# ---------------------------------------------------------------------------
# Stage 1-7: submit and analyse
# ---------------------------------------------------------------------------


def submit_request(
    repo: ContractRepository,
    contract_id: str,
    payload: RequestInput,
    now: datetime,
) -> ChangeRequest:
    """Record a newly received change request (FR-03)."""
    _require_contract(repo, contract_id)
    request = ChangeRequest(
        id=repo.next_change_request_id(contract_id),
        contract_id=contract_id,
        requester_name=payload.requester_name,
        requester_party=payload.requester_party,
        submitted_at=now,
        body_ar=payload.body_ar,
        attachments=payload.attachments,
        human_entered_amount=payload.human_entered_amount,
        human_entered_unit_rate=payload.human_entered_unit_rate,
        human_entered_days=payload.human_entered_days,
        state=CRState.RECEIVED,
    )
    stored = repo.add_change_request(request)
    _audit(
        repo,
        stored,
        AuditAction.CR_RECEIVED,
        Role.PROJECT_MANAGER.value,
        CRState.RECEIVED,
        CRState.RECEIVED,
        now,
        actor_party=payload.requester_party.value,
        actor_name=payload.requester_name,
    )
    return stored


def replace_attachments(
    repo: ContractRepository,
    cr_id: str,
    party: Party,
    role: Role,
    submitted_by: str,
    attachments: tuple[str, ...],
    now: datetime,
) -> ChangeRequest:
    """Supply the documents a request was waiting for (FR-04).

    A human action, and only the side that raised the request may take it: the
    other party has no standing to put paperwork into someone else's file, and
    a UI that merely hides the button is not a control (FR-10).

    The attachments are **replaced**, not merged. The requester is answering a
    gap list with the file as it now stands, and a merge would quietly keep a
    document they meant to withdraw.

    The state is left at AWAITING_DOCUMENTS. Supplying documents is not itself
    a claim that the file is complete - stage 2 decides that, on the next run
    of the analysis, which this request is now eligible for again.
    """
    request = _require_request(repo, cr_id)
    if request.state is not CRState.AWAITING_DOCUMENTS:
        raise InvalidStateError(
            "NOT_AWAITING_DOCUMENTS",
            f"change request {cr_id} is in {request.state.value}, not awaiting documents",
        )
    if party is not request.requester_party:
        raise WrongRoleError(
            "WRONG_PARTY",
            f"{party.value} may not supply documents for a request raised by "
            f"{request.requester_party.value}",
        )
    if role is not Role.PROJECT_MANAGER:
        raise WrongRoleError(
            "WRONG_ROLE",
            f"{role.value} may not supply documents; that is the project manager's action",
        )

    stored = repo.replace_change_request(request.model_copy(update={"attachments": attachments}))
    _audit(
        repo,
        stored,
        AuditAction.CR_DOCUMENTS_SUPPLIED,
        role.value,
        CRState.AWAITING_DOCUMENTS,
        CRState.AWAITING_DOCUMENTS,
        now,
        reason=f"{len(attachments)} document(s) supplied",
        actor_party=party.value,
        actor_name=submitted_by,
    )
    return stored


def analyse_request(
    repo: ContractRepository,
    cr_id: str,
    provider: AnalysisProvider,
    now: datetime,
) -> PipelineResult:
    """Run stages 1 to 7 and persist the outcome.

    The pipeline computes; this function decides what to store and drives the
    state change as ``CODE``. An AI stage never reaches the state machine.
    """
    request = _require_request(repo, cr_id)
    if request.state not in {
        CRState.RECEIVED,
        CRState.AWAITING_DOCUMENTS,
        CRState.REVISION_REQUESTED,
    }:
        raise InvalidStateError(
            "NOT_ANALYSABLE",
            f"a change request in {request.state} is not awaiting analysis",
        )

    contract = _require_contract(repo, request.contract_id)
    ledger = repo.get_ledger(request.contract_id)
    cost_before, days_before = cumulative_totals(repo, request.contract_id)

    previous_state = request.state
    result = run_analysis(contract, ledger, request, provider, cost_before, days_before)

    # The pipeline proposes a state; the state machine validates the move.
    target = result.request.state
    # Analysis always starts from IN_ANALYSIS, which is a code-driven move.
    transition(previous_state, CRState.IN_ANALYSIS, ActorType.CODE)
    new_state = transition(CRState.IN_ANALYSIS, target, ActorType.CODE)

    stored = result.request.model_copy(update={"state": new_state})
    repo.replace_change_request(stored)
    repo.append_stage_results(result.stages)
    repo.set_approval_chain(cr_id, result.chain)
    result.request = stored

    _audit(
        repo,
        stored,
        AuditAction.CR_ANALYSED,
        ActorType.CODE.value,
        previous_state,
        new_state,
        now,
        reason=stored.recommendation.value if stored.recommendation else None,
    )

    if new_state is CRState.AWAITING_DOCUMENTS:
        _notify(
            repo,
            stored,
            stored.requester_party,
            Role.PROJECT_MANAGER,
            NotificationKind.DOCUMENTS_REQUIRED,
            result.documents.gap_list_ar if result.documents else "",
            result.documents.summary_en if result.documents else "",
            now,
        )
    elif new_state is CRState.CLOSED_IN_SCOPE:
        _notify(
            repo,
            stored,
            stored.requester_party,
            Role.PROJECT_MANAGER,
            NotificationKind.CR_CLOSED_IN_SCOPE,
            "الطلب مغطى بالعقد الحالي وأُغلق كطلب داخل النطاق.",
            "Closed as in scope: already covered by the contract breakdown.",
            now,
        )
    return result


#: Kinds that put nothing on the ledger: one is not a change, the other is not
#: yet known to be one.
_NO_LEDGER_KINDS = (None, ChangeKind.IN_SCOPE, ChangeKind.UNCLEAR)


def _is_unpriced(request: ChangeRequest) -> bool:
    """True when a request that should have ledger figures does not have them.

    Decided from the request rather than by trying to build the entries:
    ``ChangeOrder`` refuses a financial entry worth nothing, so building them
    would raise a validation error deep in the pipeline and surface as a 500.
    The ledger is right either way - this turns an incomprehensible failure
    into one that says what to do about it.
    """
    if request.kind in _NO_LEDGER_KINDS:
        return False
    return request.added_value is None and request.removed_value is None


def ledger_entries_of(
    repo: ContractRepository, cr_id: str, contract_id: str
) -> tuple[ChangeOrder, ...]:
    """Every ledger entry this change request has put on the contract."""
    return tuple(
        order for order in repo.get_ledger(contract_id).orders if order.change_request_id == cr_id
    )


def _write_pending_entries(
    repo: ContractRepository, request: ChangeRequest, now: datetime
) -> tuple[ChangeOrder, ...]:
    """Put the request's Article 67 entries on the ledger, pending (FR-10).

    Pending means "committed if approved": reported on the ledger so both
    parties can see what is in flight, and counted toward no cumulative total
    until it is actually approved. Nothing here is specific to a government
    contract - a private contract writes the same entries, so the ledger is one
    record of every change to every contract. Article 67 is what is evaluated
    only on government contracts, not what is recorded.

    Entries are written by id, so a revised request that re-enters approval
    replaces its old entries rather than accumulating a second set beside them.
    """
    entries = tuple(
        entry.model_copy(
            update={"status": OrderStatus.PENDING_AUTHORITY_APPROVAL, "created_at": now}
        )
        for entry in ledger_entries_for(request, now)
    )
    for entry in entries:
        if repo.get_change_order(entry.id) is None:
            repo.add_change_order(entry)
        else:
            repo.replace_change_order(entry)
    return entries


def _settle_entries(
    repo: ContractRepository,
    request: ChangeRequest,
    status: OrderStatus,
) -> tuple[ChangeOrder, ...]:
    """Move a request's pending entries to a terminal status.

    Only pending entries move. An entry already approved is part of the
    contract's history and is never rewritten by a later decision.
    """
    settled = [
        repo.replace_change_order(order.model_copy(update={"status": status}))
        for order in ledger_entries_of(repo, request.id, request.contract_id)
        if order.status in PENDING_STATUSES
    ]
    return tuple(settled)


def start_approval(repo: ContractRepository, cr_id: str, now: datetime) -> ChangeRequest:
    """Move a recommended request into its approval chain (FR-10).

    Driven as CODE: entering the chain commits nobody. The decisions inside it
    are what commit, and those are HUMAN.
    """
    request = _require_request(repo, cr_id)
    steps = repo.list_approval_steps(cr_id)
    if not steps:
        raise InvalidStateError("NO_CHAIN", f"change request {cr_id} has no approval chain")

    if _is_unpriced(request):
        # A request analysed before the gross halves were persisted has a net
        # cost_impact and nothing to split it into, so it cannot be put on the
        # ledger. Re-analysing gives it the figures.
        raise InvalidStateError(
            "NOT_PRICED",
            f"change request {cr_id} has no priced ledger figures; re-run the "
            "analysis before starting approval",
        )

    new_state = transition(request.state, CRState.IN_APPROVAL, ActorType.CODE)
    stored = repo.replace_change_request(request.model_copy(update={"state": new_state}))

    # The ledger learns about the request now, as pending. Writing it here
    # rather than at approval means both parties can see what is in flight
    # before it lands, which is the point of a shared ledger.
    _write_pending_entries(repo, stored, now)

    first = steps[0]
    _notify(
        repo,
        stored,
        first.party,
        first.role,
        NotificationKind.APPROVAL_PENDING,
        f"بانتظار اعتمادكم للطلب {stored.id}.",
        f"Change request {stored.id} is awaiting your approval.",
        now,
    )
    _audit(
        repo,
        stored,
        AuditAction.CR_IN_APPROVAL,
        ActorType.CODE.value,
        request.state,
        new_state,
        now,
    )
    return stored


# ---------------------------------------------------------------------------
# Stage 8: the human approval gate (FR-10)
# ---------------------------------------------------------------------------


def _refuse_if_over_a_legal_cap(
    repo: ContractRepository,
    request: ChangeRequest,
    now: datetime,
) -> None:
    """Re-check Article 67 at the moment of final approval (FR-10, NFR-02).

    Stage 6 already checked the caps, but it checked them when the request was
    analysed. Between then and now other requests may have been approved
    against the same contract, and the law counts the cumulative position, not
    the position at the time somebody filled in a form. This is the check that
    makes the ledger mean something: without it a contract can be taken past an
    Article 67 cap by two requests that were each inside it on their own - the
    salami the cap exists to prevent.

    The ledger is read fresh and the request's own pending entries are
    evaluated against it. Pending entries count toward nothing, so this request
    is not counted against itself, and nothing else in flight is counted
    either: only what has actually been approved.

    On a breach nothing is approved. The request is flagged for legal review,
    the reviewer is told, the refusal is audited, and the caller gets the
    article it was refused under. No internal approval lifts a legal cap
    (NFR-16), so there is no "approve anyway" path here by design.
    """
    contract = _require_contract(repo, request.contract_id)
    if not contract.is_government:
        return

    entries = tuple(
        order
        for order in ledger_entries_of(repo, request.id, request.contract_id)
        if order.status in PENDING_STATUSES
    )
    legal = check_article_67(contract, repo.get_ledger(request.contract_id), entries)
    if not legal.blocked:
        return

    articles = legal.blocking_article_refs
    stored = repo.replace_change_request(
        request.model_copy(update={"legally_blocked": True, "needs_legal_review": True})
    )
    _notify(
        repo,
        stored,
        Party.GOVERNMENT_ENTITY,
        Role.LEGAL_ADVISOR,
        NotificationKind.LEGAL_REVIEW_REQUIRED,
        f"تعذّر اعتماد الطلب {stored.id}: تجاوز حدًا نظاميًا ({'، '.join(articles)}).",
        f"Final approval of {stored.id} was refused: it would exceed {', '.join(articles)}.",
        now,
    )
    _audit(
        repo,
        stored,
        AuditAction.CR_LEGAL_CAP_REFUSED,
        ActorType.CODE.value,
        stored.state,
        stored.state,
        now,
        reason="; ".join(legal.findings_en),
    )
    raise LegallyBlockedError(
        "LEGAL_CAP_EXCEEDED",
        "approving this now would exceed a cumulative Article 67 cap: "
        + "; ".join(legal.findings_en),
        articles,
    )


def decide_step(
    repo: ContractRepository,
    cr_id: str,
    party: Party,
    role: Role,
    decided_by: str,
    decision: ApprovalDecision,
    reason: str | None,
    now: datetime,
) -> tuple[ChangeRequest, ApprovalStep]:
    """Record one approver's decision. Only humans reach this (FR-10)."""
    if decision is ApprovalDecision.PENDING:
        raise InvalidStateError("INVALID_DECISION", "PENDING is not a decision")

    request = _require_request(repo, cr_id)
    if request.state is not CRState.IN_APPROVAL:
        raise InvalidStateError(
            "NOT_IN_APPROVAL", f"change request {cr_id} is {request.state}, not in approval"
        )

    steps = tuple(repo.list_approval_steps(cr_id))
    step = current_step(steps)
    if step is None:
        raise InvalidStateError("CHAIN_COMPLETE", f"change request {cr_id} has no pending step")
    if step.party is not party or step.role is not role:
        raise WrongRoleError(
            "WRONG_ROLE",
            f"position {step.position} is for {step.party.value}:{step.role.value}, "
            f"not {party.value}:{role.value}",
        )
    if decision is not ApprovalDecision.APPROVED and not reason:
        raise InvalidStateError(
            "REASON_REQUIRED", "rejecting or returning a request needs a reason"
        )

    # Before anything is written. A final approval that would take the
    # contract past an Article 67 cap is refused here, so no step is recorded
    # as approved and no entry is committed. Checking afterwards would mean
    # undoing a decision that had already been made, and an approval that has
    # to be taken back is not the same thing as one that never happened.
    remaining_after = tuple(
        other if other.position != step.position else step.model_copy(update={"decision": decision})
        for other in steps
    )
    if decision is ApprovalDecision.APPROVED and chain_is_complete(remaining_after):
        _refuse_if_over_a_legal_cap(repo, request, now)

    decided = step.model_copy(
        update={
            "decision": decision,
            "decided_by": decided_by,
            "decided_at": now,
            "reason": reason,
        }
    )
    repo.replace_approval_step(decided)
    remaining = tuple(repo.list_approval_steps(cr_id))

    previous = request.state
    if decision is ApprovalDecision.REJECTED:
        # The entries never counted toward anything; they are closed off so
        # the ledger shows what was asked for and refused, rather than
        # silently losing it.
        _settle_entries(repo, request, OrderStatus.REJECTED)
        new_state = transition(previous, CRState.REJECTED, ActorType.HUMAN)
        action = AuditAction.CR_REJECTED
        kind = NotificationKind.CR_REJECTED
        message_ar = f"تم رفض الطلب {cr_id}. السبب: {reason}"
        message_en = f"Change request {cr_id} was rejected: {reason}"
    elif decision is ApprovalDecision.REVISION_REQUESTED:
        # A revised request is a different request: its figures change, so its
        # entries do. These are closed off now and written again, by the same
        # ids, when the revision re-enters approval.
        _settle_entries(repo, request, OrderStatus.REJECTED)
        new_state = transition(previous, CRState.REVISION_REQUESTED, ActorType.HUMAN)
        action = AuditAction.CR_REVISION_REQUESTED
        kind = NotificationKind.CR_REVISION_REQUESTED
        message_ar = f"طُلب تعديل الطلب {cr_id}. السبب: {reason}"
        message_en = f"Change request {cr_id} needs revision: {reason}"
    elif chain_is_complete(remaining):
        # The commitment is made here, so this is where the ledger entries
        # start counting toward the cumulative totals.
        _settle_entries(repo, request, OrderStatus.APPROVED)
        new_state = transition(previous, CRState.APPROVED, ActorType.HUMAN)
        action = AuditAction.CR_APPROVED
        kind = NotificationKind.APPROVAL_COMPLETED
        message_ar = f"اكتملت الموافقات للطلب {cr_id}."
        message_en = f"Change request {cr_id} is fully approved."
    else:
        new_state = transition(previous, CRState.IN_APPROVAL, ActorType.HUMAN)
        action = AuditAction.CR_STEP_APPROVED
        kind = NotificationKind.APPROVAL_PENDING
        message_ar = ""
        message_en = ""

    updates: dict[str, object] = {"state": new_state}
    if decision is ApprovalDecision.REVISION_REQUESTED:
        updates["revision_count"] = request.revision_count + 1
    stored = repo.replace_change_request(request.model_copy(update=updates))

    _audit(
        repo,
        stored,
        action,
        role.value,
        previous,
        new_state,
        now,
        reason,
        actor_party=party.value,
        actor_name=decided_by,
    )

    if decision is ApprovalDecision.APPROVED and new_state is CRState.IN_APPROVAL:
        nxt = current_step(remaining)
        if nxt is not None:
            _notify(
                repo,
                stored,
                nxt.party,
                nxt.role,
                NotificationKind.APPROVAL_PENDING,
                f"بانتظار اعتمادكم للطلب {stored.id}.",
                f"Change request {stored.id} is awaiting your approval.",
                now,
            )
    elif message_en:
        _notify(
            repo,
            stored,
            stored.requester_party,
            Role.PROJECT_MANAGER,
            kind,
            message_ar,
            message_en,
            now,
        )

    return stored, decided


# ---------------------------------------------------------------------------
# Stage 9: issue the variation order (FR-12)
# ---------------------------------------------------------------------------


def issue_variation_order(
    repo: ContractRepository,
    cr_id: str,
    provider: AnalysisProvider,
    now: datetime,
) -> VariationOrder:
    """Generate the VO after the full chain approves.

    Values and citations are computed; only the Arabic scope prose is drafted
    by the provider, and it cannot change a figure.
    """
    request = _require_request(repo, cr_id)
    if request.state is not CRState.APPROVED:
        raise InvalidStateError(
            "NOT_APPROVED", f"change request {cr_id} is {request.state}, not approved"
        )

    contract = _require_contract(repo, request.contract_id)
    steps = repo.list_approval_steps(cr_id)
    existing = repo.list_variation_orders(request.contract_id)
    number = f"VO-{len(existing) + 1:03d}"

    draft = provider.vo_draft(
        VODraftInput(
            cr_id=cr_id,
            contract_title_ar=contract.title_ar,
            requested_change_ar=request.body_ar,
            cited_line_ids=request.matched_line_ids,
        )
    )

    # Which articles this VO rests on is a question for the regulation file,
    # not for a literal in Python (NFR-02). They are derived from the ledger
    # entries the request actually produces, so a VO never cites an article
    # that had nothing to do with it.
    articles = cited_articles(contract, request)

    vo = VariationOrder(
        id=f"{cr_id}-VO",
        cr_id=cr_id,
        contract_id=request.contract_id,
        number=number,
        issued_at=now,
        scope_ar=draft.scope_ar,
        scope_en=draft.scope_en,
        value=request.cost_impact or Decimal("0"),
        time_extension_days=request.time_impact_days or 0,
        cited_line_ids=request.matched_line_ids,
        cited_articles=articles,
        signatures=tuple(
            Signature(
                party=step.party,
                role=step.role,
                decided_by=step.decided_by or "",
                decided_at=step.decided_at or now,
            )
            for step in steps
            if step.decision is ApprovalDecision.APPROVED
        ),
        recorded=draft.recorded,
    )
    stored_vo = repo.add_variation_order(vo)

    previous = request.state
    new_state = transition(previous, CRState.VO_ISSUED, ActorType.CODE)
    stored = repo.replace_change_request(request.model_copy(update={"state": new_state}))

    repo.append_stage_results(
        [
            StageResult(
                cr_id=cr_id,
                stage=Stage.ISSUE_VO,
                stage_no=stage_number(Stage.ISSUE_VO),
                actor_type=ActorType.CODE,
                provider=provider.name,
                recorded=draft.recorded,
                started_at=now,
                finished_at=now,
                duration_ms=0,
                status="OK",
                summary_en=f"Issued {number} for {money(vo.value)} SAR.",
                summary_ar=draft.scope_ar,
                payload={"vo_id": vo.id, "number": number, "value": str(vo.value)},
            )
        ]
    )
    _audit(repo, stored, AuditAction.VO_ISSUED, ActorType.CODE.value, previous, new_state, now)
    _notify(
        repo,
        stored,
        stored.requester_party,
        Role.PROJECT_MANAGER,
        NotificationKind.VO_ISSUED,
        f"صدر أمر التغيير {number} بقيمة {money(vo.value)} ريال.",
        f"Variation order {number} issued for {money(vo.value)} SAR.",
        now,
    )
    return stored_vo


# ---------------------------------------------------------------------------
# Stage 10: update project records (FR-13)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ProjectRecords:
    """The contract's position after approved changes."""

    contract_id: str
    original_value: Decimal
    approved_change_value: Decimal
    revised_value: Decimal
    original_duration_days: int
    approved_extension_days: int
    revised_duration_days: int
    variation_orders: int


def update_project_records(repo: ContractRepository, contract_id: str) -> ProjectRecords:
    """Recompute the contract baseline from approved requests (FR-13).

    Derived, never accumulated in place: a stored running total can drift out
    of step with the requests behind it, a recomputation cannot.
    """
    contract = _require_contract(repo, contract_id)
    cost, days = cumulative_totals(repo, contract_id)
    return ProjectRecords(
        contract_id=contract_id,
        original_value=contract.original_value,
        approved_change_value=cost,
        revised_value=contract.original_value + cost,
        original_duration_days=contract.original_duration_days,
        approved_extension_days=days,
        revised_duration_days=contract.original_duration_days + days,
        variation_orders=len(repo.list_variation_orders(contract_id)),
    )


# ---------------------------------------------------------------------------
# Stage 11: execution and follow-up (FR-14)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ExecutionInput:
    """Actuals recorded against a variation order."""

    actual_cost: Decimal | None = None
    actual_start: object | None = None
    actual_end: object | None = None
    acceptance_verified: bool = False
    close_out: bool = False
    lessons_learned_ar: str | None = None
    notes_ar: str | None = None


def record_execution(
    repo: ContractRepository,
    vo_id: str,
    payload: ExecutionInput,
    now: datetime,
) -> ExecutionRecord:
    """Record actuals and, when asked, close the request out (FR-14)."""
    vo = repo.get_variation_order(vo_id)
    if vo is None:
        raise NotFoundError("VO_NOT_FOUND", f"variation order {vo_id} not found")
    request = _require_request(repo, vo.cr_id)

    if request.state is CRState.VO_ISSUED:
        new_state = transition(request.state, CRState.IN_EXECUTION, ActorType.HUMAN)
        request = repo.replace_change_request(request.model_copy(update={"state": new_state}))
        _audit(
            repo,
            request,
            AuditAction.EXECUTION_STARTED,
            ActorType.HUMAN.value,
            CRState.VO_ISSUED,
            new_state,
            now,
        )
    elif request.state is not CRState.IN_EXECUTION:
        raise InvalidStateError("NOT_EXECUTABLE", f"change request {request.id} is {request.state}")

    cost_deviation = payload.actual_cost - vo.value if payload.actual_cost is not None else None
    record = ExecutionRecord(
        vo_id=vo_id,
        cr_id=vo.cr_id,
        contract_id=vo.contract_id,
        actual_cost=payload.actual_cost,
        actual_start=payload.actual_start,  # type: ignore[arg-type]
        actual_end=payload.actual_end,  # type: ignore[arg-type]
        cost_deviation=cost_deviation,
        acceptance_verified=payload.acceptance_verified,
        closed_out_at=now if payload.close_out else None,
        lessons_learned_ar=payload.lessons_learned_ar,
        notes_ar=payload.notes_ar,
    )
    stored_record = repo.upsert_execution_record(record)

    if payload.close_out:
        if not payload.acceptance_verified:
            raise InvalidStateError(
                "ACCEPTANCE_REQUIRED",
                "close-out requires verification against the acceptance criteria",
            )
        previous = request.state
        closed = transition(previous, CRState.CLOSED, ActorType.HUMAN)
        request = repo.replace_change_request(request.model_copy(update={"state": closed}))
        _audit(
            repo,
            request,
            AuditAction.CR_CLOSED,
            ActorType.HUMAN.value,
            previous,
            closed,
            now,
        )
    return stored_record


# ---------------------------------------------------------------------------
# Notifications and reminders (FR-11)
# ---------------------------------------------------------------------------


def pending_approval_hours() -> int:
    """How long an approval step may wait before it is reminded about (FR-11).

    Settings win over the policy file when they say anything at all, so a demo
    can set the delay to 0 without editing policy. ``is not None`` rather than
    a truthiness test, because 0 is exactly the value a demo wants and "or"
    would silently discard it.
    """
    override = get_settings().reminder_pending_approval_hours
    return override if override is not None else get_policy().pending_approval_hours


def awaiting_documents_hours() -> int:
    """How long a request may wait on its documents before being reminded.

    Settings win over the policy file when they say anything at all, and 0 is
    a real value, so a demo can show the reminder path without waiting two
    days for one to appear (FR-11).
    """
    override = get_settings().reminder_awaiting_documents_hours
    return override if override is not None else get_policy().awaiting_documents_hours


def _asked_for_documents_at(repo: ContractRepository, request: ChangeRequest) -> datetime | None:
    """When the requester was last asked for the missing documents.

    The reminder is "you were asked N hours ago", so it is counted from the
    ask, not from submission: a request submitted on Monday and found
    incomplete on Thursday has been waiting since Thursday. The ask is the
    DOCUMENTS_REQUIRED notification, which is the same event the requester saw.
    """
    asks = [
        notification.created_at
        for notification in repo.list_notifications(request.requester_party, Role.PROJECT_MANAGER)
        if notification.cr_id == request.id
        and notification.kind is NotificationKind.DOCUMENTS_REQUIRED
    ]
    return max(asks) if asks else None


def document_reminders_for(
    repo: ContractRepository, party: Party, role: Role, now: datetime
) -> list[Notification]:
    """Requests still waiting on paperwork past the configured delay (FR-11)."""
    if role is not Role.PROJECT_MANAGER:
        # Nobody else was asked, so nobody else is reminded.
        return []

    cutoff = now - timedelta(hours=awaiting_documents_hours())
    reminders: list[Notification] = []
    for request in repo.list_requests_in_state(CRState.AWAITING_DOCUMENTS):
        if request.requester_party is not party:
            continue
        asked_at = _asked_for_documents_at(repo, request)
        if asked_at is None or asked_at > cutoff:
            continue
        waited_ar, waited_en = waited_phrase(int((now - asked_at).total_seconds() // 3600))
        reminders.append(
            Notification(
                cr_id=request.id,
                contract_id=request.contract_id,
                party=party,
                role=role,
                kind=NotificationKind.DOCUMENTS_REMINDER,
                message_ar=(
                    f"تذكير: الطلب {request.id} بانتظار المستندات المطلوبة منذ {waited_ar}."
                ),
                message_en=(
                    f"Reminder: {request.id} has been awaiting its documents for {waited_en}."
                ),
                created_at=now,
                is_reminder=True,
            )
        )
    return reminders


def reminders_for(
    repo: ContractRepository, party: Party, role: Role, now: datetime | None = None
) -> list[Notification]:
    """Pending approvals older than the configured delay.

    Computed on request: there is no background job, so nothing has to be
    running for a reminder to appear.
    """
    now = now or datetime.now(UTC)
    cutoff = now - timedelta(hours=pending_approval_hours())

    reminders: list[Notification] = []
    for step in repo.list_pending_steps():
        if step.party is not party or step.role is not role or step.created_at > cutoff:
            continue
        request = repo.get_change_request(step.cr_id)
        if request is None or request.state is not CRState.IN_APPROVAL:
            continue
        if current_step(tuple(repo.list_approval_steps(step.cr_id))) != step:
            continue
        waited_ar, waited_en = waited_phrase(int((now - step.created_at).total_seconds() // 3600))
        reminders.append(
            Notification(
                cr_id=step.cr_id,
                contract_id=request.contract_id,
                party=party,
                role=role,
                kind=NotificationKind.APPROVAL_REMINDER,
                message_ar=(f"تذكير: الطلب {step.cr_id} بانتظار اعتمادكم منذ {waited_ar}."),
                message_en=(
                    f"Reminder: {step.cr_id} has been awaiting your approval for {waited_en}."
                ),
                created_at=now,
                is_reminder=True,
            )
        )
    return reminders


#: Notification kinds that ask the reader to do something, with the question
#: that decides whether it is still outstanding.
_ASKS: dict[NotificationKind, str] = {
    NotificationKind.APPROVAL_PENDING: "approval",
    NotificationKind.DOCUMENTS_REQUIRED: "documents",
}


def _still_outstanding(
    repo: ContractRepository, notification: Notification, party: Party, role: Role
) -> bool:
    """Whether the thing a notification asked for is still being waited on.

    An inbox is a worklist, not a transcript. A notice saying "your approval is
    required" that stays in the list after the step has been decided makes the
    reader's queue permanently wrong - every request they have ever approved
    still counting as something to do. What was asked and when is kept in the
    audit log, which is the place for history.

    Computed rather than stored: there is no "mark as read" to go stale, and
    the answer is always the current state of the request.
    """
    ask = _ASKS.get(notification.kind)
    if ask is None:
        return True

    request = repo.get_change_request(notification.cr_id)
    if request is None:
        return True

    if ask == "documents":
        return request.state is CRState.AWAITING_DOCUMENTS

    # An approval is outstanding only while this party and role still have a
    # pending step on this request.
    if request.state is not CRState.IN_APPROVAL:
        return False
    step = current_step(tuple(repo.list_approval_steps(notification.cr_id)))
    return step is not None and step.party is party and step.role is role


def notifications_for(
    repo: ContractRepository, party: Party, role: Role, now: datetime | None = None
) -> list[Notification]:
    """Stored notifications plus freshly computed reminders (FR-11).

    Notices whose ask has been answered are left out: see
    :func:`_still_outstanding`.
    """
    at = now or datetime.now(UTC)
    return [
        *reminders_for(repo, party, role, at),
        *document_reminders_for(repo, party, role, at),
        *[
            notification
            for notification in repo.list_notifications(party, role)
            if _still_outstanding(repo, notification, party, role)
        ],
    ]


def recommendation_is_advisory(request: ChangeRequest) -> bool:
    """A recommendation is advice. Only the chain approves (control principle)."""
    return request.recommendation in {
        Recommendation.APPROVE,
        Recommendation.REJECT,
        Recommendation.REQUEST_REVISION,
        Recommendation.CLOSE_IN_SCOPE,
    } and request.state not in {CRState.APPROVED, CRState.VO_ISSUED}


def kind_requires_ledger(kind: ChangeKind | None) -> bool:
    """In-scope requests touch no ledger; everything else does."""
    return kind is not None and kind is not ChangeKind.IN_SCOPE
