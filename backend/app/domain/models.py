"""Core domain models.

Every monetary amount is a ``Decimal``; floats never touch money or a legal
limit (NFR-01). Currency is SAR throughout.
"""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.enums import ChangeCategory, OrderStatus, Party

CURRENCY = "SAR"


class ContractItem(BaseModel):
    """A priced line item of the original contract."""

    model_config = ConfigDict(frozen=True)

    id: str
    description_ar: str
    quantity: Decimal = Field(gt=0)
    unit_price: Decimal = Field(ge=0)
    total: Decimal = Field(ge=0)

    @model_validator(mode="after")
    def _total_must_match(self) -> "ContractItem":
        expected = self.quantity * self.unit_price
        if self.total != expected:
            msg = f"item {self.id}: total {self.total} != quantity * unit_price ({expected})"
            raise ValueError(msg)
        return self


class Contract(BaseModel):
    """A government contract and its original priced scope."""

    model_config = ConfigDict(frozen=True)

    id: str
    title_ar: str
    entity_name: str
    contractor_name: str
    original_value: Decimal = Field(gt=0)
    items: tuple[ContractItem, ...]
    start_date: date
    end_date: date

    @model_validator(mode="after")
    def _check_consistency(self) -> "Contract":
        if self.end_date <= self.start_date:
            msg = "end_date must be after start_date"
            raise ValueError(msg)
        items_total = sum((i.total for i in self.items), Decimal("0"))
        if items_total != self.original_value:
            msg = f"items total {items_total} != original_value {self.original_value}"
            raise ValueError(msg)
        return self


class ChangeOrder(BaseModel):
    """A proposed or recorded change to the contract.

    ``value`` is always a positive magnitude in SAR; direction is carried by
    ``type`` (a DECREASE_EXISTING of 100 means the contract shrinks by 100).
    A NON_FINANCIAL change must have a value of zero.
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
    #: Added beyond the Step-2 field list so a rejection reason is not discarded
    #: (FR-09). The full append-only audit trail is FR-13, still to come.
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
    """Every change order recorded against one contract, in creation order.

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
