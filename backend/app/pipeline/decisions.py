"""Stage 7 - the orchestrator's decision rules (FR-09). Deterministic code.

This module decides. The model's only job at stage 7 is to turn what is decided
here into readable Arabic, and a missing narrative changes the wording and
nothing else (NFR-15).

Rules are ordered by severity: the first that matches wins, so a legally
blocked request cannot be recommended for approval because some later rule was
more cheerful about it.
"""

from dataclasses import dataclass, field
from decimal import Decimal

from app.analysis.schemas import ScopeOutput, TechnicalOutput
from app.domain.enums import ChangeKind, Recommendation
from app.pipeline.costing import CostImpact
from app.pipeline.documents import DocumentCheck
from app.pipeline.limits import LegalCheck, PolicyCheck
from app.policy.loader import get_policy


@dataclass(frozen=True)
class Decision:
    """What stage 7 concluded, before anyone wrote prose about it."""

    recommendation: Recommendation
    reason_codes: tuple[str, ...]
    confidence: Decimal
    #: Disagreements between stages, surfaced rather than silently resolved.
    conflicts: tuple[str, ...] = field(default_factory=tuple)
    #: Set when a legal cap is breached: no internal approval can lift it.
    legally_blocked: bool = False
    policy_exception_required: bool = False
    needs_legal_review: bool = False


def detect_conflicts(
    scope: ScopeOutput,
    technical: TechnicalOutput,
    impact: CostImpact,
    documents: DocumentCheck,
) -> tuple[str, ...]:
    """Flag stages that disagree with each other (FR-09).

    These are real inconsistencies, not stylistic ones, and each means a human
    should look before anything is approved.
    """
    conflicts: list[str] = []

    if scope.in_scope and impact.cost_impact != 0:
        conflicts.append(
            "CONFLICT_IN_SCOPE_WITH_COST: stage 3 called the request in scope but stage 5 "
            f"priced it at {impact.cost_impact}."
        )
    if technical.changes_approved_product and scope.kind is ChangeKind.IN_SCOPE:
        conflicts.append(
            "CONFLICT_PRODUCT_CHANGE_IN_SCOPE: stage 4 found an approved product being "
            "changed, which cannot be in scope."
        )
    if scope.kind is ChangeKind.SUBSTITUTION and not technical.changes_approved_product:
        conflicts.append(
            "CONFLICT_SUBSTITUTION_WITHOUT_PRODUCT_CHANGE: stage 3 classified a "
            "substitution but stage 4 found no approved product being changed."
        )
    if technical.restriction_conflicts_ar:
        conflicts.append(
            "CONFLICT_RESTRICTION: the request appears to breach a contract restriction: "
            + "; ".join(technical.restriction_conflicts_ar)
        )
    if not documents.complete:
        conflicts.append(
            "CONFLICT_DOCUMENTS_INCOMPLETE: analysis ran while documents were still missing."
        )
    return tuple(conflicts)


def decide(
    scope: ScopeOutput,
    technical: TechnicalOutput,
    impact: CostImpact,
    documents: DocumentCheck,
    policy: PolicyCheck,
    legal: LegalCheck,
    confidences: tuple[Decimal, ...],
) -> Decision:
    """Apply the decision rules in severity order."""
    minimum = get_policy().minimum_confidence
    # The weakest link: one uncertain stage makes the whole reading uncertain.
    confidence = min(confidences) if confidences else Decimal("0")
    conflicts = detect_conflicts(scope, technical, impact, documents)

    needs_legal_review = legal.applies and legal.needs_legal_review
    blocked = legal.blocked
    exception_required = policy.exception_required

    reasons: list[str] = []

    # 1. Documents first: nothing should be judged on an incomplete file.
    if not documents.complete:
        return Decision(
            recommendation=Recommendation.REQUEST_REVISION,
            reason_codes=("DOCUMENTS_MISSING",),
            confidence=confidence,
            conflicts=conflicts,
            needs_legal_review=needs_legal_review,
        )

    # 2. A legal cap is blocking and no internal approval lifts it.
    if blocked:
        reasons.append("LEGAL_CAP_EXCEEDED")
        if exception_required:
            reasons.append("POLICY_EXCEPTION_CANNOT_LIFT_LEGAL_CAP")
        return Decision(
            recommendation=Recommendation.REJECT,
            reason_codes=tuple(reasons),
            confidence=confidence,
            conflicts=conflicts,
            legally_blocked=True,
            policy_exception_required=exception_required,
            needs_legal_review=True,
        )

    # 3. The request is already covered by the contract.
    if scope.in_scope and scope.kind is ChangeKind.IN_SCOPE:
        return Decision(
            recommendation=Recommendation.CLOSE_IN_SCOPE,
            reason_codes=("IN_SCOPE",),
            confidence=confidence,
            conflicts=conflicts,
        )

    # 4. The analysis is not confident enough, or could not classify it.
    if scope.kind is ChangeKind.UNCLEAR or confidence < minimum:
        return Decision(
            recommendation=Recommendation.REQUEST_REVISION,
            reason_codes=("LOW_CONFIDENCE",),
            confidence=confidence,
            conflicts=conflicts,
            needs_legal_review=needs_legal_review,
        )

    # 5. The request could not be priced. Approving a change whose value
    #    nobody can state would be approving a blank cheque.
    if impact.unpriceable:
        return Decision(
            recommendation=Recommendation.REQUEST_REVISION,
            reason_codes=("CANNOT_PRICE",),
            confidence=confidence,
            conflicts=conflicts,
            needs_legal_review=needs_legal_review,
        )

    # 6. Stages disagree. A human looks before anything is approved.
    if conflicts:
        return Decision(
            recommendation=Recommendation.REQUEST_REVISION,
            reason_codes=("STAGE_CONFLICT",),
            confidence=confidence,
            conflicts=conflicts,
            policy_exception_required=exception_required,
            needs_legal_review=needs_legal_review,
        )

    # 7. Approvable. The reasons say what the chain will have to cover.
    if exception_required:
        reasons.append("POLICY_EXCEPTION_REQUIRED")
    else:
        reasons.append("WITHIN_ALL_LIMITS")
    if technical.changes_approved_product:
        reasons.append("TECHNICAL_APPROVAL_REQUIRED")
    if impact.unit_rate_flagged:
        reasons.append("UNIT_RATE_DEVIATION")
    if impact.rate_human_entered:
        reasons.append("NEW_ITEM_RATE_HUMAN_ENTERED")
    if needs_legal_review:
        reasons.append("LEGAL_REVIEW_REQUIRED")

    return Decision(
        recommendation=Recommendation.APPROVE,
        reason_codes=tuple(reasons),
        confidence=confidence,
        conflicts=conflicts,
        policy_exception_required=exception_required,
        needs_legal_review=needs_legal_review,
    )
