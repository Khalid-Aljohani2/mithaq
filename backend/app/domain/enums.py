"""Enumerations shared across the Mithaq domain."""

from enum import StrEnum


class ChangeCategory(StrEnum):
    """The kinds of change an order can make to a contract (Article 67)."""

    NEW_ITEMS = "NEW_ITEMS"
    INCREASE_EXISTING = "INCREASE_EXISTING"
    DECREASE_EXISTING = "DECREASE_EXISTING"
    NON_FINANCIAL = "NON_FINANCIAL"


class OrderStatus(StrEnum):
    """Lifecycle of a change order. Nothing ever reaches APPROVED automatically."""

    DRAFT = "DRAFT"
    PENDING_CONTRACTOR_CONSENT = "PENDING_CONTRACTOR_CONSENT"
    PENDING_AUTHORITY_APPROVAL = "PENDING_AUTHORITY_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class Party(StrEnum):
    """The two parties to the contract. Both read the same ledger."""

    GOVERNMENT_ENTITY = "GOVERNMENT_ENTITY"
    CONTRACTOR = "CONTRACTOR"


#: Statuses whose value is not yet committed but would be if approved.
PENDING_STATUSES: frozenset[OrderStatus] = frozenset(
    {OrderStatus.PENDING_CONTRACTOR_CONSENT, OrderStatus.PENDING_AUTHORITY_APPROVAL}
)

#: Only these count toward cumulative usage.
COMMITTED_STATUSES: frozenset[OrderStatus] = frozenset({OrderStatus.APPROVED})


# ---------------------------------------------------------------------------
# Requirements v2: the change-request workflow.
#
# The types above (ChangeCategory, OrderStatus) stay as the Article 67 ledger
# primitives. A ChangeRequest is the workflow object; approving one produces
# ledger entries that the rules engine evaluates.
# ---------------------------------------------------------------------------


class ContractType(StrEnum):
    """Which rule set applies on top of organisation policy (FR-01)."""

    GOVERNMENT = "GOVERNMENT"
    PRIVATE = "PRIVATE"


class ChangeKind(StrEnum):
    """What a change request does to the contract (v2 glossary)."""

    #: Covered by an existing breakdown line. Not a change, counts to no limit.
    IN_SCOPE = "IN_SCOPE"
    #: Positive Change Request: adds work, quantity, cost or time.
    PCR = "PCR"
    #: Negative Change Request: removes work or reduces quantity or cost.
    NCR = "NCR"
    #: Replaces an approved product, specification or method. NCR + PCR.
    SUBSTITUTION = "SUBSTITUTION"
    #: The analysis could not decide. Goes to a human, never guessed past.
    UNCLEAR = "UNCLEAR"


class ImpactType(StrEnum):
    """What a change request affects (FR-07)."""

    COST = "COST"
    TIME = "TIME"
    BOTH = "BOTH"
    NONE = "NONE"


class Role(StrEnum):
    """Approver roles. PROJECT_MANAGER is the default approver (FR-02)."""

    PROJECT_MANAGER = "PROJECT_MANAGER"
    TECHNICAL_MANAGER = "TECHNICAL_MANAGER"
    FINANCE_MANAGER = "FINANCE_MANAGER"
    LEGAL_ADVISOR = "LEGAL_ADVISOR"
    CEO = "CEO"


class CRState(StrEnum):
    """Change-request lifecycle (v2 part 2.2)."""

    RECEIVED = "RECEIVED"
    AWAITING_DOCUMENTS = "AWAITING_DOCUMENTS"
    IN_ANALYSIS = "IN_ANALYSIS"
    RECOMMENDED = "RECOMMENDED"
    IN_APPROVAL = "IN_APPROVAL"
    REVISION_REQUESTED = "REVISION_REQUESTED"
    REJECTED = "REJECTED"
    CLOSED_IN_SCOPE = "CLOSED_IN_SCOPE"
    APPROVED = "APPROVED"
    VO_ISSUED = "VO_ISSUED"
    IN_EXECUTION = "IN_EXECUTION"
    CLOSED = "CLOSED"


