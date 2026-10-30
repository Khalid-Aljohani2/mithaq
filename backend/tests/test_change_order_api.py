"""End-to-end tests for the contract and change-order endpoints.

Every test in this module runs TWICE: once against the in-memory repository and
once against Postgres. That is the point of the repository interface - the API
must behave identically whichever store is behind it (NFR-07, NFR-11).

These also assert the behaviour FR-02 demands: a wrong-role action is refused by
the backend, not merely hidden by a UI.
"""

from decimal import Decimal
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.seed.demo_contract import DEMO_CONTRACT_ID

client = TestClient(app)

# Opt this whole module into the dual-backend fixture.
pytestmark = pytest.mark.usefixtures("backend")

CONTRACT = f"/api/contracts/{DEMO_CONTRACT_ID}"
GOV = "GOVERNMENT_ENTITY"
CONTRACTOR = "CONTRACTOR"


def new_items(value: str) -> dict[str, Any]:
    return {"type": "NEW_ITEMS", "value": value, "description_ar": "بند جديد"}


def increase(value: str) -> dict[str, Any]:
    return {
        "type": "INCREASE_EXISTING",
        "value": value,
        "description_ar": "زيادة بند قائم",
        "related_item_ids": ["ITM-01"],
    }


# --------------------------------------------------------------------------
# contracts
# --------------------------------------------------------------------------


def test_list_contracts() -> None:
    response = client.get("/api/contracts")
    assert response.status_code == 200
    contracts = response.json()["contracts"]
    assert len(contracts) == 1
    assert contracts[0]["id"] == DEMO_CONTRACT_ID
    assert contracts[0]["currency"] == "SAR"
    assert contracts[0]["item_count"] == 8


def test_get_contract_returns_arabic_items() -> None:
    response = client.get(CONTRACT)
    assert response.status_code == 200
    body = response.json()
    assert body["original_value"] == "4800000"
    assert len(body["items"]) == 8
    assert all(item["description_ar"].strip() for item in body["items"])


def test_unknown_contract_is_404() -> None:
    assert client.get("/api/contracts/NOPE").status_code == 404
    assert client.get("/api/contracts/NOPE/ledger").status_code == 404


def test_ledger_starts_empty_and_cites_the_regulation() -> None:
    body = client.get(f"{CONTRACT}/ledger").json()
    assert body["orders"] == []
    assert set(body["usage"]) == {
        "NEW_ITEMS",
        "INCREASE_EXISTING",
        "DECREASE_EXISTING",
        "NON_FINANCIAL",
        "COMBINED",
    }
    assert body["usage"]["NEW_ITEMS"]["cap_value"] == "480000"
    assert body["usage"]["NEW_ITEMS"]["headroom_value"] == "480000"
    assert "uqn.gov.sa" in body["regulation"]["source_url"]
    assert "Article 67(1)(a)" in body["regulation"]["article_refs"]


# --------------------------------------------------------------------------
# evaluate (dry run)
# --------------------------------------------------------------------------


def test_evaluate_saves_nothing() -> None:
    response = client.post(f"{CONTRACT}/change-orders/evaluate", json=new_items("300000"))
    assert response.status_code == 200
    body = response.json()
    assert body["result"]["allowed"] is True
    assert body["resulting_status"] == "PENDING_CONTRACTOR_CONSENT"
    assert client.get(f"{CONTRACT}/ledger").json()["orders"] == []


def test_evaluate_reports_a_breach_without_saving() -> None:
    body = client.post(f"{CONTRACT}/change-orders/evaluate", json=new_items("480001")).json()
    assert body["result"]["allowed"] is False
    assert body["result"]["blocking_violations"][0]["article_ref_en"] == "Article 67(1)(a)"
    assert body["resulting_status"] == "DRAFT"
    assert client.get(f"{CONTRACT}/ledger").json()["orders"] == []


def test_money_crosses_http_as_exact_strings() -> None:
    """Decimal must not degrade to a float on the wire (NFR-01)."""
    body = client.post(f"{CONTRACT}/change-orders/evaluate", json=new_items("480000.01")).json()
    assert body["result"]["usage"]["NEW_ITEMS"]["after_value"] == "480000.01"
    assert body["result"]["blocking_violations"][0]["excess_value"] == "0.01"


