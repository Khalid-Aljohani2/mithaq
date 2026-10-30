"""Demo presets: a seeded state that takes a story further than the baseline.

A preset is built by calling the **real service functions** with the recorded
AI outputs, never by writing rows directly. That matters for a demo: the state
on screen has to be a state the product can actually reach, produced by the
same code paths a user would drive. A fixture that inserts approved rows would
prove nothing and could drift from the workflow without anyone noticing.

The recorded provider is used rather than the live one, so a reset costs
nothing and always produces the same figures (FR-19).
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.analysis.scripted import ScriptedProvider
from app.domain.enums import ApprovalDecision, CRState, Party, Role
from app.repositories.base import ContractRepository
from app.seed.demo_contract import GOVERNMENT_CONTRACT_ID
from app.seed.demo_requests import TEXT_PCR_SMALL
from app.services import change_requests as svc

#: One extra integration point on ITM-04 at the contract rate of 135,000 SAR.
SLICE_VALUE = Decimal("135000")
#: Seven of them reach 945,000 against the 960,000 Article 67 cap.
APPROVED_SLICES = 7
#: Plus one more, left one signature short of being committed.
PENDING_SLICES = 1
SALAMI = "salami"
PRESETS = (SALAMI,)


def _submit_slice(repo: ContractRepository, index: int, at: datetime) -> str:
    """One more small increase on the government contract."""
    request = svc.submit_request(
        repo,
        GOVERNMENT_CONTRACT_ID,
        svc.RequestInput(
            requester_name="م. فهد القحطاني",
            requester_party=Party.CONTRACTOR,
            body_ar=TEXT_PCR_SMALL,
            attachments=("طلب تغيير رسمي", "عرض سعر أو تحليل تكلفة"),
        ),
        at,
    )
    return request.id


def _approve(
    repo: ContractRepository, cr_id: str, at: datetime, *, leave_last_step: bool = False
) -> None:
    """Walk the approval chain, optionally stopping one signature short."""
    svc.start_approval(repo, cr_id, at)
    while True:
        steps = tuple(repo.list_approval_steps(cr_id))
        pending = [step for step in steps if step.decision is ApprovalDecision.PENDING]
        if not pending:
            return
        if leave_last_step and len(pending) == 1:
            # The whole chain has signed except the last approver. Signing that
            # step is what the demo is for: it is the one the cumulative check
            # refuses.
            return
        step = pending[0]
        svc.decide_step(
            repo,
            cr_id,
            step.party,
            step.role,
            f"{step.role.value.title().replace('_', ' ')}",
            ApprovalDecision.APPROVED,
            None,
            at,
        )


def build_salami(repo: ContractRepository, now: datetime | None = None) -> dict[str, object]:
    """Seven approved slices and an eighth one signature short.

    Every slice is submitted and analysed **before** any is approved, so each
    one is judged against the ledger as it stood at the time - which is how the
    evasion works in the first place. No single request ever looks wrong.

    The result on screen: the Article 67 increase meter reads 945,000 of
    960,000, and one request sits in approval whose final signature the system
    will refuse under Article 67(1)(b) and 67(2).
    """
    at = now or datetime.now(UTC)
    provider = ScriptedProvider()

    total = APPROVED_SLICES + PENDING_SLICES
    ids: list[str] = []
    for index in range(total):
        # Spread the timestamps so the file reads as a sequence of requests
        # rather than eight things that happened in the same instant.
        submitted = at - timedelta(days=total - index)
        cr_id = _submit_slice(repo, index, submitted)
        svc.analyse_request(repo, cr_id, provider, submitted)
        ids.append(cr_id)

    issued: list[str] = []
    for cr_id in ids[:APPROVED_SLICES]:
        _approve(repo, cr_id, at)
        vo = svc.issue_variation_order(repo, cr_id, provider, at)
        issued.append(vo.id)

    awaiting = ids[APPROVED_SLICES]
    _approve(repo, awaiting, at, leave_last_step=True)

    request = repo.get_change_request(awaiting)
    if request is None or request.state is not CRState.IN_APPROVAL:
        msg = f"preset did not leave {awaiting} in approval"
        raise RuntimeError(msg)

    return {
        "preset": SALAMI,
        "contract_id": GOVERNMENT_CONTRACT_ID,
        "approved_request_ids": ids[:APPROVED_SLICES],
        "variation_order_ids": issued,
        "awaiting_final_signature_id": awaiting,
        "approved_increase_value": str(SLICE_VALUE * APPROVED_SLICES),
    }


def final_step_of(repo: ContractRepository, cr_id: str) -> tuple[Party, Role] | None:
    """Who has to sign for the refusal to happen. Used by the demo script."""
    step = svc.current_step(tuple(repo.list_approval_steps(cr_id)))
    return None if step is None else (step.party, step.role)
