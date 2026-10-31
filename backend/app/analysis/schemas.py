"""Input and output schemas for the AI stages (NFR-03).

Every model output is validated against one of these before anything reads it.
Nothing here carries money, a percentage or a state: an AI stage reports what
the text *says*, and deterministic code decides what that *costs* and what
happens next (NFR-15).

Note what the output types deliberately do NOT contain: no cost, no cumulative
percentage, no approval status, no next state. A provider cannot return those
because there is nowhere to put them.
"""

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import ChangeKind, ImpactType

RiskLevel = Literal["LOW", "MEDIUM", "HIGH"]


class AIOutput(BaseModel):
    """Common envelope on every AI stage result."""

    model_config = ConfigDict(frozen=True)

    #: Which provider produced this, e.g. "scripted".
    provider: str
    #: True when it came from recorded data rather than a live model (FR-19).
    #: The UI must label these as recorded.
    recorded: bool
    #: 0 to 1. Below the configured threshold the orchestrator asks a human.
    confidence: Decimal = Field(ge=0, le=1)


# ---------------------------------------------------------------------------
# Stage 1 - Intake (FR-03)
# ---------------------------------------------------------------------------


class IntakeInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    cr_id: str
    body_ar: str
    attachments: tuple[str, ...] = ()
    contract_title_ar: str = ""


class IntakeOutput(AIOutput):
    """What the request asks for, pulled out of free Arabic prose."""

    requester_name_ar: str
    requested_change_ar: str
    impact_type: ImpactType
    #: The exact phrase from the request supporting the reading (NFR-04: the
    #: request is data, and a quote is checkable against it).
    quoted_phrase_ar: str


# ---------------------------------------------------------------------------
# Stage 3 - Contract and scope analysis (FR-05)
# ---------------------------------------------------------------------------


class BreakdownLineView(BaseModel):
    """The read-only view of a breakdown line handed to a model."""

    model_config = ConfigDict(frozen=True)

    id: str
    description_ar: str
    unit_ar: str
    approved_product_ar: str | None = None
    restrictions_ar: tuple[str, ...] = ()


class ScopeInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    cr_id: str
    body_ar: str
    breakdown: tuple[BreakdownLineView, ...]


class ScopeOutput(AIOutput):
    """Explicit yes or no on whether the request is already in scope."""

    in_scope: bool
    kind: ChangeKind
    matched_line_ids: tuple[str, ...] = ()
    #: Quantity added or removed, in the matched line's unit. Code prices it.
    quantity_delta: Decimal | None = None
    #: For a substitution: what replaces the approved product.
    substitute_product_ar: str | None = None
    quoted_phrase_ar: str = ""
    reasoning_ar: str = ""


# ---------------------------------------------------------------------------
# Stage 4 - Technical assessment (FR-06)
# ---------------------------------------------------------------------------


class TechnicalInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    cr_id: str
    body_ar: str
    affected_lines: tuple[BreakdownLineView, ...]


class TechnicalOutput(AIOutput):
    """Whether an approved product or specification is being changed."""

    changes_approved_product: bool
    affected_line_ids: tuple[str, ...] = ()
    #: Restrictions the request appears to conflict with, quoted.
    restriction_conflicts_ar: tuple[str, ...] = ()
    reasoning_ar: str = ""


# ---------------------------------------------------------------------------
# Stage 6 - Risk and compliance (FR-08)
# ---------------------------------------------------------------------------


class RiskInput(BaseModel):
    """Note the computed findings are *inputs* here.

    The legal and policy results are produced by code in stages 5 and 6 and
    handed to the model to describe. The model does not compute them.
    """

    model_config = ConfigDict(frozen=True)

    cr_id: str
    body_ar: str
    kind: ChangeKind
    cost_impact: Decimal | None = None
    time_impact_days: int | None = None
    legal_findings_en: tuple[str, ...] = ()
    policy_findings_en: tuple[str, ...] = ()


class RiskOutput(AIOutput):
    delivery_risk_ar: str = ""
    operational_risk_ar: str = ""
    commercial_risk_ar: str = ""
    compliance_risk_ar: str = ""
    overall_risk_level: RiskLevel = "LOW"


# ---------------------------------------------------------------------------
# Stage 7 - Orchestrator narrative (FR-09)
# ---------------------------------------------------------------------------


class NarrativeInput(BaseModel):
    """The decision is already made when this is called.

    Code produces the recommendation, the reasons and the chain; the model only
    turns them into readable Arabic. A missing narrative degrades the wording,
    never the decision.
    """

    model_config = ConfigDict(frozen=True)

    cr_id: str
    recommendation: str
    reason_codes: tuple[str, ...] = ()
    cost_impact: Decimal | None = None
    time_impact_days: int | None = None
    chain_roles: tuple[str, ...] = ()


class NarrativeOutput(AIOutput):
    """Arabic and English prose about the same decision, from one call.

    The English fields mirror the Arabic ones item for item, so an English
    reader sees the same explanation and never a second opinion.
    """

    summary_ar: str = ""
    reasons_ar: tuple[str, ...] = ()
    next_actions_ar: tuple[str, ...] = ()
    summary_en: str = ""
    reasons_en: tuple[str, ...] = ()
    next_actions_en: tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# Stage 9 - Variation order drafting (FR-12)
# ---------------------------------------------------------------------------


class VODraftInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    cr_id: str
    contract_title_ar: str
    requested_change_ar: str
    cited_line_ids: tuple[str, ...] = ()


class VODraftOutput(AIOutput):
    """Only prose. The value, duration and citations are computed."""

    scope_ar: str = ""
    #: English rendering of the same paragraph. The Arabic stays the formal text.
    scope_en: str = ""
