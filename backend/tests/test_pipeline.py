"""Pipeline behaviour: thresholds, chains, scope closure and legal blocking.

The contract is 4,800,000 SAR over 364 days, so the caps land on exact figures:

====================  ========  =================
cap                   percent   value
====================  ========  =================
policy cost           20%         960,000 SAR
policy time           20%          72.8 days
unit rate deviation   20%       per line
finance gate          -           200,000 SAR
Article 67 new items  10%         480,000 SAR
====================  ========  =================
"""

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.analysis.scripted import ScriptedProvider
from app.domain.change_request import ChangeRequest
from app.domain.enums import ChangeKind, CRState, ImpactType, Party, Recommendation, Role
from app.domain.models import ChangeLedger, Contract
from app.pipeline.costing import check_unit_rate
from app.pipeline.documents import check_documents
from app.pipeline.limits import check_policy, to_ledger_entries
from app.pipeline.runner import PipelineResult, run_analysis
from app.seed.demo_contract import build_government_contract, build_private_contract
from app.seed.demo_requests import build_demo_requests

NOW = datetime(2027, 2, 2, 9, 0, tzinfo=UTC)


@pytest.fixture(scope="module")
def private() -> Contract:
    return build_private_contract()


@pytest.fixture(scope="module")
def government() -> Contract:
    return build_government_contract()


def demo(cr_id: str) -> ChangeRequest:
    return next(r for r in build_demo_requests() if r.id == cr_id)


def analyse(
    contract: Contract, cr_id: str, cost_before: str = "0", days_before: int = 0
) -> PipelineResult:
    return run_analysis(
        contract,
        ChangeLedger(contract_id=contract.id),
        demo(cr_id),
        ScriptedProvider(),
        Decimal(cost_before),
        days_before,
    )


# ---------------------------------------------------------------------------
# Chain building for each demo request
# ---------------------------------------------------------------------------


def roles(result: PipelineResult) -> list[Role]:
    return [step.role for step in result.chain]


def test_in_scope_request_closes_and_builds_no_chain(private: Contract) -> None:
    """FR-05: covered by the breakdown, so it is not a change at all."""
    result = analyse(private, "CR-A-INSCOPE")
    assert result.request.kind is ChangeKind.IN_SCOPE
    assert result.request.recommendation is Recommendation.CLOSE_IN_SCOPE
    assert result.request.state is CRState.CLOSED_IN_SCOPE
    assert result.request.cost_impact == Decimal("0")
    assert result.chain == ()
    assert result.request.matched_line_ids == ("ITM-07",)


def test_pcr_within_limits_goes_to_pm_procurement_and_finance(private: Contract) -> None:
    result = analyse(private, "CR-B-PCR")
    assert result.request.kind is ChangeKind.PCR
    assert result.request.cost_impact == Decimal("135000")
    assert roles(result) == [Role.PROJECT_MANAGER, Role.PROCUREMENT_MANAGER, Role.FINANCE_MANAGER]
    assert result.request.recommendation is Recommendation.APPROVE


def test_substitution_adds_technical_approval(private: Contract) -> None:
    """FR-06: changing an approved product adds a technical step."""
    result = analyse(private, "CR-C-SUBSTITUTION")
    assert result.request.kind is ChangeKind.SUBSTITUTION
    assert result.request.changes_approved_product is True
    assert roles(result) == [
        Role.PROJECT_MANAGER,
        Role.PROCUREMENT_MANAGER,
        Role.TECHNICAL_MANAGER,
        Role.FINANCE_MANAGER,
    ]
    # 12 x (56,000 - 45,000)
    assert result.request.cost_impact == Decimal("132000")


def test_substitution_flags_the_unit_rate_deviation(private: Contract) -> None:
    """56,000 against a 45,000 contract rate is 24.44%, above the 20% cap."""
    result = analyse(private, "CR-C-SUBSTITUTION")
    assert result.request.unit_rate_flagged is True
    assert result.impact is not None
    (check,) = result.impact.rate_checks
    assert check.deviation_pct == Decimal("24.4444")
    assert check.flagged is True


def test_policy_breach_adds_the_ceo(private: Contract) -> None:
    """FR-07: above 20% needs a CEO exception; finance joins on value."""
    result = analyse(private, "CR-D-POLICY")
    assert result.request.cost_impact == Decimal("1008000")
    assert result.policy is not None
    assert result.policy.cost_after_pct == Decimal("21.0000")
    assert result.policy.cost_exceeded is True
    assert result.request.policy_exception_required is True
    assert roles(result) == [
        Role.PROJECT_MANAGER,
        Role.PROCUREMENT_MANAGER,
        Role.FINANCE_MANAGER,
        Role.CEO,
    ]
    assert result.request.recommendation is Recommendation.APPROVE


def test_ncr_reduces_the_contract(private: Contract) -> None:
    result = analyse(private, "CR-E-NCR")
    assert result.request.kind is ChangeKind.NCR
    # 15 training days x 7,500
    assert result.request.cost_impact == Decimal("-112500")
    assert roles(result) == [Role.PROJECT_MANAGER, Role.PROCUREMENT_MANAGER, Role.FINANCE_MANAGER]


