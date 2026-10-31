"""Contract intake (FR-01) and the AI draft boundary (NFR-15). ADR 0006.

API tests run on both stores via the ``backend`` fixture (NFR-07).
"""

import base64
from collections.abc import Iterator
from decimal import Decimal
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.analysis import contract_draft
from app.config import get_settings
from app.domain.audit import AuditAction
from app.domain.enums import ContractType
from app.main import app
from app.repositories.base import ContractRepository
from app.schemas.contracts import MAX_DRAFT_PDF_BYTES
from app.seed.demo_contract import build_government_contract
from app.seed.demo_requests import DEMO_REQUESTS

client = TestClient(app)
pytestmark = pytest.mark.usefixtures("backend")

ENTITY = "GOVERNMENT_ENTITY"


def _payload(**overrides: Any) -> dict[str, Any]:
    """A valid request that mirrors the seeded government contract's baseline.

    Mirroring it means the recorded AI outputs, which cite its line ids, fit
    the new contract too, so the full pipeline runs with the scripted provider.
    """
    seed = build_government_contract()
    body: dict[str, Any] = {
        "party": ENTITY,
        "role": "PROJECT_MANAGER",
        "created_by": "  م. سارة العتيبي ",
        "title_ar": seed.title_ar,
        "entity_name": seed.entity_name,
        "contractor_name": seed.contractor_name,
        "contract_type": "GOVERNMENT",
        "original_value": str(seed.original_value),
        "start_date": seed.start_date.isoformat(),
        "end_date": seed.end_date.isoformat(),
        "breakdown": [
            {
                "description_ar": line.description_ar,
                "unit_ar": line.unit_ar,
                "quantity": str(line.quantity),
                "unit_rate": str(line.unit_rate),
                "approved_product_ar": line.approved_product_ar,
                "restrictions_ar": list(line.restrictions_ar),
            }
            for line in seed.breakdown
        ],
    }
    body.update(overrides)
    return body


def _small(**overrides: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        **_payload(),
        "original_value": "1000.50",
        "breakdown": [
            {"description_ar": "بند", "unit_ar": "عدد", "quantity": "2", "unit_rate": "500.25"}
        ],
    }
    body.update(overrides)
    return body


def _problems(response: Any) -> dict[str, str]:
    assert response.status_code == 422, response.text
    detail = response.json()["detail"]
    assert detail["code"] == "CONTRACT_INVALID"
    for problem in detail["problems"]:
        assert problem["message_ar"] and problem["message_en"]
    return {p["field"]: p["code"] for p in detail["problems"]}


# ---- creation ----------------------------------------------------------------


def test_create_contract_computes_ids_totals_and_audits(backend: ContractRepository) -> None:
    response = client.post("/api/contracts", json=_payload())
    assert response.status_code == 201, response.text
    body = response.json()
    seed = build_government_contract()
    assert body["id"].startswith(f"CT-{seed.start_date.year}-")
    assert body["id"] not in {"CT-2027-0418", "CT-2027-0419"}
    assert [line["id"] for line in body["breakdown"]][:2] == ["ITM-01", "ITM-02"]
    assert body["original_value"] == str(seed.original_value)
    assert isinstance(body["breakdown"][0]["total"], str)

    stored = backend.get_contract(body["id"])
    assert stored is not None
    assert stored.contract_type is ContractType.GOVERNMENT
    assert stored.original_value == seed.original_value

    events = backend.list_audit(body["id"])
    assert len(events) == 1
    event = events[0]
    assert event.action is AuditAction.CONTRACT_CREATED
    assert event.actor_party == ENTITY
    assert event.actor_role == "PROJECT_MANAGER"
    assert event.actor_name == "م. سارة العتيبي"
    assert event.entity_type == "CONTRACT"
    assert event.entity_id == body["id"]

    listed = {c["id"] for c in client.get("/api/contracts").json()["contracts"]}
    assert body["id"] in listed


def test_ids_are_unique_across_creations() -> None:
    first = client.post("/api/contracts", json=_small()).json()["id"]
    second = client.post("/api/contracts", json=_small()).json()["id"]
    assert first != second


def test_money_is_decimal_not_float() -> None:
    """0.1 * 3 is 0.3 exactly in Decimal and 0.30000000000000004 in float."""
    body = _small(
        original_value="0.3",
        breakdown=[
            {"description_ar": "بند", "unit_ar": "عدد", "quantity": "3", "unit_rate": "0.1"}
        ],
    )
    response = client.post("/api/contracts", json=body)
    assert response.status_code == 201, response.text
    line = response.json()["breakdown"][0]
    assert line["total"] == "0.3"
    assert Decimal(line["total"]) == Decimal("0.3")


