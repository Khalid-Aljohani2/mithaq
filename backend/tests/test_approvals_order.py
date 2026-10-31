"""The government approvals order (FR-02, FR-09).

Every request with a cost impact goes Project manager, Procurement manager,
Finance manager, then the Legal advisor when a legal flag applies, then the CEO
when a policy exception applies. A request without a cost impact skips Finance.
The order lives in approval_matrix.yaml; the last test proves the code follows
the configuration rather than a list of its own.
"""

from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from typing import cast

from app.domain.change_request import ChangeRequest
from app.domain.enums import Party, Role
from app.pipeline.approvals import ApprovalMatrix, ChainFacts, build_chain, get_matrix

NOW = datetime(2027, 2, 1, 8, 0, tzinfo=UTC)
REQUEST = cast(ChangeRequest, SimpleNamespace(id="CR-ORDER"))


def facts(
    cost: str,
    *,
    legal: bool = False,
    exception: bool = False,
    legally_blocked: bool = False,
    product: bool = False,
) -> ChainFacts:
    return ChainFacts(
        contractor_consent_required=False,
        changes_approved_product=product,
        needs_legal_review=legal,
        legally_blocked=legally_blocked,
        policy_exception_required=exception,
        cost_impact_abs=abs(Decimal(cost)),
    )


def chain(f: ChainFacts, matrix: ApprovalMatrix | None = None) -> list[tuple[int, Party, Role]]:
    return [(s.position, s.party, s.role) for s in build_chain(REQUEST, f, NOW, matrix)]


GOV = Party.GOVERNMENT_ENTITY


def test_cost_impact_chain_is_exactly_pm_procurement_finance() -> None:
    assert chain(facts("135000")) == [
        (1, GOV, Role.PROJECT_MANAGER),
        (2, GOV, Role.PROCUREMENT_MANAGER),
        (3, GOV, Role.FINANCE_MANAGER),
    ]


def test_cost_impact_with_legal_flag_adds_the_legal_advisor_last() -> None:
    assert chain(facts("135000", legal=True)) == [
        (1, GOV, Role.PROJECT_MANAGER),
        (2, GOV, Role.PROCUREMENT_MANAGER),
        (3, GOV, Role.FINANCE_MANAGER),
        (4, GOV, Role.LEGAL_ADVISOR),
    ]


def test_policy_exception_puts_the_ceo_after_legal() -> None:
    roles = [r for _, _, r in chain(facts("1008000", legal=True, exception=True))]
    assert roles == [
        Role.PROJECT_MANAGER,
        Role.PROCUREMENT_MANAGER,
        Role.FINANCE_MANAGER,
        Role.LEGAL_ADVISOR,
        Role.CEO,
    ]


def test_a_legal_breach_still_omits_the_ceo() -> None:
    """The CEO cannot lift a legal cap, so the exception step is not offered."""
    blocked = facts("1008000", legal=True, exception=True, legally_blocked=True)
    roles = [r for _, _, r in chain(blocked)]
    assert Role.CEO not in roles


def test_a_decrease_is_a_cost_impact_and_goes_to_finance() -> None:
    roles = [r for _, _, r in chain(facts("-112500"))]
    assert roles == [Role.PROJECT_MANAGER, Role.PROCUREMENT_MANAGER, Role.FINANCE_MANAGER]


def test_no_cost_impact_skips_finance() -> None:
    roles = [r for _, _, r in chain(facts("0"))]
    assert roles == [Role.PROJECT_MANAGER, Role.PROCUREMENT_MANAGER]


def test_a_product_change_keeps_the_technical_manager_before_finance() -> None:
    roles = [r for _, _, r in chain(facts("132000", product=True))]
    assert roles == [
        Role.PROJECT_MANAGER,
        Role.PROCUREMENT_MANAGER,
        Role.TECHNICAL_MANAGER,
        Role.FINANCE_MANAGER,
    ]


def test_the_order_comes_from_configuration() -> None:
    """Swap two positions in the matrix and the chain follows."""
    loaded = get_matrix()
    gov = loaded.parties[GOV]
    moved = {Role.PROCUREMENT_MANAGER: 45}
    swapped_rules = tuple(
        rule.model_copy(update={"position": moved.get(rule.role, rule.position)})
        for rule in gov.rules
    )
    swapped = loaded.model_copy(
        update={"parties": {**loaded.parties, GOV: gov.model_copy(update={"rules": swapped_rules})}}
    )
    roles = [r for _, _, r in chain(facts("135000"), swapped)]
    assert roles == [Role.PROJECT_MANAGER, Role.FINANCE_MANAGER, Role.PROCUREMENT_MANAGER]
