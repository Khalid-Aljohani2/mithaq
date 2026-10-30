"""Regression tests for the three defects found by the evaluation and the UI.

Each test fails on the code as it stood before Step 4D and passes after it.
They live together because what they have in common is their provenance: every
one of them is a crash a real run produced, not a case someone imagined.
"""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from app.analysis.schemas import ScopeOutput, TechnicalOutput
from app.db.engine import normalise_database_url
from app.domain.change_request import ChangeRequest
from app.domain.enums import (
    ActorType,
    ChangeKind,
    CRState,
    ImpactType,
    Party,
    Recommendation,
)
from app.domain.models import Contract
from app.domain.state_machine import can_transition, is_committing, transition
from app.main import app
from app.pipeline.costing import CostingError, compute_impact
from app.pipeline.decisions import decide
from app.pipeline.documents import check_documents
from app.pipeline.limits import LegalCheck, PolicyCheck
from app.repositories.postgres import seed_all
from app.seed.demo_contract import (
    GOVERNMENT_CONTRACT_ID,
    PRIVATE_CONTRACT_ID,
    build_private_contract,
)
from app.seed.demo_requests import TEXT_PCR_SMALL
from tests.conftest import TEST_DATABASE_URL, truncate_all

client = TestClient(app)


# ---------------------------------------------------------------------------
# (a) Analysis that finds missing documents must ask for them, not crash
#
# Stage 2 runs *inside* the analysis, so by the time the gap list exists the
# request is already in IN_ANALYSIS. That move was absent from the state
# machine, so analysing an incomplete request raised IllegalTransitionError
# and the API answered 500 instead of asking for the paperwork (FR-04).
# ---------------------------------------------------------------------------


def test_in_analysis_may_ask_for_documents() -> None:
    """The move exists, and it is not a committing one."""
    assert can_transition(CRState.IN_ANALYSIS, CRState.AWAITING_DOCUMENTS)
    assert not is_committing(CRState.IN_ANALYSIS, CRState.AWAITING_DOCUMENTS)
    # Asking for paperwork commits the organisation to nothing, so even an AI
    # actor may drive it (FR-04, NFR-15).
    assert (
        transition(CRState.IN_ANALYSIS, CRState.AWAITING_DOCUMENTS, ActorType.AI)
        is CRState.AWAITING_DOCUMENTS
    )


@pytest.mark.usefixtures("backend")
def test_analysing_an_incomplete_request_returns_the_gap_list() -> None:
    """Over HTTP, end to end: 200 with the gap list, not 500.

    The body is one the scripted provider has a recording for, so stage 1 still
    classifies it; only the attachments are short. That is the real shape of
    the defect - the analysis got far enough to find the gap and then fell over
    reporting it.
    """
    missing_the_quote = ["طلب تغيير رسمي"]
    cr_id = client.post(
        f"/api/contracts/{PRIVATE_CONTRACT_ID}/change-requests",
        json={
            "requester_name": "م. فهد القحطاني",
            "requester_party": Party.CONTRACTOR.value,
            "body_ar": TEXT_PCR_SMALL,
            "attachments": missing_the_quote,
        },
    ).json()["request"]["id"]

    response = client.post(f"/api/change-requests/{cr_id}/analyse")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["request"]["state"] == "AWAITING_DOCUMENTS"
    assert body["request"]["recommendation"] == "REQUEST_REVISION"
    # The gap list names what is missing rather than saying "incomplete".
    stage = next(s for s in body["trace"] if s["stage"] == "DOCUMENT_VALIDATION")
    assert "عرض سعر أو تحليل تكلفة" in stage["summary_ar"]
    assert stage["payload"]["missing"] == ["عرض سعر أو تحليل تكلفة"]
    assert stage["status"] == "BLOCKED"


