"""SQLAlchemy table definitions.

Money and any stored percentage is ``NUMERIC`` with no declared precision, so
Postgres stores the exact value it was given and hands back a ``Decimal``. A
float never appears anywhere in this schema (NFR-01).
"""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

#: Exact decimal, unconstrained scale: NUMERIC, never DOUBLE PRECISION.
Money = Numeric(asdecimal=True)


class Base(DeclarativeBase):
    """Declarative base for every Mithaq table."""


class ContractRow(Base):
    """One contract and its baseline (FR-01)."""

    __tablename__ = "contracts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title_ar: Mapped[str] = mapped_column(Text, nullable=False)
    entity_name: Mapped[str] = mapped_column(Text, nullable=False)
    contractor_name: Mapped[str] = mapped_column(Text, nullable=False)
    #: GOVERNMENT or PRIVATE. Decides whether Article 67 applies on top.
    contract_type: Mapped[str] = mapped_column(String(16), nullable=False)
    original_value: Mapped[Decimal] = mapped_column(Money, nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)

    breakdown: Mapped[list["BreakdownLineRow"]] = relationship(
        back_populates="contract",
        cascade="all, delete-orphan",
        order_by="BreakdownLineRow.id",
        lazy="selectin",
    )


class BreakdownLineRow(Base):
    """A priced breakdown line. Ids are unique within their contract (FR-01)."""

    __tablename__ = "breakdown_lines"

    contract_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("contracts.id", ondelete="CASCADE"), primary_key=True
    )
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    description_ar: Mapped[str] = mapped_column(Text, nullable=False)
    unit_ar: Mapped[str] = mapped_column(String(64), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Money, nullable=False)
    unit_rate: Mapped[Decimal] = mapped_column(Money, nullable=False)
    total: Mapped[Decimal] = mapped_column(Money, nullable=False)
    approved_product_ar: Mapped[str | None] = mapped_column(Text, nullable=True)
    restrictions_ar: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, default=list)

    contract: Mapped[ContractRow] = relationship(back_populates="breakdown")


class ChangeOrderRow(Base):
    """An entry in the Article 67 cumulative ledger."""

    __tablename__ = "change_orders"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    contract_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    type: Mapped[str] = mapped_column(String(32), nullable=False)
    value: Mapped[Decimal] = mapped_column(Money, nullable=False)
    related_item_ids: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, default=list)
    description_ar: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    has_written_assignment: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    contractor_consent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    decided_by: Mapped[str | None] = mapped_column(String(32), nullable=True)
    decision_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    #: The change request that produced this entry, once v2 drives the ledger.
    change_request_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)


class AuditLogRow(Base):
    """Append-only record of every state change (FR-13).

    Nothing in the application updates or deletes a row in this table. The only
    write path is an INSERT via the repository's ``append_audit``.
    """

    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    actor_role: Mapped[str] = mapped_column(String(32), nullable=False)
    #: Nullable: the agent's own moves and system events have no party or name.
    actor_party: Mapped[str | None] = mapped_column(String(32), nullable=True)
    actor_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    action: Mapped[str] = mapped_column(String(48), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(32), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(64), nullable=False)
    contract_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    previous_state: Mapped[str | None] = mapped_column(String(32), nullable=True)
    new_state: Mapped[str | None] = mapped_column(String(32), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)


Index("ix_audit_log_contract_occurred", AuditLogRow.contract_id, AuditLogRow.occurred_at)


# ---------------------------------------------------------------------------
# Requirements v2: the change-request workflow.
# ---------------------------------------------------------------------------


