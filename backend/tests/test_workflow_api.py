"""The eleven-stage workflow over HTTP.

Every test runs twice: once against the in-memory repository and once against
Postgres. The API must behave identically whichever store is behind it
(NFR-07, NFR-11).
"""

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.domain.enums import Party, Role
from app.main import app
from app.repositories.base import ContractRepository
from app.seed.demo_contract import GOVERNMENT_CONTRACT_ID, PRIVATE_CONTRACT_ID
from tests.conftest import DEMO_TOKEN

client = TestClient(app)
pytestmark = pytest.mark.usefixtures("backend")

PRIVATE = f"/api/contracts/{PRIVATE_CONTRACT_ID}"
GOV = f"/api/contracts/{GOVERNMENT_CONTRACT_ID}"
ENTITY = Party.GOVERNMENT_ENTITY.value
CONTRACTOR = Party.CONTRACTOR.value
PM = Role.PROJECT_MANAGER.value


def analyse(cr_id: str) -> dict[str, Any]:
    response = client.post(f"/api/change-requests/{cr_id}/analyse")
    assert response.status_code == 200, response.text
    return response.json()


def approve_whole_chain(cr_id: str) -> dict[str, Any]:
    client.post(f"/api/change-requests/{cr_id}/start-approval")
    body: dict[str, Any] = {}
    while True:
        current = client.get(f"/api/change-requests/{cr_id}").json()
        pending = [s for s in current["chain"] if s["decision"] == "PENDING"]
        if not pending:
            return current
        step = pending[0]
        response = client.post(
            f"/api/change-requests/{cr_id}/decide",
            json={
                "party": step["party"],
                "role": step["role"],
                "decided_by": f"{step['role']}-user",
                "decision": "APPROVED",
            },
        )
        assert response.status_code == 200, response.text
        body = response.json()
    return body


# ---------------------------------------------------------------------------
# Baseline (FR-01)
# ---------------------------------------------------------------------------


def test_both_seed_contracts_exist() -> None:
    contracts = client.get("/api/contracts").json()["contracts"]
    assert {c["id"] for c in contracts} == {PRIVATE_CONTRACT_ID, GOVERNMENT_CONTRACT_ID}


def test_contract_exposes_its_breakdown() -> None:
    body = client.get(PRIVATE).json()
    assert body["contract_type"] == "PRIVATE"
    assert len(body["breakdown"]) == 8
    line = next(x for x in body["breakdown"] if x["id"] == "ITM-05")
    assert line["unit_ar"] == "خادم"
    assert line["unit_rate"] == "45000"
    assert line["approved_product_ar"] == "خوادم من الفئة المؤسسية طراز A-2400"
    assert line["restrictions_ar"]


def test_seeded_change_requests_are_present() -> None:
    requests = client.get(f"{PRIVATE}/change-requests").json()["requests"]
    assert {r["id"] for r in requests} == {
        "CR-A-INSCOPE",
        "CR-B-PCR",
        "CR-C-SUBSTITUTION",
        "CR-D-POLICY",
        "CR-E-NCR",
    }
    assert all(r["state"] == "RECEIVED" for r in requests)


# ---------------------------------------------------------------------------
# Intake and analysis (FR-03 to FR-09)
# ---------------------------------------------------------------------------


