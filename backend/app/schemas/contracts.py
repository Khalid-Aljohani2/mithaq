"""Request and response models for the contract endpoints."""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.domain.audit import AuditEvent
from app.domain.enums import ContractType, Party, Role
from app.domain.models import ChangeOrder, Contract
from app.domain.rules import CapLine, UsageSnapshot


class ContractSummary(BaseModel):
    """One row of the contract list."""

    model_config = ConfigDict(frozen=True)

    id: str
    title_ar: str
    entity_name: str
    contractor_name: str
    original_value: Decimal
    currency: str
    start_date: date
    end_date: date
    item_count: int

    @classmethod
    def from_contract(cls, contract: Contract, currency: str) -> "ContractSummary":
        """Project a contract down to its list representation."""
        return cls(
            id=contract.id,
            title_ar=contract.title_ar,
            entity_name=contract.entity_name,
            contractor_name=contract.contractor_name,
            original_value=contract.original_value,
            currency=currency,
            start_date=contract.start_date,
            end_date=contract.end_date,
            item_count=len(contract.breakdown),
        )


class ContractListResponse(BaseModel):
    """All contracts visible to the caller."""

    model_config = ConfigDict(frozen=True)

    contracts: list[ContractSummary]


class RegulationRef(BaseModel):
    """Where the numbers on this response came from (NFR-02)."""

    model_config = ConfigDict(frozen=True)

    law_name_ar: str
    law_name_en: str
    source_url: str
    publication_date_gregorian: str
    article_refs: list[str]


class LedgerResponse(BaseModel):
    """Cumulative usage per category plus every order recorded so far (FR-10)."""

    model_config = ConfigDict(frozen=True)

    contract_id: str
    currency: str
    original_value: Decimal
    #: Article 67 usage, keyed by category name plus "COMBINED". Every line
    #: carries the article it rests on, because a ledger mixes several (NFR-02).
    usage: dict[str, UsageSnapshot]
    #: The organisation's own caps, which apply to every contract and can be
    #: escalated past by the role each line names. Kept apart from ``usage`` so
    #: a blocking legal cap is never mistaken for a negotiable one (NFR-16).
    policy_usage: dict[str, CapLine]
    #: True when Article 67 applies at all, i.e. this is a government contract.
    legal_limits_apply: bool
    orders: list[ChangeOrder]
    regulation: RegulationRef


class AuditLogResponse(BaseModel):
    """The append-only trail for one contract, oldest first (FR-13)."""

    model_config = ConfigDict(frozen=True)

    contract_id: str
    events: list[AuditEvent]


# ---------------------------------------------------------------------------
# Contract intake (ADR 0006)
# ---------------------------------------------------------------------------

#: Bounds on a contract breakdown entered through the API.
MAX_BREAKDOWN_LINES = 100
#: Bounds on an uploaded contract sent for an AI draft (NFR-08).
MAX_DRAFT_TEXT_CHARS = 200_000
MAX_DRAFT_PDF_BYTES = 10 * 1024 * 1024


class BreakdownLineInput(BaseModel):
    """One breakdown line as a person enters it. The server computes id and total."""

    model_config = ConfigDict(extra="forbid")

    description_ar: str = Field(max_length=2000)
    unit_ar: str = Field(max_length=64)
    #: Decimal, never float (NFR-01). Send it as a string to keep it exact.
    quantity: Decimal
    unit_rate: Decimal
    approved_product_ar: str | None = Field(default=None, max_length=2000)
    restrictions_ar: list[str] = Field(default_factory=list, max_length=50)


class ContractCreateInput(BaseModel):
    """A new contract and its priced baseline, entered by an authorised person (FR-01).

    Types are checked here; business rules (positive amounts, decimal places,
    the breakdown summing to the contract value, dates in order) are checked
    by ``app.services.contracts`` so every problem is reported at once, with a
    stable code, in both languages.
    """

    model_config = ConfigDict(extra="forbid")

    party: Party
    role: Role
    created_by: str = Field(max_length=200)
    title_ar: str = Field(max_length=500)
    entity_name: str = Field(max_length=500)
    contractor_name: str = Field(max_length=500)
    contract_type: ContractType
    original_value: Decimal
    start_date: date
    end_date: date
    breakdown: list[BreakdownLineInput]


class ContractProblem(BaseModel):
    """One reason a contract was refused."""

    model_config = ConfigDict(frozen=True)

    #: Where the problem is, e.g. ``end_date`` or ``breakdown[2].quantity``.
    field: str
    #: Stable code, e.g. TOTAL_MISMATCH, END_BEFORE_START, TOO_MANY_DECIMALS.
    code: str
    message_ar: str
    message_en: str


class ContractInvalidDetail(BaseModel):
    """The ``detail`` of a 422 from the contract intake routes."""

    model_config = ConfigDict(frozen=True)

    code: str = "CONTRACT_INVALID"
    message: str
    problems: list[ContractProblem]


class ContractDraftInput(BaseModel):
    """An uploaded contract to be read into a draft. Exactly one of text or PDF."""

    model_config = ConfigDict(extra="forbid")

    party: Party
    role: Role
    text: str | None = Field(default=None, max_length=MAX_DRAFT_TEXT_CHARS)
    #: Base64 of the PDF bytes. The decoded size is checked by the route.
    pdf_base64: str | None = Field(default=None, max_length=(MAX_DRAFT_PDF_BYTES * 4) // 3 + 8)
    filename: str | None = Field(default=None, max_length=255)


class ContractDraftLine(BaseModel):
    """A breakdown line as read from a document. Anything unread is null."""

    model_config = ConfigDict(frozen=True)

    description_ar: str | None = None
    unit_ar: str | None = None
    quantity: Decimal | None = None
    unit_rate: Decimal | None = None
    approved_product_ar: str | None = None
    restrictions_ar: list[str] = Field(default_factory=list)


class ContractDraft(BaseModel):
    """What the model read from a contract document. A suggestion, never a record.

    Every field is optional: a field the document does not state is null, and
    a person completes and submits the form. Nothing here is saved (NFR-15).
    """

    model_config = ConfigDict(frozen=True)

    title_ar: str | None = None
    entity_name: str | None = None
    contractor_name: str | None = None
    contract_type: ContractType | None = None
    original_value: Decimal | None = None
    start_date: date | None = None
    end_date: date | None = None
    breakdown: list[ContractDraftLine] = Field(default_factory=list)
    #: Anything the model was unsure about, for the reviewer.
    notes_en: list[str] = Field(default_factory=list)
    notes_ar: list[str] = Field(default_factory=list)


class ContractDraftResponse(BaseModel):
    """A draft plus the model and prompt version that produced it (NFR-12)."""

    model_config = ConfigDict(frozen=True)

    draft: ContractDraft
    model: str
    prompt_version: str