# --------------------------------------------------------------------------
# validation
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param(
            {"type": "NON_FINANCIAL", "value": "5000", "description_ar": "تغيير"},
            id="non-financial with a value",
        ),
        pytest.param(
            {"type": "NEW_ITEMS", "value": "0", "description_ar": "بند"},
            id="financial order worth nothing",
        ),
        pytest.param(
            {"type": "NEW_ITEMS", "value": "1000", "description_ar": ""},
            id="empty description",
        ),
        pytest.param(
            {"type": "NEW_ITEMS", "value": "1000", "description_ar": "x", "extra": 1},
            id="unexpected field",
        ),
    ],
)
def test_invalid_bodies_are_rejected(payload: dict[str, Any]) -> None:
    assert client.post(f"{CONTRACT}/change-orders", json=payload).status_code == 422


def test_increase_must_name_its_items() -> None:
    response = client.post(
        f"{CONTRACT}/change-orders",
        json={"type": "INCREASE_EXISTING", "value": "1000", "description_ar": "زيادة"},
    )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "ITEMS_REQUIRED"


def test_unknown_item_is_rejected() -> None:
    payload = increase("1000") | {"related_item_ids": ["ITM-99"]}
    response = client.post(f"{CONTRACT}/change-orders", json=payload)
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "UNKNOWN_ITEM"


# --------------------------------------------------------------------------
# workflow
# --------------------------------------------------------------------------