def test_q1_default_flags_a_human_entered_rate(private: Contract) -> None:
    """A new item with no matching line is priced by a human and flagged."""
    result = analyse(private, "CR-D-POLICY")
    assert result.request.matched_line_ids == ()
    assert result.request.rate_human_entered is True
    assert result.decision is not None
    assert "NEW_ITEM_RATE_HUMAN_ENTERED" in result.decision.reason_codes


# ---------------------------------------------------------------------------
# Article 67 on the government variant
# ---------------------------------------------------------------------------


def test_the_same_request_is_blocked_on_a_government_contract(government: Contract) -> None:
    """A legal cap is blocking where a policy cap is only an escalation."""
    result = analyse(government, "CR-D-GOV")
    assert result.legal is not None
    assert result.legal.applies is True
    assert result.legal.blocked is True
    assert result.request.legally_blocked is True
    assert result.request.recommendation is Recommendation.REJECT
    assert result.decision is not None
    assert "LEGAL_CAP_EXCEEDED" in result.decision.reason_codes


def test_a_blocked_request_offers_no_ceo_step(government: Contract) -> None:
    """CEO approval cannot lift a legal cap, so the step is not offered."""
    result = analyse(government, "CR-D-GOV")
    assert Role.CEO not in roles(result)
    assert Role.LEGAL_ADVISOR in roles(result)
    assert result.request.policy_exception_required is True


def test_article_67_does_not_apply_to_a_private_contract(private: Contract) -> None:
    result = analyse(private, "CR-D-POLICY")
    assert result.legal is not None
    assert result.legal.applies is False
    assert result.legal.blocked is False


def test_government_new_item_requires_contractor_consent(government: Contract) -> None:
    """Article 67(1)(a) always needs consent, which puts the contractor first."""
    result = analyse(government, "CR-D-GOV")
    assert result.legal is not None
    assert result.legal.requires_contractor_consent is True
    assert result.chain[0].party is Party.CONTRACTOR


# ---------------------------------------------------------------------------
# Article 67 mapping (part 2.3)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("kind", "matched", "expected"),
    [
        (ChangeKind.PCR, (), ["NEW_ITEMS"]),
        (ChangeKind.PCR, ("ITM-04",), ["INCREASE_EXISTING"]),
        (ChangeKind.NCR, ("ITM-07",), ["DECREASE_EXISTING"]),
        (ChangeKind.SUBSTITUTION, ("ITM-05",), ["DECREASE_EXISTING", "INCREASE_EXISTING"]),
        (ChangeKind.IN_SCOPE, ("ITM-07",), []),
    ],
    ids=["pcr-new", "pcr-existing", "ncr", "substitution", "in-scope"],
)
def test_change_kind_maps_onto_article_67_categories(
    kind: ChangeKind, matched: tuple[str, ...], expected: list[str], private: Contract
) -> None:
    from app.pipeline.costing import CostImpact

    impact = CostImpact(
        cost_impact=Decimal("1000"),
        added_value=Decimal("1000"),
        removed_value=Decimal("500"),
        time_impact_days=0,
        impact_type=ImpactType.COST,
    )
    entries = to_ledger_entries(demo("CR-B-PCR"), kind, impact, matched, NOW)
    assert [entry.type.value for entry in entries] == expected


# ---------------------------------------------------------------------------
# Threshold boundaries
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("proposed", "expected_pct", "flagged"),
    [
        ("45000", "0.0000", False),
        ("54000", "20.0000", False),  # exactly 20% is not flagged
        ("54000.01", "20.0000", True),  # a fraction over is
        ("36000", "20.0000", False),  # 20% under, not flagged
        ("35999", "20.0022", True),  # just past 20% under
    ],
    ids=["equal", "exactly-20-over", "just-over-20", "exactly-20-under", "just-over-20-under"],
)
def test_unit_rate_deviation_boundary(proposed: str, expected_pct: str, flagged: bool) -> None:
    """ "More than 20%" is strictly greater: exactly 20% passes."""
    check = check_unit_rate("ITM-05", Decimal("45000"), Decimal(proposed))
    assert check.deviation_pct == Decimal(expected_pct)
    assert check.flagged is flagged


@pytest.mark.parametrize(
    ("cost", "pct", "exceeded"),
    [
        # 959,999 is 19.99997...%, which DISPLAYS as 20.0000 at four decimals
        # but is under the cap. The comparison uses values, so it passes - this
        # row exists to pin that rounding does not decide the outcome.
        ("959999", "20.0000", False),
        ("960000", "20.0000", False),  # exactly 20% needs no exception
        ("960000.01", "20.0000", True),  # one halala over does
        ("1008000", "21.0000", True),
    ],
    ids=["under", "exactly-20", "just-over-20", "twenty-one"],
)
def test_policy_cost_cap_boundary(cost: str, pct: str, exceeded: bool, private: Contract) -> None:
    from app.pipeline.costing import CostImpact

    impact = CostImpact(
        cost_impact=Decimal(cost),
        added_value=Decimal(cost),
        removed_value=Decimal("0"),
        time_impact_days=0,
        impact_type=ImpactType.COST,
    )
    check = check_policy(private, Decimal("0"), 0, impact)
    assert check.cost_after_pct == Decimal(pct)
    assert check.cost_exceeded is exceeded
    assert check.exception_required is exceeded