@pytest.mark.usefixtures("backend")
def test_the_requester_is_told_which_documents_are_missing() -> None:
    """A gap list nobody receives is not a request for documents (FR-04)."""
    cr_id = client.post(
        f"/api/contracts/{PRIVATE_CONTRACT_ID}/change-requests",
        json={
            "requester_name": "م. فهد القحطاني",
            "requester_party": Party.CONTRACTOR.value,
            "body_ar": TEXT_PCR_SMALL,
            "attachments": ["طلب تغيير رسمي"],
        },
    ).json()["request"]["id"]
    client.post(f"/api/change-requests/{cr_id}/analyse")

    notifications = client.get(
        f"/api/notifications?party={Party.CONTRACTOR.value}&role=PROJECT_MANAGER"
    ).json()["notifications"]
    mine = [n for n in notifications if n["cr_id"] == cr_id]
    assert [n["kind"] for n in mine] == ["DOCUMENTS_REQUIRED"]
    assert "عرض سعر أو تحليل تكلفة" in mine[0]["message_ar"]


# ---------------------------------------------------------------------------
# (b) A decrease that names no quantity (TEST-17)
#
# "Drop the module entirely" states no number, so quantity_delta was None and
# the multiplication raised TypeError, crashing stage 5. Removing a whole line
# is worth that line's contract total; a decrease nobody can attach to a line
# goes to a human instead.
# ---------------------------------------------------------------------------

PRIVATE = build_private_contract()


def _scope(kind: ChangeKind, lines: tuple[str, ...], delta: Decimal | None) -> ScopeOutput:
    return ScopeOutput(
        provider="scripted",
        recorded=True,
        confidence=Decimal("0.9"),
        in_scope=False,
        kind=kind,
        matched_line_ids=lines,
        quantity_delta=delta,
    )


def _technical() -> TechnicalOutput:
    return TechnicalOutput(
        provider="scripted",
        recorded=True,
        confidence=Decimal("0.9"),
        changes_approved_product=False,
    )


def _within_policy() -> PolicyCheck:
    """A policy evaluation with nothing wrong in it, so rule 5 is what fires."""
    zero = Decimal("0")
    return PolicyCheck(
        cost_before_pct=zero,
        cost_after_pct=zero,
        cost_cap_pct=Decimal("20"),
        cost_exceeded=False,
        time_before_pct=zero,
        time_after_pct=zero,
        time_cap_pct=Decimal("20"),
        time_exceeded=False,
        exception_role="CEO",
    )


def _request(contract: Contract) -> ChangeRequest:
    return ChangeRequest(
        id="CR-TEST-17",
        contract_id=contract.id,
        requester_name="م. تجريبي",
        requester_party=Party.CONTRACTOR,
        submitted_at=datetime(2027, 2, 2, 9, 0, tzinfo=UTC),
        body_ar="إلغاء البند بالكامل.",
        attachments=("طلب تغيير رسمي",),
    )


def test_whole_line_removal_is_priced_from_the_contract_total() -> None:
    """No quantity stated means the whole line goes; the contract says what that is."""
    line = PRIVATE.line("ITM-07")
    assert line is not None

    impact = compute_impact(PRIVATE, _request(PRIVATE), _scope(ChangeKind.NCR, ("ITM-07",), None))

    assert impact.unpriceable is False
    assert impact.removed_value == line.total
    assert impact.cost_impact == -line.total
    assert impact.added_value == Decimal("0")
    assert impact.impact_type is ImpactType.COST
    # The figure is traceable to the contract, not to anyone's estimate.
    assert any("contract total" in note for note in impact.notes_en)


def test_a_partial_decrease_still_prices_from_the_unit_rate() -> None:
    """The whole-line path must not swallow the ordinary case."""
    line = PRIVATE.line("ITM-07")
    assert line is not None

    impact = compute_impact(
        PRIVATE, _request(PRIVATE), _scope(ChangeKind.NCR, ("ITM-07",), Decimal("3"))
    )

    assert impact.removed_value == Decimal("3") * line.unit_rate
    assert impact.unpriceable is False


def test_a_decrease_naming_no_line_goes_to_a_human() -> None:
    """Unidentifiable, so unpriceable - and that is an answer, not a crash."""
    impact = compute_impact(PRIVATE, _request(PRIVATE), _scope(ChangeKind.NCR, (), None))

    assert impact.unpriceable is True
    assert impact.unpriceable_reason
    assert impact.cost_impact == Decimal("0")


