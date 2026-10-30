"""Reminders, both kinds (FR-11).

Reminders are computed on request rather than written by a background job, so
nothing has to be running for one to appear - and nothing has to be cleaned up
when the thing being reminded about is dealt with. Both delays are read from
the policy file and can be overridden in settings, so a demo can set them to
zero and show the path working instead of waiting a day for it.
"""

from datetime import UTC, datetime, timedelta

import pytest

from app.analysis.scripted import ScriptedProvider
from app.config import get_settings
from app.domain.enums import NotificationKind, Party, Role
from app.policy.loader import get_policy
from app.repositories.memory import InMemoryContractRepository
from app.seed.demo_contract import PRIVATE_CONTRACT_ID
from app.seed.demo_requests import TEXT_PCR_SMALL
from app.services import change_requests as svc

NOW = datetime(2027, 3, 1, 9, 0, tzinfo=UTC)
PM = Role.PROJECT_MANAGER


@pytest.fixture(autouse=True)
def _clean_settings_cache():  # noqa: ANN202
    """Settings are cached, and these tests change the environment."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def awaiting_documents(repo: InMemoryContractRepository, at: datetime) -> str:
    """A request stage 2 sent back for want of a cost quote."""
    request = svc.submit_request(
        repo,
        PRIVATE_CONTRACT_ID,
        svc.RequestInput(
            requester_name="م. فهد القحطاني",
            requester_party=Party.CONTRACTOR,
            body_ar=TEXT_PCR_SMALL,
            attachments=("طلب تغيير رسمي",),
        ),
        at,
    )
    result = svc.analyse_request(repo, request.id, ScriptedProvider(), at)
    assert result.request.state.value == "AWAITING_DOCUMENTS"
    return request.id


# ---------------------------------------------------------------------------
# The configured delays
# ---------------------------------------------------------------------------


def test_both_delays_default_to_the_policy_file() -> None:
    policy = get_policy()
    assert svc.pending_approval_hours() == policy.pending_approval_hours
    assert svc.awaiting_documents_hours() == policy.awaiting_documents_hours


def test_both_delays_can_be_overridden_in_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REMINDER_PENDING_APPROVAL_HOURS", "0")
    monkeypatch.setenv("REMINDER_AWAITING_DOCUMENTS_HOURS", "0")
    get_settings.cache_clear()

    assert svc.pending_approval_hours() == 0
    assert svc.awaiting_documents_hours() == 0


def test_an_override_of_zero_is_a_value_not_an_absence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``or`` would discard it, which is exactly the value a demo wants."""
    monkeypatch.setenv("REMINDER_AWAITING_DOCUMENTS_HOURS", "0")
    get_settings.cache_clear()

    assert svc.awaiting_documents_hours() == 0
    assert get_policy().awaiting_documents_hours != 0


# ---------------------------------------------------------------------------
# The documents reminder
# ---------------------------------------------------------------------------


def test_nothing_is_reminded_before_the_delay_passes() -> None:
    repo = InMemoryContractRepository()
    awaiting_documents(repo, NOW)

    assert svc.document_reminders_for(repo, Party.CONTRACTOR, PM, NOW + timedelta(minutes=1)) == []


def test_a_request_waiting_on_documents_is_reminded(monkeypatch: pytest.MonkeyPatch) -> None:
    repo = InMemoryContractRepository()
    cr_id = awaiting_documents(repo, NOW)

    monkeypatch.setenv("REMINDER_AWAITING_DOCUMENTS_HOURS", "0")
    get_settings.cache_clear()
    reminders = svc.document_reminders_for(repo, Party.CONTRACTOR, PM, NOW + timedelta(hours=3))

    assert [r.kind for r in reminders] == [NotificationKind.DOCUMENTS_REMINDER]
    assert reminders[0].cr_id == cr_id
    assert reminders[0].is_reminder is True
    assert "3" in reminders[0].message_en


