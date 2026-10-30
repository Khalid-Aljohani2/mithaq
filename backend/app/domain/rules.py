"""Result types produced by the rules engine.

Every finding carries the article it came from (NFR-02).
"""

from decimal import Decimal

from pydantic import BaseModel, ConfigDict

COMBINED_SCOPE = "COMBINED"


class UsageSnapshot(BaseModel):
    """Cumulative usage for one scope, before and after the proposed order."""

    model_config = ConfigDict(frozen=True)

    scope: str
    cap_pct: Decimal | None
    cap_value: Decimal | None
    before_value: Decimal
    before_pct: Decimal
    after_value: Decimal
    after_pct: Decimal
    #: Value sitting in PENDING_* orders - committed only if they are approved.
    pending_value: Decimal
    pending_pct: Decimal
    headroom_value: Decimal | None
    headroom_pct: Decimal | None


class Violation(BaseModel):
    """A blocking breach of a cap."""

    model_config = ConfigDict(frozen=True)

    code: str
    scope: str
    message_ar: str
    message_en: str
    cap_pct: Decimal
    attempted_pct: Decimal
    excess_value: Decimal
    article_ref_ar: str
    article_ref_en: str


class WarningNote(BaseModel):
    """Still allowed, but close to a cap."""

    model_config = ConfigDict(frozen=True)

    code: str
    scope: str
    message_ar: str
    message_en: str
    threshold_pct: Decimal
    current_pct: Decimal
    cap_pct: Decimal
    article_ref_ar: str
    article_ref_en: str


class ConsentRequirement(BaseModel):
    """Contractor consent the law requires before this order can proceed."""

    model_config = ConfigDict(frozen=True)

    code: str
    scope: str
    message_ar: str
    message_en: str
    portion_requiring_consent: Decimal
    article_ref_ar: str
    article_ref_en: str


class RuleResult(BaseModel):
    """The deterministic verdict on one proposed change order.

    Produced only by code reading ``gtpl_2026.yaml``. No model output ever
    contributes to any field here (NFR-03).
    """

    model_config = ConfigDict(frozen=True)

    allowed: bool
    requires_contractor_consent: bool
    consent_requirements: tuple[ConsentRequirement, ...]
    blocking_violations: tuple[Violation, ...]
    warnings: tuple[WarningNote, ...]
    #: Keyed by category name plus "COMBINED".
    usage: dict[str, UsageSnapshot]
    eligible_for_time_extension: bool
    #: Article 59(2)(z): no final guarantee is required for additional works.
    exempt_from_final_guarantee: bool
    article_refs: tuple[str, ...]
    #: True when any rule applied here is flagged for legal review.
    needs_legal_review: bool
