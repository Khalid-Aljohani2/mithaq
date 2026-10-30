"""The endpoints and behaviours the UI session asked for in Step 4D.

Everything here is reachable over HTTP, because that is the only surface the
frontend has. Where a number or a string is supposed to come from a
configuration file, the test asserts it against that file rather than against a
copy of the value - a test that repeats a hardcoded string would pass just as
happily when the string *is* hardcoded, which is the thing being prevented.
"""

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.domain.audit import AuditAction
from app.domain.enums import (
    ApprovalDecision,
    ChangeCategory,
    ChangeKind,
    ImpactType,
    NotificationKind,
    Party,
    Role,
)
from app.domain.money import money
from app.main import app
from app.pipeline.documents import CHECKLISTS
from app.policy.loader import get_policy
from app.regulations.loader import get_limits
from app.repositories.memory import InMemoryContractRepository
from app.routers import evaluation
from app.seed.demo_contract import GOVERNMENT_CONTRACT_ID, PRIVATE_CONTRACT_ID
from app.seed.demo_requests import TEXT_PCR_SMALL
from app.services import change_requests as svc

client = TestClient(app)

GOV = f"/api/contracts/{GOVERNMENT_CONTRACT_ID}"
PRIVATE = f"/api/contracts/{PRIVATE_CONTRACT_ID}"
CONTRACTOR = Party.CONTRACTOR.value
PM = Role.PROJECT_MANAGER.value


def approve_whole_chain(cr_id: str) -> dict[str, Any]:
    client.post(f"/api/change-requests/{cr_id}/start-approval")
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


# ---------------------------------------------------------------------------
# The schema the frontend generates its types from
# ---------------------------------------------------------------------------


def test_openapi_schema_is_served_and_describes_the_api() -> None:
    """A fetch of /openapi.json, which is what `npm run gen:api` does.

    The backend was never the problem here - the npm script was POSIX-only and
    never applied its default URL on Windows - but nothing asserted that this
    document is served and parses, so there was no way to tell the two apart.
    """
    response = client.get("/openapi.json")

    assert response.status_code == 200
    schema = response.json()
    assert schema["openapi"].startswith("3.")
    assert schema["info"]["title"] == get_settings().app_name
    # Every route the UI depends on is described, under the method it uses.
    assert "get" in schema["paths"]["/api/contracts/{contract_id}/ledger"]
    assert "post" in schema["paths"]["/api/change-requests/{cr_id}/attachments"]
    assert "get" in schema["paths"]["/api/policy/required-documents"]
    assert "get" in schema["paths"]["/api/eval/summary"]
    assert "get" in schema["paths"]["/api/variation-orders/{vo_id}"]


def test_every_response_model_is_named_in_the_schema() -> None:
    """A bare dict crossing the boundary would leave no component behind."""
    schemas = client.get("/openapi.json").json()["components"]["schemas"]
    assert {"LedgerResponse", "CapLine", "UsageSnapshot", "AttachmentsInput"} <= set(schemas)


# ---------------------------------------------------------------------------
# (2a) Policy caps on the ledger, with the source that says how to treat them
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("backend")
def test_ledger_reports_the_policy_caps_with_their_source() -> None:
    body = client.get(f"{GOV}/ledger").json()
    policy = get_policy()

    cost = body["policy_usage"]["cost_increase"]
    assert cost["source"] == "organization_policy"
    assert Decimal(cost["cap_pct"]) == policy.cost_increase_cap_pct
    assert Decimal(cost["cap_value"]) == Decimal("4800000") * policy.cost_increase_cap_pct / 100
    # Nothing is approved on a fresh ledger, so the whole cap is headroom.
    assert Decimal(cost["used_value"]) == 0
    assert Decimal(cost["headroom_value"]) == Decimal(cost["cap_value"])
    # A policy cap is not blocking: the named role can lift it (NFR-16).
    assert cost["blocking"] is False
    assert cost["exception_role"] == policy.policy_exception_role


@pytest.mark.usefixtures("backend")
def test_the_time_cap_is_measured_in_days_not_riyals() -> None:
    time = client.get(f"{GOV}/ledger").json()["policy_usage"]["time_extension"]
    assert time["unit"] == "days"
    # 20% of the 364-day baseline.
    assert Decimal(time["cap_value"]) == Decimal("72.8")


