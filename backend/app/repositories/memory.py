"""In-memory implementation of :class:`ContractRepository`.

Good enough for local development and tests. It is NOT suitable for Vercel,
where functions keep no memory between requests (NFR-07) - Step 3 replaces it
with Postgres behind the same interface.
"""

from app.domain.audit import AuditEvent
from app.domain.models import ChangeLedger, ChangeOrder, Contract
from app.repositories.base import ContractRepository
from app.seed.demo_contract import build_demo_contract


class InMemoryContractRepository(ContractRepository):
    """Holds contracts and orders in plain dicts.

    Domain models are frozen, so stored objects cannot be mutated by a caller
    that happens to hold a reference.
    """

    def __init__(self) -> None:
        self._contracts: dict[str, Contract] = {}
        self._orders: dict[str, ChangeOrder] = {}
        self._audit: list[AuditEvent] = []
        self.reset()

    def list_contracts(self) -> list[Contract]:
        return list(self._contracts.values())

    def get_contract(self, contract_id: str) -> Contract | None:
        return self._contracts.get(contract_id)

    def get_ledger(self, contract_id: str) -> ChangeLedger:
        orders = tuple(o for o in self._orders.values() if o.contract_id == contract_id)
        return ChangeLedger(
            contract_id=contract_id,
            orders=tuple(sorted(orders, key=lambda o: (o.created_at, o.id))),
        )

    def add_change_order(self, order: ChangeOrder) -> ChangeOrder:
        if order.id in self._orders:
            msg = f"change order {order.id} already exists"
            raise ValueError(msg)
        self._orders[order.id] = order
        return order

    def get_change_order(self, order_id: str) -> ChangeOrder | None:
        return self._orders.get(order_id)

    def replace_change_order(self, order: ChangeOrder) -> ChangeOrder:
        if order.id not in self._orders:
            msg = f"change order {order.id} does not exist"
            raise ValueError(msg)
        self._orders[order.id] = order
        return order

    def next_change_order_id(self, contract_id: str) -> str:
        existing = sum(1 for o in self._orders.values() if o.contract_id == contract_id)
        return f"CO-{contract_id}-{existing + 1:03d}"

    def append_audit(self, event: AuditEvent) -> AuditEvent:
        stored = event.model_copy(update={"id": len(self._audit) + 1})
        self._audit.append(stored)
        return stored

    def list_audit(self, contract_id: str) -> list[AuditEvent]:
        return [e for e in self._audit if e.contract_id == contract_id]

    def reset(self) -> None:
        """Restore the seed contract. Audit history is deliberately kept."""
        contract = build_demo_contract()
        self._contracts = {contract.id: contract}
        self._orders = {}
