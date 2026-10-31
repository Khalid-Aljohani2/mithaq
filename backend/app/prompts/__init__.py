"""Versioned prompt files (NFR-03: prompts are versioned files in the repo).

Each AI stage has its own ``<stage>.<version>.md``. The version is part of the
filename and is recorded on every eval result, so a score always names the
prompts that produced it.
"""

from functools import cache
from pathlib import Path

PROMPT_DIR = Path(__file__).parent

#: Which prompt file each stage uses. Bump the version here, not in code.
PROMPT_VERSIONS: dict[str, str] = {
    # v2: confidence calibration, after round 0 showed a hedging intake stage
    # vetoing classifications the model was 0.95 sure of.
    # v3: impact_type rules. Round 1 left intake at 0.62 on a substitution
    # because "does this change cost?" is unanswerable from a text that quotes
    # no price - which is most texts. The rules decide it without one.
    "INTAKE": "v3",
    "SCOPE_ANALYSIS": "v2",
    "TECHNICAL_ASSESSMENT": "v2",
    "RISK_COMPLIANCE": "v2",
    # These two write prose about a decision already made, and neither
    # appeared in a dev failure. v2 (both): the same call also returns the English wording, so the
    # English interface shows the narrative and the VO scope in English.
    "ORCHESTRATOR": "v2",
    "ISSUE_VO": "v2",
    # Contract intake: reads an uploaded contract into an editable draft. It
    # saves nothing; a person reviews and submits the form (ADR 0006).
    "CONTRACT_DRAFT": "v1",
}

#: Prompt filename stem per stage.
_STEMS: dict[str, str] = {
    "INTAKE": "intake",
    "SCOPE_ANALYSIS": "scope",
    "TECHNICAL_ASSESSMENT": "technical",
    "RISK_COMPLIANCE": "risk",
    "ORCHESTRATOR": "narrative",
    "ISSUE_VO": "vo_draft",
    "CONTRACT_DRAFT": "contract_draft",
}

#: The markers the request text is wrapped in. Everything between them is data.
REQUEST_BEGIN = "<<<REQUEST_TEXT_BEGIN>>>"
REQUEST_END = "<<<REQUEST_TEXT_END>>>"


@cache
def load_prompt(stage: str) -> str:
    """Return the system prompt for a stage, at its configured version."""
    version = PROMPT_VERSIONS[stage]
    path = PROMPT_DIR / f"{_STEMS[stage]}.{version}.md"
    return path.read_text(encoding="utf-8")


def prompt_version(stage: str) -> str:
    """The version string recorded alongside results."""
    return PROMPT_VERSIONS[stage]


def all_versions() -> dict[str, str]:
    """Every stage's prompt version, for the eval result header."""
    return dict(PROMPT_VERSIONS)


def wrap_request(text: str) -> str:
    """Wrap untrusted request text in the data markers (NFR-04).

    Any occurrence of a marker inside the text itself is neutralised, so a
    request cannot close the block early and escape into instruction space.
    """
    cleaned = text.replace(REQUEST_BEGIN, "[marker removed]").replace(
        REQUEST_END, "[marker removed]"
    )
    return f"{REQUEST_BEGIN}\n{cleaned}\n{REQUEST_END}"
