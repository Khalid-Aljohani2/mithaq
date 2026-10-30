"""Enumerations shared across the Mithaq domain."""

from enum import StrEnum


class ChangeCategory(StrEnum):
    """The kinds of change an order can make to a contract (Article 67)."""

    NEW_ITEMS = "NEW_ITEMS"
    INCREASE_EXISTING = "INCREASE_EXISTING"
    DECREASE_EXISTING = "DECREASE_EXISTING"
    NON_FINANCIAL = "NON_FINANCIAL"


class OrderStatus(StrEnum):
    """Lifecycle of a change order. Nothing ever reaches APPROVED automatically."""

    DRAFT = "DRAFT"
    PENDING_CONTRACTOR_CONSENT = "PENDING_CONTRACTOR_CONSENT"
    PENDING_AUTHORITY_APPROVAL = "PENDING_AUTHORITY_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class Party(StrEnum):
    """The two parties to the contract. Both read the same ledger."""

    GOVERNMENT_ENTITY = "GOVERNMENT_ENTITY"
    CONTRACTOR = "CONTRACTOR"


#: Statuses whose value is not yet committed but would be if approved.
PENDING_STATUSES: frozenset[OrderStatus] = frozenset(
    {OrderStatus.PENDING_CONTRACTOR_CONSENT, OrderStatus.PENDING_AUTHORITY_APPROVAL}
)

#: Only these count toward cumulative usage.
COMMITTED_STATUSES: frozenset[OrderStatus] = frozenset({OrderStatus.APPROVED})
