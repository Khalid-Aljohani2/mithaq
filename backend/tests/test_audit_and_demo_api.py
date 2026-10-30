"""Audit trail (FR-13) and demo reset (FR-15) over HTTP.

Runs against both repository backends, like the rest of the API suite.
"""

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app
from app.seed.demo_contract import DEMO_CONTRACT_ID
from tests.conftest import DEMO_TOKEN

client = TestClient(app)
pytestmark = pytest.mark.usefixtures("backend")

CONTRACT = f"/api/contracts/{DEMO_CONTRACT_ID}"
GOV = "GOVERNMENT_ENTITY"
CONTRACTOR = "CONTRACTOR"
RESET = "/api/demo/reset"


def create_order(value: str = "300000") -> str:
    response = client.post(
        f"{CONTRACT}/change-orders",
        json={"type": "NEW_ITEMS", "value": value, "description_ar": "بند جديد"},
    )
    assert response.status_code == 201, response.text
    return response.json()["order"]["id"]


def audit() -> list[dict[str, Any]]:
    response = client.get(f"{CONTRACT}/audit")
    assert response.status_code == 200
    return response.json()["events"]


# --------------------------------------------------------------------------
# audit trail
# --------------------------------------------------------------------------


def test_audit_starts_empty() -> None:
    assert audit() == []


def test_unknown_contract_audit_is_404() -> None:
    assert client.get("/api/contracts/NOPE/audit").status_code == 404


def test_creating_an_order_is_audited() -> None:
    order_id = create_order()
    (event,) = audit()
    assert event["action"] == "ORDER_CREATED"
    assert event["entity_id"] == order_id
    assert event["entity_type"] == "change_order"
    assert event["previous_state"] is None
    assert event["new_state"] == "PENDING_CONTRACTOR_CONSENT"
    assert event["occurred_at"]


def test_full_approval_writes_one_row_per_transition() -> None:
    order_id = create_order()
    client.post(f"/api/change-orders/{order_id}/approve", json={"actor_role": CONTRACTOR})
    client.post(f"/api/change-orders/{order_id}/approve", json={"actor_role": GOV})

    events = audit()
    assert [e["action"] for e in events] == [
        "ORDER_CREATED",
        "CONTRACTOR_CONSENTED",
        "ORDER_APPROVED",
    ]
    assert [(e["previous_state"], e["new_state"]) for e in events] == [
        (None, "PENDING_CONTRACTOR_CONSENT"),
        ("PENDING_CONTRACTOR_CONSENT", "PENDING_AUTHORITY_APPROVAL"),
        ("PENDING_AUTHORITY_APPROVAL", "APPROVED"),
    ]
    assert [e["actor_role"] for e in events] == [GOV, CONTRACTOR, GOV]


def test_rejection_records_the_reason() -> None:
    order_id = create_order()
    client.post(
        f"/api/change-orders/{order_id}/reject",
        json={"actor_role": CONTRACTOR, "reason": "الاعتماد المالي غير متاح"},
    )
    event = audit()[-1]
    assert event["action"] == "ORDER_REJECTED"
    assert event["reason"] == "الاعتماد المالي غير متاح"
    assert event["new_state"] == "REJECTED"


def test_refused_actions_are_not_audited() -> None:
    """A rejected role attempt changed no state, so it writes no row."""
    order_id = create_order()
    before = len(audit())
    assert (
        client.post(f"/api/change-orders/{order_id}/approve", json={"actor_role": GOV}).status_code
        == 403
    )
    assert len(audit()) == before


def test_audit_ids_are_monotonic() -> None:
    for _ in range(3):
        create_order("10000")
    ids = [e["id"] for e in audit()]
    assert ids == sorted(ids)
    assert len(set(ids)) == len(ids)


# --------------------------------------------------------------------------
# demo reset
# --------------------------------------------------------------------------


def test_reset_requires_the_token() -> None:
    assert client.post(RESET).status_code == 403
    assert client.post(RESET, headers={"X-Demo-Token": "wrong"}).status_code == 403


def test_reset_restores_seed_state() -> None:
    create_order()
    assert client.get(f"{CONTRACT}/ledger").json()["orders"]

    response = client.post(RESET, headers={"X-Demo-Token": DEMO_TOKEN})
    assert response.status_code == 200
    body = response.json()
    assert body["contract_id"] == DEMO_CONTRACT_ID
    assert body["reset_at"]

    ledger = client.get(f"{CONTRACT}/ledger").json()
    assert ledger["orders"] == []
    assert ledger["usage"]["NEW_ITEMS"]["before_value"] == "0"
    assert client.get(CONTRACT).json()["original_value"] == "4800000"


def test_reset_appends_an_event_and_deletes_no_history() -> None:
    """FR-13 beats FR-15: the log is append-only, so a reset is an event."""
    create_order()
    before = audit()
    assert before

    client.post(RESET, headers={"X-Demo-Token": DEMO_TOKEN})

    after = audit()
    assert len(after) == len(before) + 1
    # every earlier row survived, byte for byte
    assert after[: len(before)] == before
    assert after[-1]["action"] == "DEMO_RESET"
    assert after[-1]["actor_role"] == "SYSTEM"


def test_reset_is_404_when_no_token_is_configured() -> None:
    """Without DEMO_RESET_TOKEN the endpoint does not exist at all (NFR-08)."""
    settings = get_settings()
    original = settings.demo_reset_token
    object.__setattr__(settings, "demo_reset_token", "")
    try:
        assert client.post(RESET, headers={"X-Demo-Token": DEMO_TOKEN}).status_code == 404
    finally:
        object.__setattr__(settings, "demo_reset_token", original)
