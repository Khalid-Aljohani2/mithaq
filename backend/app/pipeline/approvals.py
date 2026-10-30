"""Approval matrix and chain building (FR-02, FR-09, FR-10).

Deterministic code. The matrix declares which role approves what and in which
order; this module evaluates the conditions against a change request's facts
and produces the chain.

The conditions are a closed set. A matrix naming a condition that is not
implemented here fails at load time rather than silently never firing.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict

from app.domain.change_request import ApprovalStep, ChangeRequest
from app.domain.enums import ApprovalDecision, Party, Role
from app.policy.loader import get_policy

MATRIX_PATH = Path(__file__).parent.parent / "policy" / "approval_matrix.yaml"


@dataclass(frozen=True)
class ChainFacts:
    """Everything a matrix condition is allowed to look at.

    Deliberately a flat set of booleans and one figure: a condition cannot
    reach into a repository, a model output, or the request text.
    """

    contractor_consent_required: bool
    changes_approved_product: bool
    needs_legal_review: bool
    legally_blocked: bool
    policy_exception_required: bool
    cost_impact_abs: Decimal

    @classmethod
    def from_request(
        cls, request: ChangeRequest, *, contractor_consent_required: bool
    ) -> "ChainFacts":
        return cls(
            contractor_consent_required=contractor_consent_required,
            changes_approved_product=request.changes_approved_product,
            needs_legal_review=request.needs_legal_review,
            legally_blocked=request.legally_blocked,
            policy_exception_required=request.policy_exception_required,
            cost_impact_abs=abs(request.cost_impact or Decimal("0")),
        )


#: The closed set of conditions a matrix may name.
CONDITIONS: dict[str, Callable[[ChainFacts], bool]] = {
    "always": lambda _: True,
    "contractor_consent_required": lambda f: f.contractor_consent_required,
    "changes_approved_product": lambda f: f.changes_approved_product,
    "needs_legal_review": lambda f: f.needs_legal_review,
    "cost_impact_above_finance_threshold": (
        lambda f: f.cost_impact_abs > get_policy().finance_approval_value
    ),
    # A policy cap can be escalated past; a legal cap cannot. When a legal cap
    # is breached the exception step is omitted entirely, because offering it
    # would imply the CEO could lift a limit they have no power over.
    "policy_exception_effective": lambda f: f.policy_exception_required and not f.legally_blocked,
}


class MatrixRule(BaseModel):
    """One row of a party's approval matrix."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    role: Role
    position: int
    when: str
    reason_code: str
    description_en: str = ""


class PartyMatrix(BaseModel):
    model_config = ConfigDict(frozen=True, extra="ignore")

    default_role: Role
    rules: tuple[MatrixRule, ...]


class ApprovalMatrix(BaseModel):
    """The seeded, editable approval matrix for both parties."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    parties: dict[Party, PartyMatrix]

    def validate_conditions(self) -> None:
        """Fail loudly on a condition nothing implements."""
        unknown = {
            rule.when
            for matrix in self.parties.values()
            for rule in matrix.rules
            if rule.when not in CONDITIONS
        }
        if unknown:
            msg = f"approval matrix names conditions with no implementation: {sorted(unknown)}"
            raise ValueError(msg)


def load_matrix(path: Path = MATRIX_PATH) -> ApprovalMatrix:
    """Parse, validate and return the approval matrix."""
    matrix = ApprovalMatrix.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
    matrix.validate_conditions()
    return matrix


@lru_cache(maxsize=1)
def get_matrix() -> ApprovalMatrix:
    """Return the cached approval matrix."""
    return load_matrix()


def build_chain(
    request: ChangeRequest,
    facts: ChainFacts,
    now: datetime,
    matrix: ApprovalMatrix | None = None,
) -> tuple[ApprovalStep, ...]:
    """Build this change request's approval chain (FR-09).

    Returns steps in ascending matrix position, renumbered 1..n so approvers
    act in an unambiguous order.
    """
    matrix = matrix or get_matrix()

    selected: list[tuple[int, Party, MatrixRule]] = [
        (rule.position, party, rule)
        for party, party_matrix in matrix.parties.items()
        for rule in party_matrix.rules
        if CONDITIONS[rule.when](facts)
    ]
    selected.sort(key=lambda entry: (entry[0], entry[1].value, entry[2].role.value))

    return tuple(
        ApprovalStep(
            cr_id=request.id,
            position=index,
            party=party,
            role=rule.role,
            reason_code=rule.reason_code,
            decision=ApprovalDecision.PENDING,
            created_at=now,
        )
        for index, (_, party, rule) in enumerate(selected, start=1)
    )


def current_step(steps: tuple[ApprovalStep, ...]) -> ApprovalStep | None:
    """The step whose turn it is: the first still pending, in order."""
    return next((step for step in sorted(steps, key=lambda s: s.position) if step.is_pending), None)


def chain_is_complete(steps: tuple[ApprovalStep, ...]) -> bool:
    """True when every step has been approved."""
    return bool(steps) and all(step.decision is ApprovalDecision.APPROVED for step in steps)