def test_the_reminder_is_counted_from_the_ask_not_the_submission(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A request submitted on Monday and found incomplete on Thursday has been
    waiting since Thursday."""
    repo = InMemoryContractRepository()
    asked = NOW + timedelta(days=3)
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
    svc.analyse_request(repo, request.id, ScriptedProvider(), asked)

    monkeypatch.setenv("REMINDER_AWAITING_DOCUMENTS_HOURS", "24")
    get_settings.cache_clear()

    # 23 hours after the ask, but four days after submission. Counted from
    # submission this would be long overdue; counted from the ask it is not.
    assert svc.document_reminders_for(repo, Party.CONTRACTOR, PM, asked + timedelta(hours=23)) == []
    later = svc.document_reminders_for(repo, Party.CONTRACTOR, PM, asked + timedelta(hours=25))
    assert [r.kind for r in later] == [NotificationKind.DOCUMENTS_REMINDER]


def test_only_the_party_that_was_asked_is_reminded(monkeypatch: pytest.MonkeyPatch) -> None:
    repo = InMemoryContractRepository()
    awaiting_documents(repo, NOW)
    monkeypatch.setenv("REMINDER_AWAITING_DOCUMENTS_HOURS", "0")
    get_settings.cache_clear()
    later = NOW + timedelta(hours=1)

    assert svc.document_reminders_for(repo, Party.CONTRACTOR, PM, later)
    # The entity was not asked for anything, and neither was any other role.
    assert svc.document_reminders_for(repo, Party.GOVERNMENT_ENTITY, PM, later) == []
    assert svc.document_reminders_for(repo, Party.CONTRACTOR, Role.CEO, later) == []


def test_supplying_the_documents_stops_the_reminder(monkeypatch: pytest.MonkeyPatch) -> None:
    """It follows the state, not a timer."""
    repo = InMemoryContractRepository()
    cr_id = awaiting_documents(repo, NOW)
    svc.replace_attachments(
        repo,
        cr_id,
        Party.CONTRACTOR,
        PM,
        "م. فهد القحطاني",
        ("طلب تغيير رسمي", "عرض سعر أو تحليل تكلفة"),
        NOW,
    )
    svc.analyse_request(repo, cr_id, ScriptedProvider(), NOW)

    monkeypatch.setenv("REMINDER_AWAITING_DOCUMENTS_HOURS", "0")
    get_settings.cache_clear()

    assert svc.document_reminders_for(repo, Party.CONTRACTOR, PM, NOW + timedelta(hours=1)) == []


def test_a_request_that_was_never_asked_is_never_reminded() -> None:
    """No ask, no clock. A request in any other state has nothing pending."""
    repo = InMemoryContractRepository()
    svc.analyse_request(repo, "CR-B-PCR", ScriptedProvider(), NOW)

    assert svc.document_reminders_for(repo, Party.CONTRACTOR, PM, NOW + timedelta(days=30)) == []


# ---------------------------------------------------------------------------
# Both kinds together
# ---------------------------------------------------------------------------


def test_the_notification_list_carries_reminders_and_stored_notices(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = InMemoryContractRepository()
    awaiting_documents(repo, NOW)

    monkeypatch.setenv("REMINDER_AWAITING_DOCUMENTS_HOURS", "0")
    get_settings.cache_clear()
    served = svc.notifications_for(repo, Party.CONTRACTOR, PM, NOW + timedelta(hours=1))

    kinds = [n.kind for n in served]
    # The ask itself, and the reminder about it.
    assert NotificationKind.DOCUMENTS_REQUIRED in kinds
    assert NotificationKind.DOCUMENTS_REMINDER in kinds


def test_an_approval_reminder_and_a_documents_reminder_can_coexist(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Two requests, two different things being waited on, one inbox."""
    repo = InMemoryContractRepository()
    awaiting_documents(repo, NOW)
    svc.analyse_request(repo, "CR-B-PCR", ScriptedProvider(), NOW)
    svc.start_approval(repo, "CR-B-PCR", NOW)
    step = svc.current_step(tuple(repo.list_approval_steps("CR-B-PCR")))
    assert step is not None

    monkeypatch.setenv("REMINDER_AWAITING_DOCUMENTS_HOURS", "0")
    monkeypatch.setenv("REMINDER_PENDING_APPROVAL_HOURS", "0")
    get_settings.cache_clear()
    # An approval step is stamped by the pipeline clock and the documents ask
    # by the caller's, so "later" has to be later than both of them.
    later = max(step.created_at, NOW) + timedelta(hours=1)

    documents = svc.document_reminders_for(repo, Party.CONTRACTOR, PM, later)
    approvals = svc.reminders_for(repo, step.party, step.role, later)

    assert [r.kind for r in documents] == [NotificationKind.DOCUMENTS_REMINDER]
    assert [r.kind for r in approvals] == [NotificationKind.APPROVAL_REMINDER]
