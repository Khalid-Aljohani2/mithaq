"""Replays recorded AI outputs for the seeded demo requests.

Serves two purposes at once:

* it is how Step 4A runs the pipeline with no live model at all;
* it is the fallback mode of FR-19, used when the provider is unreachable.

Every output it returns carries ``recorded=True`` so the UI can label it. For
any text it does not have a recording of, it raises
:class:`~app.analysis.provider.UnknownRequestError` rather than inventing an
answer - a fallback that quietly guesses would be worse than one that stops.
"""

from app.analysis.provider import AnalysisProvider, UnknownRequestError
from app.analysis.recorded.demo_outputs import (
    PROVIDER_NAME,
    RECORDINGS,
    narrative_for,
    vo_scope_for,
)
from app.analysis.schemas import (
    IntakeInput,
    IntakeOutput,
    NarrativeInput,
    NarrativeOutput,
    RiskInput,
    RiskOutput,
    ScopeInput,
    ScopeOutput,
    TechnicalInput,
    TechnicalOutput,
    VODraftInput,
    VODraftOutput,
)
from app.domain.change_request import text_fingerprint
from app.domain.enums import Stage


class ScriptedProvider(AnalysisProvider):
    """Looks recordings up by a stable hash of the request text."""

    name = PROVIDER_NAME
    recorded = True

    def __init__(self, recordings: dict[str, dict[Stage, object]] | None = None) -> None:
        self._recordings = RECORDINGS if recordings is None else recordings

    def knows(self, body_ar: str) -> bool:
        """True when a recording exists for this text."""
        return text_fingerprint(body_ar) in self._recordings

    def _lookup(self, body_ar: str, stage: Stage) -> object:
        fingerprint = text_fingerprint(body_ar)
        recording = self._recordings.get(fingerprint)
        if recording is None or stage not in recording:
            raise UnknownRequestError(fingerprint, stage.value)
        return recording[stage]

    def intake(self, request: IntakeInput) -> IntakeOutput:
        result = self._lookup(request.body_ar, Stage.INTAKE)
        assert isinstance(result, IntakeOutput)  # noqa: S101 - recordings are typed
        return result

    def scope_analysis(self, request: ScopeInput) -> ScopeOutput:
        result = self._lookup(request.body_ar, Stage.SCOPE_ANALYSIS)
        assert isinstance(result, ScopeOutput)  # noqa: S101
        return result

    def technical_assessment(self, request: TechnicalInput) -> TechnicalOutput:
        result = self._lookup(request.body_ar, Stage.TECHNICAL_ASSESSMENT)
        assert isinstance(result, TechnicalOutput)  # noqa: S101
        return result

    def risk_assessment(self, request: RiskInput) -> RiskOutput:
        result = self._lookup(request.body_ar, Stage.RISK_COMPLIANCE)
        assert isinstance(result, RiskOutput)  # noqa: S101
        return result

    def recommendation_narrative(self, request: NarrativeInput) -> NarrativeOutput:
        """Keyed on the decision, which code has already made."""
        return narrative_for(request.recommendation, request.reason_codes)

    def vo_draft(self, request: VODraftInput) -> VODraftOutput:
        return vo_scope_for(request.requested_change_ar)