#: States from which nothing further happens.
TERMINAL_STATES: frozenset[CRState] = frozenset(
    {CRState.REJECTED, CRState.CLOSED_IN_SCOPE, CRState.CLOSED}
)


class ActorType(StrEnum):
    """Who produced a stage result (FR-15).

    The distinction is load-bearing, not decorative: an AI stage may never
    change state, issue a VO or alter a value (NFR-15).
    """

    CODE = "CODE"
    AI = "AI"
    HUMAN = "HUMAN"


class Recommendation(StrEnum):
    """What stage 7 recommends to the humans in the chain (FR-09)."""

    APPROVE = "APPROVE"
    REJECT = "REJECT"
    REQUEST_REVISION = "REQUEST_REVISION"
    CLOSE_IN_SCOPE = "CLOSE_IN_SCOPE"


class ApprovalDecision(StrEnum):
    """What a human approver did at their step (FR-10)."""

    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    REVISION_REQUESTED = "REVISION_REQUESTED"
    PENDING = "PENDING"


class Stage(StrEnum):
    """The eleven named pipeline stages (decision record 0001)."""

    INTAKE = "INTAKE"
    DOCUMENT_VALIDATION = "DOCUMENT_VALIDATION"
    SCOPE_ANALYSIS = "SCOPE_ANALYSIS"
    TECHNICAL_ASSESSMENT = "TECHNICAL_ASSESSMENT"
    COST_SCHEDULE_IMPACT = "COST_SCHEDULE_IMPACT"
    RISK_COMPLIANCE = "RISK_COMPLIANCE"
    ORCHESTRATOR = "ORCHESTRATOR"
    APPROVAL_GATE = "APPROVAL_GATE"
    ISSUE_VO = "ISSUE_VO"
    UPDATE_RECORDS = "UPDATE_RECORDS"
    EXECUTION_FOLLOW_UP = "EXECUTION_FOLLOW_UP"


#: Stage order, 1-indexed as in the requirements.
STAGE_ORDER: tuple[Stage, ...] = (
    Stage.INTAKE,
    Stage.DOCUMENT_VALIDATION,
    Stage.SCOPE_ANALYSIS,
    Stage.TECHNICAL_ASSESSMENT,
    Stage.COST_SCHEDULE_IMPACT,
    Stage.RISK_COMPLIANCE,
    Stage.ORCHESTRATOR,
    Stage.APPROVAL_GATE,
    Stage.ISSUE_VO,
    Stage.UPDATE_RECORDS,
    Stage.EXECUTION_FOLLOW_UP,
)

#: Stages an LLM runs. Everything else is deterministic code (NFR-15).
AI_STAGES: frozenset[Stage] = frozenset(
    {
        Stage.INTAKE,
        Stage.SCOPE_ANALYSIS,
        Stage.TECHNICAL_ASSESSMENT,
        Stage.RISK_COMPLIANCE,
    }
)

#: Stages where code decides and an LLM only supplies prose.
HYBRID_STAGES: frozenset[Stage] = frozenset({Stage.ORCHESTRATOR, Stage.ISSUE_VO})


def stage_number(stage: Stage) -> int:
    """1-based position of a stage, matching the requirement numbering."""
    return STAGE_ORDER.index(stage) + 1


class NotificationKind(StrEnum):
    """Why someone was notified (FR-11)."""

    APPROVAL_PENDING = "APPROVAL_PENDING"
    APPROVAL_REMINDER = "APPROVAL_REMINDER"
    DOCUMENTS_REQUIRED = "DOCUMENTS_REQUIRED"
    DOCUMENTS_REMINDER = "DOCUMENTS_REMINDER"
    CR_REJECTED = "CR_REJECTED"
    CR_REVISION_REQUESTED = "CR_REVISION_REQUESTED"
    CR_CLOSED_IN_SCOPE = "CR_CLOSED_IN_SCOPE"
    VO_ISSUED = "VO_ISSUED"
