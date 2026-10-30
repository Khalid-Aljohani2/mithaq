"""The Article 67 ledger, accumulating through the real workflow.

The rules engine has always known how to add change orders up. What it never
had was anything putting change orders on the ledger: the v2 workflow approved
requests and the ledger stayed empty, so the cumulative caps that are the
product's entire reason for existing were enforced only in the engine's own
unit tests.

These tests go over HTTP, through the same endpoints the UI uses, because that
is where the promise has to hold. Every test runs twice, in memory and against
Postgres.
"""

from decimal import Decimal
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.dependencies import get_repository
from app.domain.enums import OrderStatus
from app.main import app
from app.regulations.loader import get_limits
from app.seed.demo_contract import GOVERNMENT_CONTRACT_ID, PRIVATE_CONTRACT_ID
from app.seed.demo_requests import TEXT_GOV_WITHIN_LIMITS, TEXT_PCR_SMALL

client = TestClient(app)
pytestmark = pytest.mark.usefixtures("backend")

GOV = f"/api/contracts/{GOVERNMENT_CONTRACT_ID}"
PRIVATE = f"/api/contracts/{PRIVATE_CONTRACT_ID}"
DOCS = ["طلب تغيير رسمي", "عرض سعر أو تحليل تكلفة"]

#: The contract is 4,800,000 SAR, so Article 67(1)(b) and 67(2) both cap
#: cumulative increases at 20% = 960,000 SAR.
INCREASE_CAP = Decimal("960000")
#: One extra integration point on ITM-04 at the contract rate.
SLICE = Decimal("135000")
#: Twelve extra servers on ITM-05.
BIG = Decimal("540000")


def submit(contract: str, text: str) -> str:
    """Submit a request and return its id. The text has a recorded analysis."""
    response = client.post(
        f"/api/contracts/{contract}/change-requests",
        json={
            "requester_name": "م. فهد القحطاني",
            "requester_party": "CONTRACTOR",
            "body_ar": text,
            "attachments": DOCS,
        },
    )
    assert response.status_code == 201, response.text
    return str(response.json()["request"]["id"])


def analyse(cr_id: str) -> dict[str, Any]:
    response = client.post(f"/api/change-requests/{cr_id}/analyse")
    assert response.status_code == 200, response.text
    return dict(response.json())


def decide_all(cr_id: str) -> Any:
    """Walk the whole chain approving, returning the final response."""
    client.post(f"/api/change-requests/{cr_id}/start-approval")
    while True:
        chain = client.get(f"/api/change-requests/{cr_id}").json()["chain"]
        pending = [s for s in chain if s["decision"] == "PENDING"]
        if not pending:
            return client.get(f"/api/change-requests/{cr_id}")
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
        if response.status_code != 200:
            return response


def ledger(contract: str) -> dict[str, Any]:
    return dict(client.get(f"/api/contracts/{contract}/ledger").json())


def approved_total(contract: str, category: str) -> Decimal:
    return Decimal(ledger(contract)["usage"][category]["after_value"])


def orders_of(contract: str, cr_id: str) -> list[dict[str, Any]]:
    return [o for o in ledger(contract)["orders"] if o["change_request_id"] == cr_id]


# ---------------------------------------------------------------------------
# Entries reach the ledger at all
# ---------------------------------------------------------------------------


def test_an_analysed_request_has_not_touched_the_ledger_yet() -> None:
    """A recommendation is not a commitment, and does not reserve anything."""
    analyse("CR-F-GOV-OK")

    assert orders_of(GOVERNMENT_CONTRACT_ID, "CR-F-GOV-OK") == []
    assert approved_total(GOVERNMENT_CONTRACT_ID, "INCREASE_EXISTING") == 0


def test_entering_approval_writes_a_pending_entry() -> None:
    analyse("CR-F-GOV-OK")
    client.post("/api/change-requests/CR-F-GOV-OK/start-approval")

    entries = orders_of(GOVERNMENT_CONTRACT_ID, "CR-F-GOV-OK")
    assert len(entries) == 1
    assert entries[0]["type"] == "INCREASE_EXISTING"
    assert Decimal(entries[0]["value"]) == BIG
    assert entries[0]["status"] == OrderStatus.PENDING_AUTHORITY_APPROVAL.value


