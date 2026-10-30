"""Request and response models for the change-order endpoints.

Every request and every response crossing HTTP has a Pydantic model; no bare
dicts (NFR-11).
"""

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.enums import ChangeCategory, OrderStatus, Party
from app.domain.models import ChangeOrder
from app.domain.rules import RuleResult

#: Caps the request body as a cheap first line of defence (NFR-08).
MAX_DESCRIPTION_CHARS = 5_000


class ChangeOrderInput(BaseModel):
    """A proposed change, as submitted by a client."""

    model_config = ConfigDict(extra="forbid")

    type: ChangeCategory
    value: Decimal = Field(
        ge=0, description="Positive magnitude in SAR; direction comes from type."
    )
    related_item_ids: list[str] = Field(default_factory=list)
    description_ar: str = Field(min_length=1, max_length=MAX_DESCRIPTION_CHARS)
    has_written_assignment: bool = False

    @model_validator(mode="after")
    def _value_matches_type(self) -> "ChangeOrderInput":
        """Mirror the domain rule here so a bad body is a 422, not a 500."""
        if self.type is ChangeCategory.NON_FINANCIAL and self.value != Decimal("0"):
            msg = "a NON_FINANCIAL change order must have value 0 (Article 67(3))"
            raise ValueError(msg)
        if self.type is not ChangeCategory.NON_FINANCIAL and self.value <= Decimal("0"):
            msg = f"a {self.type.value} change order must have a value greater than 0"
            raise ValueError(msg)
        return self


class EvaluateResponse(BaseModel):
    """Result of a dry run. Nothing was saved."""

    model_config = ConfigDict(frozen=True)

    contract_id: str
    #: The status this order would get if it were created now.
    resulting_status: OrderStatus
    result: RuleResult


class ChangeOrderResponse(BaseModel):
    """A stored change order together with the verdict that placed it."""

    model_config = ConfigDict(frozen=True)

    order: ChangeOrder
    result: RuleResult


class DecisionRequest(BaseModel):
    """Who is acting. The backend checks the role, the UI does not (FR-02)."""

    model_config = ConfigDict(extra="forbid")

    actor_role: Party


class RejectRequest(DecisionRequest):
    """A rejection must say why."""

    reason: str = Field(min_length=1, max_length=MAX_DESCRIPTION_CHARS)
