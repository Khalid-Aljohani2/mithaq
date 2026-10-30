"""Change-order routes: evaluate, create, approve, reject.

Role checks live here and in the service, never only in the UI (FR-02).
"""

from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, status

from app.dependencies import LimitsDep, RepositoryDep
from app.schemas.change_orders import (
    ChangeOrderInput,
    ChangeOrderResponse,
    DecisionRequest,
    EvaluateResponse,
    RejectRequest,
)
from app.services.change_orders import (
    BlockedByRulesError,
    ChangeOrderError,
    InvalidTransitionError,
    NotFoundError,
    Proposal,
    UnknownItemError,
    WrongRoleError,
    approve_change_order,
    create_change_order,
    evaluate_proposal,
    reject_change_order,
)
from app.services.rules_engine import evaluate

contracts_router = APIRouter(prefix="/api/contracts", tags=["change-orders"])
orders_router = APIRouter(prefix="/api/change-orders", tags=["change-orders"])

#: Maps a workflow failure to the HTTP status that describes it.
_STATUS_FOR: dict[type[ChangeOrderError], int] = {
    NotFoundError: status.HTTP_404_NOT_FOUND,
    WrongRoleError: status.HTTP_403_FORBIDDEN,
    InvalidTransitionError: status.HTTP_409_CONFLICT,
    BlockedByRulesError: status.HTTP_409_CONFLICT,
    UnknownItemError: status.HTTP_422_UNPROCESSABLE_CONTENT,
}


def _http(error: ChangeOrderError) -> HTTPException:
    """Translate a workflow error into an HTTP error carrying its code."""
    code = _STATUS_FOR.get(type(error), status.HTTP_400_BAD_REQUEST)
    return HTTPException(status_code=code, detail={"code": error.code, "message": error.message})


def _proposal(payload: ChangeOrderInput) -> Proposal:
    return Proposal(
        type=payload.type,
        value=payload.value,
        related_item_ids=tuple(payload.related_item_ids),
        description_ar=payload.description_ar,
        has_written_assignment=payload.has_written_assignment,
    )


@contracts_router.post("/{contract_id}/change-orders/evaluate", response_model=EvaluateResponse)
async def evaluate_change_order(
    contract_id: str,
    payload: ChangeOrderInput,
    repo: RepositoryDep,
    limits: LimitsDep,
) -> EvaluateResponse:
    """Dry run against the current ledger. Saves nothing."""
    try:
        result, resulting_status = evaluate_proposal(
            repo, contract_id, _proposal(payload), limits, datetime.now(UTC)
        )
    except ChangeOrderError as error:
        raise _http(error) from error
    return EvaluateResponse(
        contract_id=contract_id, resulting_status=resulting_status, result=result
    )


@contracts_router.post(
    "/{contract_id}/change-orders",
    response_model=ChangeOrderResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_order(
    contract_id: str,
    payload: ChangeOrderInput,
    repo: RepositoryDep,
    limits: LimitsDep,
) -> ChangeOrderResponse:
    """Record a change order at the status its RuleResult implies.

    Never APPROVED: an order that breaches a cap is stored as a DRAFT, and one
    that passes goes into a pending queue for a human.
    """
    try:
        order, result = create_change_order(
            repo, contract_id, _proposal(payload), limits, datetime.now(UTC)
        )
    except ChangeOrderError as error:
        raise _http(error) from error
    return ChangeOrderResponse(order=order, result=result)


@orders_router.post("/{order_id}/approve", response_model=ChangeOrderResponse)
async def approve_order(
    order_id: str,
    payload: DecisionRequest,
    repo: RepositoryDep,
    limits: LimitsDep,
) -> ChangeOrderResponse:
    """Advance one approval stage after re-checking the rules."""
    try:
        order, result = approve_change_order(repo, order_id, payload.actor_role, limits)
    except ChangeOrderError as error:
        raise _http(error) from error
    return ChangeOrderResponse(order=order, result=result)


@orders_router.post("/{order_id}/reject", response_model=ChangeOrderResponse)
async def reject_order(
    order_id: str,
    payload: RejectRequest,
    repo: RepositoryDep,
    limits: LimitsDep,
) -> ChangeOrderResponse:
    """Reject an order at its current stage, recording who and why."""
    try:
        order = reject_change_order(repo, order_id, payload.actor_role, payload.reason)
    except ChangeOrderError as error:
        raise _http(error) from error

    contract = repo.get_contract(order.contract_id)
    if contract is None:  # pragma: no cover - the order cannot outlive its contract
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="contract not found")
    result = evaluate(contract, repo.get_ledger(order.contract_id), order, limits)
    return ChangeOrderResponse(order=order, result=result)
