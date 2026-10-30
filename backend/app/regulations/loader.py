"""Loads the regulation file into validated models.

All percentages come from ``gtpl_2026.yaml`` and are parsed with ``Decimal``.
No percentage is ever written in code (NFR-02).
"""

from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import ChangeCategory

REGULATION_PATH = Path(__file__).with_name("gtpl_2026.yaml")

ConsentRule = Literal["always", "above_threshold", "above_cap", "never"]


class ArticleRef(BaseModel):
    """A pointer back to the verbatim legal text."""

    model_config = ConfigDict(frozen=True)

    ref_ar: str
    ref_en: str
    subject: str
    text_ar: str


class CategoryLimit(BaseModel):
    """The rule governing one category of change."""

    model_config = ConfigDict(frozen=True)

    cap_pct: Decimal | None
    cap_is_blocking: bool
    consent_rule: ConsentRule
    consent_threshold_pct: Decimal | None
    counts_toward_combined: bool
    adds_work: bool
    article_ref_ar: str
    article_ref_en: str
    source_phrase_ar: str
    interpretation_note: str | None = None
    needs_legal_review: bool = False


class CombinedLimit(BaseModel):
    """Article 67(2): new items plus increases together."""

    model_config = ConfigDict(frozen=True)

    cap_pct: Decimal
    cap_is_blocking: bool
    members: tuple[ChangeCategory, ...]
    article_ref_ar: str
    article_ref_en: str
    source_phrase_ar: str
    needs_legal_review: bool = False


class FlagOnlyRule(BaseModel):
    """A rule the engine only raises a flag for; it computes nothing."""

    model_config = ConfigDict(frozen=True)

    flag_only: bool
    trigger: str
    article_ref_ar: str
    article_ref_en: str
    note: str
    needs_legal_review: bool = False


class TimeExtensionRule(FlagOnlyRule):
    """Article 72(1): eligibility flag only, never a day count."""


class FinalGuaranteeExemptionRule(FlagOnlyRule):
    """Article 59(2)(z): no final guarantee for assigned additional works."""


class Limits(BaseModel):
    """The structured rule set the engine reads."""

    model_config = ConfigDict(frozen=True)

    currency: str
    basis: str
    comparison_operator: Literal["lte"]
    warning_threshold_ratio: Decimal = Field(gt=0, le=1)
    categories: dict[ChangeCategory, CategoryLimit]
    combined: CombinedLimit
    time_extension: TimeExtensionRule
    final_guarantee_exemption: FinalGuaranteeExemptionRule


class RegulationSource(BaseModel):
    """Provenance of the legal text (NFR-02)."""

    model_config = ConfigDict(frozen=True)

    url: str
    publisher_ar: str
    law_name_ar: str
    law_name_en: str
    publication_date_hijri: str
    publication_date_gregorian: str
    retrieved_at: str
    retrieval_method: str


class Regulation(BaseModel):
    """The whole regulation file."""

    model_config = ConfigDict(frozen=True)

    source: RegulationSource
    effective_date: dict[str, object]
    replaces: dict[str, object]
    articles: dict[str, ArticleRef]
    limits: Limits


def load_regulation(path: Path = REGULATION_PATH) -> Regulation:
    """Parse and validate the regulation YAML."""
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    # dates round-trip from YAML as date objects; keep provenance as plain text
    src = raw["source"]
    for key in ("publication_date_gregorian", "retrieved_at"):
        src[key] = str(src[key])
    return Regulation.model_validate(raw)


@lru_cache(maxsize=1)
def get_regulation() -> Regulation:
    """Return the cached regulation."""
    return load_regulation()


def get_limits() -> Limits:
    """Return just the structured limits the engine needs."""
    return get_regulation().limits
