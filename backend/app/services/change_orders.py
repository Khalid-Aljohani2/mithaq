"""Change-order orchestration.

Sits between the routers and the repository. The routers do HTTP, this module
does the workflow, the rules engine does the law, the repository does storage
(NFR-11).

Nothing here ever auto-approves (FR-09): an order only becomes APPROVED when a
human on the authority side acts, and the rules are re-checked at that moment.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from app.domain.enums import ChangeCategory, OrderStatus, Party
from app.domain.models import ChangeOrder, Contract
from app.domain.rules import RuleResult
from app.regulations.loader import Limits
from app.repositories.base import ContractRepository
from app.services.rules_engine import evaluate

#: Which party acts at each pending stage.
STAGE_OWNER: dict[OrderStatus, Party] = {
    OrderStatus.PENDING_CONTRACTOR_CONSENT: Party.CONTRACTOR,
    OrderStatus.PENDING_AUTHORITY_APPROVAL: Party.GOVERNMENT_ENTITY,
}


class ChangeOrderError(Exception):
    """Base class for workflow failures, carrying a stable code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class NotFoundError(ChangeOrderError):
    """The contract or order does not exist."""


class WrongRoleError(ChangeOrderError):
    """The acting party may not take this action at this stage (FR-02)."""


class InvalidTransitionError(ChangeOrderError):
    """The order is not in a state where this action makes sense."""


class BlockedByRulesError(ChangeOrderError):
    """The order breaches a cap and cannot move forward."""


class UnknownItemError(ChangeOrderError):
    """The order points at contract items that do not exist."""


@dataclass(frozen=True)
class Proposal:
    """A change order someone wants to make, before it has an id or a status."""

    type: ChangeCategory
    value: Decimal
    related_item_ids: tuple[str, ...]
    description_ar: str
    has_written_assignment: bool


def _require_contract(repo: ContractRepository, contract_id: str) -> Contract:
    contract = repo.get_contract(contract_id)
    if contract is None:
        raise NotFoundError("CONTRACT_NOT_FOUND", f"contract {contract_id} not found")
    return contract


def _require_order(repo: ContractRepository, order_id: str) -> ChangeOrder:
    order = repo.get_change_order(order_id)
    if order is None:
        raise NotFoundError("ORDER_NOT_FOUND", f"change order {order_id} not found")
    return order


def _validate_items(contract: Contract, proposal: Proposal) -> None:
    """Reject references to items that are not in the contract.

    An increase or decrease has to attach to something real, otherwise the
    ledger records a number with no scope behind it.
    """
    known = {item.id for item in contract.items}
    unknown = [item_id for item_id in proposal.related_item_ids if item_id not in known]
    if unknown:
        raise UnknownItemError(
            "UNKNOWN_ITEM",
            f"contract {contract.id} has no items {unknown}",
        )
    needs_items = {ChangeCategory.INCREASE_EXISTING, ChangeCategory.DECREASE_EXISTING}
    if proposal.type in needs_items and not proposal.related_item_ids:
        raise UnknownItemError(
            "ITEMS_REQUIRED",
            f"a {proposal.type.value} order must name the contract items it changes",
        )


def initial_status(result: RuleResult) -> OrderStatus:
    """Decide the status a newly created order starts in.

    Never APPROVED. An order that breaches a cap stays a DRAFT so it can be
    reworked rather than entering the approval queue.
    """
    if not result.allowed:
        return OrderStatus.DRAFT
    if result.requires_contractor_consent:
        return OrderStatus.PENDING_CONTRACTOR_CONSENT
    return OrderStatus.PENDING_AUTHORITY_APPROVAL


def _as_order(
    contract_id: str,
    order_id: str,
    proposal: Proposal,
    status: OrderStatus,
    created_at: datetime,
) -> ChangeOrder:
    return ChangeOrder(
        id=order_id,
        contract_id=contract_id,
        type=proposal.type,
        value=proposal.value,
        related_item_ids=proposal.related_item_ids,
        description_ar=proposal.description_ar,
        status=status,
        has_written_assignment=proposal.has_written_assignment,
        contractor_consent=False,
        created_at=created_at,
    )


