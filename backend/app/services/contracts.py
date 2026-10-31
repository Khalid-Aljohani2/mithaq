"""Contract intake: a person enters a contract and its priced baseline (FR-01).

Layering (NFR-11): the router does HTTP, this module does validation, id
allocation, storage through the repository interface and the audit row.

Every problem in a submitted contract is collected and reported at once, each
with a stable code and a message in both languages, so a form can mark every
bad field in one round trip instead of one per submit.

Money stays ``Decimal`` throughout (NFR-01). A line total is computed here as
``quantity * unit_rate`` exactly; it is never rounded. A product that would
need more than two decimal places is refused rather than rounded, because
rounding would make the contract value disagree with its own lines.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from app.domain.audit import AuditAction, AuditEvent
from app.domain.enums import Party, Role
from app.domain.models import BreakdownLine, Contract
from app.repositories.base import ContractRepository
from app.schemas.contracts import (
    MAX_BREAKDOWN_LINES,
    ContractCreateInput,
    ContractProblem,
)

#: Who may enter a contract or ask for an AI draft of one: the client side
#: only, at project-manager or CEO level. Kept here as a module constant rather
#: than in ``policy.yaml`` because it is a permission, not a threshold; the
#: policy file holds caps and their escalation roles. See ADR 0006.
CONTRACT_CREATOR_PARTY = Party.GOVERNMENT_ENTITY
CONTRACT_CREATOR_ROLES: frozenset[Role] = frozenset({Role.PROJECT_MANAGER, Role.CEO})

MONEY_PLACES = 2
QUANTITY_PLACES = 4


class ContractInvalidError(Exception):
    """The submitted contract failed one or more business rules."""

    def __init__(self, problems: list[ContractProblem]) -> None:
        super().__init__(f"{len(problems)} problem(s) in the submitted contract")
        self.problems = problems


class ContractWrongRoleError(Exception):
    """This party and role may not create a contract."""

    def __init__(self, party: Party, role: Role) -> None:
        self.code = "WRONG_ROLE"
        self.message = (
            f"{party.value} {role.value} may not create a contract; only the government "
            "entity's project manager or CEO may"
        )
        super().__init__(self.message)


def check_creator(party: Party, role: Role) -> None:
    """Refuse anyone outside the client side's PM and CEO (FR-10 style check)."""
    if party is not CONTRACT_CREATOR_PARTY or role not in CONTRACT_CREATOR_ROLES:
        raise ContractWrongRoleError(party, role)


def decimal_places(value: Decimal) -> int:
    """How many digits a Decimal carries after the point, ignoring trailing zeros."""
    normalised = value.normalize()
    exponent = normalised.as_tuple().exponent
    if not isinstance(exponent, int):  # NaN or Infinity
        return 0
    return max(0, -exponent)


def _problem(field: str, code: str, ar: str, en: str) -> ContractProblem:
    return ContractProblem(field=field, code=code, message_ar=ar, message_en=en)


def _required(field: str, value: str) -> ContractProblem | None:
    if value.strip():
        return None
    return _problem(field, "REQUIRED", "هذا الحقل مطلوب.", "This field is required.")


def _finite(field: str, value: Decimal) -> ContractProblem | None:
    if value.is_finite():
        return None
    return _problem(field, "NOT_A_NUMBER", "القيمة ليست رقمًا صالحًا.", "Not a valid number.")


def _places(field: str, value: Decimal, limit: int) -> ContractProblem | None:
    if decimal_places(value) <= limit:
        return None
    return _problem(
        field,
        "TOO_MANY_DECIMALS",
        f"يسمح بـ {limit} منازل عشرية كحد أقصى.",
        f"At most {limit} decimal places are allowed.",
    )


@dataclass(frozen=True)
class _Lines:
    lines: tuple[BreakdownLine, ...]
    total: Decimal
    complete: bool


