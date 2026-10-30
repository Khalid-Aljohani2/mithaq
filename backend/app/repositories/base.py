"""Storage interface.

The pipeline and the routers depend on this abstraction, never on a concrete
store, so the in-memory and Postgres implementations stay interchangeable
(NFR-07, NFR-11).

Two deliberate omissions:

* there is no update or delete for the audit log - only ``append_audit`` and
  ``list_audit`` (FR-13);
* there is no update or delete for stage results - a trace is a record of what
  happened, not a mutable field (FR-15).
"""

from abc import ABC, abstractmethod

from app.domain.audit import AuditEvent
from app.domain.change_request import (
    ApprovalStep,
    ChangeRequest,
    ExecutionRecord,
    Notification,
    StageResult,
    VariationOrder,
)
from app.domain.enums import Party, Role
from app.domain.models import ChangeLedger, ChangeOrder, Contract


class ContractRepository(ABC):
    """Reads and writes everything the workflow needs."""

    # ---- contracts ----

    @abstractmethod
    def list_contracts(self) -> list[Contract]:
        """Return every contract."""

    @abstractmethod
    def get_contract(self, contract_id: str) -> Contract | None:
        """Return one contract, or None if it does not exist."""

    # ---- Article 67 ledger ----

    @abstractmethod
    def get_ledger(self, contract_id: str) -> ChangeLedger:
        """Return the Article 67 ledger for a contract."""

    @abstractmethod
    def add_change_order(self, order: ChangeOrder) -> ChangeOrder:
        """Append a ledger entry. The ledger is append-only."""

    @abstractmethod
    def get_change_order(self, order_id: str) -> ChangeOrder | None:
        """Return one ledger entry, or None."""

    @abstractmethod
    def replace_change_order(self, order: ChangeOrder) -> ChangeOrder:
        """Store a new revision of a ledger entry, keyed by its id."""

    # ---- change requests ----

    @abstractmethod
    def add_change_request(self, request: ChangeRequest) -> ChangeRequest:
        """Record a newly received change request."""

    @abstractmethod
    def get_change_request(self, cr_id: str) -> ChangeRequest | None:
        """Return one change request, or None."""

    @abstractmethod
    def list_change_requests(self, contract_id: str) -> list[ChangeRequest]:
        """Every change request against a contract, oldest first."""

    @abstractmethod
    def replace_change_request(self, request: ChangeRequest) -> ChangeRequest:
        """Store a new revision of a change request."""

    @abstractmethod
    def next_change_request_id(self, contract_id: str) -> str:
        """Allocate the next change-request id for a contract (FR-03)."""

    # ---- approval chain ----

    @abstractmethod
    def set_approval_chain(self, cr_id: str, steps: tuple[ApprovalStep, ...]) -> None:
        """Replace a change request's chain wholesale.

        Rebuilt rather than patched: a revised request is re-analysed from
        scratch and may need a different chain entirely.
        """

    @abstractmethod
    def list_approval_steps(self, cr_id: str) -> list[ApprovalStep]:
        """The chain in position order."""

    @abstractmethod
    def replace_approval_step(self, step: ApprovalStep) -> ApprovalStep:
        """Record one approver's decision."""

    @abstractmethod
    def list_pending_steps(self) -> list[ApprovalStep]:
        """Every pending step across all contracts, for reminders (FR-11)."""

    # ---- trace ----

    @abstractmethod
    def append_stage_results(self, results: list[StageResult]) -> None:
        """Append trace entries. Append-only, like the audit log (FR-15)."""

    @abstractmethod
    def list_stage_results(self, cr_id: str) -> list[StageResult]:
        """The trace for one change request, in order."""

    # ---- notifications ----

    @abstractmethod
    def append_notification(self, notification: Notification) -> Notification:
        """Record an in-app notification (FR-11)."""

    @abstractmethod
    def list_notifications(self, party: Party, role: Role) -> list[Notification]:
        """Notifications for one role, newest first."""

    # ---- variation orders and execution ----

    @abstractmethod
    def add_variation_order(self, vo: VariationOrder) -> VariationOrder:
        """Record an issued variation order (FR-12)."""

    @abstractmethod
    def get_variation_order(self, vo_id: str) -> VariationOrder | None:
        """Return one variation order, or None."""

    @abstractmethod
    def get_variation_order_for_request(self, cr_id: str) -> VariationOrder | None:
        """Return the variation order issued for a change request, or None.

        Asked of the store rather than derived from the id convention, so the
        convention can change without every caller learning about it.
        """

    @abstractmethod
    def list_variation_orders(self, contract_id: str) -> list[VariationOrder]:
        """Every variation order issued against a contract."""

    @abstractmethod
    def upsert_execution_record(self, record: ExecutionRecord) -> ExecutionRecord:
        """Create or update the execution record for a variation order (FR-14)."""

    @abstractmethod
    def get_execution_record(self, vo_id: str) -> ExecutionRecord | None:
        """Return the execution record for a variation order, or None."""

    # ---- audit (append-only) ----

    @abstractmethod
    def append_audit(self, event: AuditEvent) -> AuditEvent:
        """Append one audit entry (FR-13).

        The ONLY write path to the audit log. There is deliberately no update
        or delete counterpart anywhere in this interface.
        """

    @abstractmethod
    def list_audit(self, contract_id: str) -> list[AuditEvent]:
        """The audit trail for a contract, oldest first."""

    # ---- demo ----

    @abstractmethod
    def reset(self) -> None:
        """Restore the seed state (FR-19).

        Audit rows survive a reset; the caller appends a DEMO_RESET event.
        """
