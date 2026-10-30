"""The three fixes the UI merge asked for.

Each one is a thing a judge would notice in thirty seconds of using the
product: a queue that never empties, a reminder that says "0 hours ago", and a
method section that states one split size when the discipline rests on two.
"""

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.analysis.scripted import ScriptedProvider
from app.config import get_settings
from app.dependencies import get_repository
from app.domain.durations import waited_phrase
from app.domain.enums import ApprovalDecision, NotificationKind, Party, Role
from app.main import app
from app.repositories.memory import InMemoryContractRepository
from app.routers import evaluation
from app.seed.demo_contract import PRIVATE_CONTRACT_ID
from app.seed.demo_requests import TEXT_PCR_SMALL
from app.services import change_requests as svc
from eval.run import CASES_PATH, load_cases
from scripts.publish_eval_summary import split_size

client = TestClient(app)
NOW = datetime(2027, 3, 1, 9, 0, tzinfo=UTC)
PM = Role.PROJECT_MANAGER


# ---------------------------------------------------------------------------
# (a) A decided step's "approval required" leaves the inbox
# ---------------------------------------------------------------------------


def kinds_for(repo: InMemoryContractRepository, party: Party, role: Role, cr_id: str) -> list[str]:
    return [n.kind.value for n in svc.notifications_for(repo, party, role, NOW) if n.cr_id == cr_id]


def test_an_approver_sees_the_ask_while_their_step_is_pending() -> None:
    repo = InMemoryContractRepository()
    svc.analyse_request(repo, "CR-B-PCR", ScriptedProvider(), NOW)
    svc.start_approval(repo, "CR-B-PCR", NOW)
    step = svc.current_step(tuple(repo.list_approval_steps("CR-B-PCR")))
    assert step is not None

    assert NotificationKind.APPROVAL_PENDING.value in kinds_for(
        repo, step.party, step.role, "CR-B-PCR"
    )


def test_deciding_the_step_takes_the_ask_out_of_that_inbox() -> None:
    """An inbox is a worklist. A request you have already approved is not work."""
    repo = InMemoryContractRepository()
    svc.analyse_request(repo, "CR-B-PCR", ScriptedProvider(), NOW)
    svc.start_approval(repo, "CR-B-PCR", NOW)
    step = svc.current_step(tuple(repo.list_approval_steps("CR-B-PCR")))
    assert step is not None

    svc.decide_step(
        repo, "CR-B-PCR", step.party, step.role, "u", ApprovalDecision.APPROVED, None, NOW
    )

    assert NotificationKind.APPROVAL_PENDING.value not in kinds_for(
        repo, step.party, step.role, "CR-B-PCR"
    )


def test_the_next_approver_still_has_theirs() -> None:
    """Clearing one queue must not clear the chain.

    The government request, because it has a four-step chain; CR-B-PCR has
    one step and so has no "next approver" to check.
    """
    repo = InMemoryContractRepository()
    svc.analyse_request(repo, "CR-F-GOV-OK", ScriptedProvider(), NOW)
    svc.start_approval(repo, "CR-F-GOV-OK", NOW)
    first = svc.current_step(tuple(repo.list_approval_steps("CR-F-GOV-OK")))
    assert first is not None
    svc.decide_step(
        repo, "CR-F-GOV-OK", first.party, first.role, "u", ApprovalDecision.APPROVED, None, NOW
    )
    second = svc.current_step(tuple(repo.list_approval_steps("CR-F-GOV-OK")))
    assert second is not None
    assert (second.party, second.role) != (first.party, first.role)

    assert NotificationKind.APPROVAL_PENDING.value not in kinds_for(
        repo, first.party, first.role, "CR-F-GOV-OK"
    )
    assert NotificationKind.APPROVAL_PENDING.value in kinds_for(
        repo, second.party, second.role, "CR-F-GOV-OK"
    )


def test_a_finished_chain_leaves_nobody_with_an_outstanding_ask() -> None:
    repo = InMemoryContractRepository()
    svc.analyse_request(repo, "CR-B-PCR", ScriptedProvider(), NOW)
    svc.start_approval(repo, "CR-B-PCR", NOW)
    while True:
        step = svc.current_step(tuple(repo.list_approval_steps("CR-B-PCR")))
        if step is None:
            break
        svc.decide_step(
            repo, "CR-B-PCR", step.party, step.role, "u", ApprovalDecision.APPROVED, None, NOW
        )

    for party in Party:
        for role in Role:
            assert NotificationKind.APPROVAL_PENDING.value not in kinds_for(
                repo, party, role, "CR-B-PCR"
            )


def test_the_outcome_notice_stays() -> None:
    """Only the *ask* is cleared. What happened is still worth telling."""
    repo = InMemoryContractRepository()
    svc.analyse_request(repo, "CR-B-PCR", ScriptedProvider(), NOW)
    svc.start_approval(repo, "CR-B-PCR", NOW)
    while True:
        step = svc.current_step(tuple(repo.list_approval_steps("CR-B-PCR")))
        if step is None:
            break
        svc.decide_step(
            repo, "CR-B-PCR", step.party, step.role, "u", ApprovalDecision.APPROVED, None, NOW
        )

    requester = kinds_for(repo, Party.CONTRACTOR, PM, "CR-B-PCR")
    assert NotificationKind.APPROVAL_COMPLETED.value in requester


