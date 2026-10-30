"""One test suite, run against both repository implementations.

If the Postgres store and the in-memory store ever diverge, these fail. That is
what lets Step 3 swap the backing store without touching the engine, the
services or the routers (NFR-07, NFR-11).
"""

from datetime import UTC, datetime
from decimal import Decimal

from app.domain.audit import AuditAction, AuditEvent
from app.domain.enums import ChangeCategory, OrderStatus, Party
from app.domain.models import ChangeOrder
from app.repositories.base import ContractRepository
from app.seed.demo_contract import DEMO_CONTRACT_ID

_NOW = datetime(2027, 3, 1, 8, 30, tzinfo=UTC)


def make_order(
    order_id: str,
    value: str = "1000",
    status: OrderStatus = OrderStatus.DRAFT,
    minute: int = 0,
) -> ChangeOrder:
    return ChangeOrder(
        id=order_id,
        contract_id=DEMO_CONTRACT_ID,
        type=ChangeCategory.NEW_ITEMS,
        value=Decimal(value),
        related_item_ids=(),
        description_ar="بند جديد",
        status=status,
        created_at=_NOW.replace(minute=minute),
    )


def audit_event(action: AuditAction, entity_id: str, reason: str | None = None) -> AuditEvent:
    return AuditEvent(
        occurred_at=_NOW,
        actor_role=Party.CONTRACTOR.value,
        action=action,
        entity_type="change_order",
        entity_id=entity_id,
        contract_id=DEMO_CONTRACT_ID,
        previous_state=OrderStatus.DRAFT,
        new_state=OrderStatus.REJECTED,
        reason=reason,
    )


def test_seed_contract_round_trips(repository: ContractRepository) -> None:
    contract = repository.get_contract(DEMO_CONTRACT_ID)
    assert contract is not None
    assert contract.original_value == Decimal("4800000")
    assert len(contract.items) == 8
    # the model validator re-checks that items sum to the contract value
    assert sum((i.total for i in contract.items), Decimal("0")) == contract.original_value


def test_arabic_survives_the_round_trip(repository: ContractRepository) -> None:
    contract = repository.get_contract(DEMO_CONTRACT_ID)
    assert contract is not None
    assert contract.entity_name == "أمانة منطقة الواحة"
    assert contract.items[0].description_ar == "تحليل المتطلبات وتصميم معمارية النظام"


def test_money_keeps_exact_decimal_precision(repository: ContractRepository) -> None:
    """NUMERIC in, Decimal out - a float would lose this (NFR-01)."""
    awkward = "123456.789012"
    repository.add_change_order(make_order("CO-PRECISE", value=awkward))
    stored = repository.get_change_order("CO-PRECISE")
    assert stored is not None
    assert stored.value == Decimal(awkward)
    assert isinstance(stored.value, Decimal)


def test_list_contracts(repository: ContractRepository) -> None:
    assert [c.id for c in repository.list_contracts()] == [DEMO_CONTRACT_ID]


def test_unknown_lookups_return_none(repository: ContractRepository) -> None:
    assert repository.get_contract("NOPE") is None
    assert repository.get_change_order("NOPE") is None
    assert repository.get_ledger("NOPE").orders == ()


def test_change_order_crud(repository: ContractRepository) -> None:
    repository.add_change_order(make_order("CO-1"))
    assert repository.get_change_order("CO-1") is not None

    updated = make_order("CO-1", status=OrderStatus.APPROVED)
    repository.replace_change_order(updated)
    stored = repository.get_change_order("CO-1")
    assert stored is not None
    assert stored.status is OrderStatus.APPROVED


def test_duplicate_insert_is_rejected(repository: ContractRepository) -> None:
    repository.add_change_order(make_order("CO-DUP"))
    try:
        repository.add_change_order(make_order("CO-DUP"))
    except ValueError as error:
        assert "already exists" in str(error)
    else:  # pragma: no cover - guards against a silent overwrite
        raise AssertionError("expected a ValueError on duplicate insert")


def test_replacing_a_missing_order_is_rejected(repository: ContractRepository) -> None:
    try:
        repository.replace_change_order(make_order("CO-GHOST"))
    except ValueError as error:
        assert "does not exist" in str(error)
    else:  # pragma: no cover
        raise AssertionError("expected a ValueError when replacing a missing order")


def test_ledger_is_ordered_by_creation(repository: ContractRepository) -> None:
    repository.add_change_order(make_order("CO-B", minute=20))
    repository.add_change_order(make_order("CO-A", minute=5))
    assert [o.id for o in repository.get_ledger(DEMO_CONTRACT_ID).orders] == ["CO-A", "CO-B"]


def test_next_change_order_id_increments(repository: ContractRepository) -> None:
    first = repository.next_change_order_id(DEMO_CONTRACT_ID)
    repository.add_change_order(make_order(first))
    second = repository.next_change_order_id(DEMO_CONTRACT_ID)
    assert first != second
    assert first.endswith("001")
    assert second.endswith("002")


def test_audit_is_append_only_and_ordered(repository: ContractRepository) -> None:
    repository.append_audit(audit_event(AuditAction.ORDER_CREATED, "CO-1"))
    repository.append_audit(audit_event(AuditAction.ORDER_REJECTED, "CO-1", "لا يوجد اعتماد"))

    events = repository.list_audit(DEMO_CONTRACT_ID)
    assert [e.action for e in events] == [
        AuditAction.ORDER_CREATED,
        AuditAction.ORDER_REJECTED,
    ]
    assert events[1].reason == "لا يوجد اعتماد"
    assert all(e.id is not None for e in events)


def test_audit_is_scoped_to_its_contract(repository: ContractRepository) -> None:
    repository.append_audit(audit_event(AuditAction.ORDER_CREATED, "CO-1"))
    assert repository.list_audit("SOME-OTHER-CONTRACT") == []


def test_repository_exposes_no_audit_mutation_path() -> None:
    """FR-13: the interface offers append and read, and nothing else."""
    names = {n for n in dir(ContractRepository) if "audit" in n.lower()}
    assert names == {"append_audit", "list_audit"}


def test_reset_restores_seed_but_keeps_audit(repository: ContractRepository) -> None:
    """FR-15: a reset clears working state; FR-13: it never erases history."""
    repository.add_change_order(make_order("CO-1"))
    repository.append_audit(audit_event(AuditAction.ORDER_CREATED, "CO-1"))

    repository.reset()

    assert repository.get_ledger(DEMO_CONTRACT_ID).orders == ()
    assert repository.get_contract(DEMO_CONTRACT_ID) is not None
    assert len(repository.list_audit(DEMO_CONTRACT_ID)) == 1
