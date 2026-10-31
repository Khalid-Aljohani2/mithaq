"""The change-request workflow objects (Requirements v2).

A :class:`ChangeRequest` is what moves through the eleven-stage pipeline. It is
not a ledger entry: approving one produces :class:`~app.domain.models.ChangeOrder`
entries that the Article 67 engine evaluates.
"""

import hashlib
import re
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import (
    ActorType,
    ApprovalDecision,
    ChangeKind,
    CRState,
    ImpactType,
    NotificationKind,
    Party,
    Recommendation,
    Role,
    Stage,
)

_WHITESPACE = re.compile(r"\s+")


def text_fingerprint(text: str) -> str:
    """A stable hash of request text, used to look up recorded AI outputs.

    Whitespace is collapsed and the ends trimmed first, so a request that
    differs only in line wrapping still matches. Not a security primitive -
    it is a cache key.
    """
    normalised = _WHITESPACE.sub(" ", text).strip()
    return hashlib.sha256(normalised.encode("utf-8")).hexdigest()


class ChangeRequest(BaseModel):
    """A request to change the contract work (FR-03).

    Fields the pipeline fills in are optional and start empty: a freshly
    received request knows only what the requester sent.
    """

    model_config = ConfigDict(frozen=True)

    id: str
    contract_id: str
    requester_name: str
    requester_party: Party
    submitted_at: datetime
    #: The pasted Arabic request text.
    body_ar: str
    #: Names of the documents attached, used by the stage 2 checklist.
    attachments: tuple[str, ...] = ()

    # ---- values a human supplied with the request ----
    # Money never comes from a model (NFR-03). Where a figure cannot be derived
    # from contract unit rates - a brand new item, or a substitute product with
    # no contract rate - a person enters it and the request is flagged. That is
    # the documented default for open question Q1.
    #: Lump sum quoted for an item with no matching breakdown line.
    human_entered_amount: Decimal | None = None
    #: Proposed unit rate for a substitute product, compared against the
    #: contract rate by stage 5.
    human_entered_unit_rate: Decimal | None = None
    #: Time impact in days, as stated by the requester.
    human_entered_days: int | None = None

    state: CRState = CRState.RECEIVED

    # ---- filled in by the pipeline ----
    kind: ChangeKind | None = None
    impact_type: ImpactType | None = None
    matched_line_ids: tuple[str, ...] = ()
    cost_impact: Decimal | None = None
    #: The gross halves behind ``cost_impact``. Article 67 counts movements per
    #: category rather than a net figure, so a substitution's removal and
    #: addition have to survive separately - the net alone cannot be split back
    #: into them, and the ledger entries are written long after stage 5 ran.
    added_value: Decimal | None = None
    removed_value: Decimal | None = None
    time_impact_days: int | None = None
    recommendation: Recommendation | None = None
    confidence: Decimal | None = None

    #: Stage 4 found it changes an approved product, so technical approval joins
    #: the chain.
    changes_approved_product: bool = False
    #: Stage 5/6 found a policy cap exceeded, so the exception role joins.
    policy_exception_required: bool = False
    #: A legal cap is implicated. CEO approval cannot lift it.
    needs_legal_review: bool = False
    #: A legal cap is actually breached, so the request cannot be approved.
    legally_blocked: bool = False
    #: Stage 5 found the proposed unit rate deviates beyond the policy limit.
    unit_rate_flagged: bool = False
    #: The amount rests on a human-entered figure rather than a contract rate.
    rate_human_entered: bool = False

    revision_count: int = 0
    closed_reason: str | None = None

    @property
    def fingerprint(self) -> str:
        """Stable hash of the request body."""
        return text_fingerprint(self.body_ar)

    @property
    def is_open(self) -> bool:
        """True while the request can still move."""
        return self.state not in {CRState.REJECTED, CRState.CLOSED_IN_SCOPE, CRState.CLOSED}


class ApprovalStep(BaseModel):
    """One position in a change request's approval chain (FR-09, FR-10)."""

    model_config = ConfigDict(frozen=True)

    id: int | None = None
    cr_id: str
    #: 1-based position. Approvers act strictly in this order.
    position: int = Field(ge=1)
    party: Party
    role: Role
    #: Why this role is in the chain, e.g. "changes_approved_product".
    reason_code: str
    decision: ApprovalDecision = ApprovalDecision.PENDING
    decided_by: str | None = None
    decided_at: datetime | None = None
    reason: str | None = None
    created_at: datetime

    @property
    def is_pending(self) -> bool:
        return self.decision is ApprovalDecision.PENDING


class StageResult(BaseModel):
    """What one pipeline stage did (FR-15, FR-18).

    ``actor_type`` is the audit-relevant field: it records whether a human,
    deterministic code, or a model produced this result.
    """

    model_config = ConfigDict(frozen=True)

    id: int | None = None
    cr_id: str
    stage: Stage
    stage_no: int
    actor_type: ActorType
    #: Which provider produced an AI result, e.g. "scripted".
    provider: str | None = None
    #: True when the output came from recorded data rather than a live model.
    recorded: bool = False
    started_at: datetime
    finished_at: datetime
    duration_ms: int
    #: OK, BLOCKED, SKIPPED or FAILED.
    status: str
    summary_ar: str = ""
    summary_en: str = ""
    #: The stage's structured output, as returned to the trace.
    payload: dict[str, object] = Field(default_factory=dict)


class Notification(BaseModel):
    """An in-app notification for a role (FR-11)."""

    model_config = ConfigDict(frozen=True)

    id: int | None = None
    cr_id: str
    contract_id: str
    party: Party
    role: Role
    kind: NotificationKind
    message_ar: str
    message_en: str
    created_at: datetime
    #: True when this was generated as a reminder rather than a first notice.
    is_reminder: bool = False


class Signature(BaseModel):
    """One approval recorded on a variation order (FR-12)."""

    model_config = ConfigDict(frozen=True)

    party: Party
    role: Role
    decided_by: str
    decided_at: datetime


class VariationOrder(BaseModel):
    """The formal instruction, issued only after the full chain approves (FR-12)."""

    model_config = ConfigDict(frozen=True)

    id: str
    cr_id: str
    contract_id: str
    number: str
    issued_at: datetime
    scope_ar: str
    #: English rendering of the scope paragraph; the Arabic is the formal text.
    scope_en: str = ""
    value: Decimal
    time_extension_days: int
    cited_line_ids: tuple[str, ...]
    cited_articles: tuple[str, ...]
    signatures: tuple[Signature, ...]
    #: True when the Arabic prose came from recorded data (FR-19).
    recorded: bool = False


class ExecutionRecord(BaseModel):
    """Actuals and close-out against one variation order (FR-14)."""

    model_config = ConfigDict(frozen=True)

    id: int | None = None
    vo_id: str
    cr_id: str
    contract_id: str
    actual_cost: Decimal | None = None
    actual_start: date | None = None
    actual_end: date | None = None
    cost_deviation: Decimal | None = None
    schedule_deviation_days: int | None = None
    acceptance_verified: bool = False
    closed_out_at: datetime | None = None
    #: FR-20, a SHOULD: captured at close-out when someone writes one.
    lessons_learned_ar: str | None = None
    notes_ar: str | None = None