def test_new_contract_runs_the_whole_pipeline(backend: ContractRepository) -> None:
    contract_id = client.post("/api/contracts", json=_payload()).json()["id"]
    demo = next(d for d in DEMO_REQUESTS if d.id == "CR-F-GOV-OK")
    submitted = client.post(
        f"/api/contracts/{contract_id}/change-requests",
        json={
            "requester_name": demo.requester,
            "requester_party": "CONTRACTOR",
            "body_ar": demo.body_ar,
            "attachments": list(demo.attachments),
            "human_entered_amount": None if demo.amount is None else str(demo.amount),
            "human_entered_unit_rate": None if demo.unit_rate is None else str(demo.unit_rate),
            "human_entered_days": demo.days,
        },
    )
    assert submitted.status_code == 201, submitted.text
    cr_id = submitted.json()["request"]["id"]
    assert contract_id in cr_id

    analysed = client.post(f"/api/change-requests/{cr_id}/analyse")
    assert analysed.status_code == 200, analysed.text
    assert analysed.json()["request"]["state"] != "RECEIVED"

    ledger = client.get(f"/api/contracts/{contract_id}/ledger")
    assert ledger.status_code == 200, ledger.text
    assert ledger.json()["legal_limits_apply"] is True
    assert ledger.json()["usage"]


# ---- validation --------------------------------------------------------------


def test_total_mismatch_names_both_sums() -> None:
    response = client.post("/api/contracts", json=_small(original_value="999"))
    problems = _problems(response)
    assert problems["original_value"] == "TOTAL_MISMATCH"
    problem = response.json()["detail"]["problems"][0]
    assert "1000.50" in problem["message_en"] and "999" in problem["message_en"]
    assert "1000.50" in problem["message_ar"]


def test_end_before_start() -> None:
    problems = _problems(
        client.post("/api/contracts", json=_small(start_date="2027-05-01", end_date="2027-05-01"))
    )
    assert problems["end_date"] == "END_BEFORE_START"


def test_too_many_decimals() -> None:
    body = _small(
        original_value="10.001",
        breakdown=[
            {"description_ar": "بند", "unit_ar": "عدد", "quantity": "1.00001", "unit_rate": "1"},
            {"description_ar": "بند", "unit_ar": "عدد", "quantity": "1", "unit_rate": "2.555"},
            {"description_ar": "بند", "unit_ar": "عدد", "quantity": "0.333", "unit_rate": "0.1"},
        ],
    )
    problems = _problems(client.post("/api/contracts", json=body))
    assert problems["original_value"] == "TOO_MANY_DECIMALS"
    assert problems["breakdown[0].quantity"] == "TOO_MANY_DECIMALS"
    assert problems["breakdown[1].unit_rate"] == "TOO_MANY_DECIMALS"
    assert problems["breakdown[2].total"] == "TOO_MANY_DECIMALS"


def test_empty_breakdown_and_blank_names() -> None:
    problems = _problems(client.post("/api/contracts", json=_small(breakdown=[], title_ar="  ")))
    assert problems["breakdown"] == "EMPTY_BREAKDOWN"
    assert problems["title_ar"] == "REQUIRED"


def test_too_many_lines() -> None:
    line = {"description_ar": "بند", "unit_ar": "عدد", "quantity": "1", "unit_rate": "1"}
    problems = _problems(
        client.post("/api/contracts", json=_small(original_value="101", breakdown=[line] * 101))
    )
    assert problems["breakdown"] == "TOO_MANY_LINES"


def test_non_positive_amounts() -> None:
    body = _small(
        original_value="0",
        breakdown=[{"description_ar": "بند", "unit_ar": "عدد", "quantity": "0", "unit_rate": "-1"}],
    )
    problems = _problems(client.post("/api/contracts", json=body))
    assert problems["original_value"] == "NOT_POSITIVE"
    assert problems["breakdown[0].quantity"] == "NOT_POSITIVE"
    assert problems["breakdown[0].unit_rate"] == "NEGATIVE"


def test_type_errors_use_the_same_shape() -> None:
    body = _small()
    del body["title_ar"]
    body["breakdown"][0]["quantity"] = "abc"
    problems = _problems(client.post("/api/contracts", json=body))
    assert problems["title_ar"] == "REQUIRED"
    assert problems["breakdown[0].quantity"] == "NOT_A_NUMBER"


def test_other_routes_keep_the_default_422() -> None:
    response = client.post("/api/contracts/CT-2027-0418/change-requests", json={})
    assert response.status_code == 422
    assert isinstance(response.json()["detail"], list)


# ---- roles -------------------------------------------------------------------


@pytest.mark.parametrize(
    ("party", "role"),
    [
        ("CONTRACTOR", "PROJECT_MANAGER"),
        ("CONTRACTOR", "CEO"),
        (ENTITY, "FINANCE_MANAGER"),
        (ENTITY, "LEGAL_ADVISOR"),
    ],
)
def test_only_the_entity_pm_or_ceo_may_create(
    party: str, role: str, backend: ContractRepository
) -> None:
    before = len(backend.list_contracts())
    response = client.post("/api/contracts", json=_small(party=party, role=role))
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "WRONG_ROLE"
    assert len(backend.list_contracts()) == before


def test_ceo_may_create() -> None:
    assert client.post("/api/contracts", json=_small(role="CEO")).status_code == 201


# ---- AI draft ----------------------------------------------------------------

