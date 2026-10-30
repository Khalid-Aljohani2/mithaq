"""Deterministic evaluation of change orders against the GTPL 2026 limits.

Pure functions only: no I/O, no database, no network, no clock, no model call.
Give it a contract, a ledger, a proposed order and the limits, and it returns a
``RuleResult``. The same inputs always produce the same output.

Design rules this module exists to enforce:

* Money and percentages are ``Decimal`` end to end (NFR-01).
* Every percentage is read from the regulation file, never written here (NFR-02).
* Comparisons against caps are done on VALUES, not on rounded percentages, so a
  cumulative total sitting exactly on a cap is allowed rather than lost to
  rounding. Percentages are derived afterwards for display only.
* An LLM never reaches this module (NFR-03).
"""

from decimal import Decimal

from app.domain.enums import COMMITTED_STATUSES, PENDING_STATUSES, ChangeCategory, OrderStatus
from app.domain.models import ChangeLedger, ChangeOrder, Contract
from app.domain.rules import (
    COMBINED_SCOPE,
    ConsentRequirement,
    RuleResult,
    UsageSnapshot,
    Violation,
    WarningNote,
)
from app.regulations.loader import CategoryLimit, Limits

_HUNDRED = Decimal("100")
#: Percentages are reported to 4 decimal places; comparisons never use them.
_PCT_EXP = Decimal("0.0001")


def _pct(value: Decimal, base: Decimal) -> Decimal:
    """Express ``value`` as a percentage of ``base``, for display only.

    ``base`` is always ``Contract.original_value``, which the model constrains to
    be greater than zero, so no division-by-zero guard is needed here.
    """
    return (value / base * _HUNDRED).quantize(_PCT_EXP)


def _value_of_pct(pct: Decimal, original_value: Decimal) -> Decimal:
    """Convert a percentage of the contract value into an exact SAR amount."""
    return original_value * pct / _HUNDRED


def _cap_value(cap_pct: Decimal | None, original_value: Decimal) -> Decimal | None:
    """Convert an optional percentage cap into an exact SAR amount."""
    if cap_pct is None:
        return None
    return _value_of_pct(cap_pct, original_value)


def _sum_for(
    ledger: ChangeLedger,
    category: ChangeCategory,
    statuses: frozenset[OrderStatus],
) -> Decimal:
    """Total value of orders in ``category`` whose status is in ``statuses``."""
    return sum(
        (o.value for o in ledger.orders if o.type is category and o.status in statuses),
        Decimal("0"),
    )


def _combined_sum(
    ledger: ChangeLedger,
    limits: Limits,
    statuses: frozenset[OrderStatus],
) -> Decimal:
    """Total across the categories Article 67(2) adds together."""
    return sum(
        (_sum_for(ledger, c, statuses) for c in limits.combined.members),
        Decimal("0"),
    )


def _snapshot(
    scope: str,
    cap_pct: Decimal | None,
    before: Decimal,
    delta: Decimal,
    pending: Decimal,
    original_value: Decimal,
) -> UsageSnapshot:
    """Build the before/after picture for one scope."""
    after = before + delta
    cap_value = _cap_value(cap_pct, original_value)
    headroom_value = None if cap_value is None else cap_value - after
    return UsageSnapshot(
        scope=scope,
        cap_pct=cap_pct,
        cap_value=cap_value,
        before_value=before,
        before_pct=_pct(before, original_value),
        after_value=after,
        after_pct=_pct(after, original_value),
        pending_value=pending,
        pending_pct=_pct(pending, original_value),
        headroom_value=headroom_value,
        headroom_pct=None if headroom_value is None else _pct(headroom_value, original_value),
    )


def _violation(
    scope: str,
    snapshot: UsageSnapshot,
    cap_pct: Decimal,
    cap_value: Decimal,
    ref_ar: str,
    ref_en: str,
) -> Violation:
    """Describe a cap that the proposed order would breach."""
    excess = snapshot.after_value - cap_value
    return Violation(
        code=f"{scope}_CAP_EXCEEDED",
        scope=scope,
        message_ar=(
            f"تجاوز الحد النظامي: النسبة التراكمية بعد هذا الأمر {snapshot.after_pct}% "
            f"وتتجاوز الحد المسموح {cap_pct}%، بزيادة قدرها {excess} ريال."
        ),
        message_en=(
            f"Cap exceeded: cumulative usage after this order is {snapshot.after_pct}%, "
            f"above the {cap_pct}% limit, by {excess} SAR."
        ),
        cap_pct=cap_pct,
        attempted_pct=snapshot.after_pct,
        excess_value=excess,
        article_ref_ar=ref_ar,
        article_ref_en=ref_en,
    )


