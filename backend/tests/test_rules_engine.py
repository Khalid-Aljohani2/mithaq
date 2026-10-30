"""Boundary tests for the deterministic rules engine (NFR-01).

The contract is worth 4,800,000 SAR, so the caps land on exact amounts:

====================  ========  ===========
cap                   percent   SAR
====================  ========  ===========
NEW_ITEMS             10%         480,000
INCREASE_EXISTING     20%         960,000
DECREASE_EXISTING     20%         960,000
COMBINED              20%         960,000
warn (80% of 10%)      8%         384,000
warn (80% of 20%)     16%         768,000
====================  ========  ===========

Every case is tested below the cap, exactly on it, and one single riyal over.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.domain.enums import ChangeCategory, OrderStatus
from app.domain.models import ChangeLedger, ChangeOrder, Contract
from app.regulations.loader import CategoryLimit, Limits, get_limits
from app.seed.demo_contract import build_demo_contract
from app.services.rules_engine import _consent_for_category, evaluate, summarise

NEW = ChangeCategory.NEW_ITEMS
INC = ChangeCategory.INCREASE_EXISTING
DEC = ChangeCategory.DECREASE_EXISTING
NON = ChangeCategory.NON_FINANCIAL

_FIXED_TIME = datetime(2027, 2, 1, 9, 0, tzinfo=UTC)


@pytest.fixture(scope="module")
def contract() -> Contract:
    return build_demo_contract()


@pytest.fixture(scope="module")
def limits() -> Limits:
    return get_limits()


def make_order(
    category: ChangeCategory,
    value: str,
    *,
    order_id: str = "CO-TEST",
    status: OrderStatus = OrderStatus.DRAFT,
) -> ChangeOrder:
    """Build a change order with as little ceremony as possible."""
    return ChangeOrder(
        id=order_id,
        contract_id="CT-2027-0418",
        type=category,
        value=Decimal(value),
        related_item_ids=("ITM-01",) if category in {INC, DEC} else (),
        description_ar="بند اختبار",
        status=status,
        created_at=_FIXED_TIME,
    )


def ledger_of(*orders: ChangeOrder) -> ChangeLedger:
    return ChangeLedger(contract_id="CT-2027-0418", orders=orders)


def approved(category: ChangeCategory, value: str, order_id: str) -> ChangeOrder:
    return make_order(category, value, order_id=order_id, status=OrderStatus.APPROVED)


@dataclass(frozen=True)
class Case:
    """One row of the boundary table."""

    name: str
    proposed_type: ChangeCategory
    proposed_value: str
    allowed: bool
    consent: bool
    warned: bool
    prior: list[ChangeOrder] = field(default_factory=list)
    violation_scopes: tuple[str, ...] = ()


CASES: tuple[Case, ...] = (
    # ---------- NEW_ITEMS, cap 10% = 480,000 ----------
    Case("new under cap", NEW, "300000", allowed=True, consent=True, warned=False),
    Case("new just under warn threshold", NEW, "383999", allowed=True, consent=True, warned=False),
    Case("new exactly at warn threshold", NEW, "384000", allowed=True, consent=True, warned=True),
    Case("new exactly at cap", NEW, "480000", allowed=True, consent=True, warned=True),
    Case(
        "new one riyal over cap",
        NEW,
        "480001",
        allowed=False,
        consent=True,
        warned=False,
        violation_scopes=("NEW_ITEMS",),
    ),
    # ---------- INCREASE_EXISTING, cap 20% = 960,000, consent above 10% ----------
    Case(
        "increase under consent threshold", INC, "400000", allowed=True, consent=False, warned=False
    ),
    Case(
        "increase exactly at consent threshold",
        INC,
        "480000",
        allowed=True,
        consent=False,
        warned=False,
    ),
    Case(
        "increase one riyal above consent threshold",
        INC,
        "480001",
        allowed=True,
        consent=True,
        warned=False,
    ),
    Case(
        "increase exactly at warn threshold", INC, "768000", allowed=True, consent=True, warned=True
    ),
    Case("increase exactly at cap", INC, "960000", allowed=True, consent=True, warned=True),
    Case(
        "increase one riyal over cap",
        INC,
        "960001",
        allowed=False,
        consent=True,
        warned=False,
        # 960,001 breaches the 20% increase cap AND the 20% combined cap at once.
        violation_scopes=("INCREASE_EXISTING", "COMBINED"),
    ),
    # ---------- DECREASE_EXISTING, 20% is a consent trigger, never a block ----------
    Case("decrease under cap", DEC, "900000", allowed=True, consent=False, warned=True),
    Case("decrease exactly at cap", DEC, "960000", allowed=True, consent=False, warned=True),
    Case(
        "decrease one riyal over cap needs consent but is allowed",
        DEC,
        "960001",
        allowed=True,
        consent=True,
        warned=False,
    ),
    Case(
        "decrease far beyond cap is still allowed with consent",
        DEC,
        "2000000",
        allowed=True,
        consent=True,
        warned=False,
    ),
    # ---------- NON_FINANCIAL, no cap ----------
    Case("non financial change", NON, "0", allowed=True, consent=True, warned=False),
    # ---------- COMBINED, cap 20% = 960,000 ----------
    Case(
        # The increase lands exactly on the 10% consent threshold, so nothing sits
        # above it and no consent is due - only the combined cap warning fires.
        "combined exactly at cap",
        INC,
        "480000",
        allowed=True,
        consent=False,
        warned=True,
        prior=[approved(NEW, "480000", "CO-P1")],
    ),
    Case(
        "combined one riyal over cap blocks even though each cap is fine",
        INC,
        "480001",
        allowed=False,
        consent=True,
        warned=False,
        prior=[approved(NEW, "480000", "CO-P1")],
        violation_scopes=("COMBINED",),
    ),
)


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.name)
def test_boundaries(case: Case, contract: Contract, limits: Limits) -> None:
    result = evaluate(
        contract,
        ledger_of(*case.prior),
        make_order(case.proposed_type, case.proposed_value),
        limits,
    )
    assert result.allowed is case.allowed
    assert result.requires_contractor_consent is case.consent
    assert bool(result.warnings) is case.warned
    assert tuple(v.scope for v in result.blocking_violations) == case.violation_scopes
    assert all(v.article_ref_en for v in result.blocking_violations)


def test_salami_ten_small_new_item_orders(contract: Contract, limits: Limits) -> None:
    """Ten 1.5% new-item orders approved one by one.

    Six fit under the 10% cap at 9.0%. The seventh would reach 10.5% and must be
    blocked - splitting one large change into small ones must not get past the cap.
    """
    slice_value = contract.original_value * Decimal("1.5") / Decimal("100")
    assert slice_value == Decimal("72000.0")

    approved_orders: list[ChangeOrder] = []
    outcomes: list[bool] = []

    for n in range(1, 11):
        proposed = make_order(NEW, str(slice_value), order_id=f"CO-{n:02d}")
        result = evaluate(contract, ledger_of(*approved_orders), proposed, limits)
        outcomes.append(result.allowed)
        if result.allowed:
            approved_orders.append(proposed.model_copy(update={"status": OrderStatus.APPROVED}))
        else:
            break

    assert outcomes == [True] * 6 + [False]
    assert len(approved_orders) == 6
    seventh = evaluate(
        contract, ledger_of(*approved_orders), make_order(NEW, str(slice_value)), limits
    )
    assert seventh.usage["NEW_ITEMS"].before_pct == Decimal("9.0000")
    assert seventh.usage["NEW_ITEMS"].after_pct == Decimal("10.5000")
    assert not seventh.allowed
    assert seventh.blocking_violations[0].excess_value == Decimal("24000.0")

    # the remaining 1% of headroom is still usable, so the cap blocks the
    # oversized order rather than freezing the contract
    assert evaluate(contract, ledger_of(*approved_orders), make_order(NEW, "48000"), limits).allowed


def test_pending_orders_do_not_consume_headroom(contract: Contract, limits: Limits) -> None:
    """Only APPROVED orders count; pending value is reported separately."""
    pending = make_order(
        NEW, "480000", order_id="CO-PENDING", status=OrderStatus.PENDING_AUTHORITY_APPROVAL
    )
    result = evaluate(contract, ledger_of(pending), make_order(NEW, "480000"), limits)

    usage = result.usage["NEW_ITEMS"]
    assert result.allowed is True
    assert usage.before_value == Decimal("0")
    assert usage.pending_value == Decimal("480000")
    assert usage.after_value == Decimal("480000")


def test_draft_orders_are_neither_committed_nor_pending(contract: Contract, limits: Limits) -> None:
    draft = make_order(NEW, "480000", order_id="CO-DRAFT", status=OrderStatus.DRAFT)
    usage = evaluate(contract, ledger_of(draft), make_order(NEW, "1"), limits).usage["NEW_ITEMS"]
    assert usage.before_value == Decimal("0")
    assert usage.pending_value == Decimal("0")


def test_rejected_orders_are_ignored(contract: Contract, limits: Limits) -> None:
    rejected = make_order(NEW, "480000", order_id="CO-REJ", status=OrderStatus.REJECTED)
    result = evaluate(contract, ledger_of(rejected), make_order(NEW, "480000"), limits)
    assert result.allowed is True


def test_order_is_not_counted_against_itself(contract: Contract, limits: Limits) -> None:
    """Re-evaluating a stored order must exclude it from its own baseline."""
    stored = make_order(
        NEW, "480000", order_id="CO-SELF", status=OrderStatus.PENDING_AUTHORITY_APPROVAL
    )
    result = evaluate(contract, ledger_of(stored), stored, limits)
    assert result.allowed is True
    assert result.usage["NEW_ITEMS"].after_value == Decimal("480000")


@pytest.mark.parametrize(
    ("category", "value", "expected"),
    [(NEW, "1000", True), (INC, "1000", True), (DEC, "1000", False), (NON, "0", False)],
)
def test_time_extension_flag(
    category: ChangeCategory, value: str, expected: bool, contract: Contract, limits: Limits
) -> None:
    """Article 72(1) eligibility is flagged only for orders that add work."""
    result = evaluate(contract, ledger_of(), make_order(category, value), limits)
    assert result.eligible_for_time_extension is expected


def test_blocked_order_is_not_time_extension_eligible(contract: Contract, limits: Limits) -> None:
    result = evaluate(contract, ledger_of(), make_order(NEW, "480001"), limits)
    assert result.allowed is False
    assert result.eligible_for_time_extension is False
    assert result.exempt_from_final_guarantee is False


@pytest.mark.parametrize(
    ("category", "value", "expected"),
    [(NEW, "1000", True), (INC, "1000", True), (DEC, "1000", False), (NON, "0", False)],
)
def test_final_guarantee_exemption_flag(
    category: ChangeCategory, value: str, expected: bool, contract: Contract, limits: Limits
) -> None:
    """Article 59(2)(z): assigning additional works exempts the final guarantee.

    Flag only - the engine never computes or releases a guarantee amount.
    """
    result = evaluate(contract, ledger_of(), make_order(category, value), limits)
    assert result.exempt_from_final_guarantee is expected
    if expected:
        assert "Article 59(2)(z)" in result.article_refs
    else:
        assert "Article 59(2)(z)" not in result.article_refs


def test_both_additional_work_flags_move_together(contract: Contract, limits: Limits) -> None:
    """The two flags share one trigger, so they never disagree."""
    for category, value in [(NEW, "1000"), (INC, "1000"), (DEC, "1000"), (NON, "0")]:
        result = evaluate(contract, ledger_of(), make_order(category, value), limits)
        assert result.exempt_from_final_guarantee is result.eligible_for_time_extension


def test_final_guarantee_rule_quotes_the_article_verbatim(limits: Limits) -> None:
    """NFR-02: the flag is backed by the exact phrase from Article 59(2)."""
    rule = limits.final_guarantee_exemption
    assert rule.flag_only is True
    assert rule.article_ref_en == "Article 59(2)(z)"
    assert "إذا كُلف المتعاقد معه بأعمال إضافية" in rule.note


def test_increase_rule_is_flagged_for_legal_review(contract: Contract, limits: Limits) -> None:
    """Article 67(1)(b) is ambiguous, so results relying on it say so (NFR-02)."""
    assert evaluate(contract, ledger_of(), make_order(INC, "1000"), limits).needs_legal_review
    assert not evaluate(contract, ledger_of(), make_order(NEW, "1000"), limits).needs_legal_review


def test_every_finding_carries_an_article_reference(contract: Contract, limits: Limits) -> None:
    """NFR-02: nothing is asserted without saying which article says so."""
    result = evaluate(
        contract, ledger_of(approved(NEW, "480000", "CO-P1")), make_order(INC, "480001"), limits
    )
    assert result.article_refs
    for violation in result.blocking_violations:
        assert violation.article_ref_en and violation.article_ref_ar
    for consent in result.consent_requirements:
        assert consent.article_ref_en and consent.article_ref_ar


def test_consent_portion_is_only_the_part_above_the_threshold(
    contract: Contract, limits: Limits
) -> None:
    """Article 67(1)(b): consent covers the slice above 10%, not the whole increase."""
    result = evaluate(contract, ledger_of(), make_order(INC, "600000"), limits)
    (requirement,) = result.consent_requirements
    # 600,000 total increase, 480,000 of it sits under the 10% threshold.
    assert requirement.portion_requiring_consent == Decimal("120000")


def test_headroom_is_reported_in_sar(contract: Contract, limits: Limits) -> None:
    usage = evaluate(contract, ledger_of(), make_order(NEW, "80000"), limits).usage["NEW_ITEMS"]
    assert usage.cap_value == Decimal("480000")
    assert usage.headroom_value == Decimal("400000")


def test_non_financial_has_no_cap(contract: Contract, limits: Limits) -> None:
    usage = evaluate(contract, ledger_of(), make_order(NON, "0"), limits).usage["NON_FINANCIAL"]
    assert usage.cap_pct is None
    assert usage.cap_value is None
    assert usage.headroom_value is None


def test_consent_rule_never_returns_nothing(limits: Limits) -> None:
    """The 'never' consent rule is supported by the schema but unused by the law."""
    rule = limits.categories[NEW].model_copy(update={"consent_rule": "never"})
    assert isinstance(rule, CategoryLimit)
    snapshot = evaluate(build_demo_contract(), ledger_of(), make_order(NEW, "1000"), limits).usage[
        "NEW_ITEMS"
    ]
    assert _consent_for_category(NEW, rule, snapshot, Decimal("4800000")) is None


def test_summarise_reports_every_scope(contract: Contract, limits: Limits) -> None:
    usage = summarise(contract, ledger_of(approved(NEW, "240000", "CO-A")), limits)
    assert set(usage) == {
        "NEW_ITEMS",
        "INCREASE_EXISTING",
        "DECREASE_EXISTING",
        "NON_FINANCIAL",
        "COMBINED",
    }
    assert usage["NEW_ITEMS"].before_value == Decimal("240000")
    assert usage["COMBINED"].before_value == Decimal("240000")
    assert usage["COMBINED"].headroom_value == Decimal("720000")
