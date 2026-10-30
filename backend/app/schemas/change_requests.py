"""Request and response models for the change-request endpoints.

Every request and response crossing HTTP has a Pydantic model (NFR-11).
"""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.domain.change_request import (
    ApprovalStep,
    ChangeRequest,
    ExecutionRecord,
    Notification,
    StageResult,
    VariationOrder,
)
from app.domain.enums import ApprovalDecision, Party, Role

#: Caps the request body as a cheap first line of defence (NFR-08).
MAX_BODY_CHARS = 20_000


class SubmitRequestInput(BaseModel):
    """A change request as submitted (FR-03)."""

    model_config = ConfigDict(extra="forbid")

    requester_name: str = Field(min_length=1, max_length=200)
    requester_party: Party
    body_ar: str = Field(min_length=1, max_length=MAX_BODY_CHARS)
    attachments: list[str] = Field(default_factory=list, max_length=50)
    #: Human-entered figures. Money never originates from a model (NFR-03).
    human_entered_amount: Decimal | None = Field(default=None, ge=0)
    human_entered_unit_rate: Decimal | None = Field(default=None, ge=0)
    human_entered_days: int | None = Field(default=None, ge=0)


class DecisionInput(BaseModel):
    """One approver acting at their position in the chain (FR-10)."""

    model_config = ConfigDict(extra="forbid")

    party: Party
    role: Role
    decided_by: str = Field(min_length=1, max_length=200)
    decision: ApprovalDecision
    reason: str | None = Field(default=None, max_length=MAX_BODY_CHARS)


class ExecutionInputBody(BaseModel):
    """Actuals recorded against a variation order (FR-14)."""

    model_config = ConfigDict(extra="forbid")

    actual_cost: Decimal | None = Field(default=None, ge=0)
    actual_start: date | None = None
    actual_end: date | None = None
    acceptance_verified: bool = False
    close_out: bool = False
    lessons_learned_ar: str | None = Field(default=None, max_length=MAX_BODY_CHARS)
    notes_ar: str | None = Field(default=None, max_length=MAX_BODY_CHARS)


class ChangeRequestResponse(BaseModel):
    """A change request with its chain."""

    model_config = ConfigDict(frozen=True)

    request: ChangeRequest
    chain: list[ApprovalStep]


class ChangeRequestListResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    contract_id: str
    requests: list[ChangeRequest]


class AnalysisResponse(BaseModel):
    """What the pipeline concluded, plus the full trace (FR-09, FR-15)."""

    model_config = ConfigDict(frozen=True)

    request: ChangeRequest
    chain: list[ApprovalStep]
    trace: list[StageResult]
    #: Code's reason codes, not prose. The narrative lives in the trace.
    reason_codes: list[str]
    conflicts: list[str]
    #: True when the AI outputs were replayed rather than generated (FR-19).
    recorded: bool


class TraceResponse(BaseModel):
    """The agent trace for one change request (FR-15, FR-18)."""

    model_config = ConfigDict(frozen=True)

    cr_id: str
    stages: list[StageResult]
    total_duration_ms: int


class VariationOrderResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    variation_order: VariationOrder
    request: ChangeRequest


class VariationOrderListResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    contract_id: str
    variation_orders: list[VariationOrder]


class ExecutionResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    execution: ExecutionRecord
    request: ChangeRequest


class NotificationListResponse(BaseModel):
    """Stored notifications plus freshly computed reminders (FR-11)."""

    model_config = ConfigDict(frozen=True)

    party: Party
    role: Role
    notifications: list[Notification]
    reminder_count: int


class ProjectRecordsResponse(BaseModel):
    """The contract's position after approved changes (FR-13)."""

    model_config = ConfigDict(frozen=True)

    contract_id: str
    currency: str
    original_value: Decimal
    approved_change_value: Decimal
    revised_value: Decimal
    original_duration_days: int
    approved_extension_days: int
    revised_duration_days: int
    variation_orders: int
    as_of: datetime