def test_submitting_a_request_does_not_analyse_it() -> None:
    response = client.post(
        f"{PRIVATE}/change-requests",
        json={
            "requester_name": "م. تجريبي",
            "requester_party": CONTRACTOR,
            "body_ar": "نص طلب تجريبي غير مسجل.",
            "attachments": ["طلب تغيير رسمي"],
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["request"]["state"] == "RECEIVED"
    assert body["request"]["recommendation"] is None
    assert body["chain"] == []


def test_unknown_text_is_refused_rather_than_guessed() -> None:
    """The scripted provider stops instead of inventing an analysis (FR-19)."""
    cr_id = client.post(
        f"{PRIVATE}/change-requests",
        json={
            "requester_name": "م. تجريبي",
            "requester_party": CONTRACTOR,
            "body_ar": "طلب لا توجد له استجابة مسجلة على الإطلاق.",
            "attachments": ["طلب تغيير رسمي"],
        },
    ).json()["request"]["id"]
    response = client.post(f"/api/change-requests/{cr_id}/analyse")
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "NO_RECORDING"


def test_in_scope_request_closes_without_a_chain() -> None:
    body = analyse("CR-A-INSCOPE")
    assert body["request"]["state"] == "CLOSED_IN_SCOPE"
    assert body["request"]["recommendation"] == "CLOSE_IN_SCOPE"
    assert body["request"]["cost_impact"] == "0"
    assert body["chain"] == []
    assert body["recorded"] is True


def test_analysis_records_the_full_trace() -> None:
    analyse("CR-B-PCR")
    trace = client.get("/api/change-requests/CR-B-PCR/trace").json()
    assert len(trace["stages"]) == 7
    assert [s["stage_no"] for s in trace["stages"]] == [1, 2, 3, 4, 5, 6, 7]
    assert trace["total_duration_ms"] >= 0
    actors = {s["stage"]: s["actor_type"] for s in trace["stages"]}
    assert actors["COST_SCHEDULE_IMPACT"] == "CODE"
    assert actors["SCOPE_ANALYSIS"] == "AI"


def test_money_crosses_http_as_exact_strings() -> None:
    """NFR-01: a Decimal must not degrade to a float on the wire."""
    body = analyse("CR-D-POLICY")
    assert body["request"]["cost_impact"] == "1008000"
    assert isinstance(body["request"]["cost_impact"], str)


# ---------------------------------------------------------------------------
# Stage 8: the approval gate (FR-10)
# ---------------------------------------------------------------------------


def test_a_recommendation_does_not_approve_anything() -> None:
    """The control principle: the agent recommends, people approve."""
    body = analyse("CR-B-PCR")
    assert body["request"]["recommendation"] == "APPROVE"
    assert body["request"]["state"] == "RECOMMENDED"


def test_wrong_role_is_refused_by_the_backend() -> None:
    analyse("CR-D-POLICY")
    client.post("/api/change-requests/CR-D-POLICY/start-approval")
    # the CEO is last in the chain and may not jump the queue
    response = client.post(
        "/api/change-requests/CR-D-POLICY/decide",
        json={
            "party": ENTITY,
            "role": "CEO",
            "decided_by": "ceo",
            "decision": "APPROVED",
        },
    )
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "WRONG_ROLE"


def test_approvers_act_in_chain_order() -> None:
    analyse("CR-D-POLICY")
    final = approve_whole_chain("CR-D-POLICY")
    assert final["request"]["state"] == "APPROVED"
    order = [s["role"] for s in final["chain"]]
    assert order == ["PROJECT_MANAGER", "FINANCE_MANAGER", "CEO"]
    assert all(s["decision"] == "APPROVED" for s in final["chain"])


def test_rejection_needs_a_reason() -> None:
    analyse("CR-B-PCR")
    client.post("/api/change-requests/CR-B-PCR/start-approval")
    response = client.post(
        "/api/change-requests/CR-B-PCR/decide",
        json={"party": ENTITY, "role": PM, "decided_by": "pm", "decision": "REJECTED"},
    )
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "REASON_REQUIRED"


def test_rejection_notifies_the_requester() -> None:
    analyse("CR-B-PCR")
    client.post("/api/change-requests/CR-B-PCR/start-approval")
    body = client.post(
        "/api/change-requests/CR-B-PCR/decide",
        json={
            "party": ENTITY,
            "role": PM,
            "decided_by": "pm",
            "decision": "REJECTED",
            "reason": "الاعتماد المالي غير متاح",
        },
    ).json()
    assert body["request"]["state"] == "REJECTED"

    inbox = client.get("/api/notifications", params={"party": CONTRACTOR, "role": PM}).json()
    assert any(n["kind"] == "CR_REJECTED" for n in inbox["notifications"])


def test_revision_returns_the_request_for_reanalysis() -> None:
    analyse("CR-B-PCR")
    client.post("/api/change-requests/CR-B-PCR/start-approval")
    body = client.post(
        "/api/change-requests/CR-B-PCR/decide",
        json={
            "party": ENTITY,
            "role": PM,
            "decided_by": "pm",
            "decision": "REVISION_REQUESTED",
            "reason": "النطاق غير واضح",
        },
    ).json()
    assert body["request"]["state"] == "REVISION_REQUESTED"
    assert body["request"]["revision_count"] == 1
    # and it can be analysed again
    assert client.post("/api/change-requests/CR-B-PCR/analyse").status_code == 200


# ---------------------------------------------------------------------------
# Stages 9 to 11 (FR-12, FR-13, FR-14)
# ---------------------------------------------------------------------------


def test_a_vo_cannot_be_issued_before_full_approval() -> None:
    analyse("CR-B-PCR")
    response = client.post("/api/change-requests/CR-B-PCR/variation-order")
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "NOT_APPROVED"


def test_vo_is_issued_with_signatures_and_values() -> None:
    analyse("CR-C-SUBSTITUTION")
    approve_whole_chain("CR-C-SUBSTITUTION")
    body = client.post("/api/change-requests/CR-C-SUBSTITUTION/variation-order").json()
    vo = body["variation_order"]
    assert vo["number"] == "VO-001"
    assert vo["value"] == "132000"
    assert len(vo["signatures"]) == 2
    assert vo["scope_ar"]
    # vo_draft v2: the English wording comes from the same call.
    assert vo["scope_en"].startswith("This variation order covers: replacing")
    assert vo["recorded"] is True
    assert body["request"]["state"] == "VO_ISSUED"


def test_project_records_reflect_approved_changes() -> None:
    analyse("CR-D-POLICY")
    approve_whole_chain("CR-D-POLICY")
    records = client.get(f"{PRIVATE}/records").json()
    assert records["original_value"] == "4800000"
    assert records["approved_change_value"] == "1008000"
    assert records["revised_value"] == "5808000"
    assert records["original_duration_days"] == 364
    assert records["approved_extension_days"] == 45
    assert records["revised_duration_days"] == 409


def test_execution_records_actuals_and_closes_out() -> None:
    analyse("CR-B-PCR")
    approve_whole_chain("CR-B-PCR")
    vo_id = client.post("/api/change-requests/CR-B-PCR/variation-order").json()["variation_order"][
        "id"
    ]

    body = client.post(
        f"/api/variation-orders/{vo_id}/execution",
        json={"actual_cost": "140000", "acceptance_verified": True, "close_out": True},
    ).json()
    assert body["execution"]["cost_deviation"] == "5000"
    assert body["request"]["state"] == "CLOSED"


def test_close_out_requires_acceptance_verification() -> None:
    analyse("CR-B-PCR")
    approve_whole_chain("CR-B-PCR")
    vo_id = client.post("/api/change-requests/CR-B-PCR/variation-order").json()["variation_order"][
        "id"
    ]
    response = client.post(
        f"/api/variation-orders/{vo_id}/execution",
        json={"acceptance_verified": False, "close_out": True},
    )
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "ACCEPTANCE_REQUIRED"


# ---------------------------------------------------------------------------
# Article 67 on the government variant
# ---------------------------------------------------------------------------


def test_government_variant_is_blocked_and_recommends_rejection() -> None:
    body = analyse("CR-D-GOV")
    assert body["request"]["legally_blocked"] is True
    assert body["request"]["recommendation"] == "REJECT"
    assert "LEGAL_CAP_EXCEEDED" in body["reason_codes"]
    assert "CEO" not in [s["role"] for s in body["chain"]]
    assert "LEGAL_ADVISOR" in [s["role"] for s in body["chain"]]


# ---------------------------------------------------------------------------
# Notifications and reminders (FR-11)
# ---------------------------------------------------------------------------


def test_starting_approval_notifies_the_first_approver() -> None:
    analyse("CR-B-PCR")
    client.post("/api/change-requests/CR-B-PCR/start-approval")
    inbox = client.get("/api/notifications", params={"party": ENTITY, "role": PM}).json()
    assert any(n["kind"] == "APPROVAL_PENDING" for n in inbox["notifications"])


def test_no_reminder_before_the_configured_delay() -> None:
    analyse("CR-B-PCR")
    client.post("/api/change-requests/CR-B-PCR/start-approval")
    inbox = client.get("/api/notifications", params={"party": ENTITY, "role": PM}).json()
    assert inbox["reminder_count"] == 0


def test_reminder_appears_once_a_step_is_overdue(backend: ContractRepository) -> None:
    """Computed at read time, so no background job has to be running."""
    from app.services.change_requests import reminders_for

    analyse("CR-B-PCR")
    client.post("/api/change-requests/CR-B-PCR/start-approval")

    later = datetime.now(UTC) + timedelta(hours=25)
    reminders = reminders_for(backend, Party.GOVERNMENT_ENTITY, Role.PROJECT_MANAGER, later)
    assert len(reminders) == 1
    assert reminders[0].is_reminder is True
    assert reminders[0].cr_id == "CR-B-PCR"


def test_no_reminder_for_a_settled_request(backend: ContractRepository) -> None:
    from app.services.change_requests import reminders_for

    analyse("CR-B-PCR")
    approve_whole_chain("CR-B-PCR")
    later = datetime.now(UTC) + timedelta(hours=48)
    assert reminders_for(backend, Party.GOVERNMENT_ENTITY, Role.PROJECT_MANAGER, later) == []


# ---------------------------------------------------------------------------
# Audit and demo reset (FR-16, FR-19)
# ---------------------------------------------------------------------------


def test_every_state_change_is_audited() -> None:
    analyse("CR-B-PCR")
    approve_whole_chain("CR-B-PCR")
    client.post("/api/change-requests/CR-B-PCR/variation-order")
    events = client.get(f"{PRIVATE}/audit").json()["events"]
    actions = [e["action"] for e in events]
    assert "CR_ANALYSED" in actions
    assert "CR_APPROVED" in actions
    assert "VO_ISSUED" in actions
    for event in events:
        assert event["actor_role"]
        assert event["occurred_at"]


def test_demo_reset_restores_seed_and_keeps_audit() -> None:
    analyse("CR-B-PCR")
    before = len(client.get(f"{PRIVATE}/audit").json()["events"])
    assert before

    response = client.post("/api/demo/reset", headers={"X-Demo-Token": DEMO_TOKEN})
    assert response.status_code == 200

    requests = client.get(f"{PRIVATE}/change-requests").json()["requests"]
    assert all(r["state"] == "RECEIVED" for r in requests)
    after = client.get(f"{PRIVATE}/audit").json()["events"]
    assert len(after) == before + 1
    assert after[-1]["action"] == "DEMO_RESET"
