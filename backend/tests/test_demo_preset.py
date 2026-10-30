"""The salami demo preset, end to end over HTTP.

The preset exists so the video can show the cumulative protection without
twenty minutes of clicking. It is built by calling the real service functions
with the recorded AI outputs, so what appears on screen is a state the product
can actually reach - and these tests are what keeps that true. A preset that
wrote rows directly would demo a product that does not exist.
"""

from decimal import Decimal
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.domain.enums import OrderStatus
from app.main import app
from app.seed.demo_contract import GOVERNMENT_CONTRACT_ID
from app.seed.presets import APPROVED_SLICES, SLICE_VALUE
from tests.conftest import DEMO_TOKEN

client = TestClient(app)
pytestmark = pytest.mark.usefixtures("backend")

GOV = f"/api/contracts/{GOVERNMENT_CONTRACT_ID}"
CAP = Decimal("960000")
APPROVED_TOTAL = SLICE_VALUE * APPROVED_SLICES  # 945,000


def reset(preset: str | None = None, token: str = DEMO_TOKEN) -> Any:
    url = "/api/demo/reset" + (f"?preset={preset}" if preset else "")
    return client.post(url, headers={"X-Demo-Token": token})


def ledger() -> dict[str, Any]:
    return dict(client.get(f"{GOV}/ledger").json())


# ---------------------------------------------------------------------------
# The guard is the same one
# ---------------------------------------------------------------------------


def test_a_preset_still_needs_the_token() -> None:
    assert reset("salami", token="wrong").status_code == 403


def test_a_preset_with_no_token_is_refused() -> None:
    assert client.post("/api/demo/reset?preset=salami").status_code == 403


def test_an_unknown_preset_is_refused_by_name() -> None:
    """Better than silently resetting to the plain seed."""
    response = reset("not-a-preset")

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "UNKNOWN_PRESET"
    assert "salami" in response.json()["detail"]["message"]


def test_a_reset_with_no_preset_still_works() -> None:
    response = reset()

    assert response.status_code == 200
    assert response.json()["preset"] is None
    assert response.json()["preset_detail"] == {}


# ---------------------------------------------------------------------------
# What the preset builds
# ---------------------------------------------------------------------------


def test_the_preset_reports_what_it_built() -> None:
    body = reset("salami").json()

    assert body["preset"] == "salami"
    detail = body["preset_detail"]
    assert len(detail["approved_request_ids"]) == APPROVED_SLICES
    assert len(detail["variation_order_ids"]) == APPROVED_SLICES
    assert detail["awaiting_final_signature_id"]
    assert Decimal(detail["approved_increase_value"]) == APPROVED_TOTAL


def test_the_increase_meter_reads_945_000_of_960_000() -> None:
    """The number the video is about."""
    reset("salami")

    usage = ledger()["usage"]["INCREASE_EXISTING"]
    assert Decimal(usage["after_value"]) == APPROVED_TOTAL
    assert Decimal(usage["cap_value"]) == CAP
    assert Decimal(usage["headroom_value"]) == Decimal("15000")


def test_the_combined_cap_is_equally_close() -> None:
    reset("salami")

    combined = ledger()["usage"]["COMBINED"]
    assert Decimal(combined["after_value"]) == APPROVED_TOTAL
    assert Decimal(combined["cap_value"]) == CAP


def test_the_policy_layer_agrees() -> None:
    reset("salami")

    policy = ledger()["policy_usage"]["cost_increase"]
    assert Decimal(policy["used_value"]) == APPROVED_TOTAL


def test_seven_requests_are_approved_with_their_variation_orders() -> None:
    detail = reset("salami").json()["preset_detail"]

    for cr_id in detail["approved_request_ids"]:
        body = client.get(f"/api/change-requests/{cr_id}").json()
        assert body["request"]["state"] == "VO_ISSUED"
        assert body["variation_order_id"], cr_id
        # Every signature on the chain, by a person.
        assert all(step["decision"] == "APPROVED" for step in body["chain"])
        assert all(step["decided_by"] for step in body["chain"])

    issued = client.get(f"{GOV}/variation-orders").json()["variation_orders"]
    assert len(issued) == APPROVED_SLICES
    # A government VO cites the article it rests on (NFR-02).
    assert all(vo["cited_articles"] for vo in issued)


def test_every_approved_slice_is_on_the_ledger() -> None:
    reset("salami")

    entries = [
        order for order in ledger()["orders"] if order["status"] == OrderStatus.APPROVED.value
    ]
    assert len(entries) == APPROVED_SLICES
    assert all(Decimal(e["value"]) == SLICE_VALUE for e in entries)
    assert all(e["type"] == "INCREASE_EXISTING" for e in entries)


