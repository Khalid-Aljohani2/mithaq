"""Request and response models for the contract endpoints."""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.domain.models import ChangeOrder, Contract
from app.domain.rules import UsageSnapshot


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
            item_count=len(contract.items),
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
    #: Keyed by category name plus "COMBINED".
    usage: dict[str, UsageSnapshot]
    orders: list[ChangeOrder]
    regulation: RegulationRef
