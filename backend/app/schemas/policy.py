"""Request and response models for the policy and evaluation endpoints."""

from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.domain.enums import ImpactType, ThresholdSource


class DocumentChecklist(BaseModel):
    """What one impact type requires before analysis can proceed (FR-04)."""

    model_config = ConfigDict(frozen=True)

    impact_type: ImpactType
    required: list[str]


class DocumentName(BaseModel):
    """One checklist document: a stable code and its name in each language."""

    model_config = ConfigDict(frozen=True)

    code: str
    name_ar: str
    name_en: str


class RequiredDocumentsResponse(BaseModel):
    """Every checklist, so a requester can see the rule before submitting."""

    model_config = ConfigDict(frozen=True)

    checklists: list[DocumentChecklist]
    #: Names of every document the checklists use, so the UI can show them in
    #: the interface language.
    documents: list[DocumentName]


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


class EvalFieldAccuracy(BaseModel):
    """How one labelled field scored, under both label sets.

    Per *field*, not per stage: the evaluation labels five fields
    (in_scope, kind, matched_line_ids, changes_approved_product,
    recommendation), and several of them come from the same stage.
    """

    model_config = ConfigDict(frozen=True)

    field: str
    accuracy_pct: Decimal
    #: The same field scored against the audited labels
    #: (docs/eval_label_audit.md). Equal to ``accuracy_pct`` when the audit
    #: touched nothing that this field scores.
    audited_accuracy_pct: Decimal


class EvalStageLatency(BaseModel):
    """Wall time for one pipeline stage, over the cases that reached it."""

    model_config = ConfigDict(frozen=True)

    stage: str
    median_ms: Decimal
    p95_ms: Decimal
    cases: int


class EvalSummaryResponse(BaseModel):
    """The published evaluation result (FR-20).

    Served from ``docs/eval/summary.json``, which a scored run writes and a
    commit publishes. The API never recomputes it: a number the UI shows must
    be the number that was actually measured, traceable to the commit, the
    prompt versions and the label audit named here.
    """

    model_config = ConfigDict(frozen=True)

    #: False when no scored run has been published yet. Everything else is then
    #: empty, so the UI can say "not measured" rather than show a zero.
    available: bool
    generated_at: str = ""
    #: The commit the measured code was at. Traceability starts here.
    commit: str = ""
    model: str = ""
    split: str = ""
    provider: str = ""
    case_count: int = 0
    #: How many cases the dev split holds. Published beside the test count so a
    #: reader can see the split discipline the numbers rest on: prompts were
    #: tuned on these and the test split was not opened until they were final.
    dev_case_count: int = 0
    prompt_versions: dict[str, str] = {}
    #: Recommendation accuracy under the original labels - the headline figure.
    overall_accuracy_pct: Decimal | None = None
    #: The same figure under the audited labels, published beside it rather
    #: than instead of it (docs/eval_label_audit.md).
    audited_accuracy_pct: Decimal | None = None
    #: Case ids whose labels the audit corrected, so the gap can be attributed.
    audited_case_ids: list[str] = []
    fields: list[EvalFieldAccuracy] = []
    stage_latency: list[EvalStageLatency] = []
    latency_p50_ms: Decimal | None = None
    latency_p95_ms: Decimal | None = None
    total_cost_usd: Decimal | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    injection_passed: int = 0
    injection_total: int = 0
    errors: int = 0
    notes: str = ""
