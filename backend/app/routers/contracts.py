"""Contract and ledger routes, plus contract intake (ADR 0006).

Intake is two separate routes with two separate trust levels:

* ``POST /api/contracts`` - a person submits a contract. The server validates
  it, computes every line total, stores it and audits who did it.
* ``POST /api/contracts/draft`` - the model reads an uploaded document and
  returns a draft of that form. It stores nothing and audits nothing: the AI
  never creates a contract (NFR-15).

The demo reset (``POST /api/demo/reset``) restores the seed: contracts created
here are deleted by it, in both stores. Their audit rows remain, because the
audit log is append-only (FR-13).
"""

import base64
import binascii
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, status

from app.analysis.contract_draft import DraftFailedError, draft_contract
from app.dependencies import LimitsDep, RepositoryDep, SettingsDep
from app.domain.enums import ContractType
from app.domain.models import CURRENCY, Contract
from app.pipeline.limits import policy_usage
from app.regulations.loader import get_regulation
from app.schemas.contracts import (
    MAX_DRAFT_PDF_BYTES,
    AuditLogResponse,
    ContractCreateInput,
    ContractDraftInput,
    ContractDraftResponse,
    ContractInvalidDetail,
    ContractListResponse,
    ContractProblem,
    ContractSummary,
    LedgerResponse,
    RegulationRef,
)
from app.services import contracts as contract_svc
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


def _invalid(message: str, problems: list[ContractProblem]) -> HTTPException:
    detail = ContractInvalidDetail(message=message, problems=problems)
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=detail.model_dump()
    )


def _wrong_role(error: contract_svc.ContractWrongRoleError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={"code": error.code, "message": error.message},
    )


@router.post("", response_model=Contract, status_code=status.HTTP_201_CREATED)
async def create_contract(payload: ContractCreateInput, repo: RepositoryDep) -> Contract:
    """Enter a new contract and its priced baseline (FR-01). A person's action."""
    try:
        return contract_svc.create_contract(repo, payload, datetime.now(UTC))
    except contract_svc.ContractWrongRoleError as error:
        raise _wrong_role(error) from error
    except contract_svc.ContractInvalidError as error:
        raise _invalid("the contract was not saved", error.problems) from error


def _input_problem(field: str, code: str, ar: str, en: str) -> HTTPException:
    return _invalid(
        "the document could not be read",
        [ContractProblem(field=field, code=code, message_ar=ar, message_en=en)],
    )


def _checked_pdf(pdf_base64: str) -> str:
    """Decode to check size and signature; return the base64 to forward."""
    try:
        raw = base64.b64decode(pdf_base64, validate=True)
    except (binascii.Error, ValueError) as error:
        raise _input_problem(
            "pdf_base64", "NOT_BASE64", "الملف غير مرمز بصيغة base64.", "Not valid base64."
        ) from error
    if len(raw) > MAX_DRAFT_PDF_BYTES:
        raise _input_problem(
            "pdf_base64",
            "FILE_TOO_LARGE",
            "حجم الملف يتجاوز 10 ميغابايت.",
            "The file is larger than 10 MB.",
        )
    if not raw.startswith(b"%PDF"):
        raise _input_problem(
            "pdf_base64", "NOT_A_PDF", "الملف ليس بصيغة PDF.", "The file is not a PDF."
        )
    return pdf_base64


@router.post("/draft", response_model=ContractDraftResponse)
async def draft_contract_from_document(
    payload: ContractDraftInput, settings: SettingsDep
) -> ContractDraftResponse:
    """Read an uploaded contract into an editable draft. Saves and audits nothing.

    Deliberately takes no repository: the AI path cannot create a contract,
    it can only suggest the fields a person then reviews and submits (NFR-15).
    """
    try:
        contract_svc.check_creator(payload.party, payload.role)
    except contract_svc.ContractWrongRoleError as error:
        raise _wrong_role(error) from error

    has_text = payload.text is not None and bool(payload.text.strip())
    has_pdf = payload.pdf_base64 is not None and bool(payload.pdf_base64.strip())
    if has_text == has_pdf:
        raise _input_problem(
            "text",
            "ONE_SOURCE_REQUIRED",
            "أرسل نص العقد أو ملف PDF، أحدهما فقط.",
            "Send either the contract text or a PDF, exactly one of them.",
        )
    pdf = _checked_pdf(payload.pdf_base64.strip()) if payload.pdf_base64 and has_pdf else None

    if not settings.uses_live_provider:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "DRAFT_NEEDS_LIVE_PROVIDER",
                "message": "Reading a contract document needs the live AI provider "
                "(LLM_PROVIDER=anthropic with an API key). Enter the contract by hand instead.",
            },
        )

    try:
        draft, model, version = draft_contract(settings, None if pdf else payload.text, pdf)
    except DraftFailedError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": error.code, "message": error.message},
        ) from error
    return ContractDraftResponse(draft=draft, model=model, prompt_version=version)


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
