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
    "INTAKE": "v1",
    "SCOPE_ANALYSIS": "v1",
    "TECHNICAL_ASSESSMENT": "v1",
    "RISK_COMPLIANCE": "v1",
    "ORCHESTRATOR": "v1",
    "ISSUE_VO": "v1",
}

#: Prompt filename stem per stage.
_STEMS: dict[str, str] = {
    "INTAKE": "intake",
    "SCOPE_ANALYSIS": "scope",
    "TECHNICAL_ASSESSMENT": "technical",
    "RISK_COMPLIANCE": "risk",
    "ORCHESTRATOR": "narrative",
    "ISSUE_VO": "vo_draft",
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