def test_supplying_documents_clears_the_documents_ask() -> None:
    """The same rule, applied to the other kind of ask."""
    repo = InMemoryContractRepository()
    request = svc.submit_request(
        repo,
        PRIVATE_CONTRACT_ID,
        svc.RequestInput(
            requester_name="م. فهد القحطاني",
            requester_party=Party.CONTRACTOR,
            body_ar=TEXT_PCR_SMALL,
            attachments=("طلب تغيير رسمي",),
        ),
        NOW,
    )
    svc.analyse_request(repo, request.id, ScriptedProvider(), NOW)
    assert NotificationKind.DOCUMENTS_REQUIRED.value in kinds_for(
        repo, Party.CONTRACTOR, PM, request.id
    )

    svc.replace_attachments(
        repo,
        request.id,
        Party.CONTRACTOR,
        PM,
        "م. فهد القحطاني",
        ("طلب تغيير رسمي", "عرض سعر أو تحليل تكلفة"),
        NOW,
    )
    svc.analyse_request(repo, request.id, ScriptedProvider(), NOW)

    assert NotificationKind.DOCUMENTS_REQUIRED.value not in kinds_for(
        repo, Party.CONTRACTOR, PM, request.id
    )


@pytest.mark.usefixtures("backend")
def test_the_endpoint_count_drops_when_a_step_is_decided() -> None:
    """Over HTTP: the badge the UI renders is the length of this list."""
    client.post("/api/change-requests/CR-B-PCR/analyse")
    client.post("/api/change-requests/CR-B-PCR/start-approval")
    step = client.get("/api/change-requests/CR-B-PCR").json()["chain"][0]
    inbox = f"/api/notifications?party={step['party']}&role={step['role']}"
    before = len(client.get(inbox).json()["notifications"])

    decided = client.post(
        "/api/change-requests/CR-B-PCR/decide",
        json={
            "party": step["party"],
            "role": step["role"],
            "decided_by": "u",
            "decision": "APPROVED",
        },
    )
    assert decided.status_code == 200, decided.text

    after = client.get(inbox).json()["notifications"]
    assert len(after) < before
    assert all(n["kind"] != "APPROVAL_PENDING" for n in after)


# ---------------------------------------------------------------------------
# (b) A reminder with the delay set to zero
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("hours", "arabic", "english"),
    [
        (0, "أقل من ساعة", "less than an hour"),
        (1, "ساعة", "1 hour"),
        (2, "ساعتين", "2 hours"),
        (3, "3 ساعات", "3 hours"),
        (10, "10 ساعات", "10 hours"),
        (11, "11 ساعة", "11 hours"),
        (49, "49 ساعة", "49 hours"),
    ],
)
def test_the_waited_phrase_counts_in_arabic(hours: int, arabic: str, english: str) -> None:
    """Singular, dual, few and many. Arabic is not English with other words."""
    assert waited_phrase(hours) == (arabic, english)


def test_a_negative_wait_still_reads_sensibly() -> None:
    """Clock skew should not produce "-1 hours"."""
    assert waited_phrase(-3) == ("أقل من ساعة", "less than an hour")


