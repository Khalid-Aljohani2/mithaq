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
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

#: Exact decimal, unconstrained scale: NUMERIC, never DOUBLE PRECISION.
Money = Numeric(asdecimal=True)


class Base(DeclarativeBase):
    """Declarative base for every Mithaq table."""


class ContractRow(Base):
    """One government contract."""

    __tablename__ = "contracts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title_ar: Mapped[str] = mapped_column(Text, nullable=False)
    entity_name: Mapped[str] = mapped_column(Text, nullable=False)
    contractor_name: Mapped[str] = mapped_column(Text, nullable=False)
    original_value: Mapped[Decimal] = mapped_column(Money, nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)

    items: Mapped[list["ContractItemRow"]] = relationship(
        back_populates="contract",
        cascade="all, delete-orphan",
        order_by="ContractItemRow.id",
        lazy="selectin",
    )


class ContractItemRow(Base):
    """A priced line item. Item ids are unique within their contract."""

    __tablename__ = "contract_items"

    contract_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("contracts.id", ondelete="CASCADE"), primary_key=True
    )
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    description_ar: Mapped[str] = mapped_column(Text, nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Money, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Money, nullable=False)
    total: Mapped[Decimal] = mapped_column(Money, nullable=False)

    contract: Mapped[ContractRow] = relationship(back_populates="items")


class ChangeOrderRow(Base):
    """A change order against a contract."""

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


class AuditLogRow(Base):
    """Append-only record of every state change (FR-13).

    Nothing in the application updates or deletes a row in this table. The only
    write path is an INSERT via ``PostgresContractRepository.append_audit``.
    """

    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    actor_role: Mapped[str] = mapped_column(String(32), nullable=False)
    action: Mapped[str] = mapped_column(String(48), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(32), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(64), nullable=False)
    contract_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    previous_state: Mapped[str | None] = mapped_column(String(32), nullable=True)
    new_state: Mapped[str | None] = mapped_column(String(32), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)


Index("ix_audit_log_contract_occurred", AuditLogRow.contract_id, AuditLogRow.occurred_at)