class ChangeRequestRow(Base):
    """A change request moving through the eleven-stage pipeline (FR-03)."""

    __tablename__ = "change_requests"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    contract_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    requester_name: Mapped[str] = mapped_column(Text, nullable=False)
    requester_party: Mapped[str] = mapped_column(String(32), nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    body_ar: Mapped[str] = mapped_column(Text, nullable=False)
    attachments: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, default=list)

    # Human-entered figures. Money never originates from a model (NFR-03).
    human_entered_amount: Mapped[Decimal | None] = mapped_column(Money, nullable=True)
    human_entered_unit_rate: Mapped[Decimal | None] = mapped_column(Money, nullable=True)
    human_entered_days: Mapped[int | None] = mapped_column(Integer, nullable=True)

    state: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    kind: Mapped[str | None] = mapped_column(String(32), nullable=True)
    impact_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    matched_line_ids: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, default=list)
    cost_impact: Mapped[Decimal | None] = mapped_column(Money, nullable=True)
    added_value: Mapped[Decimal | None] = mapped_column(Money, nullable=True)
    removed_value: Mapped[Decimal | None] = mapped_column(Money, nullable=True)
    time_impact_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    recommendation: Mapped[str | None] = mapped_column(String(32), nullable=True)
    confidence: Mapped[Decimal | None] = mapped_column(Money, nullable=True)

    changes_approved_product: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    policy_exception_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    needs_legal_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    legally_blocked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    unit_rate_flagged: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    rate_human_entered: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    revision_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    closed_reason: Mapped[str | None] = mapped_column(Text, nullable=True)


class ApprovalStepRow(Base):
    """One position in an approval chain (FR-09, FR-10)."""

    __tablename__ = "approval_steps"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    cr_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("change_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    party: Mapped[str] = mapped_column(String(32), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    reason_code: Mapped[str] = mapped_column(String(48), nullable=False)
    decision: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    decided_by: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class StageResultRow(Base):
    """Append-only pipeline trace (FR-15, FR-18).

    Like the audit log, the application has no update or delete path for this
    table: a trace records what happened, it is not a mutable field.
    """

    __tablename__ = "stage_results"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    cr_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("change_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    stage: Mapped[str] = mapped_column(String(48), nullable=False)
    stage_no: Mapped[int] = mapped_column(Integer, nullable=False)
    #: CODE, AI or HUMAN. The field NFR-15 is audited against.
    actor_type: Mapped[str] = mapped_column(String(16), nullable=False)
    provider: Mapped[str | None] = mapped_column(String(48), nullable=True)
    recorded: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    summary_ar: Mapped[str] = mapped_column(Text, nullable=False, default="")
    summary_en: Mapped[str] = mapped_column(Text, nullable=False, default="")
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)


class NotificationRow(Base):
    """In-app notification for a role (FR-11)."""

    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    cr_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    contract_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    party: Mapped[str] = mapped_column(String(32), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    kind: Mapped[str] = mapped_column(String(48), nullable=False)
    message_ar: Mapped[str] = mapped_column(Text, nullable=False)
    message_en: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_reminder: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class VariationOrderRow(Base):
    """A formal variation order, issued only after full approval (FR-12)."""

    __tablename__ = "variation_orders"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    cr_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    contract_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    number: Mapped[str] = mapped_column(String(32), nullable=False)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    scope_ar: Mapped[str] = mapped_column(Text, nullable=False)
    scope_en: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    value: Mapped[Decimal] = mapped_column(Money, nullable=False)
    time_extension_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cited_line_ids: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, default=list)
    cited_articles: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, default=list)
    signatures: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    recorded: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class ExecutionRecordRow(Base):
    """Actuals and close-out against a variation order (FR-14)."""

    __tablename__ = "execution_records"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    vo_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    cr_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    contract_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    actual_cost: Mapped[Decimal | None] = mapped_column(Money, nullable=True)
    actual_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    actual_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    cost_deviation: Mapped[Decimal | None] = mapped_column(Money, nullable=True)
    schedule_deviation_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    acceptance_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    closed_out_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    #: FR-20, a SHOULD: captured at close-out when someone writes one.
    lessons_learned_ar: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes_ar: Mapped[str | None] = mapped_column(Text, nullable=True)
