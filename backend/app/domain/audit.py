"""Append-only audit trail (FR-13).

Every state change writes exactly one row recording who acted, when, on what,
and what the state was before and after. Rows are never updated or deleted:
there is no code path that does either, and the demo reset appends an event
rather than clearing the table.
"""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from app.domain.enums import OrderStatus

#: Actor recorded for events no party performed, such as the demo reset.
SYSTEM_ACTOR = "SYSTEM"


class AuditAction(StrEnum):
    """What happened."""

    ORDER_CREATED = "ORDER_CREATED"
    CONTRACTOR_CONSENTED = "CONTRACTOR_CONSENTED"
    ORDER_APPROVED = "ORDER_APPROVED"
    ORDER_REJECTED = "ORDER_REJECTED"
    DEMO_RESET = "DEMO_RESET"


class AuditEvent(BaseModel):
    """One immutable entry in the audit log."""

    model_config = ConfigDict(frozen=True)

    #: Assigned by the store on insert; None before it is written.
    id: int | None = None
    occurred_at: datetime
    #: A ``Party`` value, or ``SYSTEM`` for events no party performed.
    actor_role: str
    action: AuditAction
    entity_type: str
    entity_id: str
    contract_id: str
    previous_state: OrderStatus | None = None
    new_state: OrderStatus | None = None
    reason: str | None = None