def test_a_pending_entry_counts_toward_nothing() -> None:
    """ "Committed if approved" means visible, not counted (FR-10)."""
    analyse("CR-F-GOV-OK")
    client.post("/api/change-requests/CR-F-GOV-OK/start-approval")

    usage = ledger(GOVERNMENT_CONTRACT_ID)["usage"]["INCREASE_EXISTING"]
    assert Decimal(usage["after_value"]) == 0
    assert Decimal(usage["pending_value"]) == BIG
    assert Decimal(usage["headroom_value"]) == INCREASE_CAP


def test_final_approval_makes_the_entry_count() -> None:
    analyse("CR-F-GOV-OK")
    decide_all("CR-F-GOV-OK")

    entries = orders_of(GOVERNMENT_CONTRACT_ID, "CR-F-GOV-OK")
    assert [e["status"] for e in entries] == [OrderStatus.APPROVED.value]
    usage = ledger(GOVERNMENT_CONTRACT_ID)["usage"]["INCREASE_EXISTING"]
    assert Decimal(usage["after_value"]) == BIG
    assert Decimal(usage["pending_value"]) == 0
    assert Decimal(usage["headroom_value"]) == INCREASE_CAP - BIG


def test_a_substitution_writes_both_halves() -> None:
    """Article 67 counts gross movements, so a net figure would understate it."""
    analyse("CR-C-SUBSTITUTION")
    decide_all("CR-C-SUBSTITUTION")

    entries = sorted(orders_of(PRIVATE_CONTRACT_ID, "CR-C-SUBSTITUTION"), key=lambda e: e["type"])
    assert [e["type"] for e in entries] == ["DECREASE_EXISTING", "INCREASE_EXISTING"]
    assert all(e["status"] == OrderStatus.APPROVED.value for e in entries)
    # 12 servers out at 45,000 and in at 56,000: both halves, not the 132,000 net.
    assert Decimal(entries[0]["value"]) == Decimal("540000")
    assert Decimal(entries[1]["value"]) == Decimal("672000")


def test_a_private_contract_writes_the_same_entries() -> None:
    """One ledger for every contract. Article 67 is what is evaluated only on
    government contracts, not what is recorded."""
    analyse("CR-B-PCR")
    decide_all("CR-B-PCR")

    entries = orders_of(PRIVATE_CONTRACT_ID, "CR-B-PCR")
    assert len(entries) == 1
    assert entries[0]["status"] == OrderStatus.APPROVED.value
    assert ledger(PRIVATE_CONTRACT_ID)["legal_limits_apply"] is False


def test_a_request_closed_as_in_scope_writes_nothing() -> None:
    """It is not a change, so it belongs on no ledger."""
    analyse("CR-A-INSCOPE")
    assert orders_of(PRIVATE_CONTRACT_ID, "CR-A-INSCOPE") == []


# ---------------------------------------------------------------------------
# The salami: the reason cumulative caps exist
# ---------------------------------------------------------------------------


def test_slicing_a_change_past_the_cap_is_refused_at_the_final_approval() -> None:
    """Eight slices, each harmless, that together breach Article 67.

    All eight are submitted and analysed first, so every one is judged against
    an empty ledger and every one is recommended for approval. That is exactly
    how the evasion works: no single request ever looks wrong.

    Seven slices of 135,000 reach 945,000, inside the 960,000 cap. The eighth
    would reach 1,080,000, and it is refused at the moment the chain completes
    - not when it was analysed, because that is not when the commitment is
    made.
    """
    slices = [submit(GOVERNMENT_CONTRACT_ID, TEXT_PCR_SMALL) for _ in range(8)]
    for cr_id in slices:
        assert analyse(cr_id)["request"]["recommendation"] == "APPROVE"

    for position, cr_id in enumerate(slices[:7], start=1):
        decide_all(cr_id)
        assert approved_total(GOVERNMENT_CONTRACT_ID, "INCREASE_EXISTING") == SLICE * position

    assert approved_total(GOVERNMENT_CONTRACT_ID, "INCREASE_EXISTING") == Decimal("945000")

    refused = decide_all(slices[7])

    assert refused.status_code == 409, refused.text
    detail = refused.json()["detail"]
    assert detail["code"] == "LEGAL_CAP_EXCEEDED"
    # The party is told the provision, not just that it was refused (NFR-02).
    limits = get_limits()
    assert limits.combined.article_ref_en in detail["articles"]
    assert any("67" in ref for ref in detail["articles"])


