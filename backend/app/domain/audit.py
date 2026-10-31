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
    CR_DOCUMENTS_SUPPLIED = "CR_DOCUMENTS_SUPPLIED"
    CR_IN_APPROVAL = "CR_IN_APPROVAL"
    CR_STEP_APPROVED = "CR_STEP_APPROVED"
    CR_APPROVED = "CR_APPROVED"
    CR_LEGAL_CAP_REFUSED = "CR_LEGAL_CAP_REFUSED"
    CR_REJECTED = "CR_REJECTED"
    CR_REVISION_REQUESTED = "CR_REVISION_REQUESTED"
    VO_ISSUED = "VO_ISSUED"
    EXECUTION_STARTED = "EXECUTION_STARTED"
    CR_CLOSED = "CR_CLOSED"
    DEMO_RESET = "DEMO_RESET"
    #: A contract entered by an authorised person on the entity side. A
    #: contract-level event: ``entity_type`` is CONTRACT and ``entity_id`` and
    #: ``contract_id`` are both the new contract's id.
    CONTRACT_CREATED = "CONTRACT_CREATED"


class AuditEvent(BaseModel):
    """One immutable entry in the audit log."""

    model_config = ConfigDict(frozen=True)

    #: Assigned by the store on insert; None before it is written.
    id: int | None = None
    occurred_at: datetime
    #: What the actor was acting *as*: a ``Role``, an ``ActorType`` for the
    #: agent's own moves, or ``SYSTEM``.
    actor_role: str
    #: Which side of the contract acted, when a side did. ``None`` for the
    #: agent's own moves and for system events - a role alone does not say
    #: whether the entity or the contractor took the action, and on a shared
    #: ledger that is the first thing a reader needs (FR-13).
    actor_party: str | None = None
    #: The person named at the time. ``None`` where no person was involved.
    actor_name: str | None = None
    action: AuditAction
    entity_type: str
    entity_id: str
    contract_id: str
    previous_state: CRState | None = None
    new_state: CRState | None = None
    reason: str | None = None
