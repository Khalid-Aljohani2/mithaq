"""Stage 5 - cost and schedule impact (FR-07). Deterministic code.

Cost is computed from contract unit rates and quantities. A model never
multiplies, sums, or compares against a threshold here (NFR-03, NFR-15).

Where no contract rate exists - a brand new item, or a substitute product -
a human-entered figure is required and the result is flagged. That is the
documented default for open question Q1.
"""

from dataclasses import dataclass, field
from decimal import Decimal

from app.analysis.schemas import ScopeOutput
from app.domain.change_request import ChangeRequest
from app.domain.enums import ChangeKind, ImpactType
from app.domain.models import Contract
from app.policy.loader import get_policy

_HUNDRED = Decimal("100")
_PCT_EXP = Decimal("0.0001")


class CostingError(Exception):
    """The request cannot be priced from the information available."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class RateCheck:
    """Comparison of a proposed unit rate against the contract rate."""

    line_id: str
    contract_rate: Decimal
    proposed_rate: Decimal
    deviation_pct: Decimal
    cap_pct: Decimal
    flagged: bool


@dataclass(frozen=True)
class CostImpact:
    """What a change request does to cost and schedule."""

    #: Signed. Positive adds to the contract value, negative reduces it.
    cost_impact: Decimal
    #: The part that adds work, as a positive magnitude.
    added_value: Decimal
    #: The part that removes work, as a positive magnitude.
    removed_value: Decimal
    time_impact_days: int
    impact_type: ImpactType
    rate_checks: tuple[RateCheck, ...] = ()
    #: True when any figure rests on a human-entered rate rather than the
    #: contract (open question Q1).
    rate_human_entered: bool = False
    notes_en: tuple[str, ...] = field(default_factory=tuple)

    @property
    def unit_rate_flagged(self) -> bool:
        return any(check.flagged for check in self.rate_checks)


def _exact_deviation_pct(contract_rate: Decimal, proposed_rate: Decimal) -> Decimal:
    """Absolute percentage deviation, unrounded, for comparison."""
    if contract_rate == 0:
        return Decimal("0")
    return abs(proposed_rate - contract_rate) / contract_rate * _HUNDRED


def check_unit_rate(line_id: str, contract_rate: Decimal, proposed_rate: Decimal) -> RateCheck:
    """Flag a proposed rate deviating beyond the policy limit.

    "More than" is strictly greater: a deviation of exactly the cap is not
    flagged, matching how the legal caps treat "not exceeding".

    The comparison uses the **unrounded** deviation. Comparing the displayed
    4-decimal figure instead would let a rate 20.00002% off the contract round
    down to 20.0000 and escape the flag - the same rounding trap the Article 67
    engine sidesteps by comparing values rather than percentages. The rounded
    figure is kept only for display.
    """
    cap = get_policy().unit_rate_deviation_cap_pct
    exact = _exact_deviation_pct(contract_rate, proposed_rate)
    return RateCheck(
        line_id=line_id,
        contract_rate=contract_rate,
        proposed_rate=proposed_rate,
        deviation_pct=exact.quantize(_PCT_EXP),
        cap_pct=cap,
        flagged=exact > cap,
    )


def _require_line(contract: Contract, line_id: str) -> Decimal:
    line = contract.line(line_id)
    if line is None:
        raise CostingError("UNKNOWN_LINE", f"breakdown line {line_id} is not in the contract")
    return line.unit_rate


def compute_impact(
    contract: Contract,
    request: ChangeRequest,
    scope: ScopeOutput,
) -> CostImpact:
    """Price a classified change request from the contract baseline."""
    policy_days = request.human_entered_days or 0
    notes: list[str] = []
    rate_checks: list[RateCheck] = []

    if scope.kind is ChangeKind.IN_SCOPE:
        return CostImpact(
            cost_impact=Decimal("0"),
            added_value=Decimal("0"),
            removed_value=Decimal("0"),
            time_impact_days=0,
            impact_type=ImpactType.NONE,
            notes_en=("In scope: covered by the existing breakdown, costs nothing extra.",),
        )

    if scope.kind is ChangeKind.UNCLEAR:
        # The analysis could not classify the request, so there is nothing to
        # price. Returning a zero impact rather than raising lets stage 7 reach
        # its own conclusion - REQUEST_REVISION, asking the requester - which is
        # what FR-05 asks for. Raising here would turn "we need to ask a human"
        # into a crash.
        return CostImpact(
            cost_impact=Decimal("0"),
            added_value=Decimal("0"),
            removed_value=Decimal("0"),
            time_impact_days=0,
            impact_type=ImpactType.NONE,
            notes_en=("Unclassified: cannot be priced until the request is clarified.",),
        )

    if scope.kind is ChangeKind.PCR:
        if scope.matched_line_ids and scope.quantity_delta is not None:
            line_id = scope.matched_line_ids[0]
            rate = _require_line(contract, line_id)
            added = scope.quantity_delta * rate
            notes.append(f"{scope.quantity_delta} x {rate} from contract line {line_id}.")
            human_entered = False
        else:
            # No matching line: Q1's default applies.
            if request.human_entered_amount is None:
                raise CostingError(
                    "RATE_REQUIRED",
                    "a new item with no matching breakdown line needs a human-entered "
                    "amount before it can be priced (open question Q1)",
                )
            added = request.human_entered_amount
            human_entered = True
            notes.append(
                "No matching breakdown line; priced from a human-entered amount and flagged."
            )
        return CostImpact(
            cost_impact=added,
            added_value=added,
            removed_value=Decimal("0"),
            time_impact_days=policy_days,
            impact_type=_impact_type(added, policy_days),
            rate_checks=tuple(rate_checks),
            rate_human_entered=human_entered,
            notes_en=tuple(notes),
        )

    if scope.kind is ChangeKind.NCR:
        if not scope.matched_line_ids or scope.quantity_delta is None:
            raise CostingError(
                "LINE_REQUIRED", "a decrease must name the breakdown line it reduces"
            )
        line_id = scope.matched_line_ids[0]
        rate = _require_line(contract, line_id)
        removed = scope.quantity_delta * rate
        notes.append(f"-{scope.quantity_delta} x {rate} from contract line {line_id}.")
        return CostImpact(
            cost_impact=-removed,
            added_value=Decimal("0"),
            removed_value=removed,
            time_impact_days=policy_days,
            impact_type=_impact_type(-removed, policy_days),
            notes_en=tuple(notes),
        )

    if scope.kind is ChangeKind.SUBSTITUTION:
        if not scope.matched_line_ids:
            raise CostingError(
                "LINE_REQUIRED", "a substitution must name the breakdown line it replaces"
            )
        if request.human_entered_unit_rate is None:
            raise CostingError(
                "RATE_REQUIRED",
                "a substitution needs a human-entered unit rate for the substitute product",
            )
        line_id = scope.matched_line_ids[0]
        contract_rate = _require_line(contract, line_id)
        # A substitution usually replaces the whole line ("same number, different
        # product") and the request states no figure. The analysis is never shown
        # contract quantities, so it cannot supply one either - code reads the
        # contracted quantity instead of demanding a number nobody has.
        quantity = scope.quantity_delta
        if quantity is None:
            line = contract.line(line_id)
            quantity = line.quantity if line else Decimal("0")
            notes.append(
                f"No quantity stated; substituting the full contracted quantity of {line_id}."
            )
        removed = quantity * contract_rate
        added = quantity * request.human_entered_unit_rate
        rate_checks.append(check_unit_rate(line_id, contract_rate, request.human_entered_unit_rate))
        notes.append(
            f"Substitution on {line_id}: removes {quantity} x {contract_rate}, "
            f"adds {quantity} x {request.human_entered_unit_rate}."
        )
        net = added - removed
        return CostImpact(
            cost_impact=net,
            added_value=added,
            removed_value=removed,
            time_impact_days=policy_days,
            impact_type=_impact_type(net, policy_days),
            rate_checks=tuple(rate_checks),
            rate_human_entered=True,
            notes_en=tuple(notes),
        )

    raise CostingError("UNCLASSIFIED", f"cannot price a request classified as {scope.kind}")


def _impact_type(cost: Decimal, days: int) -> ImpactType:
    """What this request affects (FR-07)."""
    has_cost = cost != 0
    has_time = days != 0
    if has_cost and has_time:
        return ImpactType.BOTH
    if has_cost:
        return ImpactType.COST
    if has_time:
        return ImpactType.TIME
    return ImpactType.NONE