def test_policy_counts_cumulative_not_just_this_request(private: Contract) -> None:
    """Salami defence: small requests still add up to the cap."""
    from app.pipeline.costing import CostImpact

    impact = CostImpact(
        cost_impact=Decimal("10000"),
        added_value=Decimal("10000"),
        removed_value=Decimal("0"),
        time_impact_days=0,
        impact_type=ImpactType.COST,
    )
    assert not check_policy(private, Decimal("900000"), 0, impact).cost_exceeded
    assert check_policy(private, Decimal("955000"), 0, impact).cost_exceeded


def test_policy_time_cap_boundary(private: Contract) -> None:
    """364 days x 20% = 72.8, so 72 passes and 73 does not."""
    from app.pipeline.costing import CostImpact

    def at(days: int) -> bool:
        impact = CostImpact(
            cost_impact=Decimal("0"),
            added_value=Decimal("0"),
            removed_value=Decimal("0"),
            time_impact_days=days,
            impact_type=ImpactType.TIME,
        )
        return check_policy(private, Decimal("0"), 0, impact).time_exceeded

    assert private.original_duration_days == 364
    assert at(72) is False
    assert at(73) is True


# ---------------------------------------------------------------------------
# Stage 2 document checklist (FR-04)
# ---------------------------------------------------------------------------


def test_missing_documents_produce_a_gap_list() -> None:
    check = check_documents(ImpactType.BOTH, ("طلب تغيير رسمي",))
    assert not check.complete
    assert len(check.missing) == 2
    assert "عرض سعر أو تحليل تكلفة" in check.gap_list_ar


def test_complete_documents_pass() -> None:
    check = check_documents(ImpactType.COST, ("طلب تغيير رسمي", "عرض سعر أو تحليل تكلفة"))
    assert check.complete
    assert check.missing == ()


def test_incomplete_documents_park_the_request(private: Contract) -> None:
    """FR-04: the agent asks for paperwork. That commits nothing."""
    request = demo("CR-B-PCR").model_copy(update={"attachments": ()})
    result = run_analysis(
        private,
        ChangeLedger(contract_id=private.id),
        request,
        ScriptedProvider(),
        Decimal("0"),
        0,
    )
    assert result.request.state is CRState.AWAITING_DOCUMENTS
    assert result.request.recommendation is Recommendation.REQUEST_REVISION
    # analysis stopped at stage 2 rather than guessing past the gap
    assert len(result.stages) == 2


# ---------------------------------------------------------------------------
# Trace (FR-15, FR-18)
# ---------------------------------------------------------------------------


def test_trace_records_every_stage_with_timing(private: Contract) -> None:
    result = analyse(private, "CR-B-PCR")
    assert len(result.stages) == 7
    assert [s.stage_no for s in result.stages] == [1, 2, 3, 4, 5, 6, 7]
    for stage in result.stages:
        assert stage.duration_ms >= 0
        assert stage.finished_at >= stage.started_at
        assert stage.status in {"OK", "BLOCKED", "SKIPPED"}


def test_recorded_outputs_are_labelled(private: Contract) -> None:
    """FR-19: replayed analysis must be visibly recorded."""
    result = analyse(private, "CR-B-PCR")
    ai_stages = [s for s in result.stages if s.provider == "scripted"]
    assert ai_stages
    assert all(stage.recorded for stage in ai_stages)


# ---------------------------------------------------------------------------
# Narrative v2: Arabic and English from the same call
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("cr_id", [r.id for r in build_demo_requests()])
def test_every_recorded_narrative_has_english(
    cr_id: str, private: Contract, government: Contract
) -> None:
    request = demo(cr_id)
    contract = government if request.contract_id == government.id else private
    result = analyse(contract, cr_id)
    narrative = result.narrative
    assert narrative is not None
    assert narrative.summary_en
    assert narrative.summary_en.isascii()
    # Item for item: an English reader sees the same reasons, in order.
    assert len(narrative.reasons_en) == len(narrative.reasons_ar)
    assert len(narrative.next_actions_en) == len(narrative.next_actions_ar)
    stage = next(s for s in result.stages if s.stage.value == "ORCHESTRATOR")
    assert stage.payload["narrative"]["summary_en"] == narrative.summary_en


def test_recorded_vo_scope_has_english_for_every_demo_request() -> None:
    from app.analysis.recorded.demo_outputs import vo_scope_for
    from app.analysis.schemas import VODraftInput

    provider = ScriptedProvider()
    for request in build_demo_requests():
        draft = provider.vo_draft(
            VODraftInput(
                cr_id=request.id, contract_title_ar="", requested_change_ar=request.body_ar
            )
        )
        assert draft.scope_ar
        assert draft.scope_en.startswith("This variation order covers: ")
        assert "original Arabic request" not in draft.scope_en
        assert draft == vo_scope_for(request.body_ar)
