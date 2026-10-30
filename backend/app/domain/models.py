"""Core domain models.

Every monetary amount is a ``Decimal``; floats never touch money or a legal
limit (NFR-01). Currency is SAR throughout.

Two layers live here and they are not the same thing:

* :class:`Contract` and :class:`BreakdownLine` are the baseline (FR-01).
* :class:`ChangeOrder` and :class:`ChangeLedger` are the **Article 67 ledger**
  primitives. They are what the rules engine evaluates. A ChangeRequest (the v2
  workflow object, in ``change_request.py``) produces ledger entries when it is
  approved; it is not itself a ledger entry.
"""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.enums import ChangeCategory, ContractType, OrderStatus, Party

CURRENCY = "SAR"


class BreakdownLine(BaseModel):
    """One line of the contract breakdown, BOQ or WBS (FR-01).

    A request that is fully covered by one of these is *in scope*: it is not a
    change and counts toward no limit.
    """

    model_config = ConfigDict(frozen=True)

    id: str
    description_ar: str
    #: Unit of measure, in Arabic, e.g. "عدد" or "شهر".
    unit_ar: str
    quantity: Decimal = Field(gt=0)
    #: The contract unit rate. Stage 5 prices everything from this.
    unit_rate: Decimal = Field(ge=0)
    total: Decimal = Field(ge=0)
    #: The product or specification approved for this line, if one is named.
    approved_product_ar: str | None = None
    #: Restrictions the work must respect. A conflict is flagged by stage 4.
    restrictions_ar: tuple[str, ...] = ()

    @model_validator(mode="after")
    def _total_must_match(self) -> "BreakdownLine":
        expected = self.quantity * self.unit_rate
        if self.total != expected:
            msg = f"line {self.id}: total {self.total} != quantity * unit_rate ({expected})"
            raise ValueError(msg)
        return self


class Contract(BaseModel):
    """A contract and its priced baseline (FR-01)."""

    model_config = ConfigDict(frozen=True)

    id: str
    title_ar: str
    entity_name: str
    contractor_name: str
    #: GOVERNMENT contracts also get the Article 67 rules engine on top.
    contract_type: ContractType
    original_value: Decimal = Field(gt=0)
    breakdown: tuple[BreakdownLine, ...]
    start_date: date
    end_date: date

    @property
    def original_duration_days(self) -> int:
        """Baseline duration. The basis for the policy time-extension cap."""
        return (self.end_date - self.start_date).days

    @property
    def is_government(self) -> bool:
        """True when the Article 67 caps apply on top of organisation policy."""
        return self.contract_type is ContractType.GOVERNMENT

    def line(self, line_id: str) -> BreakdownLine | None:
        """Look up one breakdown line."""
        return next((line for line in self.breakdown if line.id == line_id), None)

    @model_validator(mode="after")
    def _check_consistency(self) -> "Contract":
        if self.end_date <= self.start_date:
            msg = "end_date must be after start_date"
            raise ValueError(msg)
        total = sum((line.total for line in self.breakdown), Decimal("0"))
        if total != self.original_value:
            msg = f"breakdown total {total} != original_value {self.original_value}"
            raise ValueError(msg)
        return self


class ChangeOrder(BaseModel):
    """An entry in the Article 67 cumulative ledger.

    ``value`` is always a positive magnitude in SAR; direction is carried by
    ``type`` (a DECREASE_EXISTING of 100 means the contract shrinks by 100).
    A NON_FINANCIAL change must have a value of zero.

    One change request can produce two of these: a substitution is an NCR for
    what it removes plus a PCR for what it adds.
    """

    model_config = ConfigDict(frozen=True)

    id: str
    contract_id: str
    type: ChangeCategory
    value: Decimal = Field(ge=0)
    related_item_ids: tuple[str, ...] = ()
    description_ar: str
    status: OrderStatus = OrderStatus.DRAFT
    has_written_assignment: bool = False
    contractor_consent: bool = False
    created_at: datetime
    #: The change request this entry came from, once v2 drives the ledger.
    change_request_id: str | None = None
    decided_by: Party | None = None
    decision_reason: str | None = None

    @model_validator(mode="after")
    def _non_financial_has_no_value(self) -> "ChangeOrder":
        if self.type is ChangeCategory.NON_FINANCIAL and self.value != Decimal("0"):
            msg = "a NON_FINANCIAL change order must have value 0 (Article 67(3))"
            raise ValueError(msg)
        if self.type is not ChangeCategory.NON_FINANCIAL and self.value == Decimal("0"):
            msg = f"a {self.type} change order must have a value greater than 0"
            raise ValueError(msg)
        return self


class ChangeLedger(BaseModel):
    """Every ledger entry recorded against one contract, in creation order.

    Shared by both parties: there is exactly one ledger per contract.
    """

    model_config = ConfigDict(frozen=True)

    contract_id: str
    orders: tuple[ChangeOrder, ...] = ()

    def excluding(self, order_id: str) -> "ChangeLedger":
        """Return a copy without ``order_id``.

        Used when re-evaluating an order that is already recorded, so it is not
        counted against itself.
        """
        return ChangeLedger(
            contract_id=self.contract_id,
            orders=tuple(o for o in self.orders if o.id != order_id),
        )
