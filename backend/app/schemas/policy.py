"""Request and response models for the policy and evaluation endpoints."""

from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.domain.enums import ImpactType, ThresholdSource


class DocumentChecklist(BaseModel):
    """What one impact type requires before analysis can proceed (FR-04)."""

    model_config = ConfigDict(frozen=True)

    impact_type: ImpactType
    required: list[str]


class RequiredDocumentsResponse(BaseModel):
    """Every checklist, so a requester can see the rule before submitting."""

    model_config = ConfigDict(frozen=True)

    checklists: list[DocumentChecklist]


class PolicyThresholdOut(BaseModel):
    """One configured limit, with the source that says how it can be treated."""

    model_config = ConfigDict(frozen=True)

    key: str
    source: ThresholdSource
    cap_pct: Decimal | None
    cap_value: Decimal | None
    basis: str | None
    blocking: bool
    exception_role: str | None
    description_ar: str
    description_en: str


class EvalStageAccuracy(BaseModel):
    """How one AI stage scored on the evaluation set."""

    model_config = ConfigDict(frozen=True)

    stage: str
    correct: int
    total: int
    accuracy_pct: Decimal


class EvalSummaryResponse(BaseModel):
    """The published evaluation result (FR-20).

    Served from ``docs/eval/summary.json``, which a scored run writes and a
    commit publishes. The API never recomputes it: a number the UI shows must
    be the number that was actually measured, traceable to the commit and the
    prompt versions named here.
    """

    model_config = ConfigDict(frozen=True)

    #: False when no scored run has been published yet. Everything else is then
    #: empty, so the UI can say "not measured" rather than show a zero.
    available: bool
    generated_at: str = ""
    commit: str = ""
    model: str = ""
    split: str = ""
    case_count: int = 0
    prompt_versions: dict[str, str] = {}
    overall_accuracy_pct: Decimal | None = None
    stages: list[EvalStageAccuracy] = []
    latency_p50_ms: int | None = None
    latency_p95_ms: int | None = None
    total_cost_usd: Decimal | None = None
    #: Scored against the audited labels as well, when both were recorded.
    audited_accuracy_pct: Decimal | None = None
    notes: str = ""