def _check_lines(payload: ContractCreateInput, problems: list[ContractProblem]) -> _Lines:
    if not payload.breakdown:
        problems.append(
            _problem(
                "breakdown",
                "EMPTY_BREAKDOWN",
                "يجب أن يحتوي جدول الكميات على بند واحد على الأقل.",
                "The breakdown needs at least one line.",
            )
        )
        return _Lines((), Decimal("0"), complete=False)
    if len(payload.breakdown) > MAX_BREAKDOWN_LINES:
        problems.append(
            _problem(
                "breakdown",
                "TOO_MANY_LINES",
                f"الحد الأقصى {MAX_BREAKDOWN_LINES} بندًا.",
                f"At most {MAX_BREAKDOWN_LINES} lines are allowed.",
            )
        )
        return _Lines((), Decimal("0"), complete=False)

    lines: list[BreakdownLine] = []
    total = Decimal("0")
    complete = True
    for index, line in enumerate(payload.breakdown):
        base = f"breakdown[{index}]"
        before = len(problems)
        for found in (
            _required(f"{base}.description_ar", line.description_ar),
            _required(f"{base}.unit_ar", line.unit_ar),
            _finite(f"{base}.quantity", line.quantity),
            _finite(f"{base}.unit_rate", line.unit_rate),
        ):
            if found:
                problems.append(found)
        if len(problems) > before:
            complete = False
            continue

        if line.quantity <= 0:
            problems.append(
                _problem(
                    f"{base}.quantity",
                    "NOT_POSITIVE",
                    "يجب أن تكون الكمية أكبر من صفر.",
                    "Quantity must be greater than zero.",
                )
            )
        if line.unit_rate < 0:
            problems.append(
                _problem(
                    f"{base}.unit_rate",
                    "NEGATIVE",
                    "لا يجوز أن يكون سعر الوحدة سالبًا.",
                    "Unit rate may not be negative.",
                )
            )
        for found in (
            _places(f"{base}.quantity", line.quantity, QUANTITY_PLACES),
            _places(f"{base}.unit_rate", line.unit_rate, MONEY_PLACES),
        ):
            if found:
                problems.append(found)
        if len(problems) > before:
            complete = False
            continue

        line_total = line.quantity * line.unit_rate
        if decimal_places(line_total) > MONEY_PLACES:
            problems.append(
                _problem(
                    f"{base}.total",
                    "TOO_MANY_DECIMALS",
                    f"ناتج الكمية × سعر الوحدة ({line_total}) يتجاوز منزلتين عشريتين.",
                    f"Quantity x unit rate ({line_total}) needs more than 2 decimal places.",
                )
            )
            complete = False
            continue

        total += line_total
        lines.append(
            BreakdownLine(
                id=f"ITM-{index + 1:02d}",
                description_ar=line.description_ar.strip(),
                unit_ar=line.unit_ar.strip(),
                quantity=line.quantity,
                unit_rate=line.unit_rate,
                total=line_total,
                approved_product_ar=(line.approved_product_ar or "").strip() or None,
                restrictions_ar=tuple(r.strip() for r in line.restrictions_ar if r.strip()),
            )
        )
    return _Lines(tuple(lines), total, complete)


def validate_contract(payload: ContractCreateInput, contract_id: str) -> Contract:
    """Check every business rule, collecting all problems; build the Contract."""
    problems: list[ContractProblem] = []
    for name in ("created_by", "title_ar", "entity_name", "contractor_name"):
        found = _required(name, getattr(payload, name))
        if found:
            problems.append(found)

    value_ok = True
    for found in (_finite("original_value", payload.original_value),):
        if found:
            problems.append(found)
            value_ok = False
    if value_ok:
        if payload.original_value <= 0:
            problems.append(
                _problem(
                    "original_value",
                    "NOT_POSITIVE",
                    "يجب أن تكون قيمة العقد أكبر من صفر.",
                    "Contract value must be greater than zero.",
                )
            )
            value_ok = False
        found = _places("original_value", payload.original_value, MONEY_PLACES)
        if found:
            problems.append(found)
            value_ok = False

    if payload.end_date <= payload.start_date:
        problems.append(
            _problem(
                "end_date",
                "END_BEFORE_START",
                "يجب أن يكون تاريخ النهاية بعد تاريخ البداية.",
                "End date must be after the start date.",
            )
        )

    lines = _check_lines(payload, problems)
    if value_ok and lines.complete and lines.total != payload.original_value:
        problems.append(
            _problem(
                "original_value",
                "TOTAL_MISMATCH",
                f"مجموع البنود ({lines.total}) لا يساوي قيمة العقد ({payload.original_value}).",
                f"The breakdown lines sum to {lines.total}, "
                f"but the contract value is {payload.original_value}.",
            )
        )

    if problems:
        raise ContractInvalidError(problems)

    return Contract(
        id=contract_id,
        title_ar=payload.title_ar.strip(),
        entity_name=payload.entity_name.strip(),
        contractor_name=payload.contractor_name.strip(),
        contract_type=payload.contract_type,
        original_value=payload.original_value,
        breakdown=lines.lines,
        start_date=payload.start_date,
        end_date=payload.end_date,
    )


def next_contract_id(repo: ContractRepository, start_year: int) -> str:
    """Allocate ``CT-<start year>-NNNN``, unique among the stored contracts."""
    existing = {c.id for c in repo.list_contracts()}
    prefix = f"CT-{start_year}-"
    number = sum(1 for cid in existing if cid.startswith(prefix)) + 1
    while f"{prefix}{number:04d}" in existing:
        number += 1
    return f"{prefix}{number:04d}"


def create_contract(
    repo: ContractRepository, payload: ContractCreateInput, now: datetime
) -> Contract:
    """Validate, store and audit a new contract. A person's action, never the AI's."""
    check_creator(payload.party, payload.role)
    contract = validate_contract(payload, next_contract_id(repo, payload.start_date.year))
    stored = repo.add_contract(contract)
    repo.append_audit(
        AuditEvent(
            occurred_at=now,
            actor_role=payload.role.value,
            actor_party=payload.party.value,
            actor_name=payload.created_by.strip(),
            action=AuditAction.CONTRACT_CREATED,
            entity_type="CONTRACT",
            entity_id=stored.id,
            contract_id=stored.id,
            reason=f"{len(stored.breakdown)} line(s), value {stored.original_value}",
        )
    )
    return stored
