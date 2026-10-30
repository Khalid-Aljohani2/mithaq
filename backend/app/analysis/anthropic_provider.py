"""The live Anthropic provider.

Sits behind the same :class:`~app.analysis.provider.AnalysisProvider` interface
as the scripted one, so nothing above it changes when the model does.

Three properties carry the requirements:

* **Schema-valid output (NFR-03).** Every call uses ``client.messages.parse``
  with the stage's Pydantic schema as ``output_format``, which is the documented
  way to get structured output. A response that still fails validation is
  retried exactly once, then the stage is marked failed and the change request
  goes to a human with the error attached - it is never guessed past.
* **Request text is data (NFR-04).** The request is wrapped in markers by
  ``app.prompts.wrap_request`` and the system prompt states that everything
  inside them is data. The provider never concatenates request text into the
  system prompt.
* **Observability (NFR-12).** Every call logs stage, model, latency, token
  counts and validation result. It never logs the API key or a full request
  body.
"""

import logging
import time
from functools import cache
from typing import TypeVar

import anthropic
from pydantic import BaseModel, ValidationError, create_model

from app.analysis.provider import AnalysisError, AnalysisProvider
from app.analysis.schemas import (
    AIOutput,
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
from app.config import Settings
from app.prompts import load_prompt, prompt_version, wrap_request

logger = logging.getLogger("mithaq.ai")

TOutput = TypeVar("TOutput", bound=AIOutput)

PROVIDER_NAME = "anthropic"

#: Fields the system owns, not the model. Asking a model to emit these wastes
#: output tokens and invites nonsense - an early run came back with
#: "provider": "scope_analysis" - so they are stripped from the schema the
#: model sees and set from code afterwards.
_ENVELOPE_FIELDS = ("provider", "recorded")


@cache
def payload_schema(output_type: type[BaseModel]) -> type[BaseModel]:
    """Derive the model-facing schema: the stage output minus the envelope.

    Derived rather than hand-written so it cannot drift from the real schema
    when a field is added.
    """
    fields = {
        name: (field.annotation, field)
        for name, field in output_type.model_fields.items()
        if name not in _ENVELOPE_FIELDS
    }
    return create_model(f"{output_type.__name__}Payload", **fields)  # type: ignore[call-overload]


class ProviderCallFailedError(AnalysisError):
    """The model could not produce a schema-valid result after one retry."""

    def __init__(self, stage: str, detail: str) -> None:
        super().__init__(
            "AI_STAGE_FAILED",
            f"stage {stage} did not return a valid result after one retry: {detail}",
        )
        self.stage = stage


class AnthropicProvider(AnalysisProvider):
    """Calls Claude for the four AI stages and the two prose helpers."""

    name = PROVIDER_NAME
    recorded = False

    def __init__(self, settings: Settings, client: anthropic.Anthropic | None = None) -> None:
        self._settings = settings
        # Injected in tests so no network is touched.
        self._client = client or anthropic.Anthropic(
            api_key=settings.llm_api_key,
            timeout=settings.llm_timeout_seconds,
            max_retries=settings.llm_max_retries,
        )

    # -- internals ---------------------------------------------------------

    def _call(
        self,
        stage: str,
        payload: BaseModel,
        request_text: str,
        output_type: type[TOutput],
        extra_context: str = "",
    ) -> TOutput:
        """Run one stage, validating against its schema and retrying once.

        The retry is deliberately a plain repeat rather than a "you got it
        wrong, try again" follow-up: a second attempt that carries the broken
        first attempt in its context tends to repeat it.
        """
        system = load_prompt(stage)
        model = self._settings.model_for(stage)
        user_content = self._user_content(payload, request_text, extra_context)

        last_error: Exception | None = None
        for attempt in (1, 2):
            started = time.perf_counter()
            try:
                response = self._client.messages.parse(
                    model=model,
                    max_tokens=self._settings.llm_max_tokens,
                    system=system,
                    messages=[{"role": "user", "content": user_content}],
                    output_format=payload_schema(output_type),
                    **self._effort_kwargs(),
                )
            except ValidationError as error:
                # The SDK validates inside parse(), so a truncated or malformed
                # response raises here rather than returning. Without this the
                # retry path below would never run for the likeliest failure.
                latency_ms = int((time.perf_counter() - started) * 1000)
                last_error = error
                self._log(stage, model, latency_ms, None, "unparseable", attempt)
                continue
            except anthropic.APIError as error:
                latency_ms = int((time.perf_counter() - started) * 1000)
                last_error = error
                self._log(
                    stage, model, latency_ms, None, "api_error", attempt, type(error).__name__
                )
                # A bad request will fail identically on a retry; a transient
                # one has already been retried by the SDK.
                if isinstance(error, anthropic.BadRequestError | anthropic.AuthenticationError):
                    break
                continue

            latency_ms = int((time.perf_counter() - started) * 1000)
            usage = getattr(response, "usage", None)

            parsed = getattr(response, "parsed_output", None)
            if parsed is None:
                last_error = ValueError("response carried no parsed_output")
                self._log(stage, model, latency_ms, usage, "no_parsed_output", attempt)
                continue

            try:
                validated = output_type.model_validate(
                    {
                        **parsed.model_dump(),
                        "provider": PROVIDER_NAME,
                        "recorded": False,
                    }
                )
            except ValidationError as error:
                last_error = error
                self._log(stage, model, latency_ms, usage, "invalid", attempt)
                continue

            self._log(stage, model, latency_ms, usage, "valid", attempt)
            return validated

        raise ProviderCallFailedError(stage, str(last_error) if last_error else "unknown")

    def _effort_kwargs(self) -> dict[str, object]:
        """Pass effort only when configured; otherwise take the model default.

        Thinking is left entirely alone. Sonnet 5.5 reports
        ``thinking.types.disabled.supported = false``, so sending a disabled
        thinking block would be a 400 on the default model.
        """
        effort = self._settings.llm_effort.strip()
        return {"output_config": {"effort": effort}} if effort else {}

    @staticmethod
    def _user_content(payload: BaseModel, request_text: str, extra_context: str) -> str:
        """Build the user turn: structured context, then the wrapped request."""
        context = payload.model_dump_json(indent=2, exclude={"body_ar"})
        parts = [
            "## Context (structured, from the system)",
            "```json",
            context,
            "```",
        ]
        if extra_context:
            parts.append(extra_context)
        if request_text:
            parts += ["", "## Change request text", wrap_request(request_text)]
        return "\n".join(parts)

    def _log(
        self,
        stage: str,
        model: str,
        latency_ms: int,
        usage: object,
        validation: str,
        attempt: int,
        error_type: str = "",
    ) -> None:
        """NFR-12. Never logs the key, the prompt, or the request body."""
        logger.info(
            "ai_call",
            extra={
                "stage": stage,
                "model": model,
                "prompt_version": prompt_version(stage),
                "latency_ms": latency_ms,
                "input_tokens": getattr(usage, "input_tokens", None),
                "output_tokens": getattr(usage, "output_tokens", None),
                "cache_read_input_tokens": getattr(usage, "cache_read_input_tokens", None),
                "validation": validation,
                "attempt": attempt,
                "error_type": error_type,
            },
        )

    # -- the interface -----------------------------------------------------

    def intake(self, request: IntakeInput) -> IntakeOutput:
        return self._call("INTAKE", request, request.body_ar, IntakeOutput)

    def scope_analysis(self, request: ScopeInput) -> ScopeOutput:
        return self._call("SCOPE_ANALYSIS", request, request.body_ar, ScopeOutput)

    def technical_assessment(self, request: TechnicalInput) -> TechnicalOutput:
        return self._call("TECHNICAL_ASSESSMENT", request, request.body_ar, TechnicalOutput)

    def risk_assessment(self, request: RiskInput) -> RiskOutput:
        return self._call("RISK_COMPLIANCE", request, request.body_ar, RiskOutput)

    def recommendation_narrative(self, request: NarrativeInput) -> NarrativeOutput:
        # No request text: the decision is already made and this is prose only.
        return self._call("ORCHESTRATOR", request, "", NarrativeOutput)

    def vo_draft(self, request: VODraftInput) -> VODraftOutput:
        return self._call("ISSUE_VO", request, "", VODraftOutput)
