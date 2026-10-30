"""Contract and ledger routes."""

from fastapi import APIRouter, HTTPException, status

from app.dependencies import LimitsDep, RepositoryDep
from app.domain.enums import ContractType
from app.domain.models import CURRENCY, Contract
from app.pipeline.limits import policy_usage
from app.regulations.loader import get_regulation
from app.schemas.contracts import (
    AuditLogResponse,
    ContractListResponse,
    ContractSummary,
    LedgerResponse,
    RegulationRef,
)
from app.services.change_requests import cumulative_totals, pending_totals
from app.services.rules_engine import summarise

router = APIRouter(prefix="/api/contracts", tags=["contracts"])


def _regulation_ref() -> RegulationRef:
    """Describe the regulation backing every number in a ledger response."""
    regulation = get_regulation()
    limits = regulation.limits
    refs = [rule.article_ref_en for rule in limits.categories.values()]
    refs.append(limits.combined.article_ref_en)
    refs.append(limits.time_extension.article_ref_en)
    return RegulationRef(
        law_name_ar=regulation.source.law_name_ar,
        law_name_en=regulation.source.law_name_en,
        source_url=regulation.source.url,
        publication_date_gregorian=regulation.source.publication_date_gregorian,
        article_refs=list(dict.fromkeys(refs)),
    )


@router.get("", response_model=ContractListResponse)
async def list_contracts(repo: RepositoryDep) -> ContractListResponse:
    """List every contract."""
    return ContractListResponse(
        contracts=[ContractSummary.from_contract(c, CURRENCY) for c in repo.list_contracts()]
    )


@router.get("/{contract_id}", response_model=Contract)
async def get_contract(contract_id: str, repo: RepositoryDep) -> Contract:
    """Return one contract with its full priced item list."""
    contract = repo.get_contract(contract_id)
    if contract is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"contract {contract_id} not found",
        )
    return contract


@router.get("/{contract_id}/ledger", response_model=LedgerResponse)
async def get_ledger(contract_id: str, repo: RepositoryDep, limits: LimitsDep) -> LedgerResponse:
    """Cumulative usage per cap plus every order recorded so far (FR-10)."""
    contract = repo.get_contract(contract_id)
    if contract is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"contract {contract_id} not found",
        )
    ledger = repo.get_ledger(contract_id)
    cost_used, days_used = cumulative_totals(repo, contract_id)
    cost_pending, days_pending = pending_totals(repo, contract_id)
    return LedgerResponse(
        contract_id=contract_id,
        currency=CURRENCY,
        original_value=contract.original_value,
        usage=summarise(contract, ledger, limits),
        policy_usage=policy_usage(contract, cost_used, days_used, cost_pending, days_pending),
        legal_limits_apply=contract.contract_type is ContractType.GOVERNMENT,
        orders=list(ledger.orders),
        regulation=_regulation_ref(),
    )


@router.get("/{contract_id}/audit", response_model=AuditLogResponse)
async def get_audit_log(contract_id: str, repo: RepositoryDep) -> AuditLogResponse:
    """Every state change recorded against this contract, oldest first (FR-13)."""
    if repo.get_contract(contract_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"contract {contract_id} not found",
        )
    return AuditLogResponse(contract_id=contract_id, events=repo.list_audit(contract_id))
