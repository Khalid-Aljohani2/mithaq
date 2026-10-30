"""Storage interface.

The engine and the routers depend on this abstraction, never on a concrete
store. Step 3 adds a Postgres implementation behind the same interface (NFR-07),
so nothing above this line has to change.
"""

from abc import ABC, abstractmethod

from app.domain.models import ChangeLedger, ChangeOrder, Contract


class ContractRepository(ABC):
    """Reads and writes contracts and their change ledgers."""

    @abstractmethod
    def list_contracts(self) -> list[Contract]:
        """Return every contract."""

    @abstractmethod
    def get_contract(self, contract_id: str) -> Contract | None:
        """Return one contract, or None if it does not exist."""

    @abstractmethod
    def get_ledger(self, contract_id: str) -> ChangeLedger:
        """Return the change ledger for a contract, empty if it has no orders."""

    @abstractmethod
    def add_change_order(self, order: ChangeOrder) -> ChangeOrder:
        """Append a new change order. The ledger is append-only."""

    @abstractmethod
    def get_change_order(self, order_id: str) -> ChangeOrder | None:
        """Return one change order, or None."""

    @abstractmethod
    def replace_change_order(self, order: ChangeOrder) -> ChangeOrder:
        """Store a new revision of an existing order, keyed by its id."""

    @abstractmethod
    def next_change_order_id(self, contract_id: str) -> str:
        """Allocate the next change-order id for a contract."""

    @abstractmethod
    def reset(self) -> None:
        """Restore the seed state (FR-15)."""
