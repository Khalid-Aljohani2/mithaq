"""NFR-15: the decision boundary.

> No code path lets an AI step change a CR's approval status, issue a VO, or
> change contract values.

These tests attack that from three directions: what an AI output is *shaped*
to carry, what a provider is *handed*, and what happens when a provider lies.
"""

import inspect
from decimal import Decimal

import pytest

from app.analysis import schemas as ai_schemas
from app.analysis.provider import AnalysisProvider
from app.analysis.scripted import ScriptedProvider
from app.domain.change_request import ChangeRequest
from app.domain.enums import ActorType, CRState, Stage
from app.domain.models import ChangeLedger
from app.pipeline.runner import run_analysis
from app.seed.demo_contract import build_private_contract
from app.seed.demo_requests import build_demo_requests

#: Field names an AI output must never carry.
FORBIDDEN_FIELDS = {
    "cost",
    "cost_impact",
    "value",
    "amount",
    "unit_rate",
    "total",
    "state",
    "status",
    "approved",
    "approval_status",
    "decision",
    "recommendation",
    "cumulative_pct",
    "vo_id",
    "variation_order",
}

AI_OUTPUT_TYPES = [
    ai_schemas.IntakeOutput,
    ai_schemas.ScopeOutput,
    ai_schemas.TechnicalOutput,
    ai_schemas.RiskOutput,
    ai_schemas.NarrativeOutput,
    ai_schemas.VODraftOutput,
]


@pytest.mark.parametrize("output_type", AI_OUTPUT_TYPES, ids=lambda t: t.__name__)
def test_ai_outputs_cannot_carry_money_or_state(output_type: type) -> None:
    """A provider cannot return a figure or a status: there is nowhere to put it.

    ``quantity_delta`` is the one quantity an AI output carries, and it is a
    count in the line's own unit, never a price. Code multiplies it by the
    contract rate.
    """
    fields = set(output_type.model_fields)
    assert not (fields & FORBIDDEN_FIELDS), (
        f"{output_type.__name__} exposes {sorted(fields & FORBIDDEN_FIELDS)}"
    )


def test_the_one_numeric_field_is_a_quantity_not_a_price() -> None:
    assert "quantity_delta" in ai_schemas.ScopeOutput.model_fields
    assert "unit_rate" not in ai_schemas.ScopeOutput.model_fields


def test_breakdown_view_given_to_a_model_has_no_rates() -> None:
    """A model is never shown what anything costs, so it cannot anchor on it."""
    fields = set(ai_schemas.BreakdownLineView.model_fields)
    assert "unit_rate" not in fields
    assert "total" not in fields
    assert "quantity" not in fields


@pytest.mark.parametrize(
    "method", sorted(AnalysisProvider.__abstractmethods__), ids=lambda m: str(m)
)
def test_provider_methods_take_no_writable_dependency(method: str) -> None:
    """A provider receives a schema and nothing else.

    No repository, no session, no clock: a provider is structurally incapable
    of writing anything, whatever its implementation tries to do.
    """
    signature = inspect.signature(getattr(AnalysisProvider, method))
    parameters = [name for name in signature.parameters if name != "self"]
    assert parameters == ["request"]
    annotation = signature.parameters["request"].annotation
    assert annotation.__module__ == "app.analysis.schemas"


def test_every_ai_output_declares_whether_it_was_recorded() -> None:
    """FR-19: the UI has to be able to label replayed output."""
    for output_type in AI_OUTPUT_TYPES:
        assert "recorded" in output_type.model_fields
        assert "provider" in output_type.model_fields


class LyingProvider(ScriptedProvider):
    """A provider that tries to force an outcome through its only channel.

    It claims total confidence and insists everything is a trivially approvable
    in-scope request. None of that may change a figure or a state.
    """

    name = "lying"

    def scope_analysis(self, request: ai_schemas.ScopeInput) -> ai_schemas.ScopeOutput:
        real = super().scope_analysis(request)
        return real.model_copy(update={"confidence": Decimal("1"), "in_scope": True})


def test_a_lying_provider_cannot_change_the_computed_cost() -> None:
    """Stage 5 prices from contract rates, not from what a model asserts."""
    contract = build_private_contract()
    request = next(r for r in build_demo_requests() if r.id == "CR-B-PCR")
    ledger = ChangeLedger(contract_id=contract.id)

    honest = run_analysis(contract, ledger, request, ScriptedProvider(), Decimal("0"), 0)
    liar = run_analysis(contract, ledger, request, LyingProvider(), Decimal("0"), 0)

    # The model claimed it was in scope and free; the cost is computed anyway.
    assert honest.impact is not None
    assert liar.impact is not None
    assert liar.impact.cost_impact == honest.impact.cost_impact == Decimal("135000")


def test_an_ai_stage_never_reaches_the_approved_state() -> None:
    """Analysis can reach RECOMMENDED at most. Approval needs the chain."""
    contract = build_private_contract()
    ledger = ChangeLedger(contract_id=contract.id)
    for request in build_demo_requests():
        if request.contract_id != contract.id:
            continue
        result = run_analysis(contract, ledger, request, ScriptedProvider(), Decimal("0"), 0)
        assert result.request.state in {
            CRState.RECOMMENDED,
            CRState.CLOSED_IN_SCOPE,
            CRState.AWAITING_DOCUMENTS,
        }
        assert result.request.state is not CRState.APPROVED
        assert result.request.state is not CRState.VO_ISSUED


def test_the_pipeline_issues_no_variation_order() -> None:
    """Stage 9 lives in the service layer behind a full-chain check."""
    contract = build_private_contract()
    request = next(r for r in build_demo_requests() if r.id == "CR-D-POLICY")
    result = run_analysis(
        contract,
        ChangeLedger(contract_id=contract.id),
        request,
        ScriptedProvider(),
        Decimal("0"),
        0,
    )
    assert not hasattr(result, "variation_order")
    assert all(stage.stage is not Stage.ISSUE_VO for stage in result.stages)


def test_ai_stages_are_recorded_as_ai_and_money_stages_as_code() -> None:
    """The trace has to show which component produced each result (FR-15)."""
    contract = build_private_contract()
    request = next(r for r in build_demo_requests() if r.id == "CR-C-SUBSTITUTION")
    result = run_analysis(
        contract,
        ChangeLedger(contract_id=contract.id),
        request,
        ScriptedProvider(),
        Decimal("0"),
        0,
    )
    actors = {stage.stage: stage.actor_type for stage in result.stages}
    assert actors[Stage.INTAKE] is ActorType.AI
    assert actors[Stage.SCOPE_ANALYSIS] is ActorType.AI
    assert actors[Stage.TECHNICAL_ASSESSMENT] is ActorType.AI
    # The stages that touch money and decisions are code.
    assert actors[Stage.DOCUMENT_VALIDATION] is ActorType.CODE
    assert actors[Stage.COST_SCHEDULE_IMPACT] is ActorType.CODE
    assert actors[Stage.ORCHESTRATOR] is ActorType.CODE


def test_contract_values_are_immutable() -> None:
    """Nothing can mutate a contract in place, AI or otherwise."""
    contract = build_private_contract()
    with pytest.raises(Exception):  # noqa: B017 - pydantic raises ValidationError
        contract.original_value = Decimal("1")  # type: ignore[misc]


def test_change_requests_are_immutable() -> None:
    request = build_demo_requests()[0]
    assert isinstance(request, ChangeRequest)
    with pytest.raises(Exception):  # noqa: B017
        request.state = CRState.APPROVED  # type: ignore[misc]
