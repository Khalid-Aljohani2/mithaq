"""Provider selection and the fallback path (FR-19).

Three situations, three behaviours:

===========================  ====================================================
situation                     what happens
===========================  ====================================================
live provider works           its answer is used, ``recorded=False``
live provider fails, text     the recorded answer is used, ``recorded=True``,
  is a seeded demo request    and the UI labels it as recorded
live provider fails, text     a clear error. Nothing is invented.
  is unknown
===========================  ====================================================

The third row is the point. A fallback that quietly guesses on unseen text
would be worse than one that stops: it would look like analysis and carry none
of the evidence.
"""

import logging

from app.analysis.provider import AnalysisError, AnalysisProvider, UnknownRequestError
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
from app.analysis.scripted import ScriptedProvider
from app.config import Settings

logger = logging.getLogger("mithaq.ai")


class NoProviderAvailableError(AnalysisError):
    """Neither the live provider nor a recording could answer."""

    def __init__(self, stage: str, reason: str) -> None:
        super().__init__(
            "NO_PROVIDER_AVAILABLE",
            f"stage {stage} could not be analysed: {reason}. "
            "The live provider is unavailable and there is no recorded answer "
            "for this request text.",
        )
        self.stage = stage


class FallbackProvider(AnalysisProvider):
    """Tries the live provider, falls back to recordings, else fails loudly."""

    name = "anthropic+scripted"
    recorded = False

    def __init__(self, primary: AnalysisProvider, fallback: ScriptedProvider | None = None) -> None:
        self._primary = primary
        self._fallback = fallback or ScriptedProvider()

    def _attempt(self, stage: str, body_ar: str, call_primary, call_fallback):  # noqa: ANN001, ANN202
        try:
            return call_primary()
        except AnalysisError as error:
            logger.warning(
                "ai_fallback",
                extra={
                    "stage": stage,
                    "reason": error.code,
                    "has_recording": self._fallback.knows(body_ar) if body_ar else True,
                },
            )
            try:
                return call_fallback()
            except UnknownRequestError as unknown:
                raise NoProviderAvailableError(stage, error.code) from unknown

    def intake(self, request: IntakeInput) -> IntakeOutput:
        return self._attempt(
            "INTAKE",
            request.body_ar,
            lambda: self._primary.intake(request),
            lambda: self._fallback.intake(request),
        )

    def scope_analysis(self, request: ScopeInput) -> ScopeOutput:
        return self._attempt(
            "SCOPE_ANALYSIS",
            request.body_ar,
            lambda: self._primary.scope_analysis(request),
            lambda: self._fallback.scope_analysis(request),
        )

    def technical_assessment(self, request: TechnicalInput) -> TechnicalOutput:
        return self._attempt(
            "TECHNICAL_ASSESSMENT",
            request.body_ar,
            lambda: self._primary.technical_assessment(request),
            lambda: self._fallback.technical_assessment(request),
        )

    def risk_assessment(self, request: RiskInput) -> RiskOutput:
        return self._attempt(
            "RISK_COMPLIANCE",
            request.body_ar,
            lambda: self._primary.risk_assessment(request),
            lambda: self._fallback.risk_assessment(request),
        )

    def recommendation_narrative(self, request: NarrativeInput) -> NarrativeOutput:
        # The scripted narrative is keyed on the decision, not the text, so it
        # can always answer - prose never blocks a decision that is already made.
        return self._attempt(
            "ORCHESTRATOR",
            "",
            lambda: self._primary.recommendation_narrative(request),
            lambda: self._fallback.recommendation_narrative(request),
        )

    def vo_draft(self, request: VODraftInput) -> VODraftOutput:
        return self._attempt(
            "ISSUE_VO",
            "",
            lambda: self._primary.vo_draft(request),
            lambda: self._fallback.vo_draft(request),
        )


def build_provider(settings: Settings) -> AnalysisProvider:
    """Choose the provider from settings.

    ``LLM_PROVIDER=anthropic`` with a key gives the live provider wrapped in the
    fallback. Anything else gives the scripted provider on its own, which is
    what keeps the whole test suite and the demo working with no key at all.
    """
    if settings.uses_live_provider:
        from app.analysis.anthropic_provider import AnthropicProvider

        logger.info(
            "ai_provider_selected",
            extra={"provider": "anthropic", "model": settings.llm_model, "fallback": "scripted"},
        )
        return FallbackProvider(AnthropicProvider(settings))

    if settings.llm_provider_requested:
        # Asked for, but unusable. Say so once, loudly, at startup rather than
        # letting every request look like a model failure.
        logger.warning(
            "ai_provider_unavailable",
            extra={
                "provider": "anthropic",
                "reason": "LLM_API_KEY is not set",
                "using": "scripted",
            },
        )

    return ScriptedProvider()
