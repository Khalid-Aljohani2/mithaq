"""Legal and policy limit checks. Deterministic code.

Two independent layers, and the difference between them is the point:

* **Organisation policy** (20% cost, 20% time) can be escalated past by the
  role named in the policy file. Exceeding it is an escalation, not a refusal.
* **Article 67** applies to GOVERNMENT contracts only, is evaluated by the
  existing rules engine, and is **blocking**. No internal approval lifts it.

The Article 67 engine is reused untouched. A change request is mapped onto
ledger entries and handed to it; none of its logic is reimplemented here.
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from app.domain.change_request import ChangeRequest
from app.domain.enums import ChangeCategory, ChangeKind, OrderStatus
from app.domain.models import ChangeLedger, ChangeOrder, Contract
from app.domain.rules import CapLine, RuleResult
from app.pipeline.costing import CostImpact
from app.policy.loader import PolicyThreshold, get_policy
from app.regulations.loader import get_limits
from app.services.rules_engine import evaluate

_HUNDRED = Decimal("100")
_PCT_EXP = Decimal("0.0001")


@dataclass(frozen=True)
class PolicyCheck:
    """Organisation policy evaluation (FR-07, second paragraph)."""

    cost_before_pct: Decimal
    cost_after_pct: Decimal
    cost_cap_pct: Decimal
    cost_exceeded: bool

    time_before_pct: Decimal
    time_after_pct: Decimal
    time_cap_pct: Decimal
    time_exceeded: bool

    exception_role: str
    findings_en: tuple[str, ...] = field(default_factory=tuple)

    @property
    def exception_required(self) -> bool:
        """True when some cap is exceeded and an exception could lift it."""
        return self.cost_exceeded or self.time_exceeded


def _pct(value: Decimal, base: Decimal) -> Decimal:
    if base == 0:
        return Decimal("0").quantize(_PCT_EXP)
    return (value / base * _HUNDRED).quantize(_PCT_EXP)


def check_policy(
    contract: Contract,
    cumulative_cost_before: Decimal,
    cumulative_days_before: int,
    impact: CostImpact,
) -> PolicyCheck:
    """Compare cumulative impact against the organisation's own caps.

    The cost figure is the **net** cumulative impact of approved change
    requests: that is what the budget actually carries. Article 67, which
    counts gross movements per category, is checked separately and is the
    stricter of the two on a government contract.

    "Above 20%" is strictly greater. Exactly 20% passes with no exception.
    """
    policy = get_policy()
    cost_cap = policy.cost_increase_cap_pct
    time_cap = policy.time_extension_cap_pct

    cost_after = cumulative_cost_before + impact.cost_impact
    days_after = cumulative_days_before + impact.time_impact_days
    duration = Decimal(contract.original_duration_days)

    cost_after_pct = _pct(cost_after, contract.original_value)
    time_after_pct = _pct(Decimal(days_after), duration)

    cost_cap_value = contract.original_value * cost_cap / _HUNDRED
    time_cap_days = duration * time_cap / _HUNDRED

    cost_exceeded = cost_after > cost_cap_value
    time_exceeded = Decimal(days_after) > time_cap_days

    findings: list[str] = []
    if cost_exceeded:
        findings.append(
            f"Cumulative cost increase reaches {cost_after_pct}% of the contract value, "
            f"above the {cost_cap}% policy cap. "
            f"Requires a {policy.policy_exception_role} exception."
        )
    if time_exceeded:
        findings.append(
            f"Cumulative time extension reaches {time_after_pct}% of the contract duration, "
            f"above the {time_cap}% policy cap. "
            f"Requires a {policy.policy_exception_role} exception."
        )
    if not findings:
        findings.append(
            f"Within policy: cost at {cost_after_pct}% and time at {time_after_pct}% "
            f"against {cost_cap}% caps."
        )

    return PolicyCheck(
        cost_before_pct=_pct(cumulative_cost_before, contract.original_value),
        cost_after_pct=cost_after_pct,
        cost_cap_pct=cost_cap,
        cost_exceeded=cost_exceeded,
        time_before_pct=_pct(Decimal(cumulative_days_before), duration),
        time_after_pct=time_after_pct,
        time_cap_pct=time_cap,
        time_exceeded=time_exceeded,
        exception_role=policy.policy_exception_role,
        findings_en=tuple(findings),
    )


def to_ledger_entries(
    request: ChangeRequest,
    kind: ChangeKind,
    impact: CostImpact,
    matched_line_ids: tuple[str, ...],
    now: datetime,
) -> tuple[ChangeOrder, ...]:
    """Map a change request onto Article 67 ledger entries.

    =================  ====================================================
    change kind        ledger entries
    =================  ====================================================
    PCR, new item      NEW_ITEMS                       Article 67(1)(a)
    PCR, existing      INCREASE_EXISTING               Article 67(1)(b)
    NCR                DECREASE_EXISTING               Article 67(1)(c)
    substitution       DECREASE_EXISTING + INCREASE_EXISTING
    in scope           nothing - it is not a change
    =================  ====================================================

    A substitution produces two entries because Article 67 counts gross
    movements per category, not a net figure. The added half is an increase of
    an *existing* line rather than a new item: the line stays, its approved
    product changes.
    """
    if kind in {ChangeKind.IN_SCOPE, ChangeKind.UNCLEAR}:
        # Nothing to put on the ledger: one is not a change, the other is not
        # yet known to be one.
        return ()

    base = {
        "contract_id": request.contract_id,
        "description_ar": request.body_ar[:200],
        "status": OrderStatus.DRAFT,
        "created_at": now,
        "change_request_id": request.id,
        "related_item_ids": matched_line_ids,
    }

    if kind is ChangeKind.PCR:
        category = (
            ChangeCategory.INCREASE_EXISTING if matched_line_ids else ChangeCategory.NEW_ITEMS
        )
        return (
            ChangeOrder(id=f"{request.id}-ADD", type=category, value=impact.added_value, **base),
        )

    if kind is ChangeKind.NCR:
        return (
            ChangeOrder(
                id=f"{request.id}-SUB",
                type=ChangeCategory.DECREASE_EXISTING,
                value=impact.removed_value,
                **base,
            ),
        )

    if kind is ChangeKind.SUBSTITUTION:
        return (
            ChangeOrder(
                id=f"{request.id}-SUB",
                type=ChangeCategory.DECREASE_EXISTING,
                value=impact.removed_value,
                **base,
            ),
            ChangeOrder(
                id=f"{request.id}-ADD",
                type=ChangeCategory.INCREASE_EXISTING,
                value=impact.added_value,
                **base,
            ),
        )

    return ()


@dataclass(frozen=True)
class LegalCheck:
    """Article 67 evaluation, for government contracts only."""

    applies: bool
    results: tuple[RuleResult, ...] = ()
    findings_en: tuple[str, ...] = field(default_factory=tuple)

    @property
    def blocked(self) -> bool:
        """True when any entry breaches a blocking cap."""
        return any(not result.allowed for result in self.results)

    @property
    def requires_contractor_consent(self) -> bool:
        return any(result.requires_contractor_consent for result in self.results)

    @property
    def needs_legal_review(self) -> bool:
        return any(result.needs_legal_review for result in self.results)

    @property
    def article_refs(self) -> tuple[str, ...]:
        refs: list[str] = []
        for result in self.results:
            refs.extend(result.article_refs)
        return tuple(dict.fromkeys(refs))


def check_article_67(
    contract: Contract,
    ledger: ChangeLedger,
    entries: tuple[ChangeOrder, ...],
) -> LegalCheck:
    """Run the existing rules engine over the proposed ledger entries.

    Private contracts skip this entirely: Article 67 governs government
    procurement, and applying it to a private contract would be inventing law.
    """
    if not contract.is_government:
        return LegalCheck(
            applies=False,
            findings_en=("Private contract: Article 67 does not apply.",),
        )
    if not entries:
        return LegalCheck(applies=True, findings_en=("No ledger movement to evaluate.",))

    limits = get_limits()
    results: list[RuleResult] = []
    findings: list[str] = []
    running = ledger

    for entry in entries:
        result = evaluate(contract, running, entry, limits)
        results.append(result)
        for violation in result.blocking_violations:
            findings.append(f"{violation.article_ref_en}: {violation.message_en}")
        for warning in result.warnings:
            findings.append(f"{warning.article_ref_en}: {warning.message_en}")
        # Both halves of a substitution must be seen together, so each entry is
        # provisionally added before the next is evaluated.
        running = ChangeLedger(
            contract_id=running.contract_id,
            orders=(*running.orders, entry.model_copy(update={"status": OrderStatus.APPROVED})),
        )

    if not findings:
        findings.append("Within every Article 67 cap.")

    return LegalCheck(applies=True, results=tuple(results), findings_en=tuple(findings))


def _cap_line(
    scope: str,
    threshold: PolicyThreshold,
    unit: str,
    basis: Decimal,
    used: Decimal,
    pending: Decimal,
) -> CapLine:
    """Turn one configured threshold into a ledger line.

    The cap percentage comes from the policy file, never from Python (NFR-16),
    and headroom is computed from values rather than from rounded percentages -
    the same reason the Article 67 engine compares values.
    """
    cap_pct = threshold.cap_pct
    assert cap_pct is not None  # noqa: S101 - guaranteed by the caller's key
    cap_value = basis * cap_pct / _HUNDRED
    headroom = cap_value - used
    return CapLine(
        scope=scope,
        source=threshold.source,
        blocking=threshold.blocking,
        exception_role=threshold.exception_role,
        unit=unit,
        cap_pct=cap_pct,
        cap_value=cap_value,
        used_value=used,
        used_pct=_pct(used, basis),
        pending_value=pending,
        pending_pct=_pct(pending, basis),
        headroom_value=headroom,
        headroom_pct=_pct(headroom, basis),
        description_ar=threshold.description_ar,
        description_en=threshold.description_en,
    )


def policy_usage(
    contract: Contract,
    cost_used: Decimal,
    days_used: int,
    cost_pending: Decimal,
    days_pending: int,
) -> dict[str, CapLine]:
    """The organisation's own caps as they stand on this contract (FR-10).

    Reported for every contract, government or not: policy applies to both.
    Article 67 is the layer that applies to government contracts only, and it
    is reported separately in ``usage``.
    """
    policy = get_policy()
    duration = Decimal(contract.original_duration_days)
    return {
        "cost_increase": _cap_line(
            "cost_increase",
            policy.thresholds["cost_increase"],
            "SAR",
            contract.original_value,
            cost_used,
            cost_pending,
        ),
        "time_extension": _cap_line(
            "time_extension",
            policy.thresholds["time_extension"],
            "days",
            duration,
            Decimal(days_used),
            Decimal(days_pending),
        ),
    }


def cited_articles(contract: Contract, request: ChangeRequest) -> tuple[str, ...]:
    """The Article 67 references a variation order rests on (NFR-02, FR-12).

    Derived from the categories the request actually moves, with every string
    read from the regulation file. A private contract cites nothing, because
    Article 67 governs government contracts only - and citing it anyway would
    be asserting a legal basis that does not exist.
    """
    if not contract.is_government or request.kind is None:
        return ()

    limits = get_limits()
    refs: list[str] = []
    for category in _categories_for(request.kind, request.matched_line_ids):
        rule = limits.categories[category]
        refs.append(rule.article_ref_en)
        if rule.counts_toward_combined:
            refs.append(limits.combined.article_ref_en)
    # dict.fromkeys keeps first-seen order; a VO should not cite 67(2) twice
    # just because a substitution touches two categories.
    return tuple(dict.fromkeys(refs))


def _categories_for(
    kind: ChangeKind, matched_line_ids: tuple[str, ...]
) -> tuple[ChangeCategory, ...]:
    """The ledger categories one change kind moves.

    The same mapping :func:`to_ledger_entries` applies, stated once so the
    citations and the ledger entries cannot drift apart.
    """
    if kind is ChangeKind.PCR:
        return (ChangeCategory.INCREASE_EXISTING if matched_line_ids else ChangeCategory.NEW_ITEMS,)
    if kind is ChangeKind.NCR:
        return (ChangeCategory.DECREASE_EXISTING,)
    if kind is ChangeKind.SUBSTITUTION:
        return (ChangeCategory.DECREASE_EXISTING, ChangeCategory.INCREASE_EXISTING)
    return ()