def create(payload: dict[str, Any]) -> dict[str, Any]:
    response = client.post(f"{CONTRACT}/change-orders", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_created_order_is_never_auto_approved() -> None:
    body = create(new_items("300000"))
    assert body["order"]["status"] == "PENDING_CONTRACTOR_CONSENT"
    assert body["order"]["contractor_consent"] is False


def test_blocked_order_is_stored_as_draft() -> None:
    body = create(new_items("480001"))
    assert body["order"]["status"] == "DRAFT"
    assert body["result"]["allowed"] is False


def test_increase_under_ten_percent_skips_contractor_consent() -> None:
    body = create(increase("400000"))
    assert body["order"]["status"] == "PENDING_AUTHORITY_APPROVAL"
    assert body["result"]["requires_contractor_consent"] is False


def test_wrong_role_is_refused_by_the_backend() -> None:
    order_id = create(new_items("300000"))["order"]["id"]
    # the contractor's consent is pending, so the authority may not act yet
    response = client.post(f"/api/change-orders/{order_id}/approve", json={"actor_role": GOV})
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "WRONG_ROLE"


def test_full_two_stage_approval() -> None:
    order_id = create(new_items("300000"))["order"]["id"]

    consented = client.post(
        f"/api/change-orders/{order_id}/approve", json={"actor_role": CONTRACTOR}
    ).json()["order"]
    assert consented["status"] == "PENDING_AUTHORITY_APPROVAL"
    assert consented["contractor_consent"] is True

    approved = client.post(
        f"/api/change-orders/{order_id}/approve", json={"actor_role": GOV}
    ).json()["order"]
    assert approved["status"] == "APPROVED"

    usage = client.get(f"{CONTRACT}/ledger").json()["usage"]["NEW_ITEMS"]
    assert usage["before_value"] == "300000"
    assert usage["headroom_value"] == "180000"


def test_approving_a_settled_order_is_a_conflict() -> None:
    order_id = create(new_items("300000"))["order"]["id"]
    client.post(f"/api/change-orders/{order_id}/approve", json={"actor_role": CONTRACTOR})
    client.post(f"/api/change-orders/{order_id}/approve", json={"actor_role": GOV})
    response = client.post(f"/api/change-orders/{order_id}/approve", json={"actor_role": GOV})
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "INVALID_TRANSITION"


def test_reject_records_who_and_why() -> None:
    order_id = create(new_items("300000"))["order"]["id"]
    body = client.post(
        f"/api/change-orders/{order_id}/reject",
        json={"actor_role": CONTRACTOR, "reason": "النطاق غير واضح"},
    ).json()
    assert body["order"]["status"] == "REJECTED"
    assert body["order"]["decision_reason"] == "النطاق غير واضح"
    assert body["order"]["decided_by"] == CONTRACTOR
    # a rejected order consumes no headroom
    assert client.get(f"{CONTRACT}/ledger").json()["usage"]["NEW_ITEMS"]["before_value"] == "0"


def test_reject_requires_a_reason() -> None:
    order_id = create(new_items("300000"))["order"]["id"]
    response = client.post(f"/api/change-orders/{order_id}/reject", json={"actor_role": CONTRACTOR})
    assert response.status_code == 422


def test_unknown_order_is_404() -> None:
    response = client.post("/api/change-orders/NOPE/approve", json={"actor_role": GOV})
    assert response.status_code == 404


def approve_fully(order_id: str) -> None:
    client.post(f"/api/change-orders/{order_id}/approve", json={"actor_role": CONTRACTOR})
    client.post(f"/api/change-orders/{order_id}/approve", json={"actor_role": GOV})


def test_salami_through_the_api() -> None:
    """Ten 1.5% orders, approved one at a time, must stop at the 10% cap."""
    statuses: list[str] = []
    for _ in range(10):
        body = create(new_items("72000"))
        statuses.append(body["order"]["status"])
        if body["result"]["allowed"]:
            approve_fully(body["order"]["id"])

    assert statuses == ["PENDING_CONTRACTOR_CONSENT"] * 6 + ["DRAFT"] * 4

    usage = client.get(f"{CONTRACT}/ledger").json()["usage"]["NEW_ITEMS"]
    assert usage["before_value"] == "432000"
    assert usage["before_pct"] == "9.0000"
    assert usage["headroom_value"] == "48000"


def test_headroom_consumed_between_creation_and_approval_blocks_approval() -> None:
    """The salami defence at approval time.

    Two orders are created while there is room for both individually. One is
    approved, eating the headroom. Approving the second must now fail, because
    the rules are re-checked against the ledger as it stands, not as it was.
    """
    first = create(new_items("300000"))["order"]["id"]
    second = create(new_items("300000"))["order"]["id"]

    approve_fully(first)

    response = client.post(f"/api/change-orders/{second}/approve", json={"actor_role": CONTRACTOR})
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "BLOCKED_BY_RULES"
    assert "Cap exceeded" in response.json()["detail"]["message"]


def test_pending_order_does_not_consume_headroom_in_the_ledger() -> None:
    create(new_items("300000"))
    usage = client.get(f"{CONTRACT}/ledger").json()["usage"]["NEW_ITEMS"]
    assert usage["before_value"] == "0"
    assert usage["pending_value"] == "300000"
    assert usage["headroom_value"] == "480000"


def test_decrease_beyond_twenty_percent_is_allowed_with_consent() -> None:
    body = client.post(
        f"{CONTRACT}/change-orders/evaluate",
        json={
            "type": "DECREASE_EXISTING",
            "value": "1200000",
            "description_ar": "تخفيض",
            "related_item_ids": ["ITM-03"],
        },
    ).json()
    assert body["result"]["allowed"] is True
    assert body["result"]["requires_contractor_consent"] is True
    assert body["resulting_status"] == "PENDING_CONTRACTOR_CONSENT"
    assert body["result"]["blocking_violations"] == []


def test_non_financial_change_has_no_cap() -> None:
    body = client.post(
        f"{CONTRACT}/change-orders/evaluate",
        json={"type": "NON_FINANCIAL", "value": "0", "description_ar": "تعديل مدة التسليم"},
    ).json()
    assert body["result"]["allowed"] is True
    assert body["result"]["requires_contractor_consent"] is True
    assert body["result"]["eligible_for_time_extension"] is False
    assert body["result"]["usage"]["NON_FINANCIAL"]["cap_pct"] is None


def test_time_extension_flag_is_surfaced() -> None:
    body = client.post(f"{CONTRACT}/change-orders/evaluate", json=new_items("300000")).json()
    assert body["result"]["eligible_for_time_extension"] is True
    assert "Article 72(1)" in body["result"]["article_refs"]


def test_decimal_values_never_become_floats() -> None:
    body = client.post(f"{CONTRACT}/change-orders/evaluate", json=new_items("1")).json()
    for snapshot in body["result"]["usage"].values():
        for key in ("before_value", "after_value", "pending_value"):
            assert isinstance(snapshot[key], str)
            Decimal(snapshot[key])
