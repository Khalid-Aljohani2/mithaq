"""Postgres implementation of :class:`ContractRepository`.

Satisfies NFR-07: no state lives in process memory, so it survives the frozen
and thawed lifecycle of a Vercel Function. Each method runs in its own short
transaction via ``session_scope``.

Money crosses this boundary as ``Decimal`` in both directions - the columns are
NUMERIC and SQLAlchemy is configured with ``asdecimal=True``.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.engine import session_scope
from app.db.tables import (
    ApprovalStepRow,
    AuditLogRow,
    BreakdownLineRow,
    ChangeOrderRow,
    ChangeRequestRow,
    ContractRow,
    ExecutionRecordRow,
    NotificationRow,
    StageResultRow,
    VariationOrderRow,
)
from app.domain.audit import AuditEvent
from app.domain.change_request import (
    ApprovalStep,
    ChangeRequest,
    ExecutionRecord,
    Notification,
    Signature,
    StageResult,
    VariationOrder,
)
from app.domain.enums import (
    ApprovalDecision,
    ChangeCategory,
    ChangeKind,
    ContractType,
    CRState,
    ImpactType,
    OrderStatus,
    Party,
    Recommendation,
    Role,
    Stage,
)
from app.domain.models import BreakdownLine, ChangeLedger, ChangeOrder, Contract
from app.repositories.base import ContractRepository
from app.seed.demo_contract import build_demo_contracts
from app.seed.demo_requests import build_demo_requests


def _to_contract(row: ContractRow) -> Contract:
    return Contract(
        id=row.id,
        title_ar=row.title_ar,
        entity_name=row.entity_name,
        contractor_name=row.contractor_name,
        contract_type=ContractType(row.contract_type),
        original_value=row.original_value,
        breakdown=tuple(
            BreakdownLine(
                id=line.id,
                description_ar=line.description_ar,
                unit_ar=line.unit_ar,
                quantity=line.quantity,
                unit_rate=line.unit_rate,
                total=line.total,
                approved_product_ar=line.approved_product_ar,
                restrictions_ar=tuple(line.restrictions_ar),
            )
            for line in row.breakdown
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
        decided_by=Party(row.decided_by) if row.decided_by else None,
        decision_reason=row.decision_reason,
        change_request_id=row.change_request_id,
    )


def _order_values(order: ChangeOrder) -> dict[str, Any]:
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
        "decided_by": order.decided_by.value if order.decided_by else None,
        "decision_reason": order.decision_reason,
        "change_request_id": order.change_request_id,
    }


def _to_request(row: ChangeRequestRow) -> ChangeRequest:
    return ChangeRequest(
        id=row.id,
        contract_id=row.contract_id,
        requester_name=row.requester_name,
        requester_party=Party(row.requester_party),
        submitted_at=row.submitted_at,
        body_ar=row.body_ar,
        attachments=tuple(row.attachments),
        human_entered_amount=row.human_entered_amount,
        human_entered_unit_rate=row.human_entered_unit_rate,
        human_entered_days=row.human_entered_days,
        state=CRState(row.state),
        kind=ChangeKind(row.kind) if row.kind else None,
        impact_type=ImpactType(row.impact_type) if row.impact_type else None,
        matched_line_ids=tuple(row.matched_line_ids),
        cost_impact=row.cost_impact,
        added_value=row.added_value,
        removed_value=row.removed_value,
        time_impact_days=row.time_impact_days,
        recommendation=Recommendation(row.recommendation) if row.recommendation else None,
        confidence=row.confidence,
        changes_approved_product=row.changes_approved_product,
        policy_exception_required=row.policy_exception_required,
        needs_legal_review=row.needs_legal_review,
        legally_blocked=row.legally_blocked,
        unit_rate_flagged=row.unit_rate_flagged,
        rate_human_entered=row.rate_human_entered,
        revision_count=row.revision_count,
        closed_reason=row.closed_reason,
    )


def _request_values(request: ChangeRequest) -> dict[str, Any]:
    return {
        "contract_id": request.contract_id,
        "requester_name": request.requester_name,
        "requester_party": request.requester_party.value,
        "submitted_at": request.submitted_at,
        "body_ar": request.body_ar,
        "attachments": list(request.attachments),
        "human_entered_amount": request.human_entered_amount,
        "human_entered_unit_rate": request.human_entered_unit_rate,
        "human_entered_days": request.human_entered_days,
        "state": request.state.value,
        "kind": request.kind.value if request.kind else None,
        "impact_type": request.impact_type.value if request.impact_type else None,
        "matched_line_ids": list(request.matched_line_ids),
        "cost_impact": request.cost_impact,
        "added_value": request.added_value,
        "removed_value": request.removed_value,
        "time_impact_days": request.time_impact_days,
        "recommendation": request.recommendation.value if request.recommendation else None,
        "confidence": request.confidence,
        "changes_approved_product": request.changes_approved_product,
        "policy_exception_required": request.policy_exception_required,
        "needs_legal_review": request.needs_legal_review,
        "legally_blocked": request.legally_blocked,
        "unit_rate_flagged": request.unit_rate_flagged,
        "rate_human_entered": request.rate_human_entered,
        "revision_count": request.revision_count,
        "closed_reason": request.closed_reason,
    }


def _to_step(row: ApprovalStepRow) -> ApprovalStep:
    return ApprovalStep(
        id=row.id,
        cr_id=row.cr_id,
        position=row.position,
        party=Party(row.party),
        role=Role(row.role),
        reason_code=row.reason_code,
        decision=ApprovalDecision(row.decision),
        decided_by=row.decided_by,
        decided_at=row.decided_at,
        reason=row.reason,
        created_at=row.created_at,
    )


def _to_stage(row: StageResultRow) -> StageResult:
    from app.domain.enums import ActorType

    return StageResult(
        id=row.id,
        cr_id=row.cr_id,
        stage=Stage(row.stage),
        stage_no=row.stage_no,
        actor_type=ActorType(row.actor_type),
        provider=row.provider,
        recorded=row.recorded,
        started_at=row.started_at,
        finished_at=row.finished_at,
        duration_ms=row.duration_ms,
        status=row.status,
        summary_ar=row.summary_ar,
        summary_en=row.summary_en,
        payload=row.payload,
    )


def _to_notification(row: NotificationRow) -> Notification:
    from app.domain.enums import NotificationKind

    return Notification(
        id=row.id,
        cr_id=row.cr_id,
        contract_id=row.contract_id,
        party=Party(row.party),
        role=Role(row.role),
        kind=NotificationKind(row.kind),
        message_ar=row.message_ar,
        message_en=row.message_en,
        created_at=row.created_at,
        is_reminder=row.is_reminder,
    )


def _to_vo(row: VariationOrderRow) -> VariationOrder:
    return VariationOrder(
        id=row.id,
        cr_id=row.cr_id,
        contract_id=row.contract_id,
        number=row.number,
        issued_at=row.issued_at,
        scope_ar=row.scope_ar,
        scope_en=row.scope_en,
        value=row.value,
        time_extension_days=row.time_extension_days,
        cited_line_ids=tuple(row.cited_line_ids),
        cited_articles=tuple(row.cited_articles),
        signatures=tuple(
            Signature(
                party=Party(s["party"]),
                role=Role(s["role"]),
                decided_by=s["decided_by"],
                decided_at=datetime.fromisoformat(s["decided_at"]),
            )
            for s in row.signatures
        ),
        recorded=row.recorded,
    )


def _to_execution(row: ExecutionRecordRow) -> ExecutionRecord:
    return ExecutionRecord(
        id=row.id,
        vo_id=row.vo_id,
        cr_id=row.cr_id,
        contract_id=row.contract_id,
        actual_cost=row.actual_cost,
        actual_start=row.actual_start,
        actual_end=row.actual_end,
        cost_deviation=row.cost_deviation,
        schedule_deviation_days=row.schedule_deviation_days,
        acceptance_verified=row.acceptance_verified,
        closed_out_at=row.closed_out_at,
        lessons_learned_ar=row.lessons_learned_ar,
        notes_ar=row.notes_ar,
    )


def _to_audit(row: AuditLogRow) -> AuditEvent:
    return AuditEvent(
        id=row.id,
        occurred_at=row.occurred_at,
        actor_role=row.actor_role,
        actor_party=row.actor_party,
        actor_name=row.actor_name,
        action=row.action,
        entity_type=row.entity_type,
        entity_id=row.entity_id,
        contract_id=row.contract_id,
        previous_state=CRState(row.previous_state) if row.previous_state else None,
        new_state=CRState(row.new_state) if row.new_state else None,
        reason=row.reason,
    )


class PostgresContractRepository(ContractRepository):
    """Durable store backed by Postgres."""

    # ---- contracts ----

    def list_contracts(self) -> list[Contract]:
        with session_scope() as session:
            rows = session.scalars(select(ContractRow).order_by(ContractRow.id)).all()
            return [_to_contract(row) for row in rows]

    def get_contract(self, contract_id: str) -> Contract | None:
        with session_scope() as session:
            row = session.get(ContractRow, contract_id)
            return None if row is None else _to_contract(row)

    def add_contract(self, contract: Contract) -> Contract:
        with session_scope() as session:
            if session.get(ContractRow, contract.id) is not None:
                msg = f"contract {contract.id} already exists"
                raise ValueError(msg)
            _insert_contract(session, contract)
        return contract

    # ---- ledger ----

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

    # ---- change requests ----

    def add_change_request(self, request: ChangeRequest) -> ChangeRequest:
        with session_scope() as session:
            if session.get(ChangeRequestRow, request.id) is not None:
                msg = f"change request {request.id} already exists"
                raise ValueError(msg)
            session.add(ChangeRequestRow(id=request.id, **_request_values(request)))
        return request

    def get_change_request(self, cr_id: str) -> ChangeRequest | None:
        with session_scope() as session:
            row = session.get(ChangeRequestRow, cr_id)
            return None if row is None else _to_request(row)

    def list_change_requests(self, contract_id: str) -> list[ChangeRequest]:
        with session_scope() as session:
            rows = session.scalars(
                select(ChangeRequestRow)
                .where(ChangeRequestRow.contract_id == contract_id)
                .order_by(ChangeRequestRow.submitted_at, ChangeRequestRow.id)
            ).all()
            return [_to_request(row) for row in rows]

    def replace_change_request(self, request: ChangeRequest) -> ChangeRequest:
        with session_scope() as session:
            row = session.get(ChangeRequestRow, request.id)
            if row is None:
                msg = f"change request {request.id} does not exist"
                raise ValueError(msg)
            for field, value in _request_values(request).items():
                setattr(row, field, value)
        return request

    def next_change_request_id(self, contract_id: str) -> str:
        with session_scope() as session:
            existing = session.scalar(
                select(func.count())
                .select_from(ChangeRequestRow)
                .where(ChangeRequestRow.contract_id == contract_id)
            )
            return f"CR-{contract_id}-{(existing or 0) + 1:03d}"

    # ---- approval chain ----

    def set_approval_chain(self, cr_id: str, steps: tuple[ApprovalStep, ...]) -> None:
        with session_scope() as session:
            session.query(ApprovalStepRow).filter(ApprovalStepRow.cr_id == cr_id).delete()
            session.flush()
            for step in steps:
                session.add(
                    ApprovalStepRow(
                        cr_id=step.cr_id,
                        position=step.position,
                        party=step.party.value,
                        role=step.role.value,
                        reason_code=step.reason_code,
                        decision=step.decision.value,
                        decided_by=step.decided_by,
                        decided_at=step.decided_at,
                        reason=step.reason,
                        created_at=step.created_at,
                    )
                )

    def list_approval_steps(self, cr_id: str) -> list[ApprovalStep]:
        with session_scope() as session:
            rows = session.scalars(
                select(ApprovalStepRow)
                .where(ApprovalStepRow.cr_id == cr_id)
                .order_by(ApprovalStepRow.position)
            ).all()
            return [_to_step(row) for row in rows]

    def replace_approval_step(self, step: ApprovalStep) -> ApprovalStep:
        with session_scope() as session:
            row = session.scalar(
                select(ApprovalStepRow).where(
                    ApprovalStepRow.cr_id == step.cr_id,
                    ApprovalStepRow.position == step.position,
                )
            )
            if row is None:
                msg = f"approval step {step.position} not found for {step.cr_id}"
                raise ValueError(msg)
            row.decision = step.decision.value
            row.decided_by = step.decided_by
            row.decided_at = step.decided_at
            row.reason = step.reason
        return step

    def list_requests_in_state(self, state: CRState) -> list[ChangeRequest]:
        with session_scope() as session:
            rows = session.scalars(
                select(ChangeRequestRow)
                .where(ChangeRequestRow.state == state.value)
                .order_by(ChangeRequestRow.submitted_at, ChangeRequestRow.id)
            ).all()
            return [_to_request(row) for row in rows]

    def list_pending_steps(self) -> list[ApprovalStep]:
        with session_scope() as session:
            rows = session.scalars(
                select(ApprovalStepRow)
                .where(ApprovalStepRow.decision == ApprovalDecision.PENDING.value)
                .order_by(ApprovalStepRow.cr_id, ApprovalStepRow.position)
            ).all()
            return [_to_step(row) for row in rows]

    # ---- trace ----

    def append_stage_results(self, results: list[StageResult]) -> None:
        with session_scope() as session:
            for result in results:
                session.add(
                    StageResultRow(
                        cr_id=result.cr_id,
                        stage=result.stage.value,
                        stage_no=result.stage_no,
                        actor_type=result.actor_type.value,
                        provider=result.provider,
                        recorded=result.recorded,
                        started_at=result.started_at,
                        finished_at=result.finished_at,
                        duration_ms=result.duration_ms,
                        status=result.status,
                        summary_ar=result.summary_ar,
                        summary_en=result.summary_en,
                        payload=result.payload,
                    )
                )

    def list_stage_results(self, cr_id: str) -> list[StageResult]:
        with session_scope() as session:
            rows = session.scalars(
                select(StageResultRow)
                .where(StageResultRow.cr_id == cr_id)
                .order_by(StageResultRow.id)
            ).all()
            return [_to_stage(row) for row in rows]

    # ---- notifications ----

    def append_notification(self, notification: Notification) -> Notification:
        with session_scope() as session:
            row = NotificationRow(
                cr_id=notification.cr_id,
                contract_id=notification.contract_id,
                party=notification.party.value,
                role=notification.role.value,
                kind=notification.kind.value,
                message_ar=notification.message_ar,
                message_en=notification.message_en,
                created_at=notification.created_at,
                is_reminder=notification.is_reminder,
            )
            session.add(row)
            session.flush()
            return notification.model_copy(update={"id": row.id})

    def list_notifications(self, party: Party, role: Role) -> list[Notification]:
        with session_scope() as session:
            rows = session.scalars(
                select(NotificationRow)
                .where(NotificationRow.party == party.value, NotificationRow.role == role.value)
                .order_by(NotificationRow.created_at.desc(), NotificationRow.id.desc())
            ).all()
            return [_to_notification(row) for row in rows]

    # ---- variation orders and execution ----

    def add_variation_order(self, vo: VariationOrder) -> VariationOrder:
        with session_scope() as session:
            if session.get(VariationOrderRow, vo.id) is not None:
                msg = f"variation order {vo.id} already exists"
                raise ValueError(msg)
            session.add(
                VariationOrderRow(
                    id=vo.id,
                    cr_id=vo.cr_id,
                    contract_id=vo.contract_id,
                    number=vo.number,
                    issued_at=vo.issued_at,
                    scope_ar=vo.scope_ar,
                    scope_en=vo.scope_en,
                    value=vo.value,
                    time_extension_days=vo.time_extension_days,
                    cited_line_ids=list(vo.cited_line_ids),
                    cited_articles=list(vo.cited_articles),
                    signatures=[
                        {
                            "party": s.party.value,
                            "role": s.role.value,
                            "decided_by": s.decided_by,
                            "decided_at": s.decided_at.isoformat(),
                        }
                        for s in vo.signatures
                    ],
                    recorded=vo.recorded,
                )
            )
        return vo

    def get_variation_order(self, vo_id: str) -> VariationOrder | None:
        with session_scope() as session:
            row = session.get(VariationOrderRow, vo_id)
            return None if row is None else _to_vo(row)

    def get_variation_order_for_request(self, cr_id: str) -> VariationOrder | None:
        with session_scope() as session:
            row = session.scalars(
                select(VariationOrderRow)
                .where(VariationOrderRow.cr_id == cr_id)
                .order_by(VariationOrderRow.issued_at, VariationOrderRow.id)
            ).first()
            return None if row is None else _to_vo(row)

    def list_variation_orders(self, contract_id: str) -> list[VariationOrder]:
        with session_scope() as session:
            rows = session.scalars(
                select(VariationOrderRow)
                .where(VariationOrderRow.contract_id == contract_id)
                .order_by(VariationOrderRow.issued_at, VariationOrderRow.id)
            ).all()
            return [_to_vo(row) for row in rows]

    def upsert_execution_record(self, record: ExecutionRecord) -> ExecutionRecord:
        with session_scope() as session:
            row = session.scalar(
                select(ExecutionRecordRow).where(ExecutionRecordRow.vo_id == record.vo_id)
            )
            if row is None:
                row = ExecutionRecordRow(vo_id=record.vo_id)
                session.add(row)
            row.cr_id = record.cr_id
            row.contract_id = record.contract_id
            row.actual_cost = record.actual_cost
            row.actual_start = record.actual_start
            row.actual_end = record.actual_end
            row.cost_deviation = record.cost_deviation
            row.schedule_deviation_days = record.schedule_deviation_days
            row.acceptance_verified = record.acceptance_verified
            row.closed_out_at = record.closed_out_at
            row.lessons_learned_ar = record.lessons_learned_ar
            row.notes_ar = record.notes_ar
            session.flush()
            return record.model_copy(update={"id": row.id})

    def get_execution_record(self, vo_id: str) -> ExecutionRecord | None:
        with session_scope() as session:
            row = session.scalar(
                select(ExecutionRecordRow).where(ExecutionRecordRow.vo_id == vo_id)
            )
            return None if row is None else _to_execution(row)

    # ---- audit ----

    def append_audit(self, event: AuditEvent) -> AuditEvent:
        """INSERT only. This class has no update or delete path for audit_log."""
        with session_scope() as session:
            row = AuditLogRow(
                occurred_at=event.occurred_at,
                actor_role=event.actor_role,
                actor_party=event.actor_party,
                actor_name=event.actor_name,
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

    # ---- demo ----

    def reset(self) -> None:
        """Restore the seed. Audit rows are deliberately left alone (FR-13).

        Every contract row is deleted, including contracts created through
        ``POST /api/contracts``; only the seed contracts are re-inserted. The
        audit rows of a dropped contract remain (the log is append-only).
        """
        with session_scope() as session:
            for table in (
                ExecutionRecordRow,
                VariationOrderRow,
                NotificationRow,
                StageResultRow,
                ApprovalStepRow,
                ChangeRequestRow,
                ChangeOrderRow,
                ContractRow,
            ):
                session.query(table).delete()
            session.flush()
            for contract in build_demo_contracts():
                _insert_contract(session, contract)
            session.flush()
            for request in build_demo_requests():
                session.add(ChangeRequestRow(id=request.id, **_request_values(request)))


def _insert_contract(session: Session, contract: Contract) -> None:
    """Insert a contract and its breakdown."""
    session.add(
        ContractRow(
            id=contract.id,
            title_ar=contract.title_ar,
            entity_name=contract.entity_name,
            contractor_name=contract.contractor_name,
            contract_type=contract.contract_type.value,
            original_value=contract.original_value,
            start_date=contract.start_date,
            end_date=contract.end_date,
            breakdown=[
                BreakdownLineRow(
                    contract_id=contract.id,
                    id=line.id,
                    description_ar=line.description_ar,
                    unit_ar=line.unit_ar,
                    quantity=line.quantity,
                    unit_rate=line.unit_rate,
                    total=line.total,
                    approved_product_ar=line.approved_product_ar,
                    restrictions_ar=list(line.restrictions_ar),
                )
                for line in contract.breakdown
            ],
        )
    )


def seed_all() -> dict[str, int]:
    """Idempotently ensure the demo contracts and requests exist, and are whole.

    "Present" is not the same as "correct". A contract row can survive a
    migration that drops its breakdown table, leaving a row with no lines -
    which fails ``Contract``'s validator (the lines must sum to the contract
    value) and turns every read of that contract into a 500. A loader that only
    checks for the row's existence skips it forever, so this repairs it.
    """
    inserted = {"contracts": 0, "repaired": 0, "change_requests": 0}
    with session_scope() as session:
        for contract in build_demo_contracts():
            row = session.get(ContractRow, contract.id)
            if row is None:
                _insert_contract(session, contract)
                inserted["contracts"] += 1
            elif len(row.breakdown) != len(contract.breakdown):
                # Rebuild the breakdown from the seed. The relationship is
                # delete-orphan, so clearing it removes the stale rows.
                row.breakdown.clear()
                session.flush()
                row.breakdown = [
                    BreakdownLineRow(
                        contract_id=contract.id,
                        id=line.id,
                        description_ar=line.description_ar,
                        unit_ar=line.unit_ar,
                        quantity=line.quantity,
                        unit_rate=line.unit_rate,
                        total=line.total,
                        approved_product_ar=line.approved_product_ar,
                        restrictions_ar=list(line.restrictions_ar),
                    )
                    for line in contract.breakdown
                ]
                row.contract_type = contract.contract_type.value
                row.original_value = contract.original_value
                inserted["repaired"] += 1
        session.flush()
        for request in build_demo_requests():
            if session.get(ChangeRequestRow, request.id) is None:
                session.add(ChangeRequestRow(id=request.id, **_request_values(request)))
                inserted["change_requests"] += 1
    return inserted


def seed_contract(contract: Contract) -> bool:
    """Idempotently ensure one contract exists. True if it was inserted."""
    with session_scope() as session:
        if session.get(ContractRow, contract.id) is not None:
            return False
        _insert_contract(session, contract)
        return True