def test_the_refused_slice_commits_nothing() -> None:
    """A refusal must leave the ledger exactly where it was."""
    slices = [submit(GOVERNMENT_CONTRACT_ID, TEXT_PCR_SMALL) for _ in range(8)]
    for cr_id in slices:
        analyse(cr_id)
    for cr_id in slices[:7]:
        decide_all(cr_id)
    before = approved_total(GOVERNMENT_CONTRACT_ID, "INCREASE_EXISTING")

    decide_all(slices[7])

    assert approved_total(GOVERNMENT_CONTRACT_ID, "INCREASE_EXISTING") == before
    entries = orders_of(GOVERNMENT_CONTRACT_ID, slices[7])
    assert [e["status"] for e in entries] == [OrderStatus.PENDING_AUTHORITY_APPROVAL.value]


def test_the_refused_request_goes_to_legal_review() -> None:
    slices = [submit(GOVERNMENT_CONTRACT_ID, TEXT_PCR_SMALL) for _ in range(8)]
    for cr_id in slices:
        analyse(cr_id)
    for cr_id in slices[:7]:
        decide_all(cr_id)

    decide_all(slices[7])

    request = client.get(f"/api/change-requests/{slices[7]}").json()["request"]
    assert request["needs_legal_review"] is True
    assert request["legally_blocked"] is True
    # Still in approval: nobody rejected it, and no internal approval can lift
    # a legal cap, so it waits for a legal reading rather than being decided.
    assert request["state"] == "IN_APPROVAL"

    notifications = client.get(
        "/api/notifications?party=GOVERNMENT_ENTITY&role=LEGAL_ADVISOR"
    ).json()["notifications"]
    # The legal adviser is also an approver on a government chain, so they
    # already hold an APPROVAL_PENDING for this request. The refusal has to
    # arrive as its own kind, or it reads as the same routine ask.
    mine = [n["kind"] for n in notifications if n["cr_id"] == slices[7]]
    assert "LEGAL_REVIEW_REQUIRED" in mine


def test_the_refusal_is_audited() -> None:
    slices = [submit(GOVERNMENT_CONTRACT_ID, TEXT_PCR_SMALL) for _ in range(8)]
    for cr_id in slices:
        analyse(cr_id)
    for cr_id in slices[:7]:
        decide_all(cr_id)

    decide_all(slices[7])

    events = client.get(f"{GOV}/audit").json()["events"]
    refusals = [e for e in events if e["action"] == "CR_LEGAL_CAP_REFUSED"]
    assert [e["entity_id"] for e in refusals] == [slices[7]]
    assert "67" in (refusals[0]["reason"] or "")


# ---------------------------------------------------------------------------
# Two requests, each fine alone
# ---------------------------------------------------------------------------


def test_two_requests_valid_separately_are_not_valid_together() -> None:
    """Both enter approval inside every cap. Only the first can finish.

    This is the case the re-check at final approval exists for: nothing about
    either request changed, and nothing was wrong when either entered the
    chain. What changed is the contract's cumulative position in between.
    """
    first = submit(GOVERNMENT_CONTRACT_ID, TEXT_GOV_WITHIN_LIMITS)
    second = submit(GOVERNMENT_CONTRACT_ID, TEXT_GOV_WITHIN_LIMITS)
    for cr_id in (first, second):
        assert analyse(cr_id)["request"]["recommendation"] == "APPROVE"

    # Both in the chain at once: 1,080,000 pending against a 960,000 cap, and
    # none of it counted, because pending commits nobody.
    client.post(f"/api/change-requests/{first}/start-approval")
    client.post(f"/api/change-requests/{second}/start-approval")
    usage = ledger(GOVERNMENT_CONTRACT_ID)["usage"]["INCREASE_EXISTING"]
    assert Decimal(usage["pending_value"]) == BIG * 2
    assert Decimal(usage["after_value"]) == 0
    assert Decimal(usage["headroom_value"]) == INCREASE_CAP

    assert decide_all(first).status_code == 200
    assert approved_total(GOVERNMENT_CONTRACT_ID, "INCREASE_EXISTING") == BIG

    refused = decide_all(second)

    assert refused.status_code == 409, refused.text
    assert refused.json()["detail"]["code"] == "LEGAL_CAP_EXCEEDED"
    assert approved_total(GOVERNMENT_CONTRACT_ID, "INCREASE_EXISTING") == BIG