def evaluate_proposal(
    repo: ContractRepository,
    contract_id: str,
    proposal: Proposal,
    limits: Limits,
    now: datetime,
) -> tuple[RuleResult, OrderStatus]:
    """Dry run. Saves nothing and changes nothing."""
    contract = _require_contract(repo, contract_id)
    _validate_items(contract, proposal)
    ledger = repo.get_ledger(contract_id)
    probe = _as_order(contract_id, "__probe__", proposal, OrderStatus.DRAFT, now)
    result = evaluate(contract, ledger, probe, limits)
    return result, initial_status(result)


def create_change_order(
    repo: ContractRepository,
    contract_id: str,
    proposal: Proposal,
    limits: Limits,
    now: datetime,
) -> tuple[ChangeOrder, RuleResult]:
    """Record a change order at the status its RuleResult implies."""
    contract = _require_contract(repo, contract_id)
    _validate_items(contract, proposal)
    ledger = repo.get_ledger(contract_id)
    order_id = repo.next_change_order_id(contract_id)
    draft = _as_order(contract_id, order_id, proposal, OrderStatus.DRAFT, now)
    result = evaluate(contract, ledger, draft, limits)
    stored = repo.add_change_order(draft.model_copy(update={"status": initial_status(result)}))
    return stored, result


def _guard_stage(order: ChangeOrder, actor_role: Party) -> None:
    """Check the order is at a decidable stage and the right party is acting."""
    expected = STAGE_OWNER.get(order.status)
    if expected is None:
        raise InvalidTransitionError(
            "INVALID_TRANSITION",
            f"change order {order.id} is {order.status} and is not awaiting a decision",
        )
    if actor_role is not expected:
        raise WrongRoleError(
            "WRONG_ROLE",
            f"{order.status} must be decided by {expected}, not {actor_role}",
        )


def approve_change_order(
    repo: ContractRepository,
    order_id: str,
    actor_role: Party,
    limits: Limits,
) -> tuple[ChangeOrder, RuleResult]:
    """Advance one approval stage, re-checking the rules first.

    Re-evaluation matters: other orders may have been approved since this one was
    created, so headroom that existed then may be gone now. This is what stops a
    queue of individually-valid orders from being approved past a cap.
    """
    order = _require_order(repo, order_id)
    _guard_stage(order, actor_role)

    contract = _require_contract(repo, order.contract_id)
    ledger = repo.get_ledger(order.contract_id)
    result = evaluate(contract, ledger, order, limits)
    if not result.allowed:
        raise BlockedByRulesError(
            "BLOCKED_BY_RULES",
            "approving this order would breach a cap given the current ledger: "
            + "; ".join(v.message_en for v in result.blocking_violations),
        )

    if order.status is OrderStatus.PENDING_CONTRACTOR_CONSENT:
        updated = order.model_copy(
            update={
                "status": OrderStatus.PENDING_AUTHORITY_APPROVAL,
                "contractor_consent": True,
                "decided_by": actor_role,
            }
        )
    else:
        updated = order.model_copy(
            update={"status": OrderStatus.APPROVED, "decided_by": actor_role}
        )

    return repo.replace_change_order(updated), result


def reject_change_order(
    repo: ContractRepository,
    order_id: str,
    actor_role: Party,
    reason: str,
) -> ChangeOrder:
    """Reject an order at its current stage, recording who and why."""
    order = _require_order(repo, order_id)
    _guard_stage(order, actor_role)
    updated = order.model_copy(
        update={
            "status": OrderStatus.REJECTED,
            "decided_by": actor_role,
            "decision_reason": reason,
        }
    )
    return repo.replace_change_order(updated)