def test_an_approval_reminder_at_zero_delay_says_less_than_an_hour(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = InMemoryContractRepository()
    svc.analyse_request(repo, "CR-B-PCR", ScriptedProvider(), NOW)
    svc.start_approval(repo, "CR-B-PCR", NOW)
    step = svc.current_step(tuple(repo.list_approval_steps("CR-B-PCR")))
    assert step is not None

    monkeypatch.setenv("REMINDER_PENDING_APPROVAL_HOURS", "0")
    get_settings.cache_clear()
    try:
        reminders = svc.reminders_for(
            repo, step.party, step.role, step.created_at + timedelta(minutes=5)
        )
    finally:
        get_settings.cache_clear()

    assert len(reminders) == 1
    assert "less than an hour" in reminders[0].message_en
    assert "أقل من ساعة" in reminders[0].message_ar
    assert "0 hours" not in reminders[0].message_en
    assert "0 ساعة" not in reminders[0].message_ar


def test_a_documents_reminder_at_zero_delay_says_less_than_an_hour(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = InMemoryContractRepository()
    request = svc.submit_request(
        repo,
        PRIVATE_CONTRACT_ID,
        svc.RequestInput(
            requester_name="م. فهد القحطاني",
            requester_party=Party.CONTRACTOR,
            body_ar=TEXT_PCR_SMALL,
            attachments=("طلب تغيير رسمي",),
        ),
        NOW,
    )
    svc.analyse_request(repo, request.id, ScriptedProvider(), NOW)

    monkeypatch.setenv("REMINDER_AWAITING_DOCUMENTS_HOURS", "0")
    get_settings.cache_clear()
    try:
        reminders = svc.document_reminders_for(
            repo, Party.CONTRACTOR, PM, NOW + timedelta(minutes=5)
        )
    finally:
        get_settings.cache_clear()

    assert len(reminders) == 1
    assert "less than an hour" in reminders[0].message_en
    assert "أقل من ساعة" in reminders[0].message_ar
    assert "0 hours" not in reminders[0].message_en


def test_a_longer_wait_still_names_the_hours(monkeypatch: pytest.MonkeyPatch) -> None:
    """The zero case must not have flattened every other one."""
    repo = InMemoryContractRepository()
    svc.analyse_request(repo, "CR-B-PCR", ScriptedProvider(), NOW)
    svc.start_approval(repo, "CR-B-PCR", NOW)
    step = svc.current_step(tuple(repo.list_approval_steps("CR-B-PCR")))
    assert step is not None

    monkeypatch.setenv("REMINDER_PENDING_APPROVAL_HOURS", "0")
    get_settings.cache_clear()
    try:
        reminders = svc.reminders_for(
            repo, step.party, step.role, step.created_at + timedelta(hours=30)
        )
    finally:
        get_settings.cache_clear()

    assert "30 hours" in reminders[0].message_en
    assert "30 ساعة" in reminders[0].message_ar


# ---------------------------------------------------------------------------
# (c) The dev split size, from the case file
# ---------------------------------------------------------------------------


def test_the_split_sizes_are_counted_from_the_case_file() -> None:
    assert split_size("dev") == 15
    assert split_size("test") == 25
    assert split_size("dev") + split_size("test") == len(load_cases(None))


def test_the_published_summary_names_the_dev_split_size() -> None:
    """The split discipline rests on two numbers; publishing one is half a claim."""
    if not evaluation.SUMMARY_PATH.is_file():
        pytest.skip("no evaluation run has been published yet")

    published = json.loads(evaluation.SUMMARY_PATH.read_text(encoding="utf-8"))
    assert published["dev_case_count"] == split_size("dev")
    assert published["case_count"] == split_size("test")


def test_the_endpoint_serves_it() -> None:
    if not evaluation.SUMMARY_PATH.is_file():
        pytest.skip("no evaluation run has been published yet")
    evaluation.reset_summary_cache()

    body = client.get("/api/eval/summary").json()

    assert body["dev_case_count"] == 15
    assert body["case_count"] == 25
    evaluation.reset_summary_cache()


def test_publishing_the_dev_count_changed_no_measured_number() -> None:
    """It is read from the case file, so no evaluation was re-run for it.

    Guards the thing that would be tempting and wrong: re-running the dev split
    to find out how big it is, and quietly republishing different numbers.
    """
    if not evaluation.SUMMARY_PATH.is_file():
        pytest.skip("no evaluation run has been published yet")

    published = json.loads(evaluation.SUMMARY_PATH.read_text(encoding="utf-8"))
    # The published run is still the TEST split at the commit it was run from.
    assert published["split"] == "test"
    assert published["commit"]
    assert Decimal(published["overall_accuracy_pct"]) == Decimal("92.0")
    assert published["errors"] == 0


def test_the_case_file_is_the_only_source_for_the_count(tmp_path: pytest.TempPathFactory) -> None:
    """Pointed at a different file, it counts that file - no hidden constant."""
    smaller = CASES_PATH.parent / "cases.jsonl"
    assert smaller == CASES_PATH
    lines = CASES_PATH.read_text(encoding="utf-8").splitlines()
    trimmed = [ln for ln in lines if ln.strip() and json.loads(ln)["split"] == "dev"][:3]
    scratch = evaluation.SUMMARY_PATH.parent.parent / "cases-scratch.jsonl"
    try:
        scratch.write_text("\n".join(trimmed) + "\n", encoding="utf-8")
        assert split_size("dev", scratch) == 3
        assert split_size("test", scratch) == 0
    finally:
        scratch.unlink(missing_ok=True)


def test_the_endpoint_serves_document_reminders_too(monkeypatch: pytest.MonkeyPatch) -> None:
    """The route used to assemble the inbox itself, so the document reminders
    added with the feature never reached the API. One inbox, built once."""
    repo = InMemoryContractRepository()
    request = svc.submit_request(
        repo,
        PRIVATE_CONTRACT_ID,
        svc.RequestInput(
            requester_name="م. فهد القحطاني",
            requester_party=Party.CONTRACTOR,
            body_ar=TEXT_PCR_SMALL,
            attachments=("طلب تغيير رسمي",),
        ),
        datetime.now(UTC),
    )
    svc.analyse_request(repo, request.id, ScriptedProvider(), datetime.now(UTC))

    app.dependency_overrides[get_repository] = lambda: repo
    monkeypatch.setenv("REMINDER_AWAITING_DOCUMENTS_HOURS", "0")
    get_settings.cache_clear()
    try:
        body = client.get("/api/notifications?party=CONTRACTOR&role=PROJECT_MANAGER").json()
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()

    kinds = [n["kind"] for n in body["notifications"]]
    assert NotificationKind.DOCUMENTS_REMINDER.value in kinds
    assert body["reminder_count"] >= 1