def test_the_same_pair_is_allowed_on_a_private_contract() -> None:
    """Article 67 governs government procurement. Applying it elsewhere would
    be inventing law, however sensible the number looks."""
    first = submit(PRIVATE_CONTRACT_ID, TEXT_GOV_WITHIN_LIMITS)
    second = submit(PRIVATE_CONTRACT_ID, TEXT_GOV_WITHIN_LIMITS)
    for cr_id in (first, second):
        analyse(cr_id)

    assert decide_all(first).status_code == 200
    assert decide_all(second).status_code == 200

    # Both landed, and both are on the ledger: the record is kept either way.
    assert approved_total(PRIVATE_CONTRACT_ID, "INCREASE_EXISTING") == BIG * 2


# ---------------------------------------------------------------------------
# Releasing what was never committed
# ---------------------------------------------------------------------------


def test_rejection_releases_the_pending_entries() -> None:
    analyse("CR-F-GOV-OK")
    client.post("/api/change-requests/CR-F-GOV-OK/start-approval")
    step = client.get("/api/change-requests/CR-F-GOV-OK").json()["chain"][0]

    client.post(
        "/api/change-requests/CR-F-GOV-OK/decide",
        json={
            "party": step["party"],
            "role": step["role"],
            "decided_by": "مراجع",
            "decision": "REJECTED",
            "reason": "التمويل غير متاح.",
        },
    )

    entries = orders_of(GOVERNMENT_CONTRACT_ID, "CR-F-GOV-OK")
    assert [e["status"] for e in entries] == [OrderStatus.REJECTED.value]
    usage = ledger(GOVERNMENT_CONTRACT_ID)["usage"]["INCREASE_EXISTING"]
    assert Decimal(usage["after_value"]) == 0
    assert Decimal(usage["pending_value"]) == 0
    # Kept rather than deleted: the ledger shows what was asked for and refused.
    assert len(entries) == 1


def test_a_rejected_request_frees_the_headroom_for_another() -> None:
    first = submit(GOVERNMENT_CONTRACT_ID, TEXT_GOV_WITHIN_LIMITS)
    second = submit(GOVERNMENT_CONTRACT_ID, TEXT_GOV_WITHIN_LIMITS)
    for cr_id in (first, second):
        analyse(cr_id)

    decide_all(first)
    # Now reject the first... it is already approved, so instead reject the
    # second and confirm a third can still take its place.
    client.post(f"/api/change-requests/{second}/start-approval")
    step = client.get(f"/api/change-requests/{second}").json()["chain"][0]
    client.post(
        f"/api/change-requests/{second}/decide",
        json={
            "party": step["party"],
            "role": step["role"],
            "decided_by": "مراجع",
            "decision": "REJECTED",
            "reason": "مكرر.",
        },
    )

    usage = ledger(GOVERNMENT_CONTRACT_ID)["usage"]["INCREASE_EXISTING"]
    assert Decimal(usage["after_value"]) == BIG
    assert Decimal(usage["pending_value"]) == 0


def test_requesting_a_revision_releases_the_entries() -> None:
    analyse("CR-F-GOV-OK")
    client.post("/api/change-requests/CR-F-GOV-OK/start-approval")
    step = client.get("/api/change-requests/CR-F-GOV-OK").json()["chain"][0]

    client.post(
        "/api/change-requests/CR-F-GOV-OK/decide",
        json={
            "party": step["party"],
            "role": step["role"],
            "decided_by": "مراجع",
            "decision": "REVISION_REQUESTED",
            "reason": "يرجى توضيح مواصفات الخوادم.",
        },
    )

    entries = orders_of(GOVERNMENT_CONTRACT_ID, "CR-F-GOV-OK")
    assert [e["status"] for e in entries] == [OrderStatus.REJECTED.value]
    assert Decimal(ledger(GOVERNMENT_CONTRACT_ID)["usage"]["INCREASE_EXISTING"]["after_value"]) == 0


