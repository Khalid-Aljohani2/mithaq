"""The published evaluation result (FR-20).

This endpoint reads a committed file and nothing else. It does not run the
evaluation, and it does not recompute a figure: a number shown next to a
recommendation has to be the number a real scored run produced, or it is
decoration. If no run has been published, it says so.
"""

import json
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter

from app.schemas.policy import EvalSummaryResponse

router = APIRouter(prefix="/api/eval", tags=["eval"])

#: ``backend/app/routers/evaluation.py`` -> repository root -> docs/eval.
SUMMARY_PATH = Path(__file__).resolve().parents[3] / "docs" / "eval" / "summary.json"


@lru_cache(maxsize=1)
def _load_summary() -> EvalSummaryResponse:
    """Read and validate the published summary, or report that there is none.

    Cached: the file is part of the deployment and cannot change under a
    running process. ``reset_summary_cache`` exists for the tests that write
    one.
    """
    if not SUMMARY_PATH.is_file():
        return EvalSummaryResponse(available=False, notes="No evaluation run has been published.")
    raw = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
    return EvalSummaryResponse.model_validate({**raw, "available": True})


def reset_summary_cache() -> None:
    """Drop the cached summary so the next request re-reads the file."""
    _load_summary.cache_clear()


@router.get("/summary", response_model=EvalSummaryResponse)
async def eval_summary() -> EvalSummaryResponse:
    """How the pipeline scored on the held-out test split, as published."""
    return _load_summary()
