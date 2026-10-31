"""In-memory implementation of :class:`ContractRepository`.

Good enough for unit tests and a quick local run. NOT suitable for Vercel,
where functions keep no memory between requests (NFR-07).
"""

from app.domain.audit import AuditEvent
from app.domain.change_request import (
    ApprovalStep,
    ChangeRequest,
    ExecutionRecord,
    Notification,
    StageResult,
    VariationOrder,
)
from app.domain.enums import ApprovalDecision, CRState, Party, Role
from app.domain.models import ChangeLedger, ChangeOrder, Contract
from app.repositories.base import ContractRepository
from app.seed.demo_contract import build_demo_contracts
from app.seed.demo_requests import build_demo_requests


class InMemoryContractRepository(ContractRepository):
    """Holds everything in plain dicts.

    Domain models are frozen, so stored objects cannot be mutated by a caller
    that happens to hold a reference.
    """

    def __init__(self) -> None:
        self._contracts: dict[str, Contract] = {}
        self._orders: dict[str, ChangeOrder] = {}
        self._requests: dict[str, ChangeRequest] = {}
        self._steps: dict[str, list[ApprovalStep]] = {}
        self._stages: dict[str, list[StageResult]] = {}
        self._notifications: list[Notification] = []
        self._vos: dict[str, VariationOrder] = {}
        self._executions: dict[str, ExecutionRecord] = {}
        self._audit: list[AuditEvent] = []
        self._sequence = 0
        self.reset()

    def _next_id(self) -> int:
        self._sequence += 1
        return self._sequence

    # ---- contracts ----

    def list_contracts(self) -> list[Contract]:
        return list(self._contracts.values())

    def get_contract(self, contract_id: str) -> Contract | None:
        return self._contracts.get(contract_id)

    def add_contract(self, contract: Contract) -> Contract:
        if contract.id in self._contracts:
            msg = f"contract {contract.id} already exists"
            raise ValueError(msg)
        self._contracts[contract.id] = contract
        return contract

    # ---- ledger ----

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

    # ---- change requests ----

    def add_change_request(self, request: ChangeRequest) -> ChangeRequest:
        if request.id in self._requests:
            msg = f"change request {request.id} already exists"
            raise ValueError(msg)
        self._requests[request.id] = request
        return request

    def get_change_request(self, cr_id: str) -> ChangeRequest | None:
        return self._requests.get(cr_id)

    def list_change_requests(self, contract_id: str) -> list[ChangeRequest]:
        return sorted(
            (r for r in self._requests.values() if r.contract_id == contract_id),
            key=lambda r: (r.submitted_at, r.id),
        )

    def replace_change_request(self, request: ChangeRequest) -> ChangeRequest:
        if request.id not in self._requests:
            msg = f"change request {request.id} does not exist"
            raise ValueError(msg)
        self._requests[request.id] = request
        return request

    def next_change_request_id(self, contract_id: str) -> str:
        existing = sum(1 for r in self._requests.values() if r.contract_id == contract_id)
        return f"CR-{contract_id}-{existing + 1:03d}"

    # ---- approval chain ----

    def set_approval_chain(self, cr_id: str, steps: tuple[ApprovalStep, ...]) -> None:
        self._steps[cr_id] = [step.model_copy(update={"id": self._next_id()}) for step in steps]

    def list_approval_steps(self, cr_id: str) -> list[ApprovalStep]:
        return sorted(self._steps.get(cr_id, []), key=lambda s: s.position)

    def replace_approval_step(self, step: ApprovalStep) -> ApprovalStep:
        steps = self._steps.get(step.cr_id, [])
        for index, existing in enumerate(steps):
            if existing.position == step.position:
                steps[index] = step
                return step
        msg = f"approval step {step.position} not found for {step.cr_id}"
        raise ValueError(msg)

    def list_requests_in_state(self, state: CRState) -> list[ChangeRequest]:
        return sorted(
            (r for r in self._requests.values() if r.state is state),
            key=lambda r: (r.submitted_at, r.id),
        )

    def list_pending_steps(self) -> list[ApprovalStep]:
        return [
            step
            for steps in self._steps.values()
            for step in steps
            if step.decision is ApprovalDecision.PENDING
        ]

    # ---- trace ----

    def append_stage_results(self, results: list[StageResult]) -> None:
        for result in results:
            self._stages.setdefault(result.cr_id, []).append(
                result.model_copy(update={"id": self._next_id()})
            )

    def list_stage_results(self, cr_id: str) -> list[StageResult]:
        return list(self._stages.get(cr_id, []))

    # ---- notifications ----

    def append_notification(self, notification: Notification) -> Notification:
        stored = notification.model_copy(update={"id": self._next_id()})
        self._notifications.append(stored)
        return stored

    def list_notifications(self, party: Party, role: Role) -> list[Notification]:
        return sorted(
            (n for n in self._notifications if n.party is party and n.role is role),
            key=lambda n: (n.created_at, n.id or 0),
            reverse=True,
        )

    # ---- variation orders and execution ----

    def add_variation_order(self, vo: VariationOrder) -> VariationOrder:
        if vo.id in self._vos:
            msg = f"variation order {vo.id} already exists"
            raise ValueError(msg)
        self._vos[vo.id] = vo
        return vo

    def get_variation_order(self, vo_id: str) -> VariationOrder | None:
        return self._vos.get(vo_id)

    def get_variation_order_for_request(self, cr_id: str) -> VariationOrder | None:
        return next((v for v in self._vos.values() if v.cr_id == cr_id), None)

    def list_variation_orders(self, contract_id: str) -> list[VariationOrder]:
        return sorted(
            (v for v in self._vos.values() if v.contract_id == contract_id),
            key=lambda v: (v.issued_at, v.id),
        )

    def upsert_execution_record(self, record: ExecutionRecord) -> ExecutionRecord:
        existing = self._executions.get(record.vo_id)
        stored = record.model_copy(update={"id": existing.id if existing else self._next_id()})
        self._executions[record.vo_id] = stored
        return stored

    def get_execution_record(self, vo_id: str) -> ExecutionRecord | None:
        return self._executions.get(vo_id)

    # ---- audit ----

    def append_audit(self, event: AuditEvent) -> AuditEvent:
        stored = event.model_copy(update={"id": len(self._audit) + 1})
        self._audit.append(stored)
        return stored

    def list_audit(self, contract_id: str) -> list[AuditEvent]:
        return [e for e in self._audit if e.contract_id == contract_id]

    # ---- demo ----

    def reset(self) -> None:
        """Restore the seed. Audit history is deliberately kept.

        Contracts created through ``POST /api/contracts`` are dropped: only
        the seed contracts survive a reset. Their audit rows remain.
        """
        self._contracts = {c.id: c for c in build_demo_contracts()}
        self._orders = {}
        self._requests = {r.id: r for r in build_demo_requests()}
        self._steps = {}
        self._stages = {}
        self._notifications = []
        self._vos = {}
        self._executions = {}