def _warning(
    scope: str,
    snapshot: UsageSnapshot,
    cap_pct: Decimal,
    threshold_pct: Decimal,
    ref_ar: str,
    ref_en: str,
) -> WarningNote:
    """Describe a cap the contract is approaching but has not breached."""
    return WarningNote(
        code=f"{scope}_APPROACHING_CAP",
        scope=scope,
        message_ar=(
            f"اقتراب من الحد النظامي: النسبة التراكمية بعد هذا الأمر {snapshot.after_pct}% "
            f"من أصل حد {cap_pct}%."
        ),
        message_en=(
            f"Approaching the cap: cumulative usage after this order is "
            f"{snapshot.after_pct}% of a {cap_pct}% limit."
        ),
        threshold_pct=threshold_pct,
        current_pct=snapshot.after_pct,
        cap_pct=cap_pct,
        article_ref_ar=ref_ar,
        article_ref_en=ref_en,
    )


def _consent_for_category(
    category: ChangeCategory,
    rule: CategoryLimit,
    snapshot: UsageSnapshot,
    original_value: Decimal,
) -> ConsentRequirement | None:
    """Decide whether this category needs contractor consent, and for how much."""
    scope = category.value

    if rule.consent_rule == "always":
        return ConsentRequirement(
            code=f"{scope}_CONSENT_ALWAYS",
            scope=scope,
            message_ar="تتطلب هذه الفئة موافقة المتعاقد معه وفقًا للمادة المشار إليها.",
            message_en="This category always requires the contractor's consent.",
            portion_requiring_consent=snapshot.after_value - snapshot.before_value,
            article_ref_ar=rule.article_ref_ar,
            article_ref_en=rule.article_ref_en,
        )

    threshold_pct = rule.consent_threshold_pct
    if rule.consent_rule in {"above_threshold", "above_cap"} and threshold_pct is not None:
        threshold_value = _value_of_pct(threshold_pct, original_value)
        if snapshot.after_value > threshold_value:
            portion = snapshot.after_value - max(threshold_value, snapshot.before_value)
            return ConsentRequirement(
                code=f"{scope}_CONSENT_ABOVE_{threshold_pct}",
                scope=scope,
                message_ar=(
                    f"تتطلب موافقة المتعاقد معه على الجزء الذي يتجاوز {threshold_pct}% "
                    f"من قيمة العقد، وقدره {portion} ريال."
                ),
                message_en=(
                    f"Contractor consent is required for the portion above {threshold_pct}% "
                    f"of the contract value, which is {portion} SAR."
                ),
                portion_requiring_consent=portion,
                article_ref_ar=rule.article_ref_ar,
                article_ref_en=rule.article_ref_en,
            )
    return None


def _check_cap(
    scope: str,
    snapshot: UsageSnapshot,
    cap_pct: Decimal,
    cap_is_blocking: bool,
    warning_ratio: Decimal,
    original_value: Decimal,
    ref_ar: str,
    ref_en: str,
) -> tuple[Violation | None, WarningNote | None]:
    """Compare a snapshot against one cap.

    "Not exceeding" is ``<=``: a cumulative total exactly on the cap is allowed,
    only a strictly greater total is a breach.
    """
    cap_value = _value_of_pct(cap_pct, original_value)
    if snapshot.after_value > cap_value:
        if cap_is_blocking:
            return _violation(scope, snapshot, cap_pct, cap_value, ref_ar, ref_en), None
        return None, None

    threshold_pct = (cap_pct * warning_ratio).quantize(_PCT_EXP)
    if snapshot.after_value >= _value_of_pct(threshold_pct, original_value):
        return None, _warning(scope, snapshot, cap_pct, threshold_pct, ref_ar, ref_en)
    return None, None


def summarise(contract: Contract, ledger: ChangeLedger, limits: Limits) -> dict[str, UsageSnapshot]:
    """Cumulative usage of the ledger as it stands, with no proposed order.

    Feeds the ledger dashboard: approved value per scope, what is still pending,
    and the remaining headroom in SAR.
    """
    original_value = contract.original_value
    usage: dict[str, UsageSnapshot] = {}

    for cat, cat_rule in limits.categories.items():
        usage[cat.value] = _snapshot(
            scope=cat.value,
            cap_pct=cat_rule.cap_pct,
            before=_sum_for(ledger, cat, COMMITTED_STATUSES),
            delta=Decimal("0"),
            pending=_sum_for(ledger, cat, PENDING_STATUSES),
            original_value=original_value,
        )

    usage[COMBINED_SCOPE] = _snapshot(
        scope=COMBINED_SCOPE,
        cap_pct=limits.combined.cap_pct,
        before=_combined_sum(ledger, limits, COMMITTED_STATUSES),
        delta=Decimal("0"),
        pending=_combined_sum(ledger, limits, PENDING_STATUSES),
        original_value=original_value,
    )
    return usage