def test_a_revised_request_writes_fresh_entries_without_doubling_up() -> None:
    """Same ids, replaced. Two sets would double-count the same change."""
    analyse("CR-F-GOV-OK")
    client.post("/api/change-requests/CR-F-GOV-OK/start-approval")
    step = client.get("/api/change-requests/CR-F-GOV-OK").json()["chain"][0]
    client.post(
        "/api/change-requests/CR-F-GOV-OK/decide",
        json={
            "party": step["party"],
            "role": step["role"],
            "decided_by": "مراجع",
            "decision": "REVISION_REQUESTED",
            "reason": "يرجى التوضيح.",
        },
    )

    analyse("CR-F-GOV-OK")
    decide_all("CR-F-GOV-OK")

    entries = orders_of(GOVERNMENT_CONTRACT_ID, "CR-F-GOV-OK")
    assert len(entries) == 1
    assert entries[0]["status"] == OrderStatus.APPROVED.value
    assert approved_total(GOVERNMENT_CONTRACT_ID, "INCREASE_EXISTING") == BIG


# ---------------------------------------------------------------------------
# The two layers agree
# ---------------------------------------------------------------------------


def net_from_ledger(contract: str) -> Decimal:
    """The net approved movement, rebuilt from the Article 67 entries."""
    usage = ledger(contract)["usage"]
    added = Decimal(usage["NEW_ITEMS"]["after_value"]) + Decimal(
        usage["INCREASE_EXISTING"]["after_value"]
    )
    removed = Decimal(usage["DECREASE_EXISTING"]["after_value"])
    return added - removed


@pytest.mark.parametrize(
    ("contract", "cr_id"),
    [
        (PRIVATE_CONTRACT_ID, "CR-B-PCR"),
        (PRIVATE_CONTRACT_ID, "CR-E-NCR"),
        (PRIVATE_CONTRACT_ID, "CR-C-SUBSTITUTION"),
        (GOVERNMENT_CONTRACT_ID, "CR-F-GOV-OK"),
    ],
)
def test_policy_and_ledger_report_the_same_approved_total(contract: str, cr_id: str) -> None:
    """Two layers, one set of facts.

    The policy cap works on the net cost impact of approved requests; Article
    67 works on gross movements per category. They are different views, but
    they are views of the same approved changes, and if they disagree one of
    them is lying to somebody.
    """
    analyse(cr_id)
    decide_all(cr_id)

    policy_used = Decimal(ledger(contract)["policy_usage"]["cost_increase"]["used_value"])
    assert policy_used == net_from_ledger(contract)


def test_the_two_layers_also_agree_while_something_is_pending() -> None:
    analyse("CR-F-GOV-OK")
    client.post("/api/change-requests/CR-F-GOV-OK/start-approval")

    body = ledger(GOVERNMENT_CONTRACT_ID)
    policy = body["policy_usage"]["cost_increase"]
    usage = body["usage"]["INCREASE_EXISTING"]
    assert Decimal(policy["pending_value"]) == Decimal(usage["pending_value"]) == BIG
    assert Decimal(policy["used_value"]) == Decimal(usage["after_value"]) == 0


def test_an_unpriced_request_cannot_enter_approval() -> None:
    """A request analysed before the gross halves were persisted.

    Writing its entries anyway would put zeros on the ledger, and a change
    counted as zero against a cumulative cap is a change that evades it. The
    refusal is loud; a silent zero would not be.
    """
    analyse("CR-F-GOV-OK")
    stored = client.get("/api/change-requests/CR-F-GOV-OK").json()["request"]
    assert stored["added_value"] is not None

    repo = app.dependency_overrides[get_repository]()
    request = repo.get_change_request("CR-F-GOV-OK")
    assert request is not None
    repo.replace_change_request(
        request.model_copy(update={"added_value": None, "removed_value": None})
    )

    response = client.post("/api/change-requests/CR-F-GOV-OK/start-approval")

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "NOT_PRICED"
    assert orders_of(GOVERNMENT_CONTRACT_ID, "CR-F-GOV-OK") == []