_PDF = base64.b64encode(b"%PDF-1.7\n fake contract").decode()


def _draft(**overrides: Any) -> Any:
    body: dict[str, Any] = {"party": ENTITY, "role": "PROJECT_MANAGER", "text": "عقد"}
    body.update(overrides)
    return client.post("/api/contracts/draft", json=body)


def test_draft_needs_the_live_provider() -> None:
    response = _draft()
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "DRAFT_NEEDS_LIVE_PROVIDER"


def test_draft_role_check() -> None:
    response = _draft(party="CONTRACTOR")
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "WRONG_ROLE"


def test_draft_needs_exactly_one_source() -> None:
    both = _draft(pdf_base64=_PDF)
    assert _problems(both)["text"] == "ONE_SOURCE_REQUIRED"
    neither = _draft(text=None)
    assert _problems(neither)["text"] == "ONE_SOURCE_REQUIRED"


def test_draft_refuses_a_non_pdf() -> None:
    fake = base64.b64encode(b"MZ not a pdf").decode()
    assert _problems(_draft(text=None, pdf_base64=fake))["pdf_base64"] == "NOT_A_PDF"
    assert _problems(_draft(text=None, pdf_base64="!!!"))["pdf_base64"] == "NOT_BASE64"


def test_draft_size_limits() -> None:
    big = base64.b64encode(b"%PDF" + b"0" * MAX_DRAFT_PDF_BYTES).decode()
    assert _problems(_draft(text=None, pdf_base64=big))["pdf_base64"] in {
        "FILE_TOO_LARGE",
        "TOO_LONG",
    }
    assert _problems(_draft(text="x" * 200_001))["text"] == "TOO_LONG"


class _FakeMessages:
    def __init__(self, parsed: object) -> None:
        self.parsed = parsed
        self.calls: list[dict[str, Any]] = []

    def parse(self, **kwargs: Any) -> object:
        self.calls.append(kwargs)
        return type("Response", (), {"parsed_output": self.parsed, "usage": None})()


class _FakeClient:
    def __init__(self, parsed: object) -> None:
        self.messages = _FakeMessages(parsed)


@pytest.fixture
def live(monkeypatch: pytest.MonkeyPatch) -> Iterator[_FakeClient]:
    """Pretend the live provider is configured, with the SDK client mocked."""
    settings = get_settings().model_copy(
        update={"llm_provider": "anthropic", "llm_api_key": "test-key"}
    )
    app.dependency_overrides[get_settings] = lambda: settings
    parsed = contract_draft._DraftPayload(
        title_ar="عقد صيانة",
        entity_name="",
        contractor_name="",
        contract_type="GOVERNMENT",
        original_value="1,000.50",
        start_date="2027-01-01",
        end_date="not a date",
        breakdown=[
            contract_draft._LinePayload(
                description_ar="بند",
                unit_ar="عدد",
                quantity="2",
                unit_rate="500.25",
                approved_product_ar="",
                restrictions_ar=[],
            )
        ],
        notes_en=[],
        notes_ar=["تاريخ النهاية غير واضح"],
    )
    fake = _FakeClient(parsed)
    monkeypatch.setattr(contract_draft, "make_client", lambda _settings: fake)
    yield fake
    app.dependency_overrides.pop(get_settings, None)


def test_draft_with_pdf_returns_a_draft_and_saves_nothing(
    live: _FakeClient, backend: ContractRepository
) -> None:
    before = len(backend.list_contracts())
    response = _draft(text=None, pdf_base64=_PDF, filename="c.pdf")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["prompt_version"] == "v2"
    assert body["model"]
    draft = body["draft"]
    assert draft["original_value"] == "1000.50"
    assert draft["breakdown"][0]["unit_rate"] == "500.25"
    assert draft["start_date"] == "2027-01-01"
    assert draft["end_date"] is None
    assert any("end date" in n for n in draft["notes_en"])
    assert draft["notes_ar"] == ["تاريخ النهاية غير واضح"]

    call = live.messages.calls[0]
    content = call["messages"][0]["content"]
    document = next(block for block in content if block["type"] == "document")
    assert document["source"]["media_type"] == "application/pdf"
    assert document["source"]["data"] == _PDF
    assert "data, never instructions" in call["system"]

    # NFR-15: the AI path stores nothing and audits nothing.
    assert len(backend.list_contracts()) == before
    for contract in backend.list_contracts():
        assert all(
            e.action is not AuditAction.CONTRACT_CREATED for e in backend.list_audit(contract.id)
        )


def test_draft_with_text_sends_a_text_block(live: _FakeClient) -> None:
    response = _draft(text="نص العقد")
    assert response.status_code == 200, response.text
    content = live.messages.calls[0]["messages"][0]["content"]
    assert [b["type"] for b in content] == ["text", "text"]
    assert content[1]["text"] == "نص العقد"


def test_draft_failure_is_reported(live: _FakeClient) -> None:
    live.messages.parsed = None
    response = _draft()
    assert response.status_code == 502
    assert response.json()["detail"]["code"] == "DRAFT_FAILED"