def evaluate(
    contract: Contract,
    ledger: ChangeLedger,
    proposed_order: ChangeOrder,
    limits: Limits,
) -> RuleResult:
    """Evaluate ``proposed_order`` against the cumulative ``ledger``.

    Only APPROVED orders count toward cumulative totals. Orders awaiting consent
    or approval are reported separately in each snapshot's ``pending_value`` as
    "committed if approved", and never silently consume headroom.

    If ``proposed_order`` is already recorded in ``ledger`` (the re-check run at
    approval time) it is excluded first so it is not counted against itself.
    """
    original_value = contract.original_value
    base_ledger = ledger.excluding(proposed_order.id)
    category = proposed_order.type
    rule = limits.categories[category]
    delta = proposed_order.value

    usage: dict[str, UsageSnapshot] = {}
    violations: list[Violation] = []
    warnings: list[WarningNote] = []
    consents: list[ConsentRequirement] = []
    refs: list[str] = []

    # Snapshot every capped category plus the proposed one, so the caller always
    # sees the whole picture rather than just the scope that happened to trip.
    for cat, cat_rule in limits.categories.items():
        if cat_rule.cap_pct is None and cat is not category:
            continue
        usage[cat.value] = _snapshot(
            scope=cat.value,
            cap_pct=cat_rule.cap_pct,
            before=_sum_for(base_ledger, cat, COMMITTED_STATUSES),
            delta=delta if cat is category else Decimal("0"),
            pending=_sum_for(base_ledger, cat, PENDING_STATUSES),
            original_value=original_value,
        )

    # ---- the proposed order's own category ----
    snapshot = usage[category.value]
    refs.append(rule.article_ref_en)

    if rule.cap_pct is not None:
        violation, warning = _check_cap(
            scope=category.value,
            snapshot=snapshot,
            cap_pct=rule.cap_pct,
            cap_is_blocking=rule.cap_is_blocking,
            warning_ratio=limits.warning_threshold_ratio,
            original_value=original_value,
            ref_ar=rule.article_ref_ar,
            ref_en=rule.article_ref_en,
        )
        if violation is not None:
            violations.append(violation)
        if warning is not None:
            warnings.append(warning)

    consent = _consent_for_category(category, rule, snapshot, original_value)
    if consent is not None:
        consents.append(consent)

    # ---- Article 67(2): new items and increases together ----
    combined = limits.combined
    combined_snapshot = _snapshot(
        scope=COMBINED_SCOPE,
        cap_pct=combined.cap_pct,
        before=_combined_sum(base_ledger, limits, COMMITTED_STATUSES),
        delta=delta if rule.counts_toward_combined else Decimal("0"),
        pending=_combined_sum(base_ledger, limits, PENDING_STATUSES),
        original_value=original_value,
    )
    usage[COMBINED_SCOPE] = combined_snapshot

    if rule.counts_toward_combined:
        refs.append(combined.article_ref_en)
        violation, warning = _check_cap(
            scope=COMBINED_SCOPE,
            snapshot=combined_snapshot,
            cap_pct=combined.cap_pct,
            cap_is_blocking=combined.cap_is_blocking,
            warning_ratio=limits.warning_threshold_ratio,
            original_value=original_value,
            ref_ar=combined.article_ref_ar,
            ref_en=combined.article_ref_en,
        )
        if violation is not None:
            violations.append(violation)
        if warning is not None:
            warnings.append(warning)

    # ---- Flags only: the engine raises them, it computes nothing ----
    # Article 72(1) time extension and Article 59(2)(z) final-guarantee exemption
    # share one trigger: an allowed order that adds work.
    allowed = not violations
    adds_work = allowed and rule.adds_work
    if adds_work:
        refs.append(limits.time_extension.article_ref_en)
        refs.append(limits.final_guarantee_exemption.article_ref_en)

    return RuleResult(
        allowed=allowed,
        requires_contractor_consent=bool(consents),
        consent_requirements=tuple(consents),
        blocking_violations=tuple(violations),
        warnings=tuple(warnings),
        usage=usage,
        eligible_for_time_extension=adds_work,
        exempt_from_final_guarantee=adds_work,
        article_refs=tuple(dict.fromkeys(refs)),
        needs_legal_review=rule.needs_legal_review,
    )