def test_the_eighth_is_one_signature_short() -> None:
    awaiting = reset("salami").json()["preset_detail"]["awaiting_final_signature_id"]

    body = client.get(f"/api/change-requests/{awaiting}").json()
    assert body["request"]["state"] == "IN_APPROVAL"
    pending = [step for step in body["chain"] if step["decision"] == "PENDING"]
    assert len(pending) == 1, "exactly one signature should be outstanding"
    assert pending[0]["position"] == len(body["chain"])
    # Its entry is pending: visible, counted toward nothing.
    usage = ledger()["usage"]["INCREASE_EXISTING"]
    assert Decimal(usage["pending_value"]) == SLICE_VALUE


# ---------------------------------------------------------------------------
# The moment the demo is for
# ---------------------------------------------------------------------------


def test_signing_the_last_step_is_refused_with_the_articles() -> None:
    detail = reset("salami").json()["preset_detail"]
    awaiting = detail["awaiting_final_signature_id"]
    step = next(
        s
        for s in client.get(f"/api/change-requests/{awaiting}").json()["chain"]
        if s["decision"] == "PENDING"
    )

    response = client.post(
        f"/api/change-requests/{awaiting}/decide",
        json={
            "party": step["party"],
            "role": step["role"],
            "decided_by": "المستشار النظامي",
            "decision": "APPROVED",
        },
    )

    assert response.status_code == 409, response.text
    body = response.json()["detail"]
    assert body["code"] == "LEGAL_CAP_EXCEEDED"
    assert "Article 67(1)(b)" in body["articles"]
    assert "Article 67(2)" in body["articles"]


def test_the_refusal_changes_no_total() -> None:
    detail = reset("salami").json()["preset_detail"]
    awaiting = detail["awaiting_final_signature_id"]
    step = next(
        s
        for s in client.get(f"/api/change-requests/{awaiting}").json()["chain"]
        if s["decision"] == "PENDING"
    )
    before = ledger()["usage"]["INCREASE_EXISTING"]

    client.post(
        f"/api/change-requests/{awaiting}/decide",
        json={
            "party": step["party"],
            "role": step["role"],
            "decided_by": "المستشار النظامي",
            "decision": "APPROVED",
        },
    )

    after = ledger()["usage"]["INCREASE_EXISTING"]
    assert after["after_value"] == before["after_value"]
    assert after["pending_value"] == before["pending_value"]
    assert Decimal(after["after_value"]) == APPROVED_TOTAL


def test_the_refusal_leaves_a_record_a_judge_can_read() -> None:
    detail = reset("salami").json()["preset_detail"]
    awaiting = detail["awaiting_final_signature_id"]
    step = next(
        s
        for s in client.get(f"/api/change-requests/{awaiting}").json()["chain"]
        if s["decision"] == "PENDING"
    )
    client.post(
        f"/api/change-requests/{awaiting}/decide",
        json={
            "party": step["party"],
            "role": step["role"],
            "decided_by": "المستشار النظامي",
            "decision": "APPROVED",
        },
    )

    request = client.get(f"/api/change-requests/{awaiting}").json()["request"]
    assert request["legally_blocked"] is True
    assert request["needs_legal_review"] is True

    events = client.get(f"{GOV}/audit").json()["events"]
    refusals = [e for e in events if e["action"] == "CR_LEGAL_CAP_REFUSED"]
    assert [e["entity_id"] for e in refusals] == [awaiting]


# ---------------------------------------------------------------------------
# It is built, not written
# ---------------------------------------------------------------------------


def test_the_preset_went_through_the_pipeline() -> None:
    """Every request has a full agent trace, because it was really analysed."""
    detail = reset("salami").json()["preset_detail"]

    trace = client.get(f"/api/change-requests/{detail['approved_request_ids'][0]}/trace").json()
    stages = [stage["stage"] for stage in trace["stages"]]
    assert "INTAKE" in stages
    assert "SCOPE_ANALYSIS" in stages
    assert "ORCHESTRATOR" in stages
    # Recorded, not live: a reset must cost nothing and never vary (FR-19).
    assert all(s["provider"] in (None, "scripted") for s in trace["stages"])


def test_resetting_again_rebuilds_the_same_state() -> None:
    """A demo that drifts between takes is not a demo."""
    first = reset("salami").json()["preset_detail"]
    first_total = ledger()["usage"]["INCREASE_EXISTING"]["after_value"]

    second = reset("salami").json()["preset_detail"]

    assert second["approved_request_ids"] == first["approved_request_ids"]
    assert second["awaiting_final_signature_id"] == first["awaiting_final_signature_id"]
    assert ledger()["usage"]["INCREASE_EXISTING"]["after_value"] == first_total


def test_a_plain_reset_clears_the_preset() -> None:
    reset("salami")
    assert Decimal(ledger()["usage"]["INCREASE_EXISTING"]["after_value"]) == APPROVED_TOTAL

    reset()

    assert Decimal(ledger()["usage"]["INCREASE_EXISTING"]["after_value"]) == 0
    assert ledger()["orders"] == []