@pytest.mark.usefixtures("backend")
def test_a_private_contract_has_policy_caps_but_no_legal_ones() -> None:
    """Policy binds both parties; Article 67 binds government contracts only."""
    private = client.get(f"{PRIVATE}/ledger").json()
    government = client.get(f"{GOV}/ledger").json()

    assert private["legal_limits_apply"] is False
    assert government["legal_limits_apply"] is True
    assert set(private["policy_usage"]) == set(government["policy_usage"])


@pytest.mark.usefixtures("backend")
def test_an_approved_request_consumes_policy_headroom() -> None:
    """A figure that never moves is not a ledger."""
    before = client.get(f"{GOV}/ledger").json()["policy_usage"]["cost_increase"]
    client.post("/api/change-requests/CR-F-GOV-OK/analyse")
    approve_whole_chain("CR-F-GOV-OK")
    after = client.get(f"{GOV}/ledger").json()["policy_usage"]["cost_increase"]

    assert Decimal(after["used_value"]) == Decimal("540000")
    assert Decimal(after["headroom_value"]) == Decimal(before["headroom_value"]) - Decimal("540000")
    assert Decimal(after["used_pct"]) == Decimal("11.25")


@pytest.mark.usefixtures("backend")
def test_a_request_in_flight_is_pending_not_used() -> None:
    """Something under consideration must not silently eat headroom (FR-10)."""
    client.post("/api/change-requests/CR-F-GOV-OK/analyse")
    client.post("/api/change-requests/CR-F-GOV-OK/start-approval")

    cost = client.get(f"{GOV}/ledger").json()["policy_usage"]["cost_increase"]
    assert Decimal(cost["pending_value"]) == Decimal("540000")
    assert Decimal(cost["used_value"]) == 0
    assert Decimal(cost["headroom_value"]) == Decimal(cost["cap_value"])


# ---------------------------------------------------------------------------
# (2b) Article refs per usage line, read from the regulation file
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("backend")
def test_each_usage_line_cites_its_own_article_in_both_languages() -> None:
    usage = client.get(f"{GOV}/ledger").json()["usage"]
    limits = get_limits()

    for category, rule in limits.categories.items():
        line = usage[category.value]
        assert line["article_ref_en"] == rule.article_ref_en
        assert line["article_ref_ar"] == rule.article_ref_ar
        assert line["source"] == "law"

    combined = usage["COMBINED"]
    assert combined["article_ref_en"] == limits.combined.article_ref_en
    assert combined["article_ref_ar"] == limits.combined.article_ref_ar


@pytest.mark.usefixtures("backend")
def test_the_refs_are_distinct_per_line() -> None:
    """One ref repeated on every line would satisfy the check above vacuously."""
    usage = client.get(f"{GOV}/ledger").json()["usage"]
    refs = {line["article_ref_en"] for line in usage.values()}
    assert len(refs) == len(usage)


@pytest.mark.usefixtures("backend")
def test_the_arabic_refs_are_arabic() -> None:
    usage = client.get(f"{GOV}/ledger").json()["usage"]
    for line in usage.values():
        assert any("؀" <= ch <= "ۿ" for ch in line["article_ref_ar"])


# ---------------------------------------------------------------------------
# (2c) Supplying the documents a request was waiting for
# ---------------------------------------------------------------------------

INCOMPLETE = ["طلب تغيير رسمي"]
COMPLETE = ["طلب تغيير رسمي", "عرض سعر أو تحليل تكلفة"]


def submit_incomplete() -> str:
    """A request that stage 2 will send back for want of a cost quote."""
    cr_id: str = client.post(
        f"{PRIVATE}/change-requests",
        json={
            "requester_name": "م. فهد القحطاني",
            "requester_party": CONTRACTOR,
            "body_ar": TEXT_PCR_SMALL,
            "attachments": INCOMPLETE,
        },
    ).json()["request"]["id"]
    client.post(f"/api/change-requests/{cr_id}/analyse")
    return cr_id


