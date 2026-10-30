"""The AI boundary.

Every AI stage in the pipeline goes through this interface. Implementations are
pure functions: schema in, schema out. They receive no repository, no session
and no clock, so a provider is structurally incapable of changing a change
request's state, issuing a variation order or altering a contract value
(NFR-15). The orchestrator treats what comes back as evidence, not instruction.

Step 4A ships only :class:`~app.analysis.scripted.ScriptedProvider`, which
replays recorded outputs and doubles as the fallback mode (FR-19). The live
provider arrives in Step 4B behind this same interface.
"""

from abc import ABC, abstractmethod

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


class AnalysisError(Exception):
    """A provider could not produce a valid result."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class UnknownRequestError(AnalysisError):
    """The scripted provider has no recording for this request text."""

    def __init__(self, fingerprint: str, stage: str) -> None:
        super().__init__(
            "NO_RECORDING",
            f"no recorded {stage} output for request fingerprint {fingerprint[:12]}... "
            "The scripted provider only answers for the seeded demo requests; "
            "a live provider is needed for anything else.",
        )
        self.fingerprint = fingerprint
        self.stage = stage


class AnalysisProvider(ABC):
    """Language understanding for the four AI stages, plus two prose helpers."""

    #: Short identifier recorded on every stage result.
    name: str = "abstract"
    #: True when outputs are replayed rather than generated live (FR-19).
    recorded: bool = False

    @abstractmethod
    def intake(self, request: IntakeInput) -> IntakeOutput:
        """Stage 1: pull the requested change out of free prose (FR-03)."""

    @abstractmethod
    def scope_analysis(self, request: ScopeInput) -> ScopeOutput:
        """Stage 3: in scope or not, and if not, what kind of change (FR-05)."""

    @abstractmethod
    def technical_assessment(self, request: TechnicalInput) -> TechnicalOutput:
        """Stage 4: does it change an approved product or spec (FR-06)."""

    @abstractmethod
    def risk_assessment(self, request: RiskInput) -> RiskOutput:
        """Stage 6: describe the risks around computed findings (FR-08)."""

    @abstractmethod
    def recommendation_narrative(self, request: NarrativeInput) -> NarrativeOutput:
        """Stage 7: turn an already-made decision into readable Arabic (FR-09)."""

    @abstractmethod
    def vo_draft(self, request: VODraftInput) -> VODraftOutput:
        """Stage 9: draft the scope prose of a variation order (FR-12)."""