def test_a_decrease_naming_a_line_the_contract_does_not_have_is_an_error() -> None:
    """A line id that is simply wrong is a bug, not a question for a human."""
    with pytest.raises(CostingError) as raised:
        compute_impact(PRIVATE, _request(PRIVATE), _scope(ChangeKind.NCR, ("ITM-99",), None))
    assert raised.value.code == "UNKNOWN_LINE"


def test_an_unpriceable_request_is_sent_back_for_revision() -> None:
    """Stage 7 turns "cannot price" into a question, never into an approval."""
    impact = compute_impact(PRIVATE, _request(PRIVATE), _scope(ChangeKind.NCR, (), None))
    documents = check_documents(ImpactType.NONE, ("طلب تغيير رسمي",))
    assert documents.complete

    decision = decide(
        scope=_scope(ChangeKind.NCR, (), None),
        technical=_technical(),
        impact=impact,
        documents=documents,
        policy=_within_policy(),
        legal=LegalCheck(applies=False),
        confidences=(Decimal("0.9"),),
    )

    assert decision.recommendation is Recommendation.REQUEST_REVISION
    assert "CANNOT_PRICE" in decision.reason_codes


# ---------------------------------------------------------------------------
# (c) A contract row whose breakdown vanished
#
# A migration left CT-2027-0418 present but with no breakdown lines. The seed
# loader only checked whether the row existed, so it skipped the contract
# forever, and every read of it failed the Contract validator - /api/contracts
# answered 500. "Present" is not the same as "correct".
# ---------------------------------------------------------------------------


def _strip_breakdown(contract_id: str) -> None:
    engine = create_engine(normalise_database_url(TEST_DATABASE_URL))
    with engine.begin() as connection:
        connection.execute(
            text("delete from breakdown_lines where contract_id = :c"), {"c": contract_id}
        )
    engine.dispose()


def _line_count(contract_id: str) -> int:
    engine = create_engine(normalise_database_url(TEST_DATABASE_URL))
    with engine.begin() as connection:
        count = connection.scalar(
            text("select count(*) from breakdown_lines where contract_id = :c"),
            {"c": contract_id},
        )
    engine.dispose()
    return count or 0


def test_seed_loader_repairs_a_contract_whose_breakdown_is_missing(
    postgres_ready: bool,
) -> None:
    if not postgres_ready:
        pytest.skip("Postgres is not reachable; start it with docker compose up -d")

    truncate_all()
    first = seed_all()
    assert first["contracts"] == 2
    expected = len(build_private_contract().breakdown)
    assert _line_count(GOVERNMENT_CONTRACT_ID) == expected

    # Exactly what the migration did.
    _strip_breakdown(GOVERNMENT_CONTRACT_ID)
    assert _line_count(GOVERNMENT_CONTRACT_ID) == 0

    repaired = seed_all()

    assert repaired["contracts"] == 0, "the row exists; it must be repaired, not duplicated"
    assert repaired["repaired"] == 1
    assert _line_count(GOVERNMENT_CONTRACT_ID) == expected


def test_a_repaired_contract_can_be_read_again(postgres_ready: bool) -> None:
    """The symptom the UI saw: the list endpoint answering 500."""
    if not postgres_ready:
        pytest.skip("Postgres is not reachable; start it with docker compose up -d")

    truncate_all()
    seed_all()
    _strip_breakdown(GOVERNMENT_CONTRACT_ID)
    seed_all()

    from app.repositories.postgres import PostgresContractRepository

    contracts = PostgresContractRepository().list_contracts()
    found = next(c for c in contracts if c.id == GOVERNMENT_CONTRACT_ID)
    assert sum(line.total for line in found.breakdown) == found.original_value


def test_seeding_a_whole_database_changes_nothing(postgres_ready: bool) -> None:
    """Repair must not fire on every start-up, or it is just a rewrite loop."""
    if not postgres_ready:
        pytest.skip("Postgres is not reachable; start it with docker compose up -d")

    truncate_all()
    seed_all()

    again = seed_all()

    assert again == {"contracts": 0, "repaired": 0, "change_requests": 0}
