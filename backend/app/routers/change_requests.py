"""Change-request routes: intake, analysis, approval, VO, execution.

Role checks live in the service, not only here, so a wrong-role action is
refused by the backend rather than merely hidden by a UI (FR-10).
"""

from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, status

from app.analysis.provider import AnalysisError
from app.dependencies import ProviderDep, RepositoryDep
from app.domain.models import CURRENCY
from app.schemas.change_requests import (
    AnalysisResponse,
    ChangeRequestListResponse,
    ChangeRequestResponse,
    DecisionInput,
    ExecutionInputBody,
    ExecutionResponse,
    ProjectRecordsResponse,
    SubmitRequestInput,
    TraceResponse,
    VariationOrderListResponse,
    VariationOrderResponse,
)
from app.services import change_requests as svc

contracts_router = APIRouter(prefix="/api/contracts", tags=["change-requests"])
requests_router = APIRouter(prefix="/api/change-requests", tags=["change-requests"])
vo_router = APIRouter(prefix="/api/variation-orders", tags=["change-requests"])

_STATUS_FOR: dict[type[svc.WorkflowError], int] = {
    svc.NotFoundError: status.HTTP_404_NOT_FOUND,
    svc.WrongRoleError: status.HTTP_403_FORBIDDEN,
    svc.InvalidStateError: status.HTTP_409_CONFLICT,
}


def _http(error: svc.WorkflowError) -> HTTPException:
    code = _STATUS_FOR.get(type(error), status.HTTP_400_BAD_REQUEST)
    return HTTPException(status_code=code, detail={"code": error.code, "message": error.message})


def _require(repo: RepositoryDep, cr_id: str) -> object:
    request = repo.get_change_request(cr_id)
    if request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "CR_NOT_FOUND", "message": f"change request {cr_id} not found"},
        )
    return request


# ---------------------------------------------------------------------------
# Intake (FR-03)
# ---------------------------------------------------------------------------


@contracts_router.post(
    "/{contract_id}/change-requests",
    response_model=ChangeRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_change_request(
    contract_id: str, payload: SubmitRequestInput, repo: RepositoryDep
) -> ChangeRequestResponse:
    """Receive a change request. Analysis is a separate, explicit step."""
    try:
        request = svc.submit_request(
            repo,
            contract_id,
            svc.RequestInput(
                requester_name=payload.requester_name,
                requester_party=payload.requester_party,
                body_ar=payload.body_ar,
                attachments=tuple(payload.attachments),
                human_entered_amount=payload.human_entered_amount,
                human_entered_unit_rate=payload.human_entered_unit_rate,
                human_entered_days=payload.human_entered_days,
            ),
            datetime.now(UTC),
        )
    except svc.WorkflowError as error:
        raise _http(error) from error
    return ChangeRequestResponse(request=request, chain=[])


@contracts_router.get("/{contract_id}/change-requests", response_model=ChangeRequestListResponse)
async def list_change_requests(contract_id: str, repo: RepositoryDep) -> ChangeRequestListResponse:
    """Every change request against a contract."""
    if repo.get_contract(contract_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="contract not found")
    return ChangeRequestListResponse(
        contract_id=contract_id, requests=repo.list_change_requests(contract_id)
    )


@requests_router.get("/{cr_id}", response_model=ChangeRequestResponse)
async def get_change_request(cr_id: str, repo: RepositoryDep) -> ChangeRequestResponse:
    """One change request with its approval chain."""
    request = _require(repo, cr_id)
    return ChangeRequestResponse(request=request, chain=repo.list_approval_steps(cr_id))  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Stages 1-7 (FR-04 to FR-09)
# ---------------------------------------------------------------------------


@requests_router.post("/{cr_id}/analyse", response_model=AnalysisResponse)
async def analyse_change_request(
    cr_id: str, repo: RepositoryDep, provider: ProviderDep
) -> AnalysisResponse:
    """Run the analysis pipeline and record the trace.

    Produces a recommendation. It approves nothing: the chain does that.
    """
    try:
        result = svc.analyse_request(repo, cr_id, provider, datetime.now(UTC))
    except svc.WorkflowError as error:
        raise _http(error) from error
    except AnalysisError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"code": error.code, "message": error.message},
        ) from error

    trace = repo.list_stage_results(cr_id)
    return AnalysisResponse(
        request=result.request,
        chain=repo.list_approval_steps(cr_id),
        trace=trace,
        reason_codes=list(result.decision.reason_codes) if result.decision else [],
        conflicts=list(result.decision.conflicts) if result.decision else [],
        recorded=any(stage.recorded for stage in trace),
    )


