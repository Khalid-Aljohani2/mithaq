"""Append-only audit trail (FR-13).

Every state change writes exactly one row recording who acted, when, on what,
and what the state was before and after. Rows are never updated or deleted:
there is no code path that does either, and the demo reset appends an event
rather than clearing the table.
"""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from app.domain.enums import CRState

#: Actor recorded for events no party performed, such as the demo reset.
SYSTEM_ACTOR = "SYSTEM"


class AuditAction(StrEnum):
    """What happened."""

    # v2 change-request workflow
    CR_RECEIVED = "CR_RECEIVED"
    CR_ANALYSED = "CR_ANALYSED"
    CR_IN_APPROVAL = "CR_IN_APPROVAL"
    CR_STEP_APPROVED = "CR_STEP_APPROVED"
    CR_APPROVED = "CR_APPROVED"
    CR_REJECTED = "CR_REJECTED"
    CR_REVISION_REQUESTED = "CR_REVISION_REQUESTED"
    VO_ISSUED = "VO_ISSUED"
    EXECUTION_STARTED = "EXECUTION_STARTED"
    CR_CLOSED = "CR_CLOSED"
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
    previous_state: CRState | None = None
    new_state: CRState | None = None
    reason: str | None = None