@pytest.mark.usefixtures("backend")
def test_supplying_documents_replaces_what_is_on_file() -> None:
    cr_id = submit_incomplete()

    response = client.post(
        f"/api/change-requests/{cr_id}/attachments",
        json={
            "party": CONTRACTOR,
            "role": PM,
            "submitted_by": "م. فهد القحطاني",
            "attachments": COMPLETE,
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["request"]["attachments"] == COMPLETE
    # Supplying documents is not a claim that the file is complete: stage 2
    # still decides that, on the next run.
    assert body["request"]["state"] == "AWAITING_DOCUMENTS"


@pytest.mark.usefixtures("backend")
def test_the_analysis_can_then_run_again_and_get_further() -> None:
    cr_id = submit_incomplete()
    client.post(
        f"/api/change-requests/{cr_id}/attachments",
        json={
            "party": CONTRACTOR,
            "role": PM,
            "submitted_by": "م. فهد القحطاني",
            "attachments": COMPLETE,
        },
    )

    body = client.post(f"/api/change-requests/{cr_id}/analyse").json()

    assert body["request"]["state"] == "RECOMMENDED"
    assert "DOCUMENTS_MISSING" not in body["reason_codes"]


@pytest.mark.usefixtures("backend")
def test_the_other_party_may_not_file_documents_for_this_one() -> None:
    """Refused by the backend, not merely hidden by the UI (FR-10)."""
    cr_id = submit_incomplete()

    response = client.post(
        f"/api/change-requests/{cr_id}/attachments",
        json={
            "party": Party.GOVERNMENT_ENTITY.value,
            "role": PM,
            "submitted_by": "موظف الجهة",
            "attachments": COMPLETE,
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "WRONG_PARTY"


@pytest.mark.usefixtures("backend")
def test_the_wrong_role_may_not_file_documents() -> None:
    cr_id = submit_incomplete()

    response = client.post(
        f"/api/change-requests/{cr_id}/attachments",
        json={
            "party": CONTRACTOR,
            "role": Role.CEO.value,
            "submitted_by": "الرئيس التنفيذي",
            "attachments": COMPLETE,
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "WRONG_ROLE"


@pytest.mark.usefixtures("backend")
def test_documents_cannot_be_filed_against_a_request_that_is_not_waiting() -> None:
    response = client.post(
        "/api/change-requests/CR-B-PCR/attachments",
        json={
            "party": CONTRACTOR,
            "role": PM,
            "submitted_by": "م. فهد القحطاني",
            "attachments": COMPLETE,
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "NOT_AWAITING_DOCUMENTS"


@pytest.mark.usefixtures("backend")
def test_filing_documents_is_audited_with_the_person_who_filed_them() -> None:
    cr_id = submit_incomplete()
    client.post(
        f"/api/change-requests/{cr_id}/attachments",
        json={
            "party": CONTRACTOR,
            "role": PM,
            "submitted_by": "م. فهد القحطاني",
            "attachments": COMPLETE,
        },
    )

    events = client.get(f"{PRIVATE}/audit").json()["events"]
    supplied = [e for e in events if e["action"] == AuditAction.CR_DOCUMENTS_SUPPLIED.value]
    assert len(supplied) == 1
    assert supplied[0]["entity_id"] == cr_id
    assert supplied[0]["actor_party"] == CONTRACTOR
    assert supplied[0]["actor_name"] == "م. فهد القحطاني"


# ---------------------------------------------------------------------------
# (2d) The checklist, before a requester runs into it
# ---------------------------------------------------------------------------


def test_required_documents_is_the_same_table_stage_2_uses() -> None:
    body = client.get("/api/policy/required-documents").json()
    served = {c["impact_type"]: c["required"] for c in body["checklists"]}

    assert served == {impact.value: list(docs) for impact, docs in CHECKLISTS.items()}


def test_a_cost_bearing_request_needs_more_than_a_form() -> None:
    """The one the UI shows most: COST is the common case."""
    body = client.get("/api/policy/required-documents").json()
    cost = next(c for c in body["checklists"] if c["impact_type"] == ImpactType.COST.value)
    assert len(cost["required"]) == 2


def test_thresholds_carry_the_source_that_justifies_them() -> None:
    thresholds = {t["key"]: t for t in client.get("/api/policy/thresholds").json()}
    policy = get_policy()

    assert set(thresholds) == set(policy.thresholds)
    assert thresholds["cost_increase"]["source"] == "organization_policy"
    assert thresholds["minimum_confidence"]["source"] == "default"
    assert Decimal(thresholds["cost_increase"]["cap_pct"]) == policy.cost_increase_cap_pct


# ---------------------------------------------------------------------------
# (2e) The published evaluation result
# ---------------------------------------------------------------------------


def test_eval_summary_says_so_when_nothing_has_been_published(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A missing file is "not measured", never a zero that reads as a score."""
    monkeypatch.setattr(evaluation, "SUMMARY_PATH", tmp_path / "absent.json")
    evaluation.reset_summary_cache()

    body = client.get("/api/eval/summary").json()

    assert body["available"] is False
    assert body["overall_accuracy_pct"] is None
    assert body["notes"]
    evaluation.reset_summary_cache()


def test_eval_summary_serves_the_published_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    published = tmp_path / "summary.json"
    published.write_text(
        json.dumps(
            {
                "generated_at": "2026-10-30T12:00:00Z",
                "commit": "abc1234",
                "model": "claude-opus-5-5",
                "split": "test",
                "case_count": 25,
                "prompt_versions": {"INTAKE": "v3"},
                "overall_accuracy_pct": "92.0",
                "audited_accuracy_pct": "96.0",
                "audited_case_ids": ["TEST-18"],
                "fields": [
                    {
                        "field": "recommendation",
                        "accuracy_pct": "92.0",
                        "audited_accuracy_pct": "96.0",
                    }
                ],
                "stage_latency": [
                    {"stage": "INTAKE", "median_ms": "1200.0", "p95_ms": "2400.0", "cases": 25}
                ],
                "latency_p50_ms": 4100,
                "latency_p95_ms": 9800,
                "total_cost_usd": "1.2345",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(evaluation, "SUMMARY_PATH", published)
    evaluation.reset_summary_cache()

    body = client.get("/api/eval/summary").json()

    assert body["available"] is True
    assert body["model"] == "claude-opus-5-5"
    assert body["case_count"] == 25
    assert Decimal(body["overall_accuracy_pct"]) == Decimal("92.0")
    # Both label sets are published side by side, never one instead of the other.
    assert Decimal(body["audited_accuracy_pct"]) == Decimal("96.0")
    assert body["audited_case_ids"] == ["TEST-18"]
    assert body["fields"][0]["field"] == "recommendation"
    assert body["stage_latency"][0]["stage"] == "INTAKE"
    # Traceability: a published number names the commit it was produced at.
    assert body["commit"] == "abc1234"
    evaluation.reset_summary_cache()


def test_the_real_summary_file_parses_if_it_exists() -> None:
    """Guards the committed artefact itself against drifting from its schema."""
    if not evaluation.SUMMARY_PATH.is_file():
        pytest.skip("no evaluation run has been published yet")
    evaluation.reset_summary_cache()
    body = client.get("/api/eval/summary").json()
    assert body["available"] is True
    assert body["commit"]
    assert body["model"]


# ---------------------------------------------------------------------------
# (b) One variation order, and the link from a request to it
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("backend")
def test_a_request_with_no_variation_order_says_none() -> None:
    body = client.get("/api/change-requests/CR-B-PCR").json()
    assert body["variation_order_id"] is None


@pytest.mark.usefixtures("backend")
def test_a_request_links_to_the_variation_order_it_produced() -> None:
    client.post("/api/change-requests/CR-B-PCR/analyse")
    approve_whole_chain("CR-B-PCR")
    issued = client.post("/api/change-requests/CR-B-PCR/variation-order").json()

    body = client.get("/api/change-requests/CR-B-PCR").json()

    assert body["variation_order_id"] == issued["variation_order"]["id"]


@pytest.mark.usefixtures("backend")
def test_one_variation_order_can_be_fetched_by_id() -> None:
    client.post("/api/change-requests/CR-B-PCR/analyse")
    approve_whole_chain("CR-B-PCR")
    vo_id = client.post("/api/change-requests/CR-B-PCR/variation-order").json()["variation_order"][
        "id"
    ]

    response = client.get(f"/api/variation-orders/{vo_id}")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["variation_order"]["id"] == vo_id
    # The request comes with it, so the UI needs one call, not two.
    assert body["request"]["id"] == "CR-B-PCR"


@pytest.mark.usefixtures("backend")
def test_an_unknown_variation_order_is_a_404_with_a_code() -> None:
    response = client.get("/api/variation-orders/VO-DOES-NOT-EXIST")
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "VO_NOT_FOUND"


# ---------------------------------------------------------------------------
# (c) Audit entries name the party and the person
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("backend")
def test_submission_records_who_submitted_it() -> None:
    cr_id = client.post(
        f"{PRIVATE}/change-requests",
        json={
            "requester_name": "م. نورة الدوسري",
            "requester_party": CONTRACTOR,
            "body_ar": TEXT_PCR_SMALL,
            "attachments": COMPLETE,
        },
    ).json()["request"]["id"]

    events = client.get(f"{PRIVATE}/audit").json()["events"]
    received = next(e for e in events if e["entity_id"] == cr_id and e["action"] == "CR_RECEIVED")
    assert received["actor_party"] == CONTRACTOR
    assert received["actor_name"] == "م. نورة الدوسري"
    assert received["actor_role"] == PM


@pytest.mark.usefixtures("backend")
def test_each_approval_records_the_party_and_the_approver() -> None:
    """On a shared ledger, a role alone does not say which side acted."""
    client.post("/api/change-requests/CR-B-PCR/analyse")
    approve_whole_chain("CR-B-PCR")

    events = client.get(f"{PRIVATE}/audit").json()["events"]
    steps = [
        e
        for e in events
        if e["entity_id"] == "CR-B-PCR" and e["action"] in {"CR_STEP_APPROVED", "CR_APPROVED"}
    ]
    assert steps
    for event in steps:
        assert event["actor_party"] in {p.value for p in Party}
        assert event["actor_name"] == f"{event['actor_role']}-user"


@pytest.mark.usefixtures("backend")
def test_the_agents_own_moves_name_no_party() -> None:
    """Nobody signed for them, and inventing a name would be worse than None."""
    client.post("/api/change-requests/CR-B-PCR/analyse")

    events = client.get(f"{PRIVATE}/audit").json()["events"]
    analysed = next(e for e in events if e["action"] == "CR_ANALYSED")
    assert analysed["actor_role"] == "CODE"
    assert analysed["actor_party"] is None
    assert analysed["actor_name"] is None


# ---------------------------------------------------------------------------
# (d) A finished chain is not a pending one, and money reads like money
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("backend")
def test_a_fully_approved_chain_notifies_completion_not_a_pending_approval() -> None:
    client.post("/api/change-requests/CR-B-PCR/analyse")
    approve_whole_chain("CR-B-PCR")

    notifications = client.get(f"/api/notifications?party={CONTRACTOR}&role={PM}").json()[
        "notifications"
    ]
    kinds = [n["kind"] for n in notifications if n["cr_id"] == "CR-B-PCR"]

    assert NotificationKind.APPROVAL_COMPLETED.value in kinds


@pytest.mark.usefixtures("backend")
def test_a_variation_order_notification_groups_the_thousands() -> None:
    client.post("/api/change-requests/CR-F-GOV-OK/analyse")
    approve_whole_chain("CR-F-GOV-OK")
    client.post("/api/change-requests/CR-F-GOV-OK/variation-order")

    notifications = client.get(f"/api/notifications?party={CONTRACTOR}&role={PM}").json()[
        "notifications"
    ]
    issued = next(n for n in notifications if n["kind"] == NotificationKind.VO_ISSUED.value)

    assert "540,000" in issued["message_en"]
    assert "540,000" in issued["message_ar"]
    assert "540000" not in issued["message_en"]


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("1008000", "1,008,000"),
        ("540000", "540,000"),
        ("999", "999"),
        ("0", "0"),
        ("1234.50", "1,234.50"),
        ("-96000.555", "-96,000.56"),
    ],
)
def test_money_formatting(value: str, expected: str) -> None:
    assert money(Decimal(value)) == expected


# ---------------------------------------------------------------------------
# (e) The reminder delay a demo can turn down
# ---------------------------------------------------------------------------


def test_the_reminder_delay_defaults_to_the_policy_file() -> None:
    get_settings.cache_clear()
    try:
        assert svc.pending_approval_hours() == get_policy().pending_approval_hours
    finally:
        get_settings.cache_clear()


def test_a_setting_overrides_the_policy_delay(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REMINDER_PENDING_APPROVAL_HOURS", "0")
    get_settings.cache_clear()
    try:
        assert svc.pending_approval_hours() == 0
    finally:
        get_settings.cache_clear()


def test_zero_hours_makes_a_pending_approval_remind_immediately(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The demo case. With the default delay the same step is silent."""
    from app.analysis.scripted import ScriptedProvider

    repo = InMemoryContractRepository()
    now = datetime(2027, 3, 1, 9, 0, tzinfo=UTC)
    svc.analyse_request(repo, "CR-B-PCR", ScriptedProvider(), now)
    svc.start_approval(repo, "CR-B-PCR", now)
    step = svc.current_step(tuple(repo.list_approval_steps("CR-B-PCR")))
    assert step is not None

    get_settings.cache_clear()
    try:
        # A minute after the step was created - the step's own clock, not wall
        # time, since the pipeline stamps it.
        soon = step.created_at + timedelta(minutes=1)
        # Default delay: nothing yet.
        assert svc.reminders_for(repo, step.party, step.role, soon) == []

        monkeypatch.setenv("REMINDER_PENDING_APPROVAL_HOURS", "0")
        get_settings.cache_clear()
        reminders = svc.reminders_for(repo, step.party, step.role, soon)
    finally:
        get_settings.cache_clear()

    assert [r.kind for r in reminders] == [NotificationKind.APPROVAL_REMINDER]
    assert reminders[0].is_reminder is True


# ---------------------------------------------------------------------------
# (f) A government request that can actually reach a variation order
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("backend")
def test_the_new_government_request_is_seeded_on_the_government_contract() -> None:
    requests = client.get(f"{GOV}/change-requests").json()["requests"]
    assert {r["id"] for r in requests} == {"CR-D-GOV", "CR-F-GOV-OK"}


@pytest.mark.usefixtures("backend")
def test_it_is_recommended_for_approval_inside_every_cap() -> None:
    body = client.post("/api/change-requests/CR-F-GOV-OK/analyse").json()

    assert body["request"]["recommendation"] == "APPROVE"
    assert body["request"]["legally_blocked"] is False
    assert body["request"]["policy_exception_required"] is False
    assert body["request"]["kind"] == ChangeKind.PCR.value
    # 540,000 of 4,800,000 is 11.25%, inside the 20% increase and combined caps.
    assert Decimal(body["request"]["cost_impact"]) == Decimal("540000")


@pytest.mark.usefixtures("backend")
def test_its_analysis_came_from_a_recording_like_the_others() -> None:
    body = client.post("/api/change-requests/CR-F-GOV-OK/analyse").json()
    assert body["recorded"] is True


@pytest.mark.usefixtures("backend")
def test_it_produces_a_variation_order_citing_article_67() -> None:
    """The point of seeding it: the demo had no government VO to show."""
    client.post("/api/change-requests/CR-F-GOV-OK/analyse")
    approve_whole_chain("CR-F-GOV-OK")

    vo = client.post("/api/change-requests/CR-F-GOV-OK/variation-order").json()["variation_order"]

    limits = get_limits()
    increase = limits.categories[ChangeCategory.INCREASE_EXISTING]
    assert vo["cited_articles"] == [increase.article_ref_en, limits.combined.article_ref_en]
    assert vo["cited_line_ids"] == ["ITM-05"]
    assert Decimal(vo["value"]) == Decimal("540000")


@pytest.mark.usefixtures("backend")
def test_a_private_contracts_variation_order_cites_no_article() -> None:
    """Article 67 governs government contracts; citing it anyway would be false."""
    client.post("/api/change-requests/CR-B-PCR/analyse")
    approve_whole_chain("CR-B-PCR")

    vo = client.post("/api/change-requests/CR-B-PCR/variation-order").json()["variation_order"]

    assert vo["cited_articles"] == []


@pytest.mark.usefixtures("backend")
def test_the_blocked_government_request_still_cannot_be_approved() -> None:
    """The new one must not have loosened anything for the old one."""
    body = client.post("/api/change-requests/CR-D-GOV/analyse").json()
    assert body["request"]["recommendation"] == "REJECT"
    assert body["request"]["legally_blocked"] is True


@pytest.mark.usefixtures("backend")
def test_approving_it_consumes_real_policy_headroom() -> None:
    """The new request consumes real headroom, not notional headroom.

    Asserted against the policy layer. The Article 67 layer is not checked
    here because it does not accumulate approved change requests at all:
    ``commit_ledger_entries`` has never been called by anything, so
    ``usage`` stays at zero whatever is approved. That is a separate defect,
    reported rather than quietly patched inside a test.
    """
    client.post("/api/change-requests/CR-F-GOV-OK/analyse")
    approve_whole_chain("CR-F-GOV-OK")

    cost = client.get(f"{GOV}/ledger").json()["policy_usage"]["cost_increase"]
    assert Decimal(cost["used_value"]) == Decimal("540000")
    assert Decimal(cost["headroom_value"]) == Decimal("960000") - Decimal("540000")


@pytest.mark.usefixtures("backend")
def test_rejecting_a_step_still_works_on_the_new_request() -> None:
    """An approvable request is only useful if it can also be refused."""
    client.post("/api/change-requests/CR-F-GOV-OK/analyse")
    client.post("/api/change-requests/CR-F-GOV-OK/start-approval")
    step = client.get("/api/change-requests/CR-F-GOV-OK").json()["chain"][0]

    response = client.post(
        "/api/change-requests/CR-F-GOV-OK/decide",
        json={
            "party": step["party"],
            "role": step["role"],
            "decided_by": "مراجع",
            "decision": ApprovalDecision.REJECTED.value,
            "reason": "التمويل غير متاح هذا العام.",
        },
    )

    assert response.status_code == 200, response.text
    assert response.json()["request"]["state"] == "REJECTED"


# ---------------------------------------------------------------------------
# The default model (docs/decisions/0002-default-model.md)
# ---------------------------------------------------------------------------


def test_the_default_model_is_the_one_the_decision_record_chose() -> None:
    from app.config import DEFAULT_MODEL

    assert DEFAULT_MODEL == "claude-opus-5-5"


def test_an_unset_model_falls_back_to_the_default_not_to_empty() -> None:
    """A blank line in an env file must not silently unset the model."""
    from app.config import DEFAULT_MODEL, Settings

    assert Settings(llm_model="").default_model == DEFAULT_MODEL
    assert Settings(llm_model="   ").default_model == DEFAULT_MODEL


def test_every_stage_runs_on_the_default_with_no_overrides_configured() -> None:
    from app.config import DEFAULT_MODEL, Settings
    from app.domain.enums import Stage

    # llm_model is passed explicitly: a developer's .env may pin a model, and
    # that correctly wins over the code default. This asserts the default, not
    # whatever happens to be in the environment running the suite.
    settings = Settings(llm_model="", llm_model_overrides="")
    for stage in Stage:
        assert settings.model_for(stage.value) == DEFAULT_MODEL


def test_a_per_stage_override_still_wins() -> None:
    """The choice is configuration, not a constant welded to a call site."""
    from app.config import DEFAULT_MODEL, Settings

    settings = Settings(llm_model="", llm_model_overrides="INTAKE=claude-haiku-5-5")
    assert settings.model_for("INTAKE") == "claude-haiku-5-5"
    assert settings.model_for("SCOPE_ANALYSIS") == DEFAULT_MODEL


def test_minimum_confidence_was_not_tuned() -> None:
    """Step 4D kept it at 0.70, and in particular did not tune it on the test split."""
    assert get_policy().minimum_confidence == Decimal("0.70")