@requests_router.get("/{cr_id}/trace", response_model=TraceResponse)
async def get_trace(cr_id: str, repo: RepositoryDep) -> TraceResponse:
    """Every stage's inputs, outputs, actor and duration (FR-15, FR-18)."""
    _require(repo, cr_id)
    stages = repo.list_stage_results(cr_id)
    return TraceResponse(
        cr_id=cr_id,
        stages=stages,
        total_duration_ms=sum(stage.duration_ms for stage in stages),
    )


# ---------------------------------------------------------------------------
# Stage 8: the human approval gate (FR-10)
# ---------------------------------------------------------------------------


@requests_router.post("/{cr_id}/start-approval", response_model=ChangeRequestResponse)
async def start_approval(cr_id: str, repo: RepositoryDep) -> ChangeRequestResponse:
    """Move a recommended request into its approval chain."""
    try:
        request = svc.start_approval(repo, cr_id, datetime.now(UTC))
    except svc.WorkflowError as error:
        raise _http(error) from error
    return ChangeRequestResponse(request=request, chain=repo.list_approval_steps(cr_id))


@requests_router.post("/{cr_id}/decide", response_model=ChangeRequestResponse)
async def decide(cr_id: str, payload: DecisionInput, repo: RepositoryDep) -> ChangeRequestResponse:
    """Approve, reject, or request revision. Humans only (FR-10)."""
    try:
        request, _ = svc.decide_step(
            repo,
            cr_id,
            payload.party,
            payload.role,
            payload.decided_by,
            payload.decision,
            payload.reason,
            datetime.now(UTC),
        )
    except svc.WorkflowError as error:
        raise _http(error) from error
    return ChangeRequestResponse(request=request, chain=repo.list_approval_steps(cr_id))


# ---------------------------------------------------------------------------
# Stage 9: variation order (FR-12)
# ---------------------------------------------------------------------------


@requests_router.post(
    "/{cr_id}/variation-order",
    response_model=VariationOrderResponse,
    status_code=status.HTTP_201_CREATED,
)
async def issue_variation_order(
    cr_id: str, repo: RepositoryDep, provider: ProviderDep
) -> VariationOrderResponse:
    """Issue the VO. Only possible once the whole chain has approved."""
    try:
        vo = svc.issue_variation_order(repo, cr_id, provider, datetime.now(UTC))
    except svc.WorkflowError as error:
        raise _http(error) from error
    request = repo.get_change_request(cr_id)
    return VariationOrderResponse(variation_order=vo, request=request)  # type: ignore[arg-type]


@contracts_router.get("/{contract_id}/variation-orders", response_model=VariationOrderListResponse)
async def list_variation_orders(
    contract_id: str, repo: RepositoryDep
) -> VariationOrderListResponse:
    """Every variation order issued against a contract."""
    if repo.get_contract(contract_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="contract not found")
    return VariationOrderListResponse(
        contract_id=contract_id, variation_orders=repo.list_variation_orders(contract_id)
    )


# ---------------------------------------------------------------------------
# Stage 10: project records (FR-13)
# ---------------------------------------------------------------------------


@contracts_router.get("/{contract_id}/records", response_model=ProjectRecordsResponse)
async def get_project_records(contract_id: str, repo: RepositoryDep) -> ProjectRecordsResponse:
    """Contract value and schedule after approved changes."""
    try:
        records = svc.update_project_records(repo, contract_id)
    except svc.WorkflowError as error:
        raise _http(error) from error
    return ProjectRecordsResponse(
        contract_id=records.contract_id,
        currency=CURRENCY,
        original_value=records.original_value,
        approved_change_value=records.approved_change_value,
        revised_value=records.revised_value,
        original_duration_days=records.original_duration_days,
        approved_extension_days=records.approved_extension_days,
        revised_duration_days=records.revised_duration_days,
        variation_orders=records.variation_orders,
        as_of=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# Stage 11: execution and close-out (FR-14)
# ---------------------------------------------------------------------------


@vo_router.post("/{vo_id}/execution", response_model=ExecutionResponse)
async def record_execution(
    vo_id: str, payload: ExecutionInputBody, repo: RepositoryDep
) -> ExecutionResponse:
    """Record actuals and, when asked, close the request out."""
    try:
        record = svc.record_execution(
            repo,
            vo_id,
            svc.ExecutionInput(
                actual_cost=payload.actual_cost,
                actual_start=payload.actual_start,
                actual_end=payload.actual_end,
                acceptance_verified=payload.acceptance_verified,
                close_out=payload.close_out,
                lessons_learned_ar=payload.lessons_learned_ar,
                notes_ar=payload.notes_ar,
            ),
            datetime.now(UTC),
        )
    except svc.WorkflowError as error:
        raise _http(error) from error
    request = repo.get_change_request(record.cr_id)
    return ExecutionResponse(execution=record, request=request)  # type: ignore[arg-type]
