"""Postgres implementation of :class:`ContractRepository`.

Satisfies NFR-07: no state lives in process memory, so it survives the frozen
and thawed lifecycle of a Vercel Function. Each method runs in its own short
transaction via ``session_scope``.

Money crosses this boundary as ``Decimal`` in both directions - the columns are
NUMERIC and SQLAlchemy is configured with ``asdecimal=True``.
"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.engine import session_scope
from app.db.tables import AuditLogRow, ChangeOrderRow, ContractItemRow, ContractRow
from app.domain.audit import AuditEvent
from app.domain.enums import ChangeCategory, OrderStatus
from app.domain.models import ChangeLedger, ChangeOrder, Contract, ContractItem
from app.repositories.base import ContractRepository
from app.seed.demo_contract import build_demo_contract


def _to_contract(row: ContractRow) -> Contract:
    return Contract(
        id=row.id,
        title_ar=row.title_ar,
        entity_name=row.entity_name,
        contractor_name=row.contractor_name,
        original_value=row.original_value,
        items=tuple(
            ContractItem(
                id=item.id,
                description_ar=item.description_ar,
                quantity=item.quantity,
                unit_price=item.unit_price,
                total=item.total,
            )
            for item in row.items
        ),
        start_date=row.start_date,
        end_date=row.end_date,
    )


def _to_order(row: ChangeOrderRow) -> ChangeOrder:
    return ChangeOrder(
        id=row.id,
        contract_id=row.contract_id,
        type=ChangeCategory(row.type),
        value=row.value,
        related_item_ids=tuple(row.related_item_ids),
        description_ar=row.description_ar,
        status=OrderStatus(row.status),
        has_written_assignment=row.has_written_assignment,
        contractor_consent=row.contractor_consent,
        created_at=row.created_at,
        decided_by=row.decided_by,
        decision_reason=row.decision_reason,
    )


def _to_audit(row: AuditLogRow) -> AuditEvent:
    return AuditEvent(
        id=row.id,
        occurred_at=row.occurred_at,
        actor_role=row.actor_role,
        action=row.action,
        entity_type=row.entity_type,
        entity_id=row.entity_id,
        contract_id=row.contract_id,
        previous_state=OrderStatus(row.previous_state) if row.previous_state else None,
        new_state=OrderStatus(row.new_state) if row.new_state else None,
        reason=row.reason,
    )


def _order_values(order: ChangeOrder) -> dict[str, object]:
    return {
        "contract_id": order.contract_id,
        "type": order.type.value,
        "value": order.value,
        "related_item_ids": list(order.related_item_ids),
        "description_ar": order.description_ar,
        "status": order.status.value,
        "has_written_assignment": order.has_written_assignment,
        "contractor_consent": order.contractor_consent,
        "created_at": order.created_at,
        "decided_by": order.decided_by,
        "decision_reason": order.decision_reason,
    }


class PostgresContractRepository(ContractRepository):
    """Durable store backed by Postgres."""

    def list_contracts(self) -> list[Contract]:
        with session_scope() as session:
            rows = session.scalars(select(ContractRow).order_by(ContractRow.id)).all()
            return [_to_contract(row) for row in rows]

    def get_contract(self, contract_id: str) -> Contract | None:
        with session_scope() as session:
            row = session.get(ContractRow, contract_id)
            return None if row is None else _to_contract(row)

    def get_ledger(self, contract_id: str) -> ChangeLedger:
        with session_scope() as session:
            rows = session.scalars(
                select(ChangeOrderRow)
                .where(ChangeOrderRow.contract_id == contract_id)
                .order_by(ChangeOrderRow.created_at, ChangeOrderRow.id)
            ).all()
            return ChangeLedger(
                contract_id=contract_id, orders=tuple(_to_order(row) for row in rows)
            )

    def add_change_order(self, order: ChangeOrder) -> ChangeOrder:
        with session_scope() as session:
            if session.get(ChangeOrderRow, order.id) is not None:
                msg = f"change order {order.id} already exists"
                raise ValueError(msg)
            session.add(ChangeOrderRow(id=order.id, **_order_values(order)))
        return order

    def get_change_order(self, order_id: str) -> ChangeOrder | None:
        with session_scope() as session:
            row = session.get(ChangeOrderRow, order_id)
            return None if row is None else _to_order(row)

    def replace_change_order(self, order: ChangeOrder) -> ChangeOrder:
        with session_scope() as session:
            row = session.get(ChangeOrderRow, order.id)
            if row is None:
                msg = f"change order {order.id} does not exist"
                raise ValueError(msg)
            for field, value in _order_values(order).items():
                setattr(row, field, value)
        return order

    def next_change_order_id(self, contract_id: str) -> str:
        with session_scope() as session:
            existing = session.scalar(
                select(func.count())
                .select_from(ChangeOrderRow)
                .where(ChangeOrderRow.contract_id == contract_id)
            )
            return f"CO-{contract_id}-{(existing or 0) + 1:03d}"

    def append_audit(self, event: AuditEvent) -> AuditEvent:
        """INSERT only. This class has no update or delete path for audit_log."""
        with session_scope() as session:
            row = AuditLogRow(
                occurred_at=event.occurred_at,
                actor_role=event.actor_role,
                action=event.action.value,
                entity_type=event.entity_type,
                entity_id=event.entity_id,
                contract_id=event.contract_id,
                previous_state=event.previous_state.value if event.previous_state else None,
                new_state=event.new_state.value if event.new_state else None,
                reason=event.reason,
            )
            session.add(row)
            session.flush()
            return event.model_copy(update={"id": row.id})

    def list_audit(self, contract_id: str) -> list[AuditEvent]:
        with session_scope() as session:
            rows = session.scalars(
                select(AuditLogRow)
                .where(AuditLogRow.contract_id == contract_id)
                .order_by(AuditLogRow.occurred_at, AuditLogRow.id)
            ).all()
            return [_to_audit(row) for row in rows]

    def reset(self) -> None:
        """Restore the seed contract and drop change orders.

        Audit rows are deliberately left alone: the log is append-only, so a
        reset is itself an event rather than an erasure.
        """
        with session_scope() as session:
            session.query(ChangeOrderRow).delete()
            session.query(ContractRow).delete()
            session.flush()
            _insert_contract(session, build_demo_contract())


def _insert_contract(session: Session, contract: Contract) -> None:
    """Insert a contract and its items."""
    session.add(
        ContractRow(
            id=contract.id,
            title_ar=contract.title_ar,
            entity_name=contract.entity_name,
            contractor_name=contract.contractor_name,
            original_value=contract.original_value,
            start_date=contract.start_date,
            end_date=contract.end_date,
            items=[
                ContractItemRow(
                    contract_id=contract.id,
                    id=item.id,
                    description_ar=item.description_ar,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    total=item.total,
                )
                for item in contract.items
            ],
        )
    )


def seed_contract(contract: Contract) -> bool:
    """Idempotently ensure ``contract`` exists. Returns True if it was inserted."""
    with session_scope() as session:
        if session.get(ContractRow, contract.id) is not None:
            return False
        _insert_contract(session, contract)
        return True
